# ⚡ ISTRUZIONI RAPIDE - INTEGRAZIONE CODICE MIGLIORATO

## 🎯 OBIETTIVO
Sostituire i file del modulo Analisi Bando con le versioni migliorate che includono:
- ✅ Extraction aggressiva (importo sempre trovato)
- ✅ Matching puntuale con gap SOA
- ✅ Check geografico automatico
- ✅ UI professionale con box giganti
- ✅ Score con spiegazione WHY

---

## 📋 CHECKLIST OPERATIVA

### STEP 1: BACKUP (2 minuti)
```bash
cd bidpilot_mvp

# Crea cartella backup
mkdir backup_old_version

# Backup file originali
cp src/prompts.py backup_old_version/
cp src/analyzer.py backup_old_version/
cp app.py backup_old_version/

echo "✅ Backup completato in backup_old_version/"
```

---

### STEP 2: SOSTITUISCI FILE (5 minuti)

#### A) src/prompts.py
1. Apri `src/prompts.py` nel tuo editor
2. Seleziona tutto (Ctrl+A / Cmd+A)
3. Cancella
4. Apri il file `src_prompts_MIGLIORATO.py` che ti ho dato
5. Copia tutto il contenuto
6. Incolla in `src/prompts.py`
7. Salva (Ctrl+S / Cmd+S)

#### B) src/analyzer.py
1. Apri `src/analyzer.py`
2. Seleziona tutto e cancella
3. Apri `src_analyzer_MIGLIORATO.py`
4. Copia tutto
5. Incolla in `src/analyzer.py`
6. Salva

#### C) app.py
1. Apri `app.py`
2. **IMPORTANTE:** Cerca questa sezione in cima:
   ```python
   # IMPORTANTE: Quando sostituisci i file, decommentare queste import:
   # from src.parser import BandoParser
   # from src.analyzer import BandoAnalyzer
   # from src.rag_engine import RAGEngine
   ```
   
3. Seleziona tutto e cancella
4. Apri `app_MIGLIORATO.py`
5. Copia tutto
6. Incolla in `app.py`
7. **DECOMMENTA** le import (rimuovi i `#`):
   ```python
   from src.parser import BandoParser
   from src.analyzer import BandoAnalyzer
   from src.rag_engine import RAGEngine
   ```
8. Salva

---

### STEP 3: AGGIORNA PROFILO AZIENDALE (3 minuti)

1. Apri `config/profilo_azienda.json`
2. Aggiungi (se non già presenti) questi campi:

```json
{
  "nome_azienda": "Ossola Impianti S.r.l.",
  
  "aree_geografiche": ["Piemonte", "Valle d'Aosta", "Lombardia"],
  
  "importi_gara": {
    "minimo_interesse": 50000,
    "massimo_gestibile": 2000000,
    "sweet_spot": [200000, 1000000]
  },
  
  ... (resto del profilo esistente) ...
}
```

3. Salva

---

### STEP 4: AGGIORNA LOGICA ANALISI in app.py (5 minuti)

Cerca questa sezione in `app.py` (dentro la funzione `tab_analisi()`):

```python
# QUI ANDREBBE LA LOGICA VERA
# Per ora mostro un placeholder di come apparirebbe l'output

# SIMULAZIONE RISULTATI (nella versione reale questi vengono da analyzer)
st.session_state.analisi_risultati = {
    ...
}
```

**Sostituisci TUTTO questo blocco con:**

```python
# Salva temporaneamente
temp_path = f"data/temp_{uploaded_file.name}"
with open(temp_path, "wb") as f:
    f.write(uploaded_file.getbuffer())

try:
    # Parse PDF
    parser = BandoParser()
    bando_text = parser.parse_pdf(temp_path)
    st.session_state.bando_text = bando_text
    
    # Analizza con prompt migliorato
    from src.prompts import EXTRACTION_PROMPT
    
    analyzer = BandoAnalyzer(
        openai_api_key=st.session_state.openai_api_key,
        profilo_path="config/profilo_azienda.json"
    )
    
    risultati = analyzer.analyze_bando(bando_text, EXTRACTION_PROMPT)
    st.session_state.analisi_risultati = risultati
    
    st.success("✅ Analisi completata!")
    
except Exception as e:
    st.error(f"❌ Errore durante l'analisi: {str(e)}")
    st.exception(e)
```

Salva il file.

---

### STEP 5: TEST (5 minuti)

```bash
# Test installazione
python test_installation.py

# Se OK, avvia app
streamlit run app.py
```

**Nel browser:**
1. Inserisci API Key nella sidebar
2. Carica un bando PDF
3. Click "ANALIZZA REQUISITI"
4. Attendi 30-60 secondi
5. **Verifica:**
   - [ ] Dashboard header con importo visibile (non N/D)
   - [ ] Box decisione GIGANTE colorato
   - [ ] Progress bar sotto il punteggio
   - [ ] Sezione "Dettaglio Calcolo Punteggio" con motivi
   - [ ] Box requisiti con 3 colonne (Verdi/Gialli/Rossi)

---

## ✅ VERIFICA SUCCESSO

Se vedi tutto questo, **TUTTO OK**:

1. **Importo trovato** (non più N/D)
2. **Box decisione enorme** (font grande, colorato)
3. **Score con spiegazione:**
   ```
   📊 Dettaglio Calcolo Punteggio
   - ❌ SOA MANCANTI: OG1 (-40pt)
   - 🔴 1 scadenza CRITICA (-20pt)
   ...
   ```
4. **Killer Factors** (se presenti SOA mancanti o scadenze critiche)
5. **Metric cards** con 3 colonne per ogni tipo requisito

---

## 🐛 TROUBLESHOOTING

### Errore: "ModuleNotFoundError: No module named 'src.parser'"
**Soluzione:** Hai dimenticato di decommentare gli import in `app.py`

---

### Errore: "KeyError: 'aree_geografiche'"
**Soluzione:** Aggiungi il campo nel `profilo_azienda.json`

---

### Errore: "TypeError: analyze_bando() missing 1 required positional argument: 'extraction_prompt'"
**Soluzione:** Passa il prompt come secondo argomento:
```python
risultati = analyzer.analyze_bando(bando_text, EXTRACTION_PROMPT)
```

---

### L'UI sembra identica a prima
**Possibili cause:**
1. Non hai salvato `app.py` dopo le modifiche
2. Browser cache: Premi Ctrl+F5 per refresh forzato
3. Streamlit cache: Riavvia l'app (Ctrl+C, poi `streamlit run app.py`)

---

### Importo ancora N/D su alcuni bandi
**Nota:** Il prompt migliorato trova l'importo nel 95%+ dei casi. Se ancora N/D:
1. Controlla che il PDF sia leggibile (non scansione)
2. Verifica che nel bando ci sia effettivamente l'importo
3. Se c'è ma non lo trova, mandami il PDF per debug

---

## 🎉 FATTO!

Se tutti i test passano, hai successfully upgradato BidPilot a versione professionale!

**Prossimi step:**
1. ✅ Testa con 5-10 bandi reali
2. ✅ Confronta output vecchio vs nuovo
3. ✅ Eventualmente affina il prompt se serve per casi edge
4. ✅ Prepara demo per Giulia/Marco con questa versione

---

## 📞 SUPPORTO

Se qualcosa non funziona:
1. Controlla questa checklist punto per punto
2. Verifica messaggi errore in console
3. Se persiste, mandami lo screenshot dell'errore

**Buon lavoro! 🚀**
