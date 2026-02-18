"""
BidPilot v4.0 - Schemi Pydantic
Allineato alla Libreria Requisiti v2.1 (84 requisiti · D01–D23 · 16 regole anti-inferenza)
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
from enum import Enum


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
    FIXABLE   = "FIXABLE"      # COLMABILE
    UNKNOWN   = "UNKNOWN"
    RISK_FLAG = "RISK_FLAG"
    PREMIANTE = "PREMIANTE"    # non-KO, solo perdita punti

class VerdictStatus(str, Enum):
    NO_GO             = "NO_GO"
    GO_WITH_STRUCTURE = "GO_WITH_STRUCTURE"
    GO_HIGH_RISK      = "GO_HIGH_RISK"
    GO                = "GO"
    # Qualificazione (D11)
    ELIGIBLE_QUALIFICATION   = "ELIGIBLE_QUALIFICATION"
    NOT_ELIGIBLE_QUALIFICATION = "NOT_ELIGIBLE_QUALIFICATION"
    # PPP multistage (D21)
    ELIGIBLE_STAGE1   = "ELIGIBLE_STAGE1"

class Confidence(str, Enum):
    HIGH    = "1.0"   # pattern esplicito: 'a pena di esclusione', 'è richiesto'
    MEDIUM  = "0.7"   # trovato ma ambiguo
    LOW     = "0.4"   # contesto, non prescrizione → mai HARD KO


# ══════════════════════════════════════════════════════════
# COMPANY PROFILE
# ══════════════════════════════════════════════════════════

class LegalRepresentative(BaseModel):
    name: str = ""
    role: str = ""
    has_digital_signature: bool = False
    signing_powers_proof: Literal["available", "missing", "unknown"] = "unknown"

class CameralRegistration(BaseModel):
    is_registered: bool = True
    rea_number: str = ""
    ateco_codes: List[str] = Field(default_factory=list)
    business_scope_text: str = ""
    coherence_with_tender_object: Literal["yes", "no", "unknown"] = "unknown"

class SOAAttestation(BaseModel):
    category: str
    soa_class: str
    expiry_date: str
    issue_date: str = ""
    notes: str = ""

class Certification(BaseModel):
    cert_type: str
    valid: bool = True
    scope: str = ""
    issuer: str = ""
    expiry_date: str = ""

class TurnoverEntry(BaseModel):
    year: int
    amount_eur: float

class SectorTurnoverEntry(BaseModel):
    year: int
    sector: str
    amount_eur: float

class SimilarWork(BaseModel):
    title: str = ""
    year: int = 0
    amount_eur: float = 0.0
    categories: List[str] = Field(default_factory=list)
    client: str = ""

class StaffRole(BaseModel):
    role: str
    available: bool = True
    name: str = ""

class Designer(BaseModel):
    name: str = ""
    profession: str = ""
    order_registration: Literal["yes", "no", "unknown"] = "unknown"
    license_date: str = ""
    young_professional: Literal["yes", "no", "unknown"] = "unknown"

class CompanyProfile(BaseModel):
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
    # Compliance CCNL
    ccnl_applied: str = ""
    # Patente a crediti (D10)
    has_credit_license: Literal["yes", "no", "unknown"] = "unknown"
    credit_license_requested: bool = False
    # PSF/PSFM (D16)
    psf_score: Optional[float] = None
    # Bilanci depositati (D17)
    deposited_statements_count: int = 0


# ══════════════════════════════════════════════════════════
# EVIDENCE
# ══════════════════════════════════════════════════════════

class Evidence(BaseModel):
    quote: str = ""
    page: int = 0
    section: str = ""
    confidence: float = 1.0  # 1.0 / 0.7 / 0.4 — Libreria C.2


# ══════════════════════════════════════════════════════════
# DECISION REPORT
# ══════════════════════════════════════════════════════════

class Fixability(BaseModel):
    is_fixable: bool = False
    allowed_methods: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)

class CompanyGap(BaseModel):
    missing_data: List[str] = Field(default_factory=list)
    missing_assets: List[str] = Field(default_factory=list)
    notes: str = ""

class RequirementResult(BaseModel):
    req_id: str
    name: str
    category: str
    status: ReqStatus
    severity: Severity
    fixability: Fixability = Field(default_factory=Fixability)
    evidence: List[Evidence] = Field(default_factory=list)
    company_gap: CompanyGap = Field(default_factory=CompanyGap)
    user_message: str = ""
    # Nuovo: confidence aggregata per questo requisito
    confidence: float = 1.0

class TopReason(BaseModel):
    issue_type: str
    severity: Severity
    message: str
    evidence: Optional[Evidence] = None
    can_be_fixed: bool = False
    fix_options: List[str] = Field(default_factory=list)

class ActionStep(BaseModel):
    step: int
    title: str
    why: str
    inputs_needed: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    evidence: List[Evidence] = Field(default_factory=list)

class ActionPlan(BaseModel):
    recommended_path: str = "none"
    steps: List[ActionStep] = Field(default_factory=list)

class ProceduralCheckItem(BaseModel):
    item: str
    deadline: Optional[str] = None
    status: Literal["PENDING", "DONE", "NOT_POSSIBLE", "UNKNOWN"] = "PENDING"
    impact: str = ""
    evidence: Optional[Evidence] = None

class DocChecklistItem(BaseModel):
    name: str
    mandatory: bool = True
    notes: str = ""

class DocumentChecklist(BaseModel):
    administrative: List[DocChecklistItem] = Field(default_factory=list)
    technical: List[DocChecklistItem] = Field(default_factory=list)
    economic: List[DocChecklistItem] = Field(default_factory=list)
    guarantees: List[DocChecklistItem] = Field(default_factory=list)
    platform: List[DocChecklistItem] = Field(default_factory=list)

class Risk(BaseModel):
    risk_id: str
    risk_type: str
    level: Literal["HIGH", "MEDIUM", "LOW"]
    message: str
    evidence: Optional[Evidence] = None
    mitigations: List[str] = Field(default_factory=list)

class Uncertainty(BaseModel):
    question: str
    why_needed: str
    blocks_verdict: bool = False

class AuditEntry(BaseModel):
    event: str
    result: str
    confidence: float = 1.0
    evidence_refs: List[Dict[str, Any]] = Field(default_factory=list)

class Verdict(BaseModel):
    status: VerdictStatus
    legal_eligibility: Literal["eligible", "not_eligible", "uncertain"]
    operational_feasibility: Literal["feasible", "risky", "not_feasible", "uncertain"]
    summary: str = ""
    # PPP multi-stage output (D21)
    stage_outputs: Optional[Dict[str, str]] = None
    # Confidence profilo (C.2 Libreria)
    profile_confidence: float = 1.0

class DecisionReport(BaseModel):
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
    tender_profile: Optional[Any] = None
    # Modalità speciale (qualificazione D11 / PPP D21)
    engine_mode: Literal["gara", "qualificazione", "ppp_multistage"] = "gara"


# ══════════════════════════════════════════════════════════
# LEGACY: BandoRequisiti — estratto dall'LLM
# v4.0: allineato alla Libreria Requisiti v2.1 completa
# ══════════════════════════════════════════════════════════

class Scadenza(BaseModel):
    tipo: str
    data: Optional[str] = None
    ora: Optional[str] = None
    obbligatorio: bool = False
    note: Optional[str] = None
    evidence: Optional[str] = None
    esclusione_se_mancante: bool = False

class SOACategoria(BaseModel):
    categoria: str
    descrizione: str = ""
    classifica: str
    prevalente: bool = False
    importo_categoria: Optional[float] = None
    is_scorporabile: bool = False
    qualificazione_obbligatoria: bool = True
    subappaltabile_100: bool = False
    evidence: Optional[str] = None

class SOAEquivalenza(BaseModel):
    """D01 — Equivalenze esplicite tra categorie SOA"""
    from_cat: str
    to_cat: str
    conditions_text: str = ""
    scope: Literal["participation_only", "execution_only", "both"] = "both"

class FiguraProfessionale(BaseModel):
    ruolo: str
    requisiti: Optional[str] = None
    obbligatorio: bool = False
    esperienza_minima: Optional[str] = None

class Criterio(BaseModel):
    codice: Optional[str] = None
    descrizione: str
    punteggio_max: float
    tipo: Optional[str] = None

class Garanzie(BaseModel):
    provvisoria: Optional[float] = None
    percentuale_provvisoria: Optional[float] = None
    definitiva: Optional[float] = None
    # Riduzioni (R30)
    riduzione_iso9001: bool = False
    riduzione_mpmi: bool = False

class CrediteLicense(BaseModel):
    """D10 — Patente a crediti"""
    required: bool = False
    trigger_condition: str = ""           # testo letterale dal disciplinare
    trigger_soa_class_threshold: str = "" # es. "III"
    pena_esclusione: bool = False

class BandoRequisiti(BaseModel):
    """Schema v4.0 — allineato alla Libreria Requisiti v2.1 (84 requisiti)"""

    # ─── Metadati gara (R00a, R00b) ───────────────────────────────────────────
    oggetto_appalto: str
    oggetto_evidence: Optional[str] = None

    stazione_appaltante: str
    stazione_evidence: Optional[str] = None

    # R00a — Tipo documento (Sezione A, Livello 0)
    document_type: Literal[
        "disciplinare", "lettera_invito", "avviso_eoi",
        "richiesta_preventivo", "verbale_esito", "avviso_manifestazione",
        "sistema_qualificazione", "altro"
    ] = "disciplinare"

    # R00b — Famiglia procedurale
    procedure_family: Literal[
        "aperta", "negoziata", "negoziata_senza_bando",
        "eoi", "affidamento_diretto", "concessione",
        "accordo_quadro", "dialogo_competitivo", "altro"
    ] = "aperta"

    procedure_legal_basis: Optional[str] = None  # es. "art.50", "art.71"

    # D11 — Pre-gate Sistema di Qualificazione
    is_qualification_system: bool = False
    qualification_system_owner: Optional[str] = None    # es. "RFI", "FSI"
    qualification_system_type: Optional[str] = None
    qualification_workflow: Optional[Literal[
        "prima_iscrizione", "estensione", "mantenimento", "dequalifica"
    ]] = None

    # Flags procedurali speciali
    is_pnrr: bool = False
    is_bim: bool = False
    is_concession: bool = False
    is_eoi: bool = False
    is_accordo_quadro: bool = False
    inversione_procedimentale: bool = False   # R50

    # ─── Importi (R24) ────────────────────────────────────────────────────────
    importo_lavori: Optional[float] = None
    importo_evidence: Optional[str] = None
    importo_base_gara: Optional[float] = None
    oneri_sicurezza: Optional[float] = None
    importo_totale: Optional[float] = None

    # ─── Geo ──────────────────────────────────────────────────────────────────
    comune_stazione_appaltante: Optional[str] = None
    provincia_stazione_appaltante: Optional[str] = None
    regione_stazione_appaltante: Optional[str] = None
    luogo_esecuzione: Optional[str] = None

    # ─── Codici ───────────────────────────────────────────────────────────────
    codice_cup: Optional[str] = None
    codice_cig: Optional[str] = None
    cpv: Optional[str] = None

    # ─── Procedura / aggiudicazione ───────────────────────────────────────────
    tipo_procedura: Optional[str] = None
    criterio_aggiudicazione: Optional[str] = None   # "minor_prezzo" | "OEPV"
    punteggio_tecnico: Optional[float] = None
    punteggio_economico: Optional[float] = None
    lotti: int = 1                                  # D09

    # ─── Scadenze (R01, R05, R06) ─────────────────────────────────────────────
    scadenze: List[Scadenza] = Field(default_factory=list)

    # ─── Canale invio (R02) ───────────────────────────────────────────────────
    canale_invio: Literal["piattaforma", "PEC", "email", "misto", "unknown"] = "unknown"
    piattaforma_gara: Optional[str] = None
    piattaforma_url: Optional[str] = None
    piattaforma_spid_required: bool = False
    piattaforma_failure_policy_exists: bool = False   # R17, R60

    # ─── SOA e categorie lavori (R24–R29, D01–D10) ────────────────────────────
    soa_richieste: List[SOACategoria] = Field(default_factory=list)
    soa_equivalences: List[SOAEquivalenza] = Field(default_factory=list)  # D01
    soa_fifth_increase_allowed: Optional[bool] = None   # D02
    soa_copy_required_pena_esclusione: bool = False      # D08
    alt_qualification_allowed: bool = False              # R27
    alt_qualification_type: Optional[Literal["art90", "art10_allII18"]] = None

    # Beni culturali (D05, D06, D07)
    avvalimento_banned_categories: List[str] = Field(default_factory=list)
    cultural_works_dm154_required: bool = False
    cultural_works_dm154_pena_esclusione: bool = False

    # D09 — Lotti: vincolo aggiudicazione
    lots_max_awardable_per_bidder: Optional[int] = None
    lots_priority_declaration_required: bool = False

    # D10 — Patente a crediti
    credit_license: Optional[CrediteLicense] = None

    # ─── Certificazioni (R28) ─────────────────────────────────────────────────
    certificazioni_richieste: List[str] = Field(default_factory=list)

    # ─── Requisiti economico-finanziari (R20, R21) ────────────────────────────
    fatturato_minimo_richiesto: Optional[float] = None
    fatturato_specifico_richiesto: Optional[float] = None
    fatturato_anni_riferimento: int = 3
    referenze_num_min: Optional[int] = None            # R21 - numero contratti analoghi
    referenze_valore_min: Optional[float] = None        # R21 - valore singolo/cumulato
    referenze_anni_lookback: int = 3                    # R21

    # ─── Forme partecipazione (R10, R11, R12) ─────────────────────────────────
    allowed_forms: List[str] = Field(default_factory=list)  # singolo/RTI/consorzio/rete/...
    rti_mandataria_quota_min: Optional[float] = None
    rti_mandante_quota_min: Optional[float] = None

    # ─── Requisiti generali (R13–R17) ─────────────────────────────────────────
    dgue_required: bool = True
    dgue_format: Optional[str] = None
    dgue_sezioni_obbligatorie: List[str] = Field(default_factory=list)
    protocollo_legalita_required: bool = False
    patto_integrita_required: bool = False
    patto_integrita_pena_esclusione: bool = False

    # ─── Idoneità professionale (R18, R19) ────────────────────────────────────
    albi_professionali_required: List[str] = Field(default_factory=list)
    figure_professionali_richieste: List[FiguraProfessionale] = Field(default_factory=list)

    # ─── Lavoro/CCNL (R36, R37) ───────────────────────────────────────────────
    ccnl_reference: Optional[str] = None
    labour_costs_must_indicate: bool = False
    labour_costs_pena_esclusione: bool = False
    safety_company_costs_must_indicate: bool = False
    safety_costs_pena_esclusione: bool = False

    # ─── Garanzie (R30, R31, R32) ─────────────────────────────────────────────
    garanzie_richieste: Optional[Garanzie] = None
    polizze_richieste: List[str] = Field(default_factory=list)   # CAR/RCT/RCO/RCP

    # ─── Avvalimento e subappalto (R33, R34, R35) ─────────────────────────────
    avvalimento_ammesso: Literal["yes", "no", "unknown"] = "unknown"
    avvalimento_regole: Optional[str] = None
    avvalimento_banned_for_general: bool = True       # sempre vietato per generali
    avvalimento_migliorativo_ammesso: bool = False

    rti_ammesso: Literal["yes", "no", "unknown"] = "unknown"
    rti_regole: Optional[str] = None

    subappalto_percentuale_max: Optional[float] = None
    subappalto_regole: Optional[str] = None
    subappalto_cascade_ban: bool = True
    subappalto_dichiarazione_dgue_pena_esclusione: bool = False   # R34
    subappalto_qualificante_ammesso: Literal["yes", "no", "unknown"] = "unknown"  # R35
    subappalto_qualificante_dichiarazione_pena_esclusione: bool = False  # D03
    soa_prevalent_must_cover_subcontracted: bool = False          # D04

    # ─── ANAC / FVOE (R07, R08) ───────────────────────────────────────────────
    anac_contributo_richiesto: Literal["yes", "no", "unknown"] = "unknown"
    fvoe_required: bool = False

    # ─── Sopralluogo (R06) ────────────────────────────────────────────────────
    sopralluogo_obbligatorio: bool = False
    sopralluogo_evidence: Optional[str] = None

    # ─── Piattaforma (R03) ────────────────────────────────────────────────────
    # già sopra: piattaforma_gara, piattaforma_url, piattaforma_spid_required

    # ─── PNRR (R38, R39, R40) ─────────────────────────────────────────────────
    pnrr_dnsh_required: bool = False
    pnrr_principi_required: List[str] = Field(default_factory=list)  # gender, giovani...
    pnrr_clausola_sociale: Optional[str] = None
    cam_obbligatori: List[str] = Field(default_factory=list)
    cam_premianti: List[str] = Field(default_factory=list)

    # ─── BIM (R41–R45) ────────────────────────────────────────────────────────
    bim_capitolato_informativo: bool = False
    bim_ogi_required: bool = False
    bim_ogi_valutazione_oepv: bool = False
    bim_ruoli_minimi: List[str] = Field(default_factory=list)
    bim_4d_required: bool = False
    bim_5d_required: bool = False

    # ─── Appalto integrato (R46, R47) ─────────────────────────────────────────
    appalto_integrato: bool = False
    appalto_integrato_evidence: Optional[str] = None
    giovane_professionista_richiesto: Literal["yes", "no", "unknown"] = "unknown"

    # ─── Offerta tecnica (R48, R49) ───────────────────────────────────────────
    tech_offer_divieto_prezzi_pena_esclusione: bool = False
    tech_offer_max_pagine: Optional[int] = None
    criteri_valutazione: List[Criterio] = Field(default_factory=list)
    vincoli_speciali: List[str] = Field(default_factory=list)

    # ─── Vincoli esecutivi (R51, R52, M1) ────────────────────────────────────
    start_lavori_tassativo: Optional[str] = None
    vincoli_esecutivi: List[str] = Field(default_factory=list)
    quinto_obbligo: bool = False
    revisione_prezzi_soglia_pct: Optional[float] = None

    # ─── EOI specifici (R22, R23, R58, R59) ──────────────────────────────────
    eoi_invited_count_target: Optional[int] = None
    eoi_selection_criteria: List[str] = Field(default_factory=list)
    sa_reserve_rights: bool = False

    # ─── D11-D20: Sistema Qualificazione ─────────────────────────────────────
    # D12
    qualification_requirements_on_submission: bool = False
    qualification_integration_only_if_owned: bool = False
    # D13
    qualification_missing_docs_deadline_days: Optional[int] = None
    qualification_failure_effect: Optional[str] = None
    # D14
    maintenance_variation_types: List[Dict[str, Any]] = Field(default_factory=list)
    # D15
    maintenance_renewal_cycle_years: int = 3
    maintenance_submit_months_before: int = 6
    maintenance_timely_extends_validity: bool = False
    qualification_expiry_date: Optional[str] = None
    # D16
    psf_min_threshold: Optional[Any] = None   # float o "in_normativa_sottosistema"
    psf_below_threshold_effect: Optional[str] = None
    psf_exception_concordato: bool = False
    # D17
    financial_min_bilanci_applicant: int = 1
    financial_min_bilanci_auxiliary: int = 2
    financial_annual_update_required: bool = False
    # D18
    avvalimento_non_frazionabili: List[str] = Field(default_factory=list)
    avvalimento_no_cascade: bool = True
    # D19
    interpello_class_type: Optional[str] = None
    interpello_cap_rule: Optional[str] = None
    rete_soggettivita_giuridica_required: bool = False
    # D20
    qualification_fee_required: bool = False
    qualification_fee_amounts: List[Dict[str, Any]] = Field(default_factory=list)
    qualification_site_visit_possible: bool = False

    # ─── D21-D23: PPP / Grandi Opere ─────────────────────────────────────────
    # D21
    procedure_multi_stage: bool = False
    procedure_stages: List[Dict[str, Any]] = Field(default_factory=list)
    # D22
    ppp_private_share_percent: Optional[float] = None
    ppp_private_contribution_amount: Optional[float] = None
    ppp_spv_required: bool = False
    ppp_governance_constraints: Optional[str] = None
    # D23
    security_special_regime: bool = False
    security_reference_text: Optional[str] = None
    security_admission_impact: Literal["esclusione", "condizione_esecutiva", "info"] = "info"

    class Config:
        validate_assignment = True
        str_strip_whitespace = True


# ══════════════════════════════════════════════════════════
# TenderProfile (struttura avanzata — output LLM v4.0)
# ══════════════════════════════════════════════════════════

class Deadline(BaseModel):
    dtype: str
    datetime_str: Optional[str] = None
    timezone: str = "Europe/Rome"
    is_mandatory: bool = False
    exclusion_if_missed: bool = False
    evidence: Optional[Evidence] = None

class WorksAmounts(BaseModel):
    total_amount_eur: Optional[float] = None
    works_amount_eur: Optional[float] = None
    services_amount_eur: Optional[float] = None
    safety_costs_eur: Optional[float] = None
    design_amount_eur: Optional[float] = None
    evidence: Optional[Evidence] = None