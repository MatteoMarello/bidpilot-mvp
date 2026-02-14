"""
Prompt templates per BidPilot MVP
"""

# Prompt per estrazione requisiti dal bando
EXTRACTION_PROMPT = """Sei un esperto di gare d'appalto pubbliche italiane. 
Analizza il seguente testo di un bando/disciplinare e estrai TUTTE le informazioni rilevanti in formato JSON strutturato.

TESTO BANDO:
{bando_text}

Estrai e restituisci un JSON con questa struttura ESATTA (se un campo non è presente, usa null):

{{
  "oggetto_appalto": "descrizione breve dell'oggetto",
  "importo_lavori": numero (solo cifra, es: 850000),
  "stazione_appaltante": "nome ente",
  "luogo_esecuzione": "città/via",
  
  "scadenze": [
    {{
      "tipo": "sopralluogo" | "quesiti" | "presentazione_offerta" | "altro",
      "data": "YYYY-MM-DD",
      "ora": "HH:MM" o null,
      "obbligatorio": true | false,
      "note": "dettagli aggiuntivi"
    }}
  ],
  
  "soa_richieste": [
    {{
      "categoria": "codice (es: OS6, OG1)",
      "descrizione": "descrizione categoria",
      "classifica": "I" | "II" | "III" | "IV" ecc,
      "importo_minimo": numero o null
    }}
  ],
  
  "certificazioni_richieste": [
    "ISO 14001",
    "ISO 9001",
    "Parità di genere",
    "CAM calcestruzzo",
    ecc
  ],
  
  "figure_professionali_richieste": [
    {{
      "ruolo": "Geologo abilitato",
      "requisiti": "descrizione requisiti specifici",
      "obbligatorio": true | false
    }}
  ],
  
  "criteri_valutazione": [
    {{
      "codice": "A",
      "descrizione": "Miglioramento prestazioni energetiche",
      "punteggio_max": 8,
      "sub_criteri": ["dettaglio1", "dettaglio2"] o null
    }}
  ],
  
  "vincoli_speciali": [
    "PNRR - Conformità DNSH obbligatoria",
    "Clausola sociale art. 50",
    ecc
  ]
}}

REGOLE IMPORTANTI:
1. Estrai TUTTE le scadenze, anche quelle nascoste nel testo
2. Per le SOA, specifica sempre categoria E classifica
3. Se un criterio di valutazione ha sotto-punti, inseriscili in sub_criteri
4. Se non trovi un'informazione, metti null (non inventare)
5. Le date devono essere in formato YYYY-MM-DD
6. Rispondi SOLO con il JSON, senza preamble o markdown

JSON:"""

# Prompt per generazione bozza offerta tecnica
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

# Prompt per match profilo aziendale
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
