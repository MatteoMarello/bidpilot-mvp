# 🚀 Quick Start - BidPilot MVP

Guida rapida per far partire l'applicazione in 5 minuti.

## Setup in 5 Passi

### 1. Installa Dipendenze
```bash
pip install -r requirements.txt
```

### 2. (Opzionale) Personalizza Profilo Aziendale
Modifica `config/profilo_azienda.json` con i tuoi dati o lascia quelli di esempio.

### 3. (Opzionale) Aggiungi Progetti Storici
Copia PDF di vecchi progetti in `data/progetti_storici/` per abilitare la generazione bozze.

```bash
# Esempio
cp ~/Documents/miei_progetti/*.pdf data/progetti_storici/
```

### 4. Avvia App
```bash
streamlit run app.py
```

### 5. Usa l'App
1. **Nella sidebar:** Inserisci OpenAI API Key
2. **Nella sidebar:** Clicca "Indicizza Progetti Storici" (se hai aggiunto PDF)
3. **Tab Analisi:** Carica un PDF di bando e clicca "Analizza"
4. **Tab Genera Bozza:** Seleziona criterio e genera bozza

## Test Veloce SENZA Progetti

Se vuoi testare solo l'analisi bando:
1. Avvia app
2. Inserisci API key
3. **Salta** step indicizzazione progetti
4. Carica PDF bando
5. Analizza

La generazione bozze sarà disabilitata, ma vedrai tutte le funzioni di analisi Go/No-Go.

## Esempio API Key

Ottieni la tua key gratis su: https://platform.openai.com/api-keys

Formato: `sk-proj-xxxxxxxxxxxxxxxxxxxxx`

## Problemi Comuni

| Problema | Soluzione |
|----------|-----------|
| "Module not found" | `pip install -r requirements.txt` |
| "API key invalid" | Verifica key su platform.openai.com |
| "No PDF in progetti_storici" | È normale se non hai aggiunto progetti - salta la generazione bozze |

## Prossimi Passi

Dopo aver testato l'MVP, leggi il `README.md` completo per:
- Personalizzazione avanzata profilo aziendale
- Best practices per progetti storici
- Consigli per demo a clienti
