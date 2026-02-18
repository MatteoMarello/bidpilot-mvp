"""
BidPilot — Analyzer  v2.0
==========================
Implementa:
  B.  Evidence obbligatoria per campi critici → None/UNKNOWN se mancante.
  C.  Validazioni post-estrazione (guardrail):
       - ogni SOA estratta deve avere evidence non vuota
       - date non parsabili → None (mai "aggiustate")
       - importi senza evidence → None (mai stimati)
  Produce BandoRequisiti validato da ParsedDocument.

Regola assoluta:
  NO evidence → NO assert → campo a None (degrada a UNKNOWN/RISK nell'engine).

Il modulo NON chiama mai l'LLM: è puro Python deterministico.
Questo lo rende completamente testabile senza API.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    from schemas import BandoRequisiti, Scadenza, SOACategoria
    _HAS_PYDANTIC = True
except (ImportError, ModuleNotFoundError):
    _HAS_PYDANTIC = False
    from dataclasses import dataclass as _dc, field as _f

    @_dc
    class Scadenza:  # type: ignore
        tipo: str = ""
        data: "Optional[str]" = None
        ora: "Optional[str]" = None
        obbligatorio: bool = False
        evidence: "Optional[str]" = None
        note: "Optional[str]" = None
        esclusione_se_mancante: bool = False

    @_dc
    class SOACategoria:  # type: ignore
        categoria: str = ""
        descrizione: str = ""
        classifica: str = ""
        prevalente: bool = False
        is_scorporabile: bool = False
        qualificazione_obbligatoria: bool = True
        importo_categoria: "Optional[float]" = None
        evidence: "Optional[str]" = None

    @_dc
    class BandoRequisiti:  # type: ignore
        oggetto_appalto: str = "UNKNOWN"
        stazione_appaltante: str = "UNKNOWN"
        codice_cig: "Optional[str]" = None
        cig_evidence: "Optional[str]" = None
        importo_lavori: "Optional[float]" = None
        importo_base_gara: "Optional[float]" = None
        importo_evidence: "Optional[str]" = None
        oneri_sicurezza: "Optional[float]" = None
        scadenze: list = _f(default_factory=list)
        soa_richieste: list = _f(default_factory=list)
        canale_invio: str = "unknown"
        piattaforma_gara: "Optional[str]" = None
        piattaforma_evidence: "Optional[str]" = None
        certificazioni_richieste: list = _f(default_factory=list)

        @property
        def model_fields(self):
            import dataclasses
            return {f.name: None for f in dataclasses.fields(self)}

logger = logging.getLogger("bidpilot.analyzer")


# ══════════════════════════════════════════════════════════════════════════════
# TIPI DI OUTPUT
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class GuardrailViolation:
    """Una violazione di guardrail rilevata durante la validazione."""
    field: str
    reason: str
    original_value: Any
    corrected_value: Any  # None o "UNKNOWN" dopo la correzione

    def __str__(self) -> str:
        orig = repr(self.original_value)[:80]
        return f"[GUARDRAIL] {self.field}: {self.reason} (era: {orig} → ora: {repr(self.corrected_value)})"


@dataclass
class AnalysisResult:
    """Output di analyze(): BandoRequisiti + lista di violazioni di guardrail."""
    bando: BandoRequisiti
    violations: List[GuardrailViolation] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def has_critical_unknowns(self) -> bool:
        """True se almeno uno dei 5 campi critici è None/UNKNOWN."""
        b = self.bando
        return any([
            b.codice_cig is None,
            b.importo_lavori is None and b.importo_base_gara is None,
            not _has_scadenza_offerta(b),
            not b.soa_richieste,
            b.canale_invio == "unknown",
        ])

    def summary(self) -> str:
        lines = [
            f"CIG: {self.bando.codice_cig or 'UNKNOWN'}",
            f"Importo lavori: {self.bando.importo_lavori or 'UNKNOWN'}",
            f"Scadenza offerta: {_scadenza_offerta_str(self.bando)}",
            f"SOA richieste: {len(self.bando.soa_richieste)} categorie",
            f"Piattaforma: {self.bando.piattaforma_gara or 'UNKNOWN'} (canale: {self.bando.canale_invio})",
            f"Violations: {len(self.violations)}",
            f"Warnings: {len(self.warnings)}",
        ]
        return "\n".join(lines)


def _has_scadenza_offerta(bando: BandoRequisiti) -> bool:
    return any(
        s.tipo in ("presentazione_offerta", "presentazione offerta", "offerta")
        and s.data is not None
        for s in bando.scadenze
    )


def _scadenza_offerta_str(bando: BandoRequisiti) -> str:
    for s in bando.scadenze:
        if s.tipo in ("presentazione_offerta", "presentazione offerta", "offerta") and s.data:
            return f"{s.data} {s.ora or ''}".strip()
    return "UNKNOWN"


# ══════════════════════════════════════════════════════════════════════════════
# B — EVIDENCE GUARDRAIL
# ══════════════════════════════════════════════════════════════════════════════

def _guardrail_cig(fields: dict) -> Tuple[Optional[str], Optional[str], Optional[GuardrailViolation]]:
    """
    B — CIG: se cig_evidence è None/vuota → codice_cig = None.
    Restituisce (codice_cig, cig_evidence, violation_or_None).
    """
    cig = fields.get("codice_cig")
    evidence = fields.get("cig_evidence")

    if cig and not evidence:
        return None, None, GuardrailViolation(
            field="codice_cig",
            reason="CIG estratto senza evidence testuale (possibile allucinazione)",
            original_value=cig,
            corrected_value=None,
        )

    # Valida formato CIG: 10 caratteri alfanumerici
    if cig and not re.fullmatch(r"[A-Z0-9]{10}", cig.upper().replace("-", "").replace(" ", "")):
        # Prova a normalizzare
        cig_norm = re.sub(r"[^A-Z0-9]", "", cig.upper())
        if len(cig_norm) == 10:
            cig = cig_norm
        else:
            return None, None, GuardrailViolation(
                field="codice_cig",
                reason=f"Formato CIG non valido (atteso 10 alfanumerici, trovato '{cig}')",
                original_value=cig,
                corrected_value=None,
            )

    return cig, evidence, None


def _guardrail_importo(fields: dict) -> Tuple[Optional[float], Optional[str], Optional[GuardrailViolation]]:
    """
    B — Importo: se importo_evidence è None → importo_lavori = importo_base_gara = None.
    """
    importo = fields.get("importo_lavori") or fields.get("importo_base_gara")
    evidence = fields.get("importo_evidence")

    if importo and not evidence:
        return None, None, GuardrailViolation(
            field="importo_lavori",
            reason="Importo estratto senza evidence testuale (possibile allucinazione)",
            original_value=importo,
            corrected_value=None,
        )

    # Sanity check: importo negativo o irrealisticamente alto
    if importo is not None:
        try:
            importo_f = float(importo)
        except (TypeError, ValueError):
            return None, None, GuardrailViolation(
                field="importo_lavori",
                reason=f"Importo non numerico: '{importo}'",
                original_value=importo,
                corrected_value=None,
            )
        if importo_f < 0:
            return None, None, GuardrailViolation(
                field="importo_lavori",
                reason=f"Importo negativo non valido: {importo_f}",
                original_value=importo,
                corrected_value=None,
            )
        if importo_f > 50_000_000_000:  # 50 miliardi: soglia massima ragionevole per IT
            return None, None, GuardrailViolation(
                field="importo_lavori",
                reason=f"Importo irrealistico (> 50B€): {importo_f}",
                original_value=importo,
                corrected_value=None,
            )
        importo = importo_f

    return importo, evidence, None


def _guardrail_piattaforma(fields: dict) -> Tuple[str, Optional[str], Optional[str], Optional[GuardrailViolation]]:
    """
    B — Piattaforma: se piattaforma_evidence è None → canale_invio = 'unknown', piattaforma_gara = None.
    Restituisce (canale_invio, piattaforma_gara, piattaforma_evidence, violation_or_None).
    """
    canale = fields.get("canale_invio", "unknown")
    piattaforma = fields.get("piattaforma_gara")
    evidence = fields.get("piattaforma_evidence")

    if (canale != "unknown" or piattaforma) and not evidence:
        return "unknown", None, None, GuardrailViolation(
            field="canale_invio",
            reason="Canale/piattaforma estratti senza evidence testuale",
            original_value={"canale_invio": canale, "piattaforma_gara": piattaforma},
            corrected_value={"canale_invio": "unknown", "piattaforma_gara": None},
        )

    return canale, piattaforma, evidence, None


# ══════════════════════════════════════════════════════════════════════════════
# C — VALIDAZIONI POST-ESTRAZIONE
# ══════════════════════════════════════════════════════════════════════════════

# Formati data supportati nell'ordine di tentativo
_DATE_FORMATS = [
    "%Y-%m-%d",        # ISO 8601 (atteso)
    "%d/%m/%Y",        # italiano comune
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%Y/%m/%d",
]

# Pattern per date testuali italiane (es. "31 marzo 2025", "1° aprile 2025")
_MONTH_IT = {
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4,
    "maggio": 5, "giugno": 6, "luglio": 7, "agosto": 8,
    "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
}
_DATE_TEXT_RE = re.compile(
    r"\b(\d{1,2})[°º]?\s+(" + "|".join(_MONTH_IT.keys()) + r")\s+(\d{4})\b",
    re.IGNORECASE,
)


def _parse_date_strict(s: Optional[str]) -> Optional[str]:
    """
    C — Parsing date strict: se non parsabile → None (mai "aggiustare").
    Restituisce stringa ISO 8601 (YYYY-MM-DD) o None.
    """
    if not s:
        return None

    s = s.strip()

    # Tenta formati numerici
    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Tenta formato testuale italiano
    m = _DATE_TEXT_RE.search(s)
    if m:
        day = int(m.group(1))
        month = _MONTH_IT[m.group(2).lower()]
        year = int(m.group(3))
        try:
            dt = datetime(year, month, day)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Non parsabile → None (C: non aggiustare)
    logger.debug(f"Data non parsabile (→ None): '{s}'")
    return None


def _validate_scadenze(raw_scadenze: List[dict]) -> Tuple[List[Scadenza], List[GuardrailViolation]]:
    """
    C — Valida le scadenze estratte dall'LLM.
    - data non parsabile → None
    - evidence mancante e data presente → data = None (B)
    - scadenza senza data né evidence → scartata con warning
    """
    result: List[Scadenza] = []
    violations: List[GuardrailViolation] = []

    for raw in raw_scadenze:
        if not isinstance(raw, dict):
            continue

        tipo = raw.get("tipo", "sconosciuto")
        data_raw = raw.get("data")
        ora_raw = raw.get("ora")
        evidence = raw.get("evidence")
        obbligatorio = bool(raw.get("obbligatorio", False))
        note = raw.get("note")
        esclusione = bool(raw.get("esclusione_se_mancante", False))

        # B: se la scadenza presenta offerta è critica e manca evidence → data = None
        is_critical = tipo in ("presentazione_offerta", "presentazione offerta", "offerta")
        if is_critical and data_raw and not evidence:
            violations.append(GuardrailViolation(
                field=f"scadenze[{tipo}].data",
                reason="Scadenza offerta senza evidence testuale",
                original_value=data_raw,
                corrected_value=None,
            ))
            data_raw = None

        # C: parse date strict
        data_parsed = _parse_date_strict(data_raw)
        if data_raw and not data_parsed:
            violations.append(GuardrailViolation(
                field=f"scadenze[{tipo}].data",
                reason=f"Data non parsabile (→ None): '{data_raw}'",
                original_value=data_raw,
                corrected_value=None,
            ))

        # Valida ora (HH:MM)
        ora_clean = None
        if ora_raw:
            if re.fullmatch(r"\d{1,2}:\d{2}", str(ora_raw).strip()):
                ora_clean = str(ora_raw).strip()
            else:
                # tenta estrazione dall'ora raw
                m = re.search(r"\b(\d{1,2}):(\d{2})\b", str(ora_raw))
                if m:
                    ora_clean = f"{int(m.group(1)):02d}:{m.group(2)}"

        result.append(Scadenza(
            tipo=tipo,
            data=data_parsed,
            ora=ora_clean,
            obbligatorio=obbligatorio,
            evidence=evidence or None,
            note=note,
            esclusione_se_mancante=esclusione,
        ))

    return result, violations


def _validate_soa(raw_soa: List[dict]) -> Tuple[List[SOACategoria], List[GuardrailViolation]]:
    """
    C — Valida le SOA estratte dall'LLM.
    - SOA senza evidence → SCARTATA (B+C: verifica letterale nella quote)
    - SOA con categoria non nel formato OG*/OS* → warning
    """
    result: List[SOACategoria] = []
    violations: List[GuardrailViolation] = []

    _SOA_RE = re.compile(r"\b(OG|OS)\s*\d+\b", re.IGNORECASE)

    for raw in raw_soa:
        if not isinstance(raw, dict):
            continue

        categoria = str(raw.get("categoria", "")).strip().upper()
        classifica = str(raw.get("classifica", "")).strip()
        evidence = raw.get("evidence")

        # B+C: evidence obbligatoria — scarta senza
        if not evidence:
            violations.append(GuardrailViolation(
                field=f"soa_richieste[{categoria}]",
                reason="SOA estratta senza evidence testuale — scartata",
                original_value=raw,
                corrected_value=None,
            ))
            continue  # NON aggiungere a result

        # C: verifica che categoria appaia letteralmente nell'evidence
        cat_base = categoria.replace(" ", "").upper()
        evidence_norm = evidence.upper().replace(" ", "")
        if cat_base not in evidence_norm:
            violations.append(GuardrailViolation(
                field=f"soa_richieste[{categoria}].evidence",
                reason=f"Categoria '{categoria}' NON appare letteralmente nell'evidence: '{evidence[:80]}'",
                original_value=evidence,
                corrected_value=None,
            ))
            continue  # SOA potenzialmente allucinata — scarta

        # Formato categoria
        if not _SOA_RE.search(categoria):
            violations.append(GuardrailViolation(
                field=f"soa_richieste[{categoria}].categoria",
                reason=f"Formato categoria non standard (atteso OG*/OS*): '{categoria}'",
                original_value=categoria,
                corrected_value=categoria,  # manteniamo ma segnaliamo
            ))

        result.append(SOACategoria(
            categoria=categoria,
            descrizione=str(raw.get("descrizione", "")),
            classifica=classifica,
            prevalente=bool(raw.get("prevalente", False)),
            is_scorporabile=bool(raw.get("is_scorporabile", False)),
            qualificazione_obbligatoria=bool(raw.get("qualificazione_obbligatoria", True)),
            importo_categoria=raw.get("importo_categoria"),
            evidence=evidence,
        ))

    return result, violations


def _validate_certificazioni(raw_certs: List[str]) -> List[str]:
    """
    C — Deduplicazione e normalizzazione leggera delle certificazioni.
    Non rimuove quelle senza evidence (le certificazioni arrivano come lista di stringhe,
    l'evidence è implicita nel fatto che l'LLM le ha estratte dal contesto mirato).
    """
    seen = set()
    result = []
    for cert in raw_certs:
        if not cert or not isinstance(cert, str):
            continue
        cert_clean = cert.strip()
        cert_key = re.sub(r"[^A-Z0-9]", "", cert_clean.upper())
        if cert_key not in seen and cert_key:
            seen.add(cert_key)
            result.append(cert_clean)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def analyze(parsed_doc) -> AnalysisResult:
    """
    Trasforma ParsedDocument (raw fields) → AnalysisResult (BandoRequisiti + violazioni).

    Questo è l'unico punto di ingresso dell'analyzer.
    Non chiama mai l'LLM: è puro Python deterministic.
    """
    fields = dict(parsed_doc.raw_fields)
    violations: List[GuardrailViolation] = []
    warnings: List[str] = []

    # ── B: CIG ──────────────────────────────────────────────────────────────
    cig, cig_evidence, v = _guardrail_cig(fields)
    if v:
        violations.append(v)
        logger.warning(str(v))
    fields["codice_cig"] = cig
    fields["cig_evidence"] = cig_evidence

    # ── B: Importo ──────────────────────────────────────────────────────────
    importo, importo_evidence, v = _guardrail_importo(fields)
    if v:
        violations.append(v)
        logger.warning(str(v))
    fields["importo_lavori"] = importo
    fields["importo_evidence"] = importo_evidence
    # importo_base_gara: se mancava importo_lavori ma c'era importo_base_gara → stesso guardrail
    if importo and not fields.get("importo_lavori"):
        fields["importo_base_gara"] = importo
    elif not importo:
        fields["importo_base_gara"] = None

    # ── B: Piattaforma ──────────────────────────────────────────────────────
    canale, piattaforma_gara, piattaforma_evidence, v = _guardrail_piattaforma(fields)
    if v:
        violations.append(v)
        logger.warning(str(v))
    fields["canale_invio"] = canale
    fields["piattaforma_gara"] = piattaforma_gara
    fields["piattaforma_evidence"] = piattaforma_evidence

    # ── C: Scadenze ─────────────────────────────────────────────────────────
    raw_scadenze = fields.get("scadenze") or []
    if isinstance(raw_scadenze, list):
        scadenze, sca_violations = _validate_scadenze(raw_scadenze)
        violations.extend(sca_violations)
    else:
        scadenze = []
        warnings.append(f"Campo 'scadenze' non è una lista: {type(raw_scadenze)}")
    fields["scadenze"] = scadenze

    # ── B+C: SOA ────────────────────────────────────────────────────────────
    raw_soa = fields.get("soa_richieste") or []
    if isinstance(raw_soa, list):
        soa_list, soa_violations = _validate_soa(raw_soa)
        violations.extend(soa_violations)
    else:
        soa_list = []
        warnings.append(f"Campo 'soa_richieste' non è una lista: {type(raw_soa)}")
    fields["soa_richieste"] = soa_list

    # ── C: Certificazioni ───────────────────────────────────────────────────
    raw_certs = fields.get("certificazioni_richieste") or []
    if isinstance(raw_certs, list):
        fields["certificazioni_richieste"] = _validate_certificazioni(raw_certs)
    else:
        fields["certificazioni_richieste"] = []
        warnings.append("Campo 'certificazioni_richieste' non è una lista.")

    # ── C: Importo oneri sicurezza ───────────────────────────────────────────
    oneri = fields.get("oneri_sicurezza")
    if oneri is not None:
        try:
            oneri_f = float(oneri)
            fields["oneri_sicurezza"] = oneri_f if oneri_f >= 0 else None
        except (TypeError, ValueError):
            fields["oneri_sicurezza"] = None

    # ── Defaults obbligatori per BandoRequisiti ──────────────────────────────
    fields.setdefault("oggetto_appalto", "UNKNOWN")
    fields.setdefault("stazione_appaltante", "UNKNOWN")
    fields.setdefault("canale_invio", "unknown")
    fields.setdefault("document_type", "disciplinare")
    fields.setdefault("procedure_family", "aperta")

    # ── Costruisci BandoRequisiti ────────────────────────────────────────────
    if _HAS_PYDANTIC:
        known_fields = set(BandoRequisiti.model_fields.keys())
    else:
        import dataclasses as _ds
        known_fields = {f.name for f in _ds.fields(BandoRequisiti)}
    clean_fields = {k: v for k, v in fields.items() if k in known_fields}

    try:
        bando = BandoRequisiti(**clean_fields)
    except Exception as exc:
        logger.error(f"Errore costruzione BandoRequisiti: {exc}")
        warnings.append(f"BandoRequisiti costruita con fallback minimale: {exc}")
        bando = BandoRequisiti(
            oggetto_appalto=fields.get("oggetto_appalto", "UNKNOWN"),
            stazione_appaltante=fields.get("stazione_appaltante", "UNKNOWN"),
        )

    # ── Log finale ──────────────────────────────────────────────────────────
    if violations:
        logger.info(f"analyze(): {len(violations)} guardrail violation(s) rilevate.")
        for v in violations:
            logger.debug(str(v))
    if warnings:
        for w in warnings:
            logger.warning(f"analyze(): {w}")

    return AnalysisResult(bando=bando, violations=violations, warnings=warnings)