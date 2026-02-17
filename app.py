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
    }
}

STATUS_CSS = {
    ReqStatus.OK: "req-ok", ReqStatus.FIXABLE: "req-fixable",
    ReqStatus.KO: "req-ko", ReqStatus.UNKNOWN: "req-unknown"
}
STATUS_ICON = {
    ReqStatus.OK: "✅", ReqStatus.FIXABLE: "🔧",
    ReqStatus.KO: "❌", ReqStatus.UNKNOWN: "❓"
}


def render_verdict(report: DecisionReport):
    cfg = VERDICT_CONFIG[report.verdict.status]
    summary = report.verdict.summary or cfg["desc"]
    st.markdown(f"""
    <div class="verdict-box {cfg['css']}">
      <h1>{cfg['emoji']} {cfg['label']}</h1>
      <div class="sub">{summary}</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    leg_icon = "✅" if report.verdict.legal_eligibility == "eligible" else ("❌" if report.verdict.legal_eligibility == "not_eligible" else "❓")
    op_icon  = "✅" if report.verdict.operational_feasibility == "feasible" else ("❌" if report.verdict.operational_feasibility == "not_feasible" else "⚠️")
    c1.metric("Ammissibilità legale", f"{leg_icon} {report.verdict.legal_eligibility.replace('_', ' ').title()}")
    c2.metric("Fattibilità operativa", f"{op_icon} {report.verdict.operational_feasibility.replace('_', ' ').title()}")


def render_top_reasons(report: DecisionReport):
    if not report.top_reasons:
        return
    st.markdown("### 🎯 Ragioni principali")
    for r in report.top_reasons:
        icon = "❌" if r.severity == Severity.HARD_KO else "⚠️"
        css = "req-ko" if r.severity == Severity.HARD_KO and not r.can_be_fixed else "req-fixable" if r.can_be_fixed else "req-unknown"
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
        return
    st.markdown("### 📋 Analisi Requisiti")

    # Tabs per categoria
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
    }

    by_cat = {}
    for r in results:
        by_cat.setdefault(r.category, []).append(r)

    # Sommario
    ko_c = sum(1 for r in results if r.status == ReqStatus.KO)
    fix_c = sum(1 for r in results if r.status == ReqStatus.FIXABLE)
    ok_c = sum(1 for r in results if r.status == ReqStatus.OK)
    unk_c = sum(1 for r in results if r.status == ReqStatus.UNKNOWN)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("✅ OK", ok_c)
    c2.metric("🔧 Colmabili", fix_c)
    c3.metric("❌ Bloccanti", ko_c)
    c4.metric("❓ Da verificare", unk_c)

    st.markdown("---")

    for cat_key, cat_label in cats.items():
        reqs = by_cat.get(cat_key, [])
        if not reqs:
            continue
        with st.expander(f"{cat_label} ({len(reqs)} requisiti)", expanded=(cat_key in ("qualification", "procedural"))):
            for r in reqs:
                css = STATUS_CSS[r.status]
                icon = STATUS_ICON[r.status]
                sev_badge = "🔴" if r.severity == Severity.HARD_KO else ("🟡" if r.severity == Severity.SOFT_RISK else "🟢")
                ev_html = ""
                if r.evidence and r.evidence[0].quote:
                    ev_html = f'<div class="evidence-quote">📎 "{r.evidence[0].quote[:200]}" (p.{r.evidence[0].page})</div>'
                fix_html = ""
                if r.fixability.is_fixable:
                    fix_html = f"<br><small>🔧 Risolvibile con: <strong>{', '.join(r.fixability.allowed_methods)}</strong></small>"
                    if r.fixability.constraints:
                        fix_html += f"<br><small>⚠️ Vincoli: {'; '.join(r.fixability.constraints[:2])}</small>"
                gap_html = ""
                if r.company_gap.missing_assets:
                    gap_html = f"<br><small>📌 Gap: {', '.join(r.company_gap.missing_assets)}</small>"
                st.markdown(f"""
                <div class="req-card {css}">
                  <strong>{icon} [{r.req_id}] {r.name}</strong> {sev_badge}
                  <br>{r.user_message}
                  {fix_html}{gap_html}{ev_html}
                </div>
                """, unsafe_allow_html=True)


def render_action_plan(report: DecisionReport):
    ap = report.action_plan
    if not ap.steps:
        st.success("✅ Nessuna azione correttiva necessaria.")
        return
    st.markdown("### 🗺️ Piano d'Azione")
    path_map = {
        "avvalimento": "🤝 Avvalimento",
        "rti": "👥 RTI (Raggruppamento)",
        "progettisti": "📐 Progettisti",
        "subappalto": "🔨 Subappalto",
        "none": "✅ Nessuna struttura necessaria"
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
        impact_badge = "🔴" if item.impact == "HARD_KO" else "🟡"
        deadline_str = f" — entro **{item.deadline}**" if item.deadline else ""
        st.markdown(f"- {icon} {impact_badge} **{item.item}**{deadline_str}")


def render_document_checklist(report: DecisionReport):
    dc = report.document_checklist
    st.markdown("### 📂 Documenti da Preparare")

    sections = [
        ("📜 Amministrativi", dc.administrative),
        ("🔧 Tecnici", dc.technical),
        ("💶 Economici", dc.economic),
        ("🛡️ Garanzie", dc.guarantees),
        ("💻 Piattaforma", dc.platform),
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
    obj = req.get("oggetto_appalto", "N/D")
    imp = req.get("importo_lavori")
    ente = req.get("stazione_appaltante", "N/D")
    imp_str = f"€{imp:,.0f}" if imp else "non specificato"
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#667eea,#764ba2);padding:1.8rem;
                border-radius:15px;color:white;margin-bottom:1.5rem;">
      <h2 style="margin:0">{obj[:100]}{"..." if len(obj)>100 else ""}</h2>
      <p style="margin:0.5rem 0 0 0;font-size:1.05rem;">
        <strong>Importo:</strong> {imp_str} &nbsp;|&nbsp;
        <strong>Ente:</strong> {ente}
      </p>
    </div>
    """, unsafe_allow_html=True)
    ev = req.get("importo_evidence")
    if ev:
        st.markdown(f'<div class="evidence-quote">📎 Evidenza importo: "{ev}"</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
# Tabs
# ══════════════════════════════════════════════════════════

def tab_analisi():
    st.header("📊 Analisi Bando — Decision Engine")

    if not st.session_state.get("api_key"):
        st.warning("⚠️ Inserire API Key nella sidebar")
        return

    uploaded = st.file_uploader("📄 Carica PDF Bando", type=["pdf"])
    if not uploaded:
        return

    st.success(f"✅ File: {uploaded.name}")
    if not st.button("🔍 ANALIZZA", type="primary", use_container_width=True):
        return

    with st.spinner("🤖 Estrazione e analisi in corso…"):
        temp = f"data/temp_{uploaded.name}"
        os.makedirs("data", exist_ok=True)
        with open(temp, "wb") as f:
            f.write(uploaded.getbuffer())

        try:
            parser = BandoParser()
            text = parser.parse_pdf(temp, mode="full")
            analyzer = BandoAnalyzer(
                openai_api_key=st.session_state.api_key,
                profilo_path="config/profilo_azienda.json"
            )
            result = analyzer.analyze_bando(text)
            st.session_state.result = result
            st.success("✅ Analisi completata!")
        except Exception as e:
            st.error(f"❌ {e}")
            st.exception(e)
            return

    # Visualizza
    _render_result(st.session_state.result)


def _render_result(result: dict):
    report: DecisionReport = result["decision_report"]
    req = result["requisiti_estratti"]

    st.markdown("---")
    render_header(req)
    render_verdict(report)

    # Barra avanzamento opzionale (valore secondario)
    legacy = result.get("legacy", {})
    score = legacy.get("punteggio_fattibilita", 0)
    if score:
        st.caption(f"Indicatore secondario: {score}/100")
        st.progress(score / 100)

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

    # Audit trace (collassato)
    with st.expander("🔍 Audit trace (sviluppatori)"):
        for entry in report.audit_trace:
            st.text(f"[{entry.event}] {entry.result} (conf: {entry.confidence:.2f})")
        st.caption(f"Generato: {report.generated_at}")


# ══════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════

def sidebar():
    st.sidebar.title("⚙️ Configurazione")
    key = st.sidebar.text_input("OpenAI API Key", type="password",
                                value=st.session_state.get("api_key", ""))
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
        st.sidebar.info(
            f"**{prof['nome_azienda']}**\n\n"
            f"SOA: {len(prof.get('soa_possedute', []))}\n"
            f"Cert: {len([c for c in prof.get('certificazioni', []) if c.get('tipo') != 'SOA'])}\n"
            f"Zone: {', '.join(prof.get('aree_geografiche', []))}"
        )
    except Exception:
        st.sidebar.error("Profilo non trovato — verificare config/profilo_azienda.json")

    st.sidebar.markdown("---")
    st.sidebar.markdown("**v3.0** • Decision Engine\n\n4 stati: GO / GO_HIGH_RISK / GO_WITH_STRUCTURE / NO_GO")


# ══════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════

def main():
    if "api_key" not in st.session_state:
        st.session_state.api_key = None
    if "result" not in st.session_state:
        st.session_state.result = None

    st.title("📋 BidPilot 3.0 — Decision Engine")
    st.caption("GO / NO-GO deterministico con evidenze, action plan e audit trail • Anti-Allucinazione")

    sidebar()

    tab1, tab2 = st.tabs(["📊 Analisi Bando", "✍️ Bozze (WIP)"])
    with tab1:
        if st.session_state.result:
            _render_result(st.session_state.result)
        tab_analisi()
    with tab2:
        st.info("🚧 Modulo generazione bozze in sviluppo")


if __name__ == "__main__":
    os.makedirs("data/progetti_storici", exist_ok=True)
    os.makedirs("config", exist_ok=True)
    main()