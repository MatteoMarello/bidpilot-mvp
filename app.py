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
    page_title="BidPilot — Decision Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ══════════════════════════════════════════════════════════
# CSS — Design System Professionale
# ══════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

/* Reset e base */
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
.stApp { background: #f4f5f7; }

/* Nasconde elementi inutili — NON nascondere header: contiene il toggle sidebar */
#MainMenu { visibility: hidden !important; }
footer { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }
.block-container { padding: 1.5rem 2rem 2rem 2rem !important; max-width: 1400px; }

/* ── TOP HEADER BAR ── */
.app-header {
    background: linear-gradient(135deg, #0f1923 0%, #1a2a3a 100%);
    border-radius: 16px;
    padding: 1.4rem 2rem;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border: 1px solid #243447;
}
.app-header-title {
    font-size: 1.4rem;
    font-weight: 700;
    color: #fff;
    letter-spacing: -0.3px;
}
.app-header-title span {
    color: #3b82f6;
}
.app-header-sub {
    font-size: 0.78rem;
    color: #7a8fa6;
    margin-top: 2px;
    font-family: 'IBM Plex Mono', monospace;
}
.app-header-badge {
    background: #1d3557;
    color: #60a5fa;
    font-size: 0.7rem;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 6px;
    font-family: 'IBM Plex Mono', monospace;
    border: 1px solid #2d4a6a;
    letter-spacing: 0.5px;
}

/* ── TENDER INFO CARD ── */
.tender-card {
    background: linear-gradient(135deg, #0f1923 0%, #162032 100%);
    border-radius: 14px;
    padding: 1.6rem 2rem;
    margin-bottom: 1.2rem;
    border: 1px solid #1e3048;
    position: relative;
    overflow: hidden;
}
.tender-card::before {
    content: '';
    position: absolute;
    top: 0; right: 0;
    width: 200px; height: 200px;
    background: radial-gradient(circle at top right, rgba(59,130,246,0.08) 0%, transparent 70%);
    pointer-events: none;
}
.tender-title {
    font-size: 1.25rem;
    font-weight: 600;
    color: #e2e8f0;
    line-height: 1.3;
    margin-bottom: 0.8rem;
}
.tender-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.6rem;
}
.tender-chip {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.1);
    color: #94a3b8;
    font-size: 0.75rem;
    padding: 4px 10px;
    border-radius: 6px;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-family: 'IBM Plex Mono', monospace;
}
.tender-chip.highlight {
    background: rgba(59,130,246,0.12);
    border-color: rgba(59,130,246,0.3);
    color: #93c5fd;
}

/* ── VERDICT CARD ── */
.verdict-wrap {
    border-radius: 14px;
    padding: 1.8rem 2rem;
    margin-bottom: 1.2rem;
    display: flex;
    align-items: flex-start;
    gap: 1.4rem;
    border: 1px solid;
}
.verdict-icon-box {
    width: 64px;
    height: 64px;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 2rem;
    flex-shrink: 0;
}
.verdict-label {
    font-size: 1.55rem;
    font-weight: 700;
    letter-spacing: -0.5px;
    line-height: 1.2;
}
.verdict-sub {
    font-size: 0.9rem;
    margin-top: 0.3rem;
    line-height: 1.5;
}

.v-go    { background: #f0fdf4; border-color: #86efac; }
.v-go .verdict-label { color: #15803d; }
.v-go .verdict-sub { color: #4ade80; }
.v-go .verdict-icon-box { background: #dcfce7; }

.v-highrisk { background: #fffbeb; border-color: #fde68a; }
.v-highrisk .verdict-label { color: #b45309; }
.v-highrisk .verdict-sub { color: #d97706; }
.v-highrisk .verdict-icon-box { background: #fef3c7; }

.v-structure { background: #eff6ff; border-color: #93c5fd; }
.v-structure .verdict-label { color: #1d4ed8; }
.v-structure .verdict-sub { color: #3b82f6; }
.v-structure .verdict-icon-box { background: #dbeafe; }

.v-nogo { background: #fff1f2; border-color: #fca5a5; }
.v-nogo .verdict-label { color: #b91c1c; }
.v-nogo .verdict-sub { color: #ef4444; }
.v-nogo .verdict-icon-box { background: #fee2e2; }

/* ── STAT CARDS ── */
.stat-row {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 0.6rem;
    margin-bottom: 1.2rem;
}
.stat-card {
    background: white;
    border-radius: 10px;
    padding: 0.9rem 1rem;
    text-align: center;
    border: 1px solid #e2e8f0;
    transition: box-shadow 0.15s;
}
.stat-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.06); }
.stat-num {
    font-size: 1.6rem;
    font-weight: 700;
    line-height: 1;
    font-family: 'IBM Plex Mono', monospace;
}
.stat-label {
    font-size: 0.67rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-top: 3px;
}
.s-ok   .stat-num { color: #16a34a; }
.s-ok   .stat-label { color: #86efac; }
.s-fix  .stat-num { color: #2563eb; }
.s-fix  .stat-label { color: #93c5fd; }
.s-ko   .stat-num { color: #dc2626; }
.s-ko   .stat-label { color: #fca5a5; }
.s-unk  .stat-num { color: #d97706; }
.s-unk  .stat-label { color: #fcd34d; }
.s-risk .stat-num { color: #7c3aed; }
.s-risk .stat-label { color: #c4b5fd; }
.s-prem .stat-num { color: #0891b2; }
.s-prem .stat-label { color: #67e8f9; }

/* ── REQUIREMENT CARDS ── */
.req-card {
    background: white;
    border-radius: 10px;
    padding: 0.85rem 1rem;
    margin: 0.35rem 0;
    border: 1px solid #e2e8f0;
    border-left: 4px solid;
    transition: box-shadow 0.12s;
}
.req-card:hover { box-shadow: 0 2px 10px rgba(0,0,0,0.06); }
.req-ok       { border-left-color: #22c55e; }
.req-fixable  { border-left-color: #3b82f6; }
.req-ko       { border-left-color: #ef4444; }
.req-unknown  { border-left-color: #f59e0b; }
.req-risk     { border-left-color: #8b5cf6; }
.req-prem     { border-left-color: #06b6d4; }

.req-id {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    font-weight: 600;
    background: #f1f5f9;
    color: #64748b;
    padding: 2px 6px;
    border-radius: 4px;
    margin-right: 6px;
}
.req-name { font-weight: 600; font-size: 0.88rem; color: #1e293b; }
.req-msg  { font-size: 0.82rem; color: #475569; margin-top: 4px; line-height: 1.5; }
.req-fix  { font-size: 0.78rem; color: #2563eb; margin-top: 4px; font-weight: 500; }
.req-gap  { font-size: 0.78rem; color: #dc2626; margin-top: 3px; }
.req-ev   {
    background: #f8fafc;
    border-left: 3px solid #cbd5e1;
    padding: 4px 8px;
    font-size: 0.75rem;
    font-style: italic;
    color: #64748b;
    border-radius: 0 4px 4px 0;
    margin-top: 6px;
    font-family: 'IBM Plex Mono', monospace;
}
.sev-badge {
    font-size: 0.62rem;
    font-weight: 700;
    padding: 1px 5px;
    border-radius: 3px;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    margin-left: 5px;
}
.sev-hard { background: #fee2e2; color: #b91c1c; }
.sev-soft { background: #fef3c7; color: #92400e; }
.conf-badge {
    font-size: 0.62rem;
    font-family: 'IBM Plex Mono', monospace;
    color: #94a3b8;
    margin-left: 5px;
}

/* ── ACTION STEPS ── */
.action-step {
    background: white;
    border-radius: 12px;
    padding: 1.1rem 1.3rem;
    margin: 0.5rem 0;
    border: 1px solid #e2e8f0;
    display: flex;
    gap: 1rem;
    align-items: flex-start;
    transition: box-shadow 0.12s;
}
.action-step:hover { box-shadow: 0 4px 14px rgba(0,0,0,0.07); }
.step-num {
    background: #0f1923;
    color: white;
    border-radius: 50%;
    width: 34px;
    height: 34px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.85rem;
    flex-shrink: 0;
    font-family: 'IBM Plex Mono', monospace;
}
.step-body { flex: 1; }
.step-title { font-weight: 600; font-size: 0.92rem; color: #0f172a; }
.step-why   { font-size: 0.8rem; color: #64748b; margin-top: 2px; }

/* ── CHECKLIST ── */
.check-item {
    display: flex;
    align-items: flex-start;
    gap: 0.7rem;
    padding: 0.55rem 0;
    border-bottom: 1px solid #f1f5f9;
    font-size: 0.84rem;
}
.check-item:last-child { border-bottom: none; }
.check-icon { flex-shrink: 0; font-size: 1rem; margin-top: 1px; }
.check-text { color: #334155; line-height: 1.4; }
.check-deadline {
    font-size: 0.72rem;
    font-family: 'IBM Plex Mono', monospace;
    color: #ef4444;
    font-weight: 600;
    margin-top: 2px;
}

/* ── DOC ITEM ── */
.doc-item {
    display: flex;
    align-items: flex-start;
    gap: 0.6rem;
    padding: 0.45rem 0.7rem;
    border-radius: 7px;
    margin: 0.2rem 0;
    font-size: 0.82rem;
}
.doc-required { background: #fff1f2; }
.doc-optional { background: #f8fafc; }
.doc-name { font-weight: 500; color: #1e293b; }
.doc-note { font-size: 0.72rem; color: #94a3b8; margin-top: 1px; }

/* ── RISK CARD ── */
.risk-card {
    border-radius: 10px;
    padding: 0.9rem 1.1rem;
    margin: 0.4rem 0;
    border-left: 4px solid;
    font-size: 0.83rem;
}
.risk-HIGH   { background: #fff1f2; border-left-color: #ef4444; color: #7f1d1d; }
.risk-MEDIUM { background: #fffbeb; border-left-color: #f59e0b; color: #78350f; }
.risk-LOW    { background: #f0fdf4; border-left-color: #22c55e; color: #14532d; }
.risk-id { font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; opacity: 0.7; }

/* ── REASON CARD ── */
.reason-card {
    background: white;
    border-radius: 10px;
    padding: 0.9rem 1.1rem;
    margin: 0.4rem 0;
    border: 1px solid;
    font-size: 0.83rem;
}
.reason-ko   { border-color: #fca5a5; background: #fff1f2; }
.reason-fix  { border-color: #93c5fd; background: #eff6ff; }
.reason-unk  { border-color: #fde68a; background: #fffbeb; }

/* ── SIDEBAR CUSTOM ── */
.sidebar-company {
    background: linear-gradient(135deg, #0f1923 0%, #1a2733 100%);
    border-radius: 12px;
    padding: 1.1rem;
    margin: 0.5rem 0;
    border: 1px solid #243447;
}
.sidebar-company-name {
    font-weight: 700;
    color: #e2e8f0;
    font-size: 0.95rem;
}
.sidebar-stat {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 4px 0;
    font-size: 0.78rem;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}
.sidebar-stat:last-child { border-bottom: none; }
.sidebar-stat-key { color: #7a8fa6; }
.sidebar-stat-val { color: #93c5fd; font-weight: 600; font-family: 'IBM Plex Mono', monospace; }
.sidebar-soa-tag {
    display: inline-block;
    background: rgba(59,130,246,0.15);
    color: #93c5fd;
    border: 1px solid rgba(59,130,246,0.25);
    border-radius: 5px;
    font-size: 0.7rem;
    font-family: 'IBM Plex Mono', monospace;
    padding: 2px 7px;
    margin: 2px;
    font-weight: 600;
}

/* ── TABS override ── */
.stTabs [data-baseweb="tab-list"] {
    background: transparent;
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    background: white;
    border-radius: 8px !important;
    border: 1px solid #e2e8f0 !important;
    color: #64748b !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    padding: 6px 14px !important;
    transition: all 0.15s !important;
}
.stTabs [aria-selected="true"] {
    background: #0f1923 !important;
    color: white !important;
    border-color: #0f1923 !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: transparent;
    padding-top: 1rem;
}

/* ── UPLOAD AREA ── */
.upload-zone {
    background: white;
    border: 2px dashed #cbd5e1;
    border-radius: 14px;
    padding: 2.5rem;
    text-align: center;
    transition: border-color 0.2s;
    margin: 1rem 0;
}
.upload-zone:hover { border-color: #3b82f6; }
.upload-icon { font-size: 2.5rem; margin-bottom: 0.5rem; }
.upload-title { font-size: 1rem; font-weight: 600; color: #1e293b; }
.upload-sub { font-size: 0.8rem; color: #94a3b8; margin-top: 4px; }

/* ── SECTION HEADER ── */
.section-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 1.2rem 0 0.7rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid #f1f5f9;
}
.section-header-icon {
    width: 28px;
    height: 28px;
    background: #0f1923;
    border-radius: 7px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75rem;
    color: white;
}
.section-header-text {
    font-size: 0.95rem;
    font-weight: 700;
    color: #0f172a;
}

/* ── PATH BADGE ── */
.path-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    color: #1d4ed8;
    font-size: 0.82rem;
    font-weight: 600;
    padding: 6px 14px;
    border-radius: 8px;
    margin-bottom: 1rem;
}

/* ── METRIC TRIO ── */
.metric-trio {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.6rem;
    margin: 0.8rem 0 1.2rem;
}
.metric-box {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 0.75rem 1rem;
    text-align: center;
}
.metric-box-label { font-size: 0.7rem; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; }
.metric-box-val   { font-size: 1.1rem; font-weight: 700; color: #1e293b; margin-top: 2px; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
# Config verdetti
# ══════════════════════════════════════════════════════════

VERDICT_CFG = {
    VerdictStatus.GO: {
        "css": "v-go", "emoji": "✅", "label": "PARTECIPA",
        "desc": "Tutti i requisiti verificati. Nessun blocco rilevato.",
    },
    VerdictStatus.GO_HIGH_RISK: {
        "css": "v-highrisk", "emoji": "⚠️", "label": "PARTECIPA — ALTA ATTENZIONE",
        "desc": "Ammissibile, ma con rischi operativi o documentali da gestire.",
    },
    VerdictStatus.GO_WITH_STRUCTURE: {
        "css": "v-structure", "emoji": "🔵", "label": "PARTECIPA CON STRUTTURA",
        "desc": "Possibile con RTI / avvalimento / progettisti. Vedi Piano d'Azione.",
    },
    VerdictStatus.NO_GO: {
        "css": "v-nogo", "emoji": "🚫", "label": "NON PARTECIPARE",
        "desc": "Requisiti bloccanti non colmabili con le strutture ammesse.",
    },
    VerdictStatus.ELIGIBLE_QUALIFICATION: {
        "css": "v-go", "emoji": "✅", "label": "ELIGIBLE — QUALIFICAZIONE",
        "desc": "Requisiti di qualificazione soddisfatti.",
    },
    VerdictStatus.NOT_ELIGIBLE_QUALIFICATION: {
        "css": "v-nogo", "emoji": "🚫", "label": "NON ELIGIBLE — QUALIFICAZIONE",
        "desc": "Requisiti di qualificazione non soddisfatti.",
    },
    VerdictStatus.ELIGIBLE_STAGE1: {
        "css": "v-highrisk", "emoji": "⚠️", "label": "ELIGIBLE STAGE 1 — PPP",
        "desc": "Ammissione stage 1. Valutare fasi successive separatamente.",
    },
}

STATUS_CSS = {
    ReqStatus.OK: "req-ok",
    ReqStatus.FIXABLE: "req-fixable",
    ReqStatus.KO: "req-ko",
    ReqStatus.UNKNOWN: "req-unknown",
    ReqStatus.RISK_FLAG: "req-risk",
    ReqStatus.PREMIANTE: "req-prem",
}
STATUS_ICON = {
    ReqStatus.OK: "✅",
    ReqStatus.FIXABLE: "🔧",
    ReqStatus.KO: "❌",
    ReqStatus.UNKNOWN: "❓",
    ReqStatus.RISK_FLAG: "⚡",
    ReqStatus.PREMIANTE: "🏆",
}


# ══════════════════════════════════════════════════════════
# Componenti UI
# ══════════════════════════════════════════════════════════

def render_header_bar():
    st.markdown("""
    <div class="app-header">
      <div>
        <div class="app-header-title">⚡ Bid<span>Pilot</span></div>
        <div class="app-header-sub">Decision Engine v3.0 · Anti-Allucinazione · 84 Requisiti</div>
      </div>
      <div class="app-header-badge">GO / NO-GO DETERMINISTICO</div>
    </div>
    """, unsafe_allow_html=True)


def render_tender_header(req: dict):
    obj  = req.get("oggetto_appalto", "N/D")
    imp  = req.get("importo_lavori") or req.get("importo_base_gara")
    ente = req.get("stazione_appaltante", "N/D")
    doc_type = req.get("document_type", "N/D")
    cig  = req.get("codice_cig", "")
    imp_str = f"€ {imp:,.0f}" if imp else "—"

    type_label = {
        "disciplinare": "📋 Disciplinare",
        "lettera_invito": "📩 Lettera invito",
        "sistema_qualificazione": "🔵 Sis. Qualificazione",
        "avviso_eoi": "📢 EOI",
        "richiesta_preventivo": "📑 Preventivo",
        "altro": "📄 Documento"
    }.get(doc_type, f"📄 {doc_type}")

    cig_chip = f'<span class="tender-chip"><span>CIG</span> {cig}</span>' if cig else ""
    ev = req.get("importo_evidence", "")
    ev_html = f'<div class="req-ev" style="margin-top:0.7rem;">📎 {ev[:180]}</div>' if ev else ""

    st.markdown(f"""
    <div class="tender-card">
      <div class="tender-title">{obj[:140]}{"…" if len(obj) > 140 else ""}</div>
      <div class="tender-meta">
        <span class="tender-chip highlight">💶 {imp_str}</span>
        <span class="tender-chip">🏛️ {ente[:50]}</span>
        <span class="tender-chip">{type_label}</span>
        {cig_chip}
      </div>
      {ev_html}
    </div>
    """, unsafe_allow_html=True)


def render_verdict(report: DecisionReport):
    cfg = VERDICT_CFG.get(report.verdict.status, VERDICT_CFG[VerdictStatus.GO_HIGH_RISK])
    summary = report.verdict.summary or cfg["desc"]

    # Confidence display
    conf = report.verdict.profile_confidence
    conf_color = "#16a34a" if conf == 1.0 else ("#d97706" if conf >= 0.7 else "#dc2626")
    conf_label = "Profilo completo" if conf == 1.0 else ("Parzialmente verificato" if conf >= 0.7 else "Dati insufficienti")

    st.markdown(f"""
    <div class="verdict-wrap {cfg['css']}">
      <div class="verdict-icon-box">{cfg['emoji']}</div>
      <div style="flex:1">
        <div class="verdict-label">{cfg['label']}</div>
        <div class="verdict-sub">{summary}</div>
      </div>
      <div style="text-align:right; min-width:130px">
        <div style="font-size:0.68rem; text-transform:uppercase; letter-spacing:0.5px; color:#94a3b8; font-weight:600;">CONFIDENCE</div>
        <div style="font-size:1.5rem; font-weight:700; color:{conf_color}; font-family:'IBM Plex Mono',monospace;">{conf:.0%}</div>
        <div style="font-size:0.7rem; color:{conf_color}; font-weight:500;">{conf_label}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Metriche legale/operativa
    leg = report.verdict.legal_eligibility
    op  = report.verdict.operational_feasibility
    leg_icon = "✅" if leg == "eligible" else ("❌" if leg == "not_eligible" else "❓")
    op_icon  = "✅" if op  == "feasible"  else ("❌" if op == "not_feasible"   else "⚠️")

    st.markdown(f"""
    <div class="metric-trio">
      <div class="metric-box">
        <div class="metric-box-label">Ammissibilità legale</div>
        <div class="metric-box-val">{leg_icon} {leg.replace('_',' ').title()}</div>
      </div>
      <div class="metric-box">
        <div class="metric-box-label">Fattibilità operativa</div>
        <div class="metric-box-val">{op_icon} {op.replace('_',' ').title()}</div>
      </div>
      <div class="metric-box">
        <div class="metric-box-label">Engine attivo</div>
        <div class="metric-box-val" style="font-size:0.85rem">⚙️ {report.engine_mode.replace('_',' ').title()}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if report.verdict.stage_outputs:
        st.info("**Output per fase (PPP)**")
        for k, v in report.verdict.stage_outputs.items():
            st.markdown(f"- **{k}**: {v}")


def render_top_reasons(report: DecisionReport):
    if not report.top_reasons:
        return
    st.markdown("""
    <div class="section-header">
      <div class="section-header-icon">🎯</div>
      <div class="section-header-text">Ragioni Principali</div>
    </div>
    """, unsafe_allow_html=True)
    for r in report.top_reasons:
        css = ("reason-ko" if (r.severity == Severity.HARD_KO and not r.can_be_fixed)
               else "reason-fix" if r.can_be_fixed else "reason-unk")
        icon = "❌" if (r.severity == Severity.HARD_KO and not r.can_be_fixed) else "🔧" if r.can_be_fixed else "❓"
        fix_html = ""
        if r.can_be_fixed and r.fix_options:
            opts = ", ".join(r.fix_options)
            fix_html = f'<div style="font-size:0.78rem;color:#2563eb;margin-top:4px;font-weight:500;">🔧 Risolvibile con: {opts}</div>'
        ev_html = ""
        if r.evidence and r.evidence.quote:
            ev_html = f'<div class="req-ev">📎 "{r.evidence.quote[:200]}"</div>'
        req_id_html = f'<span class="req-id">{r.issue_type}</span>' if r.issue_type else ""
        st.markdown(f"""
        <div class="reason-card {css}">
          {req_id_html}<strong>{icon} {r.message[:220]}</strong>
          {fix_html}{ev_html}
        </div>
        """, unsafe_allow_html=True)


def render_requirements_summary(results):
    ko_c   = sum(1 for r in results if r.status == ReqStatus.KO)
    fix_c  = sum(1 for r in results if r.status == ReqStatus.FIXABLE)
    ok_c   = sum(1 for r in results if r.status == ReqStatus.OK)
    unk_c  = sum(1 for r in results if r.status == ReqStatus.UNKNOWN)
    risk_c = sum(1 for r in results if r.status == ReqStatus.RISK_FLAG)
    prem_c = sum(1 for r in results if r.status == ReqStatus.PREMIANTE)
    st.markdown(f"""
    <div class="stat-row">
      <div class="stat-card s-ok">
        <div class="stat-num">{ok_c}</div>
        <div class="stat-label">OK ✅</div>
      </div>
      <div class="stat-card s-fix">
        <div class="stat-num">{fix_c}</div>
        <div class="stat-label">Colmabili 🔧</div>
      </div>
      <div class="stat-card s-ko">
        <div class="stat-num">{ko_c}</div>
        <div class="stat-label">Bloccanti ❌</div>
      </div>
      <div class="stat-card s-unk">
        <div class="stat-num">{unk_c}</div>
        <div class="stat-label">Da verif. ❓</div>
      </div>
      <div class="stat-card s-risk">
        <div class="stat-num">{risk_c}</div>
        <div class="stat-label">Risk Flag ⚡</div>
      </div>
      <div class="stat-card s-prem">
        <div class="stat-num">{prem_c}</div>
        <div class="stat-label">Premianti 🏆</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_requirements(report: DecisionReport):
    results = report.requirements_results
    if not results:
        st.info("Nessun requisito valutato.")
        return

    render_requirements_summary(results)

    CATS = {
        "qualification":   ("🏗️", "SOA e Qualificazione"),
        "certification":   ("🏆", "Certificazioni"),
        "procedural":      ("🔒", "Gate Procedurali"),
        "design":          ("📐", "Progettazione e BIM"),
        "financial":       ("💶", "Economico-Finanziari"),
        "operational":     ("⏱️", "Vincoli Operativi"),
        "general":         ("📜", "Requisiti Generali"),
        "guarantee":       ("🛡️", "Garanzie e Polizze"),
        "participation":   ("🤝", "Forme di Partecipazione"),
        "professional":    ("👤", "Idoneità Professionale"),
        "meta":            ("ℹ️", "Classificazione"),
    }
    by_cat: dict = {}
    for r in results:
        by_cat.setdefault(r.category, []).append(r)

    priority = list(CATS.keys())
    all_cats = priority + [c for c in by_cat if c not in priority]

    for cat_key in all_cats:
        reqs = by_cat.get(cat_key, [])
        if not reqs:
            continue
        icon, label = CATS.get(cat_key, ("📁", cat_key.title()))
        has_hard = any(r.status in (ReqStatus.KO, ReqStatus.FIXABLE) and r.severity == Severity.HARD_KO for r in reqs)
        ko_in_cat = sum(1 for r in reqs if r.status == ReqStatus.KO)
        fix_in_cat = sum(1 for r in reqs if r.status == ReqStatus.FIXABLE)
        counter = f"  🔴 {ko_in_cat}" if ko_in_cat else (f"  🔵 {fix_in_cat}" if fix_in_cat else "")

        with st.expander(f"{icon} {label} ({len(reqs)}){counter}", expanded=has_hard):
            for r in reqs:
                css = STATUS_CSS.get(r.status, "req-unknown")
                icon_s = STATUS_ICON.get(r.status, "❓")
                sev_cls = "sev-hard" if r.severity == Severity.HARD_KO else "sev-soft" if r.severity == Severity.SOFT_RISK else ""
                sev_lbl = "HARD KO" if r.severity == Severity.HARD_KO else "SOFT" if r.severity == Severity.SOFT_RISK else ""
                sev_html = f'<span class="sev-badge {sev_cls}">{sev_lbl}</span>' if sev_cls else ""
                conf_html = f'<span class="conf-badge">conf {r.confidence:.1f}</span>' if r.confidence < 1.0 else ""

                ev_html = ""
                if r.evidence:
                    ev = r.evidence[0]
                    if ev.quote:
                        p = f" (p.{ev.page})" if ev.page else ""
                        ev_html = f'<div class="req-ev">📎 "{ev.quote[:200]}"{p}</div>'

                fix_html = ""
                if r.fixability.is_fixable and r.fixability.allowed_methods:
                    methods = ", ".join(r.fixability.allowed_methods)
                    fix_html = f'<div class="req-fix">🔧 Risolvibile con: <strong>{methods}</strong></div>'
                    if r.fixability.constraints:
                        cnstr = " · ".join(r.fixability.constraints[:2])
                        fix_html += f'<div style="font-size:0.74rem;color:#d97706;margin-top:2px">⚠️ {cnstr}</div>'

                gap_html = ""
                if r.company_gap.missing_assets:
                    gaps = ", ".join(r.company_gap.missing_assets[:3])
                    gap_html = f'<div class="req-gap">📌 Gap: {gaps}</div>'

                st.markdown(f"""
                <div class="req-card {css}">
                  <span class="req-id">{r.req_id}</span>
                  <span class="req-name">{icon_s} {r.name}</span>
                  {sev_html}{conf_html}
                  <div class="req-msg">{r.user_message}</div>
                  {fix_html}{gap_html}{ev_html}
                </div>
                """, unsafe_allow_html=True)


def render_action_plan(report: DecisionReport):
    ap = report.action_plan
    if not ap or not ap.steps:
        st.success("✅ Nessuna azione correttiva necessaria — partecipazione diretta.")
        return

    path_labels = {
        "avvalimento": "🤝 Avvalimento",
        "rti": "👥 RTI — Raggruppamento Temporaneo",
        "progettisti": "📐 Gruppo di Progettazione",
        "subappalto": "🔨 Subappalto",
        "subappalto_qualificante": "🔨 Subappalto Qualificante",
        "none": "✅ Partecipazione diretta",
    }
    path_lbl = path_labels.get(ap.recommended_path, ap.recommended_path)
    st.markdown(f'<div class="path-badge">Percorso raccomandato: {path_lbl}</div>', unsafe_allow_html=True)

    for step in ap.steps:
        ev_html = ""
        if step.evidence:
            ev = step.evidence[0]
            if ev.quote:
                ev_html = f'<div class="req-ev" style="margin-top:6px">📎 "{ev.quote[:150]}"</div>'
        st.markdown(f"""
        <div class="action-step">
          <div class="step-num">{step.step}</div>
          <div class="step-body">
            <div class="step-title">{step.title}</div>
            <div class="step-why">{step.why}</div>
            {ev_html}
          </div>
        </div>
        """, unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        if step.inputs_needed:
            with col1:
                with st.expander(f"📥 Cosa serve (step {step.step})"):
                    for inp in step.inputs_needed:
                        st.markdown(f"- {inp}")
        if step.risks:
            with col2:
                with st.expander(f"⚠️ Rischi (step {step.step})"):
                    for rsk in step.risks:
                        st.markdown(f"- 🔴 {rsk}")


def render_checklist(report: DecisionReport):
    items = report.procedural_checklist
    if not items:
        return
    st.markdown("""
    <div class="section-header">
      <div class="section-header-icon">✅</div>
      <div class="section-header-text">Checklist Procedurale</div>
    </div>
    """, unsafe_allow_html=True)
    for item in items:
        status_icon = {"PENDING": "🔲", "DONE": "✅", "NOT_POSSIBLE": "🚫", "UNKNOWN": "❓"}.get(item.status, "❓")
        impact_dot = "🔴" if item.impact == "HARD_KO" else ("🟡" if item.impact == "SOFT_RISK" else "⬜")
        deadline_html = f'<div class="check-deadline">⏰ Entro {item.deadline}</div>' if item.deadline else ""
        st.markdown(f"""
        <div class="check-item">
          <span class="check-icon">{status_icon}</span>
          <div>
            <div class="check-text">{impact_dot} <strong>{item.item}</strong></div>
            {deadline_html}
          </div>
        </div>
        """, unsafe_allow_html=True)

    # Uncertainties bloccanti
    uncs = [u for u in report.uncertainties if u.blocks_verdict]
    if uncs:
        st.markdown("""
        <div class="section-header" style="margin-top:1.2rem">
          <div class="section-header-icon">❓</div>
          <div class="section-header-text">Domande Aperte (bloccanti)</div>
        </div>
        """, unsafe_allow_html=True)
        for u in uncs:
            st.warning(f"**{u.question}**\n\n_{u.why_needed}_")


def render_documents(report: DecisionReport):
    dc = report.document_checklist
    sections = [
        ("📜 Amministrativi", dc.administrative, True),
        ("🔧 Tecnici",        dc.technical,       True),
        ("💶 Economici",      dc.economic,        False),
        ("🛡️ Garanzie",      dc.guarantees,      False),
        ("💻 Piattaforma",    dc.platform,        False),
    ]
    for label, items, expanded in sections:
        if not items:
            continue
        with st.expander(f"{label} ({len(items)})", expanded=expanded):
            for d in items:
                css = "doc-required" if d.mandatory else "doc-optional"
                dot = "🔴" if d.mandatory else "🟡"
                note_html = f'<div class="doc-note">{d.notes}</div>' if d.notes else ""
                st.markdown(f"""
                <div class="doc-item {css}">
                  <span>{dot}</span>
                  <div>
                    <div class="doc-name">{d.name}</div>
                    {note_html}
                  </div>
                </div>
                """, unsafe_allow_html=True)


def render_risks(report: DecisionReport):
    if not report.risk_register:
        st.success("✅ Nessun rischio critico identificato.")
        return
    high = [r for r in report.risk_register if r.level == "HIGH"]
    med  = [r for r in report.risk_register if r.level == "MEDIUM"]
    low  = [r for r in report.risk_register if r.level == "LOW"]
    for level_label, items in [("🔴 Alta Priorità", high), ("🟡 Media Priorità", med), ("🟢 Bassa Priorità", low)]:
        if not items:
            continue
        st.markdown(f"**{level_label}**")
        for r in items:
            mit_html = ""
            if r.mitigations:
                mits = "".join(f"<li>{m}</li>" for m in r.mitigations)
                mit_html = f'<div style="margin-top:5px;font-size:0.78rem;color:#475569"><ul style="margin:0;padding-left:1.2rem">{mits}</ul></div>'
            st.markdown(f"""
            <div class="risk-card risk-{r.level}">
              <div class="risk-id">[{r.risk_id}] {r.risk_type}</div>
              <div style="margin-top:3px;font-weight:500">{r.message}</div>
              {mit_html}
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
# Render risultato completo
# ══════════════════════════════════════════════════════════

def _render_result(result: dict):
    report: DecisionReport = result["decision_report"]
    req = result["requisiti_estratti"]
    legacy = result.get("legacy", {})

    render_tender_header(req)

    # Warning geografico
    geo = legacy.get("check_geografico", {})
    if geo.get("warning"):
        st.warning(f"🗺️ {geo.get('motivo')}")

    # Engine note
    engine_note = legacy.get("engine_note", "")
    if engine_note:
        st.info(engine_note)

    render_verdict(report)
    render_top_reasons(report)

    st.markdown('<div style="height:0.4rem"></div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Requisiti",
        "🗺️ Piano d'Azione",
        "✅ Checklist",
        "📂 Documenti",
        "⚠️ Rischi",
    ])
    with tab1:
        render_requirements(report)
    with tab2:
        render_action_plan(report)
    with tab3:
        render_checklist(report)
    with tab4:
        render_documents(report)
    with tab5:
        render_risks(report)

    with st.expander("🔍 Audit Trace (sviluppatori)"):
        for entry in report.audit_trace:
            st.code(f"[{entry.event}] {entry.result}  conf:{entry.confidence:.2f}", language=None)
        st.caption(f"Generato: {report.generated_at} · Engine: {report.engine_mode}")


# ══════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════

def sidebar():
    with st.sidebar:
        st.markdown("### ⚙️ Configurazione")

        key = st.text_input(
            "OpenAI API Key", type="password",
            value=st.session_state.get("api_key", ""),
            placeholder="sk-proj-…",
            help="Ottieni la key su platform.openai.com"
        )
        if key:
            st.session_state.api_key = key
            st.success("✅ API Key configurata")
        else:
            st.warning("⚠️ Inserire API Key per procedere")

        st.markdown("---")
        st.markdown("**👤 Profilo Aziendale**")

        try:
            with open("config/profilo_azienda.json") as f:
                prof = json.load(f)

            soa_list = prof.get("soa_possedute", [])
            cert_list = [c for c in prof.get("certificazioni", []) if c.get("tipo", "").upper() != "SOA"]
            zone = " · ".join(prof.get("aree_geografiche", [])[:3])
            soa_tags = "".join(
                f'<span class="sidebar-soa-tag">{s["categoria"]} {s["classifica"]}</span>'
                for s in soa_list
            )

            st.markdown(f"""
            <div class="sidebar-company">
              <div class="sidebar-company-name">{prof['nome_azienda']}</div>
              <div style="font-size:0.72rem;color:#7a8fa6;margin-bottom:0.5rem">{prof.get('sede','')}</div>
              <div class="sidebar-stat">
                <span class="sidebar-stat-key">Zone operative</span>
                <span class="sidebar-stat-val">{len(prof.get('aree_geografiche', []))}</span>
              </div>
              <div class="sidebar-stat">
                <span class="sidebar-stat-key">SOA possedute</span>
                <span class="sidebar-stat-val">{len(soa_list)}</span>
              </div>
              <div class="sidebar-stat">
                <span class="sidebar-stat-key">Certificazioni</span>
                <span class="sidebar-stat-val">{len(cert_list)}</span>
              </div>
              <div style="margin-top:0.5rem">{soa_tags}</div>
            </div>
            """, unsafe_allow_html=True)
            st.caption(f"🗺️ {zone}")

        except FileNotFoundError:
            st.error("⚠️ `config/profilo_azienda.json` non trovato.")
        except Exception as e:
            st.error(f"Errore profilo: {e}")

        st.markdown("---")

        if st.session_state.get("result"):
            fname = st.session_state.get("analyzed_file", "bando")
            st.caption(f"📄 Analizzato: **{fname}**")
            if st.button("🗑️ Nuova analisi", use_container_width=True, type="secondary"):
                st.session_state.result = None
                st.session_state.analyzed_file = None
                st.rerun()

        st.markdown("---")
        st.markdown(
            '<div style="font-size:0.72rem;color:#94a3b8;line-height:1.6">'
            'BidPilot v3.0 · Libreria Requisiti v2.1<br>'
            '84 requisiti · 16 regole anti-inferenza<br>'
            '<code style="font-size:0.68rem">GO · GO_HIGH_RISK · GO_WITH_STRUCTURE · NO_GO</code>'
            '</div>',
            unsafe_allow_html=True
        )


# ══════════════════════════════════════════════════════════
# Tab Analisi
# ══════════════════════════════════════════════════════════

def tab_analisi():
    if not st.session_state.get("api_key"):
        st.markdown("""
        <div class="upload-zone">
          <div class="upload-icon">🔑</div>
          <div class="upload-title">API Key richiesta</div>
          <div class="upload-sub">Inserisci la tua OpenAI API Key nella sidebar per procedere.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    st.markdown("""
    <div class="section-header">
      <div class="section-header-icon">📄</div>
      <div class="section-header-text">Carica Bando di Gara</div>
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Seleziona il PDF del bando",
        type=["pdf"],
        help="PDF con testo selezionabile (non scansionato). Max 100 pagine.",
        label_visibility="collapsed"
    )

    if not uploaded:
        st.markdown("""
        <div class="upload-zone">
          <div class="upload-icon">📂</div>
          <div class="upload-title">Trascina il PDF o clicca Sfoglia</div>
          <div class="upload-sub">Supporta disciplinari, lettere invito, sistemi di qualificazione · Max 100 pagine</div>
        </div>
        """, unsafe_allow_html=True)
        return

    col1, col2 = st.columns([3, 1])
    with col1:
        st.success(f"✅ **{uploaded.name}** — {uploaded.size / 1024:.0f} KB")
    with col2:
        start = st.button("⚡ ANALIZZA", type="primary", use_container_width=True)

    if not start:
        return

    error_occurred = False
    with st.spinner("🤖 Estrazione requisiti in corso… (30–60 secondi)"):
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
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    if not error_occurred and st.session_state.get("result"):
        st.success("✅ Analisi completata!")
        st.rerun()


# ══════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════

def main():
    for key in ("api_key", "result", "analyzed_file"):
        if key not in st.session_state:
            st.session_state[key] = None

    render_header_bar()
    sidebar()

    main_tab, drafts_tab = st.tabs(["📊 Analisi Bando", "✍️ Bozze Offerta (WIP)"])

    with main_tab:
        if st.session_state.result:
            _render_result(st.session_state.result)
            st.markdown("---")
            with st.expander("🔄 Analizza un altro bando"):
                tab_analisi()
        else:
            tab_analisi()

    with drafts_tab:
        st.markdown("""
        <div class="upload-zone">
          <div class="upload-icon">🚧</div>
          <div class="upload-title">Modulo Bozze Offerta Tecnica</div>
          <div class="upload-sub">Generazione automatica bozze basate su progetti storici · Previsto in v3.1<br>
          Inserisci i PDF dei tuoi progetti in <code>data/progetti_storici/</code></div>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    os.makedirs("data/progetti_storici", exist_ok=True)
    os.makedirs("config", exist_ok=True)
    main()