"""
BidPilot v3.0 — Analyzer
Orchestratore: PDF → BandoRequisiti → CompanyProfile → DecisionReport
"""
from __future__ import annotations
import json
from datetime import datetime
from typing import Dict, Any, Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from src.schemas import BandoRequisiti, CompanyProfile, SOAAttestation, Certification
from src.schemas import TurnoverEntry, SectorTurnoverEntry, SimilarWork, Designer, StaffRole
from src.schemas import LegalRepresentative, CameralRegistration, DecisionReport
from src.prompts import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT
from src.decision_engine import produce_decision_report


# Mapping comuni → regioni per validazione geografica
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
    Analizzatore bandi v3.0 con decision engine a 4 stati.
    
    Flusso:
      1. Estrazione strutturata dal testo (LLM → BandoRequisiti)
      2. Validazione anti-allucinazione geografica
      3. Build CompanyProfile dal JSON di configurazione
      4. Decision engine deterministico → DecisionReport
    """

    def __init__(self, openai_api_key: str,
                 profilo_path: str = "config/profilo_azienda.json"):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=openai_api_key
        )
        with open(profilo_path, "r", encoding="utf-8") as f:
            self._raw_profile = json.load(f)

    # ──────────────────────────────────────────────────────
    # 1. Estrazione dal PDF
    # ──────────────────────────────────────────────────────

    def extract_requirements(self, bando_text: str) -> BandoRequisiti:
        """Estrae struttura BandoRequisiti usando GPT-4o-mini con structured output."""
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
        """Blocca incoerenze geografiche (anti-allucinazione)."""
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
        """Converte il JSON di configurazione in CompanyProfile strutturato."""
        raw = self._raw_profile

        # SOA
        soa_list = []
        for s in raw.get("soa_possedute", []):
            soa_list.append(SOAAttestation(
                category=s.get("categoria", ""),
                soa_class=s.get("classifica", ""),
                expiry_date=s.get("scadenza", ""),
                issue_date=s.get("data_emissione", ""),
                notes=s.get("note", "")
            ))

        # Certificazioni
        cert_list = []
        for c in raw.get("certificazioni", []):
            tipo = c.get("tipo", "")
            if tipo.upper() in ("SOA",):  # non è una cert ISO
                continue
            cert_list.append(Certification(
                cert_type=tipo,
                valid=True,
                scope=c.get("descrizione", ""),
                expiry_date=c.get("scadenza", "")
            ))

        # Fatturati
        turnover = []
        sector_turnover = []
        fat = raw.get("fatturato", {})
        for year_key, data in fat.items():
            try:
                y = int(year_key.replace("anno_", ""))
            except Exception:
                continue
            totale = data.get("totale", 0)
            turnover.append(TurnoverEntry(year=y, amount_eur=totale))
            settore_principale = raw.get("settore_principale", "")
            for k, v in data.items():
                if k != "totale" and isinstance(v, (int, float)):
                    sector_turnover.append(SectorTurnoverEntry(year=y, sector=k, amount_eur=v))

        # Rappresentante legale
        lr = raw.get("legale_rappresentante", {})
        legal_rep = LegalRepresentative(
            name=lr.get("nome", raw.get("nome_azienda", "")),
            role=lr.get("ruolo", "Legale Rappresentante"),
            has_digital_signature=lr.get("firma_digitale", True),
            signing_powers_proof=lr.get("poteri_firma", "available")
        )

        # CCIAA
        cciaa_data = raw.get("cciaa", {})
        cameral = CameralRegistration(
            is_registered=cciaa_data.get("iscritta", True),
            rea_number=cciaa_data.get("rea", ""),
            ateco_codes=cciaa_data.get("ateco", []),
            business_scope_text=raw.get("settore_principale", ""),
            coherence_with_tender_object="unknown"
        )

        # Figure chiave
        key_roles = []
        for f in raw.get("figure_professionali_interne", []):
            key_roles.append(StaffRole(role=f, available=True))

        # Progettisti
        design_team = []
        for d in raw.get("progettisti", []):
            design_team.append(Designer(
                name=d.get("nome", ""),
                profession=d.get("professione", ""),
                order_registration=d.get("albo", "unknown"),
                license_date=d.get("data_abilitazione", ""),
                young_professional=d.get("giovane_professionista", "unknown")
            ))

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
            bank_references_available="unknown",
            cel_records_available="unknown",
        )

    # ──────────────────────────────────────────────────────
    # 3. Entry point principale
    # ──────────────────────────────────────────────────────

    def analyze_bando(self, bando_text: str) -> Dict[str, Any]:
        """
        Pipeline completa:
          bando_text → BandoRequisiti → DecisionReport (v3.0)

        Restituisce dict con:
          - decision_report: DecisionReport
          - requisiti_estratti: dict (raw BandoRequisiti)
          - company_profile: dict (CompanyProfile)
          - legacy: dict compatibilità UI v2
        """
        # Estrazione
        bando = self.extract_requirements(bando_text)

        # Profilo aziendale
        company = self._build_company_profile()

        # Decision engine
        report: DecisionReport = produce_decision_report(bando, company)

        # Compatibilità legacy per UI
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
        """Costruisce struttura legacy per retrocompatibilità con la UI v2."""
        # Check geografico
        in_zona = False
        if bando.regione_stazione_appaltante:
            regione_norm = bando.regione_stazione_appaltante.strip().title()
            in_zona = any(regione_norm in area for area in company.operating_regions)
        
        geo = {
            "in_zona": in_zona,
            "motivo": (
                f"Bando in {bando.regione_stazione_appaltante or '?'}"
                + (", area operativa ✓" if in_zona else " — FUORI aree abituali")
            ),
            "warning": not in_zona and bool(bando.regione_stazione_appaltante)
        }

        # Scadenze legacy
        from src.requirements_engine import _parse_date, _today
        scad_dict = {"critiche": [], "prossime": [], "ok": [], "scadute": []}
        for sc in bando.scadenze:
            if not sc.data:
                continue
            d = _parse_date(sc.data)
            if d is None:
                continue
            giorni = (d - _today()).days
            info = {
                "tipo": sc.tipo, "data": sc.data, "ora": sc.ora,
                "note": sc.note, "giorni_mancanti": giorni
            }
            if giorni < 0:
                scad_dict["scadute"].append(info)
            elif giorni <= 2:
                scad_dict["critiche"].append(info)
            elif giorni <= 7:
                scad_dict["prossime"].append(info)
            else:
                scad_dict["ok"].append(info)

        # SOA legacy (da requirements_results)
        from src.schemas import ReqStatus, Severity
        soa_v = {"verdi": [], "gialli": [], "rossi": []}
        cert_v = {"verdi": [], "gialli": [], "rossi": []}
        fig_v = {"verdi": [], "gialli": [], "rossi": []}

        for r in report.requirements_results:
            if r.req_id.startswith("C") and "SOA" in r.name:
                item = {"categoria": r.name, "motivo": r.user_message, **r.fixability.model_dump()}
                if r.status == ReqStatus.OK:
                    soa_v["verdi"].append(item)
                elif r.status in (ReqStatus.KO, ReqStatus.FIXABLE):
                    soa_v["rossi"].append(item)
            elif r.req_id.startswith("D"):
                item = {"tipo": r.name, "motivo": r.user_message}
                if r.status == ReqStatus.OK:
                    cert_v["verdi"].append(item)
                elif r.status == ReqStatus.KO:
                    cert_v["rossi"].append(item)
                else:
                    cert_v["gialli"].append(item)

        # Mappa verdetto → legacy
        verdict_map = {
            "GO": "PARTECIPARE",
            "GO_HIGH_RISK": "PARTECIPARE CON CAUTELA",
            "GO_WITH_STRUCTURE": "PARTECIPARE CON STRUTTURA",
            "NO_GO": "NON PARTECIPARE"
        }
        legacy_dec = verdict_map.get(report.verdict.status.value, "PARTECIPARE CON CAUTELA")

        # Score secondario (per barra progresso)
        ko_count = sum(1 for r in report.requirements_results
                       if r.status == ReqStatus.KO and r.severity == Severity.HARD_KO)
        fix_count = sum(1 for r in report.requirements_results
                        if r.status == ReqStatus.FIXABLE)
        ok_count = sum(1 for r in report.requirements_results
                       if r.status == ReqStatus.OK)
        total = len(report.requirements_results) or 1
        score_sec = max(0, min(100, int(100 * ok_count / total) - ko_count * 20))

        return {
            "requisiti_estratti": bando.model_dump(),
            "check_geografico": geo,
            "scadenze": scad_dict,
            "soa": soa_v,
            "certificazioni": cert_v,
            "figure_professionali": fig_v,
            "decisione": legacy_dec,
            "punteggio_fattibilita": score_sec,
            "motivi_punteggio": [r.message for r in report.top_reasons],
        }