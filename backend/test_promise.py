"""Tests for the Core Promise — passes_core_promise()."""

from promise import passes_core_promise, filter_by_promise


def _job(title="Data Science Intern", company="Acme", region="US",
         status="open", categories=None, visa="unspecified",
         degree_required="", remote=False):
    """Helper: build a minimal job dict."""
    return {
        "title": title,
        "company": company,
        "region": region,
        "remote": remote,
        "status": status,
        "categories": categories or ["DS/ML"],
        "visa_sponsorship": visa,
        "degree_required": degree_required,
        "audit": {"status": "✓ Open", "confidence": "high", "visa": visa},
    }


def _prefs(regions=None, directions=None, visa_needed=False, degree_level="Master"):
    return {
        "regions": regions or ["US"],
        "directions": directions or ["DS/ML"],
        "visa_needed": visa_needed,
        "degree_level": degree_level,
    }


# ── Condition 1: OPEN ──────────────────────────────────────

class TestOpen:
    def test_open_passes(self):
        ok, _ = passes_core_promise(_job(), _prefs())
        assert ok

    def test_closed_fails(self):
        j = _job(status="closed")
        j["audit"]["status"] = "✗ Closed"
        ok, reason = passes_core_promise(j, _prefs())
        assert not ok
        assert "not_open" in reason

    def test_unverified_fails(self):
        j = _job(status="unverified")
        j["audit"]["status"] = "⚠ Unverified"
        ok, reason = passes_core_promise(j, _prefs())
        assert not ok
        assert "not_open" in reason


# ── Condition 2: LOCATION MATCH ────────────────────────────

class TestLocation:
    def test_matching_region_passes(self):
        ok, _ = passes_core_promise(_job(region="UK"), _prefs(regions=["UK"]))
        assert ok

    def test_wrong_region_fails(self):
        ok, reason = passes_core_promise(_job(region="US"), _prefs(regions=["UK"]))
        assert not ok
        assert "region_mismatch" in reason

    def test_remote_passes_any_region(self):
        ok, _ = passes_core_promise(_job(region="US", remote=True), _prefs(regions=["UK"]))
        assert ok

    def test_multi_region(self):
        ok, _ = passes_core_promise(_job(region="CA"), _prefs(regions=["US", "CA"]))
        assert ok


# ── Condition 3: DIRECTION MATCH ───────────────────────────

class TestDirection:
    def test_matching_direction_passes(self):
        ok, _ = passes_core_promise(
            _job(title="Machine Learning Intern", categories=["DS/ML"]),
            _prefs(directions=["DS/ML"]))
        assert ok

    def test_wrong_direction_fails(self):
        ok, reason = passes_core_promise(
            _job(title="Android Design Intern", categories=["Design"]),
            _prefs(directions=["DS/ML"]))
        assert not ok
        assert "direction_mismatch" in reason

    def test_title_keyword_match_without_category(self):
        """Title keywords can match even if categories are empty."""
        ok, _ = passes_core_promise(
            _job(title="Data Science Intern", categories=[]),
            _prefs(directions=["DS/ML"]))
        assert ok

    def test_generic_data_intern_with_category(self):
        """Generic 'Data Intern' passes if category matches."""
        ok, _ = passes_core_promise(
            _job(title="Data Intern", categories=["DS/ML"]),
            _prefs(directions=["DS/ML"]))
        assert ok


# ── Condition 4: IDENTITY MATCH ────────────────────────────

class TestIdentity:
    # Senior roles — always blocked
    def test_senior_blocked(self):
        ok, reason = passes_core_promise(_job(title="Senior Data Scientist"), _prefs())
        assert not ok
        assert "senior_role" in reason

    def test_lead_blocked(self):
        ok, reason = passes_core_promise(_job(title="Lead ML Engineer"), _prefs())
        assert not ok
        assert "senior_role" in reason

    def test_director_blocked(self):
        ok, reason = passes_core_promise(_job(title="Director of Analytics"), _prefs())
        assert not ok
        assert "senior_role" in reason

    def test_manager_blocked(self):
        ok, reason = passes_core_promise(_job(title="Manager, Data Science"), _prefs())
        assert not ok
        assert "senior_role" in reason

    def test_principal_blocked(self):
        ok, reason = passes_core_promise(_job(title="Principal Engineer"), _prefs())
        assert not ok
        assert "senior_role" in reason

    def test_vp_blocked(self):
        ok, reason = passes_core_promise(_job(title="VP of Engineering"), _prefs())
        assert not ok
        assert "senior_role" in reason

    def test_postdoc_blocked(self):
        ok, reason = passes_core_promise(_job(title="Postdoc Research Fellow"), _prefs())
        assert not ok
        assert "senior_role" in reason

    def test_staff_blocked(self):
        ok, reason = passes_core_promise(_job(title="Staff Software Engineer"), _prefs())
        assert not ok
        assert "senior_role" in reason

    # PhD — search-time filter
    def test_phd_job_hidden_from_masters(self):
        ok, reason = passes_core_promise(
            _job(degree_required="PhD"), _prefs(degree_level="Master"))
        assert not ok
        assert "phd_required" in reason

    def test_phd_job_shown_to_phd(self):
        ok, _ = passes_core_promise(
            _job(degree_required="PhD"), _prefs(degree_level="PhD"))
        assert ok

    def test_phd_in_title_hidden_from_masters(self):
        ok, reason = passes_core_promise(
            _job(title="PhD Research Intern"), _prefs(degree_level="Master"))
        assert not ok
        assert "phd_in_title" in reason

    def test_phd_in_title_shown_to_phd(self):
        ok, _ = passes_core_promise(
            _job(title="PhD Research Intern"), _prefs(degree_level="PhD"))
        assert ok

    # Visa — unknown is not yes
    def test_visa_needed_confirmed_passes(self):
        ok, _ = passes_core_promise(
            _job(visa="confirmed"), _prefs(visa_needed=True))
        assert ok

    def test_visa_needed_unspecified_fails(self):
        ok, reason = passes_core_promise(
            _job(visa="unspecified"), _prefs(visa_needed=True))
        assert not ok
        assert "visa_not_confirmed" in reason

    def test_visa_needed_no_sponsor_fails(self):
        ok, reason = passes_core_promise(
            _job(visa="no_sponsor"), _prefs(visa_needed=True))
        assert not ok
        assert "visa_not_confirmed" in reason

    def test_visa_not_needed_unspecified_passes(self):
        ok, _ = passes_core_promise(
            _job(visa="unspecified"), _prefs(visa_needed=False))
        assert ok


# ── filter_by_promise ──────────────────────────────────────

class TestFilterByPromise:
    def test_mixed_list(self):
        jobs = [
            _job(title="Data Science Intern", region="US"),
            _job(title="Senior Data Scientist", region="US"),
            _job(title="ML Intern", region="UK"),
        ]
        passed, rejected = filter_by_promise(jobs, _prefs(regions=["US"]))
        assert len(passed) == 1
        assert passed[0]["title"] == "Data Science Intern"
        assert len(rejected) == 2

    def test_all_rejected_returns_empty(self):
        jobs = [_job(title="Senior Lead Director Manager")]
        passed, rejected = filter_by_promise(jobs, _prefs())
        assert len(passed) == 0
        assert len(rejected) == 1

    def test_empty_input(self):
        passed, rejected = filter_by_promise([], _prefs())
        assert passed == []
        assert rejected == []
