"""
BidPilot — Parser  v2.0
========================
Implementa:
  A1-A5. Non passa più "tutto il PDF" all'LLM.
         Invece: PDF → pagine → chunk → retrieval per categoria → LLM su top chunk.
  B.     Ogni campo critico richiede evidence; senza → None (mai inventato).
  (C validazioni post-estrazione sono in analyzer.py)

Flusso:
  parse_pdf(path) → ParsedDocument
    ├─ _extract_pages(path)        → List[str] (testo per pagina)
    ├─ chunk_by_page(pages)        → List[Chunk]
    ├─ Retriever(chunks)
    ├─ per categoria → retrieve → build_context_string
    ├─ _llm_extract_category(category, context) → dict parziale
    └─ _merge_extractions(parts)   → BandoRequisiti (raw, pre-guardrail)

Il documento ParsedDocument porta anche le ExtractionTrace per il debug.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.retrieval import (
    Chunk,
    ExtractionTrace,
    Retriever,
    RetrievalResult,
    build_context_string,
    build_trace,
    chunk_by_page,
    chunk_full_text,
    CATEGORY_KEYWORDS,
)

logger = logging.getLogger("bidpilot.parser")


# ══════════════════════════════════════════════════════════════════════════════
# OUTPUT TYPES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ParsedDocument:
    """Risultato di parse_pdf: estrazione grezza + metadati di tracciamento."""
    raw_fields: Dict[str, Any]        # campi estratti pre-guardrail
    chunks: List[Chunk]               # tutti i chunk generati
    traces: List[ExtractionTrace]     # A5: log di tracciamento per categoria
    pages_count: int
    source_path: str

    def trace_for(self, category: str) -> Optional[ExtractionTrace]:
        return next((t for t in self.traces if t.category == category), None)

    def traces_as_dict(self) -> List[dict]:
        return [t.to_dict() for t in self.traces]


# ══════════════════════════════════════════════════════════════════════════════
# PDF TEXT EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

def _extract_pages_pymupdf(path: str) -> Tuple[List[str], int]:
    """Usa PyMuPDF (fitz) — preferito per accuratezza su PDF complessi."""
    import fitz  # type: ignore
    doc = fitz.open(path)
    pages = []
    for page in doc:
        text = page.get_text("text", sort=True)
        pages.append(text)
    doc.close()
    return pages, len(pages)


def _extract_pages_pdfplumber(path: str) -> Tuple[List[str], int]:
    """Fallback: pdfplumber."""
    import pdfplumber  # type: ignore
    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages.append(text)
    return pages, len(pages)


def _extract_pages_pypdf(path: str) -> Tuple[List[str], int]:
    """Fallback di ultima istanza: PyPDF2/pypdf."""
    from pypdf import PdfReader  # type: ignore
    reader = PdfReader(path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return pages, len(pages)


def _extract_pages(path: str) -> Tuple[List[str], int]:
    """
    Prova in ordine: PyMuPDF → pdfplumber → pypdf.
    Restituisce (pages, count) dove pages è lista di stringhe per pagina.
    """
    for fn in (_extract_pages_pymupdf, _extract_pages_pdfplumber, _extract_pages_pypdf):
        try:
            return fn(path)
        except ImportError:
            continue
        except Exception as exc:
            logger.warning(f"{fn.__name__} fallito su {path}: {exc}")
            continue
    raise RuntimeError(
        f"Impossibile estrarre testo da {path}: nessuna libreria PDF disponibile. "
        "Installare PyMuPDF: pip install pymupdf"
    )


# ══════════════════════════════════════════════════════════════════════════════
# LLM CALLER
# ══════════════════════════════════════════════════════════════════════════════

# Mappa categoria → schema JSON atteso dall'LLM (subset di BandoRequisiti)
# Usato per costruire il prompt di estrazione per categoria.
_CATEGORY_SCHEMA: Dict[str, dict] = {
    "anac_cig": {
        "description": "Estrai solo i campi relativi a CIG, ANAC e FVOE.",
        "fields": {
            "codice_cig": "stringa CIG (es. 'A1234567B9') oppure null se non trovata",
            "cig_evidence": "quota testuale ESATTA dove appare il CIG (obbligatoria; null se non trovata)",
            "anac_contributo_richiesto": "'yes'/'no'/'unknown'",
            "fvoe_required": "true/false",
        },
    },
    "importo": {
        "description": "Estrai solo gli importi dell'appalto.",
        "fields": {
            "importo_lavori": "numero float in euro oppure null",
            "importo_base_gara": "numero float in euro oppure null",
            "oneri_sicurezza": "numero float in euro oppure null",
            "importo_totale": "numero float in euro oppure null",
            "importo_evidence": "quota testuale ESATTA contenente l'importo (obbligatoria; null se non trovata)",
        },
    },
    "scadenze": {
        "description": "Estrai tutte le scadenze citate nel testo.",
        "fields": {
            "scadenze": [
                {
                    "tipo": "tipo scadenza (es. 'presentazione_offerta', 'chiarimenti', 'sopralluogo')",
                    "data": "data in formato ISO 8601 (YYYY-MM-DD) oppure null se non deducibile con certezza",
                    "ora": "ora in formato HH:MM oppure null",
                    "obbligatorio": "true/false",
                    "evidence": "quota testuale ESATTA della scadenza (obbligatoria; null se non trovata)",
                    "esclusione_se_mancante": "true/false",
                    "note": "eventuale nota oppure null",
                }
            ]
        },
    },
    "soa": {
        "description": "Estrai le categorie SOA richieste. Solo quelle esplicitamente citate nel testo.",
        "fields": {
            "soa_richieste": [
                {
                    "categoria": "es. 'OG1', 'OS3'",
                    "descrizione": "descrizione della categoria oppure ''",
                    "classifica": "es. 'III', 'IV-bis', 'V'",
                    "prevalente": "true se esplicitamente indicata come prevalente, altrimenti false",
                    "is_scorporabile": "true se scorporabile, altrimenti false",
                    "qualificazione_obbligatoria": "true/false",
                    "importo_categoria": "importo in euro oppure null",
                    "evidence": "quota testuale ESATTA dove appare la categoria (OBBLIGATORIA; null se non trovata — in tal caso NON includere la categoria)",
                }
            ]
        },
    },
    "piattaforma": {
        "description": "Estrai piattaforma di gara e canale di invio.",
        "fields": {
            "canale_invio": "'piattaforma'/'PEC'/'email'/'misto'/'unknown'",
            "piattaforma_gara": "nome della piattaforma oppure null",
            "piattaforma_url": "URL della piattaforma oppure null",
            "piattaforma_spid_required": "true/false",
            "piattaforma_evidence": "quota testuale ESATTA che descrive il canale di invio (obbligatoria; null se non trovata)",
        },
    },
    "certificazioni": {
        "description": "Estrai le certificazioni ISO/UNI richieste.",
        "fields": {
            "certificazioni_richieste": "lista di stringhe es. ['ISO 9001', 'ISO 14001']",
        },
    },
    "dgue": {
        "description": "Estrai informazioni su DGUE e cause di esclusione.",
        "fields": {
            "dgue_required": "true/false",
            "dgue_format": "formato richiesto oppure null",
            "dgue_sezioni_obbligatorie": "lista stringhe oppure []",
            "protocollo_legalita_required": "true/false",
            "patto_integrita_required": "true/false",
            "patto_integrita_pena_esclusione": "true/false",
        },
    },
    "forme_partecipazione": {
        "description": "Estrai informazioni su RTI, avvalimento, subappalto.",
        "fields": {
            "rti_ammesso": "'yes'/'no'/'unknown'",
            "avvalimento_ammesso": "'yes'/'no'/'unknown'",
            "subappalto_percentuale_max": "percentuale float oppure null",
            "allowed_forms": "lista stringhe es. ['RTI', 'consorzio']",
        },
    },
}

# Campi di metadati estratti separatamente (non richiedono retrieval)
_META_SCHEMA = {
    "description": "Estrai i metadati generali della gara dal testo di apertura del documento.",
    "fields": {
        "oggetto_appalto": "oggetto/titolo della gara",
        "oggetto_evidence": "quota testuale",
        "stazione_appaltante": "nome della stazione appaltante",
        "stazione_evidence": "quota testuale",
        "codice_cup": "CUP se presente oppure null",
        "cpv": "codice CPV oppure null",
        "tipo_procedura": "es. 'aperta', 'negoziata'",
        "criterio_aggiudicazione": "es. 'OEPV', 'minor prezzo'",
        "lotti": "numero intero di lotti (default 1)",
        "is_pnrr": "true/false",
        "is_bim": "true/false",
    },
}


def _build_extraction_prompt(category: str, context: str) -> str:
    """
    Costruisce il prompt per l'estrazione di una categoria.
    Regola centrale (B): se un campo evidence è null → il campo corrispondente DEVE essere null.
    """
    schema = _CATEGORY_SCHEMA.get(category, {})
    schema_json = json.dumps(schema.get("fields", {}), ensure_ascii=False, indent=2)
    description = schema.get("description", f"Estrai le informazioni su '{category}'.")

    return f"""Sei un assistente specializzato nell'estrazione strutturata da bandi di gara italiani.

## TASK
{description}

## REGOLE CRITICHE (NON DEROGABILI)
1. Rispondi SOLO con un oggetto JSON valido, nessun testo fuori dal JSON.
2. Se un'informazione non è presente nel testo → usa null (MAI inventare).
3. Per ogni campo "*_evidence": copia la frase ESATTA dal testo che prova il valore.
   - Se non trovi la frase → il campo evidence vale null E il campo principale vale null.
   - Non parafrasare: copia testualmente.
4. Per le date: usa formato ISO 8601 (YYYY-MM-DD). Se la data è ambigua o incompleta → null.
5. Per gli importi: usa solo numeri float (es. 150000.0). Se non sei certo → null.
6. Per le categorie SOA: includi solo quelle con evidence non null.

## SCHEMA DI OUTPUT ATTESO
{schema_json}

## TESTO DEL DOCUMENTO (estratto per rilevanza)
{context}

## OUTPUT (solo JSON, nessun markdown):"""


def _build_meta_prompt(context: str) -> str:
    schema_json = json.dumps(_META_SCHEMA["fields"], ensure_ascii=False, indent=2)
    return f"""Sei un assistente specializzato nell'estrazione strutturata da bandi di gara italiani.

## TASK
{_META_SCHEMA["description"]}

## REGOLE CRITICHE
1. Rispondi SOLO con un oggetto JSON valido.
2. Se un campo non è nel testo → null.
3. Non inventare. Non parafrasare le evidence: copia testualmente.

## SCHEMA
{schema_json}

## TESTO
{context}

## OUTPUT (solo JSON):"""


def _call_llm(prompt: str, model: str, api_key: str) -> dict:
    """
    Chiama l'LLM e restituisce il JSON estratto.
    Supporta Anthropic (modelli claude-*) e OpenAI (fallback/predefinito).
    Raises ValueError se il JSON non è parsabile.
    """
    raw: str

    if model.startswith("claude"):
        try:
            import anthropic  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Modello Claude richiesto ma modulo 'anthropic' non installato. "
                "Installa `anthropic` o usa un modello OpenAI (es. gpt-4o-mini)."
            ) from exc

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
    else:
        try:
            from openai import OpenAI  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Dipendenza mancante: modulo 'openai' non installato. "
                "Installa i requirements del progetto (es. `pip install -r requirements.txt`)."
            ) from exc

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "Rispondi sempre e solo con JSON valido."},
                {"role": "user", "content": prompt},
            ],
        )
        raw = (response.choices[0].message.content or "").strip()

    # Rimuovi eventuali ```json ... ``` se il modello li aggiunge
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)
    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error(f"JSON non valido dall'LLM per prompt (troncato): {prompt[:200]}")
        logger.error(f"Risposta raw: {raw[:500]}")
        raise ValueError(f"LLM non ha restituito JSON valido: {exc}") from exc


# ══════════════════════════════════════════════════════════════════════════════
# EXTRACTION PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def _extract_category(
    category: str,
    retriever: Retriever,
    model: str,
    api_key: str,
    top_n: int = 6,
    min_score: float = 0.1,
) -> Tuple[dict, ExtractionTrace]:
    """
    Retrieval + LLM extraction per una singola categoria.
    Restituisce (fields_dict, trace).
    """
    result: RetrievalResult = retriever.retrieve(category, top_n=top_n, min_score=min_score)
    trace = build_trace(category, result)

    if not result.chunks:
        logger.info(f"Categoria '{category}': nessun chunk rilevante trovato (score < {min_score}).")
        return {}, trace

    context = build_context_string(result, include_chunk_id=True)
    prompt = _build_extraction_prompt(category, context)

    try:
        fields = _call_llm(prompt, model=model, api_key=api_key)
    except ValueError as exc:
        logger.warning(f"Categoria '{category}': LLM fallito — {exc}. Restituisco dict vuoto.")
        fields = {}

    return fields, trace


def _extract_meta(
    chunks: List[Chunk],
    model: str,
    api_key: str,
) -> dict:
    """
    Estrae i metadati generali dal primo ~20% dei chunk (apertura documento).
    Non usa retrieval: l'oggetto e la SA sono quasi sempre nell'intestazione.
    """
    n_meta = max(2, len(chunks) // 5)
    meta_chunks = chunks[:n_meta]
    context = "\n\n---\n\n".join(
        f"[CHUNK {c.chunk_id} | pagina {c.page + 1}]\n{c.text}"
        for c in meta_chunks
    )
    prompt = _build_meta_prompt(context)
    try:
        return _call_llm(prompt, model=model, api_key=api_key)
    except ValueError:
        return {}


def _deep_merge(base: dict, override: dict) -> dict:
    """
    Merge ricorsivo: override sovrascrive base.
    Liste: override sostituisce (non appendono).
    None in override NON sovrascrive valore non-None in base.
    """
    result = dict(base)
    for k, v in override.items():
        if v is None and result.get(k) is not None:
            continue  # non sovrascrivere con None se base ha un valore
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def parse_pdf(
    path: str,
    model: str = "gpt-4o-mini",
    api_key: Optional[str] = None,
    categories: Optional[List[str]] = None,
    top_n_per_category: int = 6,
    min_score: float = 0.1,
) -> ParsedDocument:
    """
    Pipeline principale: PDF → ParsedDocument (raw fields + traces).

    I campi raw NON sono ancora validati (guardrail in analyzer.py).

    Args:
        path: percorso al file PDF
        model: modello LLM da usare (es. gpt-4o-mini o claude-*)
        api_key: API key provider (default: OPENAI_API_KEY, poi ANTHROPIC_API_KEY)
        categories: lista di categorie da estrarre (default: tutte)
        top_n_per_category: chunk massimi per categoria
        min_score: soglia minima di score per il retrieval
    """
    api_key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "API key non trovata. Passa api_key= o imposta OPENAI_API_KEY (o ANTHROPIC_API_KEY)."
        )

    path = str(Path(path).resolve())
    logger.info(f"parse_pdf: {path}")

    # 1. Estrai testo per pagina
    pages, pages_count = _extract_pages(path)
    logger.info(f"  Estratte {pages_count} pagine.")

    # 2. Chunking
    chunks = chunk_by_page(pages)
    if not chunks:
        # Fallback su testo completo se chunk vuoti
        full_text = "\n".join(pages)
        chunks = chunk_full_text(full_text)
    logger.info(f"  Generati {len(chunks)} chunk.")

    # 3. Retrieval engine
    retriever = Retriever(chunks)

    # 4. Metadati (senza retrieval, prime pagine)
    logger.info("  Estrazione metadati (prime pagine)...")
    raw_fields = _extract_meta(chunks, model=model, api_key=api_key)

    # 5. Estrazione per categoria
    cats = categories or list(_CATEGORY_SCHEMA.keys())
    traces: List[ExtractionTrace] = []

    for cat in cats:
        logger.info(f"  Estrazione categoria: {cat}...")
        cat_fields, trace = _extract_category(
            cat, retriever, model=model, api_key=api_key,
            top_n=top_n_per_category, min_score=min_score,
        )
        traces.append(trace)
        raw_fields = _deep_merge(raw_fields, cat_fields)
        logger.info(
            f"    → {len(cat_fields)} campi estratti, "
            f"{len(trace.top_chunks)} chunk usati, "
            f"~{trace.tokens_sent} token"
        )

    return ParsedDocument(
        raw_fields=raw_fields,
        chunks=chunks,
        traces=traces,
        pages_count=pages_count,
        source_path=path,
    )


def parse_text(
    text: str,
    model: str = "gpt-4o-mini",
    api_key: Optional[str] = None,
    categories: Optional[List[str]] = None,
    top_n_per_category: int = 6,
    min_score: float = 0.1,
) -> ParsedDocument:
    """
    Variante: accetta testo già estratto invece di un PDF.
    Usata nei test golden (evita dipendenza da file PDF reali).
    """
    api_key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("API key non trovata (OPENAI_API_KEY / ANTHROPIC_API_KEY).")

    chunks = chunk_full_text(text)
    retriever = Retriever(chunks)
    raw_fields = _extract_meta(chunks, model=model, api_key=api_key)

    cats = categories or list(_CATEGORY_SCHEMA.keys())
    traces: List[ExtractionTrace] = []

    for cat in cats:
        cat_fields, trace = _extract_category(
            cat, retriever, model=model, api_key=api_key,
            top_n=top_n_per_category, min_score=min_score,
        )
        traces.append(trace)
        raw_fields = _deep_merge(raw_fields, cat_fields)

    return ParsedDocument(
        raw_fields=raw_fields,
        chunks=chunks,
        traces=traces,
        pages_count=0,
        source_path="<text>",
    )
