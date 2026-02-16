"""
BidPilot MVP - Applicazione Streamlit VERSIONE MIGLIORATA
Sistema AI per analisi bandi con UI professionale e matching puntuale
"""
import streamlit as st
import os
import json
from datetime import datetime

# IMPORTANTE: Quando sostituisci i file, decommentare queste import:
from src.parser import BandoParser
from src.analyzer import BandoAnalyzer
from src.rag_engine import RAGEngine

# Per ora uso un placeholder per mostrare la struttura
# Nella versione finale, queste classi saranno importate normalmente


# Configurazione pagina
st.set_page_config(
    page_title="BidPilot 2.0 - Analisi Intelligente",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS PROFESSIONALE - Box grandi, colori evidenti, tipografia chiara
st.markdown("""
<style>
    /* Font professionale */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* DASHBOARD HEADER - KPI Grandi */
    .dashboard-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 30px;
        border-radius: 15px;
        margin-bottom: 30px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    
    .dashboard-kpi {
        text-align: center;
        color: white;
    }
    
    .dashboard-kpi h1 {
        font-size: 48px;
        margin: 0;
        font-weight: 700;
    }
    
    .dashboard-kpi p {
        font-size: 16px;
        margin: 5px 0 0 0;
        opacity: 0.9;
    }
    
    /* BOX DECISIONE GIGANTE */
    .decisione-box {
        padding: 40px;
        border-radius: 20px;
        margin: 30px 0;
        text-align: center;
        box-shadow: 0 15px 40px rgba(0,0,0,0.15);
        border: 4px solid;
    }
    
    .decisione-box.verde {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border-color: #28a745;
    }
    
    .decisione-box.giallo {
        background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
        border-color: #ffc107;
    }
    
    .decisione-box.rosso {
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
        border-color: #dc3545;
    }
    
    .decisione-box h1 {
        font-size: 56px;
        margin: 0;
        font-weight: 700;
    }
    
    .decisione-box .score {
        font-size: 72px;
        font-weight: 700;
        margin: 20px 0;
    }
    
    .decisione-box .score-label {
        font-size: 20px;
        opacity: 0.8;
    }
    
    /* KILLER FACTORS - Box evidenziato */
    .killer-factors {
        background: #fff3cd;
        border-left: 8px solid #ff6b6b;
        padding: 25px;
        border-radius: 10px;
        margin: 20px 0;
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    
    .killer-factors h3 {
        color: #dc3545;
        margin-top: 0;
        font-size: 24px;
    }
    
    .killer-item {
        background: white;
        padding: 15px;
        margin: 10px 0;
        border-radius: 8px;
        border-left: 4px solid #dc3545;
    }
    
    /* SCADENZE COUNTDOWN */
    .scadenza-critica {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%);
        color: white;
        padding: 25px;
        border-radius: 15px;
        margin: 15px 0;
        box-shadow: 0 8px 20px rgba(255,107,107,0.3);
        animation: pulse 2s ease-in-out infinite;
    }
    
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.02); }
    }
    
    .scadenza-critica .countdown {
        font-size: 48px;
        font-weight: 700;
        margin: 10px 0;
    }
    
    .scadenza-attenzione {
        background: linear-gradient(135deg, #ffc107 0%, #ffca2c 100%);
        color: #856404;
        padding: 20px;
        border-radius: 12px;
        margin: 12px 0;
        box-shadow: 0 5px 15px rgba(255,193,7,0.3);
    }
    
    /* BOX STATUS COLORATI */
    .status-box {
        padding: 20px;
        border-radius: 12px;
        margin: 15px 0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    
    .status-box.verde {
        background: #d4edda;
        border-left: 6px solid #28a745;
    }
    
    .status-box.giallo {
        background: #fff3cd;
        border-left: 6px solid #ffc107;
    }
    
    .status-box.rosso {
        background: #f8d7da;
        border-left: 6px solid #dc3545;
    }
    
    .status-box h4 {
        margin-top: 0;
        font-size: 18px;
        font-weight: 600;
    }
    
    .status-box p {
        margin: 8px 0;
        font-size: 14px;
    }
    
    /* PROGRESS BAR CUSTOM */
    .custom-progress {
        height: 40px;
        background: #e9ecef;
        border-radius: 20px;
        overflow: hidden;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .custom-progress-fill {
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 700;
        font-size: 18px;
        transition: width 0.5s ease;
    }
    
    .progress-verde {
        background: linear-gradient(90deg, #28a745 0%, #20c997 100%);
    }
    
    .progress-giallo {
        background: linear-gradient(90deg, #ffc107 0%, #fd7e14 100%);
    }
    
    .progress-rosso {
        background: linear-gradient(90deg, #dc3545 0%, #c82333 100%);
    }
    
    /* METRICS CARDS */
    .metric-card {
        background: white;
        padding: 25px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        text-align: center;
        border-top: 4px solid;
    }
    
    .metric-card.verde {
        border-color: #28a745;
    }
    
    .metric-card.giallo {
        border-color: #ffc107;
    }
    
    .metric-card.rosso {
        border-color: #dc3545;
    }
    
    .metric-card .value {
        font-size: 42px;
        font-weight: 700;
        margin: 10px 0;
    }
    
    .metric-card .label {
        font-size: 14px;
        color: #6c757d;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* MOTIVI PUNTEGGIO */
    .motivo-item {
        padding: 12px 15px;
        margin: 8px 0;
        border-radius: 8px;
        background: #f8f9fa;
        border-left: 4px solid #6c757d;
        font-size: 15px;
    }
    
    /* SUGGERIMENTI */
    .suggerimento-box {
        background: #e7f3ff;
        border-left: 5px solid #007bff;
        padding: 18px;
        border-radius: 8px;
        margin: 12px 0;
    }
    
    .suggerimento-box strong {
        color: #007bff;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Inizializza session state"""
    if 'openai_api_key' not in st.session_state:
        st.session_state.openai_api_key = None
    if 'analisi_risultati' not in st.session_state:
        st.session_state.analisi_risultati = None


def render_dashboard_header(risultati: dict):
    """Renderizza header dashboard con KPI principali"""
    req = risultati["requisiti_estratti"]
    
    importo = req.get("importo_lavori", 0)
    oggetto = req.get("oggetto_appalto", "N/D")
    stazione = req.get("stazione_appaltante", "N/D")
    
    st.markdown(f"""
    <div class="dashboard-header">
        <div class="dashboard-kpi">
            <p>OGGETTO APPALTO</p>
            <h1>{oggetto[:60]}{"..." if len(oggetto) > 60 else ""}</h1>
            <p style="font-size: 20px; margin-top: 15px;">
                <strong>Importo:</strong> {"€ {:,.0f}".format(importo) if importo else "Non specificato"} | 
                <strong>Ente:</strong> {stazione}
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_decisione_gigante(decisione: str, punteggio: int, motivi: list):
    """Renderizza box decisione GIGANTE con punteggio"""
    
    # Colore box basato su decisione
    if decisione == "PARTECIPARE":
        box_class = "verde"
        emoji = "✅"
        colore_score = "#28a745"
    elif decisione == "PARTECIPARE CON CAUTELA":
        box_class = "giallo"
        emoji = "⚠️"
        colore_score = "#ffc107"
    else:
        box_class = "rosso"
        emoji = "❌"
        colore_score = "#dc3545"
    
    st.markdown(f"""
    <div class="decisione-box {box_class}">
        <h1>{emoji} {decisione}</h1>
        <div class="score" style="color: {colore_score};">{punteggio}/100</div>
        <div class="score-label">PUNTEGGIO FATTIBILITÀ</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Progress bar visuale
    if punteggio >= 65:
        progress_class = "progress-verde"
    elif punteggio >= 40:
        progress_class = "progress-giallo"
    else:
        progress_class = "progress-rosso"
    
    st.markdown(f"""
    <div class="custom-progress">
        <div class="custom-progress-fill {progress_class}" style="width: {punteggio}%;">
            {punteggio}%
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Motivi del punteggio
    if motivi:
        st.markdown("### 📊 Dettaglio Calcolo Punteggio")
        for motivo in motivi:
            st.markdown(f'<div class="motivo-item">{motivo}</div>', unsafe_allow_html=True)


def render_killer_factors(soa_rossi: list, scadenze_critiche: list, cert_rossi: list):
    """Renderizza sezione KILLER FACTORS evidenziata"""
    
    has_killers = soa_rossi or scadenze_critiche or cert_rossi
    
    if not has_killers:
        return  # Nessun killer factor
    
    st.markdown("""
    <div class="killer-factors">
        <h3>🚨 FATTORI BLOCCANTI - Azione Immediata Richiesta</h3>
        <p>I seguenti requisiti CRITICI potrebbero impedire la partecipazione:</p>
    </div>
    """, unsafe_allow_html=True)
    
    # SOA mancanti
    if soa_rossi:
        for soa in soa_rossi:
            categoria = soa.get("categoria", "")
            classifica = soa.get("classifica", "")
            motivo = soa.get("motivo", "")
            suggerimento = soa.get("suggerimento", "")
            
            st.markdown(f"""
            <div class="killer-item">
                <strong>⛔ SOA {categoria} Classifica {classifica}</strong><br>
                {motivo}
                {"<br><br><strong>💡 Suggerimento:</strong> " + suggerimento if suggerimento else ""}
            </div>
            """, unsafe_allow_html=True)
    
    # Scadenze critiche
    if scadenze_critiche:
        for scad in scadenze_critiche:
            tipo = scad.get("tipo", "").upper()
            data = scad.get("data", "")
            giorni = scad.get("giorni_mancanti", 0)
            
            if giorni == 0:
                countdown_text = "SCADE OGGI"
            elif giorni == 1:
                countdown_text = "SCADE DOMANI"
            else:
                countdown_text = f"TRA {giorni} GIORNI"
            
            st.markdown(f"""
            <div class="killer-item">
                <strong>⏰ SCADENZA {tipo}: {data}</strong><br>
                <span style="font-size: 24px; color: #dc3545; font-weight: 700;">{countdown_text}</span>
            </div>
            """, unsafe_allow_html=True)
    
    # Certificazioni critiche
    if cert_rossi:
        for cert in cert_rossi:
            tipo = cert.get("tipo", "")
            motivo = cert.get("motivo", "")
            
            st.markdown(f"""
            <div class="killer-item">
                <strong>📜 CERTIFICAZIONE: {tipo}</strong><br>
                {motivo}
            </div>
            """, unsafe_allow_html=True)


def render_scadenze_countdown(scadenze: dict):
    """Renderizza scadenze con countdown visivo"""
    
    st.markdown("## 📅 Scadenze")
    
    # Critiche
    if scadenze["critiche"]:
        st.markdown("### 🔴 SCADENZE CRITICHE (≤ 2 giorni)")
        for scad in scadenze["critiche"]:
            tipo = scad.get("tipo", "").upper()
            data = scad.get("data", "")
            ora = scad.get("ora", "")
            giorni = scad.get("giorni_mancanti", 0)
            note = scad.get("note", "")
            
            if giorni == 0:
                countdown = "OGGI"
            elif giorni == 1:
                countdown = "DOMANI"
            else:
                countdown = f"{giorni} GIORNI"
            
            st.markdown(f"""
            <div class="scadenza-critica">
                <h3 style="margin: 0; color: white;">{tipo}</h3>
                <div class="countdown">{countdown}</div>
                <p style="margin: 5px 0; font-size: 18px;"><strong>{data} {ora if ora else ""}</strong></p>
                <p style="margin: 10px 0 0 0; opacity: 0.95;">{note}</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Prossime
    if scadenze["prossime"]:
        st.markdown("### 🟡 Prossime Scadenze (3-7 giorni)")
        for scad in scadenze["prossime"]:
            tipo = scad.get("tipo", "").upper()
            data = scad.get("data", "")
            giorni = scad.get("giorni_mancanti", 0)
            note = scad.get("note", "")
            
            st.markdown(f"""
            <div class="scadenza-attenzione">
                <strong>{tipo}</strong> - {data} (tra {giorni} giorni)<br>
                <small>{note}</small>
            </div>
            """, unsafe_allow_html=True)


def render_check_geografico(check_geo: dict):
    """Renderizza check geografico"""
    if check_geo.get("warning"):
        st.markdown(f"""
        <div class="suggerimento-box" style="background: #fff3cd; border-color: #ffc107;">
            <strong>🗺️ ATTENZIONE GEOGRAFICA:</strong> {check_geo['motivo']}
        </div>
        """, unsafe_allow_html=True)


def render_requisiti_box(titolo: str, verdi: list, gialli: list, rossi: list, tipo: str):
    """Renderizza box requisiti con semafori"""
    
    st.markdown(f"### {titolo}")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card verde">
            <div class="label">✅ POSSEDUTI</div>
            <div class="value">{len(verdi)}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card giallo">
            <div class="label">🟡 DA VERIFICARE</div>
            <div class="value">{len(gialli)}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card rosso">
            <div class="label">❌ MANCANTI</div>
            <div class="value">{len(rossi)}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Dettagli
    if verdi:
        with st.expander(f"✅ Vedi {len(verdi)} requisiti POSSEDUTI"):
            for item in verdi:
                if tipo == "soa":
                    st.markdown(f"""
                    <div class="status-box verde">
                        <h4>{item['categoria']} - Classifica {item['classifica']}</h4>
                        <p>{item['descrizione']}</p>
                        <p><small>✅ {item['motivo']}</small></p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    motivo = item.get("motivo", "")
                    st.markdown(f"""
                    <div class="status-box verde">
                        <h4>{item.get('tipo') or item.get('ruolo', 'N/D')}</h4>
                        <p><small>✅ {motivo}</small></p>
                    </div>
                    """, unsafe_allow_html=True)
    
    if gialli:
        with st.expander(f"🟡 Vedi {len(gialli)} requisiti DA VERIFICARE"):
            for item in gialli:
                motivo = item.get("motivo", "")
                suggerimento = item.get("suggerimento", "")
                
                st.markdown(f"""
                <div class="status-box giallo">
                    <h4>{item.get('tipo') or item.get('ruolo') or item.get('categoria', 'N/D')}</h4>
                    <p>🟡 {motivo}</p>
                    {"<p><strong>💡 Suggerimento:</strong> " + suggerimento + "</p>" if suggerimento else ""}
                </div>
                """, unsafe_allow_html=True)
    
    if rossi:
        with st.expander(f"❌ Vedi {len(rossi)} requisiti MANCANTI", expanded=True):
            for item in rossi:
                motivo = item.get("motivo", "")
                suggerimento = item.get("suggerimento", "")
                gap = item.get("gap", {})
                
                st.markdown(f"""
                <div class="status-box rosso">
                    <h4>{item.get('categoria') or item.get('tipo', 'N/D')}</h4>
                    <p>❌ {motivo}</p>
                    {"<p><strong>💡 Soluzione:</strong> " + suggerimento + "</p>" if suggerimento else ""}
                </div>
                """, unsafe_allow_html=True)


def tab_analisi():
    """Tab 1: Analisi Bando Go/No-Go - VERSIONE MIGLIORATA"""
    st.header("📊 Analisi Intelligente Bando")
    
    if not st.session_state.openai_api_key:
        st.warning("⚠️ Inserire OpenAI API Key nella sidebar per continuare")
        return
    
    # Upload PDF
    uploaded_file = st.file_uploader(
        "📄 Carica Disciplinare/Bando (PDF)",
        type=['pdf'],
        help="Carica il PDF del bando da analizzare (max 200 pagine)"
    )
    
    if uploaded_file:
        st.success(f"✅ File caricato: **{uploaded_file.name}**")
        
        # Bottone analisi GRANDE
        if st.button("🔍 ANALIZZA REQUISITI", type="primary", use_container_width=True):
            st.info("🤖 **Analisi in corso...** Il sistema sta leggendo il bando e confrontando con il tuo profilo aziendale (30-60 secondi)")
            
            # Salva temporaneamente
            temp_path = f"data/temp_{uploaded_file.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            try:
                # Parse PDF
                parser = BandoParser()
                bando_text = parser.parse_pdf(temp_path)
                st.session_state.bando_text = bando_text
                
                # Analizza con prompt migliorato
                from src.prompts import EXTRACTION_PROMPT
                
                analyzer = BandoAnalyzer(
                    openai_api_key=st.session_state.openai_api_key,
                    profilo_path="config/profilo_azienda.json"
                )
                
                risultati = analyzer.analyze_bando(bando_text, EXTRACTION_PROMPT)
                st.session_state.analisi_risultati = risultati
                
                st.success("✅ Analisi completata!")
                
            except Exception as e:
                error_text = str(e)
                if "insufficient_quota" in error_text or "exceeded your current quota" in error_text:
                    st.error("❌ Credito API esaurito: ricarica/abilita billing su OpenAI e riprova.")
                else:
                    st.error(f"❌ Errore durante l'analisi: {error_text}")
                st.exception(e)
                return
    
    # Mostra risultati se disponibili
    if st.session_state.analisi_risultati:
        risultati = st.session_state.analisi_risultati
        
        st.markdown("---")
        
        # 1. DASHBOARD HEADER
        render_dashboard_header(risultati)
        
        # 2. DECISIONE GIGANTE
        render_decisione_gigante(
            risultati["decisione"],
            risultati["punteggio_fattibilita"],
            risultati["motivi_punteggio"]
        )
        
        # 3. CHECK GEOGRAFICO
        render_check_geografico(risultati["check_geografico"])
        
        # 4. KILLER FACTORS
        render_killer_factors(
            risultati["soa"]["rossi"],
            risultati["scadenze"]["critiche"],
            risultati["certificazioni"]["rossi"]
        )
        
        st.markdown("---")
        
        # 5. SCADENZE COUNTDOWN
        render_scadenze_countdown(risultati["scadenze"])
        
        st.markdown("---")
        
        # 6. REQUISITI DETTAGLIATI
        render_requisiti_box(
            "📜 Requisiti SOA",
            risultati["soa"]["verdi"],
            risultati["soa"]["gialli"],
            risultati["soa"]["rossi"],
            "soa"
        )
        
        st.markdown("---")
        
        render_requisiti_box(
            "🏆 Certificazioni",
            risultati["certificazioni"]["verdi"],
            risultati["certificazioni"]["gialli"],
            risultati["certificazioni"]["rossi"],
            "cert"
        )
        
        st.markdown("---")
        
        render_requisiti_box(
            "👥 Figure Professionali",
            risultati["figure_professionali"]["verdi"],
            risultati["figure_professionali"]["gialli"],
            risultati["figure_professionali"]["rossi"],
            "figure"
        )


def sidebar():
    """Sidebar con configurazione"""
    st.sidebar.title("⚙️ Configurazione")
    
    # API Key
    api_key = st.sidebar.text_input(
        "OpenAI API Key",
        type="password",
        value=st.session_state.openai_api_key or "",
        help="Inserisci la tua API key di OpenAI"
    )
    
    if api_key:
        st.session_state.openai_api_key = api_key
        st.sidebar.success("✅ API Key configurata")
    else:
        st.sidebar.warning("⚠️ Inserire API Key")
    
    st.sidebar.markdown("---")
    
    # Info profilo aziendale
    st.sidebar.subheader("👤 Profilo Aziendale")
    try:
        with open("config/profilo_azienda.json", 'r', encoding='utf-8') as f:
            profilo = json.load(f)
        st.sidebar.info(f"**{profilo['nome_azienda']}**\n\n"
                       f"SOA: {len(profilo.get('soa_possedute', []))}\n\n"
                       f"Certificazioni: {len(profilo.get('certificazioni', []))}")
    except:
        st.sidebar.error("Profilo aziendale non trovato")


def main():
    """Applicazione principale"""
    init_session_state()
    
    # Header
    st.title("📋 BidPilot 2.0 - Analisi Intelligente")
    st.caption("Sistema AI per Analisi Avanzata di Bandi d'Appalto con Matching Puntuale")
    
    # Sidebar
    sidebar()
    
    # Tabs
    tab1, tab2 = st.tabs(["📊 Analisi Bando", "✍️ Genera Bozza (Prossimamente)"])
    
    with tab1:
        tab_analisi()
    
    with tab2:
        st.info("🚧 Modulo generazione bozze in arrivo...")
    
    # Footer
    st.markdown("---")
    st.caption("BidPilot 2.0 Professional | AI-Powered Tender Analysis")


if __name__ == "__main__":
    # Crea directory necessarie
    os.makedirs("data/progetti_storici", exist_ok=True)
    os.makedirs("config", exist_ok=True)
    
    main()