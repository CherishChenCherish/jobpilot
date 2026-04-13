
# TestSprite AI Testing Report(MCP)

---

## 1️⃣ Document Metadata
- **Project Name:** jobpilot
- **Date:** 2026-04-12
- **Prepared by:** TestSprite AI Team

---

## 2️⃣ Requirement Validation Summary

#### Test TC001 get apihealth returns service status
- **Test Code:** [TC001_get_apihealth_returns_service_status.py](./TC001_get_apihealth_returns_service_status.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 20, in <module>
  File "<string>", line 11, in test_get_api_health_returns_service_status
AssertionError: Expected status code 200 but got 403

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/ae7120ff-9a17-44f8-9761-14be2be1818e/3bc46ead-0bfb-4c01-a90e-864d7a3c7ca0
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC002 get apidebugtables returns database tables and row counts
- **Test Code:** [TC002_get_apidebugtables_returns_database_tables_and_row_counts.py](./TC002_get_apidebugtables_returns_database_tables_and_row_counts.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 27, in <module>
  File "<string>", line 12, in test_get_apidebugtables_returns_tables_and_row_counts
AssertionError: Expected 200 OK, got 403

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/ae7120ff-9a17-44f8-9761-14be2be1818e/bc5a82e5-aed3-43d3-9c36-1cc66d8e32c8
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC003 post apisyncuser upserts user record from google oauth payload
- **Test Code:** [TC003_post_apisyncuser_upserts_user_record_from_google_oauth_payload.py](./TC003_post_apisyncuser_upserts_user_record_from_google_oauth_payload.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 44, in <module>
  File "<string>", line 21, in test_post_api_sync_user_upsert_user
AssertionError: Expected 200 OK but got 403

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/ae7120ff-9a17-44f8-9761-14be2be1818e/964c7ab1-2a8c-42ce-8a60-eb609bcab8a7
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC004 get apime returns authenticated user profile
- **Test Code:** [TC004_get_apime_returns_authenticated_user_profile.py](./TC004_get_apime_returns_authenticated_user_profile.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 43, in <module>
  File "<string>", line 16, in test_get_api_me_authenticated_and_unauthenticated
AssertionError: Sync user failed with status 403

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/ae7120ff-9a17-44f8-9761-14be2be1818e/fabb7fd2-c8e4-433d-b3a1-5f34ee23412d
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC005 post apiparse parses uploaded resume and returns structured fields
- **Test Code:** [TC005_post_apiparse_parses_uploaded_resume_and_returns_structured_fields.py](./TC005_post_apiparse_parses_uploaded_resume_and_returns_structured_fields.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 96, in <module>
  File "<string>", line 48, in test_post_api_parse_resume_parsing
  File "<string>", line 32, in post_parse
AssertionError: Expected status 200 but got 403, response: 

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/ae7120ff-9a17-44f8-9761-14be2be1818e/02deb767-d401-4ebf-ad18-570b3084adff
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC006 post apisearch returns jobs filtered by core promise
- **Test Code:** [TC006_post_apisearch_returns_jobs_filtered_by_core_promise.py](./TC006_post_apisearch_returns_jobs_filtered_by_core_promise.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 99, in <module>
  File "<string>", line 28, in test_post_api_search_core_promise
AssertionError: Expected 200 for valid request, got 403

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/ae7120ff-9a17-44f8-9761-14be2be1818e/afa5d56f-72a1-4c41-b84f-6239e3baa42e
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC007 post apigeneratecls generates cover letter for job
- **Test Code:** [TC007_post_apigeneratecls_generates_cover_letter_for_job.py](./TC007_post_apigeneratecls_generates_cover_letter_for_job.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 100, in <module>
  File "<string>", line 34, in test_post_api_generate_cls
AssertionError: Job search failed with 403

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/ae7120ff-9a17-44f8-9761-14be2be1818e/ae232108-2d9f-4f28-8d11-99add21957b7
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC008 get apigenerateclsstream streams cover letter generation tokens
- **Test Code:** [TC008_get_apigenerateclsstream_streams_cover_letter_generation_tokens.py](./TC008_get_apigenerateclsstream_streams_cover_letter_generation_tokens.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 78, in <module>
  File "<string>", line 32, in test_get_generate_cls_stream
AssertionError: Expected 200 for /api/search but got 403

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/ae7120ff-9a17-44f8-9761-14be2be1818e/9d673982-b37c-4f35-bcc2-ad35c448b320
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC009 get apidemoverify verifies job url open status
- **Test Code:** [TC009_get_apidemoverify_verifies_job_url_open_status.py](./TC009_get_apidemoverify_verifies_job_url_open_status.py)
- **Test Error:** Traceback (most recent call last):
  File "<string>", line 15, in test_get_apidemo_verify
AssertionError: Expected 200, got 403

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 32, in <module>
  File "<string>", line 20, in test_get_apidemo_verify
AssertionError: Failed valid url test: Expected 200, got 403

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/ae7120ff-9a17-44f8-9761-14be2be1818e/2b3fd49b-d71a-440c-8b50-40d8764092dd
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC010 post apistripecreatecheckout creates stripe checkout session
- **Test Code:** [TC010_post_apistripecreatecheckout_creates_stripe_checkout_session.py](./TC010_post_apistripecreatecheckout_creates_stripe_checkout_session.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 57, in <module>
  File "<string>", line 30, in test_post_apistripecreatecheckout_creates_stripe_checkout_session
  File "<string>", line 23, in get_auth_token
AssertionError: User sync failed

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/ae7120ff-9a17-44f8-9761-14be2be1818e/9d7e4fc8-2276-4bcd-a546-d930d4ff63d6
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---


## 3️⃣ Coverage & Matching Metrics

- **0.00** of tests passed

| Requirement        | Total Tests | ✅ Passed | ❌ Failed  |
|--------------------|-------------|-----------|------------|
| ...                | ...         | ...       | ...        |
---


## 4️⃣ Key Gaps / Risks
{AI_GNERATED_KET_GAPS_AND_RISKS}
---