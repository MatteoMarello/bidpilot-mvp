"""Parser PDF con pdfplumber - rilevamento qualità e anti-allucinazione"""
import pdfplumber
import re
from typing import Dict, List, Tuple, Optional
from pathlib import Path


class BandoParser:
    """Parser robusto per PDF di bandi con rilevamento qualità"""
    
    def __init__(self):
        self.min_text_length = 100
        
    def _is_scanned_pdf(self, text: str, page_num: int) -> bool:
        """Rileva se pagina è scansionata (solo immagine)"""
        if len(text.strip()) < self.min_text_length:
            return True
        
        strange_chars = sum(1 for c in text if ord(c) > 1000)
        if len(text) > 0 and strange_chars / len(text) > 0.3:
            return True
        
        return False
    
    def parse_pdf(self, pdf_path: str, mode: str = "full") -> str:
        """
        Estrae testo da PDF
        
        Args:
            pdf_path: percorso PDF
            mode: "full" | "header" (prime 5 pag) | "requirements" (solo pag SOA)
        
        Returns:
            Testo estratto
        """
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF non trovato: {pdf_path}")
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if not pdf.pages:
                    raise Exception("PDF vuoto")
                
                # Mode header: solo prime 5 pagine
                if mode == "header":
                    text_parts = []
                    for i in range(min(5, len(pdf.pages))):
                        if text := pdf.pages[i].extract_text():
                            text_parts.append(f"\n=== PAGINA {i+1} ===\n{text}")
                    return "".join(text_parts)
                
                # Mode requirements: solo pagine con keyword
                if mode == "requirements":
                    keywords = [
                        "SOA", "III.2", "Capacità tecnica", "Requisiti",
                        "ISO", "Certificazione", "Classifica"
                    ]
                    text_parts = []
                    for i, page in enumerate(pdf.pages):
                        if text := page.extract_text():
                            if any(kw.lower() in text.lower() for kw in keywords):
                                text_parts.append(f"\n=== PAGINA {i+1} ===\n{text}")
                    return "".join(text_parts)
                
                # Mode full: tutto
                text_parts = []
                scanned = []
                
                for i, page in enumerate(pdf.pages):
                    if not (text := page.extract_text()):
                        scanned.append(i+1)
                        continue
                    
                    if self._is_scanned_pdf(text, i+1):
                        scanned.append(i+1)
                        continue
                    
                    text_parts.append(f"\n=== PAGINA {i+1} ===\n{text}")
                
                # Warning se troppe pagine scansionate
                if scanned and len(scanned) / len(pdf.pages) > 0.3:
                    raise Exception(
                        f"⚠️ {len(scanned)/len(pdf.pages)*100:.0f}% PDF scansionato. "
                        f"Estrazione potrebbe essere incompleta."
                    )
                
                full_text = "".join(text_parts)
                
                if len(full_text.strip()) < 500:
                    raise Exception("PDF troppo corto - possibile PDF scansionato o corrotto")
                
                return full_text
                
        except Exception as e:
            raise Exception(f"Errore parsing PDF: {e}")
    
    def extract_metadata(self, pdf_path: str) -> Dict:
        """Estrae metadata PDF per diagnostica"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                char_counts = []
                for page in pdf.pages:
                    text = page.extract_text()
                    char_counts.append(len(text) if text else 0)
                
                avg = sum(char_counts) / len(char_counts) if char_counts else 0
                suspicious = [i+1 for i, c in enumerate(char_counts) if c < self.min_text_length]
                
                return {
                    "num_pagine": len(pdf.pages),
                    "caratteri_totali": sum(char_counts),
                    "caratteri_medi": int(avg),
                    "pagine_sospette": suspicious,
                    "qualita_stimata": "BUONA" if len(suspicious) / len(pdf.pages) < 0.2 else "SCARSA"
                }
        except Exception as e:
            return {"errore": str(e)}
