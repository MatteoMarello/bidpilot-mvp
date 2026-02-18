"""
BidPilot v3.0 — Decision Engine UI
4 stati: NO_GO / GO_WITH_STRUCTURE / GO_HIGH_RISK / GO
"""
import streamlit as st
import os
import json
from datetime import datetime

from src.parser import BandoParser
from src.analyzer import BandoAnalyzer
from src.schemas import DecisionReport, VerdictStatus, ReqStatus, Severity

st.set_page_config(
    page_title="BidPilot 3.0 — Decision Engine",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
  * { font-family: 'Inter', -apple-system, sans-serif; }

  .verdict-box {
    padding: 2.5rem; border-radius: 20px; text-align: center;
    border: 4px solid; margin: 1.5rem 0;
    box-shadow: 0 10px 30px rgba(0,0,0,0.12);
  }
  .verdict-box h1 { font-size: 2.8rem; margin: 0 0 0.5rem 0; }
  .verdict-box .sub { font-size: 1.1rem; opacity: 0.85; }

  .v-go        { background: linear-gradient(135deg,#d4edda,#c3e6cb); border-color:#28a745; }
  .v-highrisk  { background: linear-gradient(135deg,#fff3cd,#ffe69c); border-color:#ffc107; }
  .v-structure { background: linear-gradient(135deg,#cce5ff,#b8daff); border-color:#0d6efd; }
  .v-nogo      { background: linear-gradient(135deg,#f8d7da,#f5c6cb); border-color:#dc3545; }

  .req-card {
    padding: 0.9rem 1.1rem; border-radius: 10px; margin: 0.4rem 0;
    border-left: 5px solid;
  }
  .req-ok       { background:#d4edda; border-color:#28a745; }
  .req-fixable  { background:#cce5ff; border-color:#0d6efd; }
  .req-ko       { background:#f8d7da; border-color:#dc3545; }
  .req-unknown  { background:#fff3cd; border-color:#ffc107; }

  .risk-HIGH   { background:#f8d7da; border-left:5px solid #dc3545; padding:0.8rem; border-radius:8px; margin:0.4rem 0; }
  .risk-MEDIUM { background:#fff3cd; border-left:5px solid #ffc107; padding:0.8rem; border-radius:8px; margin:0.4rem 0; }
  .risk-LOW    { background:#d4edda; border-left:5px solid #28a745;  padding:0.8rem; border-radius:8px; margin:0.4rem 0; }

  .action-step {
    background:white; border:1px solid #dee2e6;
    border-radius:12px; padding:1.2rem; margin:0.6rem 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  }
  .step-num {
    background:#0d6efd; color:white; border-radius:50%;
    width:32px; height:32px; display:inline-flex;
    align-items:center; justify-content:center; font-weight:700;
    margin-right:0.6rem;
  }
  .evidence-quote {
    background:#f8f9fa; border-left:3px solid #6c757d;
    padding:0.4rem 0.7rem; font-size:0.83rem;
    font-style:italic; border-radius:4px; margin-top:0.3rem;
  }
  .checklist-item {
    display:flex; align-items:flex-start; gap:0.5rem;
    padding:0.5rem 0; border-bottom:1px solid #f0f0f0;
  }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
# Helpers UI
# ══════════════════════════════════════════════════════════

VERDICT_CONFIG = {
    VerdictStatus.GO: {
        "css": "v-go", "emoji": "✅", "label": "PARTECIPA",
        "desc": "Tutti i requisiti verificati. Nessun blocco rilevato."
    },
    VerdictStatus.GO_HIGH_RISK: {
        "css": "v-highrisk", "emoji": "⚠️", "label": "PARTECIPA CON ATTENZIONE",
        "desc": "Ammissibile ma con rischi operativi/documentali da gestire."
    },
    VerdictStatus.GO_WITH_STRUCTURE: {
        "css": "v-structure", "emoji": "🔵", "label": "AMMISSIBILE SOLO CON STRUTTURA",
        "desc": "Possibile con RTI / avvalimento / progettisti: vedi Piano d'Azione."
    },
    VerdictStatus.NO_GO: {
        "css": "v-nogo", "emoji": "🚫", "label": "NON PARTECIPARE",
        "desc": "Requisiti bloccanti non colmabili con le strutture ammesse."
    },
    VerdictStatus.ELIGIBLE_QUALIFICATION: {
        "css": "v-go", "emoji": "✅", "label": "ELIGIBLE — QUALIFICAZIONE",
        "desc": "Requisiti di qualificazione soddisfatti."
    },
    VerdictStatus.NOT_ELIGIBLE_QUALIFICATION: {
        "css": "v-nogo", "emoji": "🚫", "label": "NON ELIGIBLE — QUALIFICAZIONE",
        "desc": "Requisiti di qualificazione non soddisfatti."
    },
    VerdictStatus.ELIGIBLE_STAGE1: {
        "css": "v-highrisk", "emoji": "⚠️", "label": "ELIGIBLE STAGE 1 — PPP",
        "desc": "Ammissione stage 1. Valutare fasi successive."
    },
}

STATUS_CSS = {
    ReqStatus.OK: "req-ok",
    ReqStatus.FIXABLE: "req-fixable",
    ReqStatus.KO: "req-ko",
    ReqStatus.UNKNOWN: "req-unknown",
    ReqStatus.RISK_FLAG: "req-unknown",
    ReqStatus.PREMIANTE: "req-ok",
}
STATUS_ICON = {
    ReqStatus.OK: "✅",
    ReqStatus.FIXABLE: "🔧",
    ReqStatus.KO: "❌",
    ReqStatus.UNKNOWN: "❓",
    ReqStatus.RISK_FLAG: "⚡",
    ReqStatus.PREMIANTE: "🏆",
}


def render_verdict(report: DecisionReport):
    cfg = VERDICT_CONFIG.get(report.verdict.status, VERDICT_CONFIG[VerdictStatus.GO_HIGH_RISK])
    summary = report.verdict.summary or cfg["desc"]
    st.markdown(f"""
    <div class="verdict-box {cfg['css']}">
      <h1>{cfg['emoji']} {cfg['label']}</h1>
      <div class="sub">{summary}</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    leg = report.verdict.legal_eligibility
    op = report.verdict.operational_feasibility
    conf = report.verdict.profile_confidence

    leg_icon = "✅" if leg == "eligible" else ("❌" if leg == "not_eligible" else "❓")
    op_icon  = "✅" if op == "feasible" else ("❌" if op == "not_feasible" else "⚠️")
    conf_label = "COMPLETA" if conf == 1.0 else ("PROVVISORIA" if conf >= 0.7 else "INAFFIDABILE")
    conf_icon = "🟢" if conf == 1.0 else ("🟡" if conf >= 0.7 else "🔴")

    c1.metric("Ammissibilità legale", f"{leg_icon} {leg.replace('_', ' ').title()}")
    c2.metric("Fattibilità operativa", f"{op_icon} {op.replace('_', ' ').title()}")
    c3.metric("Confidence profilo", f"{conf_icon} {conf:.1f} — {conf_label}")

    # PPP stage outputs
    if report.verdict.stage_outputs:
        st.info("**Output per fase (PPP)**")
        for k, v in report.verdict.stage_outputs.items():
            st.markdown(f"- **{k}**: {v}")


def render_top_reasons(report: DecisionReport):
    if not report.top_reasons:
        return
    st.markdown("### 🎯 Ragioni principali")
    for r in report.top_reasons:
        icon = "❌" if r.severity == Severity.HARD_KO else "⚠️"
        css = "req-ko" if (r.severity == Severity.HARD_KO and not r.can_be_fixed) \
              else "req-fixable" if r.can_be_fixed else "req-unknown"
        fix_text = f" → **Risolvibile con:** {', '.join(r.fix_options)}" if r.can_be_fixed else ""
        ev_html = ""
        if r.evidence and r.evidence.quote:
            ev_html = f'<div class="evidence-quote">📎 "{r.evidence.quote[:200]}"</div>'
        st.markdown(f"""
        <div class="req-card {css}">
          <strong>{icon} [{r.issue_type}]</strong> {r.message}{fix_text}
          {ev_html}
        </div>
        """, unsafe_allow_html=True)


def render_requirements(report: DecisionReport):
    results = report.requirements_results
    if not results:
        st.info("Nessun requisito valutato.")
        return
    st.markdown("### 📋 Analisi Requisiti")

    cats = {
        "qualification": "🏗️ SOA",
        "certification": "🏆 Certificazioni",
        "procedural": "🔒 Procedurali",
        "design": "📐 Progettazione",
        "financial": "💶 Finanziari",
        "operational": "⏱️ Operativi",
        "general": "📜 Generali",
        "guarantee": "🛡️ Garanzie",
        "participation": "🤝 Partecipazione",
        "professional": "👤 Idoneità professionale",
        "meta": "ℹ️ Classificazione",
    }

    by_cat = {}
    for r in results:
        by_cat.setdefault(r.category, []).append(r)

    # Sommario
    ko_c   = sum(1 for r in results if r.status == ReqStatus.KO)
    fix_c  = sum(1 for r in results if r.status == ReqStatus.FIXABLE)
    ok_c   = sum(1 for r in results if r.status == ReqStatus.OK)
    unk_c  = sum(1 for r in results if r.status == ReqStatus.UNKNOWN)
    risk_c = sum(1 for r in results if r.status == ReqStatus.RISK_FLAG)
    prem_c = sum(1 for r in results if r.status == ReqStatus.PREMIANTE)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("✅ OK", ok_c)
    c2.metric("🔧 Colmabili", fix_c)
    c3.metric("❌ Bloccanti", ko_c)
    c4.metric("❓ Da verificare", unk_c)
    c5.metric("⚡ Risk flag", risk_c)
    c6.metric("🏆 Premianti", prem_c)

    st.markdown("---")

    # Mostra prima le categorie più critiche
    priority_cats = ["qualification", "procedural", "general", "certification",
                     "financial", "design", "guarantee", "participation",
                     "professional", "operational", "meta"]
    all_cats = priority_cats + [c for c in by_cat if c not in priority_cats]

    for cat_key in all_cats:
        reqs = by_cat.get(cat_key, [])
        if not reqs:
            continue
        cat_label = cats.get(cat_key, f"📁 {cat_key.title()}")
        has_ko = any(r.status in (ReqStatus.KO, ReqStatus.FIXABLE) and r.severity == Severity.HARD_KO
                     for r in reqs)
        expanded = cat_key in ("qualification", "procedural") or has_ko

        with st.expander(f"{cat_label} ({len(reqs)} requisiti)", expanded=expanded):
            for r in reqs:
                css = STATUS_CSS.get(r.status, "req-unknown")
                icon = STATUS_ICON.get(r.status, "❓")
                sev_badge = ("🔴" if r.severity == Severity.HARD_KO
                             else "🟡" if r.severity == Severity.SOFT_RISK else "🟢")

                # Evidence (primo elemento se presente)
                ev_html = ""
                if r.evidence:
                    ev = r.evidence[0]
                    if ev.quote:
                        page_str = f" (p.{ev.page})" if ev.page else ""
                        ev_html = f'<div class="evidence-quote">📎 "{ev.quote[:200]}"{page_str}</div>'

                # Fixability
                fix_html = ""
                if r.fixability.is_fixable and r.fixability.allowed_methods:
                    fix_html = f"<br><small>🔧 Risolvibile con: <strong>{', '.join(r.fixability.allowed_methods)}</strong></small>"
                    if r.fixability.constraints:
                        fix_html += f"<br><small>⚠️ Vincoli: {'; '.join(r.fixability.constraints[:2])}</small>"

                # Gap
                gap_html = ""
                if r.company_gap.missing_assets:
                    gap_html = f"<br><small>📌 Gap: {', '.join(r.company_gap.missing_assets)}</small>"

                # Confidence badge
                conf_badge = f" <small style='color:#6c757d'>conf:{r.confidence:.1f}</small>" if r.confidence < 1.0 else ""

                st.markdown(f"""
                <div class="req-card {css}">
                  <strong>{icon} [{r.req_id}] {r.name}</strong> {sev_badge}{conf_badge}
                  <br>{r.user_message}
                  {fix_html}{gap_html}{ev_html}
                </div>
                """, unsafe_allow_html=True)


def render_action_plan(report: DecisionReport):
    ap = report.action_plan
    if not ap or not ap.steps:
        st.success("✅ Nessuna azione correttiva necessaria.")
        return
    st.markdown("### 🗺️ Piano d'Azione")
    path_map = {
        "avvalimento":  "🤝 Avvalimento",
        "rti":          "👥 RTI (Raggruppamento)",
        "progettisti":  "📐 Progettisti",
        "subappalto":   "🔨 Subappalto",
        "subappalto_qualificante": "🔨 Subappalto qualificante",
        "none":         "✅ Nessuna struttura necessaria"
    }
    st.info(f"**Percorso raccomandato:** {path_map.get(ap.recommended_path, ap.recommended_path)}")

    for step in ap.steps:
        ev_html = ""
        if step.evidence:
            ev = step.evidence[0]
            if ev.quote:
                ev_html = f'<div class="evidence-quote">📎 "{ev.quote[:150]}"</div>'
        st.markdown(f"""
        <div class="action-step">
          <span class="step-num">{step.step}</span>
          <strong>{step.title}</strong><br>
          <small style="color:#6c757d">{step.why}</small>
          {ev_html}
        </div>
        """, unsafe_allow_html=True)
        if step.inputs_needed:
            with st.expander(f"📥 Cosa serve (step {step.step})"):
                for inp in step.inputs_needed:
                    st.markdown(f"- {inp}")
        if step.risks:
            with st.expander(f"⚠️ Rischi da evitare (step {step.step})"):
                for rsk in step.risks:
                    st.markdown(f"- 🔴 {rsk}")


def render_procedural_checklist(report: DecisionReport):
    items = report.procedural_checklist
    if not items:
        return
    st.markdown("### ✅ Checklist Procedurale")
    for item in items:
        icon = {"PENDING": "🔲", "DONE": "✅", "NOT_POSSIBLE": "🚫", "UNKNOWN": "❓"}.get(item.status, "❓")
        impact_badge = "🔴" if item.impact == "HARD_KO" else ("🟡" if item.impact == "SOFT_RISK" else "⬜")
        deadline_str = f" — entro **{item.deadline}**" if item.deadline else ""
        st.markdown(f"- {icon} {impact_badge} **{item.item}**{deadline_str}")


def render_document_checklist(report: DecisionReport):
    dc = report.document_checklist
    st.markdown("### 📂 Documenti da Preparare")

    sections = [
        ("📜 Amministrativi", dc.administrative),
        ("🔧 Tecnici",        dc.technical),
        ("💶 Economici",      dc.economic),
        ("🛡️ Garanzie",      dc.guarantees),
        ("💻 Piattaforma",    dc.platform),
    ]
    for label, items in sections:
        if not items:
            continue
        with st.expander(f"{label} ({len(items)})"):
            for d in items:
                obl = "🔴" if d.mandatory else "🟡"
                notes = f" *({d.notes})*" if d.notes else ""
                st.markdown(f"- {obl} {d.name}{notes}")


def render_risk_register(report: DecisionReport):
    if not report.risk_register:
        return
    st.markdown("### ⚠️ Registro Rischi")
    for r in report.risk_register:
        level_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(r.level, "❓")
        with st.expander(f"{level_icon} [{r.risk_id}] {r.message[:80]}"):
            st.markdown(f"**Tipo:** {r.risk_type} | **Livello:** {r.level}")
            if r.mitigations:
                st.markdown("**Mitigazioni:**")
                for m in r.mitigations:
                    st.markdown(f"- {m}")


def render_uncertainties(report: DecisionReport):
    uncs = [u for u in report.uncertainties if u.blocks_verdict]
    if not uncs:
        return
    st.markdown("### ❓ Domande aperte (bloccanti)")
    for u in uncs:
        st.warning(f"**{u.question}**\n\n_{u.why_needed}_")


def render_header(req: dict):
    obj  = req.get("oggetto_appalto", "N/D")
    imp  = req.get("importo_lavori") or req.get("importo_base_gara")
    ente = req.get("stazione_appaltante", "N/D")
    doc_type = req.get("document_type", "N/D")
    engine_label = {
        "sistema_qualificazione": "🔵 Sistema Qualificazione",
        "disciplinare": "📋 Disciplinare",
        "lettera_invito": "📩 Lettera invito",
        "altro": "📄 Documento"
    }.get(doc_type, f"📄 {doc_type}")
    imp_str = f"€{imp:,.0f}" if imp else "non specificato"
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#667eea,#764ba2);padding:1.8rem;
                border-radius:15px;color:white;margin-bottom:1.5rem;">
      <h2 style="margin:0">{obj[:100]}{"..." if len(obj)>100 else ""}</h2>
      <p style="margin:0.5rem 0 0 0;font-size:1.05rem;">
        <strong>Importo:</strong> {imp_str} &nbsp;|&nbsp;
        <strong>Ente:</strong> {ente} &nbsp;|&nbsp;
        <strong>Tipo:</strong> {engine_label}
      </p>
    </div>
    """, unsafe_allow_html=True)
    ev = req.get("importo_evidence")
    if ev:
        st.markdown(f'<div class="evidence-quote">📎 Evidenza importo: "{ev}"</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
# Render risultato completo
# ══════════════════════════════════════════════════════════

def _render_result(result: dict):
    report: DecisionReport = result["decision_report"]
    req = result["requisiti_estratti"]

    st.markdown("---")
    render_header(req)
    render_verdict(report)

    # Barra secondaria (legacy)
    legacy = result.get("legacy", {})
    score = legacy.get("punteggio_fattibilita", 0)
    if score:
        st.caption(f"Indicatore secondario: {score}/100")
        st.progress(score / 100)

    # Engine mode badge
    engine_mode = result.get("legacy", {}).get("engine_mode", "gara")
    engine_note = result.get("legacy", {}).get("engine_note", "")
    if engine_note:
        st.info(engine_note)

    # Check geografico
    geo = legacy.get("check_geografico", {})
    if geo.get("warning"):
        st.warning(f"🗺️ {geo.get('motivo')}")

    render_top_reasons(report)
    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Requisiti", "🗺️ Piano d'Azione",
        "✅ Checklist", "📂 Documenti", "⚠️ Rischi"
    ])

    with tab1:
        render_requirements(report)
    with tab2:
        render_action_plan(report)
    with tab3:
        render_procedural_checklist(report)
        render_uncertainties(report)
    with tab4:
        render_document_checklist(report)
    with tab5:
        render_risk_register(report)

    # Audit trace collassato
    with st.expander("🔍 Audit trace (sviluppatori)"):
        for entry in report.audit_trace:
            st.text(f"[{entry.event}] {entry.result} (conf: {entry.confidence:.2f})")
        st.caption(f"Generato: {report.generated_at} | Engine: {report.engine_mode}")


# ══════════════════════════════════════════════════════════
# Tab: Analisi Bando
# ══════════════════════════════════════════════════════════

def tab_analisi():
    """Gestisce upload e analisi. NON chiama _render_result — lo fa main()."""
    st.header("📊 Analisi Bando — Decision Engine")

    if not st.session_state.get("api_key"):
        st.warning("⚠️ Inserire API Key nella sidebar per procedere.")
        return

    uploaded = st.file_uploader("📄 Carica PDF Bando", type=["pdf"],
                                 help="PDF con testo selezionabile (non scansionato)")
    if not uploaded:
        if not st.session_state.get("result"):
            st.info("👆 Carica un PDF per iniziare l'analisi.")
        return

    st.success(f"✅ File caricato: **{uploaded.name}**")

    if not st.button("🔍 ANALIZZA BANDO", type="primary", use_container_width=True):
        return

    # Esegui analisi
    error_occurred = False
    with st.spinner("🤖 Estrazione requisiti e analisi in corso… (30–60 secondi)"):
        os.makedirs("data", exist_ok=True)
        temp_path = f"data/temp_{uploaded.name}"
        try:
            with open(temp_path, "wb") as f:
                f.write(uploaded.getbuffer())

            parser = BandoParser()
            text = parser.parse_pdf(temp_path, mode="full")

            analyzer = BandoAnalyzer(
                openai_api_key=st.session_state.api_key,
                profilo_path="config/profilo_azienda.json"
            )
            result = analyzer.analyze_bando(text)
            st.session_state.result = result
            st.session_state.analyzed_file = uploaded.name

        except Exception as e:
            st.error(f"❌ Errore durante l'analisi: {e}")
            st.exception(e)
            error_occurred = True
        finally:
            # Pulizia file temporaneo
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    if not error_occurred and st.session_state.get("result"):
        st.success("✅ Analisi completata! Risultati mostrati di seguito.")
        st.rerun()  # Forza un rerun pulito per evitare doppio rendering


# ══════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════

def sidebar():
    st.sidebar.title("⚙️ Configurazione")

    key = st.sidebar.text_input(
        "OpenAI API Key", type="password",
        value=st.session_state.get("api_key", ""),
        help="sk-proj-... dalla piattaforma OpenAI"
    )
    if key:
        st.session_state.api_key = key
        st.sidebar.success("✅ Key configurata")
    else:
        st.sidebar.warning("⚠️ API Key richiesta")

    st.sidebar.markdown("---")
    st.sidebar.subheader("👤 Profilo Aziendale")
    try:
        with open("config/profilo_azienda.json") as f:
            prof = json.load(f)
        soa_count  = len(prof.get("soa_possedute", []))
        cert_count = len([c for c in prof.get("certificazioni", []) if c.get("tipo", "").upper() != "SOA"])
        zone       = ", ".join(prof.get("aree_geografiche", []))
        st.sidebar.info(
            f"**{prof['nome_azienda']}**\n\n"
            f"SOA: {soa_count} attestati\n\n"
            f"Cert: {cert_count} certificazioni\n\n"
            f"Zone: {zone}"
        )
    except FileNotFoundError:
        st.sidebar.error("⚠️ `config/profilo_azienda.json` non trovato.")
    except Exception as e:
        st.sidebar.error(f"Errore profilo: {e}")

    st.sidebar.markdown("---")

    # Reset analisi
    if st.session_state.get("result"):
        file_name = st.session_state.get("analyzed_file", "bando")
        st.sidebar.caption(f"📄 Ultimo analizzato: **{file_name}**")
        if st.sidebar.button("🗑️ Nuova analisi", use_container_width=True):
            st.session_state.result = None
            st.session_state.analyzed_file = None
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "**BidPilot v3.0** — Decision Engine\n\n"
        "4 stati: `GO` / `GO_HIGH_RISK` / `GO_WITH_STRUCTURE` / `NO_GO`\n\n"
        "Libreria Requisiti v2.1 · 84 requisiti · 16 regole anti-inferenza"
    )


# ══════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════

def main():
    # Inizializza session state
    if "api_key" not in st.session_state:
        st.session_state.api_key = None
    if "result" not in st.session_state:
        st.session_state.result = None
    if "analyzed_file" not in st.session_state:
        st.session_state.analyzed_file = None

    st.title("📋 BidPilot 3.0 — Decision Engine")
    st.caption(
        "GO / NO-GO deterministico con evidenze, action plan e audit trail · "
        "Anti-Allucinazione · Libreria Requisiti v2.1"
    )

    sidebar()

    main_tab, drafts_tab = st.tabs(["📊 Analisi Bando", "✍️ Bozze (WIP)"])

    with main_tab:
        # Se c'è già un risultato in sessione, mostrarlo PRIMA del form upload
        if st.session_state.result:
            _render_result(st.session_state.result)
            st.markdown("---")
            st.caption("👇 Vuoi analizzare un altro bando? Usa il pulsante 'Nuova analisi' in sidebar o carica un nuovo PDF.")

        # Sempre mostrare il form di analisi
        # (se c'è già un risultato, serve per avviare una nuova analisi)
        if not st.session_state.result:
            tab_analisi()
        else:
            # Modalità compatta: solo uploader senza header ridondante
            with st.expander("🔄 Analizza un altro bando"):
                tab_analisi()

    with drafts_tab:
        st.info("🚧 Modulo generazione bozze offerta tecnica in sviluppo.")
        st.markdown(
            "Il modulo RAG per generazione bozze basate su progetti storici è previsto in **v3.1**.\n\n"
            "Inserire PDF di progetti storici in `data/progetti_storici/` per prepararsi."
        )


if __name__ == "__main__":
    os.makedirs("data/progetti_storici", exist_ok=True)
    os.makedirs("config", exist_ok=True)
    main()