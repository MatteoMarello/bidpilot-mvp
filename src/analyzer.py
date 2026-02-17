"""
Analyzer ANTI-ALLUCINAZIONE con Structured Output Pydantic
Versione pulita e ottimizzata
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from src.schemas import BandoRequisiti
from src.prompts import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT


# Classifiche SOA → Importo massimo gestibile
CLASSIFICHE_SOA = {
    "I": 258_000, "II": 516_000, "III": 1_033_000, "IV": 2_065_000,
    "V": 3_098_000, "VI": 5_165_000, "VII": 10_329_000, "VIII": float('inf')
}

# Mapping comuni principali → regioni (per validazione anti-allucinazione)
GEO_VALIDATION = {
    "roma": "lazio", "milano": "lombardia", "torino": "piemonte",
    "napoli": "campania", "palermo": "sicilia", "genova": "liguria",
    "bologna": "emilia-romagna", "firenze": "toscana", "bari": "puglia"
}


class BandoAnalyzer:
    """Analizzatore bandi con structured output e validazione anti-allucinazione"""
    
    def __init__(self, openai_api_key: str, profilo_path: str = "config/profilo_azienda.json"):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=openai_api_key
        )
        
        with open(profilo_path, 'r', encoding='utf-8') as f:
            self.profilo = json.load(f)
    
    def extract_requirements(self, bando_text: str) -> BandoRequisiti:
        """Estrae requisiti usando structured output Pydantic"""
        # GPT-4o gestisce ~400k caratteri (128k token).
        # NON troncare a 50k - i requisiti SOA/certificazioni sono spesso
        # nelle pagine centrali del bando (pag. 20-35) e verrebbero persi.
        # Limite alzato a 300k per coprire bandi anche di 200+ pagine.
        MAX_LENGTH = 300_000
        if len(bando_text) > MAX_LENGTH:
            half = MAX_LENGTH // 2
            bando_text = bando_text[:half] + "\n\n[...TRONCATO - DOC. MOLTO LUNGO...]\n\n" + bando_text[-half:]
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", EXTRACTION_SYSTEM_PROMPT),
            ("user", EXTRACTION_USER_PROMPT)
        ])
        
        structured_llm = self.llm.with_structured_output(BandoRequisiti)
        chain = prompt | structured_llm
        
        try:
            requisiti = chain.invoke({"bando_text": bando_text})
            self._validate_extraction(requisiti)
            return requisiti
        except Exception as e:
            raise Exception(f"Errore estrazione: {str(e)}")
    
    def _validate_extraction(self, req: BandoRequisiti) -> None:
        """Validazione geografica anti-allucinazione"""
        if req.comune_stazione_appaltante and req.regione_stazione_appaltante:
            comune = req.comune_stazione_appaltante.lower()
            regione = req.regione_stazione_appaltante.lower()
            
            expected = GEO_VALIDATION.get(comune)
            if expected and expected not in regione:
                raise ValueError(
                    f"INCOERENZA GEOGRAFICA: Comune '{req.comune_stazione_appaltante}' "
                    f"non può essere in regione '{req.regione_stazione_appaltante}'"
                )
        
        # Importo ragionevole
        if req.importo_lavori and req.importo_lavori > 100_000_000:
            print(f"⚠️ Importo molto alto: €{req.importo_lavori:,.0f}")
    
    def _calcola_urgenza(self, data_str: str) -> Tuple[str, Optional[int], str]:
        """Calcola urgenza scadenza"""
        try:
            data = datetime.strptime(data_str, "%Y-%m-%d")
            giorni = (data - datetime.now()).days
            
            if giorni < 0:   return "SCADUTO", giorni, "⛔"
            if giorni <= 2:  return "CRITICO", giorni, "🔴"
            if giorni <= 7:  return "ATTENZIONE", giorni, "🟡"
            return "OK", giorni, "🟢"
        except:
            return "SCONOSCIUTO", None, "❓"
    
    def _check_geografico(self, comune: str, provincia: str, regione: str) -> Dict:
        """Verifica zona geografica"""
        aree = self.profilo.get("aree_geografiche", [])
        if not aree:
            return {"in_zona": True, "motivo": "Aree non specificate", "warning": False}
        
        regione_norm = (regione or "").strip().title()
        if any(regione_norm in area for area in aree):
            return {
                "in_zona": True,
                "motivo": f"Bando in {regione_norm}, area abituale",
                "warning": False
            }
        
        return {
            "in_zona": False,
            "motivo": f"Bando in {regione_norm} - Fuori aree abituali ({', '.join(aree)})",
            "warning": True
        }
    
    def _verifica_soa(self, soa_richiesta) -> Dict:
        """Verifica SOA con calcolo gap"""
        cat_req = soa_richiesta.categoria
        class_req = soa_richiesta.classifica
        
        for soa in self.profilo.get("soa_possedute", []):
            if soa["categoria"] != cat_req:
                continue
            
            class_map = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8}
            poss = class_map.get(soa["classifica"], 0)
            rich = class_map.get(class_req, 0)
            
            if poss >= rich:
                return {
                    "status": "VERDE",
                    "motivo": f"SOA {cat_req} Classifica {soa['classifica']} presente (scad. {soa['scadenza']})"
                }
            else:
                gap = CLASSIFICHE_SOA.get(class_req, 0) - CLASSIFICHE_SOA.get(soa["classifica"], 0)
                return {
                    "status": "ROSSO",
                    "motivo": f"SOA {cat_req} presente ma mancano €{gap:,} per Classifica {class_req}",
                    "suggerimento": "Valutare AVVALIMENTO con impresa di classifica superiore"
                }
        
        return {
            "status": "ROSSO",
            "motivo": f"SOA {cat_req} Classifica {class_req} NON posseduta",
            "suggerimento": "Ricorrere ad AVVALIMENTO con impresa che possiede SOA richiesta"
        }
    
    def _verifica_certificazione(self, cert_req: str) -> Dict:
        """Verifica certificazione"""
        for cert in self.profilo.get("certificazioni", []):
            tipo = cert.get("tipo", "")
            if tipo.lower() in cert_req.lower() or cert_req.lower() in tipo.lower():
                # Check scadenza
                if scad := cert.get("scadenza"):
                    try:
                        if datetime.strptime(scad, "%Y-%m-%d") < datetime.now():
                            return {
                                "status": "ROSSO",
                                "motivo": f"{tipo} SCADUTA il {scad} - RINNOVARE"
                            }
                    except:
                        pass
                
                return {"status": "VERDE", "motivo": f"{tipo} presente"}
        
        return {
            "status": "GIALLO",
            "motivo": f"{cert_req} - Verificare con fornitore",
            "suggerimento": "Contattare ente certificatore"
        }
    
    def _verifica_figura(self, figura) -> Dict:
        """Verifica figura professionale"""
        ruolo = figura.ruolo
        
        if ruolo in self.profilo.get("figure_professionali_interne", []):
            return {"status": "VERDE", "motivo": f"{ruolo} disponibile internamente"}
        
        for collab in self.profilo.get("collaboratori_esterni_abituali", []):
            if ruolo.lower() in collab["tipo"].lower():
                return {
                    "status": "GIALLO",
                    "motivo": f"{ruolo} - Contattare {collab['nome_studio']} (€{collab['costo_medio']:,})",
                    "costo_stimato": collab["costo_medio"]
                }
        
        return {
            "status": "GIALLO",
            "motivo": f"{ruolo} - Cercare consulente esterno",
            "suggerimento": "Contattare ordini professionali"
        }
    
    def _calcola_score(self, soa_an, cert_an, fig_an, scad_an, geo) -> Tuple[str, int, List[str]]:
        """Calcola score e decisione"""
        rossi = len(soa_an["rossi"]) + len(cert_an["rossi"])
        gialli = len(soa_an["gialli"]) + len(cert_an["gialli"]) + len(fig_an["gialli"])
        verdi = len(soa_an["verdi"]) + len(cert_an["verdi"]) + len(fig_an["verdi"])
        
        score = 100
        motivi = []
        
        if rossi > 0:
            score -= rossi * 40
            soa_manc = [s["categoria"] for s in soa_an["rossi"]]
            if soa_manc:
                motivi.append(f"❌ SOA MANCANTI: {', '.join(soa_manc)} (-{len(soa_an['rossi'])*40}pt)")
        
        if crit := len(scad_an["critiche"]):
            score -= crit * 20
            motivi.append(f"🔴 {crit} scadenza/e CRITICA/E (-{crit*20}pt)")
        
        if gialli > 0:
            score -= gialli * 10
            motivi.append(f"🟡 {gialli} requisiti DA VERIFICARE (-{gialli*10}pt)")
        
        if not geo["in_zona"]:
            score -= 15
            motivi.append("🗺️ Bando FUORI ZONA (-15pt)")
        
        bonus = min(20, verdi * 5)
        if bonus:
            score += bonus
            motivi.append(f"✅ {verdi} requisiti POSSEDUTI (+{bonus}pt)")
        
        score = max(0, min(100, score))
        
        if score < 40:
            decisione = "NON PARTECIPARE"
        elif score < 65:
            decisione = "PARTECIPARE CON CAUTELA"
        else:
            decisione = "PARTECIPARE"
        
        return decisione, score, motivi
    
    def analyze_bando(self, bando_text: str) -> Dict[str, Any]:
        """Analisi completa bando"""
        # Estrazione strutturata
        req = self.extract_requirements(bando_text)
        
        # Check geografico
        geo = self._check_geografico(
            req.comune_stazione_appaltante,
            req.provincia_stazione_appaltante,
            req.regione_stazione_appaltante
        )
        
        # Analizza scadenze
        scad = {"critiche": [], "prossime": [], "ok": [], "scadute": []}
        for s in req.scadenze:
            if s.data:
                liv, giorni, emoji = self._calcola_urgenza(s.data)
                info = {
                    "tipo": s.tipo, "data": s.data, "ora": s.ora,
                    "note": s.note, "livello": liv, "giorni_mancanti": giorni, "emoji": emoji
                }
                if liv == "SCADUTO":
                    scad["scadute"].append(info)   # già passate: info ma NO penalità
                elif liv == "CRITICO":
                    scad["critiche"].append(info)  # ≤2 giorni: urgente
                elif liv == "ATTENZIONE":
                    scad["prossime"].append(info)
                else:
                    scad["ok"].append(info)
        
        # Analizza SOA
        soa = {"verdi": [], "gialli": [], "rossi": []}
        for s in req.soa_richieste:
            ver = self._verifica_soa(s)
            info = {"categoria": s.categoria, "descrizione": s.descrizione, "classifica": s.classifica, **ver}
            soa["rossi" if ver["status"] == "ROSSO" else "verdi"].append(info)
        
        # Analizza certificazioni
        cert = {"verdi": [], "gialli": [], "rossi": []}
        for c in req.certificazioni_richieste:
            ver = self._verifica_certificazione(c)
            info = {"tipo": c, **ver}
            cert[ver["status"].lower() + "i"].append(info)
        
        # Analizza figure
        fig = {"verdi": [], "gialli": [], "rossi": []}
        for f in req.figure_professionali_richieste:
            ver = self._verifica_figura(f)
            info = {"ruolo": f.ruolo, **ver}
            fig["gialli" if ver["status"] == "GIALLO" else "verdi"].append(info)
        
        # Calcola decisione
        decisione, punteggio, motivi = self._calcola_score(soa, cert, fig, scad, geo)
        
        return {
            "requisiti_estratti": req.model_dump(),
            "check_geografico": geo,
            "scadenze": scad,
            "soa": soa,
            "certificazioni": cert,
            "figure_professionali": fig,
            "decisione": decisione,
            "punteggio_fattibilita": punteggio,
            "motivi_punteggio": motivi
        }