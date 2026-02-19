"""
BidPilot MVP — BandoCard
========================
Output: BandoCard con 6 blocchi. Nessun GO/NO-GO, nessun punteggio.
Profilo minimo (SOA + Certificazioni + Regioni) sufficiente per funzionare.

Feature flag ADVANCED_MODE:
  False (default) → MVP: solo BandoCard
  True            → modalità avanzata: piano d'azione, risk register, checklist
"""
import streamlit as st
import os
import json
from datetime import datetime

# ── Feature flag ──────────────────────────────────────
ADVANCED_MODE = False   # Cambia a True per abilitare moduli avanzati
# ──────────────────────────────────────────────────────

from src.parser import parse_pdf as _parse_pdf
from src.analyzer import analyze as _analyze
from src.requirements_engine import evaluate_all
from src.bando_card import build_bando_card, BandoCard, ReqItem
from src.profile_builder import build_from_form, build_from_json

st.set_page_config(
    page_title="BidPilot — BandoCard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ══════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
.stApp { background: #f4f5f7; }
#MainMenu { visibility: hidden !important; }
footer { display: none !important; }
.block-container { padding: 1.5rem 2rem 2rem 2rem !important; max-width: 1200px; }

/* Header */
.app-header {
    background: linear-gradient(135deg, #0f1923 0%, #1a2a3a 100%);
    border-radius: 14px; padding: 1.2rem 1.8rem; margin-bottom: 1.4rem;
    display: flex; align-items: center; justify-content: space-between;
    border: 1px solid #243447;
}
.app-header-title { font-size: 1.35rem; font-weight: 700; color: #fff; }
.app-header-title span { color: #3b82f6; }
.app-header-sub { font-size: 0.75rem; color: #7a8fa6; margin-top: 2px; font-family: 'IBM Plex Mono', monospace; }
.app-header-badge {
    background: #1d3557; color: #60a5fa; font-size: 0.68rem; font-weight: 600;
    padding: 4px 10px; border-radius: 6px; border: 1px solid #2d4a6a;
    font-family: 'IBM Plex Mono', monospace;
}

/* BandoCard container */
.bando-card {
    background: white; border-radius: 14px; border: 1px solid #e2e8f0;
    overflow: hidden; margin-bottom: 1rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}
.card-block-header {
    background: #f8fafc; border-bottom: 1px solid #e2e8f0;
    padding: 0.7rem 1.2rem; display: flex; align-items: center; gap: 0.5rem;
}
.card-block-icon { font-size: 1rem; }
.card-block-title { font-size: 0.85rem; font-weight: 700; color: #0f172a; text-transform: uppercase; letter-spacing: 0.4px; }
.card-block-body { padding: 1rem 1.2rem; }

/* Identità gara */
.gara-title { font-size: 1.1rem; font-weight: 600; color: #0f172a; line-height: 1.35; margin-bottom: 0.7rem; }
.gara-chips { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.chip {
    background: #f1f5f9; border: 1px solid #e2e8f0; color: #64748b;
    font-size: 0.72rem; padding: 3px 8px; border-radius: 5px;
    font-family: 'IBM Plex Mono', monospace; font-weight: 500;
}
.chip.blue { background: #eff6ff; border-color: #bfdbfe; color: #1d4ed8; }
.chip.green { background: #f0fdf4; border-color: #86efac; color: #15803d; }
.chip.orange { background: #fff7ed; border-color: #fed7aa; color: #c2410c; }

/* Scadenze */
.deadline-row {
    display: flex; align-items: center; gap: 0.6rem;
    padding: 0.5rem 0; border-bottom: 1px solid #f1f5f9; font-size: 0.84rem;
}
.deadline-row:last-child { border-bottom: none; }
.deadline-label { color: #475569; flex: 1; }
.deadline-date { font-family: 'IBM Plex Mono', monospace; color: #1e293b; font-weight: 600; }
.deadline-badge {
    font-size: 0.65rem; font-weight: 700; padding: 2px 6px; border-radius: 4px;
    text-transform: uppercase; letter-spacing: 0.4px;
}
.badge-urgente { background: #fee2e2; color: #b91c1c; }
.badge-scaduta { background: #fef3c7; color: #92400e; }
.badge-ok { background: #f0fdf4; color: #15803d; }
.deadline-mancante { color: #94a3b8; font-style: italic; font-size: 0.78rem; }

/* Requisiti ✅❌❓ */
.req-row {
    display: flex; align-items: flex-start; gap: 0.7rem;
    padding: 0.6rem 0; border-bottom: 1px solid #f8fafc;
}
.req-row:last-child { border-bottom: none; }
.req-emoji { font-size: 1rem; flex-shrink: 0; margin-top: 1px; }
.req-content { flex: 1; }
.req-name { font-weight: 600; font-size: 0.85rem; color: #1e293b; }
.req-msg { font-size: 0.78rem; color: #64748b; margin-top: 2px; line-height: 1.4; }
.req-evidence {
    background: #f8fafc; border-left: 3px solid #cbd5e1; padding: 4px 8px;
    font-size: 0.72rem; font-style: italic; color: #64748b; border-radius: 0 4px 4px 0;
    margin-top: 5px; font-family: 'IBM Plex Mono', monospace;
}
.req-note { font-size: 0.72rem; color: #94a3b8; margin-top: 2px; }
.profile-empty-banner {
    background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px;
    padding: 0.6rem 0.9rem; margin-bottom: 0.8rem; font-size: 0.8rem; color: #92400e;
}

/* Info operative */
.info-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.5rem; }
.info-item {
    background: #f8fafc; border-radius: 8px; padding: 0.6rem 0.8rem;
    border: 1px solid #e2e8f0;
}
.info-item-label { font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.4px; color: #94a3b8; font-weight: 600; }
.info-item-val { font-size: 0.85rem; font-weight: 600; color: #1e293b; margin-top: 2px; }
.info-si { color: #dc2626; }
.info-no { color: #16a34a; }
.info-unknown { color: #d97706; }

/* Da verificare */
.dv-item {
    display: flex; align-items: flex-start; gap: 0.5rem;
    padding: 0.5rem 0; border-bottom: 1px solid #fef3c7; font-size: 0.82rem; color: #78350f;
}
.dv-item:last-child { border-bottom: none; }

/* Sidebar */
.sidebar-section { margin-bottom: 1rem; }
.sidebar-section-title { font-size: 0.78rem; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.4px; margin-bottom: 0.4rem; }

/* Upload */
.upload-zone {
    background: white; border: 2px dashed #cbd5e1; border-radius: 12px;
    padding: 2rem; text-align: center; margin: 0.8rem 0;
}
.upload-icon { font-size: 2rem; margin-bottom: 0.4rem; }
.upload-title { font-size: 0.95rem; font-weight: 600; color: #1e293b; }
.upload-sub { font-size: 0.77rem; color: #94a3b8; margin-top: 3px; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# UI COMPONENTS
# ══════════════════════════════════════════════════════

def render_header():
    mode_badge = "ADVANCED MODE 🔓" if ADVANCED_MODE else "BANDO CARD MVP"
    st.markdown(f"""
    <div class="app-header">
      <div>
        <div class="app-header-title">⚡ Bid<span>Pilot</span></div>
        <div class="app-header-sub">BandoCard · Evidence-first · Matching ✅❌❓</div>
      </div>
      <div class="app-header-badge">{mode_badge}</div>
    </div>
    """, unsafe_allow_html=True)


def render_req_item(item: ReqItem):
    ev_html = ""
    if item.evidence_quote:
        pg = f" (p.{item.evidence_page})" if item.evidence_page else ""
        q = item.evidence_quote[:200]
        ev_html = f'<div class="req-evidence">📎 "{q}"{pg}</div>'

    note_html = f'<div class="req-note">{item.note}</div>' if item.note else ""

    st.markdown(f"""
    <div class="req-row">
      <div class="req-emoji">{item.emoji}</div>
      <div class="req-content">
        <div class="req-name">{item.name}</div>
        <div class="req-msg">{item.message}</div>
        {ev_html}{note_html}
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_bando_card(card: BandoCard):
    # ── BLOCCO 1 — IDENTITÀ GARA ──────────────────────
    imp_str = f"€ {card.importo:,.0f}" if card.importo else "Importo da verificare"
    cig_chip = f'<span class="chip blue">CIG {card.cig}</span>' if card.cig else '<span class="chip orange">CIG da verificare</span>'
    lotti_chip = f'<span class="chip">🗂️ {card.lotti} lotto/i</span>' if card.lotti > 1 else ""
    pnrr_chip = '<span class="chip orange">🔷 PNRR</span>' if card.is_pnrr else ""
    imp_chip = f'<span class="chip blue">💶 {imp_str}</span>'

    ev_html = ""
    if card.importo_evidence:
        q = card.importo_evidence[:150]
        ev_html = f'<div class="req-evidence" style="margin-top:0.6rem">📎 "{q}"</div>'

    st.markdown(f"""
    <div class="bando-card">
      <div class="card-block-header">
        <span class="card-block-icon">🏛️</span>
        <span class="card-block-title">Identità Gara</span>
      </div>
      <div class="card-block-body">
        <div class="gara-title">{card.oggetto}</div>
        <div class="gara-chips">
          {imp_chip}
          <span class="chip">🏛️ {card.ente[:60]}</span>
          <span class="chip">📋 {card.tipo_procedura}</span>
          {cig_chip}
          {lotti_chip}
          {pnrr_chip}
        </div>
        {ev_html}
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── BLOCCO 2 — SCADENZE ────────────────────────────
    if card.scadenze:
        rows_html = ""
        for sc in card.scadenze:
            if sc.data:
                date_str = f"{sc.data}" + (f" {sc.ora}" if sc.ora else "")
                if sc.scaduta:
                    badge = '<span class="deadline-badge badge-scaduta">⚠️ SCADUTA</span>'
                elif sc.urgente:
                    badge = f'<span class="deadline-badge badge-urgente">🔴 {sc.giorni_mancanti}gg</span>'
                else:
                    badge = f'<span class="deadline-badge badge-ok">{sc.giorni_mancanti}gg</span>' if sc.giorni_mancanti is not None else ""
                rows_html += f"""
                <div class="deadline-row">
                  <span class="deadline-label">{sc.label}</span>
                  <span class="deadline-date">{date_str}</span>
                  {badge}
                </div>"""
            else:
                rows_html += f"""
                <div class="deadline-row">
                  <span class="deadline-label">{sc.label}</span>
                  <span class="deadline-mancante">Da verificare nel documento</span>
                </div>"""

        st.markdown(f"""
        <div class="bando-card">
          <div class="card-block-header">
            <span class="card-block-icon">📅</span>
            <span class="card-block-title">Scadenze</span>
          </div>
          <div class="card-block-body">{rows_html}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── BLOCCO 3 — SOA RICHIESTE ──────────────────────
    if card.soa_items:
        soa_summary_ok = sum(1 for i in card.soa_items if i.stato == "ok")
        soa_summary_ko = sum(1 for i in card.soa_items if i.stato == "ko")
        soa_summary_unk = sum(1 for i in card.soa_items if i.stato == "unknown")

        st.markdown(f"""
        <div class="bando-card">
          <div class="card-block-header">
            <span class="card-block-icon">🏗️</span>
            <span class="card-block-title">SOA Richieste</span>
            &nbsp;
            <span class="chip green">✅ {soa_summary_ok}</span>
            <span class="chip" style="background:#fff1f2;border-color:#fca5a5;color:#b91c1c">❌ {soa_summary_ko}</span>
            <span class="chip orange">❓ {soa_summary_unk}</span>
          </div>
          <div class="card-block-body">
        """, unsafe_allow_html=True)

        if card.soa_profile_empty:
            st.markdown("""
            <div class="profile-empty-banner">
              ❓ Nessuna SOA inserita nel profilo — inserisci le tue attestazioni nella sidebar per vedere il matching.
            </div>
            """, unsafe_allow_html=True)

        for item in card.soa_items:
            render_req_item(item)

        st.markdown("</div></div>", unsafe_allow_html=True)

    # ── BLOCCO 4 — CERTIFICAZIONI ─────────────────────
    if card.cert_items:
        cert_ok = sum(1 for i in card.cert_items if i.stato == "ok")
        cert_ko = sum(1 for i in card.cert_items if i.stato == "ko")
        cert_unk = sum(1 for i in card.cert_items if i.stato == "unknown")

        st.markdown(f"""
        <div class="bando-card">
          <div class="card-block-header">
            <span class="card-block-icon">🏆</span>
            <span class="card-block-title">Certificazioni</span>
            &nbsp;
            <span class="chip green">✅ {cert_ok}</span>
            <span class="chip" style="background:#fff1f2;border-color:#fca5a5;color:#b91c1c">❌ {cert_ko}</span>
            <span class="chip orange">❓ {cert_unk}</span>
          </div>
          <div class="card-block-body">
        """, unsafe_allow_html=True)

        if card.cert_profile_empty:
            st.markdown("""
            <div class="profile-empty-banner">
              ❓ Nessuna certificazione inserita nel profilo — inserisci le tue certificazioni nella sidebar per vedere il matching.
            </div>
            """, unsafe_allow_html=True)

        for item in card.cert_items:
            render_req_item(item)

        st.markdown("</div></div>", unsafe_allow_html=True)

    # ── BLOCCO 5 — INFO OPERATIVE ─────────────────────
    info = card.info_op

    def yn(val: bool, si_label="SÌ", no_label="NO"):
        if val:
            return f'<span class="info-si">⚠️ {si_label}</span>'
        return f'<span class="info-no">✅ {no_label}</span>'

    def yn_str(val: str):
        if val == "si":
            return '<span class="info-si">⚠️ SÌ</span>'
        if val == "no":
            return '<span class="info-no">✅ NO</span>'
        return '<span class="info-unknown">❓ Da verificare</span>'

    piatt_str = info.piattaforma or "Non identificata"
    spid_str = " (SPID richiesto)" if info.piattaforma_spid else ""
    canale_str = info.canale_invio if info.canale_invio != "unknown" else "da verificare"

    st.markdown(f"""
    <div class="bando-card">
      <div class="card-block-header">
        <span class="card-block-icon">⚙️</span>
        <span class="card-block-title">Info Operative</span>
      </div>
      <div class="card-block-body">
        <div class="info-grid">
          <div class="info-item">
            <div class="info-item-label">Sopralluogo</div>
            <div class="info-item-val">{yn(info.sopralluogo_obbligatorio, "OBBLIGATORIO a pena esclusione", "NON richiesto")}</div>
          </div>
          <div class="info-item">
            <div class="info-item-label">Piattaforma invio</div>
            <div class="info-item-val">{piatt_str}{spid_str}</div>
          </div>
          <div class="info-item">
            <div class="info-item-label">Contributo ANAC</div>
            <div class="info-item-val">{yn_str(info.contributo_anac)}</div>
          </div>
          <div class="info-item">
            <div class="info-item-label">PNRR</div>
            <div class="info-item-val">{yn(info.pnrr, "SÌ — DNSH obbligatorio", "NO")}</div>
          </div>
          <div class="info-item">
            <div class="info-item-label">Appalto integrato</div>
            <div class="info-item-val">{yn(info.appalto_integrato, "SÌ — progettisti richiesti", "NO")}</div>
          </div>
          <div class="info-item">
            <div class="info-item-label">Canale invio</div>
            <div class="info-item-val">{canale_str}</div>
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── BLOCCO 6 — DA VERIFICARE ──────────────────────
    if card.da_verificare:
        dv_html = "".join(
            f'<div class="dv-item"><span>❓</span><span>{msg}</span></div>'
            for msg in card.da_verificare
        )
        st.markdown(f"""
        <div class="bando-card" style="border-color:#fde68a">
          <div class="card-block-header" style="background:#fffbeb;border-color:#fde68a">
            <span class="card-block-icon">❓</span>
            <span class="card-block-title" style="color:#92400e">Da Verificare ({len(card.da_verificare)})</span>
          </div>
          <div class="card-block-body" style="background:#fffbeb">{dv_html}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── ADVANCED MODE (disabilitato nel MVP) ──────────
    if ADVANCED_MODE and hasattr(st.session_state, "full_result"):
        _render_advanced(st.session_state.full_result)


def _render_advanced(result: dict):
    """Moduli avanzati — attivi solo con ADVANCED_MODE=True."""
    st.markdown("---")
    st.markdown("### 🔬 Modalità Avanzata")
    st.info("Piano d'azione, risk register e checklist — funzionalità post-MVP.")


# ══════════════════════════════════════════════════════
# SIDEBAR — PROFILO MINIMO
# ══════════════════════════════════════════════════════

def sidebar_profile():
    """Form profilo minimo nella sidebar. Restituisce MinimalProfile."""
    with st.sidebar:
        st.markdown("### ⚙️ Configurazione")

        # API Key
        api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            value=st.session_state.get("api_key", ""),
            placeholder="sk-...",
            help="Ottieni la key su platform.openai.com",
        )
        if api_key:
            st.session_state.api_key = api_key
            st.success("✅ API Key configurata")
        else:
            st.warning("⚠️ Inserire OpenAI API Key per procedere")

        st.markdown("---")

        # ── Selezione modalità profilo ──────────────────
        profile_mode = st.radio(
            "Profilo aziendale",
            ["📝 Inserisci manualmente", "📂 Carica da profilo_azienda.json"],
            index=0,
            horizontal=False,
        )

        minimal_profile = None

        if profile_mode == "📂 Carica da profilo_azienda.json":
            try:
                with open("config/profilo_azienda.json") as f:
                    prof_data = json.load(f)
                minimal_profile = build_from_json(prof_data)
                soa_tags = " ".join(
                    f"`{s['categoria']} {s['classifica']}`"
                    for s in prof_data.get("soa_possedute", [])
                )
                st.success(f"✅ **{prof_data.get('nome_azienda', 'Azienda')}**")
                st.caption(f"SOA: {soa_tags or 'nessuna'}")
                certs = [c["tipo"] for c in prof_data.get("certificazioni", []) if c.get("tipo", "").upper() != "SOA"]
                st.caption(f"Cert: {', '.join(certs) or 'nessuna'}")
            except FileNotFoundError:
                st.warning("⚠️ File `config/profilo_azienda.json` non trovato. Usa il form manuale.")
                profile_mode = "📝 Inserisci manualmente"
            except Exception as e:
                st.error(f"Errore caricamento profilo: {e}")
                profile_mode = "📝 Inserisci manualmente"

        if profile_mode == "📝 Inserisci manualmente":
            st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
            st.markdown("**🏗️ SOA Possedute**")

            # Inizializza dati SOA in session_state
            if "soa_entries" not in st.session_state:
                st.session_state.soa_entries = [{"categoria": "", "classifica": "I", "scadenza": ""}]

            soa_to_remove = None
            for i, entry in enumerate(st.session_state.soa_entries):
                col1, col2, col3, col4 = st.columns([2, 1.5, 2, 0.5])
                with col1:
                    cat = st.text_input(f"Categoria", value=entry.get("categoria", ""), key=f"soa_cat_{i}", placeholder="es. OS6", label_visibility="collapsed")
                with col2:
                    cls = st.selectbox(f"Classifica", ["I", "II", "III", "IV", "IV-bis", "V", "VI", "VII", "VIII"], index=["I", "II", "III", "IV", "IV-bis", "V", "VI", "VII", "VIII"].index(entry.get("classifica", "I")) if entry.get("classifica", "I") in ["I", "II", "III", "IV", "IV-bis", "V", "VI", "VII", "VIII"] else 0, key=f"soa_cls_{i}", label_visibility="collapsed")
                with col3:
                    scad = st.text_input(f"Scadenza", value=entry.get("scadenza", ""), key=f"soa_scad_{i}", placeholder="YYYY-MM-DD", label_visibility="collapsed")
                with col4:
                    if st.button("✕", key=f"soa_del_{i}", help="Rimuovi") and len(st.session_state.soa_entries) > 1:
                        soa_to_remove = i

                st.session_state.soa_entries[i] = {"categoria": cat.upper().strip(), "classifica": cls, "scadenza": scad}

            if soa_to_remove is not None:
                st.session_state.soa_entries.pop(soa_to_remove)
                st.rerun()

            if st.button("➕ Aggiungi SOA", use_container_width=True):
                st.session_state.soa_entries.append({"categoria": "", "classifica": "I", "scadenza": ""})
                st.rerun()

            st.markdown("**🏆 Certificazioni Possedute**")
            if "cert_entries" not in st.session_state:
                st.session_state.cert_entries = [{"tipo": "", "scadenza": ""}]

            cert_to_remove = None
            for i, entry in enumerate(st.session_state.cert_entries):
                col1, col2, col3 = st.columns([2.5, 2, 0.5])
                with col1:
                    tipo = st.text_input(f"Tipo", value=entry.get("tipo", ""), key=f"cert_tipo_{i}", placeholder="es. ISO 9001", label_visibility="collapsed")
                with col2:
                    scad = st.text_input(f"Scad.", value=entry.get("scadenza", ""), key=f"cert_scad_{i}", placeholder="YYYY-MM-DD", label_visibility="collapsed")
                with col3:
                    if st.button("✕", key=f"cert_del_{i}", help="Rimuovi") and len(st.session_state.cert_entries) > 1:
                        cert_to_remove = i

                st.session_state.cert_entries[i] = {"tipo": tipo.strip(), "scadenza": scad}

            if cert_to_remove is not None:
                st.session_state.cert_entries.pop(cert_to_remove)
                st.rerun()

            if st.button("➕ Aggiungi Certificazione", use_container_width=True):
                st.session_state.cert_entries.append({"tipo": "", "scadenza": ""})
                st.rerun()

            st.markdown("**🗺️ Regioni Operative**")
            regioni_input = st.text_input(
                "Regioni",
                value=", ".join(st.session_state.get("regioni", [])),
                placeholder="es. Piemonte, Lombardia",
                label_visibility="collapsed",
            )
            regioni = [r.strip() for r in regioni_input.split(",") if r.strip()]
            st.session_state.regioni = regioni

            # Build profile from form
            soa_clean = [e for e in st.session_state.soa_entries if e.get("categoria")]
            cert_clean = [e for e in st.session_state.cert_entries if e.get("tipo")]
            minimal_profile = build_from_form(soa_clean, cert_clean, regioni)

            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")

        # Reset
        if st.session_state.get("card_result"):
            if st.button("🗑️ Nuova analisi", use_container_width=True, type="secondary"):
                st.session_state.card_result = None
                st.session_state.analyzed_file = None
                st.rerun()

        # Info
        st.markdown(
            '<div style="font-size:0.7rem;color:#94a3b8;line-height:1.6;margin-top:0.5rem">'
            'BidPilot MVP · BandoCard<br>'
            'Evidence-first · ✅❌❓ matching<br>'
            f'Advanced mode: {"🔓 ON" if ADVANCED_MODE else "🔒 OFF"}'
            '</div>',
            unsafe_allow_html=True
        )

        return minimal_profile


# ══════════════════════════════════════════════════════
# PIPELINE ANALISI
# ══════════════════════════════════════════════════════

def run_analysis(pdf_path: str, api_key: str, minimal_profile) -> BandoCard:
    """Pipeline completa: PDF → BandoCard."""
    # 1. Parsing (extraction + guardrail)
    parsed = _parse_pdf(pdf_path, api_key=api_key)
    analysis = _analyze(parsed)
    bando = analysis.bando

    # 2. Matching requisiti
    results = evaluate_all(bando, minimal_profile.company)

    # 3. Salva risultato completo per ADVANCED_MODE
    if ADVANCED_MODE:
        st.session_state.full_result = {
            "bando": bando,
            "analysis": analysis,
            "results": results,
        }

    # 4. Costruisci BandoCard
    card = build_bando_card(
        bando=bando,
        results=results,
        soa_profile_empty=not minimal_profile.has_soa_data,
        cert_profile_empty=not minimal_profile.has_cert_data,
    )

    return card


# ══════════════════════════════════════════════════════
# TAB ANALISI
# ══════════════════════════════════════════════════════

def tab_analisi(minimal_profile):
    if not st.session_state.get("api_key"):
        st.markdown("""
        <div class="upload-zone">
          <div class="upload-icon">🔑</div>
          <div class="upload-title">API Key richiesta</div>
          <div class="upload-sub">Inserisci la tua OpenAI API Key nella sidebar per procedere.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    st.markdown("#### 📄 Carica il PDF del bando")

    uploaded = st.file_uploader(
        "Seleziona il PDF del bando",
        type=["pdf"],
        help="PDF con testo selezionabile (non scansionato). Disciplinari, lettere invito, sistemi di qualificazione.",
        label_visibility="collapsed",
    )

    if not uploaded:
        st.markdown("""
        <div class="upload-zone">
          <div class="upload-icon">📂</div>
          <div class="upload-title">Trascina il PDF qui o clicca Sfoglia</div>
          <div class="upload-sub">Disciplinari · Lettere invito · Sistemi di qualificazione · Max 100 pagine</div>
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

    error = False
    with st.spinner("🤖 Estrazione in corso… (30–90 secondi)"):
        os.makedirs("data", exist_ok=True)
        temp_path = f"data/temp_{uploaded.name}"
        try:
            with open(temp_path, "wb") as f:
                f.write(uploaded.getbuffer())

            card = run_analysis(temp_path, st.session_state.api_key, minimal_profile)
            st.session_state.card_result = card
            st.session_state.analyzed_file = uploaded.name

        except Exception as e:
            st.error(f"❌ Errore: {e}")
            if isinstance(e, RuntimeError) and (
                "modulo 'anthropic'" in str(e) or "modulo 'openai'" in str(e)
            ):
                st.info("Suggerimento: attiva il venv corretto e installa le dipendenze con `pip install -r requirements.txt`.")
            else:
                st.exception(e)
            error = True
        finally:
            try:
                os.remove(temp_path)
            except Exception:
                pass

    if not error and st.session_state.get("card_result"):
        st.success("✅ Analisi completata!")
        st.rerun()


# ══════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════

def main():
    for key in ("api_key", "card_result", "analyzed_file", "soa_entries", "cert_entries", "regioni"):
        if key not in st.session_state:
            if key == "soa_entries":
                st.session_state[key] = [{"categoria": "", "classifica": "I", "scadenza": ""}]
            elif key == "cert_entries":
                st.session_state[key] = [{"tipo": "", "scadenza": ""}]
            elif key == "regioni":
                st.session_state[key] = []
            else:
                st.session_state[key] = None

    render_header()
    minimal_profile = sidebar_profile()

    if st.session_state.card_result:
        st.caption(f"📄 Bando analizzato: **{st.session_state.analyzed_file}**")
        render_bando_card(st.session_state.card_result)
        st.markdown("---")
        with st.expander("🔄 Analizza un altro bando"):
            tab_analisi(minimal_profile)
    else:
        tab_analisi(minimal_profile)


if __name__ == "__main__":
    os.makedirs("data/progetti_storici", exist_ok=True)
    os.makedirs("config", exist_ok=True)
    main()