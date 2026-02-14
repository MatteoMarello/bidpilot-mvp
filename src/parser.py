"""
Parser per PDF di bandi d'appalto
Estrae testo e lo prepara per l'analisi LLM
"""
from typing import List
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter


class BandoParser:
    """Parser per documenti PDF di bandi"""
    
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=4000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )
    
    def parse_pdf(self, pdf_path: str) -> str:
        """
        Estrae testo completo da PDF
        
        Args:
            pdf_path: percorso file PDF
            
        Returns:
            testo completo del PDF
        """
        try:
            loader = PyPDFLoader(pdf_path)
            pages = loader.load()
            
            # Concatena tutto il testo
            full_text = "\n\n".join([page.page_content for page in pages])
            
            return full_text
            
        except Exception as e:
            raise Exception(f"Errore nel parsing del PDF: {str(e)}")
    
    def parse_and_chunk(self, pdf_path: str) -> List[str]:
        """
        Estrae e chunka il testo per elaborazioni su chunk separati
        
        Args:
            pdf_path: percorso file PDF
            
        Returns:
            lista di chunk testuali
        """
        try:
            full_text = self.parse_pdf(pdf_path)
            chunks = self.text_splitter.split_text(full_text)
            return chunks
            
        except Exception as e:
            raise Exception(f"Errore nel chunking: {str(e)}")
    
    def extract_metadata(self, pdf_path: str) -> dict:
        """
        Estrae metadata di base dal PDF
        
        Args:
            pdf_path: percorso file PDF
            
        Returns:
            dict con metadata
        """
        try:
            loader = PyPDFLoader(pdf_path)
            pages = loader.load()
            
            return {
                "num_pagine": len(pages),
                "lunghezza_caratteri": sum(len(p.page_content) for p in pages),
                "fonte": pdf_path
            }
            
        except Exception as e:
            return {"errore": str(e)}
