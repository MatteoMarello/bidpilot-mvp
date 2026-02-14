"""
Analyzer per analisi Go/No-Go del bando
Estrae requisiti e li confronta con profilo aziendale
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

from src.prompts import EXTRACTION_PROMPT, MATCH_ANALYSIS_PROMPT


class BandoAnalyzer:
    """Analizza bando e verifica match con profilo aziendale"""
    
    def __init__(self, openai_api_key: str, profilo_path: str = "config/profilo_azienda.json"):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=openai_api_key
        )
        
        # Carica profilo aziendale
        with open(profilo_path, 'r', encoding='utf-8') as f:
            self.profilo_azienda = json.load(f)
    
    def extract_requirements(self, bando_text: str) -> Dict[str, Any]:
        """
        Estrae requisiti strutturati dal testo del bando
        
        Args:
            bando_text: testo completo del bando
            
        Returns:
            dizionario con requisiti estratti
        """
        prompt = PromptTemplate(
            template=EXTRACTION_PROMPT,
            input_variables=["bando_text"]
        )
        
        chain = prompt | self.llm
        
        # Limita il testo se troppo lungo (max ~12k caratteri per evitare overflow)
        if len(bando_text) > 12000:
            bando_text = bando_text[:12000] + "\n\n[...testo troncato...]"
        
        response = chain.invoke({"bando_text": bando_text})
        
        try:
            # Estrai JSON dalla risposta
            content = response.content
            
            # Rimuovi markdown se presente
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            requisiti = json.loads(content.strip())
            return requisiti
            
        except json.JSONDecodeError as e:
            raise Exception(f"Errore nel parsing del JSON estratto: {str(e)}\nRisposta LLM: {response.content}")
    
    def _calcola_urgenza_scadenza(self, data_str: str) -> tuple:
        """
        Calcola urgenza di una scadenza
        
        Returns:
            (livello, giorni_mancanti, emoji)
            livello: 'CRITICO' | 'ATTENZIONE' | 'OK'
        """
        try:
            data_scadenza = datetime.strptime(data_str, "%Y-%m-%d")
            oggi = datetime.now()
            giorni = (data_scadenza - oggi).days
            
            if giorni < 0:
                return "SCADUTO", giorni, "⛔"
            elif giorni <= 2:
                return "CRITICO", giorni, "🔴"
            elif giorni <= 7:
                return "ATTENZIONE", giorni, "🟡"
            else:
                return "OK", giorni, "🟢"
                
        except:
            return "SCONOSCIUTO", None, "❓"
    
    def _verifica_soa(self, soa_richiesta: Dict) -> Dict:
        """Verifica se azienda possiede SOA richiesta"""
        categoria_richiesta = soa_richiesta.get("categoria", "")
        classifica_richiesta = soa_richiesta.get("classifica", "")
        
        for soa in self.profilo_azienda.get("soa_possedute", []):
            if soa["categoria"] == categoria_richiesta:
                # Verifica anche classifica (III > II > I)
                classifica_map = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}
                classifica_posseduta = classifica_map.get(soa["classifica"], 0)
                classifica_richiesta_num = classifica_map.get(classifica_richiesta, 0)
                
                if classifica_posseduta >= classifica_richiesta_num:
                    return {
                        "status": "VERDE",
                        "motivo": f"SOA {categoria_richiesta} Classifica {soa['classifica']} presente (scadenza {soa['scadenza']})"
                    }
                else:
                    return {
                        "status": "ROSSO",
                        "motivo": f"SOA {categoria_richiesta} presente ma classifica insufficiente ({soa['classifica']} < {classifica_richiesta})"
                    }
        
        return {
            "status": "ROSSO",
            "motivo": f"SOA {categoria_richiesta} non posseduta"
        }
    
    def _verifica_certificazione(self, cert_richiesta: str) -> Dict:
        """Verifica se azienda possiede certificazione"""
        cert_possedute = [c["tipo"] for c in self.profilo_azienda.get("certificazioni", [])]
        
        # Match esatto o parziale
        for cert in cert_possedute:
            if cert.lower() in cert_richiesta.lower() or cert_richiesta.lower() in cert.lower():
                cert_data = next((c for c in self.profilo_azienda["certificazioni"] if c["tipo"] == cert), None)
                return {
                    "status": "VERDE",
                    "motivo": f"{cert} presente (rinnovata {cert_data['data_rilascio']})"
                }
        
        return {
            "status": "GIALLO",
            "motivo": f"{cert_richiesta} - Verificare con fornitore o richiedere certificazione"
        }
    
    def _verifica_figura_professionale(self, figura: Dict) -> Dict:
        """Verifica disponibilità figura professionale"""
        ruolo = figura.get("ruolo", "")
        
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
                    "motivo": f"{ruolo} - Contattare {collab['nome_studio']} (ultimo utilizzo: {collab['ultimo_utilizzo']}, costo medio: €{collab['costo_medio']})"
                }
        
        return {
            "status": "GIALLO",
            "motivo": f"{ruolo} - Figura non in database. Verificare disponibilità consulenti esterni"
        }
    
    def analyze_bando(self, bando_text: str) -> Dict[str, Any]:
        """
        Analisi completa del bando con verifica requisiti
        
        Args:
            bando_text: testo completo del bando
            
        Returns:
            dizionario con analisi completa e semafori
        """
        # Estrai requisiti
        requisiti = self.extract_requirements(bando_text)
        
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
        
        # Calcola decisione finale
        num_rossi = len(soa_analisi["rossi"]) + len(cert_analisi["rossi"]) + len(figure_analisi["rossi"])
        num_gialli = len(soa_analisi["gialli"]) + len(cert_analisi["gialli"]) + len(figure_analisi["gialli"])
        num_verdi = len(soa_analisi["verdi"]) + len(cert_analisi["verdi"]) + len(figure_analisi["verdi"])
        
        if num_rossi > 0:
            decisione = "NON PARTECIPARE"
            punteggio = max(0, 40 - (num_rossi * 20))
        elif num_gialli > 2:
            decisione = "PARTECIPARE CON CAUTELA"
            punteggio = 60 + (num_verdi * 2) - (num_gialli * 5)
        else:
            decisione = "PARTECIPARE"
            punteggio = min(100, 75 + (num_verdi * 3) - (num_gialli * 5))
        
        return {
            "requisiti_estratti": requisiti,
            "scadenze": scadenze_analisi,
            "soa": soa_analisi,
            "certificazioni": cert_analisi,
            "figure_professionali": figure_analisi,
            "decisione": decisione,
            "punteggio_fattibilita": punteggio,
            "num_requisiti": {
                "verdi": num_verdi,
                "gialli": num_gialli,
                "rossi": num_rossi
            }
        }
