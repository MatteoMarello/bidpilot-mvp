# 📝 ESEMPIO COMPLETO - FUNZIONE tab_analisi() CON LOGICA INTEGRATA

Questo è l'esempio completo di come deve essere la funzione `tab_analisi()` in `app.py` 
dopo aver sostituito la simulazione con la logica vera.

```python
def tab_analisi():
    """Tab 1: Analisi Bando Go/No-Go - VERSIONE MIGLIORATA"""
    st.header("📊 Analisi Intelligente Bando")
    
    if not st.session_state.openai_api_key:
        st.warning("⚠️ Inserire OpenAI API Key nella sidebar per continuare")
        return
    
    # Upload PDF
    uploaded_file = st.file_uploader(
        "📄 Carica Disciplinare/Bando (PDF)",
        type=['pdf'],
        help="Carica il PDF del bando da analizzare (max 200 pagine)"
    )
    
    if uploaded_file:
        st.success(f"✅ File caricato: **{uploaded_file.name}**")
        
        # Bottone analisi GRANDE
        if st.button("🔍 ANALIZZA REQUISITI", type="primary", use_container_width=True):
            st.info("🤖 **Analisi in corso...** Il sistema sta leggendo il bando e confrontando con il tuo profilo aziendale (30-60 secondi)")
            
            # ========== INIZIO LOGICA VERA ==========
            
            # Salva file temporaneamente
            temp_path = f"data/temp_{uploaded_file.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            try:
                # Step 1: Parse PDF
                parser = BandoParser()
                bando_text = parser.parse_pdf(temp_path)
                st.session_state.bando_text = bando_text
                
                # Step 2: Analizza con prompt migliorato
                from src.prompts import EXTRACTION_PROMPT
                
                analyzer = BandoAnalyzer(
                    openai_api_key=st.session_state.openai_api_key,
                    profilo_path="config/profilo_azienda.json"
                )
                
                # Chiama analyze_bando con extraction_prompt
                risultati = analyzer.analyze_bando(bando_text, EXTRACTION_PROMPT)
                
                # Salva in session state
                st.session_state.analisi_risultati = risultati
                
                st.success("✅ Analisi completata!")
                
            except Exception as e:
                # Gestione errori dettagliata
                error_text = str(e)
                
                if "insufficient_quota" in error_text or "exceeded your current quota" in error_text:
                    st.error("❌ **Credito API esaurito:** Ricarica/abilita billing su OpenAI e riprova.")
                else:
                    st.error(f"❌ **Errore durante l'analisi:** {error_text}")
                st.exception(e)
                
                # Non mostrare risultati se c'è errore
                return
            
            # ========== FINE LOGICA VERA ==========
    
    # ========== RENDERING RISULTATI ==========
    # (Questa parte rimane identica a quella nel file app_MIGLIORATO.py)
    
    if st.session_state.analisi_risultati:
        risultati = st.session_state.analisi_risultati
        
        st.markdown("---")
        
        # 1. DASHBOARD HEADER
        render_dashboard_header(risultati)
        
        # 2. DECISIONE GIGANTE
        render_decisione_gigante(
            risultati["decisione"],
            risultati["punteggio_fattibilita"],
            risultati["motivi_punteggio"]
        )
        
        # 3. CHECK GEOGRAFICO
        render_check_geografico(risultati["check_geografico"])
        
        # 4. KILLER FACTORS
        render_killer_factors(
            risultati["soa"]["rossi"],
            risultati["scadenze"]["critiche"],
            risultati["certificazioni"]["rossi"]
        )
        
        st.markdown("---")
        
        # 5. SCADENZE COUNTDOWN
        render_scadenze_countdown(risultati["scadenze"])
        
        st.markdown("---")
        
        # 6. REQUISITI DETTAGLIATI
        render_requisiti_box(
            "📜 Requisiti SOA",
            risultati["soa"]["verdi"],
            risultati["soa"]["gialli"],
            risultati["soa"]["rossi"],
            "soa"
        )
        
        st.markdown("---")
        
        render_requisiti_box(
            "🏆 Certificazioni",
            risultati["certificazioni"]["verdi"],
            risultati["certificazioni"]["gialli"],
            risultati["certificazioni"]["rossi"],
            "cert"
        )
        
        st.markdown("---")
        
        render_requisiti_box(
            "👥 Figure Professionali",
            risultati["figure_professionali"]["verdi"],
            risultati["figure_professionali"]["gialli"],
            risultati["figure_professionali"]["rossi"],
            "figure"
        )
```

---

## 🔍 PUNTI CHIAVE DA NOTARE

### 1. Import del prompt
```python
from src.prompts import EXTRACTION_PROMPT
```
Questo permette di usare il prompt migliorato con le istruzioni aggressive.

### 2. Chiamata analyze_bando
```python
risultati = analyzer.analyze_bando(bando_text, EXTRACTION_PROMPT)
```
**ATTENZIONE:** Passa due argomenti:
- `bando_text`: il testo estratto dal PDF
- `EXTRACTION_PROMPT`: il template prompt migliorato

**Nella versione vecchia c'era solo:** `analyzer.analyze_bando(bando_text)`  
**Questo causava errore perché la versione nuova richiede anche il prompt.**

### 3. Gestione errori
```python
try:
    # ... analisi ...
except Exception as e:
    if "insufficient_quota" in error_text:
        st.error("❌ Credito API esaurito...")
    else:
        st.error(f"❌ Errore: {error_text}")
    st.exception(e)
    return  # IMPORTANTE: non mostrare risultati se c'è errore
```

Il `return` impedisce di mostrare l'interfaccia risultati se l'analisi fallisce.

### 4. File temporaneo
```python
temp_path = f"data/temp_{uploaded_file.name}"
with open(temp_path, "wb") as f:
    f.write(uploaded_file.getbuffer())
```

Streamlit fornisce l'uploaded_file come buffer in memoria. Dobbiamo salvarlo 
su disco temporaneamente per PyPDFLoader.

**Nota:** Il file verrà sovrascritto al prossimo upload. Va bene per MVP.  
In produzione potresti voler aggiungere timestamp: `temp_20250215_143022_bando.pdf`

---

## 📋 CHECKLIST INTEGRITÀ CODICE

Dopo aver sostituito, verifica che ci siano:

- [ ] `from src.parser import BandoParser` in cima (decommentato)
- [ ] `from src.analyzer import BandoAnalyzer` in cima (decommentato)
- [ ] `from src.prompts import EXTRACTION_PROMPT` dentro tab_analisi()
- [ ] `analyzer.analyze_bando(bando_text, EXTRACTION_PROMPT)` con DUE argomenti
- [ ] Blocco `try/except` per gestione errori
- [ ] `return` nel blocco except per non mostrare UI se errore
- [ ] Tutte le funzioni render_* (dashboard_header, decisione_gigante, ecc) presenti

---

## 🧪 TEST STEP-BY-STEP

1. **Avvia app:** `streamlit run app.py`
2. **Inserisci API key** nella sidebar
3. **Carica PDF** di un bando
4. **Click "ANALIZZA"**
5. **Attendi** 30-60 secondi
6. **Console non deve mostrare errori**
7. **Browser deve mostrare:**
   - Dashboard header viola con importo
   - Box decisione GIGANTE colorato
   - Progress bar
   - Lista motivi punteggio
   - Metric cards con 3 colonne

Se vedi tutto questo → ✅ **INTEGRAZIONE RIUSCITA!**

---

## ⚠️ ERRORI COMUNI E SOLUZIONI

### Errore: "analyze_bando() takes 2 positional arguments but 3 were given"
**Causa:** Versione vecchia di analyzer.py ancora presente  
**Soluzione:** Assicurati di aver sostituito `src/analyzer.py` con la versione nuova

---

### Errore: "name 'EXTRACTION_PROMPT' is not defined"
**Causa:** Import mancante  
**Soluzione:** Aggiungi `from src.prompts import EXTRACTION_PROMPT` nella funzione

---

### Errore: "KeyError: 'motivi_punteggio'"
**Causa:** Risultati vecchi in cache di Streamlit  
**Soluzione:**
1. Ferma app (Ctrl+C)
2. Cancella cache: `rm -rf .streamlit/`
3. Riavvia: `streamlit run app.py`

---

### UI identica a prima, nessun cambiamento visivo
**Causa:** File CSS non applicato o browser cache  
**Soluzione:**
1. Hard refresh browser: Ctrl+Shift+R (Windows) o Cmd+Shift+R (Mac)
2. Verifica che `st.markdown("""<style>...</style>""", unsafe_allow_html=True)` sia presente in cima

---

### Importo ancora "N/D" su bandi dove dovrebbe esserci
**Causa:** Prompt vecchio ancora in uso  
**Soluzione:**
1. Verifica di aver sostituito `src/prompts.py`
2. Verifica che `EXTRACTION_PROMPT` sia importato correttamente
3. Aggiungi print per debug:
   ```python
   from src.prompts import EXTRACTION_PROMPT
   print(f"Prompt length: {len(EXTRACTION_PROMPT)}")  # Dovrebbe essere ~4000+ char
   ```

---

## 🚀 DOPO IL SUCCESSO

Una volta che tutto funziona:

1. **Testa con 5-10 bandi reali diversi**
   - Verifica che importo sia sempre trovato
   - Controlla che decisione sia sensata
   - Valuta se motivi punteggio sono chiari

2. **Confronta con analisi manuale**
   - Prendi un bando che conosci bene
   - Analizza con BidPilot
   - Verifica: ha trovato tutti i requisiti?

3. **Raccogli metriche**
   - Tempo analisi: quanto ci metti tu vs BidPilot?
   - Accuratezza: quanti requisiti persi?
   - Utilità: score rispecchia realtà?

4. **Prepara demo per clienti**
   - Usa bandi LORO reali
   - Pre-carica LORO profilo
   - Script demo pronto (vedi DEMO_CHECKLIST.md)

---

**Sei pronto! 🎉**
