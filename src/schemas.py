"""
BidPilot v4.2 - Schemi Pydantic
PATCH v4.2 (evidence-first):
  - Scadenza: aggiunto campo `evidence` (quote testuale obbligatoria per guardrail)
  - BandoRequisiti: aggiunto `cig_evidence` e `piattaforma_evidence`
    → entrambi obbligatori per i guardrail post-estrazione (B)
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from enum import Enum


class _Base(BaseModel):
    model_config = {"extra": "forbid"}


# ══════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════

class Severity(str, Enum):
    HARD_KO   = "HARD_KO"
    SOFT_RISK = "SOFT_RISK"
    INFO      = "INFO"

class ReqStatus(str, Enum):
    OK        = "OK"
    KO        = "KO"
    FIXABLE   = "FIXABLE"
    UNKNOWN   = "UNKNOWN"
    RISK_FLAG = "RISK_FLAG"
    PREMIANTE = "PREMIANTE"

class VerdictStatus(str, Enum):
    NO_GO                      = "NO_GO"
    GO_WITH_STRUCTURE          = "GO_WITH_STRUCTURE"
    GO_HIGH_RISK               = "GO_HIGH_RISK"
    GO                         = "GO"
    ELIGIBLE_QUALIFICATION     = "ELIGIBLE_QUALIFICATION"
    NOT_ELIGIBLE_QUALIFICATION = "NOT_ELIGIBLE_QUALIFICATION"
    ELIGIBLE_STAGE1            = "ELIGIBLE_STAGE1"


# ══════════════════════════════════════════════════════════
# MODELLI ANNIDATI
# ══════════════════════════════════════════════════════════

class MaintenanceVariation(_Base):
    type: str = ""
    notify_within_days: Optional[int] = None
    notes: str = ""

class QualificationFee(_Base):
    system: str = ""
    amount: Optional[float] = None
    currency: str = "EUR"
    notes: str = ""

class ProcedureStage(_Base):
    name: str = ""
    documents_required: List[str] = Field(default_factory=list)
    deadline: Optional[str] = None
    eligibility_criteria: List[str] = Field(default_factory=list)


# ══════════════════════════════════════════════════════════
# COMPANY PROFILE
# ══════════════════════════════════════════════════════════

class LegalRepresentative(_Base):
    name: str = ""
    role: str = ""
    has_digital_signature: bool = False
    signing_powers_proof: Literal["available", "missing", "unknown"] = "unknown"

class CameralRegistration(_Base):
    is_registered: bool = True
    rea_number: str = ""
    ateco_codes: List[str] = Field(default_factory=list)
    business_scope_text: str = ""
    coherence_with_tender_object: Literal["yes", "no", "unknown"] = "unknown"

class SOAAttestation(_Base):
    category: str
    soa_class: str
    expiry_date: str
    issue_date: str = ""
    notes: str = ""

class Certification(_Base):
    cert_type: str
    valid: bool = True
    scope: str = ""
    issuer: str = ""
    expiry_date: str = ""

class TurnoverEntry(_Base):
    year: int
    amount_eur: float

class SectorTurnoverEntry(_Base):
    year: int
    sector: str
    amount_eur: float

class SimilarWork(_Base):
    title: str = ""
    year: int = 0
    amount_eur: float = 0.0
    categories: List[str] = Field(default_factory=list)
    client: str = ""

class StaffRole(_Base):
    role: str
    available: bool = True
    name: str = ""

class Designer(_Base):
    name: str = ""
    profession: str = ""
    order_registration: Literal["yes", "no", "unknown"] = "unknown"
    license_date: str = ""
    young_professional: Literal["yes", "no", "unknown"] = "unknown"

class CompanyProfile(_Base):
    legal_name: str = ""
    vat_id: str = ""
    tax_id: str = ""
    registered_office: str = ""
    pec: str = ""
    legal_representative: LegalRepresentative = Field(default_factory=LegalRepresentative)
    cameral_registration: CameralRegistration = Field(default_factory=CameralRegistration)
    soa_attestations: List[SOAAttestation] = Field(default_factory=list)
    certifications: List[Certification] = Field(default_factory=list)
    turnover_by_year: List[TurnoverEntry] = Field(default_factory=list)
    sector_turnover_by_year: List[SectorTurnoverEntry] = Field(default_factory=list)
    bank_references_available: Literal["yes", "no", "unknown"] = "unknown"
    cel_records_available: Literal["yes", "no", "unknown"] = "unknown"
    similar_works: List[SimilarWork] = Field(default_factory=list)
    avg_headcount: int = 0
    key_roles: List[StaffRole] = Field(default_factory=list)
    equipment_capabilities: str = ""
    has_inhouse_design: bool = False
    external_designers_available: Literal["yes", "no", "unknown"] = "unknown"
    design_team: List[Designer] = Field(default_factory=list)
    willing_rti: bool = True
    willing_avvalimento: bool = True
    willing_subcontract: bool = True
    operating_regions: List[str] = Field(default_factory=list)
    start_date_constraints: str = ""
    ccnl_applied: str = ""
    has_credit_license: Literal["yes", "no", "unknown"] = "unknown"
    credit_license_requested: bool = False
    psf_score: Optional[float] = None
    deposited_statements_count: int = 0
    has_bim_experience: bool = False
    bim_experience_count: int = 0


# ══════════════════════════════════════════════════════════
# EVIDENCE
# ══════════════════════════════════════════════════════════

class Evidence(_Base):
    quote: str = ""
    page: int = 0
    section: str = ""
    confidence: float = 1.0


# ══════════════════════════════════════════════════════════
# DECISION REPORT
# ══════════════════════════════════════════════════════════

class Fixability(_Base):
    is_fixable: bool = False
    allowed_methods: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)

class CompanyGap(_Base):
    missing_data: List[str] = Field(default_factory=list)
    missing_assets: List[str] = Field(default_factory=list)
    notes: str = ""

class RequirementResult(_Base):
    req_id: str
    name: str
    category: str
    status: ReqStatus
    severity: Severity
    fixability: Fixability = Field(default_factory=Fixability)
    evidence: List[Evidence] = Field(default_factory=list)
    company_gap: CompanyGap = Field(default_factory=CompanyGap)
    user_message: str = ""
    confidence: float = 1.0

class TopReason(_Base):
    issue_type: str
    severity: Severity
    message: str
    evidence: Optional[Evidence] = None
    can_be_fixed: bool = False
    fix_options: List[str] = Field(default_factory=list)

class ActionStep(_Base):
    step: int
    title: str
    why: str
    inputs_needed: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    evidence: List[Evidence] = Field(default_factory=list)

class ActionPlan(_Base):
    recommended_path: str = "none"
    steps: List[ActionStep] = Field(default_factory=list)

class ProceduralCheckItem(_Base):
    item: str
    deadline: Optional[str] = None
    status: Literal["PENDING", "DONE", "NOT_POSSIBLE", "UNKNOWN"] = "PENDING"
    impact: str = ""
    evidence: Optional[Evidence] = None

class DocChecklistItem(_Base):
    name: str
    mandatory: bool = True
    notes: str = ""

class DocumentChecklist(_Base):
    administrative: List[DocChecklistItem] = Field(default_factory=list)
    technical: List[DocChecklistItem] = Field(default_factory=list)
    economic: List[DocChecklistItem] = Field(default_factory=list)
    guarantees: List[DocChecklistItem] = Field(default_factory=list)
    platform: List[DocChecklistItem] = Field(default_factory=list)

class Risk(_Base):
    risk_id: str
    risk_type: str
    level: Literal["HIGH", "MEDIUM", "LOW"]
    message: str
    evidence: Optional[Evidence] = None
    mitigations: List[str] = Field(default_factory=list)

class Uncertainty(_Base):
    question: str
    why_needed: str
    blocks_verdict: bool = False

class AuditEntry(_Base):
    event: str
    result: str
    confidence: float = 1.0
    evidence_refs: List[str] = Field(default_factory=list)

class Verdict(_Base):
    status: VerdictStatus
    legal_eligibility: Literal["eligible", "not_eligible", "uncertain"]
    operational_feasibility: Literal["feasible", "risky", "not_feasible", "uncertain"]
    summary: str = ""
    stage_outputs_json: str = ""
    profile_confidence: float = 1.0

    @property
    def stage_outputs(self):
        import json
        if self.stage_outputs_json:
            try:
                return json.loads(self.stage_outputs_json)
            except Exception:
                return {}
        return None

class DecisionReport(_Base):
    verdict: Verdict
    top_reasons: List[TopReason] = Field(default_factory=list)
    requirements_results: List[RequirementResult] = Field(default_factory=list)
    action_plan: ActionPlan = Field(default_factory=ActionPlan)
    procedural_checklist: List[ProceduralCheckItem] = Field(default_factory=list)
    document_checklist: DocumentChecklist = Field(default_factory=DocumentChecklist)
    risk_register: List[Risk] = Field(default_factory=list)
    uncertainties: List[Uncertainty] = Field(default_factory=list)
    audit_trace: List[AuditEntry] = Field(default_factory=list)
    generated_at: str = ""
    engine_mode: Literal["gara", "qualificazione", "ppp_multistage"] = "gara"


# ══════════════════════════════════════════════════════════
# BandoRequisiti — estratto dall'LLM
# ══════════════════════════════════════════════════════════

class Scadenza(_Base):
    tipo: str
    data: Optional[str] = None
    ora: Optional[str] = None
    obbligatorio: bool = False
    note: Optional[str] = None
    # PATCH v4.2: evidence obbligatoria per guardrail post-estrazione (B)
    evidence: Optional[str] = None
    esclusione_se_mancante: bool = False

class SOACategoria(_Base):
    categoria: str
    descrizione: str = ""
    classifica: str
    prevalente: bool = False
    importo_categoria: Optional[float] = None
    is_scorporabile: bool = False
    qualificazione_obbligatoria: bool = True
    subappaltabile_100: bool = False
    evidence: Optional[str] = None   # OBBLIGATORIA: guardrail rimuove entry senza evidence

class SOAEquivalenza(_Base):
    from_cat: str
    to_cat: str
    conditions_text: str = ""
    scope: Literal["participation_only", "execution_only", "both"] = "both"

class FiguraProfessionale(_Base):
    ruolo: str
    requisiti: Optional[str] = None
    obbligatorio: bool = False
    esperienza_minima: Optional[str] = None

class Criterio(_Base):
    codice: Optional[str] = None
    descrizione: str
    punteggio_max: float
    tipo: Optional[str] = None

class Garanzie(_Base):
    provvisoria: Optional[float] = None
    percentuale_provvisoria: Optional[float] = None
    definitiva: Optional[float] = None
    riduzione_iso9001: bool = False
    riduzione_mpmi: bool = False

class CrediteLicense(_Base):
    required: bool = False
    trigger_condition: str = ""
    trigger_soa_class_threshold: str = ""
    pena_esclusione: bool = False

class BandoRequisiti(_Base):
    """Schema v4.2 — aggiunge cig_evidence, piattaforma_evidence per evidence-first pipeline"""

    # ─── Metadati gara ────────────────────────────────────
    oggetto_appalto: str
    oggetto_evidence: Optional[str] = None
    stazione_appaltante: str
    stazione_evidence: Optional[str] = None

    document_type: Literal[
        "disciplinare", "lettera_invito", "avviso_eoi",
        "richiesta_preventivo", "verbale_esito", "avviso_manifestazione",
        "sistema_qualificazione", "altro"
    ] = "disciplinare"

    procedure_family: Literal[
        "aperta", "negoziata", "negoziata_senza_bando",
        "eoi", "affidamento_diretto", "concessione",
        "accordo_quadro", "dialogo_competitivo", "altro"
    ] = "aperta"

    procedure_legal_basis: Optional[str] = None

    is_qualification_system: bool = False
    qualification_system_owner: Optional[str] = None
    qualification_system_type: Optional[str] = None
    qualification_workflow: Optional[Literal[
        "prima_iscrizione", "estensione", "mantenimento", "dequalifica"
    ]] = None

    is_pnrr: bool = False
    is_bim: bool = False
    is_concession: bool = False
    is_eoi: bool = False
    is_accordo_quadro: bool = False
    inversione_procedimentale: bool = False

    # ─── Importi ──────────────────────────────────────────
    importo_lavori: Optional[float] = None
    importo_evidence: Optional[str] = None   # OBBLIGATORIA per guardrail
    importo_base_gara: Optional[float] = None
    oneri_sicurezza: Optional[float] = None
    importo_totale: Optional[float] = None

    # ─── Geo ──────────────────────────────────────────────
    comune_stazione_appaltante: Optional[str] = None
    provincia_stazione_appaltante: Optional[str] = None
    regione_stazione_appaltante: Optional[str] = None
    luogo_esecuzione: Optional[str] = None

    # ─── Codici ───────────────────────────────────────────
    codice_cup: Optional[str] = None
    codice_cig: Optional[str] = None
    # PATCH v4.2: evidence per CIG obbligatoria (guardrail B)
    cig_evidence: Optional[str] = None
    cpv: Optional[str] = None

    # ─── Procedura ────────────────────────────────────────
    tipo_procedura: Optional[str] = None
    criterio_aggiudicazione: Optional[str] = None
    punteggio_tecnico: Optional[float] = None
    punteggio_economico: Optional[float] = None
    lotti: int = 1

    # ─── Scadenze ─────────────────────────────────────────
    scadenze: List[Scadenza] = Field(default_factory=list)

    # ─── Canale invio / piattaforma ───────────────────────
    canale_invio: Literal["piattaforma", "PEC", "email", "misto", "unknown"] = "unknown"
    piattaforma_gara: Optional[str] = None
    piattaforma_url: Optional[str] = None
    piattaforma_spid_required: bool = False
    piattaforma_failure_policy_exists: bool = False
    # PATCH v4.2: evidence per piattaforma (guardrail B)
    piattaforma_evidence: Optional[str] = None

    platform_failure_extends_deadline: bool = False
    platform_failure_notification_required: bool = False
    platform_failure_oe_obligations: List[str] = Field(default_factory=list)

    # ─── SOA ──────────────────────────────────────────────
    soa_richieste: List[SOACategoria] = Field(default_factory=list)
    soa_equivalences: List[SOAEquivalenza] = Field(default_factory=list)
    soa_fifth_increase_allowed: Optional[bool] = None
    soa_copy_required_pena_esclusione: bool = False
    alt_qualification_allowed: bool = False
    alt_qualification_type: Optional[Literal["art90", "art10_allII18"]] = None
    avvalimento_banned_categories: List[str] = Field(default_factory=list)
    cultural_works_dm154_required: bool = False
    cultural_works_dm154_pena_esclusione: bool = False
    lots_max_awardable_per_bidder: Optional[int] = None
    lots_priority_declaration_required: bool = False
    credit_license: Optional[CrediteLicense] = None

    # ─── Certificazioni ───────────────────────────────────
    certificazioni_richieste: List[str] = Field(default_factory=list)

    # ─── Economico-finanziari ─────────────────────────────
    fatturato_minimo_richiesto: Optional[float] = None
    fatturato_specifico_richiesto: Optional[float] = None
    fatturato_anni_riferimento: int = 3
    referenze_num_min: Optional[int] = None
    referenze_valore_min: Optional[float] = None
    referenze_anni_lookback: int = 3

    # ─── Forme partecipazione ─────────────────────────────
    allowed_forms: List[str] = Field(default_factory=list)
    rti_mandataria_quota_min: Optional[float] = None
    rti_mandante_quota_min: Optional[float] = None

    # ─── Requisiti generali ───────────────────────────────
    dgue_required: bool = True
    dgue_format: Optional[str] = None
    dgue_sezioni_obbligatorie: List[str] = Field(default_factory=list)
    protocollo_legalita_required: bool = False
    patto_integrita_required: bool = False
    patto_integrita_pena_esclusione: bool = False

    # ─── Idoneità professionale ───────────────────────────
    albi_professionali_required: List[str] = Field(default_factory=list)
    figure_professionali_richieste: List[FiguraProfessionale] = Field(default_factory=list)

    # ─── CCNL / Lavoro ────────────────────────────────────
    ccnl_reference: Optional[str] = None
    labour_costs_must_indicate: bool = False
    labour_costs_pena_esclusione: bool = False
    safety_company_costs_must_indicate: bool = False
    safety_costs_pena_esclusione: bool = False

    # ─── Garanzie ─────────────────────────────────────────
    garanzie_richieste: Optional[Garanzie] = None
    polizze_richieste: List[str] = Field(default_factory=list)

    # ─── Avvalimento / subappalto ─────────────────────────
    avvalimento_ammesso: Literal["yes", "no", "unknown"] = "unknown"
    avvalimento_regole: Optional[str] = None
    avvalimento_banned_for_general: bool = True
    avvalimento_migliorativo_ammesso: bool = False
    rti_ammesso: Literal["yes", "no", "unknown"] = "unknown"
    rti_regole: Optional[str] = None
    subappalto_percentuale_max: Optional[float] = None
    subappalto_regole: Optional[str] = None
    subappalto_cascade_ban: bool = True
    subappalto_dichiarazione_dgue_pena_esclusione: bool = False
    subappalto_qualificante_ammesso: Literal["yes", "no", "unknown"] = "unknown"
    subappalto_qualificante_dichiarazione_pena_esclusione: bool = False
    soa_prevalent_must_cover_subcontracted: bool = False

    # ─── ANAC / FVOE ──────────────────────────────────────
    anac_contributo_richiesto: Literal["yes", "no", "unknown"] = "unknown"
    fvoe_required: bool = False

    # ─── Sopralluogo ──────────────────────────────────────
    sopralluogo_obbligatorio: bool = False
    sopralluogo_evidence: Optional[str] = None

    # ─── PNRR ─────────────────────────────────────────────
    pnrr_dnsh_required: bool = False
    pnrr_principi_required: List[str] = Field(default_factory=list)
    pnrr_clausola_sociale: Optional[str] = None
    cam_obbligatori: List[str] = Field(default_factory=list)
    cam_premianti: List[str] = Field(default_factory=list)

    # ─── BIM R41-R45 ──────────────────────────────────────
    bim_capitolato_informativo: bool = False
    bim_ogi_required: bool = False
    bim_ogi_valutazione_oepv: bool = False
    bim_ruoli_minimi: List[str] = Field(default_factory=list)
    bim_4d_required: bool = False
    bim_5d_required: bool = False
    bim_experience_required: bool = False
    bim_experience_min_count: Optional[int] = None
    bim_experience_min_amount: Optional[float] = None
    bim_experience_is_admission: bool = False
    bim_lod_min_fase: Optional[str] = None
    bim_ifc_required: bool = False
    bim_ifc_schema: Optional[str] = None
    bim_as_built_required: bool = False

    # ─── Appalto integrato ────────────────────────────────
    appalto_integrato: bool = False
    appalto_integrato_evidence: Optional[str] = None
    giovane_professionista_richiesto: Literal["yes", "no", "unknown"] = "unknown"

    # ─── Offerta tecnica R48, R49 ─────────────────────────
    tech_offer_divieto_prezzi_pena_esclusione: bool = False
    tech_offer_max_pagine: Optional[int] = None
    criteri_valutazione: List[Criterio] = Field(default_factory=list)
    vincoli_speciali: List[str] = Field(default_factory=list)
    tech_offer_riservatezza_required: bool = False
    tech_offer_riservatezza_scope: Optional[str] = None

    # ─── Vincoli contrattuali R51-R53, M1 ────────────────
    start_lavori_tassativo: Optional[str] = None
    vincoli_esecutivi: List[str] = Field(default_factory=list)
    quinto_obbligo: bool = False
    revisione_prezzi_soglia_pct: Optional[float] = None
    cct_previsto: bool = False
    cct_composizione: Optional[int] = None
    foro_competente: Optional[str] = None
    arbitrato_escluso: bool = False
    tech_claims_must_be_provable: bool = False
    tech_claims_verification_timing: Literal[
        "pre_aggiudicazione", "post_aggiudicazione", "unknown"
    ] = "unknown"

    # ─── Concessione R54, R55 ─────────────────────────────
    concession_price_in_tech_ko: bool = False
    concession_offer_forbidden_forms: List[str] = Field(default_factory=list)
    concession_above_base_is_ko: bool = False

    # ─── EOI R22, R23, R58, R59 ──────────────────────────
    eoi_invited_count_target: Optional[int] = None
    eoi_selection_criteria: List[str] = Field(default_factory=list)
    eoi_selection_method: Literal["punteggio", "sorteggio", "ordine_arrivo", "unknown"] = "unknown"
    sa_reserve_rights: bool = False
    eoi_territorial_experience_required: bool = False
    eoi_territorial_area: Optional[str] = None
    eoi_territorial_lookback_years: int = 5
    eoi_size_factor_used: bool = False
    eoi_employee_reference_year: Optional[int] = None

    # ─── D11-D20: Sistema Qualificazione ──────────────────
    qualification_requirements_on_submission: bool = False
    qualification_integration_only_if_owned: bool = False
    qualification_missing_docs_deadline_days: Optional[int] = None
    qualification_failure_effect: Optional[str] = None
    maintenance_variation_types: List[MaintenanceVariation] = Field(default_factory=list)
    maintenance_renewal_cycle_years: int = 3
    maintenance_submit_months_before: int = 6
    maintenance_timely_extends_validity: bool = False
    qualification_expiry_date: Optional[str] = None
    psf_min_threshold: Optional[float] = None
    psf_below_threshold_effect: Optional[str] = None
    psf_exception_concordato: bool = False
    financial_min_bilanci_applicant: int = 1
    financial_min_bilanci_auxiliary: int = 2
    financial_annual_update_required: bool = False
    avvalimento_non_frazionabili: List[str] = Field(default_factory=list)
    avvalimento_no_cascade: bool = True
    interpello_class_type: Optional[str] = None
    interpello_cap_rule: Optional[str] = None
    rete_soggettivita_giuridica_required: bool = False
    qualification_fee_required: bool = False
    qualification_fee_amounts: List[QualificationFee] = Field(default_factory=list)
    qualification_site_visit_possible: bool = False

    # ─── D21-D23: PPP / Grandi Opere ─────────────────────
    procedure_multi_stage: bool = False
    procedure_stages: List[ProcedureStage] = Field(default_factory=list)
    ppp_private_share_percent: Optional[float] = None
    ppp_private_contribution_amount: Optional[float] = None
    ppp_spv_required: bool = False
    ppp_governance_constraints: Optional[str] = None
    security_special_regime: bool = False
    security_reference_text: Optional[str] = None
    security_admission_impact: Literal["esclusione", "condizione_esecutiva", "info"] = "info"


# ══════════════════════════════════════════════════════════
# TenderProfile (legacy)
# ══════════════════════════════════════════════════════════

class Deadline(_Base):
    dtype: str
    datetime_str: Optional[str] = None
    timezone: str = "Europe/Rome"
    is_mandatory: bool = False
    exclusion_if_missed: bool = False
    evidence: Optional[Evidence] = None

class WorksAmounts(_Base):
    total_amount_eur: Optional[float] = None
    works_amount_eur: Optional[float] = None
    services_amount_eur: Optional[float] = None
    safety_costs_eur: Optional[float] = None
    design_amount_eur: Optional[float] = None
    evidence: Optional[Evidence] = None