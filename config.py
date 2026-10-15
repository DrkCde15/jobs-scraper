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
JOB_ALERT_TITLE = "Vagas Remotas Administrativas, Operacionais e Financeiras"

# Sites de vagas varridos (nome -> cláusula de domínio para a busca).
SITES = {
    "linkedin": "site:linkedin.com/jobs/view",
    "indeed": "site:br.indeed.com",
    "infojobs": "site:infojobs.com.br",
    "vagas": "site:vagas.com.br",
    "catho": "site:catho.com.br",
    "programathor": "site:programathor.com.br",
    "geekhunter": "site:geekhunter.com.br",
    "gupy": "site:gupy.io",
    "trampos": "site:trampos.co",
}

# Permite restringir os sites via .env, ex.: ENABLED_SITES=linkedin,indeed,infojobs
ENABLED_SITES = [
    item.strip()
    for item in os.getenv("ENABLED_SITES", "").split(",")
    if item.strip()
] or list(SITES)

QUERY_STEMS = [
    # 1. Assistente administrativo.
    "assistente administrativo remoto brasil",
    "auxiliar administrativo remoto brasil",
    "assistente de operacoes remoto brasil",
    # 2. Operacoes / back-office.
    "auxiliar de operacoes remoto brasil",
    "assistente de cadastro remoto brasil",
    "analista de operacoes junior remoto brasil",
    # 3. Assistente de dados / relatorios (ponte admin-dados).
    "assistente de indicadores remoto brasil",
    "assistente de relatorios remoto brasil",
    "auxiliar de bi remoto brasil",
    # 4. Financeiro.
    "auxiliar financeiro remoto brasil",
    "assistente de faturamento remoto brasil",
    "assistente de controladoria remoto brasil",
    # Vagas em ingles publicadas no Brasil.
    "administrative assistant remote brasil",
    "operations assistant remote brasil junior",
    # Aprendiz (porta de entrada).
    "jovem aprendiz administrativo remoto brasil",
    "jovem aprendiz remoto brasil",
]

SEARCH_QUERIES = [
    f"{stem} {SITES[site_name]}"
    for site_name in ENABLED_SITES
    for stem in QUERY_STEMS
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
MAX_JOB_AGE_DAYS = int(os.getenv("MAX_JOB_AGE_DAYS", "7"))
REQUIRE_POSTED_AGE = env_bool("REQUIRE_POSTED_AGE", default=True)

# --- Arquivos de estado -------------------------------------
SEEN_JOBS_FILE = "seen_jobs.json"
LOG_FILE = "scraper.log"

# --- Empresas remote-friendly -------------------------------
REMOTE_COMPANIES_FILE = os.getenv("REMOTE_COMPANIES_FILE", "empresas_remote.csv")
REMOTE_COMPANY_QUERY_LIMIT = int(os.getenv("REMOTE_COMPANY_QUERY_LIMIT", "8"))
