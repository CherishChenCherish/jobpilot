"use client";

import { signIn, useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL || "https://jobpilot-v1.up.railway.app";

export default function Landing() {
  const { data: session } = useSession();
  const router = useRouter();
  const [demoUrl, setDemoUrl] = useState("");
  const [demoResult, setDemoResult] = useState<any>(null);
  const [demoLoading, setDemoLoading] = useState(false);

  useEffect(() => {
    if (session) router.push("/dashboard");
  }, [session, router]);

  const runDemo = async () => {
    if (!demoUrl.trim()) return;
    setDemoLoading(true);
    setDemoResult(null);
    try {
      const r = await fetch(`${API}/api/demo-verify?url=${encodeURIComponent(demoUrl.trim())}`);
      setDemoResult(await r.json());
    } catch {
      setDemoResult({ status: "\u26A0 Unverified", reason: "Could not reach verification service" });
    }
    setDemoLoading(false);
  };

  return (
    <main className="min-h-screen">

      {/* Hero */}
      <section className="max-w-4xl mx-auto px-8 pt-20 pb-16 text-center">
        <h1 className="text-5xl md:text-7xl font-serif leading-tight tracking-tight">
          Find jobs that
          <br />
          are <span className="text-accent">actually</span>
          <br />
          still open.
        </h1>
        <p className="mt-6 text-lg text-muted max-w-xl mx-auto leading-relaxed">
          Upload your resume. We verify every posting is open,
          then write your cover letters. No keyword stuffing. No generic AI.
        </p>
        <div className="mt-10 flex flex-col items-center gap-3">
          <button onClick={() => signIn("google")} className="btn-gold text-lg">
            Try free &mdash; no card needed
          </button>
          <span className="text-sm text-muted">
            3 free searches &bull; Takes 2 minutes
          </span>
        </div>
      </section>

      {/* ── Demo verifier (CHANGE 1: prove it before signup) ── */}
      <section className="max-w-2xl mx-auto px-8 py-16">
        <div className="bg-surface rounded-2xl p-6 md:p-8 border border-border">
          <h2 className="text-xl font-serif mb-2 text-center">Is that job posting still open?</h2>
          <p className="text-sm text-muted text-center mb-6">Paste any job URL. We'll check in 10 seconds. Free, no signup.</p>
          <div className="flex gap-2">
            <input
              type="text"
              value={demoUrl}
              onChange={e => setDemoUrl(e.target.value)}
              onKeyDown={e => e.key === "Enter" && runDemo()}
              placeholder="https://boards.greenhouse.io/company/jobs/12345"
              className="flex-1 bg-card border border-border rounded-lg px-4 py-3 text-sm text-white placeholder-muted/40 focus:border-accent outline-none"
            />
            <button onClick={runDemo} disabled={demoLoading || !demoUrl.trim()}
              className={`px-5 py-3 rounded-lg text-sm font-semibold transition shrink-0 ${
                demoLoading ? "bg-card text-muted" : "btn-blue"
              }`}>
              {demoLoading ? "\u21BB Checking..." : "Check"}
            </button>
          </div>

          {demoResult && (
            <div className={`mt-5 p-4 rounded-lg border ${
              demoResult.status?.includes("Open") ? "bg-open/10 border-open/30" :
              demoResult.status?.includes("Closed") ? "bg-closed/10 border-closed/30" :
              "bg-warn/10 border-warn/30"
            }`}>
              <div className="flex items-center gap-2 mb-2">
                <span className={`text-lg ${
                  demoResult.status?.includes("Open") ? "text-open" :
                  demoResult.status?.includes("Closed") ? "text-closed" : "text-warn"
                }`}>
                  {demoResult.status?.includes("Open") ? "\u2713" : demoResult.status?.includes("Closed") ? "\u2717" : "\u26A0"}
                </span>
                <span className="font-semibold text-sm">{demoResult.status}</span>
                {demoResult.confidence && (
                  <span className="text-[10px] text-muted">({demoResult.confidence} confidence)</span>
                )}
              </div>
              {(demoResult.job_title || demoResult.company) && (
                <div className="text-sm text-muted mb-1">
                  {demoResult.company && <span className="text-white">{demoResult.company}</span>}
                  {demoResult.company && demoResult.job_title && " \u2014 "}
                  {demoResult.job_title}
                </div>
              )}
              <div className="text-xs text-muted">{demoResult.reason}</div>
              {demoResult.posting_age_days && (
                <div className="text-xs text-muted mt-1">Posted ~{demoResult.posting_age_days} days ago</div>
              )}
              <div className="mt-4 pt-3 border-t border-border/50 text-center">
                <button onClick={() => signIn("google")} className="btn-gold text-sm">
                  Sign up free to verify all your jobs at once
                </button>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* How it works */}
      <section className="max-w-5xl mx-auto px-8 py-20">
        <h2 className="text-3xl font-serif text-center mb-16">How it works</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {[
            {
              step: "01",
              title: "Upload your resume",
              desc: "PDF or DOCX. We extract every skill, metric, and achievement into your Profile Vault.",
            },
            {
              step: "02",
              title: "We find + verify",
              desc: "Search Greenhouse, Lever, and company sites. Then verify each posting is actually still open.",
            },
            {
              step: "03",
              title: "Download results",
              desc: "Get an Excel with verified jobs, custom cover letters (scored 1-5), and an application tracker.",
            },
          ].map((item) => (
            <div key={item.step} className="bg-surface rounded-xl p-8 border border-border">
              <div className="text-accent font-mono text-sm mb-3">{item.step}</div>
              <h3 className="text-xl font-serif mb-3">{item.title}</h3>
              <p className="text-muted text-sm leading-relaxed">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pain points */}
      <section className="max-w-3xl mx-auto px-8 py-16 text-center">
        <h2 className="text-3xl font-serif mb-6">Sound familiar?</h2>
        <div className="space-y-4 text-muted text-lg">
          <p>&ldquo;Applied to 30 jobs. 12 were already closed. Found out after wasting 6 hours.&rdquo;</p>
          <p>&ldquo;AI wrote me a cover letter that started with &lsquo;I am excited to apply.&rsquo; So did everyone else&rsquo;s.&rdquo;</p>
        </div>
        <p className="mt-8 text-accent font-semibold">We built JobPilot to fix this.</p>
      </section>

      {/* Pricing preview */}
      <section className="max-w-4xl mx-auto px-8 py-20" id="pricing">
        <h2 className="text-3xl font-serif text-center mb-12">Simple pricing</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-2xl mx-auto">
          {/* Free */}
          <div className="bg-surface rounded-xl p-8 border border-border">
            <div className="text-sm text-muted mb-1">Free</div>
            <div className="text-4xl font-bold mb-4">$0</div>
            <ul className="space-y-3 text-sm text-muted mb-8">
              <li className="flex items-center gap-2"><span className="text-open">&#10003;</span> 3 searches</li>
              <li className="flex items-center gap-2"><span className="text-open">&#10003;</span> Resume parsing</li>
              <li className="flex items-center gap-2"><span className="text-open">&#10003;</span> Job verification</li>
              <li className="flex items-center gap-2"><span className="text-open">&#10003;</span> Cover letters</li>
              <li className="flex items-center gap-2"><span className="text-open">&#10003;</span> Excel export</li>
            </ul>
            <button onClick={() => signIn("google")} className="btn-blue w-full">
              Get started
            </button>
          </div>
          {/* Pro */}
          <div className="bg-surface rounded-xl p-8 border-2 border-gold relative">
            <div className="absolute -top-3 right-6 bg-gold text-black text-xs font-bold px-3 py-1 rounded-full">
              RECOMMENDED
            </div>
            <div className="text-sm text-gold mb-1">Pro</div>
            <div className="text-4xl font-bold mb-1">$12<span className="text-lg text-muted">/mo</span></div>
            <p className="text-xs text-muted mb-4">Cancel anytime</p>
            <ul className="space-y-3 text-sm text-muted mb-8">
              <li className="flex items-center gap-2"><span className="text-gold">&#10003;</span> Unlimited searches</li>
              <li className="flex items-center gap-2"><span className="text-gold">&#10003;</span> Everything in Free</li>
              <li className="flex items-center gap-2"><span className="text-gold">&#10003;</span> Priority verification</li>
              <li className="flex items-center gap-2"><span className="text-gold">&#10003;</span> Visa sponsor check</li>
              <li className="flex items-center gap-2"><span className="text-gold">&#10003;</span> Interview prep Q&A</li>
            </ul>
            <button onClick={() => signIn("google")} className="btn-gold w-full">Upgrade to Pro</button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-8 mt-16">
        <div className="max-w-6xl mx-auto px-8 flex items-center justify-between text-sm text-muted">
          <span>JobPilot &copy; 2026</span>
          <span>Built by Cherish Chen</span>
        </div>
      </footer>
    </main>
  );
}
