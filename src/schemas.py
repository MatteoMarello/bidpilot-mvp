"""Schemi Pydantic per Structured Output Anti-Allucinazione"""
from pydantic import BaseModel, Field
from typing import List, Optional


class Scadenza(BaseModel):
    """Scadenza con evidence"""
    tipo: str = Field(description="'sopralluogo' | 'quesiti' | 'presentazione_offerta' | 'seduta_pubblica'")
    data: Optional[str] = Field(None, description="YYYY-MM-DD. None se non trovata")
    ora: Optional[str] = Field(None, description="HH:MM")
    obbligatorio: bool = Field(description="True se esplicitamente obbligatorio")
    note: Optional[str] = Field(None, description="Modalità (es: 'tramite portale')")
    evidence: Optional[str] = Field(None, description="FRASE ESATTA dal testo")


class SOACategoria(BaseModel):
    """Categoria SOA con evidence"""
    categoria: str = Field(description="Codice (es: OS6, OG1)")
    descrizione: str = Field(description="Descrizione categoria")
    classifica: str = Field(description="I, II, III, IV, V, VI, VII, VIII")
    prevalente: bool = Field(False, description="True se prevalente")
    importo_categoria: Optional[float] = Field(None, description="Importo specifico categoria")
    evidence: Optional[str] = Field(None, description="FRASE ESATTA")


class Criterio(BaseModel):
    """Criterio valutazione"""
    codice: Optional[str] = Field(None, description="Codice (A, B, C)")
    descrizione: str = Field(description="Descrizione")
    punteggio_max: float = Field(description="Punteggio massimo")
    tipo: Optional[str] = Field(None, description="'qualitativo' | 'quantitativo' | 'misto'")


class FiguraProfessionale(BaseModel):
    """Figura professionale richiesta"""
    ruolo: str = Field(description="Es: Geologo, Ingegnere")
    requisiti: Optional[str] = Field(None, description="Abilitazione richiesta")
    obbligatorio: bool = Field(False)
    esperienza_minima: Optional[str] = Field(None, description="Anni esperienza")


class Garanzie(BaseModel):
    """Garanzie richieste"""
    provvisoria: Optional[float] = Field(None, description="Importo garanzia provvisoria €")
    percentuale_provvisoria: Optional[float] = Field(None, description="Percentuale (2.0 = 2%)")
    definitiva: Optional[float] = Field(None, description="Importo garanzia definitiva")


class BandoRequisiti(BaseModel):
    """
    Schema principale estrazione bando
    
    ANTI-ALLUCINAZIONE:
    - Ogni campo non trovato → None
    - Per campi critici → compila _evidence
    - Se vedi "Roma" scrivi "Roma", non "Milano"
    """
    
    # Dati principali con evidence
    oggetto_appalto: str = Field(description="Oggetto appalto (max 200 char)")
    oggetto_evidence: Optional[str] = Field(None, description="Frase esatta oggetto")
    
    stazione_appaltante: str = Field(description="Nome ente")
    stazione_evidence: Optional[str] = Field(None, description="FRASE ESATTA ente")
    
    importo_lavori: Optional[float] = Field(None, description="Importo base gara €. None se non trovato")
    importo_evidence: Optional[str] = Field(None, description="FRASE ESATTA importo")
    
    importo_base_gara: Optional[float] = Field(None, description="Se diverso da importo_lavori")
    oneri_sicurezza: Optional[float] = Field(None, description="Oneri sicurezza")
    
    # Localizzazione (critica per check geografico)
    comune_stazione_appaltante: Optional[str] = Field(None, description="Solo nome comune (es: 'Roma')")
    provincia_stazione_appaltante: Optional[str] = Field(None, description="Sigla (es: 'RM')")
    regione_stazione_appaltante: Optional[str] = Field(None, description="Nome regione (es: 'Lazio')")
    luogo_esecuzione: Optional[str] = Field(None, description="Località esecuzione")
    
    # Codici
    codice_cup: Optional[str] = Field(None, description="CUP")
    codice_cig: Optional[str] = Field(None, description="CIG")
    
    # Procedura
    tipo_procedura: Optional[str] = Field(None, description="'aperta' | 'ristretta' | 'negoziata'")
    criterio_aggiudicazione: Optional[str] = Field(None, description="'minor_prezzo' | 'oepv'")
    punteggio_tecnico: Optional[float] = Field(None, description="Punti tecnici OEPV")
    punteggio_economico: Optional[float] = Field(None, description="Punti economici OEPV")
    
    # Liste strutturate
    scadenze: List[Scadenza] = Field(default_factory=list, description="Lista scadenze")
    soa_richieste: List[SOACategoria] = Field(default_factory=list, description="SOA richieste")
    certificazioni_richieste: List[str] = Field(default_factory=list, description="Es: ['ISO 14001']")
    figure_professionali_richieste: List[FiguraProfessionale] = Field(default_factory=list)
    criteri_valutazione: List[Criterio] = Field(default_factory=list)
    vincoli_speciali: List[str] = Field(default_factory=list, description="Es: ['PNRR']")
    garanzie_richieste: Optional[Garanzie] = Field(None)
    
    class Config:
        validate_assignment = True
        str_strip_whitespace = True
