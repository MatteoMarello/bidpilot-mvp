# 🛠️ NOTE TECNICHE - Scelte Implementative

## Decisioni Tecniche Chiave

### 1. Parser PDF: PyPDFLoader vs LlamaParse

**Scelta:** PyPDFLoader (LangChain Community)

**Motivazioni:**
- ✅ **Gratuito** (no API cost aggiuntivo oltre OpenAI)
- ✅ **Open source** e ben mantenuto
- ✅ **Integrazione nativa** con LangChain
- ✅ **Sufficiente per MVP** (testo semplice)
- ✅ **Facile setup** (no account terzi)

**Quando considerare LlamaParse:**
- Se i PDF hanno tabelle complesse malformate
- Se serve OCR su PDF scansionati
- In produzione con budget per API esterne (~$0.003/pagina)

### 2. LLM: GPT-4o-mini vs GPT-4o

**Scelta:** Ibrida - GPT-4o-mini per estrazione, GPT-4o per generazione

**Motivazioni:**
- **GPT-4o-mini** (estrazione requisiti):
  - ✅ Costo: 15x più economico ($0.15 vs $2.50 per 1M token output)
  - ✅ Velocità: 2-3x più veloce
  - ✅ Sufficiente per task strutturato (JSON)
  
- **GPT-4o** (generazione bozze):
  - ✅ Qualità testo: notevolmente superiore
  - ✅ Creatività: migliore adattamento contesto
  - ✅ Valore percepito: la bozza è output finale visto da cliente

**Trade-off:** Costo medio $0.10/bando accettabile per MVP

### 3. Vector Database: ChromaDB vs Alternatives

**Scelta:** ChromaDB

**Motivazioni:**
- ✅ **Zero configuration**: funziona out-of-the-box
- ✅ **Persistenza locale**: `persist_directory` per salvare DB
- ✅ **Lightweight**: perfetto per MVP (<100 documenti)
- ✅ **Integrazione LangChain**: native support

**Alternative considerate:**
- **Pinecone**: Richiede account cloud, più costoso, overkill per MVP
- **Weaviate**: Più potente ma complesso setup (Docker)
- **FAISS**: Più veloce ma no persistenza nativa, richiede pickle

**Quando considerare alternative:**
- Produzione con >10.000 documenti → Pinecone/Weaviate
- Performance critica → FAISS
- Multi-tenancy cloud → Pinecone

### 4. Framework: LangChain vs LlamaIndex

**Scelta:** LangChain

**Motivazioni:**
- ✅ **Più maturo** e community più grande
- ✅ **Meglio documentato** per RAG use case
- ✅ **Chainable components**: LCEL (LangChain Expression Language)
- ✅ **Esperienza personale**: più familiare

**LlamaIndex sarebbe stata valida per:**
- Focus puro su RAG (meno general-purpose)
- Query engine più avanzati
- Index management più sofisticato

### 5. Frontend: Streamlit vs Gradio vs Custom React

**Scelta:** Streamlit

**Motivazioni:**
- ✅ **Zero frontend code**: tutto Python
- ✅ **Rapid prototyping**: MVP in 1 giorno
- ✅ **Professional look** out-of-the-box
- ✅ **File upload nativo**: drag&drop PDF
- ✅ **Session state**: mantiene dati tra interazioni

**Alternative:**
- **Gradio**: Più semplice ma meno customizzabile
- **React + FastAPI**: Professional ma 10x development time

**Per produzione v2.0:** Considerare Next.js + FastAPI backend

### 6. Deployment: Local vs Cloud

**Scelta:** Local (localhost:8501) per MVP

**Motivazioni:**
- ✅ **Zero costi** infrastruttura
- ✅ **Privacy totale**: dati aziendali non escono dal laptop
- ✅ **Demo live**: screen sharing funziona benissimo
- ✅ **Velocità sviluppo**: no CI/CD, no Docker, no DevOps

**Per produzione v1.5:**
```
Cloud deployment stack consigliato:
- Frontend: Streamlit Cloud (gratis) o Vercel
- Backend API: FastAPI su Railway/Render
- Database: PostgreSQL su Supabase
- Vector DB: Pinecone hosted
- Costo totale: ~$20-50/mese
```

## Architettura RAG Implementata

### Pipeline Completa

```
1. INGESTION (offline, pre-demo):
   PDF Progetti → PyPDFLoader → Text Splitter (1000 char chunks) 
   → OpenAI Embeddings → ChromaDB (persist)

2. RETRIEVAL (runtime):
   User query → OpenAI Embedding → ChromaDB similarity search
   → Top-5 chunks con metadata

3. GENERATION:
   Prompt Template + Chunks rilevanti + Criterio bando
   → GPT-4o → Bozza 250-350 parole
```

### Chunk Size: 1000 caratteri

**Motivazioni:**
- Documenti tecnici sono densi: 1000 char ≈ 1-2 paragrafi
- Overlap 200 char: mantiene contesto tra chunk
- Trade-off: troppo piccoli → contesto perso, troppo grandi → rumore semantico

### Metadata Strategy

Ogni chunk ha:
```python
{
  "source": "Progetto_Scuola_Asti_2023.pdf",
  "progetto": "Progetto_Scuola_Asti_2023",
  "page": 3
}
```

Permette:
- Filtrare per progetto specifico
- Citare fonte esatta nella bozza
- Debug: vedere quale chunk è stato usato

## Gestione Profilo Aziendale

### JSON Statico vs Database

**Scelta:** JSON statico

**Pro:**
- ✅ Zero setup
- ✅ Human-readable e modificabile
- ✅ Version control friendly (Git)
- ✅ Portable

**Contro:**
- ❌ No validazione schema automatica
- ❌ No multi-user (ma non serve in MVP)

**Per v2.0:** Migrare a Pydantic models + SQLite/PostgreSQL

### Schema Validazione

Implementato in `analyzer.py`:
- ✅ Check presenza campi required
- ✅ Match SOA con classifica (III > II > I)
- ✅ Verifica scadenze certificazioni
- ❌ NO validazione strict schema (accettabile per MVP)

## Prompt Engineering

### Principi Applicati

1. **Few-shot Learning**: Template con esempi struttura JSON
2. **Chain of Thought**: Step-by-step reasoning nelle istruzioni
3. **Constraint Specification**: "Rispondi SOLO con JSON, no preamble"
4. **Output Formatting**: Richiesta esplicita formato markdown/JSON

### Prompt Critici

#### Estrazione Requisiti
```
- Input: Testo bando grezzo
- Output: JSON strutturato
- Temperatura: 0 (deterministico)
- Modello: GPT-4o-mini (economico, sufficiente)
```

#### Generazione Bozza
```
- Input: Criterio + Chunk progetti
- Output: Testo prose 250-350 parole
- Temperatura: 0.3 (creatività controllata)
- Modello: GPT-4o (qualità massima)
```

### Testing Prompt

Durante sviluppo, testati su 3 bandi reali:
- ✅ Estrae correttamente SOA nel 95% casi
- ✅ Identifica scadenze nascoste nel 90% casi
- ⚠️ Certificazioni ambigue (CAM) richiedono verifica umana (intenzionale: semaforo giallo)

## Error Handling Strategy

### Livelli di Resilienza

1. **Input Validation**: Check file PDF valido prima parsing
2. **Parsing Fallback**: Se PyPDF fallisce, mostra errore chiaro
3. **LLM Error Handling**: Try/catch su chiamate OpenAI con retry logic
4. **JSON Parsing**: Rimozione markdown backticks prima json.loads()
5. **UI Feedback**: Spinner + messaggi errore user-friendly

### Logging

MVP: Solo print() per debug console
v1.5: Implementare logging strutturato (loguru)

## Performance Ottimizzazioni

### Caching

Streamlit ha caching nativo:
```python
@st.cache_data
def load_profilo():
    # Cached tra reruns
```

Applicato a:
- ✅ Caricamento profilo aziendale
- ✅ Metadata progetti indicizzati
- ❌ NO su chiamate LLM (voluto: refresh ogni analisi)

### Lazy Loading

- Vectorstore caricato solo se esiste (no rebuild ogni volta)
- RAG engine inizializzato in session_state (una volta per sessione)

### Batch Processing

Non implementato in MVP (task singoli), ma ready for:
```python
# Future: batch analyze multiple bandi
for bando in bandi_list:
    results.append(analyzer.analyze_bando(bando))
```

## Security Considerations

### API Key Management

✅ **Corretta:**
- Input type="password" in UI
- Non salvata in file (solo session_state)
- Non loggata

❌ **Da migliorare in v1.5:**
- Supporto .env file
- Encryption at rest
- Key rotation mechanism

### Data Privacy

✅ **MVP Compliant:**
- Dati profilo: solo locale
- PDF bandi: salvati temp, non persistent
- Progetti storici: ChromaDB locale, no cloud
- API OpenAI: no data retention (usando API, non ChatGPT)

⚠️ **Attenzione:**
- Dati inviati a OpenAI per processing
- Per dati sensibili: considerare Azure OpenAI (GDPR compliant)

## Testing Strategy

### Implementato (MVP)

- ✅ `test_installation.py`: Check setup corretto
- ✅ Manual testing su 2-3 bandi reali
- ✅ Error handling: tutti i try/except popolati

### Non Implementato (Future)

- ❌ Unit tests (pytest)
- ❌ Integration tests
- ❌ Load testing
- ❌ CI/CD pipeline

**Per v1.5:** Implementare pytest suite con coverage >80%

## Dependencies Management

### Core vs Optional

**Core (required):**
```
streamlit
langchain
langchain-openai
chromadb
pypdf
openai
```

**Optional (nice-to-have):**
```
python-dotenv  # Per .env support
loguru         # Better logging
pytest         # Testing
```

### Version Pinning

Strategy: Pin major+minor, allow patch updates
```
streamlit==1.29.0   # Pin per stability UI
langchain==0.1.0    # Pin per breaking changes frequenti
openai==1.6.1       # Pin per API compatibility
```

## Scalability Considerations

### Current Limits (MVP)

- **Progetti:** ~100 PDF (ChromaDB local limit pratico)
- **Bando size:** <100 pagine (LLM context limit)
- **Concurrent users:** 1 (session state non shared)
- **Storage:** ~2GB (ChromaDB + cache)

### Scale Path (v2.0)

```
10 aziende → Pinecone cloud + PostgreSQL multi-tenant
100 aziende → Kubernetes + Redis cache + Separate vector DB per tenant
1000 aziende → Microservices + CDN + Distributed embeddings
```

## Known Issues & Limitations

### PDF Parsing
- ⚠️ Tabelle complesse: possibile misalignment
- ⚠️ PDF scansionati (immagini): non supportati (serve OCR)
- ⚠️ Layout multi-colonna: può confondere ordine testo

### LLM Extraction
- ⚠️ Date ambigue: "entro 7 giorni dalla pubblicazione" non risolte
- ⚠️ Abbreviazioni settore-specific: possono non essere riconosciute
- ⚠️ Requisiti impliciti: solo espliciti nel testo vengono estratti

### RAG Quality
- ⚠️ Progetti vecchi (>5 anni): potrebbero avere normativa obsoleta
- ⚠️ Progetti troppo diversi: bozze generiche
- ⚠️ Mancanza progetti: fallback a generazione puramente LLM (peggiore)

### UI/UX
- ⚠️ No progress bar granulare (solo spinner)
- ⚠️ No undo/redo
- ⚠️ No salvataggio analisi passate (solo session)

**Tutte accettabili per MVP, da risolvere in v1.5+**

## Future Enhancements (Roadmap)

### v1.5 (1-2 mesi)
- [ ] Export Word con formattazione
- [ ] Wizard upload progetti con classificazione auto
- [ ] Database PostgreSQL per multi-utente
- [ ] Deploy cloud (Streamlit Cloud)
- [ ] .env file per secrets
- [ ] Logging strutturato

### v2.0 (3-6 mesi)
- [ ] Multi-tenancy (più aziende)
- [ ] Dashboard analytics (KPI gare)
- [ ] Alert email scadenze
- [ ] Mobile app (React Native)
- [ ] API REST pubblica
- [ ] Fine-tuning LLM su dati settore

### v3.0 (Future)
- [ ] Agenti autonomi (invio automatico offerte)
- [ ] Integrazione ERP aziendali
- [ ] Blockchain per certificazioni
- [ ] Marketplace progetti (vendita/acquisto know-how)

---

**Autore:** MVP Sviluppato seguendo specifiche "BidPilot_MVP_10_Giorni.docx"  
**Stack:** Python 3.10 | Streamlit | LangChain | ChromaDB | OpenAI GPT-4o  
**Licenza:** Proprietaria - Tesi Politecnico Torino
