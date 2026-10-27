import unittest

from filters import is_allowed_posted_age, is_target_role, parse_job_age_to_days


class JobAgeTests(unittest.TestCase):
    def test_hours_and_minutes_are_fractional_days(self):
        self.assertAlmostEqual(parse_job_age_to_days("8 hours ago"), 8 / 24)
        self.assertAlmostEqual(parse_job_age_to_days("30 minutes ago"), 30 / 1440)

    def test_recent_hours_are_not_rejected_by_age_limit(self):
        self.assertTrue(is_allowed_posted_age("8 hours ago"))

    def test_age_in_days_keeps_existing_meaning(self):
        self.assertEqual(parse_job_age_to_days("7 days ago"), 7)
        self.assertTrue(is_allowed_posted_age("180 days ago"))
        self.assertFalse(is_allowed_posted_age("181 days ago"))

    def test_technology_roles_are_in_scope(self):
        titles = (
            "Desenvolvedor Backend Junior",
            "Frontend Developer Jr",
            "Engenheiro Full Stack",
            "Analista de Segurança da Informação",
            "QA Automation Engineer",
            "Data Scientist",
            "DevOps Engineer",
            "Analista de Suporte Técnico",
        )
        for title in titles:
            with self.subTest(title=title):
                self.assertTrue(is_target_role(title))

    def test_non_technology_roles_remain_out_of_scope(self):
        self.assertFalse(is_target_role("Assistente Administrativo"))
        self.assertFalse(is_target_role("Vendedor"))


if __name__ == "__main__":
    unittest.main()
