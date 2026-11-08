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
JOB_BOARD_SEARCH_SITES = ("linkedin", "indeed", "infojobs", "glassdoor")
JOB_BOARD_DOMAINS = {
    "linkedin": ("linkedin.com",),
    "indeed": ("indeed.com",),
    "infojobs": ("infojobs.com.br",),
    "glassdoor": ("glassdoor.com", "glassdoor.com.br"),
}
JOB_BOARD_SEARCH_QUERIES = {
    "linkedin": ("site:linkedin.com/jobs/view",),
    "indeed": ("site:br.indeed.com",),
    "infojobs": ("site:infojobs.com.br",),
    "glassdoor": ("site:glassdoor.com", "site:glassdoor.com.br"),
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
QUERY_STEMS = [
    "desenvolvedor junior",
    "dev junior",
    "programador junior",
    "backend junior",
    "frontend junior",
    "full stack junior",
]

MAX_RESULTS_PER_QUERY = 20

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

# --- Empresas remote-friendly -------------------------------
REMOTE_COMPANIES_FILE = os.getenv("REMOTE_COMPANIES_FILE", "empresas_remote.csv")
REMOTE_COMPANY_QUERY_LIMIT = int(os.getenv("REMOTE_COMPANY_QUERY_LIMIT", "8"))
