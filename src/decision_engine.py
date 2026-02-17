"""
BidPilot v3.0 — Decision Engine
Produce il DecisionReport finale: verdetto a 4 stati, action plan, checklist, risk register.
"""
from __future__ import annotations
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


# ═══════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════

def _ev(quote: str = "", page: int = 0, section: str = "") -> Evidence:
    return Evidence(quote=quote, page=page, section=section)


def _days_left(date_str: Optional[str]) -> Optional[int]:
    if not date_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            d = datetime.strptime(date_str[:16], fmt[:len(date_str)])
            return (d - datetime.now()).days
        except Exception:
            pass
    return None


# ═══════════════════════════════════════════════════════
# Verdetto
# ═══════════════════════════════════════════════════════

def _compute_verdict(results: List[RequirementResult]) -> Verdict:
    """
    Regola deterministica di verdetto:
    1. HARD_KO non fixable → NO_GO (non eligible)
    2. HARD_KO tutti fixable → GO_WITH_STRUCTURE (uncertain)
    3. Solo SOFT_RISK/INFO → GO_HIGH_RISK o GO

    Priorità di analisi:
      gate procedurali → SOA → progettazione → requisiti speciali → rischi operativi
    """
    hard_ko_not_fixable = [
        r for r in results
        if r.severity == Severity.HARD_KO
        and r.status == ReqStatus.KO
    ]
    hard_ko_fixable = [
        r for r in results
        if r.severity == Severity.HARD_KO
        and r.status == ReqStatus.FIXABLE
    ]
    soft_risks = [
        r for r in results
        if r.severity == Severity.SOFT_RISK
        and r.status in (ReqStatus.KO, ReqStatus.FIXABLE, ReqStatus.UNKNOWN)
    ]
    operational_risks = [
        r for r in results
        if r.category == "operational"
        and r.status == ReqStatus.UNKNOWN
    ]

    if hard_ko_not_fixable:
        return Verdict(
            status=VerdictStatus.NO_GO,
            legal_eligibility="not_eligible",
            operational_feasibility="not_feasible",
            summary=(
                f"{len(hard_ko_not_fixable)} requisito/i HARD KO non sanabile/i: "
                + "; ".join(r.name for r in hard_ko_not_fixable[:3])
            )
        )

    if hard_ko_fixable:
        return Verdict(
            status=VerdictStatus.GO_WITH_STRUCTURE,
            legal_eligibility="uncertain",
            operational_feasibility="risky" if operational_risks else "feasible",
            summary=(
                f"{len(hard_ko_fixable)} gap colmabile/i con struttura (RTI/avvalimento/progettisti): "
                + "; ".join(r.name for r in hard_ko_fixable[:3])
            )
        )

    if soft_risks or operational_risks:
        return Verdict(
            status=VerdictStatus.GO_HIGH_RISK,
            legal_eligibility="eligible",
            operational_feasibility="risky",
            summary=(
                f"Formalmente ammissibile ma con {len(soft_risks + operational_risks)} "
                "rischio/i da gestire."
            )
        )

    return Verdict(
        status=VerdictStatus.GO,
        legal_eligibility="eligible",
        operational_feasibility="feasible",
        summary="Tutti i requisiti verificati. Nessun blocco rilevato."
    )


# ═══════════════════════════════════════════════════════
# Top Reasons
# ═══════════════════════════════════════════════════════

def _build_top_reasons(results: List[RequirementResult]) -> List[TopReason]:
    """Estrai le 3 ragioni più rilevanti per l'utente"""
    # Priorità: HARD_KO KO → HARD_KO FIXABLE → SOFT_RISK
    priority_order = [
        (Severity.HARD_KO, ReqStatus.KO),
        (Severity.HARD_KO, ReqStatus.FIXABLE),
        (Severity.SOFT_RISK, ReqStatus.KO),
        (Severity.SOFT_RISK, ReqStatus.FIXABLE),
        (Severity.SOFT_RISK, ReqStatus.UNKNOWN),
    ]
    selected = []
    for sev, status in priority_order:
        for r in results:
            if r.severity == sev and r.status == status and r not in selected:
                selected.append(r)
            if len(selected) >= 3:
                break
        if len(selected) >= 3:
            break

    reasons = []
    for r in selected:
        reasons.append(TopReason(
            issue_type=r.req_id,
            severity=r.severity,
            message=r.user_message,
            evidence=r.evidence[0] if r.evidence else None,
            can_be_fixed=r.fixability.is_fixable,
            fix_options=r.fixability.allowed_methods
        ))
    return reasons


# ═══════════════════════════════════════════════════════
# Action Plan
# ═══════════════════════════════════════════════════════

def _build_action_plan(results: List[RequirementResult],
                       bando: BandoRequisiti,
                       company: CompanyProfile) -> ActionPlan:
    """Costruisce il piano d'azione in base ai gap rilevati"""
    fixable = [r for r in results if r.status == ReqStatus.FIXABLE]
    if not fixable:
        return ActionPlan(recommended_path="none", steps=[])

    # Scegli il percorso principale
    all_methods: Dict[str, int] = {}
    for r in fixable:
        for m in r.fixability.allowed_methods:
            all_methods[m] = all_methods.get(m, 0) + 1

    if not all_methods:
        return ActionPlan(recommended_path="none", steps=[])

    # Percorso più frequente
    recommended = max(all_methods, key=all_methods.get)

    steps: List[ActionStep] = []
    step_num = 1

    if recommended == "avvalimento":
        steps.append(ActionStep(
            step=step_num, title="Seleziona impresa ausiliaria",
            why="Copre il/i requisito/i mancante/i tramite avvalimento.",
            inputs_needed=[
                "Impresa ausiliaria con SOA/requisiti richiesti validi",
                "Verifica che l'ausiliaria non partecipi alla stessa gara",
                "Verifica che non sia già ausiliaria di altro concorrente"
            ],
            risks=[
                "Nullità del contratto se privo di indicazione risorse/mezzi",
                "Responsabilità solidale ausiliaria per esecuzione"
            ]
        ))
        step_num += 1
        steps.append(ActionStep(
            step=step_num, title="Redigi contratto di avvalimento",
            why="Il contratto deve indicare esplicitamente risorse, mezzi e personale messi a disposizione.",
            inputs_needed=[
                "Elenco specifico risorse/mezzi/personale (non generico)",
                "Durata corrispondente all'intera esecuzione contratto",
                "Clausola responsabilità solidale"
            ],
            risks=[
                "Contratto 'vuoto' → nullità → esclusione",
                f"Regole specifiche bando: {bando.avvalimento_regole or 'verificare'}"
            ]
        ))
        step_num += 1

    elif recommended == "rti":
        steps.append(ActionStep(
            step=step_num, title="Costituisci RTI con impresa qualificata",
            why="Il raggruppamento copre i requisiti mancanti del singolo.",
            inputs_needed=[
                "Mandataria: individua impresa con requisiti prevalente",
                "Mandante/i: coprono scorporabili e requisiti secondari",
                "Quote di esecuzione coerenti con qualificazioni"
            ],
            risks=[
                "Quote mandataria devono rispettare minimi bando",
                f"Regole RTI bando: {bando.rti_regole or 'verificare'}",
                "Firma mandato di rappresentanza prima della scadenza"
            ]
        ))
        step_num += 1
        steps.append(ActionStep(
            step=step_num, title="Definisci quote e mandato RTI",
            why="Le quote di esecuzione devono corrispondere alle qualificazioni possedute.",
            inputs_needed=[
                "Proposta quote (mandataria X%, mandante Y%)",
                "Verifica che mandataria copra categoria prevalente",
                "Atto di mandato collettivo speciale con rappresentanza"
            ],
            risks=["Quote non conformi → esclusione RTI"]
        ))
        step_num += 1

    elif recommended == "progettisti":
        steps.append(ActionStep(
            step=step_num, title="Individua e formalizza gruppo di progettazione",
            why="Appalto integrato: necessari progettisti qualificati indicati nell'offerta.",
            inputs_needed=[
                "Professionisti iscritti agli albi (arch./ing./geom.) per le discipline richieste",
                "Eventuale giovane professionista se richiesto",
                "Dichiarazioni di disponibilità firmate"
            ],
            risks=[
                "Mancanza iscrizione albo → esclusione",
                "Giovane professionista obbligatorio: verificare data abilitazione"
            ]
        ))
        step_num += 1

    elif recommended == "subappalto":
        pct = bando.subappalto_percentuale_max or 0
        steps.append(ActionStep(
            step=step_num, title="Pianifica subappalto nei limiti consentiti",
            why="Le lavorazioni scorporabili mancanti possono essere affidate in subappalto.",
            inputs_needed=[
                f"Individuare subappaltatore qualificato con SOA richiesta",
                f"Quota da subappaltare ≤ {pct:.0f}% dell'importo totale",
                "Indicazione eventuale terna subappaltatori se richiesta"
            ],
            risks=[
                "Non subappaltare la prevalente in misura prevalente",
                f"Regole: {bando.subappalto_regole or 'verificare capitolato'}"
            ]
        ))
        step_num += 1

    # Step finale: documentazione
    steps.append(ActionStep(
        step=step_num, title="Prepara documentazione struttura prescelta",
        why="Ogni struttura richiede documenti specifici nell'envelope amministrativo.",
        inputs_needed=[
            "DGUE di tutti i soggetti (impresa + ausiliaria/mandante/progettisti)",
            "Dichiarazioni ex art. 94-98 di tutti",
            "Contratto avvalimento/mandato RTI/lettere d'incarico progettisti"
        ],
        risks=["Documentazione incompleta → soccorso istruttorio o esclusione"]
    ))

    return ActionPlan(recommended_path=recommended, steps=steps)


# ═══════════════════════════════════════════════════════
# Procedural Checklist
# ═══════════════════════════════════════════════════════

def _build_procedural_checklist(bando: BandoRequisiti) -> List[ProceduralCheckItem]:
    items = []

    for sc in bando.scadenze:
        if "sopralluogo" in sc.tipo.lower():
            items.append(ProceduralCheckItem(
                item="Sopralluogo obbligatorio",
                deadline=sc.data,
                status="PENDING" if not (sc.data and _days_left(sc.data) and _days_left(sc.data) < 0) else "NOT_POSSIBLE",
                impact="HARD_KO" if bando.sopralluogo_obbligatorio else "INFO",
                evidence=_ev(quote=bando.sopralluogo_evidence or "", section="Sopralluogo")
            ))
        if "quesiti" in sc.tipo.lower() or "chiarimenti" in sc.tipo.lower():
            items.append(ProceduralCheckItem(
                item="Invio quesiti/chiarimenti",
                deadline=sc.data,
                status="PENDING",
                impact="INFO"
            ))
        if "offerta" in sc.tipo.lower() or "presentazione" in sc.tipo.lower():
            items.append(ProceduralCheckItem(
                item="Scadenza presentazione offerta",
                deadline=sc.data,
                status="PENDING",
                impact="HARD_KO"
            ))

    if bando.anac_contributo_richiesto == "yes":
        items.append(ProceduralCheckItem(
            item="Pagamento contributo ANAC (FVOE)",
            status="PENDING",
            impact="HARD_KO"
        ))

    if bando.piattaforma_gara:
        items.append(ProceduralCheckItem(
            item=f"Registrazione piattaforma: {bando.piattaforma_gara}",
            status="UNKNOWN",
            impact="HARD_KO"
        ))

    items.append(ProceduralCheckItem(
        item="Verifica firma digitale valida (CNS/CRS)",
        status="PENDING",
        impact="HARD_KO"
    ))

    return items


# ═══════════════════════════════════════════════════════
# Document Checklist
# ═══════════════════════════════════════════════════════

def _build_document_checklist(bando: BandoRequisiti, company: CompanyProfile) -> DocumentChecklist:
    admin = [
        DocChecklistItem(name="DGUE (Document di Gara Unico Europeo)", notes="Uno per ogni soggetto"),
        DocChecklistItem(name="Dichiarazioni ex art. 94-98 d.lgs. 36/2023"),
        DocChecklistItem(name="Visura camerale / autocertificazione CCIAA"),
        DocChecklistItem(name="Passaporto europeo / PASSOE (se piattaforma lo richiede)"),
    ]
    if bando.sopralluogo_obbligatorio:
        admin.append(DocChecklistItem(name="Attestato sopralluogo", mandatory=True,
                                     notes="Da allegare pena esclusione"))
    if bando.anac_contributo_richiesto == "yes":
        admin.append(DocChecklistItem(name="Ricevuta pagamento contributo ANAC"))

    technical = [
        DocChecklistItem(name="Copia attestato SOA (tutte le categorie richieste)"),
        DocChecklistItem(name="Certificazioni di qualità (ISO 9001, ISO 14001, ecc.)"),
    ]
    if bando.appalto_integrato:
        technical.append(DocChecklistItem(
            name="Elenco nominativo progettisti + CV + iscrizione albo",
            notes="Obbligatorio per appalto integrato"
        ))
        if bando.giovane_professionista_richiesto == "yes":
            technical.append(DocChecklistItem(
                name="Dichiarazione giovane professionista (data abilitazione)",
                mandatory=True
            ))
    if bando.fatturato_minimo_richiesto or bando.fatturato_specifico_richiesto:
        technical.append(DocChecklistItem(name="Bilanci / fatturati ultimi 3 esercizi"))

    economic = [
        DocChecklistItem(name="Offerta economica (modello bando)", mandatory=True),
        DocChecklistItem(name="Giustificativi prezzi (se offerta anomala)"),
    ]
    if bando.criteri_valutazione:
        economic.append(DocChecklistItem(
            name=f"Relazione tecnica (criteri: {', '.join(c.codice or c.descrizione[:20] for c in bando.criteri_valutazione[:3])})",
            mandatory=True
        ))

    guarantees = [
        DocChecklistItem(
            name="Cauzione provvisoria (fideiussione)",
            mandatory=bando.garanzie_richieste is not None,
            notes="Verifica riduzioni per ISO"
        ),
        DocChecklistItem(name="Impegno fideiussore per definitiva"),
    ]

    platform = [
        DocChecklistItem(
            name=f"Caricamento su {bando.piattaforma_gara or 'piattaforma gara'}",
            notes="Rispettare formati e dimensioni ammesse"
        ),
        DocChecklistItem(name="Firma digitale su ogni documento"),
        DocChecklistItem(name="Marca temporale (se richiesta dal bando)"),
    ]

    return DocumentChecklist(
        administrative=admin,
        technical=technical,
        economic=economic,
        guarantees=guarantees,
        platform=platform
    )


# ═══════════════════════════════════════════════════════
# Risk Register
# ═══════════════════════════════════════════════════════

def _build_risk_register(bando: BandoRequisiti, results: List[RequirementResult]) -> List[Risk]:
    risks = []

    # SOA scadenza imminente
    for r in results:
        if "C5_" in r.req_id and r.status == ReqStatus.KO:
            risks.append(Risk(
                risk_id=r.req_id, risk_type="soa_expiry",
                level="HIGH", message=r.user_message,
                mitigations=["Avviare rinnovo SOA immediatamente", "Verificare termine rinnovo"]
            ))

    # Vincoli esecutivi
    if bando.start_lavori_tassativo:
        risks.append(Risk(
            risk_id="M1", risk_type="execution_start_date",
            level="HIGH",
            message=f"Inizio lavori tassativo {bando.start_lavori_tassativo}: rischio operativo elevato.",
            mitigations=["Verificare disponibilità squadre", "Pianificare forniture con anticipo"]
        ))
    for v in bando.vincoli_esecutivi:
        lv = v.lower()
        level = "HIGH" if any(k in lv for k in ["scuola", "ospedale", "occupato", "tassativo"]) else "MEDIUM"
        risks.append(Risk(
            risk_id="M_exec", risk_type="execution_constraint",
            level=level, message=v,
            mitigations=["Pianificare fasi e turni", "Verificare accesso al cantiere"]
        ))

    # Scadenze critiche
    for sc in bando.scadenze:
        if sc.data:
            giorni = _days_left(sc.data)
            if giorni is not None and 0 <= giorni <= 7:
                risks.append(Risk(
                    risk_id=f"H_deadline_{sc.tipo}",
                    risk_type="deadline_critical",
                    level="HIGH",
                    message=f"Scadenza critica: {sc.tipo} entro {giorni} giorni ({sc.data})",
                    mitigations=["Agire entro oggi", "Delegare se necessario"]
                ))

    return risks


# ═══════════════════════════════════════════════════════
# Uncertainties
# ═══════════════════════════════════════════════════════

def _build_uncertainties(results: List[RequirementResult],
                         bando: BandoRequisiti) -> List[Uncertainty]:
    questions = []

    for r in results:
        if r.status == ReqStatus.UNKNOWN and r.severity == Severity.HARD_KO:
            questions.append(Uncertainty(
                question=f"[{r.req_id}] {r.user_message[:120]}",
                why_needed=f"Blocca il verdetto definitivo (HARD KO): {r.name}",
                blocks_verdict=True
            ))

    # Domande specifiche
    if bando.sopralluogo_obbligatorio:
        questions.append(Uncertainty(
            question="Hai già prenotato / effettuato il sopralluogo? (necessario attestato)",
            why_needed="Sopralluogo obbligatorio a pena di esclusione",
            blocks_verdict=True
        ))
    if bando.anac_contributo_richiesto == "unknown":
        questions.append(Uncertainty(
            question="Il bando richiede pagamento contributo ANAC? Verificare art. 'contributo'.",
            why_needed="Mancato pagamento = esclusione",
            blocks_verdict=True
        ))
    if bando.appalto_integrato and not any(r.req_id == "G1" and r.status == ReqStatus.OK
                                           for r in results):
        questions.append(Uncertainty(
            question="Hai progettisti disponibili e indicabili nell'offerta?",
            why_needed="Appalto integrato: obbligo indicazione progettisti",
            blocks_verdict=True
        ))

    return questions[:8]  # Max 8 domande


# ═══════════════════════════════════════════════════════
# MAIN: produce_decision_report
# ═══════════════════════════════════════════════════════

def produce_decision_report(bando: BandoRequisiti,
                            company: CompanyProfile) -> DecisionReport:
    """
    Orchestratore principale:
    1. Valuta tutti i requisiti atomici
    2. Calcola verdetto deterministico
    3. Costruisce top reasons, action plan, checklist, risk register
    """
    audit: List[AuditEntry] = []

    # 1. Valuta requisiti
    results = evaluate_all(bando, company)
    audit.append(AuditEntry(
        event="EVALUATE_ALL_REQUIREMENTS",
        result=f"{len(results)} requisiti valutati",
        confidence=1.0
    ))

    # 2. Verdetto
    verdict = _compute_verdict(results)
    audit.append(AuditEntry(
        event="COMPUTE_VERDICT",
        result=f"Verdetto: {verdict.status}",
        confidence=1.0
    ))

    # 3. Top reasons (max 3)
    top_reasons = _build_top_reasons(results)

    # 4. Action plan
    action_plan = _build_action_plan(results, bando, company)
    audit.append(AuditEntry(
        event="BUILD_ACTION_PLAN",
        result=f"Percorso: {action_plan.recommended_path}, {len(action_plan.steps)} passi",
        confidence=1.0
    ))

    # 5. Checklist procedurale
    proc_checklist = _build_procedural_checklist(bando)

    # 6. Checklist documentale
    doc_checklist = _build_document_checklist(bando, company)

    # 7. Risk register
    risk_register = _build_risk_register(bando, results)

    # 8. Incertezze
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
        generated_at=datetime.utcnow().isoformat() + "Z"
    )
