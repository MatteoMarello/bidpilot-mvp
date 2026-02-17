# 🔧 BidPilot v3.1 — Patch Notes (Fix Matematici + Nuovi Gate)

## Bug risolti

### [C1/C2] Calcolo classifica SOA — Fix Matematico CRITICO
**Problema:** Il sistema usava l'importo totale del bando per determinare la classifica SOA richiesta,
generando "falsi negativi" (es: bando da €710k totale → richiedeva OG1 cl.III anche se OG1 era €460k → cl.II bastava).

**Fix:** `_required_class_from_amount(importo_categoria)` calcola la classifica dalla singola categoria.
- Il campo `SOACategoria.importo_categoria` viene estratto separatamente per ogni categoria dal prompt.
- La classifica viene verificata PRIMA dal valore estratto dal bando; se assente, calcolata dall'importo categoria.
- Tabella corretta: ≤258k→I | ≤516k→II | ≤1.033k→III | ≤2.065k→IV | ecc.

### [C2] Confusione OG11 vs OS28 — Fix Anti-Allucinazione
**Problema:** Il sistema scambiava OS28 (termico/condizionamento) per OG11 (Impianti Tecnologici),
categorie distinte che NON sono equivalenti.

**Fix:**
- Ogni categoria è trattata come distinta: `OG11 ≠ OS28 ≠ OS30`.
- Aggiunto campo `SOACategoria.inferred: bool` (default False): se True, la categoria è stata
  dedotta dalla descrizione delle lavorazioni, non dal codice esplicito nel bando.
- Il prompt ora istruisce esplicitamente a NON fare equivalenze tra categorie.

### [C1/C2] Distinzione Prevalente vs Scorporabili
**Problema:** Il messaggio di errore non distingueva chiaramente il ruolo delle categorie.

**Fix:**
- `eval_C1_prevalente` chiarisce che è la PREVALENTE e cosa comporta mancanza.
- `eval_C2_scorporabili`: se l'azienda manca ANCHE della prevalente (caso frequente per imprese
  specialistiche), il messaggio suggerisce **RTI Orizzontale** in modo esplicito,
  spiegando il ruolo mandataria/mandante.

### [D] Matching certificazioni STRICT — Fix Falsi Positivi
**Problema:** ISO 9001 (qualità) veniva accettato quando il bando richiedeva OHSAS 18001 o ISO 45001 (sicurezza).

**Fix:** Introdotta tabella `_CERT_SYNONYMS` + `_CERT_EQUIVALENCES`.
- ISO 9001 ≠ ISO 14001 ≠ ISO 45001 ≠ OHSAS 18001.
- Equivalenze accettate: ISO 45001 ↔ OHSAS 18001 (stessa area, normativa aggiornata).
- Se l'azienda ha una cert simile ma diversa, il messaggio lo segnala ESPLICITAMENTE:
  *"ATTENZIONE: l'azienda ha 'ISO 9001' ma questa NON soddisfa 'ISO 45001' (scope diverso)."*

---

## Nuove funzionalità

### [H_MANODOPERA] Gate Costi della Manodopera — NEW
- Verifica se i costi manodopera sono indicati nel bando (art. 41 c.14 d.lgs. 36/2023).
- Verifica se NON sono soggetti a ribasso (requisito di legge).
- Se soggetti a ribasso → SOFT_RISK con segnalazione di possibile illegittimità.
- Nuovi campi in `BandoRequisiti`: `costi_manodopera_indicati`, `costi_manodopera_eur`,
  `costi_manodopera_soggetti_ribasso`, `costi_manodopera_evidence`.

### [H_SUBAPPALTO_VIETATO] Gate Divieto Subappalto — NEW
- Verifica se alcune categorie hanno il subappalto vietato al 100%.
- L'azienda deve possedere SOA propria per quelle lavorazioni (non può affidarle a terzi).
- Nuovo campo in `BandoRequisiti`: `subappalto_vietato_categorie: List[str]`.

---

## File modificati

| File | Modifiche |
|------|-----------|
| `src/requirements_engine.py` | Fix C1/C2 classifica, fix cert matching, nuovi gate H_MANODOPERA e H_SUBAPPALTO_VIETATO |
| `src/schemas.py` | `SOACategoria.inferred`, `BandoRequisiti.costi_manodopera_*`, `subappalto_vietato_categorie` |
| `src/prompts.py` | Istruzioni per importo categoria, flag inferred, manodopera, divieto subappalto |
