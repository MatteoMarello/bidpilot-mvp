"""
Prompt templates per BidPilot MVP - VERSIONE MIGLIORATA
Con extraction aggressiva e istruzioni dettagliate
"""

# Prompt per estrazione requisiti dal bando - VERSIONE AGGRESSIVA
EXTRACTION_PROMPT = """Sei un analista esperto di gare d'appalto pubbliche italiane con 20 anni di esperienza. 
Il tuo compito è estrarre OGNI SINGOLA informazione rilevante dal bando, cercando in modo AGGRESSIVO anche dati nascosti o scritti in formati insoliti.

TESTO BANDO:
{bando_text}

Estrai e restituisci un JSON con questa struttura ESATTA:

{{
  "oggetto_appalto": "descrizione completa dell'oggetto (max 200 caratteri)",
  "importo_lavori": numero,
  "importo_base_gara": numero o null,
  "oneri_sicurezza": numero o null,
  "stazione_appaltante": "nome ente completo",
  "comune_stazione_appaltante": "solo nome comune/città (es: Monza, non 'Comune di Monza')",
  "provincia_stazione_appaltante": "sigla provincia (es: MB, TO, MI)",
  "regione_stazione_appaltante": "nome regione (es: Lombardia, Piemonte)",
  "luogo_esecuzione": "città, provincia e via/località precisa se disponibile",
  "codice_cup": "codice CUP se presente" o null,
  "codice_cig": "codice CIG se presente" o null,
  "tipo_procedura": "aperta" | "ristretta" | "negoziata" | "altro",
  "criterio_aggiudicazione": "minor_prezzo" | "oepv" | "altro",
  "punteggio_tecnico": numero (se OEPV, es: 70) o null,
  "punteggio_economico": numero (se OEPV, es: 30) o null,
  
  "scadenze": [
    {{
      "tipo": "sopralluogo" | "quesiti" | "presentazione_offerta" | "seduta_pubblica" | "altro",
      "data": "YYYY-MM-DD",
      "ora": "HH:MM" o null,
      "obbligatorio": true | false,
      "note": "dettagli modalità (es: 'tramite portale SINTEL', 'su appuntamento via PEC')"
    }}
  ],
  
  "soa_richieste": [
    {{
      "categoria": "codice (es: OS6, OG1, OS28)",
      "descrizione": "descrizione categoria",
      "classifica": "I" | "II" | "III" | "IV" | "V" | "VI" | "VII" | "VIII",
      "prevalente": true | false,
      "importo_categoria": numero o null
    }}
  ],
  
  "certificazioni_richieste": [
    "ISO 14001",
    "ISO 9001",
    "ISO 45001",
    "Parità di genere",
    "Rating di legalità",
    "CAM (Criteri Ambientali Minimi)",
    ecc
  ],
  
  "figure_professionali_richieste": [
    {{
      "ruolo": "es: Geologo, Ingegnere strutturista, BIM Manager, Archeologo, RUP",
      "requisiti": "abilitazione/iscrizione richiesta",
      "obbligatorio": true | false,
      "esperienza_minima": "anni esperienza se specificato" o null
    }}
  ],
  
  "criteri_valutazione": [
    {{
      "codice": "A" | "B" | "C" ecc,
      "descrizione": "titolo criterio",
      "punteggio_max": numero,
      "sub_criteri": ["sottocriterio 1", "sottocriterio 2"] o null,
      "tipo": "qualitativo" | "quantitativo" | "misto" o null
    }}
  ],
  
  "vincoli_speciali": [
    "PNRR",
    "Clausola sociale art. 50",
    "Subappalto obbligatorio/vietato",
    "Avvalimento ammesso/vietato",
    ecc
  ],
  
  "garanzie_richieste": {{
    "provvisoria": numero o null,
    "percentuale_provvisoria": numero (es: 2) o null,
    "definitiva": numero o null
  }}
}}

ISTRUZIONI CRITICHE PER IMPORTO (MASSIMA PRIORITÀ):
- CERCA l'importo in TUTTI i modi possibili:
  1. "Importo a base di gara": €X
  2. "Importo lavori": €X
  3. "Importo totale": €X soggetto a ribasso + €Y oneri sicurezza
  4. Cifre scritte in LETTERE: "Euro seicentomila/00" o "seicentomila virgola zero zero"
  5. Tabelle con voci "Lavori", "Oneri", "Totale"
  6. "Valore stimato appalto"
  7. Nel quadro economico del progetto
  8. "Importo complessivo dell'appalto"
- Se trovi più importi, usa quello "a base di gara" o "soggetto a ribasso"
- Se l'importo è suddiviso (lavori + oneri), SOMMA i due valori per importo_lavori
- IMPORTANTE: NON mettere null sull'importo se c'è QUALSIASI cifra rilevante nel documento
- Se davvero non trovi nulla dopo aver cercato OVUNQUE, scrivi 0 (non null)

ISTRUZIONI CRITICHE PER SOPRALLUOGO:
- Cerca TUTTE le varianti: "sopralluogo", "presa visione", "accesso al cantiere", "visita obbligatoria", "visita luoghi", "accesso ai luoghi"
- Estrai SEMPRE data limite e modalità (es: "entro il", "su appuntamento tramite PEC a...")
- Se dice esplicitamente "facoltativo" o "non obbligatorio" → obbligatorio: false
- Se NON esplicita → obbligatorio: true (è la norma nelle gare pubbliche)
- Cerca anche frasi come "richiesta visita da inoltrare entro..." o "presa visione da effettuare entro"

ISTRUZIONI PER LOCALIZZAZIONE:
- comune_stazione_appaltante: SOLO il nome del comune (es: "Monza", non "Comune di Monza")
- provincia_stazione_appaltante: SOLO la sigla (es: "MB", "TO", "MI")
- regione_stazione_appaltante: nome completo (es: "Lombardia", "Piemonte")
- Se la stazione appaltante è una città metropolitana, usa la città principale

ISTRUZIONI PER SOA:
- Specifica SEMPRE quale categoria è PREVALENTE (quella con importo maggiore o esplicitamente indicata come prevalente)
- Se il bando dice "OG1 per €X" o "OS6 Classifica III minima", inserisci importo_categoria: X
- Calcola la classifica richiesta guardando gli importi se non esplicitata
- Se dice "categoria prevalente OG1" o "categoria maggioritaria", metti prevalente: true
- Se ci sono più categorie SOA, quella con importo maggiore è SEMPRE prevalente: true

ISTRUZIONI PER TIPO GARA:
- Cerca "criterio di aggiudicazione": 
  - "minor prezzo" o "prezzo più basso" → minor_prezzo
  - "offerta economicamente più vantaggiosa" o "OEPV" o "migliore rapporto qualità/prezzo" → oepv
- Se OEPV, estrai punteggi tecnico ed economico:
  - Di solito scritto come "70 punti tecnici, 30 punti economici"
  - O in tabella con "Punteggio tecnico: 70", "Punteggio economico: 30"

REGOLE FINALI:
1. Se non trovi un dato DOPO aver cercato ovunque → metti null
2. Date in formato YYYY-MM-DD (converti "17 luglio 2024" in "2024-07-17")
3. Orari in formato HH:MM (converti "ore 12" in "12:00", "ore 12:00" in "12:00")
4. Importi SEMPRE come numero puro (850000 non "€850.000,00")
5. Rispondi SOLO con JSON valido, ZERO testo prima o dopo, NO markdown backticks
6. Se trovi informazioni parziali, inseriscile comunque (meglio qualcosa che null)

JSON:"""


# Prompt per generazione bozza offerta tecnica (NON MODIFICATO - per dopo)
GENERATION_PROMPT = """Sei un ingegnere esperto in gare d'appalto. Devi scrivere una bozza di risposta a un criterio specifico di un bando, utilizzando come riferimento soluzioni tecniche che l'azienda ha già implementato con successo in progetti passati.

CRITERIO DEL NUOVO BANDO:
{criterio_descrizione}
Punteggio massimo: {punteggio_max} punti

CONTESTO PROGETTI PASSATI RILEVANTI:
{progetti_rilevanti}

ISTRUZIONI:
1. Scrivi una bozza di 250-350 parole che risponda specificamente al criterio richiesto
2. USA le soluzioni tecniche dei progetti passati come base, ma ADATTALE al nuovo contesto
3. Mantieni un tono professionale e tecnico
4. Cita esplicitamente i progetti passati quando menzioni soluzioni specifiche (es: "soluzione adottata in Progetto X...")
5. Includi dati quantitativi dove possibile (%, kWh, m², ecc)
6. Se ci sono vincoli normativi specifici (PNRR, CAM, DNSH), menzionali esplicitamente

NON:
- Non copiare letteralmente dai progetti passati
- Non inventare dati o percentuali non presenti nei documenti
- Non essere generico: ogni affermazione deve essere supportata da un progetto o da normativa

FORMATO OUTPUT:
Testo della bozza (senza titoli o intestazioni)

BOZZA:"""


# Prompt per match profilo aziendale (NON MODIFICATO)
MATCH_ANALYSIS_PROMPT = """Analizza il seguente requisito del bando e determina se l'azienda lo soddisfa.

REQUISITO BANDO:
{requisito}

PROFILO AZIENDA:
{profilo_azienda}

Rispondi in formato JSON:
{{
  "status": "VERDE" | "GIALLO" | "ROSSO",
  "motivo": "spiegazione breve del motivo",
  "azione_suggerita": "cosa fare (se status != VERDE)" o null,
  "riferimento_progetto_passato": "nome progetto dove hai usato soluzione simile" o null
}}

LOGICA:
- VERDE: requisito pienamente soddisfatto dai dati aziendali
- GIALLO: dato non presente in profilo MA probabilmente risolvibile (es: con consulente esterno abituale)
- ROSSO: requisito mancante e difficile/impossibile da ottenere in tempo utile

Rispondi SOLO con il JSON:"""