
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
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/66216bdb-ce40-48fd-bd4a-a2672508a5f6/d4290e1a-2b6d-42ec-817b-551a92636a90
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC002 get apidebugtables returns database tables and row counts
- **Test Code:** [TC002_get_apidebugtables_returns_database_tables_and_row_counts.py](./TC002_get_apidebugtables_returns_database_tables_and_row_counts.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/66216bdb-ce40-48fd-bd4a-a2672508a5f6/b128c268-b1b6-4ea1-9dc4-ddf10927af81
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC003 post apisyncuser upserts user record from google oauth payload
- **Test Code:** [TC003_post_apisyncuser_upserts_user_record_from_google_oauth_payload.py](./TC003_post_apisyncuser_upserts_user_record_from_google_oauth_payload.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/66216bdb-ce40-48fd-bd4a-a2672508a5f6/1a54a905-cbea-41fa-abde-0c92d6a2f09a
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC004 get apime returns authenticated user profile
- **Test Code:** [TC004_get_apime_returns_authenticated_user_profile.py](./TC004_get_apime_returns_authenticated_user_profile.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 45, in <module>
  File "<string>", line 32, in test_get_apime_authenticated_and_unauthenticated
AssertionError: Expected 200 with auth but got 404

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/66216bdb-ce40-48fd-bd4a-a2672508a5f6/efcd2c43-1bf1-44ed-bd01-8423967fb10f
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC005 post apiparse parses uploaded resume and returns structured fields
- **Test Code:** [TC005_post_apiparse_parses_uploaded_resume_and_returns_structured_fields.py](./TC005_post_apiparse_parses_uploaded_resume_and_returns_structured_fields.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 62, in <module>
  File "<string>", line 26, in test_post_apiparse
AssertionError: Expected 200 for valid PDF, got 422

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/66216bdb-ce40-48fd-bd4a-a2672508a5f6/3bab41f3-2006-4f5d-aec9-04da62775015
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC006 post apisearch returns jobs filtered by core promise
- **Test Code:** [TC006_post_apisearch_returns_jobs_filtered_by_core_promise.py](./TC006_post_apisearch_returns_jobs_filtered_by_core_promise.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 61, in <module>
  File "<string>", line 30, in test_post_apisearch_core_promise
AssertionError: Expected 200 but got 429

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/66216bdb-ce40-48fd-bd4a-a2672508a5f6/745fee9f-a742-4c96-a185-fbbd2ac5c4b1
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC007 post apigeneratecls generates cover letter for job
- **Test Code:** [TC007_post_apigeneratecls_generates_cover_letter_for_job.py](./TC007_post_apigeneratecls_generates_cover_letter_for_job.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 98, in <module>
  File "<string>", line 53, in test_post_api_generate_cls
AssertionError: Expected 200, got 400

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/66216bdb-ce40-48fd-bd4a-a2672508a5f6/f83efb07-ea8e-486e-b518-98a12c83218e
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC008 get apigenerateclsstream streams cover letter generation tokens
- **Test Code:** [TC008_get_apigenerateclsstream_streams_cover_letter_generation_tokens.py](./TC008_get_apigenerateclsstream_streams_cover_letter_generation_tokens.py)
- **Test Error:** Traceback (most recent call last):
  File "<string>", line 19, in test_get_apigenerateclsstream
  File "<string>", line 13, in get_auth_headers
AssertionError: Authentication simulation unsupported: test environment must provide valid auth headers.

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 89, in <module>
  File "<string>", line 21, in test_get_apigenerateclsstream
AssertionError: Auth setup failed: Authentication simulation unsupported: test environment must provide valid auth headers.

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/66216bdb-ce40-48fd-bd4a-a2672508a5f6/69c4ed3d-796b-4408-88dc-336b5df0a3ab
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC009 get apidemoverify verifies job url open status
- **Test Code:** [TC009_get_apidemoverify_verifies_job_url_open_status.py](./TC009_get_apidemoverify_verifies_job_url_open_status.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/66216bdb-ce40-48fd-bd4a-a2672508a5f6/ad71b5a3-d9c4-4fc6-a852-00ecbd560c60
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC010 post apistripecreatecheckout creates stripe checkout session
- **Test Code:** [TC010_post_apistripecreatecheckout_creates_stripe_checkout_session.py](./TC010_post_apistripecreatecheckout_creates_stripe_checkout_session.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/66216bdb-ce40-48fd-bd4a-a2672508a5f6/45169b3c-f7d7-4e02-8086-55d64ef9ab3f
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