import math
import unittest
from datetime import date
from unittest.mock import patch

from job_search import (
    accept_search_hits,
    canonicalize_search_job,
    dedup_jobs,
    format_jobspy_posted_age,
    is_relevant_search_job,
    jobspy_hit_to_dict,
    parse_search_hit,
    search_all,
)
from sites import is_supported_job_url, job_site_name


class JobSpyHitMappingTests(unittest.TestCase):
    def test_hit_uses_direct_url_and_description(self):
        hit = jobspy_hit_to_dict(
            {
                "job_url": "https://br.indeed.com/viewjob?jk=abc&from=serp",
                "job_url_direct": "https://br.indeed.com/viewjob?jk=abc",
                "title": "Desenvolvedor Python Junior",
                "description": "Vaga remota com Python e Django.",
            }
        )
        self.assertEqual(hit["href"], "https://br.indeed.com/viewjob?jk=abc")
        self.assertEqual(hit["title"], "Desenvolvedor Python Junior")
        self.assertIn("Python e Django", hit["body"])

    def test_hit_falls_back_to_job_url(self):
        hit = jobspy_hit_to_dict(
            {"job_url": "https://www.linkedin.com/jobs/view/123", "title": "Python Jr"}
        )
        self.assertEqual(hit["href"], "https://www.linkedin.com/jobs/view/123")

    def test_posted_age_is_appended_to_body(self):
        hit = jobspy_hit_to_dict(
            {"job_url": "https://x/1", "title": "T", "date_posted": date(2026, 11, 5)}
        )
        self.assertIn("publicada em 05/11/2026", hit["body"])

    def test_posted_age_accepts_iso_string(self):
        self.assertEqual(
            format_jobspy_posted_age("2026-11-05"),
            "publicada em 05/11/2026",
        )

    def test_posted_age_ignores_empty_value(self):
        self.assertEqual(format_jobspy_posted_age(None), "")
        self.assertEqual(format_jobspy_posted_age("sem data"), "")


class IndeedUrlSupportTests(unittest.TestCase):
    def test_indeed_job_url_is_supported(self):
        url = "https://br.indeed.com/viewjob?jk=abc123"
        self.assertTrue(is_supported_job_url(url))
        self.assertEqual(job_site_name(url), "indeed")

    def test_indeed_listing_url_is_rejected(self):
        self.assertFalse(is_supported_job_url("https://br.indeed.com/q-python-junior"))


class JobSpyUrlScopeTests(unittest.TestCase):
    """O JobSpy devolve a URL do site de recrutamento da empresa, nao do board."""

    ATS_URL = "https://applicants.bairesdev.com/job/71/281679/apply"

    def test_hit_carries_board_source_for_ats_urls(self):
        hit = jobspy_hit_to_dict(
            {
                "job_url": self.ATS_URL,
                "title": "Desenvolvedor Python Junior",
                "site": "indeed",
            }
        )
        self.assertEqual(hit["href"], self.ATS_URL)
        self.assertEqual(hit["source"], "indeed")

    def test_hit_treats_pandas_nan_as_empty_url(self):
        hit = jobspy_hit_to_dict(
            {"job_url": math.nan, "job_url_direct": math.nan, "title": "X", "site": "indeed"}
        )
        self.assertEqual(hit["href"], "")

    def test_ats_url_is_rejected_for_ddg_but_accepted_for_jobspy(self):
        job = canonicalize_search_job(
            parse_search_hit({"href": self.ATS_URL, "title": "Dev Python Jr", "body": ""})
        )
        self.assertFalse(is_relevant_search_job(job))
        self.assertTrue(
            is_relevant_search_job(job, require_supported_url=False)
        )

    def test_jobspy_keeps_ats_url_and_falls_back_to_board_source(self):
        hits = [
            jobspy_hit_to_dict(
                {
                    "job_url": self.ATS_URL,
                    "title": "Desenvolvedor Python Junior",
                    "site": "indeed",
                }
            )
        ]
        jobs = accept_search_hits(hits, set(), require_supported_url=False)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["url"], self.ATS_URL)
        self.assertEqual(jobs[0]["source"], "indeed")

    def test_jobspy_rejects_nan_url(self):
        hits = [jobspy_hit_to_dict({"job_url": math.nan, "title": "X", "site": "indeed"})]
        self.assertEqual(accept_search_hits(hits, set(), require_supported_url=False), [])


class SearchAllTests(unittest.TestCase):
    def test_search_all_deduplicates_urls_across_sources(self):
        shared = "https://www.linkedin.com/jobs/view/999"
        ddg_jobs = [
            {"url": shared, "title": "Vaga A", "snippet": ""},
            {"url": "https://gupy.io/jobs/1", "title": "Vaga B", "snippet": ""},
        ]
        jobspy_jobs = [
            {"url": "https://br.indeed.com/viewjob?jk=1", "title": "Vaga C", "snippet": ""},
            {"url": shared, "title": "Vaga A repetida", "snippet": ""},
        ]
        with (
            patch("job_search.ddg_search", return_value=list(ddg_jobs)),
            patch("job_search.jobspy_search", return_value=list(jobspy_jobs)),
        ):
            jobs = search_all()

        urls = [job["url"] for job in jobs]
        self.assertEqual(len(urls), 3)
        self.assertEqual(urls.count(shared), 1)

    def test_dedup_jobs_keeps_first_occurrence(self):
        jobs = [
            {"url": "https://gupy.io/jobs/5", "title": "primeira"},
            {"url": "https://gupy.io/jobs/5?from=x", "title": "segunda"},
        ]
        unique = dedup_jobs(jobs)
        self.assertEqual(len(unique), 1)
        self.assertEqual(unique[0]["title"], "primeira")


if __name__ == "__main__":
    unittest.main()
