import tempfile
import unittest
from pathlib import Path
from unittest import mock

import companies
import config
import job_search
from job_search import build_search_queries
from sites import is_supported_job_url, job_site_name


class CsvSearchScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.csv_path = Path(self.temp_dir.name) / "companies.csv"
        self.csv_path.write_text(
            "NAME,WEBSITE,REGION\n"
            "Worldwide Co,worldwide.example,Worldwide\n"
            "Latam Co,careers.latam.example,Latin America (Remote)\n"
            "Brazil Co,brazil.example,Brazil\n",
            encoding="utf-8",
        )
        companies.clear_cache()
        self.config_patch = mock.patch.object(config, "REMOTE_COMPANIES_FILE", str(self.csv_path))
        self.config_patch.start()

    def tearDown(self):
        self.config_patch.stop()
        companies.clear_cache()
        self.temp_dir.cleanup()

    def test_queries_are_limited_to_csv_company_domains(self):
        queries = companies.build_company_queries(str(self.csv_path), limit=8)

        self.assertEqual(len(queries), 2)
        self.assertIn("site:careers.latam.example", queries[0])
        self.assertIn("site:brazil.example", queries[1])
        self.assertTrue(all("site:linkedin.com" not in query for query in queries))

    def board_queries_and_company_queries(self):
        queries = build_search_queries()
        company_queries = companies.build_company_queries(
            config.REMOTE_COMPANIES_FILE, config.REMOTE_COMPANY_QUERY_LIMIT
        )
        return queries[: len(queries) - len(company_queries)], company_queries

    def test_search_queries_include_the_requested_job_boards(self):
        board_queries, _ = self.board_queries_and_company_queries()

        self.assertTrue(board_queries)
        for site_name in config.JOB_BOARD_SEARCH_SITES:
            with self.subTest(site=site_name):
                for clause in config.JOB_BOARD_SEARCH_QUERIES[site_name]:
                    self.assertTrue(any(clause in query for query in board_queries))

    def test_job_board_queries_come_before_csv_company_queries(self):
        queries = build_search_queries()
        _, company_queries = self.board_queries_and_company_queries()
        board_count = len(queries) - len(company_queries)

        self.assertTrue(company_queries)
        self.assertEqual(queries[board_count:], company_queries)

    def test_search_queries_stay_short_enough_for_search_engines(self):
        # Regressao do bug original: 40 termos em OR viravam uma consulta de
        # ~1800 caracteres e os motores devolviam erro em vez de resultados.
        for query in build_search_queries():
            with self.subTest(query=query[:60]):
                self.assertLessEqual(len(query), 200)

    def test_board_searches_are_not_split_into_extra_queries(self):
        # Fatiar os termos em lotes dobrou as buscas (12 -> 22) e derrubou o
        # volume de resultados (32 -> 18): cada fatia fica estreita e ainda
        # gasta mais cota de rate limit. Um board = uma consulta.
        expected_board_queries = sum(
            len(clauses) for clauses in config.JOB_BOARD_SEARCH_QUERIES.values()
        )
        board_queries, _ = self.board_queries_and_company_queries()
        self.assertEqual(len(board_queries), expected_board_queries)

    def test_search_query_passes_the_configured_backend(self):
        # O padrao do ddgs dispara ~8 requisicoes por query em motores que
        # nao funcionam no runner (brave 429, mojeek 403, typeahead sem
        # vaga). Sem o backend configurado a rodada volta a estourar o
        # rate limit com requisicoes que nao trazem resultado nenhum.
        engine = mock.Mock()
        engine.text.return_value = []

        job_search.search_query_jobs(engine, '("dev junior") site:linkedin.com/jobs/view', set())

        engine.text.assert_called_once()
        self.assertEqual(engine.text.call_args.kwargs["backend"], config.SEARCH_BACKEND)
        self.assertEqual(engine.text.call_args.kwargs["max_results"], config.MAX_RESULTS_PER_QUERY)

    def test_csv_hosts_accept_domains_and_subdomains_only(self):
        self.assertTrue(is_supported_job_url("https://careers.latam.example/jobs/1"))
        self.assertTrue(is_supported_job_url("https://jobs.careers.latam.example/jobs/1"))
        self.assertFalse(is_supported_job_url("https://latam.example.attacker.test/jobs/1"))
        self.assertFalse(is_supported_job_url("https://notcareers.latam.example/jobs/1"))
        self.assertFalse(is_supported_job_url("https://careers.latam.example@attacker.test/jobs/1"))
        self.assertEqual(job_site_name("https://careers.latam.example/jobs/1"), "Latam Co")

    def test_requested_job_boards_are_accepted_but_other_boards_are_not(self):
        accepted = (
            "https://www.linkedin.com/jobs/view/123",
            "https://www.infojobs.com.br/vaga-developer.aspx",
            "https://portal.gupy.io/job/123",
            "https://www.vagas.com.br/vaga-de-dev-jr/1",
            "https://www.catho.com.br/vaga/1",
            "https://programathor.com.br/jobs/1",
            "https://jobs.geekhunter.com.br/vaga/1",
            "https://trampos.co/oportunidades/1",
        )
        for url in accepted:
            with self.subTest(url=url):
                self.assertTrue(is_supported_job_url(url))

        # Fora de escopo: renderizavam quase nada (indeed 0 em 9 queries,
        # glassdoor 1 em 6) e cada busca custa cota de rate limit.
        rejected = (
            "https://br.indeed.com/viewjob?jk=abc",
            "https://www.glassdoor.com.br/Vaga/desenvolvedor-vagas",
            "https://www.monster.com/jobs/1",
            "https://linkedin.com.attacker.test/jobs/1",
        )
        for url in rejected:
            with self.subTest(url=url):
                self.assertFalse(is_supported_job_url(url))

        self.assertEqual(job_site_name(accepted[0]), "linkedin")

    def test_listing_pages_are_rejected_even_on_allowed_boards(self):
        listings = (
            "https://www.infojobs.com.br/vagas-de-emprego-desenvolvedor+junior.aspx",
            "https://br.indeed.com/q-desenvolvedor-junior-full-stack-vagas.html",
            "https://www.glassdoor.com/Job/junior-backend-developer-jobs-SRCH_KO0,24.htm",
            "https://www.glassdoor.com.br/Vaga/desenvolvedor-jr-vagas-SRCH_KO0,16.htm",
        )
        for url in listings:
            with self.subTest(url=url):
                self.assertFalse(is_supported_job_url(url))


if __name__ == "__main__":
    unittest.main()
