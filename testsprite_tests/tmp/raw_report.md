
# TestSprite AI Testing Report(MCP)

---

## 1️⃣ Document Metadata
- **Project Name:** jobpilot
- **Date:** 2026-04-15
- **Prepared by:** TestSprite AI Team

---

## 2️⃣ Requirement Validation Summary

#### Test TC001 Complete onboarding with profile criteria and a PDF/DOCX resume to reach parsed profile and initial results
- **Test Code:** [TC001_Complete_onboarding_with_profile_criteria_and_a_PDFDOCX_resume_to_reach_parsed_profile_and_initial_results.py](./TC001_Complete_onboarding_with_profile_criteria_and_a_PDFDOCX_resume_to_reach_parsed_profile_and_initial_results.py)
- **Test Error:** TEST BLOCKED

The login page could not be reached — the /login route returns a 404, so I cannot sign in to continue the onboarding steps.

Observations:
- Navigated to http://localhost:3001/login and the page shows '404 This page could not be found.'
- No login form fields are present; only navigation links and the 404 message are visible.
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/3091907b-8a62-4b6a-bbdd-bff6ce501730/b37eaa29-5ab0-4dd9-8491-80a8673e0b85
- **Status:** BLOCKED
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC002 Apply region and degree filters to refine Core Promise job results
- **Test Code:** [TC002_Apply_region_and_degree_filters_to_refine_Core_Promise_job_results.py](./TC002_Apply_region_and_degree_filters_to_refine_Core_Promise_job_results.py)
- **Test Error:** TEST BLOCKED

The login flow is not reachable — I cannot access the dashboard to verify filters as a returning user.

Observations:
- Clicking 'Sign in' did not open a login modal or show email/password fields.
- Navigating to /login returned a 404 page.
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/3091907b-8a62-4b6a-bbdd-bff6ce501730/adb6a063-fc87-4c56-8f81-89355da47ddb
- **Status:** BLOCKED
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC003 Update direction or degree criteria and refresh results
- **Test Code:** [TC003_Update_direction_or_degree_criteria_and_refresh_results.py](./TC003_Update_direction_or_degree_criteria_and_refresh_results.py)
- **Test Error:** TEST BLOCKED

The feature could not be reached — the login page and login form are not accessible, so the test cannot proceed.

Observations:
- Navigating to /login showed a 404 page with the message 'This page could not be found.'
- No login form fields (email/password) are visible on the page.
- Clicking the 'Sign in' link did not reveal a login form in previous attempts.
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/3091907b-8a62-4b6a-bbdd-bff6ce501730/73a36ebd-58de-4437-93c5-375b37be3120
- **Status:** BLOCKED
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC004 Submit a valid job URL in the demo verifier to see a verification result
- **Test Code:** [TC004_Submit_a_valid_job_URL_in_the_demo_verifier_to_see_a_verification_result.py](./TC004_Submit_a_valid_job_URL_in_the_demo_verifier_to_see_a_verification_result.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/3091907b-8a62-4b6a-bbdd-bff6ce501730/88ffe0fe-3453-4f6b-8179-587032adc8cf
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC005 Reject non-PDF/DOCX resume uploads during onboarding
- **Test Code:** [TC005_Reject_non_PDFDOCX_resume_uploads_during_onboarding.py](./TC005_Reject_non_PDFDOCX_resume_uploads_during_onboarding.py)
- **Test Error:** TEST BLOCKED

The onboarding flow could not be reached because the site redirected to Google OAuth sign-in and I do not have credentials to complete that sign-in.

Observations:
- Clicking 'Try free — no card needed' redirected to the Google Accounts sign-in page.
- The Google sign-in form is displayed and the onboarding/upload UI is not accessible without completing OAuth.
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/3091907b-8a62-4b6a-bbdd-bff6ce501730/a52bc121-b56c-4af4-a307-f8499628f711
- **Status:** BLOCKED
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC006 Reject malformed URLs in the demo verifier
- **Test Code:** [TC006_Reject_malformed_URLs_in_the_demo_verifier.py](./TC006_Reject_malformed_URLs_in_the_demo_verifier.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/3091907b-8a62-4b6a-bbdd-bff6ce501730/f7627652-dc04-42f9-841c-f4a21c7468a8
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---


## 3️⃣ Coverage & Matching Metrics

- **33.33** of tests passed

| Requirement        | Total Tests | ✅ Passed | ❌ Failed  |
|--------------------|-------------|-----------|------------|
| ...                | ...         | ...       | ...        |
---


## 4️⃣ Key Gaps / Risks
{AI_GNERATED_KET_GAPS_AND_RISKS}
---