import unittest
from unittest import mock

import config
from bs4 import BeautifulSoup

import sites

OPEN_JOB_HTML = """
<section class="top-card-layout">
  <h1 class="top-card-layout__title">Desenvolvedor Junior Python</h1>
  <div class="topcard__flavor--metadata">Remoto · Brasil</div>
</section>
<p>Descricao da vaga e requisitos do candidato.</p>
"""

CLOSED_JOB_HTML = OPEN_JOB_HTML + '<p class="closed-job-banner">Esta vaga nao esta mais disponivel</p>'


def build_snapshot(html: str, title: str, url: str = "https://www.linkedin.com/jobs/view/123") -> dict:
    soup = BeautifulSoup(html, "html.parser")
    full_text = " ".join(part for part in [soup.get_text(" ", strip=True), title] if part)
    return {
        "url": url,
        "original_url": url,
        "title": title,
        "soup": soup,
        "full_text": full_text,
    }


class ClosedJobDetectionTests(unittest.TestCase):
    def test_open_job_without_apply_button_is_not_treated_as_closed(self):
        # Sem login o LinkedIn nao renderiza o botao de candidatura. Isso nao
        # pode ser lido como "vaga encerrada", senao vagas abertas saem do fluxo.
        snapshot = build_snapshot(
            OPEN_JOB_HTML,
            title="Desenvolvedor Junior Python | LinkedIn Jobs",
        )
        with mock.patch.object(config, "REQUIRE_APPLY_EVIDENCE", False):
            self.assertFalse(sites.is_closed_linkedin_job_page(snapshot))

    def test_page_with_closed_banner_is_rejected(self):
        snapshot = build_snapshot(
            CLOSED_JOB_HTML,
            title="Desenvolvedor Junior Python | LinkedIn Jobs",
        )
        with mock.patch.object(config, "REQUIRE_APPLY_EVIDENCE", False):
            self.assertTrue(sites.is_closed_linkedin_job_page(snapshot))

    def test_expired_redirect_is_rejected(self):
        snapshot = build_snapshot(
            OPEN_JOB_HTML,
            title="Desenvolvedor Junior Python | LinkedIn Jobs",
            url="https://br.linkedin.com/jobs/foo-vagas?trk=expired_jd_redirect",
        )
        self.assertTrue(sites.is_closed_linkedin_job_page(snapshot))

    def test_apply_evidence_is_enforced_only_when_enabled(self):
        snapshot = build_snapshot(
            OPEN_JOB_HTML,
            title="Desenvolvedor Junior Python | LinkedIn Jobs",
        )
        with mock.patch.object(config, "REQUIRE_APPLY_EVIDENCE", True):
            self.assertTrue(sites.is_closed_linkedin_job_page(snapshot))

    def test_page_without_job_title_is_rejected(self):
        snapshot = build_snapshot(
            "<p>Sem titulo de vaga aqui.</p>",
            title="Cadastre-se | LinkedIn",
        )
        with mock.patch.object(config, "REQUIRE_APPLY_EVIDENCE", False):
            self.assertTrue(sites.is_closed_linkedin_job_page(snapshot))


class LoginWallDetectionTests(unittest.TestCase):
    def test_password_widget_alone_is_not_a_login_wall(self):
        # O widget de login do cabecalho esta no DOM de toda vaga. Se ele
        # contasse como muralha, toda pagina boa forcaria um reload a toa.
        snapshot = build_snapshot(
            OPEN_JOB_HTML + "<input type='password' name='session_password'>",
            title="Desenvolvedor Junior Python | LinkedIn Jobs",
        )
        self.assertFalse(sites.is_linkedin_login_wall(snapshot))

    def test_auth_title_is_a_login_wall(self):
        snapshot = build_snapshot("<p>Sem conteudo de vaga.</p>", title="LinkedIn: entre ou cadastre-se")
        self.assertTrue(sites.is_linkedin_login_wall(snapshot))

    def test_signup_title_is_a_login_wall(self):
        snapshot = build_snapshot("<p>Sem conteudo de vaga.</p>", title="Cadastre-se | LinkedIn")
        self.assertTrue(sites.is_linkedin_login_wall(snapshot))

    def test_job_page_is_not_a_login_wall(self):
        snapshot = build_snapshot(
            OPEN_JOB_HTML,
            title="Desenvolvedor Junior Python | LinkedIn Jobs",
        )
        self.assertFalse(sites.is_linkedin_login_wall(snapshot))

    def test_retry_skipped_when_job_is_closed(self):
        snapshot = build_snapshot(
            CLOSED_JOB_HTML,
            title="Desenvolvedor Junior Python | LinkedIn Jobs",
        )
        with mock.patch.object(config, "REQUIRE_APPLY_EVIDENCE", False):
            self.assertFalse(sites.needs_linkedin_retry(snapshot))

    def test_retry_runs_when_open_job_has_no_posted_age(self):
        snapshot = build_snapshot(
            OPEN_JOB_HTML,
            title="Desenvolvedor Junior Python | LinkedIn Jobs",
        )
        with (
            mock.patch.object(config, "REQUIRE_APPLY_EVIDENCE", False),
            mock.patch.object(config, "REQUIRE_POSTED_AGE", True),
        ):
            self.assertTrue(sites.needs_linkedin_retry(snapshot))

    def test_no_retry_when_open_job_has_posted_age(self):
        snapshot = build_snapshot(
            OPEN_JOB_HTML + "<p>Há 3 dias</p>",
            title="Desenvolvedor Junior Python | LinkedIn Jobs",
        )
        with (
            mock.patch.object(config, "REQUIRE_APPLY_EVIDENCE", False),
            mock.patch.object(config, "REQUIRE_POSTED_AGE", True),
        ):
            self.assertFalse(sites.needs_linkedin_retry(snapshot))


class ListingUrlTests(unittest.TestCase):
    def test_search_and_listing_pages_are_rejected(self):
        urls = (
            "https://br.indeed.com/q-desenvolvedor-junior-vagas.html",
            "https://qa.infojobs.com.br/vagas-de-analista-desenvolvedor-junior-em-sao-paulo.aspx",
            "https://qa2.infojobs.com.br/vaga-de-desenvolvedor-junior-em-sao-paulo__10300012.aspx",
            "https://www.glassdoor.com/Salary/Google-Desenvolvedor-Junior-Salaries-E9079.htm",
            "https://www.glassdoor.com.br/Vaga/desenvolvedor-jr-SRCH_KO0,16.htm",
        )
        for url in urls:
            with self.subTest(url=url):
                self.assertFalse(sites.is_supported_job_url(url))

    def test_individual_job_pages_still_pass(self):
        urls = (
            "https://www.linkedin.com/jobs/view/4459953962",
            "https://empregos.pandape.infojobs.com.br/Detail/2755329",
            "https://www.infojobs.com.br/vaga-developer.aspx",
            "https://www.vagas.com.br/vaga-de-desenvolvedor-junior-remoto/123456",
            "https://portal.gupy.io/job/123456",
        )
        for url in urls:
            with self.subTest(url=url):
                self.assertTrue(sites.is_supported_job_url(url))

    def test_listing_url_pattern_matches_listing_pages_only(self):
        # independentemente do escopo dos boards: as regexes de listagem
        # continuam cobrindo indeed e glassdoor caso voltem as buscas.
        listings = (
            "https://br.indeed.com/q-desenvolvedor-junior-vagas.html",
            "https://www.infojobs.com.br/vagas-de-emprego-x.aspx",
            "https://www.glassdoor.com/Salary/x-Salaries-E1.htm",
            "https://www.glassdoor.com.br/Vaga/x-SRCH_KO0,16.htm",
        )
        job_pages = (
            "https://br.indeed.com/viewjob?jk=abc",
            "https://www.infojobs.com.br/vaga-developer.aspx",
            "https://www.linkedin.com/jobs/view/4459953962",
            "https://www.vagas.com.br/vaga-de-dev-junior-123456",
        )
        for url in listings:
            with self.subTest(url=url):
                self.assertTrue(sites.is_listing_url(url))
        for url in job_pages:
            with self.subTest(url=url):
                self.assertFalse(sites.is_listing_url(url))


if __name__ == "__main__":
    unittest.main()
