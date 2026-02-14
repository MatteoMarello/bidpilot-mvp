"""
RAG Engine per generazione bozze offerte tecniche
Recupera contenuti da progetti storici e genera bozze
"""
import os
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import PromptTemplate

from src.prompts import GENERATION_PROMPT


class RAGEngine:
    """Engine RAG per recupero e generazione contenuti"""
    
    def __init__(self, openai_api_key: str, progetti_dir: str = "data/progetti_storici"):
        self.openai_api_key = openai_api_key
        self.progetti_dir = progetti_dir
        
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.3,
            api_key=openai_api_key
        )
        
        self.embeddings = OpenAIEmbeddings(api_key=openai_api_key)
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", "! ", "? ", ", ", " ", ""]
        )
        
        self.vectorstore = None
        self.progetti_metadata = []
    
    def ingest_progetti(self, force_rebuild: bool = False) -> None:
        """
        Indicizza tutti i PDF dei progetti storici in ChromaDB
        
        Args:
            force_rebuild: se True, ricrea l'indice da zero
        """
        persist_directory = "data/chroma_db"
        
        # Se esiste già e non forziamo rebuild, carica
        if os.path.exists(persist_directory) and not force_rebuild:
            print(f"📚 Caricamento database esistente da {persist_directory}...")
            self.vectorstore = Chroma(
                persist_directory=persist_directory,
                embedding_function=self.embeddings
            )
            return
        
        print("📚 Indicizzazione progetti storici in corso...")
        
        documents = []
        
        # Carica tutti i PDF dalla cartella progetti
        if not os.path.exists(self.progetti_dir):
            os.makedirs(self.progetti_dir)
            print(f"⚠️  Cartella {self.progetti_dir} creata. Inserire PDF dei progetti storici.")
            return
        
        pdf_files = [f for f in os.listdir(self.progetti_dir) if f.endswith('.pdf')]
        
        if not pdf_files:
            print(f"⚠️  Nessun PDF trovato in {self.progetti_dir}. Inserire progetti storici.")
            return
        
        for pdf_file in pdf_files:
            pdf_path = os.path.join(self.progetti_dir, pdf_file)
            print(f"  - Processando {pdf_file}...")
            
            try:
                loader = PyPDFLoader(pdf_path)
                pages = loader.load()
                
                # Aggiungi metadata
                for page in pages:
                    page.metadata["source"] = pdf_file
                    page.metadata["progetto"] = pdf_file.replace(".pdf", "")
                
                documents.extend(pages)
                
                # Salva metadata del progetto
                self.progetti_metadata.append({
                    "nome_file": pdf_file,
                    "progetto": pdf_file.replace(".pdf", ""),
                    "num_pagine": len(pages)
                })
                
            except Exception as e:
                print(f"    ⚠️  Errore nel caricamento di {pdf_file}: {str(e)}")
        
        if not documents:
            print("⚠️  Nessun documento caricato correttamente.")
            return
        
        # Chunka i documenti
        print(f"✂️  Chunking di {len(documents)} pagine...")
        chunks = self.text_splitter.split_documents(documents)
        print(f"✅ Creati {len(chunks)} chunks")
        
        # Crea vectorstore
        print("🔮 Creazione embeddings e vectorstore...")
        self.vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=persist_directory
        )
        
        print(f"✅ Database creato con successo! {len(chunks)} chunks indicizzati.")
    
    def search_relevant_content(self, query: str, k: int = 5, filter_dict: Dict = None) -> List[Dict[str, Any]]:
        """
        Cerca contenuti semanticamente rilevanti
        
        Args:
            query: testo di ricerca
            k: numero di risultati
            filter_dict: filtri metadata opzionali
            
        Returns:
            lista di risultati con contenuto e metadata
        """
        if not self.vectorstore:
            raise Exception("Vectorstore non inizializzato. Eseguire ingest_progetti() prima.")
        
        # Ricerca semantica
        if filter_dict:
            results = self.vectorstore.similarity_search(query, k=k, filter=filter_dict)
        else:
            results = self.vectorstore.similarity_search(query, k=k)
        
        # Formatta risultati
        formatted_results = []
        for doc in results:
            formatted_results.append({
                "contenuto": doc.page_content,
                "progetto": doc.metadata.get("progetto", "Sconosciuto"),
                "source": doc.metadata.get("source", ""),
                "page": doc.metadata.get("page", 0)
            })
        
        return formatted_results
    
    def generate_draft(self, criterio: Dict[str, Any], progetti_context: List[Dict] = None) -> str:
        """
        Genera bozza offerta tecnica per un criterio specifico
        
        Args:
            criterio: dict con descrizione e punteggio del criterio
            progetti_context: contenuti rilevanti dai progetti (opzionale, altrimenti cerca automaticamente)
            
        Returns:
            testo della bozza generata
        """
        criterio_desc = criterio.get("descrizione", "")
        punteggio_max = criterio.get("punteggio_max", 0)
        
        # Se non forniti, cerca contenuti rilevanti
        if not progetti_context:
            query = f"{criterio_desc} soluzioni tecniche implementate"
            progetti_context = self.search_relevant_content(query, k=5)
        
        # Formatta progetti per il prompt
        progetti_formatted = ""
        for i, prog in enumerate(progetti_context, 1):
            progetti_formatted += f"\n\n--- PROGETTO {i}: {prog['progetto']} ---\n"
            progetti_formatted += f"Contenuto: {prog['contenuto'][:800]}...\n"
        
        # Genera bozza
        prompt = PromptTemplate(
            template=GENERATION_PROMPT,
            input_variables=["criterio_descrizione", "punteggio_max", "progetti_rilevanti"]
        )
        
        chain = prompt | self.llm
        
        response = chain.invoke({
            "criterio_descrizione": criterio_desc,
            "punteggio_max": punteggio_max,
            "progetti_rilevanti": progetti_formatted
        })
        
        return response.content.strip()
    
    def get_progetti_stats(self) -> Dict:
        """Ritorna statistiche sui progetti indicizzati"""
        if not self.vectorstore:
            return {"status": "non_inizializzato"}
        
        return {
            "status": "attivo",
            "num_progetti": len(self.progetti_metadata),
            "progetti": [p["progetto"] for p in self.progetti_metadata]
        }
