import unittest
from tabular_data import Table
from monday_client import MondayClient
from data_resilience_engine import DataResilienceEngine
from cross_board_engine import CrossBoardEngine
from bi_agent_core import BIAgentCore
from leadership_update_generator import LeadershipUpdateGenerator

class TestMondayBIAgent(unittest.TestCase):

    def setUp(self):
        self.raw_deals = MondayClient.generate_mock_deals()
        self.raw_wos = MondayClient.generate_mock_work_orders()
        self.clean_deals = DataResilienceEngine.clean_deals(self.raw_deals)
        self.clean_wos = DataResilienceEngine.clean_work_orders(self.raw_wos)
        self.cross_engine = CrossBoardEngine(self.clean_deals, self.clean_wos)
        self.bi_agent = BIAgentCore(self.clean_deals, self.clean_wos)

    def test_date_resilience(self):
        d1, q1, y1 = DataResilienceEngine.parse_flexible_date("2024-03-15")
        self.assertEqual(d1, "2024-03-15")
        self.assertEqual(q1, "Q1 2024")
        self.assertEqual(y1, 2024)

        d2, q2, y2 = DataResilienceEngine.parse_flexible_date("14/03/2024")
        self.assertEqual(d2, "2024-03-14")
        self.assertEqual(q2, "Q1 2024")

        d3, q3, y3 = DataResilienceEngine.parse_flexible_date("Q2 2024")
        self.assertEqual(q3, "Q2 2024")

        d4, q4, y4 = DataResilienceEngine.parse_flexible_date("")
        self.assertIsNone(d4)

    def test_currency_resilience(self):
        v1, _ = DataResilienceEngine.parse_currency_amount("₹ 45,00,000")
        self.assertEqual(v1, 4500000.0)

        v2, _ = DataResilienceEngine.parse_currency_amount("₹65 Lakhs")
        self.assertEqual(v2, 6500000.0)

        v3, _ = DataResilienceEngine.parse_currency_amount("₹1.1 Cr")
        self.assertEqual(v3, 11000000.0)

        v4, _ = DataResilienceEngine.parse_currency_amount("$48,000")
        self.assertEqual(v4, 48000.0 * 83.0)

        v5, _ = DataResilienceEngine.parse_currency_amount("$35k")
        self.assertEqual(v5, 35000.0 * 83.0)

    def test_sector_canonicalization(self):
        self.assertEqual(DataResilienceEngine.canonicalize_sector("Renewables / Energy"), "Energy & Utilities")
        self.assertEqual(DataResilienceEngine.canonicalize_sector("Solar & Wind"), "Energy & Utilities")
        self.assertEqual(DataResilienceEngine.canonicalize_sector("Infra & Construction"), "Infrastructure")
        self.assertEqual(DataResilienceEngine.canonicalize_sector("Mining & Metals"), "Mining & Metals")
        self.assertEqual(DataResilienceEngine.canonicalize_sector("Agriculture"), "Agriculture")
        self.assertEqual(DataResilienceEngine.canonicalize_sector("Defence Perimeter"), "Defence & Security")

    def test_cross_board_kpis(self):
        kpis = self.cross_engine.get_summary_kpis()
        self.assertGreater(kpis["closed_won_revenue"], 0)
        self.assertGreater(kpis["open_pipeline_value"], 0)
        self.assertGreater(kpis["weighted_pipeline_value"], 0)
        self.assertGreaterEqual(kpis["win_rate_pct"], 0)
        self.assertLessEqual(kpis["win_rate_pct"], 100)
        self.assertGreater(kpis["total_work_orders"], 0)
        self.assertGreater(kpis["revenue_at_risk"], 0)

    def test_revenue_at_risk_detection(self):
        risk_table = self.cross_engine.get_revenue_at_risk_details()
        self.assertFalse(risk_table.empty)
        clients_at_risk = risk_table.unique("client")
        self.assertTrue(any("Tata Power" in str(c) for c in clients_at_risk))

    def test_bi_agent_founder_queries(self):
        # 1. Sector pipeline
        res1 = self.bi_agent.process_query("How is our pipeline looking for the energy sector this quarter?")
        self.assertEqual(res1["intent"], "SECTOR_PIPELINE")
        self.assertIn("Energy & Utilities", res1["title"])
        self.assertIsNotNone(res1["executive_summary"])

        # 2. Revenue at risk
        res2 = self.bi_agent.process_query("Which high-value clients have delayed work orders?")
        self.assertEqual(res2["intent"], "REVENUE_AT_RISK")
        self.assertFalse(res2["data_table"].empty)

        # 3. Leadership Update
        res3 = self.bi_agent.process_query("Prepare a leadership update for this quarter")
        self.assertEqual(res3["intent"], "LEADERSHIP_UPDATE")
        self.assertIn("Skylark Drones", res3.get("full_briefing_markdown", ""))

    def test_leadership_generator(self):
        gen = LeadershipUpdateGenerator(self.clean_deals, self.clean_wos)
        brief = gen.generate_update("Q2 2024")
        self.assertIn("Skylark Drones — Executive Leadership Update", brief["markdown_report"])
        self.assertIn("Top Commercial Wins", brief["markdown_report"])
        self.assertIn("Critical Red Flags", brief["markdown_report"])
        self.assertGreater(len(brief["strategic_actions"]), 0)

if __name__ == "__main__":
    unittest.main(verbosity=2)