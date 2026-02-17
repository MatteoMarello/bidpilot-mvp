# BidPilot 2.0 - MVP

Sistema AI per analisi automatica bandi d'appalto pubblici con tecnologia anti-allucinazione.

## 🎯 Funzionalità

**Analisi Go/No-Go Bandi:**
- Estrazione automatica requisiti (SOA, certificazioni, scadenze)
- Matching intelligente con profilo aziendale
- Validazione geografica e temporale
- Score fattibilità 0-100 con spiegazione dettagliata
- Alert scadenze critiche

**Tecnologia Anti-Allucinazione:**
- Structured Output con Pydantic
- Validazione geografica (Roma ≠ Milano)
- Evidence-based extraction (citazione fonte)
- Controlli coerenza automatici

## 🚀 Quick Start

### 1. Installazione

```bash
# Installa dipendenze
pip install -r requirements.txt

# Verifica installazione
python test_installation.py
```

### 2. Configurazione

**Ottieni OpenAI API Key:**
- Vai su https://platform.openai.com/api-keys
- Crea key (formato: `sk-proj-...`)
- Costo stimato: ~€0.10-0.50 per bando

**Profilo aziendale:**
- Modifica `config/profilo_azienda.json`
- Campi essenziali: `nome_azienda`, `soa_possedute`, `certificazioni`

### 3. Avvio

```bash
streamlit run app.py
```

### 4. Utilizzo

1. Inserisci API Key nella sidebar
2. Carica PDF bando (max 100 pagine)
3. Click "ANALIZZA"
4. Visualizza risultati in 30-60 secondi

## 📁 Struttura

```
bidpilot_mvp/
├── app.py                   # App Streamlit
├── requirements.txt         # Dipendenze
├── test_installation.py     # Test setup
├── config/
│   └── profilo_azienda.json # Profilo (PERSONALIZZARE)
├── src/
│   ├── parser.py           # Parser PDF (pdfplumber)
│   ├── analyzer.py         # Logica analisi + validazione
│   ├── schemas.py          # Schemi Pydantic
│   ├── prompts.py          # Template prompt
│   └── rag_engine.py       # RAG per bozze (WIP)
└── data/
    └── progetti_storici/   # PDF progetti (opzionale)
```

## ⚙️ Configurazione Profilo

Esempio `config/profilo_azienda.json`:

```json
{
  "nome_azienda": "Tua Azienda S.r.l.",
  "aree_geografiche": ["Piemonte", "Lombardia"],
  "soa_possedute": [
    {
      "categoria": "OS6",
      "classifica": "III",
      "scadenza": "2026-09-15"
    }
  ],
  "certificazioni": [
    {
      "tipo": "ISO 14001",
      "scadenza": "2028-01-15"
    }
  ]
}
```

## 🐛 Troubleshooting

**"Module not found"**
```bash
pip install -r requirements.txt
```

**"API key invalid"**
- Verifica key su platform.openai.com
- Controlla crediti disponibili

**"PDF scansionato"**
- Usare PDF con testo selezionabile
- Evitare scansioni/immagini

**App lenta**
- PDF troppo grande: ridurre a <50 pagine
- Riavviare: Ctrl+C poi `streamlit run app.py`

## 📊 Stack Tecnologico

- **Frontend:** Streamlit 1.32
- **LLM:** GPT-4o (OpenAI)
- **Framework:** LangChain 0.1
- **Validation:** Pydantic 2.7
- **PDF:** pdfplumber 0.11
- **Vector DB:** ChromaDB 0.4 (per future bozze)

## 🔐 Privacy

- Profilo e PDF restano locali
- Invio testo a OpenAI solo per analisi
- Nessun training su dati utente (API policy)

## 💰 Costi

- Setup: Gratuito (tranne OpenAI API)
- Per bando: ~€0.10-0.50
- Con €20 credito: ~40-200 bandi

## 📝 Limitazioni MVP

**NON implementato:**
- Login multi-utente
- Export Word formattato
- Dashboard analytics
- Deploy cloud
- Alert email automatici

Saranno sviluppate in v2.0 dopo validazione MVP.

## 🆘 Supporto

**Problemi comuni:**
1. Controlla questo README
2. Esegui `python test_installation.py`
3. Verifica console per errori

## 📄 Licenza

Progetto tesi - Politecnico di Torino  
Sviluppo: Febbraio 2025  
Versione: 2.0-MVP

---

**Sviluppato con 💙 per semplificare le gare d'appalto**
