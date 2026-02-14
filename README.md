# BidPilot 2.0 - MVP

Sistema di Intelligenza Artificiale per analisi automatica di bandi d'appalto pubblici e generazione bozze offerte tecniche.

## 🎯 Funzionalità

### 1. Analisi Bando Go/No-Go
- **Estrazione automatica requisiti** da PDF del bando (SOA, certificazioni, scadenze, figure professionali)
- **Matching intelligente** con profilo aziendale
- **Semafori operativi**: Verde/Giallo/Rosso per ogni requisito
- **Alert scadenze critiche** con calcolo giorni residui
- **Decisione suggerita** con punteggio di fattibilità (0-100)

### 2. Generazione Bozza Offerta Tecnica
- **RAG (Retrieval-Augmented Generation)** su database progetti storici
- **Ricerca semantica** di contenuti rilevanti da progetti passati vincenti
- **Generazione bozza** per singoli criteri di valutazione
- **Citazioni progetti** per tracciabilità soluzioni tecniche

## 📋 RequisiTI
- Python 3.10+
- OpenAI API Key (per GPT-4o-mini e GPT-4o)
- ~2GB spazio disco per ChromaDB

## 🚀 Installazione

### 1. Clona o scarica il progetto

```bash
cd bidpilot_mvp
```

### 2. Crea ambiente virtuale (consigliato)

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# oppure
venv\Scripts\activate  # Windows
```

### 3. Installa dipendenze

```bash
pip install -r requirements.txt
```

### 4. Configura profilo aziendale

Il file `config/profilo_azienda.json` contiene i dati della tua azienda (SOA, certificazioni, fatturato).

**È già precompilato con dati di esempio (Ossola Impianti).** 

Per personalizzarlo:
```bash
# Modifica il file con i tuoi dati reali
nano config/profilo_azienda.json
```

Campi principali:
- `nome_azienda`: nome società
- `soa_possedute`: array di SOA con categoria, classifica, scadenza
- `certificazioni`: ISO, attestazioni varie
- `fatturato`: ultimi 3 anni diviso per categoria
- `collaboratori_esterni_abituali`: consulenti utilizzati in passato

### 5. Prepara progetti storici

Crea una cartella `data/progetti_storici/` e inserisci i PDF di:
- Offerte tecniche vinte
- Relazioni tecniche di progetti passati
- Capitolati esecutivi
- Qualsiasi documento tecnico riutilizzabile

```bash
mkdir -p data/progetti_storici
# Copia i tuoi PDF in questa cartella
cp /path/to/progetto1.pdf data/progetti_storici/
cp /path/to/progetto2.pdf data/progetti_storici/
```

**Nota:** Più progetti inserisci, migliore sarà la qualità delle bozze generate.

## 🎮 Utilizzo

### 1. Avvia l'applicazione

```bash
streamlit run app.py
```

L'app si aprirà automaticamente nel browser su `http://localhost:8501`

### 2. Configura API Key

Nella **sidebar sinistra**:
1. Inserisci la tua OpenAI API Key
2. Clicca **"Indicizza Progetti Storici"**
   - Prima volta: richiede ~30-60 sec
   - Crea database vettoriale in `data/chroma_db/`

### 3. Analizza un bando (Tab 1)

1. **Carica PDF** del disciplinare/bando
2. Clicca **"Analizza Requisiti"**
3. Attendi 30-60 secondi
4. Visualizza:
   - Scadenze critiche con giorni residui
   - Requisiti SOA: ✅ posseduti / ❌ mancanti
   - Certificazioni: ✅ presenti / 🟡 da verificare
   - Figure professionali: ✅ interne / 🟡 consulenti esterni
   - **Decisione suggerita**: PARTECIPARE / CAUTELA / NON PARTECIPARE

### 4. Genera bozza offerta (Tab 2)

1. Dopo aver analizzato il bando, vai su **"Genera Bozza"**
2. **Seleziona criterio** dal dropdown (es: "Criterio A - Prestazioni Energetiche")
3. Clicca **"Genera Bozza con AI"**
4. Sistema:
   - Cerca automaticamente progetti simili nel database
   - Genera bozza 250-350 parole
   - Mostra progetti utilizzati come riferimento
5. **Copia/Download** la bozza e personalizzala

## 📁 Struttura Progetto

```
bidpilot_mvp/
├── app.py                          # Applicazione Streamlit principale
├── requirements.txt                # Dipendenze Python
├── config/
│   └── profilo_azienda.json       # Profilo aziendale (PERSONALIZZARE!)
├── src/
│   ├── parser.py                  # Parser PDF con PyPDFLoader
│   ├── analyzer.py                # Analisi Go/No-Go e matching
│   ├── rag_engine.py              # RAG con ChromaDB
│   └── prompts.py                 # Template prompt per LLM
├── data/
│   ├── progetti_storici/          # INSERIRE QUI i PDF progetti
│   └── chroma_db/                 # Database vettoriale (auto-generato)
└── README.md                       # Questo file
```

## 🔧 Troubleshooting

### Errore: "OpenAI API Key not valid"
- Verifica che la key sia corretta
- Controlla crediti disponibili su platform.openai.com

### Errore: "No PDF found in progetti_storici"
- Inserisci almeno 1 PDF nella cartella `data/progetti_storici/`
- Riclicca "Indicizza Progetti Storici"

### Database ChromaDB corrotto
```bash
rm -rf data/chroma_db/
# Poi riavvia app e riindicizza progetti
```

### Performance lenta
- PDF troppo grandi: riduci a <50 pagine se possibile
- Troppi progetti: inizia con 5-10 PDF rappresentativi

## 🧪 Testing Rapido (Senza Progetti)

Se vuoi testare SOLO la funzione di analisi bando:

1. Avvia app: `streamlit run app.py`
2. Inserisci API key
3. **Salta** l'indicizzazione progetti
4. Vai su "Analisi Bando"
5. Carica un PDF di bando
6. Analizza

La generazione bozze NON funzionerà senza progetti indicizzati (è intenzionale).

## 💡 Consigli per Demo

### Demo a Cliente (Giulia/Marco)
1. **Pre-carica** il loro profilo aziendale in `config/profilo_azienda.json`
2. **Pre-indicizza** 5-7 loro progetti storici in `data/progetti_storici/`
3. Durante demo:
   - Condividi schermo
   - Carica un loro bando reale recente
   - Analizza in diretta
   - Mostra semafori e scadenze
   - Genera bozza per 1-2 criteri
4. Enfatizza:
   - Tempo risparmiato (30min → 5min)
   - Sicurezza nel non perdere requisiti nascosti
   - Riutilizzo know-how aziendale

## 🔐 Privacy & Sicurezza

- **Dati locali**: Profilo aziendale e progetti restano sul tuo computer
- **ChromaDB**: Database vettoriale salvato localmente in `data/chroma_db/`
- **OpenAI API**: I testi vengono inviati a OpenAI solo per analisi/generazione
  - Non vengono usati per training di modelli pubblici (conforme API policy OpenAI)
  - Usa API key aziendale per controllo completo

## 📊 Limitazioni MVP

Questa è una versione **MVP (Minimum Viable Product)**. NON include:
- ❌ Login multi-utente
- ❌ Form configurazione profilo (usa JSON manuale)
- ❌ Wizard upload progetti con classificazione AI
- ❌ Export Word con formattazione
- ❌ Dashboard analytics
- ❌ Alert email automatici
- ❌ Deploy cloud (gira solo in locale)

Queste funzionalità saranno sviluppate nelle versioni successive (v1.5, v2.0).

## 🆘 Supporto

Per problemi o domande:
1. Controlla questo README
2. Verifica i requisiti tecnici
3. Controlla la console per errori Python

## 📝 Licenza

Progetto di tesi - Politecnico di Torino
Sviluppato come MVP dimostrativo

---

**Versione:** 1.0-MVP  
**Ultimo aggiornamento:** Febbraio 2025  
**Stack:** Python 3.10+ | Streamlit | LangChain | ChromaDB | OpenAI GPT-4o
