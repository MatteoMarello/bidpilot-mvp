# BidPilot — Note Refactor MVP

**Data:** Febbraio 2026  
**Obiettivo:** Riallineamento all'MVP descritto in `BidPilot_MVP_Strategia.md`

---

## File Modificati / Aggiunti

### `app.py` — Riscrittura completa

**Cosa è cambiato:**
- Rimosso intero blocco UI "Decision Engine" (verdict GO/NO-GO, score, label "NON PARTECIPARE")
- Aggiunto form **profilo minimo** nella sidebar (SOA + Certificazioni + Regioni)
- Output sostituito con **BandoCard 6 blocchi** (✅❌❓ matching)
- Aggiunto `ADVANCED_MODE = False` come feature flag in cima al file

**Feature flag `ADVANCED_MODE`:**
```python
ADVANCED_MODE = False   # default MVP
# ADVANCED_MODE = True  # per abilitare piano d'azione, risk register, bozze
```
Quando `False`: mostra solo BandoCard.  
Quando `True`: mostra anche `_render_advanced()` (stub, da implementare).

**Profilo progressivo:**
- L'utente può inserire solo SOA + cert + regioni e il sistema funziona
- Se un campo aziendale non è presente → stato `❓` (mai `❌` per mancanza di info)
- Opzione "Carica da `profilo_azienda.json`" per chi ha già il profilo completo

---

### `src/bando_card.py` — Nuovo modulo

**Cosa fa:**
- Riceve `BandoRequisiti` + `List[RequirementResult]` dall'engine esistente
- Produce `BandoCard` strutturata con 6 blocchi
- Implementa regola hard MVP: evidence mancante → "Da verificare", mai inventato

**Mapping stati:**
```
ReqStatus.OK        → ✅ ok
ReqStatus.KO        → ❌ ko  (ma: se profilo_empty → ❓ forced_unknown)
ReqStatus.FIXABLE   → ❌ ko  (nel MVP non mostriamo "colmabile con RTI/avvalimento")
ReqStatus.UNKNOWN   → ❓ unknown
ReqStatus.RISK_FLAG → ❓ unknown  (segnalato ma non ❌)
ReqStatus.PREMIANTE → ignorato nel MVP (non rilevante per screening)
```

**Flag profilo vuoto:**
- `soa_profile_empty=True` → tutte le SOA mostrano ❓ (nessun dato per matchare)
- `cert_profile_empty=True` → tutte le cert mostrano ❓

---

### `src/profile_builder.py` — Nuovo modulo

**Cosa fa:**
- `build_from_form(soa, certs, regioni)` → `MinimalProfile` da form sidebar
- `build_from_json(dict)` → `MinimalProfile` da profilo completo JSON

**Default sicuri (non generano KO fuorvianti):**

| Campo | Default | Effetto sull'engine |
|-------|---------|---------------------|
| `has_digital_signature` | `True` | R04 = OK (assume firma disponibile) |
| `signing_powers_proof` | `"available"` | R04 = OK |
| `cameral_registration.coherence` | `"unknown"` | R18 = UNKNOWN, non KO |
| `turnover_by_year` | `[]` | R20 = UNKNOWN (nessun dato) |
| `similar_works` | `[]` | R21 = UNKNOWN (nessun dato) |
| `has_credit_license` | `"unknown"` | D10 = UNKNOWN, non KO |
| `deposited_statements_count` | `0` | D17 = UNKNOWN/KO (rilevante solo per qualificazione) |

---

## Cosa NON è cambiato (moduli esistenti invariati)

| File | Status |
|------|--------|
| `src/parser.py` | ✅ Invariato |
| `src/analyzer.py` | ✅ Invariato |
| `src/requirements_engine.py` | ✅ Invariato |
| `src/decision_engine.py` | ✅ Invariato (usato solo con ADVANCED_MODE=True) |
| `src/schemas.py` | ✅ Invariato |
| `src/prompts.py` | ✅ Invariato |
| `src/retrieval.py` | ✅ Invariato |
| `src/rag_engine.py` | ✅ Invariato (modulo bozze, sempre WIP) |
| `config/profilo_azienda.json` | ✅ Invariato (caricabile via "Carica da JSON") |
| `data/aliases.yaml` | ✅ Invariato |

---

## Cosa è disabilitato (behind ADVANCED_MODE)

Nel MVP `ADVANCED_MODE = False` nasconde:
- Piano d'azione (RTI / avvalimento / subappalto suggestions)
- Risk register
- Checklist procedurale
- Document checklist  
- Tab "Bozze Offerta Tecnica"
- Audit trace / developer view

Questi moduli esistono già nel codebase (`src/decision_engine.py`) e restano funzionanti.
Basta impostare `ADVANCED_MODE = True` per riattivarli (serve però interfaccia avanzata).

---

## Regola hard MVP

```
Evidence mancante dal bando  → campo = "Da verificare" nel Blocco 6
Dato aziendale mancante      → stato requisito = ❓  (MAI ❌)
```

Questo è garantito da:
1. **`src/analyzer.py`** (guardrail B+C): già implementato, rimuove campi senza evidence
2. **`src/bando_card.py`** (`force_unknown=soa_profile_empty`): se profilo vuoto, forza ❓
3. **`src/profile_builder.py`** (default sicuri): dati mancanti → engine ritorna UNKNOWN

---

## Come testare

```bash
# Avvio MVP
streamlit run app.py

# Test con profilo vuoto (tutto ❓ per SOA/cert)
# → non inserire nulla nel form → caricare PDF → verificare che SOA mostri ❓

# Test con profilo parziale
# → inserire solo OS6 cl.III → verificare che OS6 mostri ✅/❌ e le altre ❓

# Test con profilo completo
# → usare "Carica da profilo_azienda.json" → verificare matching completo

# Abilitare ADVANCED_MODE
# → cambiare ADVANCED_MODE = True in app.py → riavviare
```

---

## Prossimi passi (post-validazione MVP)

1. **ADVANCED_MODE=True**: collegare `_render_advanced()` a `decision_engine.py`
2. **Export BandoCard**: aggiungere export PDF/DOCX della BandoCard
3. **Salvataggio profilo**: save/load profilo dal form minimo
4. **Multi-bando**: confronto BandoCard su più bandi caricati
5. **Modulo offerta tecnica**: seguire istruzioni Sezione 6 di `BidPilot_MVP_Strategia.md`
