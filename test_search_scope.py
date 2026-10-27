import tempfile
import unittest
from pathlib import Path
from unittest import mock

import companies
import config
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

    def test_search_queries_include_the_requested_job_boards(self):
        queries = build_search_queries()
        board_queries = queries[-sum(
            len(config.JOB_BOARD_SEARCH_QUERIES[site_name])
            for site_name in config.JOB_BOARD_SEARCH_SITES
        ):]

        self.assertEqual(len(board_queries), 5)
        for site_name in config.JOB_BOARD_SEARCH_SITES:
            with self.subTest(site=site_name):
                for clause in config.JOB_BOARD_SEARCH_QUERIES[site_name]:
                    self.assertTrue(any(clause in query for query in board_queries))

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
            "https://br.indeed.com/viewjob?jk=abc",
            "https://www.infojobs.com.br/vaga-developer.aspx",
            "https://www.glassdoor.com.br/Vaga/desenvolvedor-vagas",
        )
        for url in accepted:
            with self.subTest(url=url):
                self.assertTrue(is_supported_job_url(url))

        self.assertFalse(is_supported_job_url("https://www.gupy.io/jobs/123"))
        self.assertFalse(is_supported_job_url("https://linkedin.com.attacker.test/jobs/1"))
        self.assertEqual(job_site_name(accepted[0]), "linkedin")


if __name__ == "__main__":
    unittest.main()
