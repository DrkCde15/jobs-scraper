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
JOB_ALERT_TITLE = "Vagas Remotas de Tecnologia para Nível Inicial"

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

QUERY_STEMS = [
    "desenvolvedor de software junior remoto brasil",
    "software developer junior remote brasil",
    "programador junior remoto brasil",
    "engenheiro de software junior remoto brasil",
    "backend developer junior remoto brasil",
    "back-end developer junior remoto brasil",
    "desenvolvedor backend junior remoto brasil",
    "frontend developer junior remoto brasil",
    "front-end developer junior remoto brasil",
    "desenvolvedor frontend junior remoto brasil",
    "full stack developer junior remoto brasil",
    "desenvolvedor full stack junior remoto brasil",
    "desenvolvedor web junior remoto brasil",
    "desenvolvedor mobile junior remoto brasil",
    "android developer junior remoto brasil",
    "ios developer junior remoto brasil",
    "analista de dados junior remoto brasil",
    "data analyst junior remote brasil",
    "data engineer junior remoto brasil",
    "engenheiro de dados junior remoto brasil",
    "data scientist junior remote brasil",
    "cientista de dados junior remoto brasil",
    "analista de business intelligence junior remoto brasil",
    "bi analyst junior remote brasil",
    "machine learning junior engineer remote brasil",
    "qa analyst junior remoto brasil",
    "analista de testes junior remoto brasil",
    "software tester junior remote brasil",
    "qa automation junior remote brasil",
    "test automation engineer junior remote brasil",
    "sdet junior remote brasil",
    "analista de qualidade de software junior remoto brasil",
    "analista de seguranca da informacao junior remoto brasil",
    "cybersecurity analyst junior remote brasil",
    "information security analyst junior remote brasil",
    "soc analyst junior remote brasil",
    "devops engineer junior remoto brasil",
    "cloud engineer junior remoto brasil",
    "site reliability engineer junior remote brasil",
    "platform engineer junior remote brasil",
    "analista de infraestrutura junior remoto brasil",
    "database administrator junior remote brasil",
    "database analyst junior remoto brasil",
    "analista de sistemas junior remoto brasil",
    "analista de ti junior remoto brasil",
    "technical support analyst junior remote brasil",
    "suporte tecnico de ti junior remoto brasil",
    "help desk analyst junior remote brasil",
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
REQUIRE_APPLY_EVIDENCE = env_bool("REQUIRE_APPLY_EVIDENCE", default=True)
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
