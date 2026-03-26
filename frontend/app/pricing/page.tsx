"use client";

import { signIn } from "next-auth/react";
import Link from "next/link";

export default function Pricing() {
  return (
    <main className="min-h-screen">
      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-5 max-w-6xl mx-auto">
        <Link href="/" className="text-2xl font-bold tracking-tight">
          Job<span className="text-accent">Pilot</span>
        </Link>
        <button onClick={() => signIn("google")} className="text-sm bg-white/10 hover:bg-white/20 px-4 py-2 rounded-lg transition">
          Sign in
        </button>
      </nav>

      <div className="max-w-4xl mx-auto px-8 py-20">
        <h1 className="text-4xl font-serif text-center mb-4">Simple, honest pricing</h1>
        <p className="text-center text-muted mb-16">No hidden fees. No annual lock-in. Cancel anytime.</p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-2xl mx-auto mb-20">
          {/* Free */}
          <div className="bg-surface rounded-xl p-8 border border-border">
            <div className="text-sm text-muted mb-1">Free</div>
            <div className="text-5xl font-bold mb-2">$0</div>
            <p className="text-sm text-muted mb-6">Perfect to try it out</p>
            <ul className="space-y-3 text-sm text-muted mb-8">
              <li>&#10003; 3 full searches</li>
              <li>&#10003; Resume parsing</li>
              <li>&#10003; Job verification</li>
              <li>&#10003; Cover letter generation</li>
              <li>&#10003; Excel export</li>
            </ul>
            <button onClick={() => signIn("google")} className="btn-blue w-full">Start free</button>
          </div>

          {/* Pro */}
          <div className="bg-surface rounded-xl p-8 border-2 border-gold relative">
            <div className="absolute -top-3 right-6 bg-gold text-black text-xs font-bold px-3 py-1 rounded-full">BEST VALUE</div>
            <div className="text-sm text-gold mb-1">Pro</div>
            <div className="text-5xl font-bold mb-2">$12<span className="text-xl text-muted">/mo</span></div>
            <p className="text-sm text-muted mb-6">For active job seekers</p>
            <ul className="space-y-3 text-sm text-muted mb-8">
              <li className="text-gold">&#10003; Unlimited searches</li>
              <li>&#10003; Everything in Free</li>
              <li>&#10003; Priority verification speed</li>
              <li>&#10003; Visa sponsor database</li>
              <li>&#10003; Interview prep Q&A</li>
              <li>&#10003; Search history</li>
            </ul>
            <button className="btn-gold w-full">Upgrade to Pro</button>
          </div>
        </div>

        {/* FAQ */}
        <h2 className="text-2xl font-serif text-center mb-10">FAQ</h2>
        <div className="space-y-6 max-w-2xl mx-auto">
          {[
            {
              q: "Why $12/month?",
              a: "We run AI verification on every job posting and generate custom cover letters for each match. This costs us real money per search. $12/month keeps us sustainable while being 50-75% cheaper than Jobscan ($50) or ResumeWorded ($49).",
            },
            {
              q: "What makes this different from Teal or Jobscan?",
              a: "They optimize for ATS keyword scores. We optimize for interview rate. We verify every job is actually still open (40% of listings are ghost jobs), and our cover letters start with your strongest metric instead of 'I am writing to apply.'",
            },
            {
              q: "Can I cancel anytime?",
              a: "Yes. Cancel with one click. No questions asked. You keep access until the end of your billing period.",
            },
            {
              q: "Do you support international students?",
              a: "Yes. We check every employer's H1B sponsorship history and flag positions that explicitly don't sponsor. We also filter for OPT/CPT-friendly roles.",
            },
            {
              q: "How accurate is the job verification?",
              a: "We verify directly against Greenhouse and Lever APIs (100% accurate for those platforms), and use HTML analysis for other sites. Our false positive rate on 'open' status is under 5%.",
            },
          ].map((faq, i) => (
            <div key={i} className="bg-surface rounded-xl p-6 border border-border">
              <h3 className="font-semibold mb-2">{faq.q}</h3>
              <p className="text-sm text-muted leading-relaxed">{faq.a}</p>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
