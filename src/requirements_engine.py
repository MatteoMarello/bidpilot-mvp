"""
BidPilot v3.0 — Libreria Requisiti Atomici (A1–M7)
Ogni requisito ha: id, name, category, severity, sanabilità, logica di valutazione.
"""
from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional, Any

from src.schemas import (
    BandoRequisiti, CompanyProfile, SOAAttestation,
    RequirementResult, Fixability, CompanyGap, Evidence,
    ReqStatus, Severity
)

# Classifiche SOA → importo massimo coperto (€)
CLASSIFICHE_SOA: Dict[str, float] = {
    "I": 258_000, "II": 516_000, "III": 1_033_000,
    "IV": 2_065_000, "V": 3_098_000, "VI": 5_165_000,
    "VII": 10_329_000, "VIII": float("inf")
}

CLASS_RANK = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8}

# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────

def _today() -> datetime:
    return datetime.now()

def _parse_date(s: str) -> Optional[datetime]:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None

def _ev(quote: str = "", page: int = 0, section: str = "") -> Evidence:
    return Evidence(quote=quote, page=page, section=section)

def _ok(req_id: str, name: str, cat: str, msg: str,
        evidence: Optional[Evidence] = None) -> RequirementResult:
    return RequirementResult(
        req_id=req_id, name=name, category=cat,
        status=ReqStatus.OK, severity=Severity.INFO,
        evidence=[evidence] if evidence else [],
        user_message=msg
    )

def _ko(req_id: str, name: str, cat: str, sev: Severity, msg: str,
        fixable: bool = False, methods: List[str] = None,
        constraints: List[str] = None, gaps: List[str] = None,
        evidence: Optional[Evidence] = None) -> RequirementResult:
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
        user_message=msg
    )

def _unknown(req_id: str, name: str, cat: str, msg: str,
             evidence: Optional[Evidence] = None) -> RequirementResult:
    return RequirementResult(
        req_id=req_id, name=name, category=cat,
        status=ReqStatus.UNKNOWN, severity=Severity.SOFT_RISK,
        evidence=[evidence] if evidence else [],
        user_message=msg
    )


# ─────────────────────────────────────────────────────────
# Requisiti A — Ammissibilità generale
# ─────────────────────────────────────────────────────────

def eval_A1(bando: BandoRequisiti, company: CompanyProfile) -> RequirementResult:
    """A1 – Cause di esclusione (art. 94-98)"""
    return RequirementResult(
        req_id="A1", name="Cause di esclusione", category="general",
        status=ReqStatus.UNKNOWN, severity=Severity.HARD_KO,
        user_message=(
            "Verificare assenza cause di esclusione (art. 94-98 d.lgs. 36/2023). "
            "Richiedere autocertificazione al legale rappresentante e a tutti i soggetti indicati."
        )
    )

def eval_A2(bando: BandoRequisiti, company: CompanyProfile) -> RequirementResult:
    """A2 – Patti integrità / anticollusione"""
    return RequirementResult(
        req_id="A2", name="Patto integrità / anticollusione", category="general",
        status=ReqStatus.UNKNOWN, severity=Severity.HARD_KO,
        user_message="Verificare possibilità di sottoscrivere patto di integrità e dichiarazioni anticollusione."
    )

def eval_A5(bando: BandoRequisiti, company: CompanyProfile) -> RequirementResult:
    """A5 – Regolarità fiscale (DURC/DURF)"""
    return RequirementResult(
        req_id="A5", name="Regolarità fiscale", category="general",
        status=ReqStatus.UNKNOWN, severity=Severity.HARD_KO,
        user_message=(
            "Verificare posizione fiscale e DURC. "
            "Irregolarità fiscale è causa di esclusione non sanabile."
        )
    )


# ─────────────────────────────────────────────────────────
# Requisiti B — Idoneità professionale
# ─────────────────────────────────────────────────────────

def eval_B1(bando: BandoRequisiti, company: CompanyProfile) -> RequirementResult:
    """B1 – Iscrizione CCIAA"""
    cr = company.cameral_registration
    if cr.is_registered and cr.coherence_with_tender_object == "yes":
        return _ok("B1", "Iscrizione CCIAA", "professional",
                   f"Impresa iscritta CCIAA (REA: {cr.rea_number}), oggetto sociale coerente.")
    if not cr.is_registered:
        return _ko("B1", "Iscrizione CCIAA", "professional", Severity.HARD_KO,
                   "Impresa non risulta iscritta CCIAA. Requisito non sanabile.",
                   gaps=["Iscrizione CCIAA"])
    if cr.coherence_with_tender_object == "no":
        return _ko("B1", "Iscrizione CCIAA", "professional", Severity.HARD_KO,
                   "Oggetto sociale non coerente con l'appalto. Verificare ATECO e oggetto.",
                   gaps=["Coerenza oggetto sociale"])
    return _unknown("B1", "Iscrizione CCIAA", "professional",
                    "Verificare iscrizione CCIAA e coerenza oggetto sociale con l'appalto.")

def eval_B4(bando: BandoRequisiti, company: CompanyProfile) -> RequirementResult:
    """B4 – Procura / poteri firma"""
    lr = company.legal_representative
    if not lr.has_digital_signature:
        return _ko("B4", "Firma digitale legale rappresentante", "procedural",
                   Severity.HARD_KO,
                   "Il firmatario non dispone di firma digitale valida. Procurarsela prima della scadenza.",
                   gaps=["Firma digitale CNS/CRS"])
    if lr.signing_powers_proof == "missing":
        return _ko("B4", "Poteri di firma", "procedural", Severity.HARD_KO,
                   "Manca documentazione poteri firma (procura/statuto). Allegare prima della scadenza.",
                   gaps=["Procura o statuto con poteri firma"])
    if lr.has_digital_signature and lr.signing_powers_proof in ("available", "unknown"):
        return _ok("B4", "Firma digitale", "procedural",
                   f"{lr.name} ({lr.role}) con firma digitale disponibile.")
    return _unknown("B4", "Firma digitale", "procedural",
                    "Verificare disponibilità firma digitale e poteri firma del sottoscrittore.")


# ─────────────────────────────────────────────────────────
# Requisiti C — Qualificazione SOA
# ─────────────────────────────────────────────────────────

def _find_soa(company: CompanyProfile, category: str) -> Optional[SOAAttestation]:
    for att in company.soa_attestations:
        if att.category.upper() == category.upper():
            return att
    return None

def _soa_valid(att: SOAAttestation) -> bool:
    d = _parse_date(att.expiry_date)
    return d is not None and d > _today()

def eval_C1_prevalente(bando: BandoRequisiti, company: CompanyProfile,
                       participation_forms: Any) -> RequirementResult:
    """C1 – Categoria prevalente: possesso SOA richiesta"""
    prev = None
    for s in bando.soa_richieste:
        if s.prevalente:
            prev = s
            break
    if not prev and bando.soa_richieste:
        prev = bando.soa_richieste[0]
    if not prev:
        return _unknown("C1", "SOA prevalente", "qualification",
                        "Nessuna categoria SOA prevalente rilevata nel bando.")

    ev = _ev(quote=prev.evidence or "", section="Requisiti SOA")
    att = _find_soa(company, prev.categoria)

    if att is None:
        # Non posseduta
        fix_methods = []
        constraints = []
        if bando.avvalimento_ammesso == "yes":
            fix_methods.append("avvalimento")
            constraints.append("Ausiliaria non può partecipare alla stessa gara")
            constraints.append("Contratto avvalimento deve indicare risorse/mezzi specifici")
        if bando.rti_ammesso == "yes":
            fix_methods.append("rti")
            constraints.append("Quote RTI devono rispettare le regole del bando")
        return _ko(
            "C1", f"SOA prevalente {prev.categoria} cl.{prev.classifica}", "qualification",
            Severity.HARD_KO,
            f"SOA {prev.categoria} classifica {prev.classifica} NON posseduta. "
            f"Importo richiesto: {CLASSIFICHE_SOA.get(prev.classifica, '?'):,}€",
            fixable=bool(fix_methods),
            methods=fix_methods,
            constraints=constraints,
            gaps=[f"SOA {prev.categoria} cl.{prev.classifica}"],
            evidence=ev
        )

    if not _soa_valid(att):
        return _ko(
            "C1", f"SOA prevalente {prev.categoria}", "qualification",
            Severity.HARD_KO,
            f"SOA {prev.categoria} SCADUTA il {att.expiry_date}. Rinnovarla PRIMA della scadenza offerta.",
            gaps=[f"Rinnovo SOA {prev.categoria}"],
            evidence=ev
        )

    poss_rank = CLASS_RANK.get(att.soa_class, 0)
    req_rank = CLASS_RANK.get(prev.classifica, 0)

    if poss_rank >= req_rank:
        return _ok("C1", f"SOA prevalente {prev.categoria}", "qualification",
                   f"SOA {prev.categoria} cl.{att.soa_class} ✓ (scad. {att.expiry_date})", evidence=ev)
    else:
        gap_eur = CLASSIFICHE_SOA.get(prev.classifica, 0) - CLASSIFICHE_SOA.get(att.soa_class, 0)
        fix_methods = []
        if bando.avvalimento_ammesso == "yes":
            fix_methods.append("avvalimento")
        if bando.rti_ammesso == "yes":
            fix_methods.append("rti")
        return _ko(
            "C1", f"SOA prevalente {prev.categoria}", "qualification",
            Severity.HARD_KO,
            f"SOA {prev.categoria} posseduta cl.{att.soa_class} < richiesta cl.{prev.classifica}. "
            f"Gap: {gap_eur:,.0f}€",
            fixable=bool(fix_methods),
            methods=fix_methods,
            constraints=["Contratto avvalimento con risorse esplicite se avvalimento"],
            gaps=[f"SOA {prev.categoria} cl.{prev.classifica}"],
            evidence=ev
        )

def eval_C2_scorporabili(bando: BandoRequisiti, company: CompanyProfile) -> List[RequirementResult]:
    """C2 – Scorporabili / categorie secondarie"""
    results = []
    scorp = [s for s in bando.soa_richieste if not s.prevalente]
    for s in scorp:
        ev = _ev(quote=s.evidence or "", section="Categorie lavori")
        att = _find_soa(company, s.categoria)
        req_id = f"C2_{s.categoria}"

        if att and _soa_valid(att) and CLASS_RANK.get(att.soa_class, 0) >= CLASS_RANK.get(s.classifica, 0):
            results.append(_ok(req_id, f"SOA scorporabile {s.categoria}", "qualification",
                               f"SOA {s.categoria} cl.{att.soa_class} ✓", evidence=ev))
        else:
            # Possibili soluzioni
            methods = []
            if bando.subappalto_percentuale_max and bando.subappalto_percentuale_max > 0:
                methods.append("subappalto")
            if bando.avvalimento_ammesso == "yes":
                methods.append("avvalimento")
            if bando.rti_ammesso == "yes":
                methods.append("rti")
            missing_note = f"SOA {s.categoria} cl.{s.classifica}"
            results.append(_ko(
                req_id, f"SOA scorporabile {s.categoria}", "qualification",
                Severity.HARD_KO,
                f"SOA {s.categoria} classifica {s.classifica} mancante o insufficiente.",
                fixable=bool(methods),
                methods=methods,
                gaps=[missing_note],
                evidence=ev
            ))
    return results

def eval_C5_validita(bando: BandoRequisiti, company: CompanyProfile) -> List[RequirementResult]:
    """C5 – Validità temporale SOA"""
    results = []
    # Prendi la deadline offerta
    deadline_offerta = None
    for sc in bando.scadenze:
        if "offerta" in sc.tipo.lower() or "presentazione" in sc.tipo.lower():
            deadline_offerta = _parse_date(sc.data) if sc.data else None
            break

    for att in company.soa_attestations:
        exp = _parse_date(att.expiry_date)
        if exp is None:
            results.append(_unknown(
                f"C5_{att.category}", f"Validità SOA {att.category}", "qualification",
                f"Data scadenza SOA {att.category} non leggibile: '{att.expiry_date}'"
            ))
        elif exp < _today():
            results.append(_ko(
                f"C5_{att.category}", f"SOA {att.category} scaduta", "qualification",
                Severity.HARD_KO,
                f"SOA {att.category} SCADUTA il {att.expiry_date}. Rinnovare immediatamente.",
                gaps=[f"Rinnovo SOA {att.category}"]
            ))
        elif deadline_offerta and exp < deadline_offerta:
            results.append(_ko(
                f"C5_{att.category}", f"SOA {att.category} scade prima dell'offerta", "qualification",
                Severity.HARD_KO,
                f"SOA {att.category} scade il {att.expiry_date}, PRIMA della scadenza offerta ({deadline_offerta.date()}). "
                "Avviare rinnovo.",
                gaps=[f"Rinnovo anticipato SOA {att.category}"]
            ))
        else:
            results.append(_ok(
                f"C5_{att.category}", f"Validità SOA {att.category}", "qualification",
                f"SOA {att.category} valida fino al {att.expiry_date}"
            ))
    return results


# ─────────────────────────────────────────────────────────
# Requisiti D — Certificazioni
# ─────────────────────────────────────────────────────────

def _find_cert(company: CompanyProfile, cert_type: str) -> Optional[Any]:
    for c in company.certifications:
        if cert_type.lower().replace(" ", "") in c.cert_type.lower().replace(" ", ""):
            return c
    return None

def eval_D_certificazioni(bando: BandoRequisiti, company: CompanyProfile) -> List[RequirementResult]:
    """D1-D4 – Certificazioni richieste"""
    results = []
    for i, cert_req in enumerate(bando.certificazioni_richieste):
        req_id = f"D{i+1}"
        found = _find_cert(company, cert_req)
        if not found:
            results.append(_ko(
                req_id, f"Certificazione {cert_req}", "certification",
                Severity.HARD_KO,
                f"{cert_req} NON posseduta. Verificare se ottenibile prima della scadenza.",
                gaps=[cert_req]
            ))
        else:
            exp = _parse_date(found.expiry_date) if found.expiry_date else None
            if exp and exp < _today():
                results.append(_ko(
                    req_id, f"Certificazione {cert_req}", "certification",
                    Severity.HARD_KO,
                    f"{cert_req} SCADUTA il {found.expiry_date}. Rinnovare subito.",
                    gaps=[f"Rinnovo {cert_req}"]
                ))
            else:
                results.append(_ok(
                    req_id, f"Certificazione {cert_req}", "certification",
                    f"{cert_req} presente e valida (scad. {found.expiry_date})"
                ))
    return results


# ─────────────────────────────────────────────────────────
# Requisiti E — Economico-finanziari
# ─────────────────────────────────────────────────────────

def eval_E1_fatturato(bando: BandoRequisiti, company: CompanyProfile) -> Optional[RequirementResult]:
    """E1 – Fatturato globale minimo"""
    req = bando.fatturato_minimo_richiesto
    if not req:
        return None
    recent = sorted(company.turnover_by_year, key=lambda x: x.year, reverse=True)[:3]
    if not recent:
        return _unknown("E1", "Fatturato globale minimo", "financial",
                        f"Soglia richiesta: {req:,.0f}€. Caricare dati fatturato nel profilo.")
    avg = sum(r.amount_eur for r in recent) / len(recent)
    if avg >= req:
        return _ok("E1", "Fatturato globale minimo", "financial",
                   f"Fatturato medio {avg:,.0f}€ ≥ soglia {req:,.0f}€ ✓")
    methods = []
    if bando.avvalimento_ammesso == "yes":
        methods.append("avvalimento")
    if bando.rti_ammesso == "yes":
        methods.append("rti")
    return _ko(
        "E1", "Fatturato globale minimo", "financial", Severity.HARD_KO,
        f"Fatturato medio {avg:,.0f}€ < soglia richiesta {req:,.0f}€",
        fixable=bool(methods), methods=methods,
        gaps=[f"Fatturato globale minimo {req:,.0f}€"]
    )

def eval_E2_fatturato_specifico(bando: BandoRequisiti, company: CompanyProfile) -> Optional[RequirementResult]:
    """E2 – Fatturato specifico settore"""
    req = bando.fatturato_specifico_richiesto
    if not req:
        return None
    recent = sorted(company.sector_turnover_by_year, key=lambda x: x.year, reverse=True)[:3]
    if not recent:
        return _unknown("E2", "Fatturato specifico settore", "financial",
                        f"Soglia settore richiesta: {req:,.0f}€. Caricare dati nel profilo.")
    avg = sum(r.amount_eur for r in recent) / len(recent)
    if avg >= req:
        return _ok("E2", "Fatturato specifico settore", "financial",
                   f"Fatturato settore medio {avg:,.0f}€ ≥ soglia {req:,.0f}€ ✓")
    methods = ["avvalimento"] if bando.avvalimento_ammesso == "yes" else []
    return _ko(
        "E2", "Fatturato specifico settore", "financial", Severity.HARD_KO,
        f"Fatturato settore medio {avg:,.0f}€ < soglia {req:,.0f}€",
        fixable=bool(methods), methods=methods,
        gaps=[f"Fatturato settore {req:,.0f}€"]
    )


# ─────────────────────────────────────────────────────────
# Requisiti G — Progettazione (appalto integrato)
# ─────────────────────────────────────────────────────────

def eval_G1_appalto_integrato(bando: BandoRequisiti, company: CompanyProfile) -> Optional[RequirementResult]:
    """G1 – Presenza progettazione richiesta"""
    if not bando.appalto_integrato:
        return None
    ev = _ev(quote=bando.appalto_integrato_evidence or "", section="Descrizione appalto")

    if company.has_inhouse_design:
        return _ok("G1", "Progettazione (appalto integrato)", "design",
                   "Capacità progettuale interna disponibile.", evidence=ev)

    if company.external_designers_available == "yes" and company.design_team:
        return _ok("G1", "Progettazione (appalto integrato)", "design",
                   f"Progettisti esterni disponibili: {len(company.design_team)} figure.", evidence=ev)

    if company.willing_rti or company.external_designers_available != "no":
        return _ko(
            "G1", "Progettazione (appalto integrato)", "design",
            Severity.HARD_KO,
            "Appalto integrato rilevato: necessari progettisti qualificati.",
            fixable=True,
            methods=["progettisti"],
            constraints=["Progettisti devono essere iscritti all'albo", "Indicazione nominativa richiesta"],
            gaps=["Gruppo di progettazione"],
            evidence=ev
        )

    return _ko(
        "G1", "Progettazione (appalto integrato)", "design",
        Severity.HARD_KO,
        "Appalto integrato: nessun progettista disponibile. KO non colmabile senza struttura.",
        evidence=ev
    )

def eval_G4_giovane_professionista(bando: BandoRequisiti, company: CompanyProfile) -> Optional[RequirementResult]:
    """G4 – Giovane professionista (se richiesto)"""
    if bando.giovane_professionista_richiesto != "yes":
        return None
    for d in company.design_team:
        if d.young_professional == "yes":
            return _ok("G4", "Giovane professionista", "design",
                       f"{d.name} soddisfa il requisito 'giovane professionista'.")
    return _ko(
        "G4", "Giovane professionista", "design", Severity.HARD_KO,
        "Bando richiede giovane professionista (abilitato da meno di 5 anni): nessuno disponibile.",
        fixable=True, methods=["progettisti"],
        gaps=["Giovane professionista abilitato"]
    )


# ─────────────────────────────────────────────────────────
# Requisiti H — Gate procedurali
# ─────────────────────────────────────────────────────────

def eval_H1_sopralluogo(bando: BandoRequisiti, company: CompanyProfile) -> Optional[RequirementResult]:
    """H1 – Sopralluogo obbligatorio"""
    if not bando.sopralluogo_obbligatorio:
        return None
    ev = _ev(quote=bando.sopralluogo_evidence or "", section="Modalità partecipazione")

    # Cerca deadline sopralluogo
    deadline_text = ""
    for sc in bando.scadenze:
        if "sopralluogo" in sc.tipo.lower():
            deadline_text = f" entro il {sc.data}" if sc.data else ""
            if sc.data:
                d = _parse_date(sc.data)
                if d and d < _today():
                    return _ko(
                        "H1", "Sopralluogo obbligatorio", "procedural",
                        Severity.HARD_KO,
                        f"Sopralluogo obbligatorio: SCADUTO il {sc.data}. Partecipazione IMPOSSIBILE.",
                        evidence=ev
                    )
            break

    return RequirementResult(
        req_id="H1", name="Sopralluogo obbligatorio", category="procedural",
        status=ReqStatus.UNKNOWN, severity=Severity.HARD_KO,
        evidence=[ev],
        user_message=(
            f"Sopralluogo OBBLIGATORIO a pena di esclusione{deadline_text}. "
            "Prenotare immediatamente e assicurarsi di ricevere attestato."
        )
    )

def eval_H4_anac(bando: BandoRequisiti, company: CompanyProfile) -> Optional[RequirementResult]:
    """H4 – Contributo ANAC"""
    if bando.anac_contributo_richiesto == "no":
        return None
    if bando.anac_contributo_richiesto == "unknown":
        return _unknown("H4", "Contributo ANAC", "procedural",
                        "Verificare se richiesto contributo ANAC e pagarlo prima della scadenza.")
    return RequirementResult(
        req_id="H4", name="Contributo ANAC", category="procedural",
        status=ReqStatus.UNKNOWN, severity=Severity.HARD_KO,
        user_message=(
            "Contributo ANAC richiesto. Pagare su FVOE prima della scadenza offerta. "
            "Mancato pagamento = esclusione."
        )
    )

def eval_H5_piattaforma(bando: BandoRequisiti, company: CompanyProfile) -> RequirementResult:
    """H5 – Piattaforma telematica"""
    piatt = bando.piattaforma_gara or "non specificata"
    lr = company.legal_representative
    if not lr.has_digital_signature:
        return _ko(
            "H5", f"Piattaforma {piatt}", "procedural",
            Severity.HARD_KO,
            f"Piattaforma: {piatt}. Firma digitale mancante: impossibile firmare documenti.",
            gaps=["Firma digitale CNS/CRS"]
        )
    return RequirementResult(
        req_id="H5", name=f"Piattaforma {piatt}", category="procedural",
        status=ReqStatus.UNKNOWN, severity=Severity.SOFT_RISK,
        user_message=f"Verificare registrazione su {piatt} e abilitazione alla gara specifica."
    )


# ─────────────────────────────────────────────────────────
# Requisiti I — Garanzie
# ─────────────────────────────────────────────────────────

def eval_I1_provvisoria(bando: BandoRequisiti, company: CompanyProfile) -> Optional[RequirementResult]:
    """I1/I2 – Cauzione provvisoria"""
    if bando.garanzie_richieste is None:
        return None
    g = bando.garanzie_richieste
    if g.provvisoria is None and g.percentuale_provvisoria is None:
        return None

    imp = g.provvisoria
    if imp is None and g.percentuale_provvisoria and bando.importo_lavori:
        imp = bando.importo_lavori * g.percentuale_provvisoria / 100

    msg = f"Cauzione provvisoria richiesta: {imp:,.0f}€" if imp else "Cauzione provvisoria richiesta"
    # Check riduzione ISO
    has_iso9001 = any(c.cert_type.upper().replace(" ", "") in ("ISO9001", "ISO 9001")
                      for c in company.certifications)
    if has_iso9001:
        msg += " (riduzione 50% per ISO 9001 applicabile)"

    return RequirementResult(
        req_id="I1", name="Cauzione provvisoria", category="guarantee",
        status=ReqStatus.UNKNOWN, severity=Severity.HARD_KO,
        user_message=msg + ". Attivare fideiussione presso istituto abilitato entro scadenza."
    )


# ─────────────────────────────────────────────────────────
# Requisiti K — Avvalimento
# ─────────────────────────────────────────────────────────

def eval_K_avvalimento(bando: BandoRequisiti) -> Optional[RequirementResult]:
    """K1-K3 – Regole avvalimento"""
    if bando.avvalimento_ammesso == "no":
        return RequirementResult(
            req_id="K1", name="Avvalimento", category="participation",
            status=ReqStatus.KO, severity=Severity.SOFT_RISK,
            user_message="Il bando ESCLUDE l'avvalimento. Non utilizzabile per colmare gap."
        )
    if bando.avvalimento_ammesso == "yes":
        return RequirementResult(
            req_id="K1", name="Avvalimento ammesso", category="participation",
            status=ReqStatus.OK, severity=Severity.SOFT_RISK,
            user_message=(
                f"Avvalimento ammesso. Regole: {bando.avvalimento_regole or 'verificare bando'}. "
                "Attenzione: ausiliaria NON può partecipare; contratto deve indicare risorse specifiche."
            )
        )
    return None


# ─────────────────────────────────────────────────────────
# Requisiti L — Subappalto
# ─────────────────────────────────────────────────────────

def eval_L1_subappalto(bando: BandoRequisiti) -> Optional[RequirementResult]:
    """L1 – Limiti subappalto"""
    pct = bando.subappalto_percentuale_max
    if pct is None:
        return None
    return RequirementResult(
        req_id="L1", name="Limite subappalto", category="participation",
        status=ReqStatus.OK, severity=Severity.SOFT_RISK,
        user_message=(
            f"Subappalto max {pct:.0f}%. "
            f"Regole: {bando.subappalto_regole or 'verificare capitolato'}. "
            "Verificare che la prevalente non venga subappaltata in misura prevalente."
        )
    )


# ─────────────────────────────────────────────────────────
# Requisiti M — Vincoli esecutivi
# ─────────────────────────────────────────────────────────

def eval_M1_inizio_lavori(bando: BandoRequisiti, company: CompanyProfile) -> Optional[RequirementResult]:
    """M1 – Inizio lavori tassativo"""
    if not bando.start_lavori_tassativo:
        return None
    d = _parse_date(bando.start_lavori_tassativo)
    giorni = (d - _today()).days if d else None
    msg = f"Inizio lavori tassativo entro {bando.start_lavori_tassativo}"
    if giorni is not None:
        msg += f" (tra {giorni} giorni)"
    if company.start_date_constraints:
        msg += f". Vincoli azienda: {company.start_date_constraints}"

    return RequirementResult(
        req_id="M1", name="Inizio lavori tassativo", category="operational",
        status=ReqStatus.UNKNOWN, severity=Severity.SOFT_RISK,
        user_message=msg + ". Valutare disponibilità risorse e cantiere."
    )

def eval_M_vincoli(bando: BandoRequisiti) -> List[RequirementResult]:
    """M2+ – Vincoli esecutivi generici"""
    results = []
    for i, v in enumerate(bando.vincoli_esecutivi):
        results.append(RequirementResult(
            req_id=f"M{i+2}", name="Vincolo esecutivo", category="operational",
            status=ReqStatus.UNKNOWN, severity=Severity.SOFT_RISK,
            user_message=v
        ))
    return results


# ══════════════════════════════════════════════════════════
# ENTRY POINT: Valuta tutti i requisiti
# ══════════════════════════════════════════════════════════

def evaluate_all(bando: BandoRequisiti, company: CompanyProfile,
                 participation_forms: Any = None) -> List[RequirementResult]:
    """
    Esegue la valutazione completa di tutti i requisiti atomici
    e restituisce la lista di RequirementResult.
    """
    results: List[RequirementResult] = []

    # A — Generali (sempre presenti come UNKNOWN/flag)
    results.extend([eval_A1(bando, company), eval_A2(bando, company), eval_A5(bando, company)])

    # B — Idoneità
    results.append(eval_B1(bando, company))
    results.append(eval_B4(bando, company))

    # C — SOA
    c1 = eval_C1_prevalente(bando, company, participation_forms)
    results.append(c1)
    results.extend(eval_C2_scorporabili(bando, company))
    results.extend(eval_C5_validita(bando, company))

    # D — Certificazioni
    results.extend(eval_D_certificazioni(bando, company))

    # E — Economico-finanziari
    for e in [eval_E1_fatturato(bando, company), eval_E2_fatturato_specifico(bando, company)]:
        if e:
            results.append(e)

    # G — Progettazione
    for g in [eval_G1_appalto_integrato(bando, company), eval_G4_giovane_professionista(bando, company)]:
        if g:
            results.append(g)

    # H — Gate procedurali
    for h in [eval_H1_sopralluogo(bando, company), eval_H4_anac(bando, company)]:
        if h:
            results.append(h)
    results.append(eval_H5_piattaforma(bando, company))

    # I — Garanzie
    i1 = eval_I1_provvisoria(bando, company)
    if i1:
        results.append(i1)

    # K — Avvalimento
    k1 = eval_K_avvalimento(bando)
    if k1:
        results.append(k1)

    # L — Subappalto
    l1 = eval_L1_subappalto(bando)
    if l1:
        results.append(l1)

    # M — Operativi
    m1 = eval_M1_inizio_lavori(bando, company)
    if m1:
        results.append(m1)
    results.extend(eval_M_vincoli(bando))

    # Filtra None
    return [r for r in results if r is not None]