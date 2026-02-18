"""
BidPilot — Retrieval Engine  v1.0
==================================
Implementa:
  A2. Spezza il testo PDF in chunk (per pagina, max ~1500 token ciascuno).
  A3. Keyword scoring per categoria di estrazione.
  A4. Restituisce i top-N chunk per categoria, da passare all'LLM.
  A5. ExtractionTrace: log di quali chunk sono stati usati per cosa.

Design deliberato:
  - NESSUNA dipendenza da modelli vettoriali o indici ANN.
  - Scoring BM25-like puramente lessicale: trasparente, reproducibile, testabile.
  - Se un termine multi-parola ("UNI EN", "art. 94") appare nel chunk → peso doppio.
  - Tie-break: preferisce chunk più vicini all'inizio del documento (position bias).
"""
from __future__ import annotations

import re
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ══════════════════════════════════════════════════════════════════════════════
# KEYWORD CATALOG
# Ogni categoria → lista di termini (singoli o multi-parola).
# Termini multi-parola pesano 2× in _score().
# ══════════════════════════════════════════════════════════════════════════════

CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "soa": [
        "SOA", "OG", "OS",
        "categoria", "classifica", "prevalente", "scorporabile",
        "attestazione SOA", "qualificazione obbligatoria",
        "OG1", "OG2", "OG3", "OG4", "OG11", "OS3", "OS6", "OS18",
        "quinto d'obbligo", "quinto obbligo", "categoria prevalente",
        "importo categoria", "classifica I", "classifica II", "classifica III",
        "classifica IV", "classifica V", "classifica VI", "classifica VII",
        "classifica VIII",
    ],
    "scadenze": [
        "termine", "scadenza", "presentazione", "offerta", "ore",
        "quesiti", "chiarimenti", "sopralluogo", "data", "entro",
        "perentorio", "tassativo", "invio", "deposito",
        "termine di presentazione", "scadenza offerte",
        "ore 12:00", "ore 13:00", "ore 18:00",
    ],
    "anac_cig": [
        "CIG", "ANAC", "contributo", "FVOE", "AVCP", "pagoPA",
        "codice identificativo gara", "codice CIG",
        "contributo gara", "ANAC contributo",
        "FVOE fascicolo", "versamento contributo",
    ],
    "dgue": [
        "DGUE", "art. 94", "art. 95", "cause di esclusione",
        "DURC", "regolarità fiscale", "documento di gara unico europeo",
        "dichiarazione antimafia", "casellario", "art. 94 del codice",
        "art. 95 del codice", "esclusione automatica", "motivi esclusione",
        "regolarità contributiva",
    ],
    "certificazioni": [
        "ISO", "certificazione", "UNI EN",
        "45001", "9001", "14001", "27001", "50001",
        "sistema di gestione", "qualità", "ambiente", "sicurezza",
        "UNI EN ISO 9001", "UNI EN ISO 14001", "UNI EN ISO 45001",
        "OHSAS 18001", "certificato", "ente certificatore",
    ],
    "piattaforma": [
        "piattaforma", "portale", "Sintel", "MEPA", "PEC",
        "abilitazione", "registrazione", "portale gare",
        "piattaforma telematica", "sistema telematico",
        "upload", "caricamento", "firma digitale",
        "SATER", "Acquistinretepa", "piattaforma regionale",
        "Tuttogare", "Traspare",
    ],
    "importo": [
        "importo", "base d'asta", "importo lavori", "importo a base",
        "oneri sicurezza", "importo complessivo", "valore stimato",
        "€", "euro", "000,00", "mila euro",
        "importo a base di gara", "valore dell'appalto",
        "corrispettivo", "compenso",
    ],
    "forme_partecipazione": [
        "RTI", "raggruppamento temporaneo", "consorzio", "rete d'impresa",
        "mandataria", "mandante", "avvalimento", "subappalto",
        "GEIE", "impresa ausiliaria", "impresa ausiliata",
    ],
}

# ══════════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Chunk:
    """Un singolo chunk di testo estratto dal documento."""
    chunk_id: str          # es. "p3" (pagina 3) o "p3_b1" (pagina 3, blocco 1)
    page: int              # 0-indexed
    text: str
    token_estimate: int    # stima: len(text) // 4
    char_start: int = 0    # offset assoluto nel testo completo
    char_end: int = 0


@dataclass
class ScoredChunk:
    """Chunk con punteggio per una categoria."""
    chunk: Chunk
    score: float
    matched_terms: List[str] = field(default_factory=list)


@dataclass
class RetrievalResult:
    """Risultato del retrieval per una singola categoria."""
    category: str
    chunks: List[ScoredChunk]          # già ordinati per score desc
    total_chunks_considered: int


@dataclass
class ExtractionTrace:
    """
    A5 — Log di tracciamento: quali chunk sono stati usati per quale categoria.
    Serializzabile come dict per il log di debug.
    """
    category: str
    top_chunks: List[str]          # chunk_id dei chunk selezionati
    top_scores: List[float]
    top_pages: List[int]
    total_available: int
    tokens_sent: int               # stima token inviati all'LLM

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "top_chunks": self.top_chunks,
            "top_scores": [round(s, 3) for s in self.top_scores],
            "top_pages": self.top_pages,
            "total_available": self.total_available,
            "tokens_sent": self.tokens_sent,
        }


# ══════════════════════════════════════════════════════════════════════════════
# CHUNKER
# ══════════════════════════════════════════════════════════════════════════════

_MAX_CHUNK_CHARS = 6_000   # ~1500 token (stima 4 char/token)
_MIN_CHUNK_CHARS = 100     # chunk troppo corti vengono ignorati


def chunk_by_page(pages: List[str]) -> List[Chunk]:
    """
    A2 — Chunking per pagina. Se una pagina supera _MAX_CHUNK_CHARS la spezza
    in sub-blocchi da _MAX_CHUNK_CHARS caratteri con overlap di ~200 char.

    Args:
        pages: lista di stringhe, una per pagina (0-indexed)

    Returns:
        Lista di Chunk ordinati per pagina e posizione
    """
    chunks: List[Chunk] = []
    abs_offset = 0

    for page_idx, page_text in enumerate(pages):
        text = page_text.strip()
        if len(text) < _MIN_CHUNK_CHARS:
            abs_offset += len(page_text) + 1
            continue

        if len(text) <= _MAX_CHUNK_CHARS:
            chunk_id = f"p{page_idx + 1}"
            chunks.append(Chunk(
                chunk_id=chunk_id,
                page=page_idx,
                text=text,
                token_estimate=len(text) // 4,
                char_start=abs_offset,
                char_end=abs_offset + len(text),
            ))
        else:
            # Spezza con overlap
            overlap = 200
            pos = 0
            sub_idx = 0
            while pos < len(text):
                end = min(pos + _MAX_CHUNK_CHARS, len(text))
                sub_text = text[pos:end].strip()
                if len(sub_text) >= _MIN_CHUNK_CHARS:
                    chunk_id = f"p{page_idx + 1}_b{sub_idx}"
                    chunks.append(Chunk(
                        chunk_id=chunk_id,
                        page=page_idx,
                        text=sub_text,
                        token_estimate=len(sub_text) // 4,
                        char_start=abs_offset + pos,
                        char_end=abs_offset + end,
                    ))
                    sub_idx += 1
                pos = end - overlap if end < len(text) else end

        abs_offset += len(page_text) + 1

    return chunks


def chunk_full_text(full_text: str) -> List[Chunk]:
    """
    Fallback: chunking su testo completo senza separatori di pagina.
    Stima le pagine dal numero di caratteri (~3000 char/pagina A4).
    """
    CHARS_PER_PAGE = 3_000
    pages = []
    pos = 0
    while pos < len(full_text):
        end = pos + CHARS_PER_PAGE
        # cerca line break più vicino per non tagliare parole
        if end < len(full_text):
            nl = full_text.rfind('\n', pos, end + 200)
            if nl > pos:
                end = nl
        pages.append(full_text[pos:end])
        pos = end
    return chunk_by_page(pages)


# ══════════════════════════════════════════════════════════════════════════════
# SCORER
# ══════════════════════════════════════════════════════════════════════════════

def _normalize(text: str) -> str:
    """Lowercase, collassa spazi multipli."""
    return re.sub(r'\s+', ' ', text.lower())


def _score(chunk: Chunk, keywords: List[str], position_bias: float = 0.0) -> Tuple[float, List[str]]:
    """
    Calcola score BM25-like per un chunk dato un set di keyword.

    Score = Σ weight_i * log(1 + tf_i)
    dove:
      - tf_i = occorrenze del termine i nel chunk
      - weight_i = 2.0 per multi-parola, 1.0 per singola parola
      - position_bias = piccola penalità proporzionale alla posizione nel doc
        (chunk iniziali premiati, ma solo lievemente)

    Returns:
        (score, lista di termini che hanno matchato)
    """
    text_norm = _normalize(chunk.text)
    score = 0.0
    matched: List[str] = []

    for kw in keywords:
        kw_norm = _normalize(kw)
        is_multiword = ' ' in kw_norm
        weight = 2.0 if is_multiword else 1.0

        # Conta occorrenze (non overlapping)
        tf = len(re.findall(re.escape(kw_norm), text_norm))
        if tf > 0:
            score += weight * math.log(1 + tf)
            matched.append(kw)

    # Position bias: −0.1 per ogni 10 chunk di distanza dall'inizio
    score = max(0.0, score - position_bias * 0.01)
    return score, matched


# ══════════════════════════════════════════════════════════════════════════════
# RETRIEVER
# ══════════════════════════════════════════════════════════════════════════════

class Retriever:
    """
    A3-A4 — Retrieval per categoria: score tutti i chunk, restituisce i top-N.
    """

    def __init__(self, chunks: List[Chunk]):
        self.chunks = chunks

    def retrieve(
        self,
        category: str,
        top_n: int = 6,
        min_score: float = 0.1,
        keywords: Optional[List[str]] = None,
    ) -> RetrievalResult:
        """
        Recupera i chunk più rilevanti per una categoria.

        Args:
            category: nome della categoria (deve esistere in CATEGORY_KEYWORDS
                       oppure passare keywords esplicite)
            top_n: numero massimo di chunk da restituire
            min_score: soglia minima; chunk sotto soglia scartati
            keywords: override delle keyword (se None usa il catalog)
        """
        kws = keywords if keywords is not None else CATEGORY_KEYWORDS.get(category, [])
        if not kws:
            raise ValueError(f"Categoria '{category}' non trovata e nessuna keyword fornita.")

        scored: List[ScoredChunk] = []
        for i, chunk in enumerate(self.chunks):
            position_bias = i  # bias crescente
            s, matched = _score(chunk, kws, position_bias)
            if s >= min_score:
                scored.append(ScoredChunk(chunk=chunk, score=s, matched_terms=matched))

        scored.sort(key=lambda x: -x.score)
        top = scored[:top_n]

        # Ri-ordina i top chunk per posizione nel documento (più naturale per l'LLM)
        top.sort(key=lambda x: x.chunk.char_start)

        return RetrievalResult(
            category=category,
            chunks=top,
            total_chunks_considered=len(self.chunks),
        )

    def retrieve_all(
        self,
        categories: Optional[List[str]] = None,
        top_n: int = 6,
        min_score: float = 0.1,
    ) -> Dict[str, RetrievalResult]:
        """Retrieve per tutte le categorie (o sottoinsieme)."""
        cats = categories or list(CATEGORY_KEYWORDS.keys())
        return {cat: self.retrieve(cat, top_n=top_n, min_score=min_score) for cat in cats}


# ══════════════════════════════════════════════════════════════════════════════
# TRACE BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def build_trace(category: str, result: RetrievalResult) -> ExtractionTrace:
    """A5 — Costruisce ExtractionTrace da un RetrievalResult."""
    return ExtractionTrace(
        category=category,
        top_chunks=[sc.chunk.chunk_id for sc in result.chunks],
        top_scores=[sc.score for sc in result.chunks],
        top_pages=[sc.chunk.page + 1 for sc in result.chunks],  # 1-indexed per leggibilità
        total_available=result.total_chunks_considered,
        tokens_sent=sum(sc.chunk.token_estimate for sc in result.chunks),
    )


def build_context_string(result: RetrievalResult, include_chunk_id: bool = True) -> str:
    """
    Costruisce la stringa di contesto da passare all'LLM.
    Ogni chunk è delimitato da marker per facilitare l'estrazione evidence.
    """
    parts = []
    for sc in result.chunks:
        header = f"[CHUNK {sc.chunk.chunk_id} | pagina {sc.chunk.page + 1}]"
        if include_chunk_id:
            parts.append(f"{header}\n{sc.chunk.text}")
        else:
            parts.append(sc.chunk.text)
    return "\n\n---\n\n".join(parts)
