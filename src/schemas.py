"""
Schemi Pydantic per Structured Output - ANTI-ALLUCINAZIONE
Ogni campo critico ha un campo _evidence che cita la frase esatta dal PDF
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date


class Scadenza(BaseModel):
    """Singola scadenza con evidence"""
    tipo: str = Field(description="Tipo: 'sopralluogo' | 'quesiti' | 'presentazione_offerta' | 'seduta_pubblica'")
    data: Optional[str] = Field(None, description="Formato YYYY-MM-DD. None se non trovata.")
    ora: Optional[str] = Field(None, description="Formato HH:MM. None se non specificata.")
    obbligatorio: bool = Field(description="True se esplicitamente obbligatorio, False altrimenti")
    note: Optional[str] = Field(None, description="Modalità (es: 'tramite portale SINTEL')")
    evidence: Optional[str] = Field(None, description="FRASE ESATTA dal testo dove hai trovato questa scadenza")


class SOACategoria(BaseModel):
    """Categoria SOA richiesta con evidence"""
    categoria: str = Field(description="Codice categoria (es: OS6, OG1)")
    descrizione: str = Field(description="Descrizione categoria")
    classifica: str = Field(description="I, II, III, IV, V, VI, VII, VIII")
    prevalente: bool = Field(False, description="True se è la categoria prevalente")
    importo_categoria: Optional[float] = Field(None, description="Importo specifico per questa categoria, se indicato")
    evidence: Optional[str] = Field(None, description="FRASE ESATTA dove hai trovato questa SOA")


class Criterio(BaseModel):
    """Criterio di valutazione"""
    codice: Optional[str] = Field(None, description="Codice criterio (A, B, C, etc)")
    descrizione: str = Field(description="Descrizione del criterio")
    punteggio_max: float = Field(description="Punteggio massimo assegnabile")
    tipo: Optional[str] = Field(None, description="'qualitativo' | 'quantitativo' | 'misto'")


class FiguraProfessionale(BaseModel):
    """Figura professionale richiesta"""
    ruolo: str = Field(description="Es: Geologo, Ingegnere strutturista, BIM Manager")
    requisiti: Optional[str] = Field(None, description="Abilitazione/iscrizione richiesta")
    obbligatorio: bool = Field(False)
    esperienza_minima: Optional[str] = Field(None, description="Anni esperienza se specificato")


class Garanzie(BaseModel):
    """Garanzie richieste"""
    provvisoria: Optional[float] = Field(None, description="Importo garanzia provvisoria in euro")
    percentuale_provvisoria: Optional[float] = Field(None, description="Percentuale (es: 2.0 per 2%)")
    definitiva: Optional[float] = Field(None, description="Importo garanzia definitiva")


class BandoRequisiti(BaseModel):
    """
    SCHEMA PRINCIPALE - Estrazione strutturata bando
    
    REGOLE ANTI-ALLUCINAZIONE:
    1. OGNI campo che non trovi esplicitamente nel testo → None
    2. NON indovinare, NON inferire, NON completare
    3. Per campi critici (ente, importo, date) → compila _evidence
    4. Se vedi "Roma" scrivi "Roma", non "Milano"
    5. Se anno non è chiaro, metti None invece di inventarlo
    """
    
    # === DATI PRINCIPALI CON EVIDENCE ===
    oggetto_appalto: str = Field(description="Descrizione oggetto appalto (max 200 caratteri)")
    oggetto_evidence: Optional[str] = Field(None, description="Frase esatta dove hai trovato l'oggetto")
    
    stazione_appaltante: str = Field(description="Nome completo ente appaltante")
    stazione_evidence: Optional[str] = Field(None, description="FRASE ESATTA dove hai trovato l'ente (es: 'Roma Capitale - Dipartimento...')")
    
    importo_lavori: Optional[float] = Field(None, description="Importo base di gara in euro. None se NON trovato.")
    importo_evidence: Optional[str] = Field(None, description="FRASE ESATTA dove hai trovato l'importo (es: 'Importo a base di gara: € 850.000,00')")
    
    importo_base_gara: Optional[float] = Field(None, description="Se diverso da importo_lavori")
    oneri_sicurezza: Optional[float] = Field(None, description="Oneri sicurezza separati")
    
    # === LOCALIZZAZIONE (critica per check geografico) ===
    comune_stazione_appaltante: Optional[str] = Field(None, description="SOLO nome comune (es: 'Roma', NON 'Roma Capitale')")
    provincia_stazione_appaltante: Optional[str] = Field(None, description="Sigla provincia (es: 'RM', 'TO')")
    regione_stazione_appaltante: Optional[str] = Field(None, description="Nome regione (es: 'Lazio', 'Piemonte')")
    luogo_esecuzione: Optional[str] = Field(None, description="Località esecuzione lavori")
    
    # === CODICI ===
    codice_cup: Optional[str] = Field(None, description="Codice CUP se presente")
    codice_cig: Optional[str] = Field(None, description="Codice CIG se presente")
    
    # === PROCEDURA ===
    tipo_procedura: Optional[str] = Field(None, description="'aperta' | 'ristretta' | 'negoziata' | altro")
    criterio_aggiudicazione: Optional[str] = Field(None, description="'minor_prezzo' | 'oepv' | altro")
    punteggio_tecnico: Optional[float] = Field(None, description="Punti tecnici se OEPV")
    punteggio_economico: Optional[float] = Field(None, description="Punti economici se OEPV")
    
    # === SCADENZE (con evidence) ===
    scadenze: List[Scadenza] = Field(default_factory=list, description="Lista scadenze trovate")
    
    # === SOA (con evidence) ===
    soa_richieste: List[SOACategoria] = Field(default_factory=list, description="Categorie SOA richieste")
    
    # === CERTIFICAZIONI ===
    certificazioni_richieste: List[str] = Field(default_factory=list, description="Es: ['ISO 14001', 'ISO 9001']")
    
    # === FIGURE PROFESSIONALI ===
    figure_professionali_richieste: List[FiguraProfessionale] = Field(default_factory=list)
    
    # === CRITERI VALUTAZIONE ===
    criteri_valutazione: List[Criterio] = Field(default_factory=list)
    
    # === VINCOLI SPECIALI ===
    vincoli_speciali: List[str] = Field(default_factory=list, description="Es: ['PNRR', 'Clausola sociale art. 50']")
    
    # === GARANZIE ===
    garanzie_richieste: Optional[Garanzie] = Field(None)
    
    class Config:
        # Validazione stretta
        validate_assignment = True
        str_strip_whitespace = True
