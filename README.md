# Job Scraper

Busca vagas remotas de nível inicial em tecnologia no Brasil — desenvolvimento,
dados, segurança, QA/testes, infraestrutura/cloud/DevOps, sistemas, bancos de
dados e suporte de TI — valida os anúncios com Playwright e envia as novas
oportunidades por e-mail. As buscas do DuckDuckGo incluem os domínios `WEBSITE`
do arquivo `empresas_remote.csv` e os portais LinkedIn, Indeed, InfoJobs e
Glassdoor. Outros job boards configurados são usados apenas no diagnóstico.

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
`EMAIL_USE_SSL`, `RUN_INTERVAL_MINUTES`, `MAX_JOB_AGE_DAYS`,
`REQUIRE_REMOTE`, `REQUIRE_TARGET_ROLE` e `REMOTE_COMPANY_QUERY_LIMIT` ajustam
o envio, o agendamento e os filtros. `REMOTE_COMPANIES_FILE` pode apontar para
outro CSV com as colunas `NAME`, `WEBSITE` e `REGION`.

Por padrão, são aceitas vagas publicadas nos últimos 180 dias (aproximadamente
seis meses); `MAX_JOB_AGE_DAYS` permite alterar esse limite.

O limite de consultas extras é intencional: cada domínio do CSV gera uma
consulta, e `REMOTE_COMPANY_QUERY_LIMIT` controla quantas são executadas por
ciclo. Somente empresas com região Brazil/Latam entram nessas consultas.

## Testes

```bash
python -m unittest discover -v
```
