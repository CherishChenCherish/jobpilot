"use client";

import { useState, useEffect } from "react";

type OnboardingData = {
  jobType: string;
  directions: string[];
  visaNeeded: boolean;
};

const STORAGE_KEY = "jobpilot_onboarding_done";

export function useOnboarding() {
  const [show, setShow] = useState(false);
  const [data, setData] = useState<OnboardingData | null>(null);

  useEffect(() => {
    const done = localStorage.getItem(STORAGE_KEY);
    const saved = localStorage.getItem("jobpilot_prefs");
    if (!done) {
      setShow(true);
    } else if (saved) {
      setData(JSON.parse(saved));
    }
  }, []);

  const complete = (d: OnboardingData) => {
    localStorage.setItem(STORAGE_KEY, "true");
    localStorage.setItem("jobpilot_prefs", JSON.stringify(d));
    setData(d);
    setShow(false);
  };

  const dismiss = () => {
    localStorage.setItem(STORAGE_KEY, "true");
    setShow(false);
  };

  return { showOnboarding: show, onboardingData: data, completeOnboarding: complete, dismissOnboarding: dismiss };
}

export function OnboardingModal({ onComplete }: { onComplete: (d: OnboardingData) => void }) {
  const [step, setStep] = useState(0);
  const [jobType, setJobType] = useState("");
  const [directions, setDirections] = useState<string[]>([]);
  const [visa, setVisa] = useState<boolean | null>(null);

  const toggleDir = (d: string) =>
    setDirections(prev => prev.includes(d) ? prev.filter(x => x !== d) : [...prev, d]);

  const finish = (v: boolean) => {
    onComplete({ jobType, directions, visaNeeded: v });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="bg-surface border border-border rounded-2xl p-8 max-w-md w-full mx-4 shadow-2xl">
        {/* Step indicator */}
        <div className="flex gap-1.5 mb-6 justify-center">
          {[0, 1, 2].map(i => (
            <div key={i} className={`h-1 rounded-full transition-all ${
              i === step ? "w-8 bg-accent" : i < step ? "w-8 bg-accent/40" : "w-8 bg-border"
            }`} />
          ))}
        </div>

        {/* Step 0: Job type */}
        {step === 0 && (
          <div className="text-center">
            <h3 className="text-xl font-serif mb-2">What are you looking for?</h3>
            <p className="text-sm text-muted mb-6">We'll tailor your search to match.</p>
            <div className="space-y-3">
              {[
                { v: "intern_2026", l: "Summer 2026 Internship", icon: "\u2600" },
                { v: "new_grad_2027", l: "Full-time 2027", icon: "\uD83C\uDF93" },
                { v: "both", l: "Both — show me everything", icon: "\uD83D\uDD0D" },
              ].map(o => (
                <button key={o.v} onClick={() => { setJobType(o.v); setStep(1); }}
                  className="w-full text-left px-5 py-4 rounded-xl bg-card border border-border hover:border-accent transition flex items-center gap-3">
                  <span className="text-xl">{o.icon}</span>
                  <span className="text-sm">{o.l}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 1: Directions */}
        {step === 1 && (
          <div className="text-center">
            <h3 className="text-xl font-serif mb-2">Which areas interest you?</h3>
            <p className="text-sm text-muted mb-6">Select all that apply.</p>
            <div className="flex flex-wrap gap-2 justify-center mb-6">
              {[
                "DS/ML", "Software Engineering", "Data Engineering",
                "Health Informatics", "Business Analytics", "Product Management",
                "Quantitative Finance", "Research / NLP", "Consulting",
              ].map(d => (
                <button key={d} onClick={() => toggleDir(d)}
                  className={`px-3 py-2 rounded-lg text-sm transition border ${
                    directions.includes(d) ? "border-accent text-accent bg-accent/10" : "border-border text-muted hover:border-muted"
                  }`}>{d}</button>
              ))}
            </div>
            <button onClick={() => { if (directions.length > 0) setStep(2); }}
              disabled={directions.length === 0}
              className={`w-full py-3 rounded-lg text-sm font-semibold transition ${
                directions.length > 0 ? "btn-blue" : "bg-card text-muted/40 cursor-not-allowed"
              }`}>
              Continue ({directions.length} selected)
            </button>
          </div>
        )}

        {/* Step 2: Visa */}
        {step === 2 && (
          <div className="text-center">
            <h3 className="text-xl font-serif mb-2">Do you need visa sponsorship?</h3>
            <p className="text-sm text-muted mb-6">We'll filter out jobs that don't sponsor.</p>
            <div className="space-y-3">
              <button onClick={() => finish(true)}
                className="w-full text-left px-5 py-4 rounded-xl bg-card border border-border hover:border-accent transition">
                <span className="text-sm font-semibold">Yes</span>
                <span className="text-xs text-muted block mt-0.5">I need OPT / CPT / H-1B sponsorship</span>
              </button>
              <button onClick={() => finish(false)}
                className="w-full text-left px-5 py-4 rounded-xl bg-card border border-border hover:border-accent transition">
                <span className="text-sm font-semibold">No</span>
                <span className="text-xs text-muted block mt-0.5">I'm authorized to work in the US</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
