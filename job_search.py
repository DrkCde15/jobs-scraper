from __future__ import annotations

import logging
import re
import time
from collections.abc import Iterable, Mapping
from typing import Any

from ddgs import DDGS

import config
from filters import has_known_blocked_age, is_closed_text, is_desired_seniority, is_target_role
from models import Job
from sites import is_supported_job_url, job_site_name, normalize_job_url


log = logging.getLogger(__name__)

DEFAULT_SEARCH_TITLE = "Vaga"

# Pausa curta entre buscas: disparar tudo de uma vez deixa o motor de busca
# devolver erro de limite de taxa no meio da rodada.
QUERY_DELAY_SECONDS = 2.0


def search_all() -> list[Job]:
    """Busca em todas as fontes ligadas e remove URLs repetidas entre elas."""
    jobs = ddg_search()
    jobs.extend(jobspy_search())
    return dedup_jobs(jobs)


def dedup_jobs(jobs: Iterable[Job]) -> list[Job]:
    unique_jobs: list[Job] = []
    seen_urls: set[str] = set()
    for job in jobs:
        key = normalize_job_url(job.get("url", ""))
        if key:
            if key in seen_urls:
                continue
            seen_urls.add(key)
        unique_jobs.append(job)
    return unique_jobs


def ddg_search() -> list[Job]:
    results: list[Job] = []
    seen_urls: set[str] = set()

    queries = build_search_queries()
    with DDGS() as duckduckgo:
        for query in queries:
            results.extend(search_query_jobs(duckduckgo, query, seen_urls))
            time.sleep(QUERY_DELAY_SECONDS)

    log.info("🔎  %d vagas únicas encontradas via DDG", len(results))
    return results


def jobspy_search() -> list[Job]:
    """Busca direta nos job boards via JobSpy (LinkedIn, Indeed, ...).

    O JobSpy devolve descricao e data de publicacao do proprio board, o que
    alimenta os mesmos filtros de senioridade, papel e idade usados no DDG.
    Uma falha por termo (ex.: LinkedIn 429 em burst) vira warning e as
    demais buscas seguem.
    """
    if not config.JOBSPY_ENABLED or not config.JOBSPY_SITES:
        return []

    from jobspy import scrape_jobs

    results: list[Job] = []
    seen_urls: set[str] = set()

    for term in config.JOBSPY_QUERY_STEMS:
        log.info("🔍  JobSpy buscando: %s", term)
        try:
            frame = scrape_jobs(
                site_name=list(config.JOBSPY_SITES),
                search_term=term,
                location=config.JOBSPY_LOCATION,
                is_remote=config.JOBSPY_IS_REMOTE,
                hours_old=config.JOBSPY_HOURS_OLD,
                results_wanted=config.JOBSPY_RESULTS_PER_TERM,
                country_indeed=config.JOBSPY_COUNTRY_INDEED,
                verbose=0,
            )
        except Exception as exc:
            log.warning("Erro no JobSpy ('%s'): %s", term, exc)
            continue

        rows: list[Mapping[str, Any]] = list(frame.to_dict("records") if frame is not None else [])
        hits = [jobspy_hit_to_dict(row) for row in rows]
        jobs = accept_search_hits(hits, seen_urls, require_supported_url=False)
        log.info("✅ JobSpy '%s': %d/%d links aproveitados", term, len(jobs), len(hits))
        results.extend(jobs)
        time.sleep(QUERY_DELAY_SECONDS)

    log.info("🔎  %d vagas únicas encontradas via JobSpy", len(results))
    return results


def jobspy_hit_to_dict(row: Mapping[str, Any]) -> dict[str, str]:
    """JobPost do JobSpy no mesmo shape de hit do DDGS.

    `href/title/body` deixam o hit reaproveitar accept_search_hits e todos
    os filtros sem caminho paralelo. `source` guarda o board de origem
    (indeed/linkedin) porque a URL pode apontar para o site da empresa.
    """
    url = jobspy_text(row.get("job_url_direct")) or jobspy_text(row.get("job_url"))
    parts = [jobspy_text(row.get("description"))]
    posted_age = format_jobspy_posted_age(row.get("date_posted"))
    if posted_age:
        parts.append(posted_age)
    return {
        "href": url,
        "title": jobspy_text(row.get("title")),
        "body": " ".join(part for part in parts if part),
        "source": jobspy_text(row.get("site")),
    }


def jobspy_text(value: object) -> str:
    """Normaliza o valor vindo do pandas: NaN vira string no DDGS, nao URL."""
    if value is None:
        return ""
    if isinstance(value, float) and value != value:  # NaN
        return ""
    return str(value).strip()


def format_jobspy_posted_age(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value != value:  # NaN
        return ""
    if hasattr(value, "strftime"):
        try:
            return f"publicada em {value.strftime('%d/%m/%Y')}"
        except (TypeError, ValueError):
            return ""
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", str(value))
    if not match:
        return ""
    year, month, day = match.groups()
    return f"publicada em {day}/{month}/{year}"


def build_search_queries() -> list[str]:
    # Todos os termos entram na mesma consulta OR: medido em producao, fatiar
    # em lotes de 2 dobrou o numero de buscas (12 -> 22) e CAIU o volume de
    # resultados (32 -> 18), porque cada fatia fica estreita demais e ainda
    # gasta mais cota de rate limit.
    search_terms = " OR ".join(f'"{stem}"' for stem in config.QUERY_STEMS)
    return [
        f"({search_terms}) {site_clause}"
        for site_name in config.JOB_BOARD_SEARCH_SITES
        for site_clause in config.JOB_BOARD_SEARCH_QUERIES[site_name]
    ]


def search_query_jobs(duckduckgo: DDGS, query: str, seen_urls: set[str]) -> list[Job]:
    log.info("🔍  Buscando: %s", query)
    try:
        hits = list(
            duckduckgo.text(
                query,
                backend=config.SEARCH_BACKEND,
                max_results=config.MAX_RESULTS_PER_QUERY,
            )
            or []
        )
    except Exception as exc:
        log.warning("Erro na busca DDG ('%s'): %s", query, exc)
        return []

    jobs = accept_search_hits(hits, seen_urls)
    log.info("✅ Query '%s': %d/%d links aproveitados", query, len(jobs), len(hits))
    return jobs


def accept_search_hits(
    hits: Iterable[Mapping[str, Any]],
    seen_urls: set[str],
    *,
    require_supported_url: bool = True,
) -> list[Job]:
    accepted_jobs: list[Job] = []
    for hit in hits:
        job = parse_search_hit(hit)
        if not is_relevant_search_job(job, require_supported_url=require_supported_url):
            continue

        canonical_job = canonicalize_search_job(job)
        if canonical_job["url"] in seen_urls:
            continue

        seen_urls.add(canonical_job["url"])
        accepted_jobs.append(canonical_job)
    return accepted_jobs


def parse_search_hit(hit: Mapping[str, Any]) -> Job:
    return {
        "url": str(hit.get("href") or "").strip(),
        "title": str(hit.get("title") or DEFAULT_SEARCH_TITLE).strip(),
        "snippet": str(hit.get("body") or "").strip(),
        "source": str(hit.get("source") or "").strip(),
    }


def is_relevant_search_job(job: Job, *, require_supported_url: bool = True) -> bool:
    result_text = f"{job['title']} {job['snippet']}"
    if not job["url"]:
        log.info("descartada (sem url)")
        return False
    # O JobSpy ja veio de um board curado: a URL pode apontar para o
    # proprio site de recrutamento da empresa (inhire, lever, greenhouse),
    # que e onde a candidatura acontece. O DDG, que aceita qualquer host,
    # continua exigindo dominio conhecido.
    if require_supported_url and not is_supported_job_url(job["url"]):
        log.info("descartada (url nao suportada): %s", job["url"])
        return False
    if is_closed_text(result_text):
        log.info("descartada (encerrada): %s", job["url"])
        return False
    if has_known_blocked_age(result_text):
        log.info("descartada (idade): %s", job["url"])
        return False
    if not is_desired_seniority(job["title"], job["snippet"]):
        log.info("descartada (senioridade): %s | %s", job["url"], job["title"][:80])
        return False
    if config.REQUIRE_TARGET_ROLE and not is_target_role(job["title"], job["snippet"]):
        log.info("descartada (papel): %s | %s", job["url"], job["title"][:70])
        return False
    return True


def canonicalize_search_job(job: Job) -> Job:
    return {
        **job,
        "url": normalize_job_url(job["url"]),
        "source": job_site_name(job["url"]) or job.get("source", ""),
    }
