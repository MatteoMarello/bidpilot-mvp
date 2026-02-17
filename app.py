"""BidPilot MVP - App Streamlit Pulita"""
import streamlit as st
import os
import json
from datetime import datetime

from src.parser import BandoParser
from src.analyzer import BandoAnalyzer


st.set_page_config(
    page_title="BidPilot 2.0",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Pulito e Ottimizzato
st.markdown("""
<style>
    * { font-family: 'Inter', -apple-system, sans-serif; }
    
    .header-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    
    .decisione-box {
        padding: 3rem;
        border-radius: 20px;
        text-align: center;
        box-shadow: 0 15px 40px rgba(0,0,0,0.15);
        border: 4px solid;
        margin: 2rem 0;
    }
    
    .decisione-box.verde { background: linear-gradient(135deg, #d4edda, #c3e6cb); border-color: #28a745; }
    .decisione-box.giallo { background: linear-gradient(135deg, #fff3cd, #ffeaa7); border-color: #ffc107; }
    .decisione-box.rosso { background: linear-gradient(135deg, #f8d7da, #f5c6cb); border-color: #dc3545; }
    
    .decisione-box h1 { font-size: 3.5rem; margin: 0; }
    .decisione-box .score { font-size: 4.5rem; font-weight: 700; margin: 1rem 0; }
    
    .killer-box {
        background: #fff3cd;
        border-left: 8px solid #ff6b6b;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .scadenza-critica {
        background: linear-gradient(135deg, #ff6b6b, #ee5a6f);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.02); } }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        text-align: center;
        border-top: 4px solid;
    }
    
    .metric-card.verde { border-color: #28a745; }
    .metric-card.giallo { border-color: #ffc107; }
    .metric-card.rosso { border-color: #dc3545; }
    .metric-card .value { font-size: 2.5rem; font-weight: 700; }
    
    .status-box {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid;
    }
    
    .status-box.verde { background: #d4edda; border-color: #28a745; }
    .status-box.giallo { background: #fff3cd; border-color: #ffc107; }
    .status-box.rosso { background: #f8d7da; border-color: #dc3545; }
    
    .evidence { background: #f8f9fa; padding: 0.5rem; margin: 0.5rem 0; font-size: 0.85rem; font-style: italic; }
</style>
""", unsafe_allow_html=True)


def init_session():
    """Inizializza session state"""
    if 'api_key' not in st.session_state:
        st.session_state.api_key = None
    if 'risultati' not in st.session_state:
        st.session_state.risultati = None


def render_header(ris: dict):
    """Renderizza header dashboard"""
    req = ris["requisiti_estratti"]
    importo = req.get("importo_lavori")
    oggetto = req.get("oggetto_appalto", "N/D")
    ente = req.get("stazione_appaltante", "N/D")
    
    st.markdown(f"""
    <div class="header-box">
        <h1>{oggetto[:80]}{"..." if len(oggetto) > 80 else ""}</h1>
        <p style="font-size:1.2rem; margin-top:1rem;">
            <strong>Importo:</strong> {"€{:,.0f}".format(importo) if importo else "Non specificato"} | 
            <strong>Ente:</strong> {ente}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    if req.get("importo_evidence"):
        st.markdown(f'<div class="evidence">📝 Evidence: "{req["importo_evidence"]}"</div>', unsafe_allow_html=True)


def render_decisione(dec: str, score: int, motivi: list):
    """Renderizza decisione finale"""
    css_class = {"PARTECIPARE": "verde", "PARTECIPARE CON CAUTELA": "giallo", "NON PARTECIPARE": "rosso"}
    emoji = {"PARTECIPARE": "✅", "PARTECIPARE CON CAUTELA": "⚠️", "NON PARTECIPARE": "❌"}
    
    st.markdown(f"""
    <div class="decisione-box {css_class.get(dec, 'giallo')}">
        <h1>{emoji.get(dec, '⚠️')} {dec}</h1>
        <div class="score">{score}/100</div>
        <div>PUNTEGGIO FATTIBILITÀ</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.progress(score / 100)
    
    if motivi:
        st.markdown("### 📊 Dettaglio Calcolo")
        for m in motivi:
            st.markdown(f'<div class="status-box giallo">{m}</div>', unsafe_allow_html=True)


def render_killers(soa_r: list, scad_c: list, cert_r: list):
    """Renderizza fattori bloccanti"""
    if not (soa_r or scad_c or cert_r):
        return
    
    st.markdown('<div class="killer-box"><h3>🚨 FATTORI BLOCCANTI</h3></div>', unsafe_allow_html=True)
    
    for s in soa_r:
        st.error(f"⛔ SOA {s['categoria']} {s['classifica']}: {s['motivo']}")
        if s.get('suggerimento'):
            st.info(f"💡 {s['suggerimento']}")
    
    for sc in scad_c:
        st.markdown(f"""
        <div class="scadenza-critica">
            <h3>{sc['tipo'].upper()}</h3>
            <div style="font-size:2rem;">{sc.get('giorni_mancanti', 0)} GIORNI</div>
            <p>{sc['data']}</p>
        </div>
        """, unsafe_allow_html=True)


def render_requisiti(titolo: str, verdi: list, gialli: list, rossi: list):
    """Renderizza box requisiti"""
    st.markdown(f"### {titolo}")
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown(f"""
        <div class="metric-card verde">
            <div class="label">✅ POSSEDUTI</div>
            <div class="value">{len(verdi)}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with c2:
        st.markdown(f"""
        <div class="metric-card giallo">
            <div class="label">🟡 DA VERIFICARE</div>
            <div class="value">{len(gialli)}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with c3:
        st.markdown(f"""
        <div class="metric-card rosso">
            <div class="label">❌ MANCANTI</div>
            <div class="value">{len(rossi)}</div>
        </div>
        """, unsafe_allow_html=True)
    
    if verdi:
        with st.expander(f"✅ {len(verdi)} posseduti"):
            for v in verdi:
                st.markdown(f'<div class="status-box verde">{v.get("categoria") or v.get("tipo") or v.get("ruolo")}: {v["motivo"]}</div>', unsafe_allow_html=True)
    
    if gialli:
        with st.expander(f"🟡 {len(gialli)} da verificare"):
            for g in gialli:
                st.markdown(f'<div class="status-box giallo">{g.get("tipo") or g.get("ruolo")}: {g["motivo"]}</div>', unsafe_allow_html=True)
    
    if rossi:
        with st.expander(f"❌ {len(rossi)} mancanti", expanded=True):
            for r in rossi:
                st.markdown(f'<div class="status-box rosso">{r.get("categoria") or r.get("tipo")}: {r["motivo"]}</div>', unsafe_allow_html=True)


def tab_analisi():
    """Tab analisi bando"""
    st.header("📊 Analisi Intelligente Bando")
    
    if not st.session_state.api_key:
        st.warning("⚠️ Inserire API Key nella sidebar")
        return
    
    uploaded = st.file_uploader("📄 Carica PDF Bando", type=['pdf'])
    
    if uploaded:
        st.success(f"✅ File: {uploaded.name}")
        
        if st.button("🔍 ANALIZZA", type="primary", use_container_width=True):
            with st.spinner("🤖 Analisi in corso..."):
                temp = f"data/temp_{uploaded.name}"
                with open(temp, "wb") as f:
                    f.write(uploaded.getbuffer())
                
                try:
                    parser = BandoParser()
                    text = parser.parse_pdf(temp, mode="full")
                    
                    analyzer = BandoAnalyzer(
                        openai_api_key=st.session_state.api_key,
                        profilo_path="config/profilo_azienda.json"
                    )
                    
                    ris = analyzer.analyze_bando(text)
                    st.session_state.risultati = ris
                    st.success("✅ Analisi completata!")
                    
                except Exception as e:
                    if "INCOERENZA" in str(e):
                        st.error(f"❌ {e}")
                    else:
                        st.error(f"❌ Errore: {e}")
                    st.exception(e)
                    return
    
    # Mostra risultati
    if ris := st.session_state.risultati:
        st.markdown("---")
        render_header(ris)
        render_decisione(ris["decisione"], ris["punteggio_fattibilita"], ris["motivi_punteggio"])
        
        if ris["check_geografico"].get("warning"):
            st.warning(f"🗺️ {ris['check_geografico']['motivo']}")
        
        render_killers(ris["soa"]["rossi"], ris["scadenze"]["critiche"], ris["certificazioni"]["rossi"])
        
        st.markdown("---")
        st.markdown("## 📅 Scadenze")
        
        # Scadenze critiche (≤2 giorni)
        for s in ris["scadenze"]["critiche"]:
            st.markdown(f'<div class="scadenza-critica"><strong>{s["tipo"]}</strong>: {s["data"]} (tra {s["giorni_mancanti"]} giorni)</div>', unsafe_allow_html=True)
        
        # Scadenze già passate — informative, non bloccanti
        if ris["scadenze"].get("scadute"):
            st.info(f"ℹ️ **Bando con scadenze già passate** — Questo bando è probabilmente concluso. Le scadenze non influenzano il punteggio tecnico.")
            with st.expander(f"📋 Vedi {len(ris['scadenze']['scadute'])} scadenze già passate"):
                for s in ris["scadenze"]["scadute"]:
                    st.markdown(f"- **{s['tipo']}**: {s['data']} ({abs(s['giorni_mancanti'])} giorni fa)")
        
        st.markdown("---")
        render_requisiti("📜 SOA", ris["soa"]["verdi"], ris["soa"]["gialli"], ris["soa"]["rossi"])
        st.markdown("---")
        render_requisiti("🏆 Certificazioni", ris["certificazioni"]["verdi"], ris["certificazioni"]["gialli"], ris["certificazioni"]["rossi"])
        st.markdown("---")
        render_requisiti("👥 Figure", ris["figure_professionali"]["verdi"], ris["figure_professionali"]["gialli"], ris["figure_professionali"]["rossi"])


def sidebar():
    """Sidebar configurazione"""
    st.sidebar.title("⚙️ Config")
    
    key = st.sidebar.text_input("OpenAI API Key", type="password", value=st.session_state.api_key or "")
    
    if key:
        st.session_state.api_key = key
        st.sidebar.success("✅ Key configurata")
    else:
        st.sidebar.warning("⚠️ Inserire key")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("👤 Profilo")
    
    try:
        with open("config/profilo_azienda.json") as f:
            prof = json.load(f)
        st.sidebar.info(f"**{prof['nome_azienda']}**\n\nSOA: {len(prof.get('soa_possedute', []))}")
    except:
        st.sidebar.error("Profilo non trovato")


def main():
    """Main app"""
    init_session()
    
    st.title("📋 BidPilot 2.0")
    st.caption("Analisi AI Bandi d'Appalto • Anti-Allucinazione")
    
    sidebar()
    
    tab1, tab2 = st.tabs(["📊 Analisi", "✍️ Bozze (WIP)"])
    
    with tab1:
        tab_analisi()
    
    with tab2:
        st.info("🚧 Modulo generazione bozze in sviluppo")
    
    st.markdown("---")
    st.caption("BidPilot 2.0 • Powered by GPT-4o + Pydantic")


if __name__ == "__main__":
    os.makedirs("data/progetti_storici", exist_ok=True)
    os.makedirs("config", exist_ok=True)
    main()