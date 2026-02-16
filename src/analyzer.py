"""
Analyzer ANTI-ALLUCINAZIONE con Structured Output Pydantic
Estrazione deterministica e basata su evidenze
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from src.langchain_compat import create_chat_openai
from langchain.prompts import ChatPromptTemplate

from src.schemas import BandoRequisiti
from src.prompts import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT


# Mapping classifiche SOA -> importo massimo
CLASSIFICHE_SOA_IMPORTO = {
    "I": 258000,
    "II": 516000,
    "III": 1033000,
    "IV": 2065000,
    "V": 3098000,
    "VI": 5165000,
    "VII": 10329000,
    "VIII": float('inf')
}


class BandoAnalyzer:
    """
    Analizzatore bandi con STRUCTURED OUTPUT e ANTI-ALLUCINAZIONE
    
    Usa Pydantic + with_structured_output per risultati deterministici
    """
    
    def __init__(self, openai_api_key: str, profilo_path: str = "config/profilo_azienda.json"):
        # LLM con temperatura 0 per massima determinismo
        self.llm = create_chat_openai(
            model="gpt-4o",  # Upgraded da gpt-4o-mini per accuracy
            temperature=0,
            api_key=openai_api_key
        )
        
        # Carica profilo aziendale
        with open(profilo_path, 'r', encoding='utf-8') as f:
            self.profilo_azienda = json.load(f)
    
    def extract_requirements(self, bando_text: str) -> BandoRequisiti:
        """
        Estrae requisiti usando STRUCTURED OUTPUT Pydantic
        
        Args:
            bando_text: testo del bando (da parser)
            
        Returns:
            BandoRequisiti (oggetto Pydantic validato)
            
        Raises:
            Exception se LLM non rispetta schema
        """
        # Limita testo se troppo lungo (GPT-4o supporta 128k ma meglio non esagerare)
        MAX_LENGTH = 50000
        if len(bando_text) > MAX_LENGTH:
            # Tronca mantenendo inizio (header) e fine (scadenze spesso alla fine)
            half = MAX_LENGTH // 2
            bando_text = bando_text[:half] + "\n\n[...TESTO TRONCATO...]\n\n" + bando_text[-half:]
        
        # Crea prompt con system + user message
        prompt = ChatPromptTemplate.from_messages([
            ("system", EXTRACTION_SYSTEM_PROMPT),
            ("user", EXTRACTION_USER_PROMPT)
        ])
        
        # STRUCTURED OUTPUT con Pydantic
        structured_llm = self.llm.with_structured_output(BandoRequisiti)
        
        # Chain: prompt → LLM → Pydantic validation
        chain = prompt | structured_llm
        
        try:
            # Invoca chain
            requisiti = chain.invoke({"bando_text": bando_text})
            
            # Validazione post-extraction
            self._validate_extraction(requisiti)
            
            return requisiti
            
        except Exception as e:
            raise Exception(f"Errore estrazione strutturata: {str(e)}")
    
    def _validate_extraction(self, requisiti: BandoRequisiti) -> None:
        """
        Validazione post-estrazione per rilevare allucinazioni evidenti
        
        Raises:
            ValueError se rileva incoerenze gravi
        """
        # Check 1: Se ha estratto ente, DEVE avere evidence
        if requisiti.stazione_appaltante and requisiti.stazione_appaltante != "Non specificato":
            if not requisiti.stazione_evidence:
                print("⚠️ WARNING: Ente estratto senza evidence - possibile allucinazione")
        
        # Check 2: Coerenza geografica (Roma → Lazio, Milano → Lombardia)
        if requisiti.comune_stazione_appaltante and requisiti.regione_stazione_appaltante:
            comune = requisiti.comune_stazione_appaltante.lower()
            regione = requisiti.regione_stazione_appaltante.lower()
            
            # Mapping comuni → regioni (principali)
            COERENZA_GEO = {
                "roma": "lazio",
                "milano": "lombardia",
                "torino": "piemonte",
                "napoli": "campania",
                "palermo": "sicilia",
                "genova": "liguria",
                "bologna": "emilia-romagna",
                "firenze": "toscana",
                "bari": "puglia",
                "catania": "sicilia"
            }
            
            expected_regione = COERENZA_GEO.get(comune)
            if expected_regione and expected_regione not in regione:
                raise ValueError(
                    f"❌ INCOERENZA GEOGRAFICA RILEVATA: "
                    f"Comune='{requisiti.comune_stazione_appaltante}' "
                    f"ma Regione='{requisiti.regione_stazione_appaltante}'. "
                    f"Atteso: '{expected_regione.title()}'. "
                    f"Probabile ALLUCINAZIONE."
                )
        
        # Check 3: Importo ragionevole (< 100M€)
        if requisiti.importo_lavori and requisiti.importo_lavori > 100_000_000:
            print(f"⚠️ WARNING: Importo molto alto (€{requisiti.importo_lavori:,.0f}) - verifica manualmente")
        
        # Check 4: Date nel futuro o passato ragionevole
        for scad in requisiti.scadenze:
            if scad.data:
                try:
                    data_scad = datetime.strptime(scad.data, "%Y-%m-%d")
                    oggi = datetime.now()
                    
                    # Scadenza troppo vecchia (> 2 anni fa)
                    if data_scad < oggi - timedelta(days=730):
                        print(f"⚠️ WARNING: Scadenza troppo vecchia ({scad.data}) - verifica manualmente")
                    
                    # Scadenza troppo futura (> 3 anni)
                    if data_scad > oggi + timedelta(days=1095):
                        print(f"⚠️ WARNING: Scadenza molto futura ({scad.data}) - verifica manualmente")
                        
                except:
                    pass
    
    def _calcola_urgenza_scadenza(self, data_str: str) -> Tuple[str, int, str]:
        """Calcola urgenza scadenza"""
        try:
            data_scadenza = datetime.strptime(data_str, "%Y-%m-%d")
            oggi = datetime.now()
            giorni = (data_scadenza - oggi).days
            
            if giorni < 0:
                return "SCADUTO", giorni, "⛔"
            elif giorni == 0:
                return "CRITICO", 0, "🔴"
            elif giorni <= 2:
                return "CRITICO", giorni, "🔴"
            elif giorni <= 7:
                return "ATTENZIONE", giorni, "🟡"
            else:
                return "OK", giorni, "🟢"
        except:
            return "SCONOSCIUTO", None, "❓"
    
    def _check_geografico(self, comune_bando: str, provincia_bando: str, regione_bando: str) -> Dict:
        """Verifica zona geografica"""
        aree_abituali = self.profilo_azienda.get("aree_geografiche", [])
        
        if not aree_abituali:
            return {
                "in_zona": True,
                "motivo": "Area geografiche non specificate nel profilo",
                "warning": False
            }
        
        regione_norm = (regione_bando or "").strip().title()
        
        for area in aree_abituali:
            if regione_norm and regione_norm in area:
                return {
                    "in_zona": True,
                    "motivo": f"Bando in {regione_norm}, area abituale dell'azienda",
                    "warning": False
                }
        
        return {
            "in_zona": False,
            "motivo": f"Bando in {regione_norm or 'località non specificata'} - Fuori dalle aree abituali ({', '.join(aree_abituali)})",
            "warning": True
        }
    
    def _calcola_gap_classifica(self, classifica_richiesta: str, classifica_posseduta: str) -> Dict:
        """Calcola gap monetario tra classifiche SOA"""
        importo_richiesto = CLASSIFICHE_SOA_IMPORTO.get(classifica_richiesta, 0)
        importo_posseduto = CLASSIFICHE_SOA_IMPORTO.get(classifica_posseduta, 0)
        
        gap = importo_richiesto - importo_posseduto
        
        if gap > 0:
            return {
                "gap_euro": gap,
                "gap_descrizione": f"Mancano €{gap:,} di classifica (posseduta {classifica_posseduta}, richiesta {classifica_richiesta})"
            }
        else:
            return {
                "gap_euro": 0,
                "gap_descrizione": f"Classifica {classifica_posseduta} sufficiente"
            }
    
    def _verifica_soa(self, soa_richiesta) -> Dict:
        """Verifica SOA con gap calcolo"""
        categoria_richiesta = soa_richiesta.categoria
        classifica_richiesta = soa_richiesta.classifica
        
        for soa in self.profilo_azienda.get("soa_possedute", []):
            if soa["categoria"] == categoria_richiesta:
                classifica_posseduta = soa["classifica"]
                
                classifica_map = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8}
                num_posseduta = classifica_map.get(classifica_posseduta, 0)
                num_richiesta = classifica_map.get(classifica_richiesta, 0)
                
                if num_posseduta >= num_richiesta:
                    return {
                        "status": "VERDE",
                        "motivo": f"SOA {categoria_richiesta} Classifica {classifica_posseduta} presente (scadenza {soa['scadenza']})",
                        "gap": None
                    }
                else:
                    gap_info = self._calcola_gap_classifica(classifica_richiesta, classifica_posseduta)
                    return {
                        "status": "ROSSO",
                        "motivo": f"SOA {categoria_richiesta} presente ma {gap_info['gap_descrizione']}",
                        "gap": gap_info,
                        "suggerimento": "Valutare AVVALIMENTO con impresa di classifica superiore"
                    }
        
        return {
            "status": "ROSSO",
            "motivo": f"SOA {categoria_richiesta} Classifica {classifica_richiesta} NON posseduta",
            "gap": {"gap_euro": CLASSIFICHE_SOA_IMPORTO.get(classifica_richiesta, 0), 
                    "gap_descrizione": f"Categoria {categoria_richiesta} non presente"},
            "suggerimento": "Ricorrere ad AVVALIMENTO con impresa che possiede la SOA richiesta"
        }
    
    def _verifica_certificazione(self, cert_richiesta: str) -> Dict:
        """Verifica certificazione"""
        cert_possedute = [c.get("tipo", "") for c in self.profilo_azienda.get("certificazioni", [])]
        
        for cert in cert_possedute:
            if cert.lower() in cert_richiesta.lower() or cert_richiesta.lower() in cert.lower():
                cert_data = next((c for c in self.profilo_azienda["certificazioni"] if c.get("tipo") == cert), None)
                
                if cert_data:
                    scadenza_cert = cert_data.get("scadenza", "")
                    try:
                        data_scad = datetime.strptime(scadenza_cert, "%Y-%m-%d")
                        if data_scad < datetime.now():
                            return {
                                "status": "ROSSO",
                                "motivo": f"{cert} SCADUTA il {scadenza_cert} - RINNOVARE URGENTEMENTE"
                            }
                    except:
                        pass
                
                return {
                    "status": "VERDE",
                    "motivo": f"{cert} presente"
                }
        
        return {
            "status": "GIALLO",
            "motivo": f"{cert_richiesta} - Verificare con fornitore",
            "suggerimento": "Contattare ente certificatore"
        }
    
    def _verifica_figura_professionale(self, figura) -> Dict:
        """Verifica figura professionale"""
        ruolo = figura.ruolo
        
        if ruolo in self.profilo_azienda.get("figure_professionali_interne", []):
            return {
                "status": "VERDE",
                "motivo": f"{ruolo} disponibile internamente"
            }
        
        for collab in self.profilo_azienda.get("collaboratori_esterni_abituali", []):
            if ruolo.lower() in collab["tipo"].lower():
                return {
                    "status": "GIALLO",
                    "motivo": f"{ruolo} - Contattare {collab['nome_studio']} (costo: €{collab['costo_medio']:,})",
                    "costo_stimato": collab["costo_medio"]
                }
        
        return {
            "status": "GIALLO",
            "motivo": f"{ruolo} - Cercare consulente esterno",
            "suggerimento": "Contattare ordini professionali"
        }
    
    def _calcola_score_e_decisione(self, soa_analisi, cert_analisi, figure_analisi, 
                                    scadenze_analisi, check_geo, requisiti) -> Tuple[str, int, List[str]]:
        """Calcola score e decisione finale"""
        num_rossi = len(soa_analisi["rossi"]) + len(cert_analisi["rossi"])
        num_gialli = len(soa_analisi["gialli"]) + len(cert_analisi["gialli"]) + len(figure_analisi["gialli"])
        num_verdi = len(soa_analisi["verdi"]) + len(cert_analisi["verdi"]) + len(figure_analisi["verdi"])
        
        punteggio = 100
        motivi = []
        
        if num_rossi > 0:
            punteggio -= num_rossi * 40
            if soa_analisi["rossi"]:
                soa_mancanti = [s["categoria"] for s in soa_analisi["rossi"]]
                motivi.append(f"❌ SOA MANCANTI: {', '.join(soa_mancanti)} (-{len(soa_analisi['rossi'])*40}pt)")
        
        if scadenze_analisi["critiche"]:
            num_critiche = len(scadenze_analisi["critiche"])
            punteggio -= num_critiche * 20
            motivi.append(f"🔴 {num_critiche} scadenza/e CRITICA/E (-{num_critiche*20}pt)")
        
        if num_gialli > 0:
            punteggio -= num_gialli * 10
            motivi.append(f"🟡 {num_gialli} requisiti DA VERIFICARE (-{num_gialli*10}pt)")
        
        if not check_geo["in_zona"]:
            punteggio -= 15
            motivi.append(f"🗺️ Bando FUORI ZONA (-15pt)")
        
        bonus_verdi = min(20, num_verdi * 5)
        if bonus_verdi > 0:
            punteggio += bonus_verdi
            motivi.append(f"✅ {num_verdi} requisiti POSSEDUTI (+{bonus_verdi}pt)")
        
        punteggio = max(0, min(100, punteggio))
        
        if punteggio < 40:
            decisione = "NON PARTECIPARE"
        elif punteggio < 65:
            decisione = "PARTECIPARE CON CAUTELA"
        else:
            decisione = "PARTECIPARE"
        
        return decisione, punteggio, motivi
    
    def analyze_bando(self, bando_text: str) -> Dict[str, Any]:
        """
        Analisi completa con STRUCTURED OUTPUT
        
        Args:
            bando_text: testo estratto dal parser
            
        Returns:
            Dizionario analisi completa
        """
        # ESTRAZIONE STRUTTURATA con Pydantic
        requisiti = self.extract_requirements(bando_text)
        
        # Check geografico
        check_geo = self._check_geografico(
            requisiti.comune_stazione_appaltante,
            requisiti.provincia_stazione_appaltante,
            requisiti.regione_stazione_appaltante
        )
        
        # Analizza scadenze
        scadenze_analisi = {"critiche": [], "prossime": [], "ok": []}
        
        for scadenza in requisiti.scadenze:
            if scadenza.data:
                livello, giorni, emoji = self._calcola_urgenza_scadenza(scadenza.data)
                scad_info = {
                    "tipo": scadenza.tipo,
                    "data": scadenza.data,
                    "ora": scadenza.ora,
                    "note": scadenza.note,
                    "livello": livello,
                    "giorni_mancanti": giorni,
                    "emoji": emoji
                }
                
                if livello in ["CRITICO", "SCADUTO"]:
                    scadenze_analisi["critiche"].append(scad_info)
                elif livello == "ATTENZIONE":
                    scadenze_analisi["prossime"].append(scad_info)
                else:
                    scadenze_analisi["ok"].append(scad_info)
        
        # Analizza SOA
        soa_analisi = {"verdi": [], "gialli": [], "rossi": []}
        
        for soa in requisiti.soa_richieste:
            verifica = self._verifica_soa(soa)
            soa_info = {
                "categoria": soa.categoria,
                "descrizione": soa.descrizione,
                "classifica": soa.classifica,
                **verifica
            }
            
            if verifica["status"] == "VERDE":
                soa_analisi["verdi"].append(soa_info)
            else:
                soa_analisi["rossi"].append(soa_info)
        
        # Analizza certificazioni
        cert_analisi = {"verdi": [], "gialli": [], "rossi": []}
        
        for cert in requisiti.certificazioni_richieste:
            verifica = self._verifica_certificazione(cert)
            cert_info = {"tipo": cert, **verifica}
            
            if verifica["status"] == "VERDE":
                cert_analisi["verdi"].append(cert_info)
            elif verifica["status"] == "GIALLO":
                cert_analisi["gialli"].append(cert_info)
            else:
                cert_analisi["rossi"].append(cert_info)
        
        # Analizza figure
        figure_analisi = {"verdi": [], "gialli": [], "rossi": []}
        
        for figura in requisiti.figure_professionali_richieste:
            verifica = self._verifica_figura_professionale(figura)
            figura_info = {"ruolo": figura.ruolo, **verifica}
            
            if verifica["status"] == "VERDE":
                figure_analisi["verdi"].append(figura_info)
            else:
                figure_analisi["gialli"].append(figura_info)
        
        # Calcola decisione
        decisione, punteggio, motivi_score = self._calcola_score_e_decisione(
            soa_analisi, cert_analisi, figure_analisi, scadenze_analisi, 
            check_geo, requisiti
        )
        
        # Converti Pydantic a dict per output
        requisiti_dict = requisiti.model_dump()
        
        return {
            "requisiti_estratti": requisiti_dict,
            "check_geografico": check_geo,
            "scadenze": scadenze_analisi,
            "soa": soa_analisi,
            "certificazioni": cert_analisi,
            "figure_professionali": figure_analisi,
            "decisione": decisione,
            "punteggio_fattibilita": punteggio,
            "motivi_punteggio": motivi_score,
            "num_requisiti": {
                "verdi": len(soa_analisi["verdi"]) + len(cert_analisi["verdi"]) + len(figure_analisi["verdi"]),
                "gialli": len(soa_analisi["gialli"]) + len(cert_analisi["gialli"]) + len(figure_analisi["gialli"]),
                "rossi": len(soa_analisi["rossi"]) + len(cert_analisi["rossi"])
            }
        }