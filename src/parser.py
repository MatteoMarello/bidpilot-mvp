"""
Parser PDF ANTI-ALLUCINAZIONE con pdfplumber
Estrae testo mantenendo struttura e rileva PDF scansionati/illeggibili
"""
import pdfplumber
import re
from typing import Dict, List, Tuple, Optional
from pathlib import Path


class BandoParser:
    """Parser robusto per PDF di bandi con rilevamento qualità"""
    
    def __init__(self):
        self.min_text_length = 100  # Minimo caratteri per pagina valida
        
    def _is_scanned_pdf(self, text: str, page_num: int) -> bool:
        """
        Rileva se una pagina è scansionata (solo immagine, no testo estraibile)
        
        Returns:
            True se probabile PDF scansionato
        """
        # Se la pagina ha meno di X caratteri, probabile scansione
        if len(text.strip()) < self.min_text_length:
            return True
        
        # Se il testo è solo caratteri strani/Unicode, probabile OCR mal riuscito
        strange_chars = sum(1 for c in text if ord(c) > 1000)
        if len(text) > 0 and strange_chars / len(text) > 0.3:
            return True
        
        return False
    
    def _extract_header_pages(self, pdf_path: str, max_pages: int = 5) -> str:
        """
        Estrae solo le prime N pagine (per metadati principali)
        
        Returns:
            Testo prime pagine
        """
        text_parts = []
        
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            pages_to_read = min(max_pages, total_pages)
            
            for i in range(pages_to_read):
                page = pdf.pages[i]
                text = page.extract_text()
                
                if text:
                    # Mantieni separazione tra pagine
                    text_parts.append(f"\n\n=== PAGINA {i+1} ===\n\n")
                    text_parts.append(text)
        
        return "".join(text_parts)
    
    def _extract_section_by_keywords(self, pdf_path: str, keywords: List[str]) -> str:
        """
        Cerca pagine che contengono determinate parole chiave
        Utile per estrarre solo sezioni rilevanti (es: SOA, Requisiti)
        
        Args:
            pdf_path: percorso PDF
            keywords: lista parole chiave (es: ["SOA", "III.2", "Capacità tecnica"])
            
        Returns:
            Testo delle pagine che contengono almeno una keyword
        """
        text_parts = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                
                if not text:
                    continue
                
                # Check se contiene keyword (case-insensitive)
                text_lower = text.lower()
                if any(kw.lower() in text_lower for kw in keywords):
                    text_parts.append(f"\n\n=== PAGINA {i+1} (SEZIONE REQUISITI) ===\n\n")
                    text_parts.append(text)
        
        return "".join(text_parts)
    
    def parse_pdf(self, pdf_path: str, mode: str = "full") -> str:
        """
        Estrae testo da PDF mantenendo struttura
        
        Args:
            pdf_path: percorso file PDF
            mode: "full" (tutto) | "header" (prime 5 pag) | "requirements" (solo pagine SOA/requisiti)
            
        Returns:
            Testo estratto
            
        Raises:
            Exception se PDF illeggibile o scansionato
        """
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF non trovato: {pdf_path}")
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                
                if total_pages == 0:
                    raise Exception("PDF vuoto (0 pagine)")
                
                # Se mode = header, leggi solo prime pagine
                if mode == "header":
                    return self._extract_header_pages(pdf_path, max_pages=5)
                
                # Se mode = requirements, cerca solo pagine con parole chiave
                if mode == "requirements":
                    keywords = [
                        "SOA", "III.2", "III.1", "Capacità tecnica", "Capacità economica",
                        "Requisiti di partecipazione", "Attestazione", "Classifica",
                        "ISO", "Certificazione", "UNI EN"
                    ]
                    return self._extract_section_by_keywords(pdf_path, keywords)
                
                # Mode = full: estrai tutto
                text_parts = []
                scanned_pages = []
                
                for i, page in enumerate(pdf.pages):
                    page_num = i + 1
                    text = page.extract_text()
                    
                    if not text:
                        scanned_pages.append(page_num)
                        continue
                    
                    # Check se pagina scansionata
                    if self._is_scanned_pdf(text, page_num):
                        scanned_pages.append(page_num)
                        continue
                    
                    # Aggiungi separatore pagina per mantenere contesto
                    text_parts.append(f"\n\n=== PAGINA {page_num} ===\n\n")
                    text_parts.append(text)
                
                # Warning se molte pagine scansionate
                if scanned_pages:
                    perc_scanned = len(scanned_pages) / total_pages * 100
                    
                    if perc_scanned > 30:
                        raise Exception(
                            f"⚠️ ATTENZIONE: {perc_scanned:.0f}% del PDF sembra scansionato (pagine {scanned_pages[:5]}...). "
                            f"L'estrazione potrebbe essere incompleta o errata. "
                            f"Considera di usare un PDF con testo selezionabile o applicare OCR."
                        )
                
                full_text = "".join(text_parts)
                
                if len(full_text.strip()) < 500:
                    raise Exception(
                        f"PDF troppo corto ({len(full_text)} caratteri). "
                        f"Possibile PDF scansionato o corrotto."
                    )
                
                return full_text
                
        except Exception as e:
            raise Exception(f"Errore parsing PDF: {str(e)}")
    
    def extract_metadata(self, pdf_path: str) -> Dict:
        """
        Estrae metadata di base dal PDF per diagnostica
        
        Returns:
            dict con statistiche PDF
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                
                # Conta caratteri per pagina
                char_counts = []
                for page in pdf.pages:
                    text = page.extract_text()
                    char_counts.append(len(text) if text else 0)
                
                avg_chars = sum(char_counts) / len(char_counts) if char_counts else 0
                min_chars = min(char_counts) if char_counts else 0
                max_chars = max(char_counts) if char_counts else 0
                
                # Rileva pagine sospette
                suspicious_pages = [
                    i+1 for i, count in enumerate(char_counts) 
                    if count < self.min_text_length
                ]
                
                return {
                    "num_pagine": total_pages,
                    "caratteri_totali": sum(char_counts),
                    "caratteri_medi_per_pagina": int(avg_chars),
                    "caratteri_min": min_chars,
                    "caratteri_max": max_chars,
                    "pagine_sospette_scansionate": suspicious_pages,
                    "qualita_stimata": "BUONA" if len(suspicious_pages) / total_pages < 0.2 else "SCARSA",
                    "fonte": pdf_path
                }
                
        except Exception as e:
            return {"errore": str(e)}
    
    def chunked_extraction(self, pdf_path: str, chunk_size: int = 10000) -> List[Tuple[str, int, int]]:
        """
        Estrae testo in chunk sovrapposti per LLM
        
        Returns:
            Lista di (chunk_text, start_page, end_page)
        """
        full_text = self.parse_pdf(pdf_path, mode="full")
        
        chunks = []
        current_chunk = ""
        start_page = 1
        current_page = 1
        
        # Split per pagina mantenendo marker
        pages = re.split(r'=== PAGINA (\d+) ===', full_text)
        
        for i in range(1, len(pages), 2):
            page_num = int(pages[i])
            page_text = pages[i+1] if i+1 < len(pages) else ""
            
            if len(current_chunk) + len(page_text) > chunk_size:
                # Salva chunk corrente
                if current_chunk:
                    chunks.append((current_chunk, start_page, current_page - 1))
                
                # Inizia nuovo chunk
                current_chunk = page_text
                start_page = page_num
            else:
                current_chunk += f"\n\n=== PAGINA {page_num} ===\n\n" + page_text
            
            current_page = page_num
        
        # Aggiungi ultimo chunk
        if current_chunk:
            chunks.append((current_chunk, start_page, current_page))
        
        return chunks