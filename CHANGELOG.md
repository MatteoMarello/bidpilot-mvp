# 🔄 CHANGELOG — BidPilot v3.0 Decision Engine

## ✅ MODIFICHE PRINCIPALI

### Output: da "scoring" a decisione a 4 stati

Prima: punteggio 0-100 → "PARTECIPARE / NON PARTECIPARE"

Ora: 4 stati deterministici
- **NO_GO** — requisiti bloccanti non colmabili
- **GO_WITH_STRUCTURE** — colmabile con RTI / avvalimento / progettisti
- **GO_HIGH_RISK** — ammissibile ma con rischi operativi/documentali
- **GO** — tutti i requisiti verificati, nessun blocco

### Nuovi file

| File | Descrizione |
|------|-------------|
| `src/requirements_engine.py` | Libreria requisiti atomici A1–M7 con logica di valutazione |
| `src/decision_engine.py` | Engine decisionale deterministico → DecisionReport |

### File modificati

| File | Modifiche |
|------|-----------|
| `src/schemas.py` | Nuovi schemi: CompanyProfile, TenderProfile, DecisionReport + legacy BandoRequisiti |
| `src/analyzer.py` | Orchestratore aggiornato: usa decision_engine invece di scoring |
| `src/prompts.py` | Prompt aggiornati con nuovi campi (sopralluogo, avvalimento, RTI, appalto integrato…) |
| `app.py` | UI completamente rinnovata con 4 tab: Requisiti / Piano d'Azione / Checklist / Rischi |
| `config/profilo_azienda.json` | Aggiunto legale_rappresentante, cciaa, partecipazione, progettisti |

---

## 🧱 Architettura v3.0

```
PDF
 │
 ▼
BandoParser.parse_pdf()
 │
 ▼
BandoAnalyzer.extract_requirements()  ←── LLM (GPT-4o-mini)
 │  → BandoRequisiti (Pydantic structured output)
 │
 ▼
BandoAnalyzer._build_company_profile()
 │  → CompanyProfile (da profilo_azienda.json)
 │
 ▼
requirements_engine.evaluate_all(bando, company)
 │  → List[RequirementResult]  (A1…M7, deterministici)
 │
 ▼
decision_engine.produce_decision_report(bando, company)
 │  → DecisionReport
 │     ├── Verdict (4 stati)
 │     ├── TopReasons (max 3, con evidenze)
 │     ├── RequirementsResults (tutti i req atomici)
 │     ├── ActionPlan (step concreti per colmare gap)
 │     ├── ProceduralChecklist
 │     ├── DocumentChecklist
 │     ├── RiskRegister
 │     ├── Uncertainties (domande per l'utente)
 │     └── AuditTrace
```

---

## 📋 Requisiti Atomici Implementati

### A — Generali
A1 Cause esclusione · A2 Patti integrità · A5 Regolarità fiscale

### B — Idoneità
B1 Iscrizione CCIAA · B4 Firma digitale/poteri

### C — SOA
C1 Prevalente · C2 Scorporabili · C5 Validità temporale

### D — Certificazioni
D1-Dn per ogni certificazione richiesta dal bando

### E — Economico-finanziari
E1 Fatturato globale · E2 Fatturato specifico

### G — Progettazione
G1 Appalto integrato · G4 Giovane professionista

### H — Gate procedurali (priorità massima)
H1 Sopralluogo · H4 ANAC contributo · H5 Piattaforma

### I — Garanzie
I1 Cauzione provvisoria

### K — Avvalimento
K1 Ammissibilità e regole

### L — Subappalto
L1 Limiti percentuali

### M — Operativi
M1 Inizio lavori tassativo · M2+ Vincoli esecutivi

---

## 🏗️ Sanabilità (per ogni KO)

I KO "colmabili" propongono automaticamente metodi ammessi dal bando:
- **avvalimento** — solo se bando lo ammette e con vincoli estratti
- **rti** — solo se bando lo ammette, con quote
- **subappalto** — nei limiti percentuali estratti dal bando
- **progettisti** — solo per appalto integrato

---

## 🔐 Anti-allucinazione v3.0

- Ogni requisito/KO ha `evidence` (quote + page + section)
- Se manca evidenza → status `UNKNOWN`, mai `KO`
- Validazione geografica blocca incoerenze (Roma → Lazio)
- Incertezze esplicite nell'output (campo `uncertainties`)
- AuditTrace completo per ogni decisione

---

## ⚠️ Breaking Changes

**CompanyProfile**: il JSON `profilo_azienda.json` ha nuovi campi obbligatori:
- `legale_rappresentante` (nome, ruolo, firma_digitale)
- `cciaa` (iscritta, rea, ateco)
- `partecipazione` (rti, avvalimento, subappalto)

Vedere `config/profilo_azienda.json` per il formato aggiornato.

---

## 📝 TODO

- [ ] Completare requisiti atomici F (CEL/referenze), J (RTI consorzi), K esteso
- [ ] Export PDF/Word del DecisionReport
- [ ] Multi-lotto (gestione lotti separati)
- [ ] Modulo bozze offerta tecnica (WIP)