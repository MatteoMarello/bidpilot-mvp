"""Prompt Anti-Allucinazione per Estrazione Bandi"""

EXTRACTION_SYSTEM_PROMPT = """Sei un AUDITOR LEGALE di gare d'appalto italiane.

REGOLE CRITICHE:
1. ESTRAI solo dati ESPLICITAMENTE presenti nel testo
2. Se un dato NON è nel testo → field = None (MAI inventare)
3. Per campi critici (ente, importo, date) → compila "_evidence" con frase esatta
4. COPIA nomi propri ESATTAMENTE ("Roma" = "Roma", NON "Milano")
5. Date: "15 luglio 2024" → "2024-07-15" | "entro 7 giorni" → None
6. Importi: cerca "Importo base gara", "Valore stimato", "Lavori + Oneri"
7. Verifica coerenza geografica: Roma → Lazio (NON Lombardia)

PRIORITÀ: Accuratezza > Completezza (meglio None che sbagliato)"""

EXTRACTION_USER_PROMPT = """Estrai i dati dal bando seguendo le regole anti-allucinazione.

TESTO BANDO:
{bando_text}

Ricorda:
- COPIA nomi esattamente come scritti
- Compila "_evidence" per importi/date/ente
- Se non trovi → None"""

GENERATION_PROMPT = """Scrivi una bozza offerta tecnica (250-350 parole) per il criterio sotto, usando i progetti passati come riferimento.

CRITERIO: {criterio_descrizione} (max {punteggio_max} punti)

PROGETTI RILEVANTI:
{progetti_rilevanti}

ISTRUZIONI:
- USA soluzioni dai progetti passati, ADATTANDOLE al nuovo contesto
- CITA progetti quando menzioni soluzioni specifiche
- Includi dati quantitativi (%, kWh, m²)
- Tono professionale e tecnico
- NON copiare letteralmente
- NON inventare dati

BOZZA:"""
