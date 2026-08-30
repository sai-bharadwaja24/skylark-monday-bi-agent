"""
Unit tests for data_processing.py / reports.py / cross_link.py.

Deliberately uses fixture data shaped like the REAL Deals/Work Orders
boards (real column names, real Deal Stage vocabulary like "H. Work Order
Received", real Execution Status values like "Pause / struck") rather than
a convenient invented schema - so a green test suite here actually proves
something about correctness on the real boards, not just on data that was
designed to make the code look good.
"""

import pandas as pd

import cross_link
import data_processing as dp
import reports


def _sample_deals():
    return [
        {"Deal Name": "Alpha", "Owner code": "OWNER_001", "Client Code": "COMPANY001",
         "Deal Status": "Won", "Masked Deal value": 5000000, "Closure Probability": None,
         "Deal Stage": "G. Project Won", "Sector/service": "Mining"},
        {"Deal Name": "Beta", "Owner code": "OWNER_002", "Client Code": "COMPANY002",
         "Deal Status": "Dead", "Masked Deal value": 2000000, "Closure Probability": None,
         "Deal Stage": "L. Project Lost", "Sector/service": "Railways"},
        {"Deal Name": "Gamma", "Owner code": "OWNER_002", "Client Code": "COMPANY003",
         "Deal Status": "Open", "Masked Deal value": 3000000, "Closure Probability": "High",
         "Deal Stage": "F. Negotiations", "Sector/service": "Mining"},
        {"Deal Name": "Delta", "Owner code": "OWNER_003", "Client Code": "COMPANY004",
         "Deal Status": "Open", "Masked Deal value": None, "Closure Probability": "Low",
         "Deal Stage": "A. Lead Generated", "Sector/service": None},
        # stray duplicated-header row, like the real file has
        {"Deal Name": "Deal Name", "Owner code": "Owner code", "Client Code": "Client Code",
         "Deal Status": "Deal Status", "Masked Deal value": None, "Closure Probability": None,
         "Deal Stage": "Deal Stage", "Sector/service": "Sector/service"},
    ]


def _sample_work_orders():
    return [
        {"Deal name masked": "Alpha", "Customer Name Code": "WOCOMPANY_001",
         "Execution Status": "Completed", "Amount Receivable (Masked)": 0, "Sector": "Mining"},
        {"Deal name masked": "Gamma", "Customer Name Code": "WOCOMPANY_002",
         "Execution Status": "Ongoing", "Amount Receivable (Masked)": 150000, "Sector": "Mining"},
        {"Deal name masked": "Epsilon", "Customer Name Code": "WOCOMPANY_003",
         "Execution Status": "Pause / struck", "Amount Receivable (Masked)": 500000, "Sector": "Railways"},
        {"Deal name masked": "Zeta", "Customer Name Code": "WOCOMPANY_004",
         "Execution Status": "Not Started", "Amount Receivable (Masked)": None, "Sector": None},
    ]


def test_clean_deals_drops_stray_header_row():
    result = dp.clean_deals(_sample_deals())
    assert len(result.df) == 4  # 5 rows minus 1 stray header row
    assert any("duplicated header" in c for c in result.caveats)


def test_clean_deals_flags_missing_value_and_sector():
    result = dp.clean_deals(_sample_deals())
    assert any("no deal value recorded" in c for c in result.caveats)
    assert any("no sector/service recorded" in c for c in result.caveats)


def test_clean_work_orders_preserves_real_status_vocabulary():
    """The other implementation's keyword classifier silently mapped
    'Pause / struck' and 'Not Started' to 'In Progress'. This one keeps
    the real Execution Status text untouched, so no information is lost."""
    result = dp.clean_work_orders(_sample_work_orders())
    statuses = set(result.df["Execution Status"])
    assert "Pause / struck" in statuses
    assert "Not Started" in statuses


def test_hygiene_score_is_between_0_and_100():
    deals = dp.clean_deals(_sample_deals()).df
    wos = dp.clean_work_orders(_sample_work_orders()).df
    score = dp.compute_hygiene_score(deals, wos)
    assert 0.0 <= score <= 100.0


def test_cross_link_matches_by_name_and_flags_it_as_approximate():
    deals = dp.clean_deals(_sample_deals()).df
    wos = dp.clean_work_orders(_sample_work_orders()).df
    linked, caveat = cross_link.deals_with_open_work_orders(deals, wos)
    # "Gamma" is Open on Deals and has a non-Completed work order -> should match
    assert "Gamma" in set(linked["Deal Name"])
    assert "approximate" in caveat


def test_leadership_report_computes_real_win_rate():
    deals = dp.clean_deals(_sample_deals()).df
    wos = dp.clean_work_orders(_sample_work_orders()).df
    deal_caveats = dp.clean_deals(_sample_deals()).caveats
    wo_caveats = dp.clean_work_orders(_sample_work_orders()).caveats
    report = reports.build_leadership_report(deals, wos, deal_caveats, wo_caveats)
    # 1 Won ("Alpha") + 1 Dead ("Beta") = 2 terminal deals -> 50% win rate
    assert "50.0%" in report
    assert "Skylark Drones" in report


def test_leadership_report_does_not_fabricate_csat():
    """Regression check: an earlier draft silently substituted a hardcoded
    4.5/5.0 CSAT when no feedback column existed. This board has no CSAT
    field at all, so the report must say so instead of inventing a number."""
    deals = dp.clean_deals(_sample_deals()).df
    wos = dp.clean_work_orders(_sample_work_orders()).df
    report = reports.build_leadership_report(deals, wos, [], [])
    assert "No CSAT" in report
    assert "4.5" not in report


if __name__ == "__main__":
    import sys
    failures = 0
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
