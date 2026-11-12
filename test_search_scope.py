import unittest
from unittest import mock

import config
import job_search
from job_search import build_search_queries
from sites import is_supported_job_url, job_site_name


class SearchScopeTests(unittest.TestCase):
    def test_search_queries_include_the_requested_job_boards(self):
        queries = build_search_queries()

        self.assertTrue(queries)
        for site_name in config.JOB_BOARD_SEARCH_SITES:
            with self.subTest(site=site_name):
                for clause in config.JOB_BOARD_SEARCH_QUERIES[site_name]:
                    self.assertTrue(any(clause in query for query in queries))

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
        self.assertEqual(len(build_search_queries()), expected_board_queries)

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

    def test_hosts_outside_job_boards_are_rejected(self):
        # So JOB_BOARD_DOMAINS passa: o antigo fallback por dominio de
        # empresa removido junto com o CSV nao abre caminho para host
        # desconhecido nem para ataque de subdominio.
        rejected = (
            "https://careers.latam.example/jobs/1",
            "https://jobs.careers.latam.example/jobs/1",
            "https://latam.example.attacker.test/jobs/1",
            "https://notcareers.latam.example/jobs/1",
            "https://careers.latam.example@attacker.test/jobs/1",
        )
        for url in rejected:
            with self.subTest(url=url):
                self.assertFalse(is_supported_job_url(url))
                self.assertEqual(job_site_name(url), "")

    def test_requested_job_boards_are_accepted_but_other_boards_are_not(self):
        accepted = (
            "https://www.linkedin.com/jobs/view/123",
            # indeed entra pelo JobSpy, que busca direto no board; a query
            # site: do DDG continuou devolvendo 0 resultados.
            "https://br.indeed.com/viewjob?jk=abc",
            "https://www.infojobs.com.br/vaga-developer.aspx",
            "https://portal.gupy.io/job/123",
            "https://www.vagas.com.br/vaga-de-dev-jr/1",
            "https://www.catho.com.br/vaga/1",
            "https://programathor.com.br/jobs/1",
            "https://jobs.geekhunter.com.br/vaga/1",
            "https://trampos.co/oportunidades/1",
            # Glassdoor via JobSpy: vaga individual com jl= na query.
            "https://www.glassdoor.com.br/job-listing/j?jl=1010324571717",
        )
        for url in accepted:
            with self.subTest(url=url):
                self.assertTrue(is_supported_job_url(url))

        # Fora de escopo: nao estao em JOB_BOARD_DOMAINS nem no JobSpy.
        rejected = (
            "https://www.monster.com/jobs/1",
            "https://linkedin.com.attacker.test/jobs/1",
        )
        for url in rejected:
            with self.subTest(url=url):
                self.assertFalse(is_supported_job_url(url))

        self.assertEqual(job_site_name(accepted[0]), "linkedin")
        self.assertEqual(job_site_name(accepted[1]), "indeed")
        self.assertEqual(job_site_name(accepted[-1]), "glassdoor")

    def test_listing_pages_are_rejected_even_on_allowed_boards(self):
        listings = (
            "https://www.infojobs.com.br/vagas-de-emprego-desenvolvedor+junior.aspx",
            "https://br.indeed.com/q-desenvolvedor-junior-full-stack-vagas.html",
            "https://www.glassdoor.com/Job/junior-backend-developer-jobs-SRCH_KO0,24.htm",
            "https://www.glassdoor.com.br/Vaga/desenvolvedor-jr-vagas-SRCH_KO0,16.htm",
            "https://www.glassdoor.com.br/Vaga/desenvolvedor-vagas",
        )
        for url in listings:
            with self.subTest(url=url):
                self.assertFalse(is_supported_job_url(url))

    def test_jobspy_uses_more_terms_than_the_ddg_or_query(self):
        # O DDG junta tudo em uma query OR (limite ~200 chars); o JobSpy
        # faz uma chamada por termo e pode ir alem sem estourar o buscador.
        self.assertGreater(len(config.JOBSPY_QUERY_STEMS), len(config.QUERY_STEMS))
        for stem in config.QUERY_STEMS:
            self.assertIn(stem, config.JOBSPY_QUERY_STEMS)

    def test_jobspy_search_uses_the_extended_term_list(self):
        frame = mock.Mock()
        frame.to_dict.return_value = []
        scrape = mock.Mock(return_value=frame)
        fake_jobspy = mock.Mock(scrape_jobs=scrape)
        with (
            mock.patch.object(config, "JOBSPY_ENABLED", True),
            mock.patch.object(config, "JOBSPY_SITES", ("indeed",)),
            mock.patch.object(config, "JOBSPY_QUERY_STEMS", ("termo a", "termo b")),
            mock.patch.dict("sys.modules", {"jobspy": fake_jobspy}),
        ):
            job_search.jobspy_search()

        self.assertEqual(scrape.call_count, 2)
        called_terms = [call.kwargs["search_term"] for call in scrape.call_args_list]
        self.assertEqual(called_terms, ["termo a", "termo b"])


if __name__ == "__main__":
    unittest.main()
