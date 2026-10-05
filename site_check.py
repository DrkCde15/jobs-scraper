"""Pre-flight check: verifica se os job boards do `config.SITES` estao no ar.

Uso:
    python site_check.py                     # Playwright (se instalado), senao HTTP
    python site_check.py --quick             # so HTTP padrao, mais rapido
    python site_check.py --sites linkedin,gupy
    python site_check.py --timeout 10
    python scraper.py --check-sites [--quick]

Retorna exit 0 se todos responderem, 1 caso contrario.
"""
from __future__ import annotations

import argparse
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

import config

try:
    from playwright.sync_api import sync_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    sync_playwright = None
    PLAYWRIGHT_AVAILABLE = False


log = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Trechos tipicos de pagina de bloqueio (WAF/captcha), ja normalizados
# (minusculas, sem acento) para comparar com o HTML em lowercase.
BLOCK_MARKERS = (
    "just a moment",
    "attention required",
    "access denied",
    "access to this page has been denied",
    "cloudflare",
    "captcha",
    "are you a robot",
    "verify you are human",
    "perimeterx",
    "datadome",
)

# Checagem extra: o pipeline depende do DDG para descobrir as vagas.
DDG_CHECK_URL = "https://duckduckgo.com/html/?q=teste"

MAX_BODY_SCAN_CHARS = 200_000
MIN_BODY_CHARS = 200


@dataclass
class SiteResult:
    name: str
    url: str
    ok: bool
    status: int | None
    elapsed_ms: int
    detail: str = ""


def site_homepage_url(clause: str) -> str:
    """Deriva `https://<dominio>` da clausula `site:...` do config."""
    domain = clause.removeprefix("site:").split("/", 1)[0].lower()
    return f"https://{domain}"


def find_block_marker(html: str) -> str:
    lowered = (html or "").lower()
    for marker in BLOCK_MARKERS:
        if marker in lowered:
            return marker
    return ""


def check_via_http(name: str, url: str, timeout_s: float) -> SiteResult:
    started = time.monotonic()
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            status = response.status
            raw = response.read(MAX_BODY_SCAN_CHARS).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return SiteResult(name, url, False, exc.code, _elapsed_ms(started), f"HTTP {exc.code}")
    except Exception as exc:
        return SiteResult(name, url, False, None, _elapsed_ms(started), f"falha de rede: {exc}")
    elapsed_ms = _elapsed_ms(started)
    if status is not None and status >= 400:
        return SiteResult(name, url, False, status, elapsed_ms, f"HTTP {status}")
    marker = find_block_marker(raw)
    if marker:
        return SiteResult(name, url, False, status, elapsed_ms, f"bloqueio detectado ({marker})")
    if len(raw.strip()) < MIN_BODY_CHARS:
        return SiteResult(name, url, False, status, elapsed_ms, "resposta vazia/curta demais")
    return SiteResult(name, url, True, status, elapsed_ms, "OK")


def check_via_playwright(page, name: str, url: str, timeout_ms: int) -> SiteResult:
    started = time.monotonic()
    try:
        response = page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
        status = response.status if response is not None else None
        html = page.content()[:MAX_BODY_SCAN_CHARS]
        title = page.title().strip()[:80]
    except Exception as exc:
        return SiteResult(name, url, False, None, _elapsed_ms(started), f"falha no browser: {exc}")
    elapsed_ms = _elapsed_ms(started)
    if status is not None and status >= 400:
        return SiteResult(name, url, False, status, elapsed_ms, f"HTTP {status}")
    marker = find_block_marker(html)
    if marker:
        return SiteResult(name, url, False, status, elapsed_ms, f"bloqueio detectado ({marker})")
    detail = f"OK ({title})" if title else "OK"
    return SiteResult(name, url, True, status, elapsed_ms, detail)


def run_checks(
    site_names: list[str] | None = None,
    use_playwright: bool = True,
    timeout_s: float = 15,
    include_ddg: bool = True,
) -> list[SiteResult]:
    """Checa os sites habilitados. Retorna um resultado por site."""
    selected = site_names or config.ENABLED_SITES
    targets = [(name, site_homepage_url(config.SITES[name])) for name in selected if name in config.SITES]
    unknown = [name for name in selected if name not in config.SITES]
    for name in unknown:
        log.warning("Site desconhecido ignorado: %s", name)
    if include_ddg:
        targets.append(("duckduckgo", DDG_CHECK_URL))

    results: list[SiteResult] = []
    if use_playwright and PLAYWRIGHT_AVAILABLE:
        results.extend(_run_with_playwright(targets, timeout_s))
    else:
        if use_playwright and not PLAYWRIGHT_AVAILABLE:
            log.warning("Playwright nao instalado; usando HTTP padrao.")
        for name, url in targets:
            results.append(check_via_http(name, url, timeout_s))
    return results


def print_report(results: list[SiteResult]) -> bool:
    """Imprime resumo e retorna True se todos passaram."""
    for result in results:
        status = "OK  " if result.ok else "FAIL"
        code = result.status if result.status is not None else "-"
        print(f"[{status}] {result.name:<12} {result.url} (HTTP {code}, {result.elapsed_ms}ms) {result.detail}")
    failed = [result.name for result in results if not result.ok]
    if failed:
        print(f"\n❌  {len(failed)} site(s) com problema: {', '.join(failed)}")
        return False
    print(f"\n✔  Todos os {len(results)} sites responderam.")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verifica se os job boards estao no ar.")
    parser.add_argument("--quick", action="store_true", help="Usa HTTP padrao em vez do Playwright.")
    parser.add_argument("--sites", default="", help="Ex.: --sites linkedin,gupy (padrao: ENABLED_SITES).")
    parser.add_argument("--timeout", type=float, default=15, help="Timeout por site, em segundos.")
    parser.add_argument("--no-ddg", action="store_true", help="Pula a checagem do DuckDuckGo.")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    site_names = [item.strip() for item in args.sites.split(",") if item.strip()] or None
    results = run_checks(
        site_names,
        use_playwright=not args.quick,
        timeout_s=args.timeout,
        include_ddg=not args.no_ddg,
    )
    return 0 if print_report(results) else 1


def _run_with_playwright(targets: list[tuple[str, str]], timeout_s: float) -> list[SiteResult]:
    results: list[SiteResult] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(user_agent=USER_AGENT, locale="pt-BR")
            page = context.new_page()
            for name, url in targets:
                log.info("🔍  Checando %s (%s)...", name, url)
                results.append(check_via_playwright(page, name, url, int(timeout_s * 1000)))
        finally:
            browser.close()
    return results


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


if __name__ == "__main__":
    raise SystemExit(main())
