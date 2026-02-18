"""
BidPilot v4.1 — Libreria Requisiti Atomici
FIX: eval_D14, eval_D20, eval_D21 aggiornati per modelli tipizzati (non più Dict)
"""
from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional, Any

from src.schemas import (
    BandoRequisiti, CompanyProfile, SOAAttestation,
    RequirementResult, Fixability, CompanyGap, Evidence,
    ReqStatus, Severity
)

CLASSIFICHE_SOA: Dict[str, float] = {
    "I": 258_000, "II": 516_000, "III": 1_033_000,
    "IV": 2_065_000, "V": 3_098_000, "VI": 5_165_000,
    "VII": 10_329_000, "VIII": float("inf")
}
CLASS_RANK = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8}

_CERT_EQUIVALENCES: Dict[str, str] = {
    "OHSAS18001": "ISO45001",
    "BSOHSAS18001": "ISO45001",
    "ISO45001": "OHSAS18001",
}

def _normalize_cert(s: str) -> str:
    return s.upper().replace(" ", "").replace("-", "").replace("_", "").replace(":", "")

def _cert_match(cert_required: str, cert_possessed: str) -> bool:
    req_norm = _normalize_cert(cert_required)
    pos_norm = _normalize_cert(cert_possessed)
    if req_norm == pos_norm:
        return True
    if pos_norm.startswith(req_norm) or req_norm.startswith(pos_norm):
        return True
    equiv = _CERT_EQUIVALENCES.get(req_norm)
    if equiv and _normalize_cert(equiv) == pos_norm:
        return True
    equiv2 = _CERT_EQUIVALENCES.get(pos_norm)
    if equiv2 and _normalize_cert(equiv2) == req_norm:
        return True
    return False


def _today() -> datetime:
    return datetime.now()

def _parse_date(s: str) -> Optional[datetime]:
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s[:10], fmt)
        except Exception:
            pass
    try:
        return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M")
    except Exception:
        pass
    return None

def _ev(quote: str = "", page: int = 0, section: str = "", confidence: float = 1.0) -> Evidence:
    return Evidence(quote=quote, page=page, section=section, confidence=confidence)

def _ok(req_id: str, name: str, cat: str, msg: str,
        evidence: Optional[Evidence] = None, confidence: float = 1.0) -> RequirementResult:
    return RequirementResult(
        req_id=req_id, name=name, category=cat,
        status=ReqStatus.OK, severity=Severity.INFO,
        evidence=[evidence] if evidence else [],
        user_message=msg, confidence=confidence
    )

def _ko(req_id: str, name: str, cat: str, sev: Severity, msg: str,
        fixable: bool = False, methods: List[str] = None,
        constraints: List[str] = None, gaps: List[str] = None,
        evidence: Optional[Evidence] = None, confidence: float = 1.0) -> RequirementResult:
    return RequirementResult(
        req_id=req_id, name=name, category=cat,
        status=ReqStatus.FIXABLE if fixable else ReqStatus.KO,
        severity=sev,
        fixability=Fixability(
            is_fixable=fixable,
            allowed_methods=methods or [],
            constraints=constraints or []
        ),
        company_gap=CompanyGap(missing_assets=gaps or []),
        evidence=[evidence] if evidence else [],
        user_message=msg, confidence=confidence
    )

def _unknown(req_id: str, name: str, cat: str, msg: str,
             evidence: Optional[Evidence] = None,
             sev: Severity = Severity.SOFT_RISK) -> RequirementResult:
    return RequirementResult(
        req_id=req_id, name=name, category=cat,
        status=ReqStatus.UNKNOWN, severity=sev,
        evidence=[evidence] if evidence else [],
        user_message=msg, confidence=0.7
    )

def _risk(req_id: str, name: str, cat: str, msg: str,
          evidence: Optional[Evidence] = None) -> RequirementResult:
    return RequirementResult(
        req_id=req_id, name=name, category=cat,
        status=ReqStatus.RISK_FLAG, severity=Severity.SOFT_RISK,
        evidence=[evidence] if evidence else [],
        user_message=msg, confidence=1.0
    )

def _premiante(req_id: str, name: str, cat: str, msg: str,
               punti_persi: float = 0.0) -> RequirementResult:
    return RequirementResult(
        req_id=req_id, name=name, category=cat,
        status=ReqStatus.PREMIANTE, severity=Severity.INFO,
        user_message=f"[PREMIANTE] {msg} — perdita stimata: {punti_persi:.0f} punti",
        confidence=1.0
    )


# ─────────────────────────────────────────────────────────
# L0 — Classificazione (R00a, R00b)
# ─────────────────────────────────────────────────────────

def eval_R00a(bando: BandoRequisiti) -> RequirementResult:
    doc_type = bando.document_type
    if doc_type == "richiesta_preventivo":
        return _risk("R00a", "Tipo documento — Richiesta preventivo", "meta",
                     "Documento = richiesta preventivo: NON applicare SOA, garanzie, DGUE.")
    if doc_type == "verbale_esito":
        return _risk("R00a", "Tipo documento — Verbale esito", "meta",
                     "Verbale esito: solo knowledge base, NON engine eligibility gara.")
    if doc_type == "sistema_qualificazione":
        return _risk("R00a", "Tipo documento — Sistema di Qualificazione", "meta",
                     "Documento = Sistema di Qualificazione (D11): attivare engine qualificazione D12–D20.")
    return _ok("R00a", f"Tipo documento: {doc_type}", "meta",
               f"Documento classificato come '{doc_type}'. Engine gara ordinaria applicabile.")

def eval_R00b(bando: BandoRequisiti) -> RequirementResult:
    family = bando.procedure_family
    basis = bando.procedure_legal_basis or "N/D"
    return _ok("R00b", f"Procedura: {family}", "meta",
               f"Famiglia procedurale: {family} (base legale: {basis}).")


# ─────────────────────────────────────────────────────────
# L1 — Gate digitali (R01–R05)
# ─────────────────────────────────────────────────────────

def eval_R01(bando: BandoRequisiti) -> Optional[RequirementResult]:
    for sc in bando.scadenze:
        if "offerta" in sc.tipo.lower() or "presentazione" in sc.tipo.lower():
            d = _parse_date(sc.data) if sc.data else None
            if d is None:
                return _unknown("R01", "Deadline offerta", "procedural",
                                f"Data scadenza offerta non parseable: '{sc.data}'.",
                                sev=Severity.HARD_KO)
            if d < _today():
                return _ko("R01", "Deadline offerta SCADUTA", "procedural",
                           Severity.HARD_KO,
                           f"Scadenza offerta già passata ({sc.data}). NO_GO immediato.",
                           confidence=1.0)
            giorni = (d - _today()).days
            msg = f"Deadline offerta: {sc.data} (tra {giorni} giorni)"
            if giorni <= 3:
                return _risk("R01", "Deadline offerta critica", "procedural", msg + " — URGENZA MASSIMA")
            return _ok("R01", "Deadline offerta", "procedural", msg, confidence=1.0)
    return _unknown("R01", "Deadline offerta", "procedural",
                    "Data scadenza offerta non trovata nel documento.",
                    sev=Severity.HARD_KO)

def eval_R02(bando: BandoRequisiti) -> RequirementResult:
    canale = bando.canale_invio
    piatt = bando.piattaforma_gara or "N/D"
    if canale == "unknown":
        return _unknown("R02", "Canale di invio", "procedural",
                        "Canale di invio obbligatorio non identificato.")
    return _ok("R02", f"Canale: {canale}", "procedural",
               f"Canale di invio: {canale}. Piattaforma: {piatt}")

def eval_R03(bando: BandoRequisiti) -> RequirementResult:
    piatt = bando.piattaforma_gara
    if not piatt:
        return _unknown("R03", "Piattaforma telematica", "procedural",
                        "Piattaforma gara non identificata nel documento.")
    msg = f"Verificare registrazione e abilitazione su {piatt}"
    if bando.piattaforma_spid_required:
        msg += " — SPID/domicilio digitale richiesto."
    return RequirementResult(
        req_id="R03", name=f"Piattaforma {piatt}", category="procedural",
        status=ReqStatus.UNKNOWN, severity=Severity.HARD_KO,
        user_message=msg, confidence=1.0
    )

def eval_R04(bando: BandoRequisiti, company: CompanyProfile) -> RequirementResult:
    lr = company.legal_representative
    if not lr.has_digital_signature:
        return _ko("R04", "Firma digitale legale rappresentante", "procedural",
                   Severity.HARD_KO,
                   "Firma digitale mancante: impossibile firmare documenti di gara.",
                   gaps=["Firma digitale CNS/CRS"])
    if lr.signing_powers_proof == "missing":
        return _ko("R04", "Poteri di firma", "procedural", Severity.HARD_KO,
                   "Manca documentazione poteri firma.",
                   gaps=["Procura o statuto con poteri firma"])
    return _ok("R04", "Firma digitale", "procedural",
               f"{lr.name} ({lr.role}) con firma digitale disponibile.")

def eval_R05(bando: BandoRequisiti) -> Optional[RequirementResult]:
    for sc in bando.scadenze:
        if "quesiti" in sc.tipo.lower() or "chiarimenti" in sc.tipo.lower():
            d = _parse_date(sc.data) if sc.data else None
            if d and d < _today():
                return _risk("R05", "Deadline quesiti scaduta", "procedural",
                             f"Deadline quesiti {sc.data} già scaduta.")
            if sc.data:
                return _ok("R05", "Deadline quesiti", "procedural",
                           f"Termine quesiti: {sc.data}.")
    return None


# ─────────────────────────────────────────────────────────
# L2 — Sopralluogo (R06)
# ─────────────────────────────────────────────────────────

def eval_R06(bando: BandoRequisiti) -> Optional[RequirementResult]:
    if not bando.sopralluogo_obbligatorio:
        return None
    ev = _ev(quote=bando.sopralluogo_evidence or "", section="Sopralluogo")
    for sc in bando.scadenze:
        if "sopralluogo" in sc.tipo.lower():
            d = _parse_date(sc.data) if sc.data else None
            if d and d < _today():
                return _ko("R06", "Sopralluogo obbligatorio — SCADUTO", "procedural",
                           Severity.HARD_KO,
                           f"Sopralluogo obbligatorio SCADUTO ({sc.data}). Partecipazione IMPOSSIBILE.",
                           evidence=ev)
            if sc.data:
                return RequirementResult(
                    req_id="R06", name="Sopralluogo obbligatorio", category="procedural",
                    status=ReqStatus.UNKNOWN, severity=Severity.HARD_KO, evidence=[ev],
                    user_message=f"Sopralluogo OBBLIGATORIO a pena di esclusione entro {sc.data}. Prenotare.",
                    confidence=1.0
                )
    return RequirementResult(
        req_id="R06", name="Sopralluogo obbligatorio", category="procedural",
        status=ReqStatus.UNKNOWN, severity=Severity.HARD_KO, evidence=[ev],
        user_message="Sopralluogo OBBLIGATORIO a pena di esclusione. Verificare deadline.",
        confidence=1.0
    )


# ─────────────────────────────────────────────────────────
# L3 — ANAC / FVOE (R07, R08, R09)
# ─────────────────────────────────────────────────────────

def eval_R07(bando: BandoRequisiti) -> Optional[RequirementResult]:
    if bando.anac_contributo_richiesto == "no":
        return None
    if bando.anac_contributo_richiesto == "unknown":
        if bando.codice_cig:
            return _unknown("R07", "Contributo ANAC", "procedural",
                            f"CIG presente ({bando.codice_cig}) ma contributo ANAC non esplicitato.",
                            sev=Severity.HARD_KO)
        return None
    return RequirementResult(
        req_id="R07", name="Contributo ANAC", category="procedural",
        status=ReqStatus.UNKNOWN, severity=Severity.HARD_KO,
        user_message="Contributo ANAC richiesto. Pagare su FVOE/pagoPA prima della scadenza.",
        confidence=1.0
    )

def eval_R08(bando: BandoRequisiti) -> Optional[RequirementResult]:
    if not bando.fvoe_required:
        return None
    return RequirementResult(
        req_id="R08", name="FVOE — Fascicolo Virtuale OE", category="procedural",
        status=ReqStatus.UNKNOWN, severity=Severity.SOFT_RISK,
        user_message="FVOE richiesto: verificare completezza del fascicolo.",
        confidence=1.0
    )

def eval_R09(bando: BandoRequisiti) -> RequirementResult:
    return _risk("R09", "Verifica requisiti post-aggiudicazione", "procedural",
                 "Dopo l'aggiudicazione: verifica requisiti prevista. "
                 "KO verifica → incameramento cauzione + segnalazione ANAC.")


# ─────────────────────────────────────────────────────────
# L4 — Forma di partecipazione (R10, R11, R12)
# ─────────────────────────────────────────────────────────

def eval_R10(bando: BandoRequisiti, company: CompanyProfile) -> RequirementResult:
    allowed = bando.allowed_forms
    if not allowed:
        return _ok("R10", "Forme partecipazione", "participation",
                   "Forme non specificate: tutte ammesse (default art.65 d.lgs.36/2023).")
    forms_str = ", ".join(allowed)
    if "singolo" in allowed or not company.willing_rti:
        return _ok("R10", "Forme partecipazione", "participation",
                   f"Forme ammesse: {forms_str}. Partecipazione singola verificata.")
    if company.willing_rti and "RTI" in " ".join(allowed).upper():
        return _ok("R10", "Forme partecipazione", "participation",
                   f"Forme ammesse: {forms_str}. RTI ammesso.")
    return _unknown("R10", "Forme partecipazione", "participation",
                    f"Forme ammesse: {forms_str}. Verificare compatibilità.")

def eval_R11(bando: BandoRequisiti) -> Optional[RequirementResult]:
    if bando.rti_ammesso == "no":
        return None
    if bando.rti_mandataria_quota_min or bando.rti_mandante_quota_min:
        msg = (f"RTI: mandataria ≥{bando.rti_mandataria_quota_min or '?'}%, "
               f"mandante ≥{bando.rti_mandante_quota_min or '?'}%.")
        return _risk("R11", "RTI — Quote minime", "participation",
                     msg + " " + (bando.rti_regole or ""))
    return _ok("R11", "RTI — Quote", "participation",
               f"RTI ammesso. Regole: {bando.rti_regole or 'verificare disciplinare'}")

def eval_R12(bando: BandoRequisiti) -> RequirementResult:
    return RequirementResult(
        req_id="R12", name="Divieto partecipazione plurima", category="general",
        status=ReqStatus.UNKNOWN, severity=Severity.HARD_KO,
        user_message="Verificare: impresa non partecipa allo stesso lotto sia come singolo "
                     "sia come componente RTI. Controllare controllante/controllata.",
        confidence=1.0
    )


# ─────────────────────────────────────────────────────────
# L5 — Requisiti generali (R13–R17)
# ─────────────────────────────────────────────────────────

def eval_R13(bando: BandoRequisiti) -> Optional[RequirementResult]:
    if not bando.dgue_required:
        return None
    sezioni = ", ".join(bando.dgue_sezioni_obbligatorie) if bando.dgue_sezioni_obbligatorie else "standard"
    return RequirementResult(
        req_id="R13", name="DGUE obbligatorio", category="general",
        status=ReqStatus.UNKNOWN, severity=Severity.HARD_KO,
        user_message=f"DGUE obbligatorio. Sezioni: {sezioni}. "
                     f"Formato: {bando.dgue_format or 'PDF/eDGUE'}. In RTI: DGUE per ogni membro.",
        confidence=1.0
    )

def eval_R14(bando: BandoRequisiti) -> RequirementResult:
    return RequirementResult(
        req_id="R14", name="Cause di esclusione art.94–98", category="general",
        status=ReqStatus.UNKNOWN, severity=Severity.HARD_KO,
        user_message="Verificare assenza cause esclusione (art.94–98 d.lgs.36/2023) per: "
                     "legale rappresentante, soci maggioritari, direttori tecnici, amministratori.",
        confidence=0.7
    )

def eval_R15(bando: BandoRequisiti) -> RequirementResult:
    return RequirementResult(
        req_id="R15", name="Regolarità DURC e fiscale", category="general",
        status=ReqStatus.UNKNOWN, severity=Severity.HARD_KO,
        user_message="Verificare DURC in corso di validità (120 giorni) e regolarità fiscale.",
        confidence=0.7
    )

def eval_R16(bando: BandoRequisiti) -> Optional[RequirementResult]:
    if not bando.protocollo_legalita_required and not bando.patto_integrita_required:
        return None
    if bando.patto_integrita_pena_esclusione:
        return RequirementResult(
            req_id="R16", name="Patto integrità (pena esclusione)", category="general",
            status=ReqStatus.UNKNOWN, severity=Severity.HARD_KO,
            user_message="Patto integrità obbligatorio A PENA DI ESCLUSIONE. Leggere il testo.",
            confidence=1.0
        )
    return _ok("R16", "Patto integrità", "general",
               "Patto integrità/protocollo legalità richiesto: firmare e allegare.")

def eval_R17(bando: BandoRequisiti) -> Optional[RequirementResult]:
    if not bando.piattaforma_failure_policy_exists:
        return None
    return _risk("R17", "Policy malfunzionamento piattaforma", "procedural",
                 "In caso di malfunzionamento certificato: (1) screenshot con timestamp, "
                 "(2) PEC immediata alla SA, (3) conservare log.")


# ─────────────────────────────────────────────────────────
# L6 — Idoneità professionale (R18, R19)
# ─────────────────────────────────────────────────────────

def eval_R18(bando: BandoRequisiti, company: CompanyProfile) -> RequirementResult:
    cr = company.cameral_registration
    if cr.is_registered and cr.coherence_with_tender_object == "yes":
        return _ok("R18", "Iscrizione CCIAA", "professional",
                   f"Impresa iscritta CCIAA (REA: {cr.rea_number}), oggetto sociale coerente.")
    if not cr.is_registered:
        return _ko("R18", "Iscrizione CCIAA", "professional", Severity.HARD_KO,
                   "Impresa non iscritta CCIAA.", gaps=["Iscrizione CCIAA"])
    if cr.coherence_with_tender_object == "no":
        return _ko("R18", "CCIAA — Coerenza oggetto sociale", "professional", Severity.HARD_KO,
                   "Oggetto sociale non coerente con l'appalto.",
                   fixable=True, methods=["rti"], gaps=["Coerenza oggetto sociale"])
    return _unknown("R18", "Iscrizione CCIAA", "professional",
                    "Verificare iscrizione CCIAA e coerenza oggetto sociale con CPV gara.")

def eval_R19(bando: BandoRequisiti, company: CompanyProfile) -> Optional[RequirementResult]:
    if not bando.albi_professionali_required:
        return None
    albi_str = ", ".join(bando.albi_professionali_required)
    company_roles = [r.role.lower() for r in company.key_roles]
    missing = [a for a in bando.albi_professionali_required
               if not any(a.lower() in r for r in company_roles)]
    if not missing:
        return _ok("R19", "Albi professionali", "professional",
                   f"Figure professionali richieste ({albi_str}) disponibili internamente.")
    return _ko("R19", "Albi professionali", "professional", Severity.HARD_KO,
               f"Figure mancanti: {', '.join(missing)}.",
               fixable=True, methods=["progettisti"], gaps=missing)


# ─────────────────────────────────────────────────────────
# L7 — Economico-finanziari (R20–R23)
# ─────────────────────────────────────────────────────────

def eval_R20(bando: BandoRequisiti, company: CompanyProfile) -> Optional[RequirementResult]:
    req = bando.fatturato_minimo_richiesto
    if not req:
        return None
    recent = sorted(company.turnover_by_year, key=lambda x: x.year, reverse=True)[:bando.fatturato_anni_riferimento]
    if not recent:
        return _unknown("R20", "Fatturato globale minimo", "financial",
                        f"Soglia: {req:,.0f}€. Caricare dati fatturato nel profilo.",
                        sev=Severity.HARD_KO)
    avg = sum(r.amount_eur for r in recent) / len(recent)
    if avg >= req:
        return _ok("R20", "Fatturato globale minimo", "financial",
                   f"Fatturato medio {avg:,.0f}€ ≥ soglia {req:,.0f}€ ✓")
    methods = []
    if bando.avvalimento_ammesso == "yes":
        methods.append("avvalimento")
    if bando.rti_ammesso == "yes":
        methods.append("rti (sommando fatturati)")
    return _ko("R20", "Fatturato globale minimo", "financial", Severity.HARD_KO,
               f"Fatturato medio {avg:,.0f}€ < soglia {req:,.0f}€.",
               fixable=bool(methods), methods=methods,
               gaps=[f"Fatturato globale {req:,.0f}€"])

def eval_R21(bando: BandoRequisiti, company: CompanyProfile) -> Optional[RequirementResult]:
    req_val = bando.referenze_valore_min
    if not req_val:
        return None
    similar = company.similar_works
    if not similar:
        return _unknown("R21", "Referenze lavori/servizi analoghi", "financial",
                        f"Soglia referenze: {req_val:,.0f}€ in {bando.referenze_anni_lookback} anni. "
                        "Inserire opere analoghe nel profilo.",
                        sev=Severity.HARD_KO)
    tot = sum(w.amount_eur for w in similar)
    if tot >= req_val:
        return _ok("R21", "Referenze lavori analoghi", "financial",
                   f"Referenze totali {tot:,.0f}€ ≥ soglia {req_val:,.0f}€ ✓")
    methods = []
    if bando.avvalimento_ammesso == "yes":
        methods.append("avvalimento")
    if bando.rti_ammesso == "yes":
        methods.append("rti")
    return _ko("R21", "Referenze lavori analoghi", "financial", Severity.HARD_KO,
               f"Referenze {tot:,.0f}€ < soglia {req_val:,.0f}€ in {bando.referenze_anni_lookback} anni.",
               fixable=bool(methods), methods=methods,
               gaps=[f"Referenze analoghi {req_val:,.0f}€"])

def eval_R22(bando: BandoRequisiti) -> Optional[RequirementResult]:
    if not bando.is_eoi or not bando.eoi_territorial_experience_required:
        return None
    area = bando.eoi_territorial_area or "area specificata nel documento"
    return _risk("R22", f"EOI — Esperienza territoriale ({area})", "procedural",
                 f"Esperienza in '{area}' è CRITERIO DI SELEZIONE EOI, NON requisito gara. "
                 f"Lookback: {bando.eoi_territorial_lookback_years} anni.")

def eval_R23(bando: BandoRequisiti) -> Optional[RequirementResult]:
    if not bando.is_eoi or not bando.eoi_size_factor_used:
        return None
    ref_year = bando.eoi_employee_reference_year or "anno precedente"
    return _risk("R23", "EOI — Fattore dimensione aziendale", "procedural",
                 f"Dimensione aziendale influenza punteggio EOI. Anno riferimento: {ref_year}. "
                 "NON è soglia minima → non genera KO.")


# ─────────────────────────────────────────────────────────
# L8 — SOA (R24–R29, D01–D10)
# ─────────────────────────────────────────────────────────

def _find_soa(company: CompanyProfile, category: str) -> Optional[SOAAttestation]:
    for att in company.soa_attestations:
        if att.category.upper() == category.upper():
            return att
    return None

def _soa_valid(att: SOAAttestation) -> bool:
    d = _parse_date(att.expiry_date)
    return d is not None and d > _today()

def _check_soa_equivalence(bando: BandoRequisiti, required_cat: str,
                            company: CompanyProfile) -> Optional[str]:
    for eq in bando.soa_equivalences:
        if eq.to_cat.upper() == required_cat.upper():
            att = _find_soa(company, eq.from_cat)
            if att and _soa_valid(att):
                return eq.from_cat
    return None

def eval_R24(bando: BandoRequisiti) -> Optional[RequirementResult]:
    imp = bando.importo_lavori or bando.importo_base_gara
    if imp is None:
        return _unknown("R24", "Importo base gara", "qualification",
                        "Importo base gara non trovato: tutti i calcoli SOA → UNKNOWN.",
                        sev=Severity.HARD_KO)
    if imp < 150_000:
        return _risk("R24", f"Importo {imp:,.0f}€ — sotto soglia SOA 150k", "qualification",
                     f"Importo {imp:,.0f}€ < 150.000€: NON applicare check SOA.")
    return _ok("R24", f"Importo base {imp:,.0f}€", "qualification",
               f"Importo base: {imp:,.0f}€. Classifiche SOA applicabili.")

def eval_R25(bando: BandoRequisiti, company: CompanyProfile) -> RequirementResult:
    imp = bando.importo_lavori or bando.importo_base_gara
    if imp and imp < 150_000:
        return _ok("R25", "SOA prevalente — N/A sotto soglia", "qualification",
                   "Importo < 150k: check SOA non applicabile.")
    prev = next((s for s in bando.soa_richieste if s.prevalente), None)
    if not prev and bando.soa_richieste:
        prev = bando.soa_richieste[0]
    if not prev:
        return _unknown("R25", "SOA prevalente", "qualification",
                        "Nessuna categoria SOA prevalente rilevata.")
    ev = _ev(quote=prev.evidence or "", section="Requisiti SOA", confidence=1.0)
    equiv_cat = _check_soa_equivalence(bando, prev.categoria, company)
    if equiv_cat:
        return _ok("R25", f"SOA {prev.categoria} (equivalenza {equiv_cat})", "qualification",
                   f"Equivalenza SOA esplicita: {equiv_cat} ≡ {prev.categoria} ✓", evidence=ev)
    att = _find_soa(company, prev.categoria)
    if att is None:
        fix_methods, constraints = [], []
        if bando.avvalimento_ammesso == "yes" and prev.categoria not in bando.avvalimento_banned_categories:
            fix_methods.append("avvalimento")
            constraints.append("Ausiliaria non può partecipare alla stessa gara")
        if bando.rti_ammesso == "yes":
            fix_methods.append("rti")
        return _ko("R25", f"SOA prevalente {prev.categoria} cl.{prev.classifica}", "qualification",
                   Severity.HARD_KO,
                   f"SOA {prev.categoria} cl.{prev.classifica} NON posseduta.",
                   fixable=bool(fix_methods), methods=fix_methods, constraints=constraints,
                   gaps=[f"SOA {prev.categoria} cl.{prev.classifica}"], evidence=ev)
    if not _soa_valid(att):
        return _ko("R25", f"SOA {prev.categoria} scaduta", "qualification",
                   Severity.HARD_KO,
                   f"SOA {prev.categoria} SCADUTA il {att.expiry_date}. Rinnovare SUBITO.",
                   gaps=[f"Rinnovo SOA {prev.categoria}"], evidence=ev)
    poss_rank = CLASS_RANK.get(att.soa_class, 0)
    req_rank = CLASS_RANK.get(prev.classifica, 0)
    if poss_rank >= req_rank:
        return _ok("R25", f"SOA prevalente {prev.categoria}", "qualification",
                   f"SOA {prev.categoria} cl.{att.soa_class} ✓ (scad. {att.expiry_date})",
                   evidence=ev)
    fix_methods = []
    if bando.avvalimento_ammesso == "yes" and prev.categoria not in bando.avvalimento_banned_categories:
        fix_methods.append("avvalimento")
    if bando.rti_ammesso == "yes":
        fix_methods.append("rti")
    return _ko("R25", f"SOA prevalente {prev.categoria}", "qualification",
               Severity.HARD_KO,
               f"SOA {prev.categoria} posseduta cl.{att.soa_class} < richiesta cl.{prev.classifica}.",
               fixable=bool(fix_methods), methods=fix_methods,
               gaps=[f"SOA {prev.categoria} cl.{prev.classifica}"], evidence=ev)

def eval_R26_scorporabili(bando: BandoRequisiti, company: CompanyProfile) -> List[RequirementResult]:
    results = []
    scorp = [s for s in bando.soa_richieste if not s.prevalente]
    for s in scorp:
        ev = _ev(quote=s.evidence or "", section="Categorie lavori")
        req_id = f"R26_{s.categoria}"
        equiv_cat = _check_soa_equivalence(bando, s.categoria, company)
        if equiv_cat:
            results.append(_ok(req_id, f"SOA scorporabile {s.categoria} (equiv. {equiv_cat})",
                               "qualification", f"Equivalenza: {equiv_cat} ≡ {s.categoria} ✓", evidence=ev))
            continue
        att = _find_soa(company, s.categoria)
        has_soa = att and _soa_valid(att) and CLASS_RANK.get(att.soa_class, 0) >= CLASS_RANK.get(s.classifica, 0)
        if has_soa:
            results.append(_ok(req_id, f"SOA scorporabile {s.categoria}", "qualification",
                               f"SOA {s.categoria} cl.{att.soa_class} ✓", evidence=ev))
        else:
            methods = []
            if s.subappaltabile_100 or (bando.subappalto_percentuale_max and bando.subappalto_percentuale_max > 0):
                if bando.subappalto_qualificante_dichiarazione_pena_esclusione:
                    methods.append("subappalto_qualificante [DICHIARAZIONE A PENA ESCLUSIONE]")
                else:
                    methods.append("subappalto_qualificante")
            if bando.avvalimento_ammesso == "yes" and s.categoria not in bando.avvalimento_banned_categories:
                methods.append("avvalimento")
            if bando.rti_ammesso == "yes":
                methods.append("rti")
            results.append(_ko(req_id, f"SOA scorporabile {s.categoria}", "qualification",
                               Severity.HARD_KO,
                               f"SOA {s.categoria} cl.{s.classifica} mancante.",
                               fixable=bool(methods), methods=methods,
                               gaps=[f"SOA {s.categoria} cl.{s.classifica}"], evidence=ev))
    return results

def eval_R27(bando: BandoRequisiti) -> Optional[RequirementResult]:
    imp = bando.importo_lavori or bando.importo_base_gara
    if not imp or imp >= 150_000:
        return None
    if not bando.alt_qualification_allowed:
        return _unknown("R27", "Qualificazione alternativa (sotto soglia)", "qualification",
                        "Importo < 150k: verificare art.90 DPR 207/2010 o All.II.18 art.10.",
                        sev=Severity.HARD_KO)
    alt_type = bando.alt_qualification_type or "art90"
    return _ok("R27", f"Qualificazione alternativa ({alt_type})", "qualification",
               f"Qualificazione alternativa {alt_type} applicabile.")

def eval_R27_alt_culturale(bando: BandoRequisiti) -> Optional[RequirementResult]:
    if bando.alt_qualification_type != "art10_allII18":
        return None
    return _risk("D07", "Qualificazione All.II.18 art.10 (beni culturali)", "qualification",
                 "Qualificazione beni culturali: 5 requisiti art.10. NON usare art.90 come fallback.")

def eval_R29_accordo_quadro(bando: BandoRequisiti) -> Optional[RequirementResult]:
    if not bando.is_accordo_quadro:
        return None
    return _risk("R29", "Accordo Quadro — Regole speciali", "qualification",
                 "AQ: requisiti SOA per categorie del perimetro. Verificare ordini attuativi.")

def eval_R28_soa_validita(bando: BandoRequisiti, company: CompanyProfile) -> List[RequirementResult]:
    results = []
    deadline_offerta = None
    for sc in bando.scadenze:
        if "offerta" in sc.tipo.lower() or "presentazione" in sc.tipo.lower():
            deadline_offerta = _parse_date(sc.data) if sc.data else None
            break
    for att in company.soa_attestations:
        exp = _parse_date(att.expiry_date)
        req_id = f"C5_{att.category}"
        if exp is None:
            results.append(_unknown(req_id, f"Validità SOA {att.category}", "qualification",
                                    f"Data scadenza SOA {att.category} non leggibile."))
        elif exp < _today():
            results.append(_ko(req_id, f"SOA {att.category} SCADUTA", "qualification",
                               Severity.HARD_KO,
                               f"SOA {att.category} SCADUTA il {att.expiry_date}.",
                               gaps=[f"Rinnovo SOA {att.category}"]))
        elif deadline_offerta and exp < deadline_offerta:
            results.append(_ko(req_id, f"SOA {att.category} scade prima dell'offerta", "qualification",
                               Severity.HARD_KO,
                               f"SOA {att.category} scade {att.expiry_date}, prima della deadline. Rinnovare.",
                               gaps=[f"Rinnovo SOA {att.category}"]))
        else:
            results.append(_ok(req_id, f"Validità SOA {att.category}", "qualification",
                               f"SOA {att.category} valida fino al {att.expiry_date}"))
    if bando.soa_copy_required_pena_esclusione:
        results.append(RequirementResult(
            req_id="D08", name="Copia SOA obbligatoria (pena esclusione)", category="qualification",
            status=ReqStatus.UNKNOWN, severity=Severity.HARD_KO,
            user_message="Allegare copia attestato SOA PENA DI ESCLUSIONE.",
            confidence=1.0
        ))
    return results


# ─────────────────────────────────────────────────────────
# D01–D10: SOA Differenzianti
# ─────────────────────────────────────────────────────────

def eval_D02(bando: BandoRequisiti) -> Optional[RequirementResult]:
    if bando.soa_fifth_increase_allowed is None or not bando.soa_fifth_increase_allowed:
        return None
    return _risk("D02", "Regola +1/5 classifica SOA", "qualification",
                 "Regola incremento quinto classifica SOA esplicitamente citata.")

def eval_D05(bando: BandoRequisiti, company: CompanyProfile) -> Optional[RequirementResult]:
    if not bando.avvalimento_banned_categories:
        return None
    banned = [c for c in bando.avvalimento_banned_categories if c.upper() in ("OG2", "OS2A", "OS2B")]
    if not banned:
        return None
    missing_og2 = [c for c in banned if not _find_soa(company, c)]
    if missing_og2:
        fix_methods = []
        if bando.rti_ammesso == "yes":
            fix_methods.append("rti")
        if bando.subappalto_qualificante_ammesso == "yes":
            fix_methods.append("subappalto_qualificante")
        return _ko("D05", "SOA OG2/culturali — avvalimento vietato (art.132)", "qualification",
                   Severity.HARD_KO,
                   f"Avvalimento vietato ex art.132 per {', '.join(missing_og2)}.",
                   fixable=bool(fix_methods), methods=fix_methods, gaps=missing_og2)
    return _ok("D05", "SOA beni culturali OG2", "qualification",
               f"SOA {', '.join(banned)} presente: divieto avvalimento art.132 non impatta.")

def eval_D06(bando: BandoRequisiti) -> Optional[RequirementResult]:
    if not bando.cultural_works_dm154_required:
        return None
    if bando.cultural_works_dm154_pena_esclusione:
        return RequirementResult(
            req_id="D06", name="DM 154/2017 qualificazione beni culturali", category="qualification",
            status=ReqStatus.UNKNOWN, severity=Severity.HARD_KO,
            user_message="Qualificazione DM 154/2017 obbligatoria A PENA DI ESCLUSIONE.",
            confidence=1.0
        )
    return _unknown("D06", "DM 154/2017 beni culturali", "qualification",
                    "DM 154/2017 richiesto: verificare possesso.")

def eval_D09(bando: BandoRequisiti) -> Optional[RequirementResult]:
    if not bando.lots_max_awardable_per_bidder or bando.lotti <= 1:
        return None
    return _risk("D09", f"Lotti: max {bando.lots_max_awardable_per_bidder} aggiudicazione", "procedural",
                 f"In {bando.lotti} lotti, max aggiudicabile = {bando.lots_max_awardable_per_bidder}. "
                 "Scegliere il lotto target strategico.")

def eval_D10(bando: BandoRequisiti, company: CompanyProfile) -> Optional[RequirementResult]:
    cl = bando.credit_license
    if not cl or not cl.required:
        return None
    trigger = cl.trigger_condition or "non specificato"
    has_soa_iii = any(
        CLASS_RANK.get(att.soa_class, 0) >= 3 and _soa_valid(att)
        for att in company.soa_attestations
    )
    if cl.trigger_soa_class_threshold == "III" and has_soa_iii:
        return _ok("D10", "Patente a crediti — N/A (SOA ≥ III)", "qualification",
                   "Patente a crediti: trigger SOA < III. OE con SOA ≥ III non soggetta.")
    if cl.pena_esclusione:
        if company.has_credit_license == "yes" or company.credit_license_requested:
            return _ok("D10", "Patente a crediti", "qualification",
                       "Patente a crediti disponibile o richiesta ✓")
        return _ko("D10", "Patente a crediti mancante (pena esclusione)", "qualification",
                   Severity.HARD_KO,
                   f"Patente a crediti obbligatoria A PENA ESCLUSIONE. Trigger: '{trigger}'.",
                   gaps=["Patente a crediti — presentare richiesta"])
    return RequirementResult(
        req_id="D10", name="Patente a crediti", category="qualification",
        status=ReqStatus.UNKNOWN, severity=Severity.SOFT_RISK,
        user_message=f"Patente a crediti richiesta. Trigger: '{trigger}'. Verificare.",
        confidence=0.7
    )


# ─────────────────────────────────────────────────────────
# L9 — Garanzie (R30, R31, R32)
# ─────────────────────────────────────────────────────────

def eval_R30(bando: BandoRequisiti, company: CompanyProfile) -> Optional[RequirementResult]:
    if bando.garanzie_richieste is None:
        return None
    g = bando.garanzie_richieste
    if g.provvisoria is None and g.percentuale_provvisoria is None:
        return None
    imp = g.provvisoria
    if imp is None and g.percentuale_provvisoria and (bando.importo_lavori or bando.importo_base_gara):
        imp = (bando.importo_lavori or bando.importo_base_gara) * g.percentuale_provvisoria / 100
    msg = f"Cauzione provvisoria: {imp:,.0f}€" if imp else "Cauzione provvisoria richiesta"
    has_iso9001 = any(_cert_match("ISO 9001", c.cert_type) for c in company.certifications)
    if has_iso9001:
        riduz = imp * 0.5 if imp else None
        msg += f" (riduzione 50% per ISO 9001 → {riduz:,.0f}€)" if riduz else " (riduzione 50% per ISO 9001)"
    return RequirementResult(
        req_id="R30", name="Garanzia provvisoria", category="guarantee",
        status=ReqStatus.UNKNOWN, severity=Severity.HARD_KO,
        user_message=msg + ". Attivare fideiussione bancaria/assicurativa.",
        confidence=1.0
    )

def eval_R31_R32(bando: BandoRequisiti) -> List[RequirementResult]:
    results = []
    g = bando.garanzie_richieste
    if g and g.definitiva:
        results.append(_risk("R31", f"Cauzione definitiva {g.definitiva:,.0f}€", "guarantee",
                             "Cauzione definitiva richiesta prima della stipula."))
    for pol in bando.polizze_richieste:
        results.append(_risk(f"R32_{pol}", f"Polizza {pol}", "guarantee",
                             f"Polizza {pol} richiesta. Tempi emissione 2-4 settimane: pianificare."))
    return results


# ─────────────────────────────────────────────────────────
# L10 — Avvalimento e subappalto (R33, R34, R35)
# ─────────────────────────────────────────────────────────

def eval_R33(bando: BandoRequisiti) -> Optional[RequirementResult]:
    if bando.avvalimento_ammesso == "no":
        return RequirementResult(
            req_id="R33", name="Avvalimento VIETATO", category="participation",
            status=ReqStatus.KO, severity=Severity.SOFT_RISK,
            user_message="Il bando ESCLUDE l'avvalimento. Non utilizzabile per colmare gap.",
            confidence=1.0
        )
    if bando.avvalimento_ammesso == "yes":
        banned_str = f" Vietato per: {', '.join(bando.avvalimento_banned_categories)}." \
                     if bando.avvalimento_banned_categories else ""
        return _ok("R33", "Avvalimento ammesso", "participation",
                   f"Avvalimento ammesso.{banned_str} "
                   f"Regole: {bando.avvalimento_regole or 'verificare'}.")
    return None

def eval_R34(bando: BandoRequisiti) -> Optional[RequirementResult]:
    pct = bando.subappalto_percentuale_max
    if pct is None:
        return None
    msg = f"Subappalto max {pct:.0f}%. Divieto cascata: {'sì' if bando.subappalto_cascade_ban else 'no'}."
    if bando.subappalto_dichiarazione_dgue_pena_esclusione:
        msg += " ⚠️ DICHIARAZIONE SUBAPPALTO NEL DGUE OBBLIGATORIA A PENA DI ESCLUSIONE."
        return RequirementResult(
            req_id="R34", name="Subappalto — dichiarazione DGUE pena esclusione",
            category="participation", status=ReqStatus.UNKNOWN, severity=Severity.HARD_KO,
            user_message=msg, confidence=1.0
        )
    return _ok("R34", "Limite subappalto", "participation", msg)

def eval_R35(bando: BandoRequisiti) -> Optional[RequirementResult]:
    if bando.subappalto_qualificante_ammesso == "no":
        return None
    if bando.subappalto_qualificante_ammesso == "yes":
        msg = "Subappalto qualificante ammesso per copertura categorie scorporabili mancanti."
        if bando.subappalto_qualificante_dichiarazione_pena_esclusione:
            msg += " ⚠️ DICHIARAZIONE OBBLIGATORIA A PENA DI ESCLUSIONE."
        if bando.soa_prevalent_must_cover_subcontracted:
            msg += " ⚠️ La classifica prevalente deve coprire ANCHE l'importo subappaltato."
        return _ok("R35", "Subappalto qualificante", "participation", msg)
    return None


# ─────────────────────────────────────────────────────────
# L11 — CCNL e manodopera (R36, R37)
# ─────────────────────────────────────────────────────────

def eval_R36(bando: BandoRequisiti, company: CompanyProfile) -> Optional[RequirementResult]:
    if not bando.ccnl_reference:
        return None
    if company.ccnl_applied and company.ccnl_applied.lower() != bando.ccnl_reference.lower():
        return _risk("R36", "CCNL — Dichiarazione equivalenza necessaria", "general",
                     f"SA richiede CCNL '{bando.ccnl_reference}', azienda applica '{company.ccnl_applied}'.")
    return _ok("R36", "CCNL applicabile", "general",
               f"CCNL riferimento: {bando.ccnl_reference}.")

def eval_R37(bando: BandoRequisiti) -> Optional[RequirementResult]:
    if not bando.labour_costs_must_indicate and not bando.safety_company_costs_must_indicate:
        return None
    pena = bando.labour_costs_pena_esclusione or bando.safety_costs_pena_esclusione
    parts = []
    if bando.labour_costs_must_indicate:
        parts.append("costi manodopera")
    if bando.safety_company_costs_must_indicate:
        parts.append("oneri sicurezza aziendali")
    msg = "Indicare nell'offerta economica: " + ", ".join(parts)
    if pena:
        msg += " — A PENA DI ESCLUSIONE."
        return RequirementResult(
            req_id="R37", name="Costi manodopera/sicurezza — pena esclusione",
            category="general", status=ReqStatus.UNKNOWN, severity=Severity.HARD_KO,
            user_message=msg, confidence=1.0
        )
    return _risk("R37", "Costi manodopera/sicurezza", "general", msg)


# ─────────────────────────────────────────────────────────
# L12 — PNRR (R38, R39, R40)
# ─────────────────────────────────────────────────────────

def eval_R38_R39(bando: BandoRequisiti) -> List[RequirementResult]:
    results = []
    if not bando.is_pnrr:
        return results
    if bando.pnrr_dnsh_required:
        results.append(RequirementResult(
            req_id="R38", name="PNRR — DNSH obbligatorio", category="general",
            status=ReqStatus.UNKNOWN, severity=Severity.HARD_KO,
            user_message="DNSH obbligatorio: allegare dichiarazione + checklist. Mancanza = KO.",
            confidence=1.0
        ))
    if bando.pnrr_principi_required:
        principi_str = ", ".join(bando.pnrr_principi_required)
        results.append(RequirementResult(
            req_id="R39", name=f"PNRR — Principi trasversali ({principi_str})",
            category="general", status=ReqStatus.UNKNOWN, severity=Severity.HARD_KO,
            user_message=f"Principi PNRR richiesti: {principi_str}.",
            confidence=0.7
        ))
    if bando.cam_obbligatori:
        results.append(_risk("R40", f"CAM obbligatori: {', '.join(bando.cam_obbligatori)}", "general",
                             "CAM obbligatori in capitolato."))
    return results


# ─────────────────────────────────────────────────────────
# L13 — BIM (R41–R45)
# ─────────────────────────────────────────────────────────

def eval_R41_R45(bando: BandoRequisiti, company: CompanyProfile) -> List[RequirementResult]:
    results = []
    if not bando.is_bim or not bando.bim_capitolato_informativo:
        return results
    if bando.bim_ogi_required:
        results.append(RequirementResult(
            req_id="R41", name="BIM — OGI obbligatoria nell'offerta tecnica",
            category="design", status=ReqStatus.UNKNOWN, severity=Severity.HARD_KO,
            user_message="OGI (Offerta Gestione Informativa): OBBLIGATORIA come contenuto offerta tecnica.",
            confidence=1.0
        ))
    if bando.bim_experience_required:
        if bando.bim_experience_is_admission:
            min_count = bando.bim_experience_min_count or 1
            if company.has_bim_experience and company.bim_experience_count >= min_count:
                results.append(_ok("R42", "BIM — Esperienza pregressa", "design",
                                   f"Esperienza BIM: {company.bim_experience_count} lavori ≥ {min_count} ✓"))
            else:
                results.append(_ko("R42", "BIM — Esperienza pregressa mancante", "design",
                                   Severity.HARD_KO,
                                   f"Bando richiede ≥{min_count} lavori BIM come requisito di ammissione.",
                                   fixable=bando.rti_ammesso == "yes",
                                   methods=["rti"] if bando.rti_ammesso == "yes" else [],
                                   gaps=[f"Esperienze BIM pregresse (min {min_count})"]))
        else:
            if company.has_bim_experience:
                results.append(_premiante("R42", "BIM — Esperienza pregressa", "design",
                                          "Esperienza BIM disponibile: inserire nell'OGI per OEPV."))
            else:
                results.append(_premiante("R42", "BIM — Esperienza mancante", "design",
                                          "Esperienza BIM non dichiarata: perdita punti OEPV.", 5.0))
    if bando.bim_ruoli_minimi:
        results.append(_risk("R43", f"BIM ruoli: {', '.join(bando.bim_ruoli_minimi)}", "design",
                             f"Ruoli BIM da dichiarare nell'OGI: {', '.join(bando.bim_ruoli_minimi)}."))
    lod_items = []
    if bando.bim_lod_min_fase:
        lod_items.append(f"LOD min fase: {bando.bim_lod_min_fase}")
    if bando.bim_ifc_required:
        schema_str = f" (schema: {bando.bim_ifc_schema})" if bando.bim_ifc_schema else ""
        lod_items.append(f"IFC obbligatorio{schema_str}")
    if bando.bim_as_built_required:
        lod_items.append("As-built BIM (LOD F)")
    if lod_items:
        results.append(_risk("R44", "BIM LOD/IFC deliverable", "design",
                             f"Deliverable BIM: {'; '.join(lod_items)}."))
    if bando.bim_4d_required or bando.bim_5d_required:
        dims = []
        if bando.bim_4d_required:
            dims.append("4D (scheduling)")
        if bando.bim_5d_required:
            dims.append("5D (computo/SAL)")
        results.append(_risk("R45", f"BIM {'+'.join(dims)}", "design",
                             f"BIM {' e '.join(dims)} richiesto."))
    return results


# ─────────────────────────────────────────────────────────
# L14 — Appalto integrato (R46–R49)
# ─────────────────────────────────────────────────────────

def eval_R46(bando: BandoRequisiti, company: CompanyProfile) -> Optional[RequirementResult]:
    if not bando.appalto_integrato:
        return None
    ev = _ev(quote=bando.appalto_integrato_evidence or "", section="Appalto integrato")
    if company.has_inhouse_design:
        return _ok("R46", "Progettazione (appalto integrato)", "design",
                   "Capacità progettuale interna disponibile.", evidence=ev)
    if company.external_designers_available == "yes" and company.design_team:
        return _ok("R46", "Progettazione (appalto integrato)", "design",
                   f"Progettisti esterni: {len(company.design_team)} figure disponibili.", evidence=ev)
    return _ko("R46", "Progettazione (appalto integrato)", "design",
               Severity.HARD_KO,
               "Appalto integrato: progettisti obbligatori (indicazione nominativa in offerta).",
               fixable=True, methods=["progettisti"],
               gaps=["Gruppo di progettazione"], evidence=ev)

def eval_R47(bando: BandoRequisiti, company: CompanyProfile) -> Optional[RequirementResult]:
    if bando.giovane_professionista_richiesto != "yes":
        return None
    for d in company.design_team:
        if d.young_professional == "yes":
            return _ok("R47", "Giovane professionista", "design",
                       f"{d.name}: soddisfa requisito giovane professionista.")
    return _ko("R47", "Giovane professionista mancante", "design",
               Severity.HARD_KO,
               "Bando richiede giovane professionista. Verificare soglia anni nel disciplinare.",
               fixable=True, methods=["progettisti"],
               gaps=["Giovane professionista abilitato"])

def eval_R48(bando: BandoRequisiti) -> Optional[RequirementResult]:
    if not bando.tech_offer_divieto_prezzi_pena_esclusione:
        return None
    msg = "Offerta tecnica NON deve contenere prezzi/costi A PENA DI ESCLUSIONE."
    if bando.tech_offer_max_pagine:
        msg += f" Max {bando.tech_offer_max_pagine} pagine."
    return RequirementResult(
        req_id="R48", name="Offerta tecnica — divieti formali", category="design",
        status=ReqStatus.UNKNOWN, severity=Severity.HARD_KO,
        user_message=msg, confidence=1.0
    )

def eval_R49(bando: BandoRequisiti) -> Optional[RequirementResult]:
    if not bando.tech_offer_riservatezza_required:
        return None
    scope = bando.tech_offer_riservatezza_scope or "parti da indicare esplicitamente"
    return _risk("R49", "Offerta tecnica — dichiarazione riservatezza", "design",
                 f"Dichiarazione riservatezza richiesta ({scope}). NON è KO se omessa.")


# ─────────────────────────────────────────────────────────
# L15 — Regole contrattuali (R50–R53)
# ─────────────────────────────────────────────────────────

def eval_R50(bando: BandoRequisiti) -> Optional[RequirementResult]:
    if not bando.inversione_procedimentale:
        return None
    return _risk("R50", "Inversione procedimentale (art.107)", "procedural",
                 "Sequenza invertita: SA apre offerte economiche PRIMA dei requisiti.")

def eval_R51_R52(bando: BandoRequisiti) -> List[RequirementResult]:
    results = []
    if bando.quinto_obbligo:
        results.append(_risk("R51", "Quinto d'obbligo", "operational",
                             "SA può variare il contratto ±20%. Includere margine nell'offerta."))
    if bando.revisione_prezzi_soglia_pct:
        results.append(_risk("R51b", f"Revisione prezzi (soglia {bando.revisione_prezzi_soglia_pct}%)",
                             "operational",
                             f"Revisione prezzi attivata oltre {bando.revisione_prezzi_soglia_pct}%."))
    if bando.cct_previsto:
        comp_str = f" ({bando.cct_composizione} componenti)" if bando.cct_composizione else ""
        results.append(_risk("R52_CCT", f"Collegio Consultivo Tecnico{comp_str}", "operational",
                             "CCT previsto: strumento per risoluzione rapida delle riserve."))
    if bando.arbitrato_escluso:
        foro = bando.foro_competente or "N/D"
        results.append(_risk("R52_arbitrato", "Arbitrato escluso", "operational",
                             f"Controversie solo in sede ordinaria (foro: {foro})."))
    elif bando.foro_competente:
        results.append(_risk("R52_foro", f"Foro competente: {bando.foro_competente}", "operational",
                             f"Verificare distanza dalla sede aziendale."))
    return results

def eval_R53(bando: BandoRequisiti) -> Optional[RequirementResult]:
    if not bando.tech_claims_must_be_provable:
        return None
    timing_str = {
        "pre_aggiudicazione": "prima dell'aggiudicazione",
        "post_aggiudicazione": "dopo l'aggiudicazione",
        "unknown": "timing da verificare"
    }.get(bando.tech_claims_verification_timing, "da verificare")
    return _risk("R53", "Dichiarazioni tecniche — prova documentale", "design",
                 f"Dichiarazioni offerta tecnica devono essere supportate da documentazione "
                 f"(verifica {timing_str}). Mappare ogni claim con documento PRIMA della presentazione.")


# ─────────────────────────────────────────────────────────
# L16 — Tipologie speciali (R54–R60)
# ─────────────────────────────────────────────────────────

def eval_R54_R55(bando: BandoRequisiti) -> List[RequirementResult]:
    results = []
    if not bando.is_concession:
        return results
    if bando.concession_price_in_tech_ko:
        results.append(RequirementResult(
            req_id="R54", name="Concessione — separazione buste",
            category="procedural", status=ReqStatus.UNKNOWN, severity=Severity.HARD_KO,
            user_message="CONCESSIONE: prezzi nella busta tecnica = HARD KO automatico.",
            confidence=1.0
        ))
    if bando.concession_offer_forbidden_forms:
        forms_str = ", ".join(bando.concession_offer_forbidden_forms)
        results.append(RequirementResult(
            req_id="R55", name="Concessione — offerta inammissibile", category="procedural",
            status=ReqStatus.UNKNOWN, severity=Severity.HARD_KO,
            user_message=f"Forme offerta inammissibili: {forms_str}.",
            confidence=1.0
        ))
    return results

def eval_R58(bando: BandoRequisiti) -> Optional[RequirementResult]:
    if not bando.is_eoi:
        return None
    criteria_str = ", ".join(bando.eoi_selection_criteria) if bando.eoi_selection_criteria else "N/D"
    target = bando.eoi_invited_count_target or "N/D"
    return _risk("R58", f"EOI — Selezione invitati (target: {target})", "procedural",
                 f"Criteri selezione EOI ({criteria_str}) NON sono requisiti di ammissione gara.")

def eval_R59(bando: BandoRequisiti) -> Optional[RequirementResult]:
    if not bando.sa_reserve_rights:
        return None
    return _risk("R59", "Riserva SA: annullamento/sospensione", "procedural",
                 "La SA si riserva di non procedere senza obblighi verso i partecipanti.")

def eval_R60(bando: BandoRequisiti) -> Optional[RequirementResult]:
    if not bando.platform_failure_extends_deadline and not bando.platform_failure_notification_required:
        if not bando.platform_failure_oe_obligations:
            return None
    obligations = bando.platform_failure_oe_obligations or [
        "Screenshot con timestamp del tentativo fallito",
        "PEC immediata alla SA con documentazione",
        "Conservare log di sistema"
    ]
    obligations_str = "; ".join(obligations)
    proroga_str = "SA DEVE prorogare se malfunzionamento certificato. " if bando.platform_failure_extends_deadline else ""
    return _risk("R60", "Piattaforma — procedura malfunzionamento", "procedural",
                 f"Procedura operativa: {obligations_str}. {proroga_str}")


# ─────────────────────────────────────────────────────────
# D11–D23: Qualificazione e PPP
# ─────────────────────────────────────────────────────────

def eval_D11(bando: BandoRequisiti) -> Optional[RequirementResult]:
    if not bando.is_qualification_system:
        return None
    owner = bando.qualification_system_owner or "N/D"
    return _risk("D11", f"Sistema di Qualificazione {owner} — Engine qualificazione attivato",
                 "meta",
                 f"DOCUMENTO = Sistema di Qualificazione ({owner}). "
                 "Attivare SOLO D12–D20. Output: ELIGIBLE/NOT_ELIGIBLE, non GO/NO_GO gara.")

def eval_D12(bando: BandoRequisiti) -> Optional[RequirementResult]:
    if not bando.is_qualification_system:
        return None
    return RequirementResult(
        req_id="D12", name="Requisiti alla data domanda (qualificazione)", category="qualification",
        status=ReqStatus.UNKNOWN, severity=Severity.HARD_KO,
        user_message="In sistema di qualificazione: tutti i requisiti devono essere POSSEDUTI "
                     "alla data della domanda. Mancanza → KO non sanabile.",
        confidence=1.0
    )

def eval_D13(bando: BandoRequisiti) -> Optional[RequirementResult]:
    if not bando.is_qualification_system:
        return None
    gg = bando.qualification_missing_docs_deadline_days
    effetto = bando.qualification_failure_effect or "decadenza_domanda"
    return _risk("D13", "Qualificazione — monitoraggio integrazioni documenti", "qualification",
                 f"Se SA richiede integrazione documenti: rispondere entro {gg or 'N/D'} giorni. "
                 f"Mancata risposta → {effetto}.")

def eval_D14(bando: BandoRequisiti) -> Optional[RequirementResult]:
    """FIX: MaintenanceVariation ha .type e .notify_within_days (non .get())"""
    if not bando.is_qualification_system or not bando.maintenance_variation_types:
        return None
    var_list = [
        f"{v.type or '?'}: entro {v.notify_within_days or '?'} gg"
        for v in bando.maintenance_variation_types
    ]
    return _risk("D14", "Mantenimento qualificazione — comunicazione variazioni", "qualification",
                 "Obbligo comunicazione variazioni: " + "; ".join(var_list) + ". "
                 "Ritardo → sospensione/dequalifica.")

def eval_D15(bando: BandoRequisiti) -> Optional[RequirementResult]:
    if not bando.is_qualification_system:
        return None
    exp = bando.qualification_expiry_date
    if exp:
        d = _parse_date(exp)
        if d:
            months_left = (d - _today()).days / 30
            if months_left < bando.maintenance_submit_months_before:
                return _ko("D15", "Rinnovo qualificazione — URGENTE", "qualification",
                           Severity.HARD_KO,
                           f"Qualificazione scade {exp} (tra ~{months_left:.0f} mesi). "
                           f"Inviare rinnovo almeno {bando.maintenance_submit_months_before} mesi prima.",
                           gaps=["Domanda rinnovo qualificazione"])
    return _risk("D15", "Rinnovo qualificazione triennale", "qualification",
                 f"Ciclo rinnovo: {bando.maintenance_renewal_cycle_years} anni. "
                 f"Inviare almeno {bando.maintenance_submit_months_before} mesi prima della scadenza.")

def eval_D16(bando: BandoRequisiti, company: CompanyProfile) -> Optional[RequirementResult]:
    if not bando.is_qualification_system:
        return None
    threshold = bando.psf_min_threshold
    if threshold is None:
        return _unknown("D16", "PSF/PSFM — score economico-finanziario", "financial",
                        "Soglie PSF/PSFM rinviate a normativa di sottosistema. Consultare committente.",
                        sev=Severity.HARD_KO)
    psf_company = company.psf_score
    if psf_company is None:
        return _unknown("D16", "PSF/PSFM", "financial",
                        f"Soglia PSF: {threshold}. Calcolare PSF aziendale e confrontare.")
    if psf_company >= float(threshold):
        return _ok("D16", "PSF — score sufficiente", "financial",
                   f"PSF aziendale {psf_company:.2f} ≥ soglia {threshold} ✓")
    return _ko("D16", "PSF sotto soglia", "financial", Severity.HARD_KO,
               f"PSF {psf_company:.2f} < soglia {threshold}.",
               gaps=["PSF/PSFM sufficiente"])

def eval_D17(bando: BandoRequisiti, company: CompanyProfile) -> Optional[RequirementResult]:
    if not bando.is_qualification_system:
        return None
    min_req = bando.financial_min_bilanci_applicant
    count = company.deposited_statements_count
    if count < min_req:
        avv_allowed = bando.avvalimento_ammesso == "yes"
        return _ko("D17", f"Bilanci depositati insufficienti ({count} < {min_req})", "financial",
                   Severity.HARD_KO,
                   f"Richiedente: {count} bilanci, richiesti ≥{min_req}.",
                   fixable=avv_allowed, methods=["avvalimento"] if avv_allowed else [],
                   gaps=[f"Bilanci depositati (min {min_req})"])
    return _ok("D17", f"Bilanci depositati {count} ≥ {min_req}", "financial",
               "Bilanci depositati sufficienti ✓")

def eval_D18(bando: BandoRequisiti, company: CompanyProfile) -> Optional[RequirementResult]:
    if not bando.is_qualification_system or not bando.avvalimento_non_frazionabili:
        return None
    nf_str = ", ".join(bando.avvalimento_non_frazionabili)
    return _risk("D18", f"Avvalimento — requisiti non frazionabili: {nf_str}", "qualification",
                 f"Requisiti non frazionabili ({nf_str}): soluzione BINARIA.")

def eval_D19(bando: BandoRequisiti, company: CompanyProfile) -> Optional[RequirementResult]:
    if not bando.is_qualification_system:
        return None
    if bando.rete_soggettivita_giuridica_required:
        return _risk("D19", "Rete — soggettività giuridica richiesta", "qualification",
                     "Rete SENZA soggettività giuridica: NON qualificabile come soggetto unico.")
    if bando.interpello_class_type:
        return _risk("D19", f"Classe interpello: {bando.interpello_class_type}", "qualification",
                     f"Classe '{bando.interpello_class_type}': {bando.interpello_cap_rule or 'verificare cap'}.")
    return None

def eval_D20(bando: BandoRequisiti) -> Optional[RequirementResult]:
    """FIX: QualificationFee ha .system e .amount (non .get())"""
    if not bando.is_qualification_system or not bando.qualification_fee_required:
        return None
    if bando.qualification_fee_amounts:
        fee_str = "; ".join(
            f"{f.system or '?'}: {f.amount or '?'}€"
            for f in bando.qualification_fee_amounts
        )
    else:
        fee_str = "verificare tabella"
    return RequirementResult(
        req_id="D20", name="Fee qualificazione obbligatorio", category="procedural",
        status=ReqStatus.UNKNOWN, severity=Severity.HARD_KO,
        user_message=f"Rimborso spese richiesto: {fee_str}. Mancato pagamento → KO procedura.",
        confidence=1.0
    )

def eval_D21(bando: BandoRequisiti) -> Optional[RequirementResult]:
    """FIX: ProcedureStage ha .name (non .get('name'))"""
    if not bando.procedure_multi_stage:
        return None
    stages_str = ", ".join(s.name or "?" for s in bando.procedure_stages) \
                 if bando.procedure_stages else "N/D"
    return _risk("D21", f"PPP multi-stage: {stages_str}", "meta",
                 f"Procedura multi-stage ({stages_str}). Mai GO/NO_GO unico. Output per FASE.")

def eval_D22(bando: BandoRequisiti, company: CompanyProfile) -> Optional[RequirementResult]:
    if not bando.ppp_private_share_percent and not bando.ppp_private_contribution_amount:
        return None
    contrib = bando.ppp_private_contribution_amount
    pct = bando.ppp_private_share_percent
    msg = f"Quota privata: {pct or '?'}% ({contrib:,.0f}€)." if contrib else f"Quota privata: {pct or '?'}%."
    spv_msg = f" SPV richiesta. Governance: {bando.ppp_governance_constraints or 'verificare'}." \
              if bando.ppp_spv_required else ""
    return _unknown("D22", "PPP — quota privata e SPV", "financial",
                    msg + spv_msg,
                    sev=Severity.HARD_KO)

def eval_D23(bando: BandoRequisiti) -> Optional[RequirementResult]:
    if not bando.security_special_regime:
        return None
    impact = bando.security_admission_impact
    if impact == "esclusione":
        return RequirementResult(
            req_id="D23", name="Security — regime speciale (pena esclusione)", category="general",
            status=ReqStatus.UNKNOWN, severity=Severity.HARD_KO,
            user_message=f"Security speciale A PENA DI ESCLUSIONE. "
                         f"Riferimento: {bando.security_reference_text or 'N/D'}.",
            confidence=1.0
        )
    return _risk("D23", "Security — regime speciale infrastrutture critiche", "general",
                 f"Regime di sicurezza speciale ({bando.security_reference_text or 'N/D'}): "
                 "condizione di esecuzione, non di ammissione.")


# ─────────────────────────────────────────────────────────
# Certificazioni
# ─────────────────────────────────────────────────────────

def eval_D_certificazioni(bando: BandoRequisiti, company: CompanyProfile) -> List[RequirementResult]:
    results = []
    for i, cert_req in enumerate(bando.certificazioni_richieste):
        req_id = f"D{i+1}"
        found = next((c for c in company.certifications if _cert_match(cert_req, c.cert_type)), None)
        if not found:
            similar = next((c for c in company.certifications
                            if _normalize_cert(cert_req)[:3] in _normalize_cert(c.cert_type)), None)
            note = ""
            if similar:
                note = (f" ATTENZIONE: l'azienda ha '{similar.cert_type}' "
                        f"ma NON soddisfa '{cert_req}' (scope diverso).")
            results.append(_ko(req_id, f"Certificazione {cert_req}", "certification",
                               Severity.HARD_KO,
                               f"{cert_req} NON posseduta." + note,
                               gaps=[cert_req]))
        else:
            exp = _parse_date(found.expiry_date) if found.expiry_date else None
            if exp and exp < _today():
                results.append(_ko(req_id, f"Certificazione {cert_req}", "certification",
                                   Severity.HARD_KO,
                                   f"{cert_req} SCADUTA il {found.expiry_date}.",
                                   gaps=[f"Rinnovo {cert_req}"]))
            else:
                results.append(_ok(req_id, f"Certificazione {cert_req}", "certification",
                                   f"{cert_req} valida (scad. {found.expiry_date or 'N/D'}) ✓"))
    return results


# ─────────────────────────────────────────────────────────
# Vincoli esecutivi (M1, M2+)
# ─────────────────────────────────────────────────────────

def eval_M1(bando: BandoRequisiti, company: CompanyProfile) -> Optional[RequirementResult]:
    if not bando.start_lavori_tassativo:
        return None
    d = _parse_date(bando.start_lavori_tassativo)
    giorni = (d - _today()).days if d else None
    msg = f"Inizio lavori tassativo: {bando.start_lavori_tassativo}"
    if giorni is not None:
        msg += f" (tra {giorni} giorni)"
    if company.start_date_constraints:
        msg += f". Vincoli azienda: {company.start_date_constraints}"
    return RequirementResult(
        req_id="M1", name="Inizio lavori tassativo", category="operational",
        status=ReqStatus.UNKNOWN, severity=Severity.SOFT_RISK,
        user_message=msg + ". Valutare disponibilità risorse.", confidence=1.0
    )

def eval_M_vincoli(bando: BandoRequisiti) -> List[RequirementResult]:
    results = []
    for i, v in enumerate(bando.vincoli_esecutivi):
        results.append(RequirementResult(
            req_id=f"M{i+2}", name="Vincolo esecutivo", category="operational",
            status=ReqStatus.UNKNOWN, severity=Severity.SOFT_RISK,
            user_message=v, confidence=0.7
        ))
    return results


# ══════════════════════════════════════════════════════════
# ENTRY POINT PRINCIPALE
# ══════════════════════════════════════════════════════════

def evaluate_all(bando: BandoRequisiti, company: CompanyProfile,
                 participation_forms: Any = None) -> List[RequirementResult]:
    results: List[RequirementResult] = []

    # L0 — Classificazione (sempre)
    results.append(eval_R00a(bando))
    results.append(eval_R00b(bando))

    d11 = eval_D11(bando)
    if d11:
        results.append(d11)

    # ENGINE QUALIFICAZIONE
    if bando.is_qualification_system:
        for fn in [eval_D12, eval_D13, eval_D14, eval_D15]:
            r = fn(bando)
            if r:
                results.append(r)
        for fn_co in [(eval_D16, company), (eval_D17, company)]:
            r = fn_co[0](bando, fn_co[1])
            if r:
                results.append(r)
        r = eval_D18(bando, company)
        if r:
            results.append(r)
        r = eval_D19(bando, company)
        if r:
            results.append(r)
        r = eval_D20(bando)
        if r:
            results.append(r)
        return [r for r in results if r is not None]

    # ENGINE GARA ORDINARIA
    is_preventivo = bando.document_type == "richiesta_preventivo"

    # L1 — Gate digitali
    for fn in [eval_R01, eval_R05]:
        r = fn(bando)
        if r:
            results.append(r)
    results.append(eval_R02(bando))
    results.append(eval_R03(bando))
    results.append(eval_R04(bando, company))
    r = eval_R60(bando)
    if r:
        results.append(r)

    # L2 — Sopralluogo
    r = eval_R06(bando)
    if r:
        results.append(r)

    # L3 — ANAC/FVOE
    for fn in [eval_R07, eval_R08]:
        r = fn(bando)
        if r:
            results.append(r)
    results.append(eval_R09(bando))

    if not is_preventivo:
        # L4 — Partecipazione
        results.append(eval_R10(bando, company))
        r = eval_R11(bando)
        if r:
            results.append(r)
        results.append(eval_R12(bando))

        # L5 — Requisiti generali
        r = eval_R13(bando)
        if r:
            results.append(r)
        results.append(eval_R14(bando))
        results.append(eval_R15(bando))
        r = eval_R16(bando)
        if r:
            results.append(r)
        r = eval_R17(bando)
        if r:
            results.append(r)

        # L6 — Idoneità professionale
        results.append(eval_R18(bando, company))
        r = eval_R19(bando, company)
        if r:
            results.append(r)

        # L7 — Economico-finanziari
        for fn_c in [eval_R20, eval_R21]:
            r = fn_c(bando, company)
            if r:
                results.append(r)
        for fn_b in [eval_R22, eval_R23]:
            r = fn_b(bando)
            if r:
                results.append(r)

        # L8 — SOA
        r = eval_R24(bando)
        if r:
            results.append(r)
        results.append(eval_R25(bando, company))
        results.extend(eval_R26_scorporabili(bando, company))
        r = eval_R27(bando)
        if r:
            results.append(r)
        r = eval_R27_alt_culturale(bando)
        if r:
            results.append(r)
        results.extend(eval_R28_soa_validita(bando, company))
        r = eval_R29_accordo_quadro(bando)
        if r:
            results.append(r)

        # D01–D10
        r = eval_D02(bando)
        if r:
            results.append(r)
        r = eval_D05(bando, company)
        if r:
            results.append(r)
        r = eval_D06(bando)
        if r:
            results.append(r)
        r = eval_D09(bando)
        if r:
            results.append(r)
        r = eval_D10(bando, company)
        if r:
            results.append(r)

        # L9 — Garanzie
        r = eval_R30(bando, company)
        if r:
            results.append(r)
        results.extend(eval_R31_R32(bando))

        # L10 — Avvalimento e subappalto
        r = eval_R33(bando)
        if r:
            results.append(r)
        r = eval_R34(bando)
        if r:
            results.append(r)
        r = eval_R35(bando)
        if r:
            results.append(r)

        # L11 — CCNL
        r = eval_R36(bando, company)
        if r:
            results.append(r)
        r = eval_R37(bando)
        if r:
            results.append(r)

        # L12 — PNRR
        results.extend(eval_R38_R39(bando))

        # L13 — BIM
        results.extend(eval_R41_R45(bando, company))

        # L14 — Appalto integrato
        r = eval_R46(bando, company)
        if r:
            results.append(r)
        r = eval_R47(bando, company)
        if r:
            results.append(r)
        r = eval_R48(bando)
        if r:
            results.append(r)
        r = eval_R49(bando)
        if r:
            results.append(r)

        # L15 — Regole contrattuali
        r = eval_R50(bando)
        if r:
            results.append(r)
        results.extend(eval_R51_R52(bando))
        r = eval_R53(bando)
        if r:
            results.append(r)

        # L16 — Tipologie speciali
        results.extend(eval_R54_R55(bando))
        r = eval_R58(bando)
        if r:
            results.append(r)
        r = eval_R59(bando)
        if r:
            results.append(r)

        # Certificazioni
        results.extend(eval_D_certificazioni(bando, company))

    # PPP / Grandi Opere
    r = eval_D21(bando)
    if r:
        results.append(r)
    r = eval_D22(bando, company)
    if r:
        results.append(r)
    r = eval_D23(bando)
    if r:
        results.append(r)

    # Vincoli esecutivi
    r = eval_M1(bando, company)
    if r:
        results.append(r)
    results.extend(eval_M_vincoli(bando))

    return [r for r in results if r is not None]