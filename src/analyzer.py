"""
BidPilot v4.0 — Analyzer
Orchestratore: PDF → BandoRequisiti v4.0 → DecisionReport
Motori: gara ordinaria / qualificazione (D11) / PPP multi-stage (D21)
"""
from __future__ import annotations
import json
from datetime import datetime
from typing import Dict, Any

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from src.schemas import (
    BandoRequisiti, CompanyProfile, SOAAttestation, Certification,
    TurnoverEntry, SectorTurnoverEntry, SimilarWork, Designer, StaffRole,
    LegalRepresentative, CameralRegistration, DecisionReport
)
from src.prompts import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT
from src.decision_engine import produce_decision_report

# Validazione geografica anti-allucinazione
GEO_VALIDATION = {
    "roma": "lazio", "milano": "lombardia", "torino": "piemonte",
    "napoli": "campania", "palermo": "sicilia", "genova": "liguria",
    "bologna": "emilia-romagna", "firenze": "toscana", "bari": "puglia",
    "venezia": "veneto", "verona": "veneto", "padova": "veneto",
    "trieste": "friuli-venezia giulia", "trento": "trentino",
    "perugia": "umbria", "ancona": "marche", "cagliari": "sardegna",
    "catania": "sicilia", "messina": "sicilia"
}


class BandoAnalyzer:
    """
    Analizzatore bandi v4.0 — Libreria Requisiti v2.1 (84 requisiti).

    Flusso:
      1. Estrazione strutturata dal testo (LLM → BandoRequisiti v4.0)
      2. Validazione anti-allucinazione geografica
      3. Build CompanyProfile dal JSON di configurazione
      4. Decision engine → DecisionReport
         - Engine qualificazione se is_qualification_system
         - Engine PPP se procedure_multi_stage
         - Engine gara altrimenti
    """

    def __init__(self, openai_api_key: str,
                 profilo_path: str = "config/profilo_azienda.json"):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=openai_api_key)
        with open(profilo_path, "r", encoding="utf-8") as f:
            self._raw_profile = json.load(f)

    # ──────────────────────────────────────────────────────
    # 1. Estrazione dal PDF
    # ──────────────────────────────────────────────────────

    def extract_requirements(self, bando_text: str) -> BandoRequisiti:
        MAX_LENGTH = 300_000
        if len(bando_text) > MAX_LENGTH:
            half = MAX_LENGTH // 2
            bando_text = (
                bando_text[:half]
                + "\n\n[...DOCUMENTO TRONCATO — SEZIONE CENTRALE OMESSA...]\n\n"
                + bando_text[-half:]
            )
        prompt = ChatPromptTemplate.from_messages([
            ("system", EXTRACTION_SYSTEM_PROMPT),
            ("user", EXTRACTION_USER_PROMPT),
        ])
        structured_llm = self.llm.with_structured_output(BandoRequisiti)
        chain = prompt | structured_llm
        try:
            requisiti: BandoRequisiti = chain.invoke({"bando_text": bando_text})
            self._validate_geo(requisiti)
            return requisiti
        except Exception as e:
            raise RuntimeError(f"Errore estrazione bando: {e}") from e

    def _validate_geo(self, req: BandoRequisiti) -> None:
        if req.comune_stazione_appaltante and req.regione_stazione_appaltante:
            comune = req.comune_stazione_appaltante.lower().strip()
            regione = req.regione_stazione_appaltante.lower().strip()
            expected = GEO_VALIDATION.get(comune)
            if expected and expected not in regione:
                raise ValueError(
                    f"INCOERENZA GEOGRAFICA: comune '{req.comune_stazione_appaltante}' "
                    f"non può essere in regione '{req.regione_stazione_appaltante}'"
                )

    # ──────────────────────────────────────────────────────
    # 2. Build CompanyProfile da JSON
    # ──────────────────────────────────────────────────────

    def _build_company_profile(self) -> CompanyProfile:
        raw = self._raw_profile

        soa_list = [
            SOAAttestation(
                category=s.get("categoria", ""),
                soa_class=s.get("classifica", ""),
                expiry_date=s.get("scadenza", ""),
                issue_date=s.get("data_emissione", ""),
                notes=s.get("note", "")
            )
            for s in raw.get("soa_possedute", [])
        ]

        cert_list = [
            Certification(
                cert_type=c.get("tipo", ""),
                valid=True,
                scope=c.get("descrizione", ""),
                expiry_date=c.get("scadenza", "")
            )
            for c in raw.get("certificazioni", [])
            if c.get("tipo", "").upper() not in ("SOA",)
        ]

        fat = raw.get("fatturato", {})
        turnover, sector_turnover = [], []
        for year_key, data in fat.items():
            try:
                y = int(year_key.replace("anno_", ""))
            except Exception:
                continue
            turnover.append(TurnoverEntry(year=y, amount_eur=data.get("totale", 0)))
            for k, v in data.items():
                if k != "totale" and isinstance(v, (int, float)):
                    sector_turnover.append(SectorTurnoverEntry(year=y, sector=k, amount_eur=v))

        lr = raw.get("legale_rappresentante", {})
        legal_rep = LegalRepresentative(
            name=lr.get("nome", raw.get("nome_azienda", "")),
            role=lr.get("ruolo", "Legale Rappresentante"),
            has_digital_signature=lr.get("firma_digitale", True),
            signing_powers_proof=lr.get("poteri_firma", "available")
        )

        cciaa_data = raw.get("cciaa", {})
        cameral = CameralRegistration(
            is_registered=cciaa_data.get("iscritta", True),
            rea_number=cciaa_data.get("rea", ""),
            ateco_codes=cciaa_data.get("ateco", []),
            business_scope_text=raw.get("settore_principale", ""),
            coherence_with_tender_object="unknown"
        )

        key_roles = [StaffRole(role=f, available=True)
                     for f in raw.get("figure_professionali_interne", [])]

        design_team = [
            Designer(
                name=d.get("nome", ""),
                profession=d.get("professione", ""),
                order_registration=d.get("albo", "unknown"),
                license_date=d.get("data_abilitazione", ""),
                young_professional=d.get("giovane_professionista", "unknown")
            )
            for d in raw.get("progettisti", [])
        ]

        return CompanyProfile(
            legal_name=raw.get("nome_azienda", ""),
            registered_office=raw.get("sede", ""),
            soa_attestations=soa_list,
            certifications=cert_list,
            turnover_by_year=sorted(turnover, key=lambda x: x.year, reverse=True),
            sector_turnover_by_year=sorted(sector_turnover, key=lambda x: x.year, reverse=True),
            legal_representative=legal_rep,
            cameral_registration=cameral,
            key_roles=key_roles,
            design_team=design_team,
            has_inhouse_design=raw.get("progettazione_interna", False),
            external_designers_available="yes" if design_team else "unknown",
            willing_rti=raw.get("partecipazione", {}).get("rti", True),
            willing_avvalimento=raw.get("partecipazione", {}).get("avvalimento", True),
            willing_subcontract=raw.get("partecipazione", {}).get("subappalto", True),
            operating_regions=raw.get("aree_geografiche", []),
            start_date_constraints=raw.get("vincoli_inizio_lavori", ""),
            ccnl_applied=raw.get("ccnl_applicato", ""),
            has_credit_license=raw.get("patente_crediti", "unknown"),
            deposited_statements_count=raw.get("bilanci_depositati", 0),
        )

    # ──────────────────────────────────────────────────────
    # 3. Entry point principale
    # ──────────────────────────────────────────────────────

    def analyze_bando(self, bando_text: str) -> Dict[str, Any]:
        bando = self.extract_requirements(bando_text)
        company = self._build_company_profile()
        report: DecisionReport = produce_decision_report(bando, company)
        legacy = self._build_legacy(bando, company, report)
        return {
            "decision_report": report,
            "requisiti_estratti": bando.model_dump(),
            "company_profile": company.model_dump(),
            "legacy": legacy,
        }

    def _build_legacy(self, bando: BandoRequisiti,
                      company: CompanyProfile,
                      report: DecisionReport) -> Dict[str, Any]:
        # Check geografico
        in_zona = False
        if bando.regione_stazione_appaltante:
            reg = bando.regione_stazione_appaltante.strip().title()
            in_zona = any(reg in area for area in company.operating_regions)
        geo = {
            "in_zona": in_zona,
            "motivo": (
                f"Bando in {bando.regione_stazione_appaltante or '?'}"
                + (" — area operativa ✓" if in_zona else " — FUORI aree abituali")
            ),
            "warning": not in_zona and bool(bando.regione_stazione_appaltante)
        }

        # Scadenze legacy
        from src.requirements_engine import _parse_date, _today
        scad_dict: Dict[str, list] = {"critiche": [], "prossime": [], "ok": [], "scadute": []}
        for sc in bando.scadenze:
            if not sc.data:
                continue
            d = _parse_date(sc.data)
            if d is None:
                continue
            giorni = (d - _today()).days
            info = {"tipo": sc.tipo, "data": sc.data, "ora": sc.ora,
                    "note": sc.note, "giorni_mancanti": giorni}
            if giorni < 0:
                scad_dict["scadute"].append(info)
            elif giorni <= 2:
                scad_dict["critiche"].append(info)
            elif giorni <= 7:
                scad_dict["prossime"].append(info)
            else:
                scad_dict["ok"].append(info)

        from src.schemas import ReqStatus, Severity
        ko_count = sum(1 for r in report.requirements_results
                       if r.status == ReqStatus.KO and r.severity == Severity.HARD_KO)
        ok_count = sum(1 for r in report.requirements_results if r.status == ReqStatus.OK)
        total = len(report.requirements_results) or 1
        score_sec = max(0, min(100, int(100 * ok_count / total) - ko_count * 20))

        verdict_map = {
            "GO": "PARTECIPARE",
            "GO_HIGH_RISK": "PARTECIPARE CON CAUTELA",
            "GO_WITH_STRUCTURE": "PARTECIPARE CON STRUTTURA",
            "NO_GO": "NON PARTECIPARE",
            "ELIGIBLE_QUALIFICATION": "ELIGIBLE — QUALIFICAZIONE",
            "NOT_ELIGIBLE_QUALIFICATION": "NON ELIGIBLE — QUALIFICAZIONE",
            "ELIGIBLE_STAGE1": "ELIGIBLE STAGE 1 — PPP",
        }
        legacy_dec = verdict_map.get(report.verdict.status.value, "PARTECIPARE CON CAUTELA")

        # Nota engine mode
        engine_note = ""
        if report.engine_mode == "qualificazione":
            engine_note = f"⚙️ Engine QUALIFICAZIONE attivato ({bando.qualification_system_owner or 'N/D'})"
        elif report.engine_mode == "ppp_multistage":
            engine_note = "⚙️ Engine PPP MULTI-STAGE attivato"

        return {
            "requisiti_estratti": bando.model_dump(),
            "check_geografico": geo,
            "scadenze": scad_dict,
            "decisione": legacy_dec,
            "punteggio_fattibilita": score_sec,
            "motivi_punteggio": [r.message for r in report.top_reasons],
            "engine_mode": report.engine_mode,
            "engine_note": engine_note,
            "profile_confidence": report.verdict.profile_confidence,
        }