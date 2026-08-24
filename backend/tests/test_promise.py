"""JobPilot — Core Promise gate tests."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from promise import passes_core_promise


DEFAULT_PREFS = {
    "regions": ["US"],
    "directions": ["data science", "machine learning"],
    "visa_needed": True,
    "degree_level": "Master",
}


def make_job(**overrides):
    base = {
        "title": "Data Scientist",
        "company": "TestCorp",
        "audit": {"status": "✓ Open"},
        "degree_required": "BS",
        "location": "New York, NY",
    }
    base.update(overrides)
    return base


class TestCorePromise:
    def test_good_job_passes(self):
        ok, reason = passes_core_promise(make_job(), DEFAULT_PREFS)
        assert ok is True
        assert reason == ""

    def test_closed_job_fails(self):
        ok, reason = passes_core_promise(
            make_job(audit={"status": "Closed"}), DEFAULT_PREFS
        )
        assert ok is False
        assert "not_open" in reason

    def test_senior_role_blocked(self):
        ok, reason = passes_core_promise(
            make_job(title="Senior Staff Data Scientist"), DEFAULT_PREFS
        )
        assert ok is False
        assert "senior" in reason

    def test_phd_required_blocked_for_master(self):
        ok, reason = passes_core_promise(
            make_job(degree_required="PhD"), DEFAULT_PREFS
        )
        assert ok is False
        assert "degree" in reason

    def test_bs_job_visible_to_master(self):
        ok, reason = passes_core_promise(
            make_job(degree_required="BS"), DEFAULT_PREFS
        )
        assert ok is True
