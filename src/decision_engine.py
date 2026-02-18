"""
BidPilot v4.0 — Decision Engine
PATCH: aggiornato per schemas.py v4.1
- Verdict usa stage_outputs_json (str JSON) invece di stage_outputs (Dict)
- Resto invariato
"""
from __future__ import annotations
import json
from datetime import datetime
from typing import List, Optional, Dict

from src.schemas import (
    BandoRequisiti, CompanyProfile, DecisionReport, Verdict,
    VerdictStatus, RequirementResult, ReqStatus, Severity,
    TopReason, ActionPlan, ActionStep, Evidence,
    ProceduralCheckItem, DocumentChecklist, DocChecklistItem,
    Risk, Uncertainty, AuditEntry
)
from src.requirements_engine import evaluate_all


# ════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════

def _ev(quote: str = "", page: int = 0, section: str = "") -> Evidence:
    return Evidence(quote=quote, page=page, section=section)

def _days_left(date_str: Optional[str]) -> Optional[int]:
    if not date_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            d = datetime.strptime(date_str[:10], fmt[:10])
            return (d - datetime.now()).days
        except Exception:
            pass
    return None


# ════════════════════════════════════════════════════════
# Verdetto
# ════════════════════════════════════════════════════════

def _compute_profile_confidence(results: List[RequirementResult]) -> float:
    hard_results = [r for r in results if r.severity == Severity.HARD_KO]
    if not hard_results:
        return 1.0
    return min(r.confidence for r in hard_results)


def _compute_verdict(results: List[RequirementResult], bando: BandoRequisiti) -> Verdict:
    profile_conf = _compute_profile_confidence(results)

    # Engine qualificazione (D11)
    if bando.is_qualification_system:
        hard_ko_qual = [r for r in results
                        if r.severity == Severity.HARD_KO
                        and r.status == ReqStatus.KO
                        and r.confidence >= 0.7]
        if hard_ko_qual:
            return Verdict(
                status=VerdictStatus.NOT_ELIGIBLE_QUALIFICATION,
                legal_eligibility="not_eligible",
                operational_feasibility="not_feasible",
                summary="Sistema di Qualificazione: requisiti bloccanti non soddisfatti.",
                profile_confidence=profile_conf
            )
        return Verdict(
            status=VerdictStatus.ELIGIBLE_QUALIFICATION,
            legal_eligibility="eligible",
            operational_feasibility="feasible",
            summary="Sistema di Qualificazione: requisiti soddisfatti.",
            profile_confidence=profile_conf
        )

    # Engine PPP multi-stage (D21)
    if bando.procedure_multi_stage:
        stage1_ko = [r for r in results
                     if r.severity == Severity.HARD_KO
                     and r.status == ReqStatus.KO
                     and r.confidence >= 0.7
                     and r.category in ("qualification", "general", "procedural")]
        stage1_status = "NOT_ELIGIBLE" if stage1_ko else "ELIGIBLE"
        stage3_ko = [r for r in results
                     if r.req_id in ("D22",) and r.status in (ReqStatus.KO, ReqStatus.UNKNOWN)]
        stage3_risk = "HIGH" if stage3_ko else "MEDIUM"
        # FIX: stage_outputs_json invece di stage_outputs dict
        so_json = json.dumps({
            "stage1_admission": stage1_status,
            "stage2_risk": "MEDIUM (risorse per dialogo)",
            "stage3_financial_risk": stage3_risk,
        })
        return Verdict(
            status=VerdictStatus.ELIGIBLE_STAGE1,
            legal_eligibility="uncertain",
            operational_feasibility="risky",
            summary=f"PPP Multi-stage: Stage 1 = {stage1_status}. Stage 3 rischio {stage3_risk}.",
            stage_outputs_json=so_json,
            profile_confidence=profile_conf
        )

    # Engine gara ordinaria
    active_results = [r for r in results if r.status != ReqStatus.PREMIANTE]

    hard_ko_definitive = [r for r in active_results
                          if r.severity == Severity.HARD_KO
                          and r.status == ReqStatus.KO
                          and r.confidence == 1.0]
    if hard_ko_definitive:
        return Verdict(
            status=VerdictStatus.NO_GO,
            legal_eligibility="not_eligible",
            operational_feasibility="not_feasible",
            summary=f"{len(hard_ko_definitive)} requisito/i HARD KO non sanabile/i: "
                    + "; ".join(r.name for r in hard_ko_definitive[:3]),
            profile_confidence=profile_conf
        )

    hard_ko_ambiguous = [r for r in active_results
                         if r.severity == Severity.HARD_KO
                         and r.status == ReqStatus.KO
                         and r.confidence == 0.7]

    hard_ko_fixable = [r for r in active_results
                       if r.severity == Severity.HARD_KO
                       and r.status == ReqStatus.FIXABLE]

    if hard_ko_fixable and not hard_ko_ambiguous:
        return Verdict(
            status=VerdictStatus.GO_WITH_STRUCTURE,
            legal_eligibility="uncertain",
            operational_feasibility="feasible",
            summary=f"{len(hard_ko_fixable)} gap colmabile/i con struttura: "
                    + "; ".join(r.name for r in hard_ko_fixable[:3]),
            profile_confidence=profile_conf
        )

    unknown_hard = [r for r in active_results
                    if r.severity == Severity.HARD_KO and r.status == ReqStatus.UNKNOWN]
    soft_issues = [r for r in active_results
                   if r.severity == Severity.SOFT_RISK
                   and r.status in (ReqStatus.KO, ReqStatus.FIXABLE, ReqStatus.UNKNOWN)]

    if hard_ko_ambiguous or hard_ko_fixable or unknown_hard or soft_issues:
        n_issues = len(hard_ko_ambiguous) + len(hard_ko_fixable) + len(unknown_hard) + len(soft_issues)
        return Verdict(
            status=VerdictStatus.GO_HIGH_RISK,
            legal_eligibility="eligible" if not hard_ko_ambiguous else "uncertain",
            operational_feasibility="risky",
            summary=f"Formalmente ammissibile con {n_issues} punto/i da verificare o risolvere.",
            profile_confidence=profile_conf
        )

    return Verdict(
        status=VerdictStatus.GO,
        legal_eligibility="eligible",
        operational_feasibility="feasible",
        summary="Tutti i requisiti verificati. Nessun blocco rilevato.",
        profile_confidence=profile_conf
    )


# ════════════════════════════════════════════════════════
# Top Reasons
# ════════════════════════════════════════════════════════

def _build_top_reasons(results: List[RequirementResult]) -> List[TopReason]:
    priority = [
        (Severity.HARD_KO, ReqStatus.KO),
        (Severity.HARD_KO, ReqStatus.FIXABLE),
        (Severity.HARD_KO, ReqStatus.UNKNOWN),
        (Severity.SOFT_RISK, ReqStatus.KO),
        (Severity.SOFT_RISK, ReqStatus.UNKNOWN),
    ]
    selected = []
    for sev, status in priority:
        for r in results:
            if r.status == ReqStatus.PREMIANTE:
                continue
            if r.severity == sev and r.status == status and r not in selected:
                selected.append(r)
            if len(selected) >= 3:
                break
        if len(selected) >= 3:
            break
    return [
        TopReason(
            issue_type=r.req_id, severity=r.severity,
            message=r.user_message,
            evidence=r.evidence[0] if r.evidence else None,
            can_be_fixed=r.fixability.is_fixable,
            fix_options=r.fixability.allowed_methods
        )
        for r in selected
    ]


# ════════════════════════════════════════════════════════
# Action Plan
# ════════════════════════════════════════════════════════

def _build_action_plan(results: List[RequirementResult],
                       bando: BandoRequisiti,
                       company: CompanyProfile) -> ActionPlan:
    fixable = [r for r in results if r.status == ReqStatus.FIXABLE]
    if not fixable:
        return ActionPlan(recommended_path="none", steps=[])

    all_methods: Dict[str, int] = {}
    for r in fixable:
        for m in r.fixability.allowed_methods:
            base = m.split(" ")[0]
            all_methods[base] = all_methods.get(base, 0) + 1
    if not all_methods:
        return ActionPlan(recommended_path="none", steps=[])
    recommended = max(all_methods, key=all_methods.get)

    steps: List[ActionStep] = []
    step_num = 1

    if recommended == "avvalimento":
        steps.append(ActionStep(
            step=step_num, title="Seleziona impresa ausiliaria qualificata",
            why="Copre il/i requisito/i mancante/i tramite avvalimento.",
            inputs_needed=[
                "Ausiliaria con SOA/requisiti richiesti validi",
                "Verificare che ausiliaria non partecipi alla stessa gara",
            ],
            risks=[
                "Requisiti non frazionabili: o hai il 100% o KO",
                f"Regole specifiche: {bando.avvalimento_regole or 'verificare'}"
            ]
        ))
        step_num += 1
        steps.append(ActionStep(
            step=step_num, title="Redigi contratto di avvalimento specifico",
            why="Il contratto deve indicare esplicitamente risorse, mezzi e personale.",
            inputs_needed=["Elenco specifico risorse/mezzi/personale", "Clausola responsabilità solidale"],
            risks=["Contratto 'vuoto' → nullità → esclusione"]
        ))
        step_num += 1

    elif recommended == "rti":
        q_mand = bando.rti_mandataria_quota_min
        steps.append(ActionStep(
            step=step_num, title="Costituisci RTI con impresa qualificata",
            why="Il raggruppamento copre i requisiti mancanti.",
            inputs_needed=[
                f"Mandataria: ≥{q_mand or '?'}% requisiti (SOA prevalente)",
                "Mandanti: coprono scorporabili e requisiti secondari",
            ],
            risks=[f"Quote mandataria: {bando.rti_regole or 'verificare disciplinare'}"]
        ))
        step_num += 1

    elif recommended == "progettisti":
        steps.append(ActionStep(
            step=step_num, title="Individua e formalizza gruppo di progettazione",
            why="Appalto integrato: progettisti obbligatori nell'offerta.",
            inputs_needed=["Professionisti iscritti agli albi", "Dichiarazioni di disponibilità firmate"],
            risks=["Mancanza iscrizione albo → esclusione"]
        ))
        step_num += 1

    elif recommended in ("subappalto", "subappalto_qualificante"):
        pct = bando.subappalto_percentuale_max or 30
        steps.append(ActionStep(
            step=step_num, title="Pianifica subappalto qualificante",
            why="Le lavorazioni scorporabili mancanti coperte tramite subappalto.",
            inputs_needed=[
                f"Subappaltatore con SOA richiesta",
                f"Quota subappaltata ≤ {pct:.0f}% importo totale",
            ],
            risks=["Divieto cascata (R34)", "Dichiarazione esplicita in DGUE"]
        ))
        step_num += 1

    steps.append(ActionStep(
        step=step_num, title="Prepara documentazione struttura prescelta",
        why="Ogni struttura richiede documenti nell'envelope amministrativo.",
        inputs_needed=["DGUE di tutti i soggetti", "Dichiarazioni art.94-98 di tutti"],
        risks=["Documentazione incompleta → soccorso istruttorio o esclusione"]
    ))
    return ActionPlan(recommended_path=recommended, steps=steps)


# ════════════════════════════════════════════════════════
# Procedural Checklist
# ════════════════════════════════════════════════════════

def _build_procedural_checklist(bando: BandoRequisiti) -> List[ProceduralCheckItem]:
    items = []
    for sc in bando.scadenze:
        tipo_low = sc.tipo.lower()
        if "sopralluogo" in tipo_low:
            past = _days_left(sc.data)
            items.append(ProceduralCheckItem(
                item="Sopralluogo obbligatorio",
                deadline=sc.data,
                status="NOT_POSSIBLE" if (past is not None and past < 0) else "PENDING",
                impact="HARD_KO",
                evidence=_ev(quote=bando.sopralluogo_evidence or "", section="Sopralluogo")
            ))
        elif "offerta" in tipo_low or "presentazione" in tipo_low:
            items.append(ProceduralCheckItem(
                item="Scadenza presentazione offerta", deadline=sc.data,
                status="PENDING", impact="HARD_KO"
            ))
        elif "quesiti" in tipo_low or "chiarimenti" in tipo_low:
            items.append(ProceduralCheckItem(
                item="Deadline quesiti/chiarimenti", deadline=sc.data,
                status="PENDING", impact="INFO"
            ))
    if bando.anac_contributo_richiesto == "yes":
        items.append(ProceduralCheckItem(
            item="Pagamento contributo ANAC (FVOE/pagoPA)", status="PENDING", impact="HARD_KO"
        ))
    if bando.fvoe_required:
        items.append(ProceduralCheckItem(
            item="Completamento fascicolo FVOE", status="UNKNOWN", impact="SOFT_RISK"
        ))
    if bando.piattaforma_gara:
        items.append(ProceduralCheckItem(
            item=f"Registrazione/abilitazione su {bando.piattaforma_gara}",
            status="UNKNOWN", impact="HARD_KO"
        ))
    items.append(ProceduralCheckItem(
        item="Verifica firma digitale valida (CNS/CRS)", status="PENDING", impact="HARD_KO"
    ))
    if bando.dgue_required:
        items.append(ProceduralCheckItem(
            item="Compilazione DGUE (tutte le sezioni obbligatorie)", status="PENDING", impact="HARD_KO"
        ))
    if bando.pnrr_dnsh_required:
        items.append(ProceduralCheckItem(
            item="Dichiarazione DNSH + checklist PNRR", status="PENDING", impact="HARD_KO"
        ))
    if bando.is_qualification_system:
        items.append(ProceduralCheckItem(
            item="Invio domanda di qualificazione (prima della scadenza)",
            status="PENDING", impact="HARD_KO"
        ))
        if bando.qualification_fee_required:
            items.append(ProceduralCheckItem(
                item="Versamento rimborso spese qualificazione", status="PENDING", impact="HARD_KO"
            ))
    return items


# ════════════════════════════════════════════════════════
# Document Checklist
# ════════════════════════════════════════════════════════

def _build_document_checklist(bando: BandoRequisiti, company: CompanyProfile) -> DocumentChecklist:
    admin = [
        DocChecklistItem(name="DGUE compilato (tutti i soggetti)", notes="Uno per ogni soggetto del raggruppamento"),
        DocChecklistItem(name="Dichiarazioni art.94-98 d.lgs.36/2023"),
        DocChecklistItem(name="Visura camerale / autocertificazione CCIAA"),
    ]
    if bando.sopralluogo_obbligatorio:
        admin.append(DocChecklistItem(name="Attestato sopralluogo", mandatory=True, notes="Pena esclusione"))
    if bando.anac_contributo_richiesto == "yes":
        admin.append(DocChecklistItem(name="Ricevuta pagamento contributo ANAC"))
    if bando.patto_integrita_required:
        admin.append(DocChecklistItem(name="Patto integrità firmato",
                                      mandatory=bando.patto_integrita_pena_esclusione))
    if bando.protocollo_legalita_required:
        admin.append(DocChecklistItem(name="Protocollo legalità firmato"))
    if bando.is_qualification_system:
        admin.append(DocChecklistItem(name="Domanda di qualificazione (modello committente)"))

    technical = [
        DocChecklistItem(name="Copia attestato/i SOA (tutte le categorie richieste)"),
        DocChecklistItem(name="Certificazioni di qualità (ISO 9001/14001/45001 ecc.)"),
    ]
    if bando.soa_copy_required_pena_esclusione:
        technical[0] = DocChecklistItem(name="Copia attestato SOA",
                                         mandatory=True, notes="PENA DI ESCLUSIONE")
    if bando.appalto_integrato:
        technical.append(DocChecklistItem(name="Elenco nominativo progettisti + CV + iscrizione albo",
                                           notes="Obbligatorio per appalto integrato"))
    if bando.giovane_professionista_richiesto == "yes":
        technical.append(DocChecklistItem(name="Dichiarazione giovane professionista",
                                           mandatory=True, notes="Data abilitazione esplicita"))
    if bando.bim_ogi_required:
        technical.append(DocChecklistItem(name="OGI (Offerta Gestione Informativa BIM)",
                                           mandatory=True))
    if bando.credit_license and bando.credit_license.required:
        technical.append(DocChecklistItem(name="Patente a crediti",
                                           mandatory=bando.credit_license.pena_esclusione))
    if bando.cultural_works_dm154_required:
        technical.append(DocChecklistItem(name="Qualificazione DM 154/2017 beni culturali",
                                           mandatory=bando.cultural_works_dm154_pena_esclusione))

    economic = [DocChecklistItem(name="Offerta economica (modello bando)", mandatory=True)]
    if bando.labour_costs_must_indicate:
        economic.append(DocChecklistItem(name="Costi manodopera indicati in offerta economica",
                                          mandatory=bando.labour_costs_pena_esclusione))
    if bando.safety_company_costs_must_indicate:
        economic.append(DocChecklistItem(name="Oneri sicurezza aziendali indicati",
                                          mandatory=bando.safety_costs_pena_esclusione))
    if bando.criteri_valutazione:
        economic.append(DocChecklistItem(
            name=f"Relazione tecnica OEPV ({len(bando.criteri_valutazione)} criteri)", mandatory=True))

    from src.schemas import _Base
    has_iso9001 = False
    try:
        from src.requirements_engine import _cert_match
        has_iso9001 = any(_cert_match("ISO 9001", c.cert_type) for c in company.certifications)
    except Exception:
        pass
    prov_note = "Verifica riduzione 50% per ISO 9001" if has_iso9001 else "Verifica riduzioni MPMI"
    guarantees = [
        DocChecklistItem(name="Cauzione provvisoria (fideiussione bancaria/assicurativa)",
                          mandatory=bando.garanzie_richieste is not None,
                          notes=prov_note),
        DocChecklistItem(name="Impegno fideiussore per definitiva"),
    ]
    for pol in bando.polizze_richieste:
        guarantees.append(DocChecklistItem(name=f"Polizza {pol}", mandatory=False))

    platform = [
        DocChecklistItem(name=f"Upload su {bando.piattaforma_gara or 'piattaforma gara'}",
                          notes="Rispettare formati e dimensioni"),
        DocChecklistItem(name="Firma digitale su ogni documento"),
    ]
    if bando.pnrr_dnsh_required:
        platform.append(DocChecklistItem(name="Dichiarazione DNSH + checklist allegata", mandatory=True))

    return DocumentChecklist(
        administrative=admin, technical=technical, economic=economic,
        guarantees=guarantees, platform=platform
    )


# ════════════════════════════════════════════════════════
# Risk Register
# ════════════════════════════════════════════════════════

def _build_risk_register(bando: BandoRequisiti, results: List[RequirementResult]) -> List[Risk]:
    risks = []

    for r in results:
        if "C5_" in r.req_id and r.status == ReqStatus.KO:
            risks.append(Risk(risk_id=r.req_id, risk_type="soa_expiry", level="HIGH",
                              message=r.user_message,
                              mitigations=["Avviare rinnovo SOA immediatamente"]))

    if bando.start_lavori_tassativo:
        risks.append(Risk(risk_id="M1", risk_type="start_date", level="HIGH",
                          message=f"Inizio lavori tassativo: {bando.start_lavori_tassativo}",
                          mitigations=["Pianificare forniture e risorse in anticipo"]))

    for sc in bando.scadenze:
        if sc.data:
            gg = _days_left(sc.data)
            if gg is not None and 0 <= gg <= 7:
                risks.append(Risk(risk_id=f"H_deadline_{sc.tipo}",
                                  risk_type="deadline_critical", level="HIGH",
                                  message=f"Scadenza critica: {sc.tipo} entro {gg} giorni ({sc.data})",
                                  mitigations=["Agire entro oggi"]))

    for v in bando.vincoli_esecutivi:
        lv = v.lower()
        level = "HIGH" if any(k in lv for k in ["scuola", "ospedale", "occupato", "tassativo"]) else "MEDIUM"
        risks.append(Risk(risk_id="M_exec", risk_type="execution_constraint",
                          level=level, message=v,
                          mitigations=["Pianificare fasi e turni"]))

    if bando.is_pnrr and bando.pnrr_dnsh_required:
        risks.append(Risk(risk_id="PNRR_DNSH", risk_type="pnrr_compliance", level="HIGH",
                          message="DNSH obbligatorio in gara PNRR: mancanza = KO.",
                          mitigations=["Compilare checklist DNSH", "Allegare dichiarazione d'impegno"]))

    if bando.lots_max_awardable_per_bidder and bando.lotti > 1:
        risks.append(Risk(risk_id="D09_lotti", risk_type="strategy", level="MEDIUM",
                          message=f"Gara multi-lotto ({bando.lotti}): max {bando.lots_max_awardable_per_bidder} aggiudicabili.",
                          mitigations=["Scegliere il lotto target strategico"]))

    if bando.is_qualification_system and bando.qualification_expiry_date:
        gg = _days_left(bando.qualification_expiry_date)
        if gg is not None and gg < 180:
            risks.append(Risk(risk_id="D15_rinnovo", risk_type="qualification_expiry", level="HIGH",
                              message=f"Qualificazione scade {bando.qualification_expiry_date} (tra ~{gg//30} mesi).",
                              mitigations=[f"Inviare domanda rinnovo almeno {bando.maintenance_submit_months_before} mesi prima"]))

    return risks


# ════════════════════════════════════════════════════════
# Uncertainties
# ════════════════════════════════════════════════════════

def _build_uncertainties(results: List[RequirementResult], bando: BandoRequisiti) -> List[Uncertainty]:
    questions = []
    for r in results:
        if r.status == ReqStatus.UNKNOWN and r.severity == Severity.HARD_KO:
            questions.append(Uncertainty(
                question=f"[{r.req_id}] {r.user_message[:120]}",
                why_needed=f"Blocca il verdetto (HARD KO): {r.name}",
                blocks_verdict=True
            ))
    if bando.sopralluogo_obbligatorio:
        questions.append(Uncertainty(
            question="Hai già prenotato/effettuato il sopralluogo? (attestato da allegare)",
            why_needed="Sopralluogo obbligatorio a pena di esclusione",
            blocks_verdict=True
        ))
    if bando.anac_contributo_richiesto == "unknown" and bando.codice_cig:
        questions.append(Uncertainty(
            question="Il bando richiede pagamento contributo ANAC? Verificare articolo dedicato.",
            why_needed="Mancato pagamento = esclusione",
            blocks_verdict=True
        ))
    return questions[:8]


# ════════════════════════════════════════════════════════
# ENTRY POINT PRINCIPALE
# ════════════════════════════════════════════════════════

def produce_decision_report(bando: BandoRequisiti, company: CompanyProfile) -> DecisionReport:
    audit: List[AuditEntry] = []

    if bando.is_qualification_system:
        engine_mode = "qualificazione"
    elif bando.procedure_multi_stage:
        engine_mode = "ppp_multistage"
    else:
        engine_mode = "gara"

    results = evaluate_all(bando, company)
    audit.append(AuditEntry(
        event="EVALUATE_ALL_REQUIREMENTS",
        result=f"{len(results)} requisiti valutati — engine: {engine_mode}",
        confidence=1.0
    ))

    profile_conf = min((r.confidence for r in results if r.severity == Severity.HARD_KO), default=1.0)
    audit.append(AuditEntry(
        event="PROFILE_CONFIDENCE",
        result=f"Confidence aggregata: {profile_conf:.1f}",
        confidence=profile_conf
    ))

    verdict = _compute_verdict(results, bando)
    audit.append(AuditEntry(
        event="COMPUTE_VERDICT",
        result=f"Verdetto: {verdict.status} | Conf: {profile_conf:.1f}",
        confidence=profile_conf
    ))

    top_reasons = _build_top_reasons(results)
    action_plan = _build_action_plan(results, bando, company)
    audit.append(AuditEntry(
        event="BUILD_ACTION_PLAN",
        result=f"Percorso: {action_plan.recommended_path}, {len(action_plan.steps)} passi",
        confidence=1.0
    ))

    proc_checklist = _build_procedural_checklist(bando)
    doc_checklist = _build_document_checklist(bando, company)
    risk_register = _build_risk_register(bando, results)
    uncertainties = _build_uncertainties(results, bando)

    return DecisionReport(
        verdict=verdict,
        top_reasons=top_reasons,
        requirements_results=results,
        action_plan=action_plan,
        procedural_checklist=proc_checklist,
        document_checklist=doc_checklist,
        risk_register=risk_register,
        uncertainties=uncertainties,
        audit_trace=audit,
        generated_at=datetime.utcnow().isoformat() + "Z",
        engine_mode=engine_mode
    )