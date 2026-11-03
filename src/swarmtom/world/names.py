"""Fictional names. Every organisation, product and person here is invented."""

from __future__ import annotations

import random
from dataclasses import dataclass

CLIENTS = ["Vantrel Diagnostics", "Quorvane Medical", "Belisto Biosensors", "Corrigan-Velt Devices", "Nyssa Lab Systems"]
PRODUCTS = [("GlucoTrace 4", "GT4"), ("SteadyGluc S2", "SG2"), ("VeraSense CGM-7", "VS7"), ("Lumetra G3", "LG3")]
VENDORS = [
    "Corvane Analytics", "Mirelle Data Assurance", "Tessaly QA", "Brandt & Okafor Validation", "Ildra Compliance Labs",
    "Pemberly Audit Systems", "Saro Data Works", "Haldane Quality Partners", "Orrin & Vey Assurance", "Kestova Review Group",
]
CALLSIGNS = ["LEDGER", "MERIDIAN", "OSPREY", "TALLIS", "VANE", "CAIRN", "HALYARD", "SEXTANT", "LUMEN", "ARGUS"]
OPS_LEADS = [
    "Dana Whitcombe", "Priya Raman", "Tomasz Wierzbicki", "Aiko Matsuda", "Femi Adeyemi",
    "Laura Castellanos", "Jonas Lindqvist", "Mei-Ling Chou", "Ruairi Brennan", "Sofia Marchetti",
]
TECHNICIANS = [
    "Hannah Kroll", "Wei Zhang", "Marcus Bell", "Ines Duarte", "Oleg Petrov", "Grace Mensah", "Ravi Kulkarni",
    "Elena Sokolova", "Tunde Bakare", "Chloe Fontaine", "Sami Haddad", "Yuki Tanaka",
]
REGULATOR = "National Medical Device Agency (NMDA)"


@dataclass(frozen=True)
class Cast:
    client: str
    product: str
    product_code: str
    vendors: list[str]
    callsigns: list[str]
    ops_leads: list[str]
    technicians: list[str]


def sample_cast(rng: random.Random, n_agents: int) -> Cast:
    product, code = rng.choice(PRODUCTS)
    return Cast(
        client=rng.choice(CLIENTS),
        product=product,
        product_code=code,
        vendors=rng.sample(VENDORS, n_agents),
        callsigns=rng.sample(CALLSIGNS, n_agents),
        ops_leads=rng.sample(OPS_LEADS, n_agents),
        technicians=rng.sample(TECHNICIANS, 9),
    )
