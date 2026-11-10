# Job Scraper

Busca vagas remotas de nível inicial em tecnologia no Brasil — desenvolvimento,
dados, segurança, QA/testes, infraestrutura/cloud/DevOps, sistemas, bancos de
dados e suporte de TI — valida os anúncios com Playwright e envia as novas
oportunidades por e-mail. As buscas passam pelos job boards configurados —
LinkedIn, InfoJobs, Vagas, Catho, Programathor, GeekHunter, Gupy e Trampos.
Outros boards configurados são usados apenas no diagnóstico.

## Executar localmente

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
python scraper.py --once
```

Para manter o scraper executando e repetir a busca no intervalo configurado:

```bash
python scraper.py
```

O comando `python scraper.py --check-sites` é apenas um diagnóstico dos job
boards e do DuckDuckGo; ele não altera os domínios usados nas buscas de vagas.

## Configuração

Defina as credenciais SMTP no `.env` (ou no ambiente):

```dotenv
EMAIL_SMTP_USER=seu-email@example.com
EMAIL_SMTP_PASSWORD=sua-senha-de-app
EMAIL_FROM=seu-email@example.com
EMAIL_TO=destino@example.com
```

Opcionalmente, `EMAIL_SMTP_HOST`, `EMAIL_SMTP_PORT`, `EMAIL_USE_TLS`,
`EMAIL_USE_SSL`, `RUN_INTERVAL_MINUTES`, `MAX_JOB_AGE_DAYS`, `REQUIRE_REMOTE`
e `REQUIRE_TARGET_ROLE` ajustam o envio, o agendamento e os filtros.

Por padrão, são aceitas vagas publicadas nos últimos 180 dias (aproximadamente
seis meses); `MAX_JOB_AGE_DAYS` permite alterar esse limite.

## Testes

```bash
python -m unittest discover -v
```
