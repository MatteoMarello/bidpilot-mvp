"""
BidPilot MVP — Profile Builder
================================
Costruisce un CompanyProfile dal form minimo (SOA + Certificazioni + Regioni).

Principio MVP:
  - Dati non forniti → default "unknown" che fanno tornare UNKNOWN dall'engine, mai KO.
  - I flag `has_soa_data` e `has_cert_data` servono alla BandoCard per distinguere
    "dato mancante nel profilo" (❓ per mancanza di info) da
    "dato presente ma non coperto" (❌ lacuna reale).
"""
from __future__ import annotations
from datetime import date
from typing import List, Optional

from src.schemas import (
    CompanyProfile, LegalRepresentative, CameralRegistration,
    SOAAttestation, Certification
)


class MinimalProfile:
    """Wrapper around CompanyProfile che porta flag di completezza dati."""

    def __init__(
        self,
        company: CompanyProfile,
        has_soa_data: bool,
        has_cert_data: bool,
        has_region_data: bool,
    ):
        self.company = company
        self.has_soa_data = has_soa_data
        self.has_cert_data = has_cert_data
        self.has_region_data = has_region_data


def build_from_form(
    soa_entries: List[dict],    # [{"categoria": "OS6", "classifica": "III", "scadenza": "2027-04-20"}, ...]
    cert_entries: List[dict],   # [{"tipo": "ISO 9001", "scadenza": "2026-03-15"}, ...]
    regioni: List[str],         # ["Piemonte", "Lombardia"]
    nome_azienda: str = "Azienda",
) -> MinimalProfile:
    """
    Costruisce MinimalProfile dal form minimo.

    Regole default (MVP):
      - legal_representative: firma digitale = True, poteri = available
        → non genera KO su R04 (firma digitale), che sarebbe fuorviante.
      - cameral_registration: iscritta = True, coerenza = unknown
        → R18 torna UNKNOWN (da verificare), non OK né KO.
      - Nessun fatturato, nessuna referenza → R20, R21 tornano UNKNOWN.
      - Nessun dato BIM, PPP, patente → engine salta quei check o torna UNKNOWN.
    """
    # SOA
    soa_attestations = []
    for entry in soa_entries:
        cat = entry.get("categoria", "").strip().upper()
        cls = entry.get("classifica", "").strip().upper()
        scad = entry.get("scadenza", "") or _default_expiry()
        if cat and cls:
            soa_attestations.append(SOAAttestation(
                category=cat,
                soa_class=cls,
                expiry_date=scad,
            ))

    # Certificazioni
    certifications = []
    for entry in cert_entries:
        tipo = entry.get("tipo", "").strip()
        scad = entry.get("scadenza", "") or _default_expiry()
        if tipo:
            certifications.append(Certification(
                cert_type=tipo,
                valid=True,
                expiry_date=scad,
            ))

    company = CompanyProfile(
        legal_name=nome_azienda,

        # Default "sicuri" per non generare KO fuorvianti su dati non richiesti
        legal_representative=LegalRepresentative(
            name="",
            role="Legale Rappresentante",
            has_digital_signature=True,          # assume disponibile
            signing_powers_proof="available",    # assume disponibile
        ),
        cameral_registration=CameralRegistration(
            is_registered=True,
            coherence_with_tender_object="unknown",  # → R18 = UNKNOWN, non KO
        ),

        soa_attestations=soa_attestations,
        certifications=certifications,
        operating_regions=regioni,

        # Dati finanziari assenti → R20, R21 = UNKNOWN
        turnover_by_year=[],
        similar_works=[],

        # Partecipazione aperta → R10 = OK
        willing_rti=True,
        willing_avvalimento=True,
        willing_subcontract=True,

        # BIM / PPP / Patente → non valutati senza dati
        has_bim_experience=False,
        bim_experience_count=0,
        has_credit_license="unknown",

        # Default sicuri per altri campi
        bank_references_available="unknown",
        cel_records_available="unknown",
        external_designers_available="unknown",
        deposited_statements_count=0,
    )

    return MinimalProfile(
        company=company,
        has_soa_data=len(soa_attestations) > 0,
        has_cert_data=len(certifications) > 0,
        has_region_data=len(regioni) > 0,
    )


def build_from_json(profilo_dict: dict) -> MinimalProfile:
    """
    Costruisce MinimalProfile da un JSON profilo completo (es. profilo_azienda.json).
    Usato come fallback quando esiste già un profilo salvato.
    """
    # SOA
    soa_attestations = [
        SOAAttestation(
            category=s.get("categoria", ""),
            soa_class=s.get("classifica", ""),
            expiry_date=s.get("scadenza", _default_expiry()),
            issue_date=s.get("data_emissione", ""),
        )
        for s in profilo_dict.get("soa_possedute", [])
        if s.get("categoria") and s.get("classifica")
    ]

    certifications = [
        Certification(
            cert_type=c.get("tipo", ""),
            valid=True,
            expiry_date=c.get("scadenza", _default_expiry()),
        )
        for c in profilo_dict.get("certificazioni", [])
        if c.get("tipo") and c.get("tipo", "").upper() != "SOA"
    ]

    # Fatturato
    from src.schemas import TurnoverEntry
    turnover = [
        TurnoverEntry(year=int(year), amount_eur=float(data.get("totale", 0)))
        for year, data in profilo_dict.get("fatturato", {}).items()
        if isinstance(data, dict) and data.get("totale")
    ]

    # Opere analoghe
    from src.schemas import SimilarWork
    opere = [
        SimilarWork(
            title=op.get("titolo", ""),
            year=op.get("anno", 0),
            amount_eur=float(op.get("importo", 0)),
            categories=op.get("categorie", []),
            client=op.get("committente", ""),
        )
        for op in profilo_dict.get("opere_analoghe", [])
    ]

    # Figure professionali / progettisti
    from src.schemas import Designer
    design_team = [
        Designer(
            name=p.get("nome", ""),
            profession=p.get("professione", ""),
            order_registration=p.get("albo", "unknown"),
            license_date=p.get("data_abilitazione", ""),
            young_professional=p.get("giovane_professionista", "unknown"),
        )
        for p in profilo_dict.get("progettisti", [])
    ]

    legal_rep_data = profilo_dict.get("legale_rappresentante", {})
    legal_rep = LegalRepresentative(
        name=legal_rep_data.get("nome", ""),
        role=legal_rep_data.get("ruolo", "Legale Rappresentante"),
        has_digital_signature=legal_rep_data.get("firma_digitale", True),
        signing_powers_proof=legal_rep_data.get("poteri_firma", "available"),
    )

    cciaa = profilo_dict.get("cciaa", {})
    cam_reg = CameralRegistration(
        is_registered=cciaa.get("iscritta", True),
        rea_number=cciaa.get("rea", ""),
        ateco_codes=cciaa.get("ateco", []),
        coherence_with_tender_object="unknown",
    )

    part = profilo_dict.get("partecipazione", {})

    company = CompanyProfile(
        legal_name=profilo_dict.get("nome_azienda", ""),
        registered_office=profilo_dict.get("sede", ""),
        legal_representative=legal_rep,
        cameral_registration=cam_reg,
        soa_attestations=soa_attestations,
        certifications=certifications,
        operating_regions=profilo_dict.get("aree_geografiche", []),
        turnover_by_year=turnover,
        similar_works=opere,
        design_team=design_team,
        has_inhouse_design=not profilo_dict.get("progettazione_interna", False),
        external_designers_available="yes" if design_team else "unknown",
        willing_rti=part.get("rti", True),
        willing_avvalimento=part.get("avvalimento", True),
        willing_subcontract=part.get("subappalto", True),
        ccnl_applied=profilo_dict.get("ccnl_applicato", ""),
        has_credit_license=profilo_dict.get("patente_crediti", "unknown"),
        deposited_statements_count=profilo_dict.get("bilanci_depositati", 0),
        has_bim_experience=False,
        bim_experience_count=0,
        bank_references_available="unknown",
        cel_records_available="unknown",
    )

    return MinimalProfile(
        company=company,
        has_soa_data=len(soa_attestations) > 0,
        has_cert_data=len(certifications) > 0,
        has_region_data=len(profilo_dict.get("aree_geografiche", [])) > 0,
    )


def _default_expiry() -> str:
    """Scadenza di default: 3 anni da oggi (safe default)."""
    d = date.today()
    return f"{d.year + 3}-{d.month:02d}-{d.day:02d}"
