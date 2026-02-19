"""
BidPilot MVP — BandoCard Engine
=================================
Trasforma BandoRequisiti + List[RequirementResult] nella BandoCard MVP.

La BandoCard ha 6 blocchi:
  1. Identità gara
  2. Scadenze (con alert se < 7 giorni)
  3. SOA richieste (con stato ✅❌❓)
  4. Certificazioni richieste (con stato ✅❌❓)
  5. Info operative
  6. Da verificare (ambiguità + dati mancanti)

Regola hard MVP:
  - Se evidence mancante dal bando → "Da verificare"
  - Se dato aziendale mancante → stato = ❓ (mai ❌ per mancanza di info)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple

from src.schemas import BandoRequisiti, RequirementResult, ReqStatus, Severity


# ══════════════════════════════════════════════════════
# DATACLASSES OUTPUT
# ══════════════════════════════════════════════════════

@dataclass
class ScadenzaItem:
    tipo: str
    label: str          # etichetta leggibile
    data: Optional[str]
    ora: Optional[str]
    giorni_mancanti: Optional[int]
    urgente: bool       # True se <= 7 giorni
    scaduta: bool
    evidence: Optional[str]


@dataclass
class ReqItem:
    req_id: str
    name: str
    stato: str          # "ok" | "ko" | "unknown"
    emoji: str          # "✅" | "❌" | "❓"
    message: str
    evidence_quote: Optional[str]
    evidence_page: Optional[int]
    note: Optional[str] = None


@dataclass
class InfoOperativa:
    sopralluogo_obbligatorio: bool
    sopralluogo_note: Optional[str]
    piattaforma: Optional[str]
    piattaforma_spid: bool
    pnrr: bool
    appalto_integrato: bool
    dgue_required: bool
    contributo_anac: str    # "si" | "no" | "da_verificare"
    canale_invio: str


@dataclass
class BandoCard:
    # Blocco 1 — Identità
    oggetto: str
    ente: str
    cig: Optional[str]
    importo: Optional[float]
    importo_evidence: Optional[str]
    tipo_procedura: str
    cpv: Optional[str]
    lotti: int
    is_pnrr: bool

    # Blocco 2 — Scadenze
    scadenze: List[ScadenzaItem]

    # Blocco 3 — SOA
    soa_items: List[ReqItem]
    soa_profile_empty: bool   # True = nessun dato SOA nel profilo → tutto ❓

    # Blocco 4 — Certificazioni
    cert_items: List[ReqItem]
    cert_profile_empty: bool

    # Blocco 5 — Info operative
    info_op: InfoOperativa

    # Blocco 6 — Da verificare
    da_verificare: List[str]    # messaggi testuali ambiguità
    note_avanzate: List[str]    # requisiti SOFT_RISK non critici


# ══════════════════════════════════════════════════════
# BUILDER
# ══════════════════════════════════════════════════════

_TIPO_LABEL = {
    "presentazione_offerta": "Scadenza offerta",
    "presentazione offerta": "Scadenza offerta",
    "offerta": "Scadenza offerta",
    "chiarimenti": "Termine quesiti/chiarimenti",
    "quesiti": "Termine quesiti",
    "sopralluogo": "Sopralluogo obbligatorio",
    "aggiudicazione": "Aggiudicazione prevista",
    "consegna_lavori": "Consegna lavori",
}


def _parse_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(s[:len(fmt)], fmt)
        except Exception:
            pass
    return None


def _giorni_mancanti(data_str: Optional[str]) -> Optional[int]:
    d = _parse_date(data_str)
    if d is None:
        return None
    return (d - datetime.now()).days


def _build_scadenze(bando: BandoRequisiti) -> Tuple[List[ScadenzaItem], List[str]]:
    items = []
    da_verificare = []

    for sc in bando.scadenze:
        label = _TIPO_LABEL.get(sc.tipo.lower(), sc.tipo.replace("_", " ").title())
        giorni = _giorni_mancanti(sc.data)
        scaduta = giorni is not None and giorni < 0
        urgente = giorni is not None and 0 <= giorni <= 7

        if sc.data is None:
            da_verificare.append(f"Data '{label}' non trovata nel documento — verificare manualmente")

        items.append(ScadenzaItem(
            tipo=sc.tipo,
            label=label,
            data=sc.data,
            ora=sc.ora,
            giorni_mancanti=giorni,
            urgente=urgente,
            scaduta=scaduta,
            evidence=sc.evidence,
        ))

    return items, da_verificare


def _result_to_item(r: RequirementResult, force_unknown: bool = False) -> ReqItem:
    """Converte RequirementResult in ReqItem MVP."""
    if force_unknown or r.status == ReqStatus.UNKNOWN:
        stato, emoji = "unknown", "❓"
    elif r.status == ReqStatus.OK:
        stato, emoji = "ok", "✅"
    elif r.status in (ReqStatus.KO, ReqStatus.FIXABLE):
        stato, emoji = "ko", "❌"
    elif r.status == ReqStatus.RISK_FLAG:
        stato, emoji = "unknown", "❓"
    else:
        stato, emoji = "ok", "✅"

    ev_quote, ev_page = None, None
    if r.evidence:
        ev = r.evidence[0]
        ev_quote = ev.quote or None
        ev_page = ev.page or None

    return ReqItem(
        req_id=r.req_id,
        name=r.name,
        stato=stato,
        emoji=emoji,
        message=r.user_message,
        evidence_quote=ev_quote,
        evidence_page=ev_page,
    )


def _build_soa_items(
    bando: BandoRequisiti,
    results: List[RequirementResult],
    soa_profile_empty: bool,
) -> Tuple[List[ReqItem], List[str]]:
    """
    Costruisce la lista SOA per la BandoCard.

    Se soa_profile_empty=True: tutte le SOA tornano ❓
    (non abbiamo dati per valutare, non ❌ per mancanza di info profilo)
    """
    soa_results = [
        r for r in results
        if r.category == "qualification"
        and (r.req_id.startswith("R25") or r.req_id.startswith("R26_") or r.req_id.startswith("C5_"))
        and r.status != ReqStatus.PREMIANTE
    ]

    da_verificare = []
    items = []

    # Se non ci sono SOA nel bando
    if not bando.soa_richieste:
        imp = bando.importo_lavori or bando.importo_base_gara
        if imp and imp < 150_000:
            items.append(ReqItem(
                req_id="SOA_NA",
                name="SOA non richiesta",
                stato="ok", emoji="✅",
                message=f"Importo {imp:,.0f}€ < 150.000€: attestazione SOA non applicabile.",
                evidence_quote=bando.importo_evidence,
                evidence_page=None,
            ))
        else:
            da_verificare.append("Categorie SOA non identificate nel documento — verificare manualmente")
        return items, da_verificare

    # Una entry per ogni SOA richiesta nel bando
    for soa in bando.soa_richieste:
        cat = soa.categoria
        # Trova il risultato matching
        matching = next(
            (r for r in soa_results if cat.upper() in r.name.upper() or cat.upper() in r.req_id.upper()),
            None
        )

        if matching is None:
            stato, emoji = ("unknown", "❓")
            message = f"SOA {cat} cl.{soa.classifica} — verifica nel profilo"
            ev_quote = soa.evidence
            ev_page = None
        else:
            item = _result_to_item(matching, force_unknown=soa_profile_empty)
            stato, emoji = item.stato, item.emoji
            message = item.message
            ev_quote = item.evidence_quote or soa.evidence
            ev_page = item.evidence_page

        label_prev = " (prevalente)" if soa.prevalente else ""
        label_scorp = " (scorporabile)" if soa.is_scorporabile and not soa.prevalente else ""

        items.append(ReqItem(
            req_id=f"SOA_{cat}",
            name=f"{cat} cl.{soa.classifica}{label_prev}{label_scorp}",
            stato=stato,
            emoji=emoji,
            message=message,
            evidence_quote=ev_quote,
            evidence_page=ev_page,
            note=soa.descrizione or None,
        ))

    return items, da_verificare


def _build_cert_items(
    bando: BandoRequisiti,
    results: List[RequirementResult],
    cert_profile_empty: bool,
) -> Tuple[List[ReqItem], List[str]]:
    """
    Costruisce la lista certificazioni per la BandoCard.
    Se cert_profile_empty=True: tutte le cert tornano ❓
    """
    cert_results = {
        r.req_id: r for r in results
        if r.category == "certification"
    }

    da_verificare = []
    items = []

    if not bando.certificazioni_richieste:
        return items, da_verificare

    for i, cert_req in enumerate(bando.certificazioni_richieste):
        req_id = f"CERT_{i+1}"
        r = cert_results.get(req_id)

        if r is None:
            items.append(ReqItem(
                req_id=req_id,
                name=cert_req,
                stato="unknown", emoji="❓",
                message=f"{cert_req} — dato non disponibile nel profilo",
                evidence_quote=None,
                evidence_page=None,
            ))
        else:
            item = _result_to_item(r, force_unknown=cert_profile_empty)
            items.append(ReqItem(
                req_id=req_id,
                name=cert_req,
                stato=item.stato,
                emoji=item.emoji,
                message=item.message,
                evidence_quote=item.evidence_quote,
                evidence_page=item.evidence_page,
            ))

    return items, da_verificare


def _build_info_operative(bando: BandoRequisiti) -> Tuple[InfoOperativa, List[str]]:
    da_verificare = []

    # Contributo ANAC
    if bando.anac_contributo_richiesto == "yes":
        contributo = "si"
    elif bando.anac_contributo_richiesto == "no":
        contributo = "no"
    else:
        if bando.codice_cig:
            da_verificare.append(
                f"Contributo ANAC: CIG presente ({bando.codice_cig}) ma contributo non esplicitato nel documento"
            )
        contributo = "da_verificare"

    if bando.piattaforma_gara is None:
        da_verificare.append("Piattaforma/canale di invio non identificati — verificare nel documento")

    return InfoOperativa(
        sopralluogo_obbligatorio=bando.sopralluogo_obbligatorio,
        sopralluogo_note=bando.sopralluogo_evidence if bando.sopralluogo_obbligatorio else None,
        piattaforma=bando.piattaforma_gara,
        piattaforma_spid=bando.piattaforma_spid_required,
        pnrr=bando.is_pnrr,
        appalto_integrato=bando.appalto_integrato,
        dgue_required=bando.dgue_required,
        contributo_anac=contributo,
        canale_invio=bando.canale_invio,
    ), da_verificare


def _collect_da_verificare(
    results: List[RequirementResult],
    bando: BandoRequisiti,
) -> Tuple[List[str], List[str]]:
    """
    Raccoglie UNKNOWN HARD_KO come "Da verificare"
    e SOFT_RISK come note avanzate.
    """
    skip_categories = {"qualification", "certification"}  # già gestite
    skip_prefixes = {"R25", "R26_", "C5_", "CERT_", "SOA_"}

    da_verificare = []
    note_avanzate = []

    for r in results:
        if r.category in skip_categories:
            continue
        if any(r.req_id.startswith(p) for p in skip_prefixes):
            continue
        if r.status == ReqStatus.PREMIANTE:
            continue

        if r.status == ReqStatus.UNKNOWN and r.severity == Severity.HARD_KO:
            da_verificare.append(f"[{r.req_id}] {r.user_message}")
        elif r.status == ReqStatus.RISK_FLAG:
            note_avanzate.append(f"[{r.req_id}] {r.user_message}")
        elif r.status in (ReqStatus.KO, ReqStatus.FIXABLE) and r.severity == Severity.HARD_KO:
            da_verificare.append(f"[{r.req_id}] {r.user_message}")

    # Importo mancante
    if bando.importo_lavori is None and bando.importo_base_gara is None:
        da_verificare.append("Importo base gara non trovato — verificare manualmente nel documento")

    return da_verificare, note_avanzate


# ══════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════

def build_bando_card(
    bando: BandoRequisiti,
    results: List[RequirementResult],
    soa_profile_empty: bool = False,
    cert_profile_empty: bool = False,
) -> BandoCard:
    """
    Costruisce la BandoCard MVP da BandoRequisiti + RequirementResults.

    Args:
        bando: dati estratti dal PDF
        results: output dell'engine di matching
        soa_profile_empty: True se l'utente non ha inserito SOA nel profilo
        cert_profile_empty: True se l'utente non ha inserito certificazioni
    """
    # Blocco 2 — Scadenze
    scadenze, dv_scad = _build_scadenze(bando)

    # Blocco 3 — SOA
    soa_items, dv_soa = _build_soa_items(bando, results, soa_profile_empty)

    # Blocco 4 — Certificazioni
    cert_items, dv_cert = _build_cert_items(bando, results, cert_profile_empty)

    # Blocco 5 — Info operative
    info_op, dv_info = _build_info_operative(bando)

    # Blocco 6 — Da verificare
    dv_general, note_avanzate = _collect_da_verificare(results, bando)

    da_verificare = dv_scad + dv_soa + dv_cert + dv_info + dv_general

    return BandoCard(
        # Blocco 1
        oggetto=bando.oggetto_appalto,
        ente=bando.stazione_appaltante,
        cig=bando.codice_cig,
        importo=bando.importo_lavori or bando.importo_base_gara,
        importo_evidence=bando.importo_evidence,
        tipo_procedura=bando.tipo_procedura or bando.procedure_family,
        cpv=bando.cpv,
        lotti=bando.lotti,
        is_pnrr=bando.is_pnrr,

        # Blocco 2
        scadenze=scadenze,

        # Blocco 3
        soa_items=soa_items,
        soa_profile_empty=soa_profile_empty,

        # Blocco 4
        cert_items=cert_items,
        cert_profile_empty=cert_profile_empty,

        # Blocco 5
        info_op=info_op,

        # Blocco 6
        da_verificare=da_verificare,
        note_avanzate=note_avanzate,
    )
