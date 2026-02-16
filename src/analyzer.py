"""
Analyzer per analisi Go/No-Go del bando - VERSIONE MIGLIORATA
Con matching puntuale, check geografico, gap SOA, suggerimenti avvalimento
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

# Import dal file prompts
# from src.prompts import EXTRACTION_PROMPT  # Verrà importato quando file sarà sostituito


# Mapping classifiche SOA -> importo massimo
CLASSIFICHE_SOA_IMPORTO = {
    "I": 258000,
    "II": 516000,
    "III": 1033000,
    "IV": 2065000,
    "V": 3098000,
    "VI": 5165000,
    "VII": 10329000,
    "VIII": float('inf')  # Illimitato
}


class BandoAnalyzer:
    """Analizza bando e verifica match con profilo aziendale - VERSIONE MIGLIORATA"""
    
    def __init__(self, openai_api_key: str, profilo_path: str = "config/profilo_azienda.json"):
        try:
            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0,
                api_key=openai_api_key
            )
        except Exception as e:
            if "unexpected keyword argument 'proxies'" in str(e):
                raise RuntimeError(
                    "Incompatibilità tra pacchetti OpenAI/LangChain rilevata. "
                    "Allinea le dipendenze: pip install -r requirements.txt --upgrade --force-reinstall"
                ) from e
            raise
        
        # Carica profilo aziendale
        with open(profilo_path, 'r', encoding='utf-8') as f:
            self.profilo_azienda = json.load(f)
    
    def extract_requirements(self, bando_text: str, extraction_prompt: str) -> Dict[str, Any]:
        """
        Estrae requisiti strutturati dal testo del bando
        
        Args:
            bando_text: testo completo del bando
            extraction_prompt: template prompt per extraction
            
        Returns:
            dizionario con requisiti estratti
        """
        prompt = PromptTemplate(
            template=extraction_prompt,
            input_variables=["bando_text"]
        )
        
        chain = prompt | self.llm
        
        # Limita il testo se troppo lungo
        if len(bando_text) > 15000:
            bando_text = bando_text[:15000] + "\n\n[...testo troncato per lunghezza...]"
        
        response = chain.invoke({"bando_text": bando_text})
        
        try:
            content = response.content
            
            # Rimuovi markdown se presente
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            requisiti = json.loads(content.strip())
            return requisiti
            
        except json.JSONDecodeError as e:
            raise Exception(f"Errore parsing JSON estratto: {str(e)}\nRisposta LLM: {response.content[:500]}")
    
    def _calcola_urgenza_scadenza(self, data_str: str) -> Tuple[str, int, str]:
        """
        Calcola urgenza di una scadenza
        
        Returns:
            (livello, giorni_mancanti, emoji)
        """
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
        """
        Verifica se il bando è nella zona geografica abituale dell'azienda
        
        Returns:
            {"in_zona": bool, "motivo": str, "warning": bool}
        """
        aree_abituali = self.profilo_azienda.get("aree_geografiche", [])
        
        # Normalizza input
        comune_norm = (comune_bando or "").strip().lower()
        provincia_norm = (provincia_bando or "").strip().upper()
        regione_norm = (regione_bando or "").strip().title()
        
        if not aree_abituali:
            # Nessuna area specificata = va bene tutto
            return {
                "in_zona": True,
                "motivo": "Area geografiche non specificate nel profilo",
                "warning": False
            }
        
        # Check regione
        for area in aree_abituali:
            area_norm = area.strip().title()
            
            # Match esatto regione
            if regione_norm and area_norm == regione_norm:
                return {
                    "in_zona": True,
                    "motivo": f"Bando in {regione_norm}, area abituale dell'azienda",
                    "warning": False
                }
            
            # Match parziale (es: "Lombardia" in "Milano, Lombardia")
            if regione_norm and regione_norm in area_norm:
                return {
                    "in_zona": True,
                    "motivo": f"Bando in {regione_norm}, area abituale",
                    "warning": False
                }
        
        # Fuori zona
        aree_str = ", ".join(aree_abituali)
        return {
            "in_zona": False,
            "motivo": f"Bando in {regione_norm or comune_norm or 'località non specificata'} - Fuori dalle aree abituali ({aree_str})",
            "warning": True
        }
    
    def _calcola_gap_classifica(self, classifica_richiesta: str, classifica_posseduta: str) -> Dict:
        """
        Calcola gap monetario tra classifica posseduta e richiesta
        
        Returns:
            {"gap_euro": int, "gap_descrizione": str}
        """
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
                "gap_descrizione": f"Classifica {classifica_posseduta} sufficiente (richiesta {classifica_richiesta})"
            }
    
    def _verifica_soa(self, soa_richiesta: Dict) -> Dict:
        """Verifica se azienda possiede SOA richiesta - CON GAP CALCOLO"""
        categoria_richiesta = soa_richiesta.get("categoria", "")
        classifica_richiesta = soa_richiesta.get("classifica", "")
        
        for soa in self.profilo_azienda.get("soa_possedute", []):
            if soa["categoria"] == categoria_richiesta:
                classifica_posseduta = soa["classifica"]
                
                # Verifica classifica (III > II > I)
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
        
        # SOA non posseduta affatto
        return {
            "status": "ROSSO",
            "motivo": f"SOA {categoria_richiesta} Classifica {classifica_richiesta} NON posseduta",
            "gap": {"gap_euro": CLASSIFICHE_SOA_IMPORTO.get(classifica_richiesta, 0), 
                    "gap_descrizione": f"Categoria {categoria_richiesta} non presente in profilo"},
            "suggerimento": "Ricorrere ad AVVALIMENTO con impresa che possiede la SOA richiesta"
        }
    
    def _verifica_certificazione(self, cert_richiesta: str) -> Dict:
        """Verifica se azienda possiede certificazione"""
        cert_richiesta_norm = (cert_richiesta or "").strip()
        if not cert_richiesta_norm:
            return {
                "status": "GIALLO",
                "motivo": "Certificazione non specificata nel bando"
            }

        cert_possedute = [
            (c.get("tipo") or "").strip()
            for c in self.profilo_azienda.get("certificazioni", [])
            if isinstance(c, dict)
        ]
        
        # Match esatto o parziale
        for cert in cert_possedute:
            if not cert:
                continue
            if cert.lower() in cert_richiesta_norm.lower() or cert_richiesta_norm.lower() in cert.lower():
                cert_data = next(
                    (c for c in self.profilo_azienda["certificazioni"] if c.get("tipo") == cert),
                    None
                )
                
                # Check scadenza certificazione
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
                
                data_rilascio = cert_data.get("data_rilascio", "data non disponibile") if cert_data else "data non disponibile"
                return {
                    "status": "VERDE",
                    "motivo": f"{cert} presente (rinnovata {data_rilascio})"
                }
        
        return {
            "status": "GIALLO",
            "motivo": f"{cert_richiesta_norm} - Verificare con fornitore o richiedere certificazione",
            "suggerimento": "Contattare ente certificatore per tempistiche rilascio"
        }
    
    def _verifica_figura_professionale(self, figura: Dict) -> Dict:
        """Verifica disponibilità figura professionale"""
        ruolo = (figura.get("ruolo") or "").strip()
        
        # Verifica se è interno
        if ruolo in self.profilo_azienda.get("figure_professionali_interne", []):
            return {
                "status": "VERDE",
                "motivo": f"{ruolo} disponibile internamente"
            }
        
        # Verifica se è collaboratore esterno abituale
        for collab in self.profilo_azienda.get("collaboratori_esterni_abituali", []):
            if ruolo.lower() in collab["tipo"].lower():
                return {
                    "status": "GIALLO",
                    "motivo": f"{ruolo} - Contattare {collab['nome_studio']} (ultimo utilizzo: {collab['ultimo_utilizzo']}, costo medio: €{collab['costo_medio']:,})",
                    "costo_stimato": collab["costo_medio"]
                }
        
        return {
            "status": "GIALLO",
            "motivo": f"{ruolo} - Figura non in database. Verificare disponibilità consulenti esterni",
            "suggerimento": "Cercare professionista tramite ordini professionali o network aziendali"
        }
    
    def _calcola_score_e_decisione(self, 
                                    soa_analisi: Dict, 
                                    cert_analisi: Dict, 
                                    figure_analisi: Dict,
                                    scadenze_analisi: Dict,
                                    check_geo: Dict,
                                    requisiti: Dict) -> Tuple[str, int, List[str]]:
        """
        Calcola decisione finale e score con spiegazione WHY
        
        Returns:
            (decisione, punteggio, motivi_list)
        """
        num_rossi = len(soa_analisi["rossi"]) + len(cert_analisi["rossi"]) + len(figure_analisi["rossi"])
        num_gialli = len(soa_analisi["gialli"]) + len(cert_analisi["gialli"]) + len(figure_analisi["gialli"])
        num_verdi = len(soa_analisi["verdi"]) + len(cert_analisi["verdi"]) + len(figure_analisi["verdi"])
        
        punteggio = 100  # Partiamo da 100
        motivi = []
        
        # KILLER FACTORS (-80 punti ciascuno)
        if num_rossi > 0:
            punteggio -= num_rossi * 40
            if soa_analisi["rossi"]:
                soa_mancanti = [s["categoria"] for s in soa_analisi["rossi"]]
                motivi.append(f"❌ SOA MANCANTI: {', '.join(soa_mancanti)} (-{len(soa_analisi['rossi'])*40}pt)")
            if cert_analisi["rossi"]:
                motivi.append(f"❌ Certificazioni scadute o critiche (-{len(cert_analisi['rossi'])*40}pt)")
        
        # Scadenze critiche (-20 punti ciascuna)
        if scadenze_analisi["critiche"]:
            num_critiche = len(scadenze_analisi["critiche"])
            punteggio -= num_critiche * 20
            motivi.append(f"🔴 {num_critiche} scadenza/e CRITICA/E entro 2 giorni (-{num_critiche*20}pt)")
        
        # Requisiti gialli (-10 punti ciascuno)
        if num_gialli > 0:
            punteggio -= num_gialli * 10
            motivi.append(f"🟡 {num_gialli} requisiti DA VERIFICARE (-{num_gialli*10}pt)")
        
        # Fuori zona geografica (-15 punti)
        if not check_geo["in_zona"]:
            punteggio -= 15
            motivi.append(f"🗺️ Bando FUORI ZONA abituale (-15pt)")
        
        # Importo fuori sweet spot (-10 punti)
        importo_gara = requisiti.get("importo_lavori", 0)
        sweet_spot = self.profilo_azienda.get("importi_gara", {}).get("sweet_spot", [0, 999999999])
        if importo_gara > 0:
            if importo_gara < sweet_spot[0] or importo_gara > sweet_spot[1]:
                punteggio -= 10
                motivi.append(f"💰 Importo €{importo_gara:,} fuori sweet spot (€{sweet_spot[0]:,}-€{sweet_spot[1]:,}) (-10pt)")
        
        # Bonus per requisiti verdi (+5 punti ciascuno, max +20)
        bonus_verdi = min(20, num_verdi * 5)
        if bonus_verdi > 0:
            punteggio += bonus_verdi
            motivi.append(f"✅ {num_verdi} requisiti POSSEDUTI (+{bonus_verdi}pt)")
        
        # Limita punteggio tra 0 e 100
        punteggio = max(0, min(100, punteggio))
        
        # Decisione basata su punteggio
        if punteggio < 40:
            decisione = "NON PARTECIPARE"
        elif punteggio < 65:
            decisione = "PARTECIPARE CON CAUTELA"
        else:
            decisione = "PARTECIPARE"
        
        return decisione, punteggio, motivi
    
    def analyze_bando(self, bando_text: str, extraction_prompt: str) -> Dict[str, Any]:
        """
        Analisi completa del bando con verifica requisiti - VERSIONE MIGLIORATA
        
        Args:
            bando_text: testo completo del bando
            extraction_prompt: prompt per estrazione (passato da fuori)
            
        Returns:
            dizionario con analisi completa e semafori
        """
        # Estrai requisiti
        requisiti = self.extract_requirements(bando_text, extraction_prompt)
        
        # Check geografico
        check_geo = self._check_geografico(
            requisiti.get("comune_stazione_appaltante", ""),
            requisiti.get("provincia_stazione_appaltante", ""),
            requisiti.get("regione_stazione_appaltante", "")
        )
        
        # Analizza scadenze
        scadenze_analisi = {
            "critiche": [],
            "prossime": [],
            "ok": []
        }
        
        for scadenza in requisiti.get("scadenze", []):
            livello, giorni, emoji = self._calcola_urgenza_scadenza(scadenza["data"])
            scadenza_info = {
                **scadenza,
                "livello": livello,
                "giorni_mancanti": giorni,
                "emoji": emoji
            }
            
            if livello == "CRITICO" or livello == "SCADUTO":
                scadenze_analisi["critiche"].append(scadenza_info)
            elif livello == "ATTENZIONE":
                scadenze_analisi["prossime"].append(scadenza_info)
            else:
                scadenze_analisi["ok"].append(scadenza_info)
        
        # Analizza SOA
        soa_analisi = {
            "verdi": [],
            "gialli": [],
            "rossi": []
        }
        
        for soa in requisiti.get("soa_richieste", []):
            verifica = self._verifica_soa(soa)
            soa_info = {**soa, **verifica}
            
            if verifica["status"] == "VERDE":
                soa_analisi["verdi"].append(soa_info)
            elif verifica["status"] == "GIALLO":
                soa_analisi["gialli"].append(soa_info)
            else:
                soa_analisi["rossi"].append(soa_info)
        
        # Analizza certificazioni
        cert_analisi = {
            "verdi": [],
            "gialli": [],
            "rossi": []
        }
        
        for cert in requisiti.get("certificazioni_richieste", []):
            verifica = self._verifica_certificazione(cert)
            cert_info = {"tipo": cert, **verifica}
            
            if verifica["status"] == "VERDE":
                cert_analisi["verdi"].append(cert_info)
            elif verifica["status"] == "GIALLO":
                cert_analisi["gialli"].append(cert_info)
            else:
                cert_analisi["rossi"].append(cert_info)
        
        # Analizza figure professionali
        figure_analisi = {
            "verdi": [],
            "gialli": [],
            "rossi": []
        }
        
        for figura in requisiti.get("figure_professionali_richieste", []):
            verifica = self._verifica_figura_professionale(figura)
            figura_info = {**figura, **verifica}
            
            if verifica["status"] == "VERDE":
                figure_analisi["verdi"].append(figura_info)
            elif verifica["status"] == "GIALLO":
                figure_analisi["gialli"].append(figura_info)
            else:
                figure_analisi["rossi"].append(figura_info)
        
        # Calcola decisione finale CON MOTIVI
        decisione, punteggio, motivi_score = self._calcola_score_e_decisione(
            soa_analisi, cert_analisi, figure_analisi, scadenze_analisi, check_geo, requisiti
        )
        
        num_rossi = len(soa_analisi["rossi"]) + len(cert_analisi["rossi"]) + len(figure_analisi["rossi"])
        num_gialli = len(soa_analisi["gialli"]) + len(cert_analisi["gialli"]) + len(figure_analisi["gialli"])
        num_verdi = len(soa_analisi["verdi"]) + len(cert_analisi["verdi"]) + len(figure_analisi["verdi"])
        
        return {
            "requisiti_estratti": requisiti,
            "check_geografico": check_geo,
            "scadenze": scadenze_analisi,
            "soa": soa_analisi,
            "certificazioni": cert_analisi,
            "figure_professionali": figure_analisi,
            "decisione": decisione,
            "punteggio_fattibilita": punteggio,
            "motivi_punteggio": motivi_score,  # NUOVO: spiegazione score
            "num_requisiti": {
                "verdi": num_verdi,
                "gialli": num_gialli,
                "rossi": num_rossi
            }
        }