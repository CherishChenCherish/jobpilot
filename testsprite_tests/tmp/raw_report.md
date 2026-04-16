
# TestSprite AI Testing Report(MCP)

---

## 1️⃣ Document Metadata
- **Project Name:** jobpilot
- **Date:** 2026-04-16
- **Prepared by:** TestSprite AI Team

---

## 2️⃣ Requirement Validation Summary

#### Test TC001 get apihealth returns service status
- **Test Code:** [TC001_get_apihealth_returns_service_status.py](./TC001_get_apihealth_returns_service_status.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/c335e677-e801-4342-97be-da93f922d668/7da75d02-7086-4434-b91d-962ffdf552ff
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC002 get apidebugtables returns database tables and row counts
- **Test Code:** [TC002_get_apidebugtables_returns_database_tables_and_row_counts.py](./TC002_get_apidebugtables_returns_database_tables_and_row_counts.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/c335e677-e801-4342-97be-da93f922d668/4769433d-716f-4e5b-b779-85f9b3b92b89
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC003 post apisyncuser upserts user record from google oauth payload
- **Test Code:** [TC003_post_apisyncuser_upserts_user_record_from_google_oauth_payload.py](./TC003_post_apisyncuser_upserts_user_record_from_google_oauth_payload.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/c335e677-e801-4342-97be-da93f922d668/cb8f47df-ea29-435a-a0dc-b038ea661e00
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC004 get apime returns authenticated user profile
- **Test Code:** [TC004_get_apime_returns_authenticated_user_profile.py](./TC004_get_apime_returns_authenticated_user_profile.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 39, in <module>
  File "<string>", line 35, in test_tc004_get_api_me_authenticated_user_profile
AssertionError: Expected status 401 without auth, got 200

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/c335e677-e801-4342-97be-da93f922d668/0fce422a-ff5c-46f2-96ae-c8b38c0db463
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC005 post apiparse parses uploaded resume and returns structured fields
- **Test Code:** [TC005_post_apiparse_parses_uploaded_resume_and_returns_structured_fields.py](./TC005_post_apiparse_parses_uploaded_resume_and_returns_structured_fields.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 81, in <module>
  File "<string>", line 75, in test_post_apiparse_resume_parsing
AssertionError: Unexpected status code 422 for empty file

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/c335e677-e801-4342-97be-da93f922d668/de73ca65-a8e2-4028-b28e-cf366298d423
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC006 post apisearch returns jobs filtered by core promise
- **Test Code:** [TC006_post_apisearch_returns_jobs_filtered_by_core_promise.py](./TC006_post_apisearch_returns_jobs_filtered_by_core_promise.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 77, in <module>
  File "<string>", line 67, in test_post_apisearch_jobs_filtered_by_core_promise
AssertionError: Unauthenticated request did not return 401: {"search_id": null, "jobs": [], "audit_summary": {"jobs_searched": 0, "jobs_verified": 0, "jobs_open": 0, "jobs_unverified": 0, "jobs_dropped": 0, "jobs_promise_rejected": 0, "cl_generated": 0, "cl_status": "pending", "source": "cache", "warming": true, "timestamp": "2026-04-16T12:51:38.729179+00:00", "zero_reason": "No jobs match your current filters. (regions: US; directions: DS/ML; visa sponsorship required) We're actively searching for more — check back soon."}, "errors": ["No jobs match your current filters. (regions: US; directions: DS/ML; visa sponsorship required) We're actively searching for more — check back soon."]}

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/c335e677-e801-4342-97be-da93f922d668/b6ec2867-e97d-476f-8734-3835287cda79
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC007 post apigeneratecls generates cover letter for job
- **Test Code:** [TC007_post_apigeneratecls_generates_cover_letter_for_job.py](./TC007_post_apigeneratecls_generates_cover_letter_for_job.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 86, in <module>
  File "<string>", line 58, in test_post_api_generate_cls
AssertionError: Expected 400 for invalid job_id, got 200

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/c335e677-e801-4342-97be-da93f922d668/0f4511d7-1516-4de2-9320-e60ed6c5401d
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC008 get apigenerateclsstream streams cover letter generation tokens
- **Test Code:** [TC008_get_apigenerateclsstream_streams_cover_letter_generation_tokens.py](./TC008_get_apigenerateclsstream_streams_cover_letter_generation_tokens.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 81, in <module>
  File "<string>", line 35, in test_get_apigenerateclsstream_tokens
AssertionError: No jobs returned from /api/search, can't test streaming cover letters.

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/c335e677-e801-4342-97be-da93f922d668/2639a0c3-bac8-4c1b-8f80-006a3ab7d1eb
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC009 get apidemoverify verifies job url open status
- **Test Code:** [TC009_get_apidemoverify_verifies_job_url_open_status.py](./TC009_get_apidemoverify_verifies_job_url_open_status.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/c335e677-e801-4342-97be-da93f922d668/ea963d9b-3af8-4f88-ba3f-40554a9cf885
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC010 post apistripecreatecheckout creates stripe checkout session
- **Test Code:** [TC010_post_apistripecreatecheckout_creates_stripe_checkout_session.py](./TC010_post_apistripecreatecheckout_creates_stripe_checkout_session.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/c335e677-e801-4342-97be-da93f922d668/3eba3040-b397-42a1-961a-dac710d093d4
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---


## 3️⃣ Coverage & Matching Metrics

- **50.00** of tests passed

| Requirement        | Total Tests | ✅ Passed | ❌ Failed  |
|--------------------|-------------|-----------|------------|
| ...                | ...         | ...       | ...        |
---


## 4️⃣ Key Gaps / Risks
{AI_GNERATED_KET_GAPS_AND_RISKS}
---