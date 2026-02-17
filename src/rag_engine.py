"""RAG Engine per generazione bozze offerte tecniche"""
import os
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate

from src.prompts import GENERATION_PROMPT


class RAGEngine:
    """Engine RAG per recupero e generazione contenuti da progetti storici"""
    
    def __init__(self, openai_api_key: str, progetti_dir: str = "data/progetti_storici"):
        self.api_key = openai_api_key
        self.progetti_dir = progetti_dir
        
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.3, api_key=openai_api_key)
        self.embeddings = OpenAIEmbeddings(api_key=openai_api_key)
        
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " "]
        )
        
        self.vectorstore = None
        self.metadata = []
    
    def ingest_progetti(self, force_rebuild: bool = False) -> None:
        """Indicizza PDF progetti in ChromaDB"""
        persist_dir = "data/chroma_db"
        
        # Carica esistente se disponibile
        if os.path.exists(persist_dir) and not force_rebuild:
            print(f"📚 Caricamento DB da {persist_dir}...")
            self.vectorstore = Chroma(persist_directory=persist_dir, embedding_function=self.embeddings)
            return
        
        print("📚 Indicizzazione progetti...")
        
        if not os.path.exists(self.progetti_dir):
            os.makedirs(self.progetti_dir)
            print(f"⚠️ Cartella {self.progetti_dir} creata. Inserire PDF progetti.")
            return
        
        pdf_files = [f for f in os.listdir(self.progetti_dir) if f.endswith('.pdf')]
        
        if not pdf_files:
            print(f"⚠️ Nessun PDF in {self.progetti_dir}")
            return
        
        documents = []
        
        for pdf in pdf_files:
            path = os.path.join(self.progetti_dir, pdf)
            print(f"  - {pdf}...")
            
            try:
                loader = PyPDFLoader(path)
                pages = loader.load()
                
                for page in pages:
                    page.metadata["source"] = pdf
                    page.metadata["progetto"] = pdf.replace(".pdf", "")
                
                documents.extend(pages)
                self.metadata.append({"nome": pdf, "progetto": pdf.replace(".pdf", ""), "pagine": len(pages)})
                
            except Exception as e:
                print(f"    ⚠️ Errore: {e}")
        
        if not documents:
            print("⚠️ Nessun documento caricato")
            return
        
        print(f"✂️ Chunking {len(documents)} pagine...")
        chunks = self.splitter.split_documents(documents)
        print(f"✅ {len(chunks)} chunks creati")
        
        print("🔮 Creazione embeddings...")
        self.vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=persist_dir
        )
        
        print(f"✅ DB creato! {len(chunks)} chunks indicizzati")
    
    def search_content(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Cerca contenuti rilevanti"""
        if not self.vectorstore:
            raise Exception("Vectorstore non inizializzato. Eseguire ingest_progetti()")
        
        results = self.vectorstore.similarity_search(query, k=k)
        
        return [{
            "contenuto": doc.page_content,
            "progetto": doc.metadata.get("progetto", "Sconosciuto"),
            "source": doc.metadata.get("source", ""),
            "page": doc.metadata.get("page", 0)
        } for doc in results]
    
    def generate_draft(self, criterio: Dict[str, Any], context: List[Dict] = None) -> str:
        """Genera bozza offerta per criterio"""
        desc = criterio.get("descrizione", "")
        punti = criterio.get("punteggio_max", 0)
        
        if not context:
            context = self.search_content(f"{desc} soluzioni tecniche", k=5)
        
        progetti_text = ""
        for i, p in enumerate(context, 1):
            progetti_text += f"\n--- PROGETTO {i}: {p['progetto']} ---\n{p['contenuto'][:800]}...\n"
        
        prompt = PromptTemplate(
            template=GENERATION_PROMPT,
            input_variables=["criterio_descrizione", "punteggio_max", "progetti_rilevanti"]
        )
        
        chain = prompt | self.llm
        
        response = chain.invoke({
            "criterio_descrizione": desc,
            "punteggio_max": punti,
            "progetti_rilevanti": progetti_text
        })
        
        return response.content.strip()
    
    def get_stats(self) -> Dict:
        """Statistiche progetti indicizzati"""
        if not self.vectorstore:
            return {"status": "non_inizializzato"}
        
        return {
            "status": "attivo",
            "num_progetti": len(self.metadata),
            "progetti": [p["progetto"] for p in self.metadata]
        }
