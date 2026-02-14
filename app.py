"""
BidPilot MVP - Applicazione Streamlit
Sistema AI per analisi bandi d'appalto e generazione bozze offerte tecniche
"""
import streamlit as st
import os
import json
from datetime import datetime

from src.parser import BandoParser
from src.analyzer import BandoAnalyzer
from src.rag_engine import RAGEngine


# Configurazione pagina
st.set_page_config(
    page_title="BidPilot 2.0 - MVP",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS custom per migliorare UI
st.markdown("""
<style>
    .big-font {
        font-size: 20px !important;
        font-weight: bold;
    }
    .status-verde {
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        padding: 10px;
        margin: 10px 0;
    }
    .status-giallo {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 10px;
        margin: 10px 0;
    }
    .status-rosso {
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
        padding: 10px;
        margin: 10px 0;
    }
    .metric-box {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Inizializza session state"""
    if 'openai_api_key' not in st.session_state:
        st.session_state.openai_api_key = None
    if 'bando_text' not in st.session_state:
        st.session_state.bando_text = None
    if 'analisi_risultati' not in st.session_state:
        st.session_state.analisi_risultati = None
    if 'rag_engine' not in st.session_state:
        st.session_state.rag_engine = None
    if 'progetti_ingested' not in st.session_state:
        st.session_state.progetti_ingested = False


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
        st.sidebar.warning("⚠️ Inserire API Key per utilizzare BidPilot")
    
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
    
    st.sidebar.markdown("---")
    
    # Gestione progetti storici
    st.sidebar.subheader("📚 Database Progetti")
    
    if st.session_state.rag_engine and st.session_state.progetti_ingested:
        stats = st.session_state.rag_engine.get_progetti_stats()
        if stats["status"] == "attivo":
            st.sidebar.success(f"✅ {stats['num_progetti']} progetti indicizzati")
            with st.sidebar.expander("Vedi progetti"):
                for prog in stats["progetti"]:
                    st.write(f"• {prog}")
        else:
            st.sidebar.warning("Database non inizializzato")
    else:
        st.sidebar.info("Database non ancora caricato")
    
    if st.sidebar.button("🔄 (Re)Indicizza Progetti Storici"):
        if not st.session_state.openai_api_key:
            st.sidebar.error("Inserire API Key prima!")
        else:
            with st.spinner("Indicizzazione in corso..."):
                try:
                    rag = RAGEngine(
                        openai_api_key=st.session_state.openai_api_key,
                        progetti_dir="data/progetti_storici"
                    )
                    rag.ingest_progetti(force_rebuild=True)
                    st.session_state.rag_engine = rag
                    st.session_state.progetti_ingested = True
                    st.sidebar.success("✅ Progetti indicizzati!")
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"Errore: {str(e)}")


def render_scadenza(scadenza: dict):
    """Renderizza una scadenza con il suo emoji"""
    emoji = scadenza.get("emoji", "📅")
    tipo = scadenza.get("tipo", "").upper()
    data = scadenza.get("data", "")
    ora = scadenza.get("ora", "")
    giorni = scadenza.get("giorni_mancanti", 0)
    obbligatorio = scadenza.get("obbligatorio", False)
    note = scadenza.get("note", "")
    
    obblig_badge = "🚨 OBBLIGATORIO" if obbligatorio else ""
    ora_str = f"ORE {ora}" if ora else ""
    
    if giorni is not None and giorni >= 0:
        giorni_str = f"(tra {giorni} giorni)" if giorni > 0 else "(OGGI)"
    else:
        giorni_str = ""
    
    st.markdown(f"**{emoji} {data} {ora_str} {giorni_str}** → **{tipo}** {obblig_badge}")
    if note:
        st.caption(f"ℹ️ {note}")


def tab_analisi():
    """Tab 1: Analisi Bando Go/No-Go"""
    st.header("📊 Analisi Bando Go/No-Go")
    
    if not st.session_state.openai_api_key:
        st.warning("⚠️ Inserire OpenAI API Key nella sidebar per continuare")
        return
    
    # Upload PDF
    uploaded_file = st.file_uploader(
        "📄 Carica Disciplinare/Bando (PDF)",
        type=['pdf'],
        help="Carica il PDF del bando da analizzare"
    )
    
    if uploaded_file:
        # Salva temporaneamente
        temp_path = f"data/temp_{uploaded_file.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        st.success(f"✅ File caricato: {uploaded_file.name}")
        
        # Bottone analisi
        if st.button("🔍 Analizza Requisiti", type="primary", use_container_width=True):
            with st.spinner("🤖 Analisi in corso... (può richiedere 30-60 secondi)"):
                try:
                    # Parse PDF
                    parser = BandoParser()
                    bando_text = parser.parse_pdf(temp_path)
                    st.session_state.bando_text = bando_text
                    
                    # Analizza
                    analyzer = BandoAnalyzer(
                        openai_api_key=st.session_state.openai_api_key,
                        profilo_path="config/profilo_azienda.json"
                    )
                    
                    risultati = analyzer.analyze_bando(bando_text)
                    st.session_state.analisi_risultati = risultati
                    
                    st.success("✅ Analisi completata!")
                    
                except Exception as e:
                    st.error(f"❌ Errore durante l'analisi: {str(e)}")
                    st.exception(e)
    
    # Mostra risultati se disponibili
    if st.session_state.analisi_risultati:
        st.markdown("---")
        risultati = st.session_state.analisi_risultati
        req = risultati["requisiti_estratti"]
        
        # Header con info bando
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Oggetto", req.get("oggetto_appalto", "N/D")[:30] + "...")
        with col2:
            importo = req.get("importo_lavori", 0)
            st.metric("Importo", f"€ {importo:,.0f}" if importo else "N/D")
        with col3:
            st.metric("Stazione Appaltante", req.get("stazione_appaltante", "N/D"))
        
        # DECISIONE FINALE
        st.markdown("---")
        decisione = risultati["decisione"]
        punteggio = risultati["punteggio_fattibilita"]
        
        if decisione == "PARTECIPARE":
            st.success(f"## ✅ DECISIONE: {decisione}")
            st.progress(punteggio / 100)
            st.write(f"**Punteggio Fattibilità: {punteggio}/100**")
        elif decisione == "PARTECIPARE CON CAUTELA":
            st.warning(f"## 🟡 DECISIONE: {decisione}")
            st.progress(punteggio / 100)
            st.write(f"**Punteggio Fattibilità: {punteggio}/100**")
        else:
            st.error(f"## ❌ DECISIONE: {decisione}")
            st.progress(punteggio / 100)
            st.write(f"**Punteggio Fattibilità: {punteggio}/100**")
        
        # SCADENZE CRITICHE
        st.markdown("---")
        st.subheader("🔴 SCADENZE CRITICHE - Azione Immediata")
        
        if risultati["scadenze"]["critiche"]:
            for scad in risultati["scadenze"]["critiche"]:
                render_scadenza(scad)
        else:
            st.info("✅ Nessuna scadenza critica nei prossimi 2 giorni")
        
        # PROSSIME SCADENZE
        if risultati["scadenze"]["prossime"]:
            st.markdown("---")
            st.subheader("🟡 Prossime Scadenze (3-7 giorni)")
            for scad in risultati["scadenze"]["prossime"]:
                render_scadenza(scad)
        
        # REQUISITI SOA
        st.markdown("---")
        st.subheader("📜 Requisiti SOA")
        
        tab_verdi, tab_rossi = st.tabs(["✅ Posseduti", "❌ Mancanti"])
        
        with tab_verdi:
            if risultati["soa"]["verdi"]:
                for soa in risultati["soa"]["verdi"]:
                    st.markdown(f"""
                    <div class="status-verde">
                        <strong>{soa['categoria']} - Classifica {soa['classifica']}</strong><br>
                        {soa['descrizione']}<br>
                        <small>✅ {soa['motivo']}</small>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Nessuna SOA richiesta o tutte mancanti")
        
        with tab_rossi:
            if risultati["soa"]["rossi"]:
                for soa in risultati["soa"]["rossi"]:
                    st.markdown(f"""
                    <div class="status-rosso">
                        <strong>{soa['categoria']} - Classifica {soa['classifica']}</strong><br>
                        {soa['descrizione']}<br>
                        <small>❌ {soa['motivo']}</small>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.success("✅ Tutte le SOA richieste sono possedute!")
        
        # CERTIFICAZIONI
        st.markdown("---")
        st.subheader("🏆 Certificazioni")
        
        cert_tabs = st.tabs(["✅ Possedute", "🟡 Da Verificare"])
        
        with cert_tabs[0]:
            if risultati["certificazioni"]["verdi"]:
                for cert in risultati["certificazioni"]["verdi"]:
                    st.markdown(f"""
                    <div class="status-verde">
                        <strong>{cert['tipo']}</strong><br>
                        <small>✅ {cert['motivo']}</small>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Nessuna certificazione verde")
        
        with cert_tabs[1]:
            if risultati["certificazioni"]["gialli"]:
                for cert in risultati["certificazioni"]["gialli"]:
                    st.markdown(f"""
                    <div class="status-giallo">
                        <strong>{cert['tipo']}</strong><br>
                        <small>🟡 {cert['motivo']}</small>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.success("Nessuna certificazione da verificare")
        
        # FIGURE PROFESSIONALI
        if risultati["figure_professionali"]["verdi"] or risultati["figure_professionali"]["gialli"]:
            st.markdown("---")
            st.subheader("👥 Figure Professionali")
            
            fig_tabs = st.tabs(["✅ Disponibili", "🟡 Da Contattare"])
            
            with fig_tabs[0]:
                if risultati["figure_professionali"]["verdi"]:
                    for fig in risultati["figure_professionali"]["verdi"]:
                        st.markdown(f"""
                        <div class="status-verde">
                            <strong>{fig['ruolo']}</strong><br>
                            <small>✅ {fig['motivo']}</small>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("Nessuna figura interna disponibile")
            
            with fig_tabs[1]:
                if risultati["figure_professionali"]["gialli"]:
                    for fig in risultati["figure_professionali"]["gialli"]:
                        st.markdown(f"""
                        <div class="status-giallo">
                            <strong>{fig['ruolo']}</strong><br>
                            <small>💡 {fig['motivo']}</small>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.success("Nessuna figura esterna necessaria")
        
        # Riepilogo numerico
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("✅ Requisiti Verdi", risultati["num_requisiti"]["verdi"])
        with col2:
            st.metric("🟡 Requisiti Gialli", risultati["num_requisiti"]["gialli"])
        with col3:
            st.metric("❌ Requisiti Rossi", risultati["num_requisiti"]["rossi"])


def tab_bozza():
    """Tab 2: Generazione Bozza Offerta Tecnica"""
    st.header("✍️ Generazione Bozza Offerta Tecnica")
    
    if not st.session_state.openai_api_key:
        st.warning("⚠️ Inserire OpenAI API Key nella sidebar per continuare")
        return
    
    # Verifica che analisi sia stata fatta
    if not st.session_state.analisi_risultati:
        st.info("ℹ️ Eseguire prima l'analisi del bando nella tab 'Analisi Bando'")
        return
    
    # Verifica che progetti siano stati indicizzati
    if not st.session_state.progetti_ingested or not st.session_state.rag_engine:
        st.warning("⚠️ Indicizzare prima i progetti storici dalla sidebar (bottone 'Indicizza Progetti')")
        
        # Mostra istruzioni
        st.info("""
        **Come preparare i progetti storici:**
        1. Inserire PDF di progetti/gare vinte nella cartella `data/progetti_storici/`
        2. Cliccare il bottone nella sidebar per indicizzarli
        3. Il sistema creerà automaticamente il database vettoriale
        """)
        return
    
    # Estrai criteri dal risultato analisi
    criteri = st.session_state.analisi_risultati["requisiti_estratti"].get("criteri_valutazione", [])
    
    if not criteri:
        st.warning("⚠️ Nessun criterio di valutazione trovato nel bando analizzato")
        return
    
    # Selezione criterio
    st.subheader("1️⃣ Seleziona Criterio")
    
    criterio_options = []
    for crit in criteri:
        label = f"{crit.get('codice', '?')} - {crit.get('descrizione', 'N/D')} ({crit.get('punteggio_max', 0)} punti)"
        criterio_options.append(label)
    
    selected_idx = st.selectbox(
        "Scegli il criterio per cui generare la bozza:",
        range(len(criterio_options)),
        format_func=lambda x: criterio_options[x]
    )
    
    criterio_selezionato = criteri[selected_idx]
    
    # Mostra dettagli criterio
    with st.expander("📋 Dettagli Criterio"):
        st.write(f"**Codice:** {criterio_selezionato.get('codice', 'N/D')}")
        st.write(f"**Descrizione:** {criterio_selezionato.get('descrizione', 'N/D')}")
        st.write(f"**Punteggio Max:** {criterio_selezionato.get('punteggio_max', 0)} punti")
        if criterio_selezionato.get('sub_criteri'):
            st.write("**Sub-criteri:**")
            for sub in criterio_selezionato['sub_criteri']:
                st.write(f"  • {sub}")
    
    st.markdown("---")
    st.subheader("2️⃣ Genera Bozza")
    
    # Bottone generazione
    if st.button("🤖 Genera Bozza con AI", type="primary", use_container_width=True):
        with st.spinner("🔮 Ricerca progetti rilevanti e generazione bozza in corso..."):
            try:
                # Ricerca progetti rilevanti
                query = criterio_selezionato.get("descrizione", "")
                progetti_context = st.session_state.rag_engine.search_relevant_content(query, k=5)
                
                # Mostra progetti trovati
                st.success(f"✅ Trovati {len(progetti_context)} chunk rilevanti da progetti storici")
                
                with st.expander("📚 Progetti Rilevanti Trovati"):
                    progetti_unici = list(set([p["progetto"] for p in progetti_context]))
                    for prog in progetti_unici:
                        st.write(f"• **{prog}**")
                
                # Genera bozza
                bozza = st.session_state.rag_engine.generate_draft(
                    criterio=criterio_selezionato,
                    progetti_context=progetti_context
                )
                
                # Mostra bozza
                st.markdown("---")
                st.subheader("📄 Bozza Generata")
                
                st.markdown(f"""
                <div class="metric-box">
                    <strong>Criterio:</strong> {criterio_selezionato.get('codice', '')} - {criterio_selezionato.get('descrizione', '')}<br>
                    <strong>Punteggio Max:</strong> {criterio_selezionato.get('punteggio_max', 0)} punti
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("### 💡 Testo Bozza")
                st.text_area(
                    "Bozza (copia e modifica):",
                    value=bozza,
                    height=400,
                    key="bozza_output"
                )
                
                # Bottoni azioni
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        "📥 Download Bozza (.txt)",
                        data=bozza,
                        file_name=f"bozza_criterio_{criterio_selezionato.get('codice', 'X')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                with col2:
                    if st.button("📋 Copia in Clipboard", use_container_width=True):
                        st.write("💡 Usa Ctrl+A e Ctrl+C per copiare il testo sopra")
                
                # Note tecniche
                st.warning("""
                ⚠️ **NOTE IMPORTANTI:**
                - Questa è una BOZZA generata automaticamente
                - Verificare SEMPRE la correttezza tecnica con un esperto
                - Adattare il testo al contesto specifico del bando
                - Controllare riferimenti normativi e percentuali
                """)
                
            except Exception as e:
                st.error(f"❌ Errore durante la generazione: {str(e)}")
                st.exception(e)


def main():
    """Applicazione principale"""
    init_session_state()
    
    # Header
    st.title("📋 BidPilot 2.0 - MVP")
    st.caption("Sistema AI per Analisi Bandi d'Appalto e Generazione Bozze Offerte Tecniche")
    
    # Sidebar
    sidebar()
    
    # Tabs principali
    tab1, tab2 = st.tabs(["📊 Analisi Bando", "✍️ Genera Bozza"])
    
    with tab1:
        tab_analisi()
    
    with tab2:
        tab_bozza()
    
    # Footer
    st.markdown("---")
    st.caption("BidPilot 2.0 MVP | Developed with Streamlit & LangChain")


if __name__ == "__main__":
    # Crea directory necessarie
    os.makedirs("data/progetti_storici", exist_ok=True)
    os.makedirs("data/chroma_db", exist_ok=True)
    os.makedirs("config", exist_ok=True)
    
    main()
