# ============================================================
#  config.py - configuracao do scraper
# ============================================================
from pathlib import Path
import os
import re

from dotenv import load_dotenv


# Mesmo padrao do freela-scraper: aceita .env local e data/.env.
load_dotenv()
load_dotenv(Path("data") / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def parse_email_list(value: str | None) -> list[str]:
    return [
        item.strip()
        for item in re.split(r"[,;\n]+", value or "")
        if item.strip()
    ]


# --- Busca ---------------------------------------------------
JOB_ALERT_TITLE = "Vagas de Desenvolvedor Júnior Remoto"

# Job boards disponíveis para diagnóstico.
SITES = {
    "linkedin": "site:linkedin.com/jobs/view",
    "indeed": "site:br.indeed.com",
    "infojobs": "site:infojobs.com.br",
    "glassdoor": "site:glassdoor.com",
    "vagas": "site:vagas.com.br",
    "catho": "site:catho.com.br",
    "programathor": "site:programathor.com.br",
    "geekhunter": "site:geekhunter.com.br",
    "gupy": "site:gupy.io",
    "trampos": "site:trampos.co",
}

# Portais usados nas buscas de vagas, além dos domínios do CSV.
# Medido em producao (2026-11-08, 2 rodadas com busca ok):
#   linkedin 26 resultados em 6 queries, infojobs 7 em 6;
#   indeed 0 em 9, glassdoor 1 em 6, e o CSV 1 em 14.
# Por isso indeed e glassdoor sao de fora, e o CSV usa poucas queries.
# Os boards brasileiros do SITES entram para dar oferta local.
JOB_BOARD_SEARCH_SITES = (
    "linkedin",
    "infojobs",
    "vagas",
    "catho",
    "programathor",
    "geekhunter",
    "gupy",
    "trampos",
)
JOB_BOARD_DOMAINS = {
    "linkedin": ("linkedin.com",),
    "infojobs": ("infojobs.com.br",),
    "vagas": ("vagas.com.br",),
    "catho": ("catho.com.br",),
    "programathor": ("programathor.com.br",),
    "geekhunter": ("geekhunter.com.br",),
    "gupy": ("gupy.io",),
    "trampos": ("trampos.co",),
}
JOB_BOARD_SEARCH_QUERIES = {
    "linkedin": ("site:linkedin.com/jobs/view",),
    "infojobs": ("site:infojobs.com.br",),
    "vagas": ("site:vagas.com.br",),
    "catho": ("site:catho.com.br",),
    "programathor": ("site:programathor.com.br",),
    "geekhunter": ("site:geekhunter.com.br",),
    "gupy": ("site:gupy.io",),
    "trampos": ("site:trampos.co",),
}

# Sites verificados pelo comando --check-sites.
ENABLED_SITES = [
    item.strip()
    for item in os.getenv("ENABLED_SITES", "").split(",")
    if item.strip()
] or list(SITES)

# Mantemos poucos termos e curtos: uma lista longa com OR vira uma consulta
# de milhares de caracteres e os motores de busca devolvem erro em vez de
# resultados. Medido em producao, 40 termos -> 0 resultados em todas as buscas.
# Escopo: somente vagas de Python (junior/entry).
QUERY_STEMS = [
    "desenvolvedor python",
    "python junior",
    "python developer",
    "engenheiro de software python",
]

MAX_RESULTS_PER_QUERY = 20

# Backends de busca do ddgs. O padrao do ddgs ("auto") dispara ~8 requisicoes
# por query em 7 motores, e medido em producao (2026-11-08) no runner do
# Actions so o Yahoo devolvia pagina de busca real:
#   brave 429 e mojeek 403 em 100% das chamadas, startpage captcha-block,
#   wikipedia e grokipedia sao typeahead de 1 resultado (nunca devolvem vaga),
#   html.duckduckgo.com 202 em todas.
# Com "yahoo" a rodada faz 1 requisicao por query em vez de 8, o que reduz a
# pressao de rate limit sem perder nenhum resultado observado.
SEARCH_BACKEND = os.getenv("SEARCH_BACKEND", "yahoo")

# --- E-mail de envio ----------------------------------------
SMTP_HOST = os.getenv("EMAIL_SMTP_HOST") or os.getenv("SMTP_HOST") or "smtp.gmail.com"
SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT") or os.getenv("SMTP_PORT") or "587")
SMTP_USER = os.getenv("EMAIL_SMTP_USER") or os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("EMAIL_SMTP_PASSWORD") or os.getenv("SMTP_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM") or os.getenv("SMTP_FROM") or SMTP_USER
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", default=env_bool("SMTP_USE_SSL", default=False))
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", default=env_bool("SMTP_USE_TLS", default=not EMAIL_USE_SSL))

# --- E-mail de destino --------------------------------------
TO_EMAILS = parse_email_list(
    os.getenv("EMAIL_TO") or os.getenv("TO_EMAILS") or os.getenv("TO_EMAIL")
)

# --- Agendamento local --------------------------------------
RUN_INTERVAL_MINUTES = int(os.getenv("RUN_INTERVAL_MINUTES", "360"))

# --- Validacao de disponibilidade ---------------------------
# Mantemos True por padrao para evitar enviar vagas que o LinkedIn ja fechou.
REQUIRE_PLAYWRIGHT_VALIDATION = env_bool("REQUIRE_PLAYWRIGHT_VALIDATION", default=True)
# Desligado por padrao: sem login o LinkedIn troca o botao de candidatura por
# um link de "Entrar", entao toda vaga aberta era lida como encerrada (medido
# em producao, bloqueou ate vaga de Brasilia). Quem quiser a checagem de volta
# pode ligar por env, sabendo que ela so e confiavel com sessao autenticada.
# A deteccao de vaga fechada continua ativa pelo texto da propria pagina.
REQUIRE_APPLY_EVIDENCE = env_bool("REQUIRE_APPLY_EVIDENCE", default=False)
# Apenas vagas remotas (presencial e hibrido sao descartados).
REQUIRE_REMOTE = env_bool("REQUIRE_REMOTE", default=True)
REQUIRE_TARGET_ROLE = env_bool("REQUIRE_TARGET_ROLE", default=True)

# --- Filtro de idade de vagas (dias) ---------------------------
MAX_JOB_AGE_DAYS = int(os.getenv("MAX_JOB_AGE_DAYS", "180"))
REQUIRE_POSTED_AGE = env_bool("REQUIRE_POSTED_AGE", default=True)

# --- Arquivos de estado -------------------------------------
SEEN_JOBS_FILE = "seen_jobs.json"
LOG_FILE = "scraper.log"
