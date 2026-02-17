"""
BidPilot v3.1 - Schemi Pydantic
CHANGES v3.1:
  - SOACategoria: aggiunto campo `inferred` (categoria identificata per inferenza)
  - BandoRequisiti: aggiunti campi manodopera e divieto subappalto per categorie
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
    OK      = "OK"
    KO      = "KO"
    FIXABLE = "FIXABLE"
    UNKNOWN = "UNKNOWN"

class VerdictStatus(str, Enum):
    NO_GO             = "NO_GO"
    GO_WITH_STRUCTURE = "GO_WITH_STRUCTURE"
    GO_HIGH_RISK      = "GO_HIGH_RISK"
    GO                = "GO"


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
    category: str          # es. "OG1"
    soa_class: str         # "I" … "VIII"
    expiry_date: str       # YYYY-MM-DD
    issue_date: str = ""
    notes: str = ""

class Certification(BaseModel):
    cert_type: str         # "ISO9001", "ISO14001", …
    valid: bool = True
    scope: str = ""
    issuer: str = ""
    expiry_date: str = ""  # YYYY-MM-DD

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


# ══════════════════════════════════════════════════════════
# TENDER PROFILE  (estratto dal PDF)
# ══════════════════════════════════════════════════════════

class Evidence(BaseModel):
    quote: str = ""
    page: int = 0
    section: str = ""

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

class PrevalentCategory(BaseModel):
    category: str
    amount_eur: Optional[float] = None
    percentage: Optional[float] = None
    required_class: str = ""
    notes: str = ""
    evidence: Optional[Evidence] = None

class ScorporabileCategory(BaseModel):
    category: str
    amount_eur: Optional[float] = None
    percentage: Optional[float] = None
    qualification_required: bool = True
    is_sios: Literal["yes", "no", "unknown"] = "unknown"
    subcontract_allowed: Literal["yes", "no", "limited", "unknown"] = "unknown"
    notes: str = ""
    evidence: Optional[Evidence] = None

class ParticipationForms(BaseModel):
    allowed: List[str] = Field(default_factory=list)
    rti_rules_summary: str = ""
    avvalimento_rules_summary: str = ""
    subcontract_rules_summary: str = ""
    subcontract_max_pct: Optional[float] = None
    avvalimento_excluded_reqs: List[str] = Field(default_factory=list)
    evidence: Optional[Evidence] = None

class DesignRequirements(BaseModel):
    is_design_build: Literal["yes", "no", "unknown"] = "unknown"
    requires_design_team: Literal["yes", "no", "unknown"] = "unknown"
    requires_young_professional: Literal["yes", "no", "unknown"] = "unknown"
    required_disciplines: List[str] = Field(default_factory=list)
    evidence: Optional[Evidence] = None

class ProceduralKiller(BaseModel):
    pktype: str
    is_mandatory: bool = False
    deadline: Optional[str] = None
    evidence: Optional[Evidence] = None

class ExecutionConstraint(BaseModel):
    ectype: str
    date: Optional[str] = None
    hardness: Literal["hard", "soft"] = "soft"
    description: str = ""
    evidence: Optional[Evidence] = None

class ExtractionConfidence(BaseModel):
    overall: float = 0.0
    by_section: Dict[str, float] = Field(default_factory=dict)
    missing_sections: List[str] = Field(default_factory=list)

class TenderProfile(BaseModel):
    title: str = ""
    contracting_authority: str = ""
    cig: str = ""
    cup: str = ""
    procedure_type: str = ""
    platform: str = ""
    lots: int = 1
    deadlines: List[Deadline] = Field(default_factory=list)
    amounts: WorksAmounts = Field(default_factory=WorksAmounts)
    prevalent_category: Optional[PrevalentCategory] = None
    scorporabili: List[ScorporabileCategory] = Field(default_factory=list)
    participation_forms: ParticipationForms = Field(default_factory=ParticipationForms)
    certifications_required: List[str] = Field(default_factory=list)
    min_turnover_eur: Optional[float] = None
    min_sector_turnover_eur: Optional[float] = None
    design_requirements: DesignRequirements = Field(default_factory=DesignRequirements)
    procedural_killers: List[ProceduralKiller] = Field(default_factory=list)
    anac_fee_required: Literal["yes", "no", "unknown"] = "unknown"
    execution_constraints: List[ExecutionConstraint] = Field(default_factory=list)
    provvisoria_required: Literal["yes", "no", "unknown"] = "unknown"
    provvisoria_amount_eur: Optional[float] = None
    provvisoria_pct: Optional[float] = None
    comune: str = ""
    provincia: str = ""
    regione: str = ""
    luogo_esecuzione: str = ""
    extraction_confidence: ExtractionConfidence = Field(default_factory=ExtractionConfidence)


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
    tender_profile: Optional[TenderProfile] = None


# ══════════════════════════════════════════════════════════
# LEGACY: BandoRequisiti — schema usato dall'estrazione LLM
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
    importo_categoria: Optional[float] = None   # importo specifico della categoria (non totale appalto)
    inferred: bool = False                        # NEW v3.1: True se categoria identificata per inferenza
    evidence: Optional[str] = None

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

class BandoRequisiti(BaseModel):
    """Schema usato dall'LLM per l'estrazione strutturata dal PDF"""
    oggetto_appalto: str
    oggetto_evidence: Optional[str] = None

    stazione_appaltante: str
    stazione_evidence: Optional[str] = None

    importo_lavori: Optional[float] = None
    importo_evidence: Optional[str] = None
    importo_base_gara: Optional[float] = None
    oneri_sicurezza: Optional[float] = None

    comune_stazione_appaltante: Optional[str] = None
    provincia_stazione_appaltante: Optional[str] = None
    regione_stazione_appaltante: Optional[str] = None
    luogo_esecuzione: Optional[str] = None

    codice_cup: Optional[str] = None
    codice_cig: Optional[str] = None

    tipo_procedura: Optional[str] = None
    criterio_aggiudicazione: Optional[str] = None
    punteggio_tecnico: Optional[float] = None
    punteggio_economico: Optional[float] = None

    scadenze: List[Scadenza] = Field(default_factory=list)
    soa_richieste: List[SOACategoria] = Field(default_factory=list)
    certificazioni_richieste: List[str] = Field(default_factory=list)
    figure_professionali_richieste: List[FiguraProfessionale] = Field(default_factory=list)
    criteri_valutazione: List[Criterio] = Field(default_factory=list)
    vincoli_speciali: List[str] = Field(default_factory=list)
    garanzie_richieste: Optional[Garanzie] = None

    # CAMPI v3.0
    sopralluogo_obbligatorio: bool = False
    sopralluogo_evidence: Optional[str] = None
    anac_contributo_richiesto: Literal["yes", "no", "unknown"] = "unknown"
    avvalimento_ammesso: Literal["yes", "no", "unknown"] = "unknown"
    avvalimento_regole: Optional[str] = None
    rti_ammesso: Literal["yes", "no", "unknown"] = "unknown"
    rti_regole: Optional[str] = None
    subappalto_percentuale_max: Optional[float] = None
    subappalto_regole: Optional[str] = None
    appalto_integrato: bool = False
    appalto_integrato_evidence: Optional[str] = None
    giovane_professionista_richiesto: Literal["yes", "no", "unknown"] = "unknown"
    vincoli_esecutivi: List[str] = Field(default_factory=list)
    start_lavori_tassativo: Optional[str] = None
    piattaforma_gara: Optional[str] = None
    fatturato_minimo_richiesto: Optional[float] = None
    fatturato_specifico_richiesto: Optional[float] = None

    # NUOVI CAMPI v3.1 — Manodopera
    costi_manodopera_indicati: bool = False
    costi_manodopera_eur: Optional[float] = None
    costi_manodopera_soggetti_ribasso: bool = False
    costi_manodopera_evidence: Optional[str] = None

    # NUOVI CAMPI v3.1 — Divieto subappalto per categoria
    subappalto_vietato_categorie: List[str] = Field(default_factory=list)
    subappalto_vietato_evidence: Optional[str] = None

    class Config:
        validate_assignment = True
        str_strip_whitespace = True