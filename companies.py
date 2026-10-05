"""Base de empresas remote-friendly a partir de `empresas_remote.csv`.

O CSV tem colunas NAME,WEBSITE,REGION e mistura formatos de WEBSITE
(dominio puro, URL completa, subpath). Este modulo normaliza tudo e
expoe lookup por nome da empresa + geracao limitada de queries extras.
"""
from __future__ import annotations

import csv
import logging
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from text_utils import normalize_text, normalize_whitespace

log = logging.getLogger(__name__)

CSV_COLUMNS = ("NAME", "WEBSITE", "REGION")

# So gera queries extras para regioes com afinidade Brasil/Latam.
# "Worldwide" e "USA/Europe" ficam de fora para nao explodir o DDG
# (241 empresas x N queries = ban certo).
QUERYABLE_REGION_MARKERS = (
    "brazil",
    "latin america",
    "latam",
    "brasil",
)


def normalize_company_name(name: str) -> str:
    return normalize_whitespace(normalize_text(name or ""))


def domain_from_website(website: str) -> str:
    raw = (website or "").strip()
    if not raw:
        return ""
    # Aceita "algorand.com" sem scheme.
    if "://" not in raw:
        raw = "//" + raw
    try:
        host = (urlsplit(raw).netloc or "").lower()
    except ValueError:
        host = ""
    if not host:
        # Fallback: pega primeiro segmento do path ("crunchbase.com/organization/...")
        host = raw.lstrip("/").split("/", 1)[0].lower()
    if host.startswith("www."):
        host = host[4:]
    return host.strip()


def resolve_csv_path(configured: str = "empresas_remote.csv") -> Path:
    return Path(configured)


@lru_cache(maxsize=1)
def load_remote_companies(csv_path: str = "empresas_remote.csv") -> dict[str, dict[str, str]]:
    """Carrega CSV uma vez. Chave = nome normalizado. Tolerante a falta do arquivo."""
    path = resolve_csv_path(csv_path)
    if not path.exists():
        log.warning("Arquivo de empresas remotas nao encontrado: %s", path)
        return {}
    try:
        with path.open(encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            companies: dict[str, dict[str, str]] = {}
            for row in reader or []:
                name = (row.get("NAME") or "").strip()
                if not name:
                    continue
                key = normalize_company_name(name)
                if not key or key in companies:
                    continue
                website = (row.get("WEBSITE") or "").strip()
                companies[key] = {
                    "name": name,
                    "website": website,
                    "domain": domain_from_website(website),
                    "region": (row.get("REGION") or "").strip(),
                }
    except OSError as exc:
        log.warning("Nao foi possivel ler %s: %s", path, exc)
        return {}
    log.info("📇  %d empresas remote-friendly carregadas de %s", len(companies), path)
    return companies


def find_remote_company(company_name: str, csv_path: str = "empresas_remote.csv") -> dict[str, str] | None:
    """Match exato por nome normalizado. Retorna None se nao for remote-friendly."""
    key = normalize_company_name(company_name)
    if not key:
        return None
    return load_remote_companies(csv_path).get(key)


def annotate_job(job: dict[str, str], csv_path: str = "empresas_remote.csv") -> dict[str, str]:
    """Adiciona `remote_region`/`careers_url` quando a company esta no CSV."""
    match = find_remote_company(job.get("company", ""), csv_path)
    if not match:
        return job
    return {
        **job,
        "remote_friendly": "sim",
        "remote_region": match["region"],
        "careers_url": match["website"],
    }


def build_company_queries(
    csv_path: str = "empresas_remote.csv",
    limit: int = 8,
) -> list[str]:
    """Gera no maximo `limit` queries extras, 1 por empresa BR/Latam.

    Mantem o volume baixo de proposito: cada query custa 1 chamada DDG
    + validacoes Playwright por resultado.
    """
    if limit <= 0:
        return []
    companies = load_remote_companies(csv_path).values()
    queries: list[str] = []
    for company in companies:
        region = normalize_text(company["region"])
        if not any(marker in region for marker in QUERYABLE_REGION_MARKERS):
            continue
        queries.append(f'"{company["name"]}" dados junior OR trainee brasil')
        if len(queries) >= limit:
            break
    return queries


def clear_cache() -> None:
    load_remote_companies.cache_clear()
