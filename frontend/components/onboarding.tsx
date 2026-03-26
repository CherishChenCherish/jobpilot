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

  const toggleDir = (d: string) =>
    setDirections(prev => prev.includes(d) ? prev.filter(x => x !== d) : [...prev, d]);

  const finish = (v: boolean) => {
    onComplete({ jobType, directions, visaNeeded: v });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md"
         style={{ animation: "fadeIn 0.3s ease" }}>
      <div className="max-w-md w-full mx-4 rounded-2xl shadow-2xl overflow-hidden"
           style={{
             background: "#1E293B",
             border: "1px solid #334155",
             animation: "slideUp 0.4s ease",
           }}>
        {/* Step indicator */}
        <div className="flex gap-2 pt-7 pb-2 justify-center">
          {[0, 1, 2].map(i => (
            <div key={i} className="h-1.5 rounded-full transition-all duration-500"
              style={{
                width: i === step ? 32 : 32,
                background: i === step ? "#3B82F6" : i < step ? "#3B82F680" : "#334155",
              }} />
          ))}
        </div>

        <div className="px-8 pb-8 pt-4">
          {/* Step 0: Job type */}
          {step === 0 && (
            <div className="text-center">
              <h3 className="text-2xl font-serif mb-2" style={{ color: "#F1F5F9" }}>
                What are you looking for?
              </h3>
              <p className="text-sm mb-8" style={{ color: "#CBD5E1" }}>
                We&apos;ll tailor your search to match.
              </p>
              <div className="space-y-3">
                {[
                  { v: "intern_2026", l: "Summer 2026 Internship", sub: "10-12 week program", icon: "\u2600\uFE0F" },
                  { v: "new_grad_2027", l: "Full-time 2027", sub: "Starting after graduation", icon: "\uD83C\uDF93" },
                  { v: "both", l: "Both \u2014 show me everything", sub: "We\u2019ll search both pipelines", icon: "\uD83D\uDD0D" },
                ].map(o => (
                  <button key={o.v} onClick={() => { setJobType(o.v); setStep(1); }}
                    className="w-full text-left px-5 py-4 rounded-xl transition-all duration-200 flex items-center gap-4 group"
                    style={{
                      background: "#0F172A",
                      border: "1px solid #334155",
                    }}
                    onMouseEnter={e => { e.currentTarget.style.borderColor = "#3B82F6"; e.currentTarget.style.background = "#1A2744"; }}
                    onMouseLeave={e => { e.currentTarget.style.borderColor = "#334155"; e.currentTarget.style.background = "#0F172A"; }}>
                    <span className="text-2xl">{o.icon}</span>
                    <div>
                      <span className="text-sm font-semibold block" style={{ color: "#F1F5F9" }}>{o.l}</span>
                      <span className="text-xs block mt-0.5" style={{ color: "#94A3B8" }}>{o.sub}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step 1: Directions */}
          {step === 1 && (
            <div className="text-center">
              <h3 className="text-2xl font-serif mb-2" style={{ color: "#F1F5F9" }}>
                Which areas interest you?
              </h3>
              <p className="text-sm mb-6" style={{ color: "#CBD5E1" }}>
                Select all that apply.
              </p>
              <div className="flex flex-wrap gap-2 justify-center mb-8">
                {[
                  "DS / ML", "Software Engineering", "Data Engineering",
                  "Health Informatics", "Business Analytics", "Product Management",
                  "Quantitative Finance", "Research / NLP", "Consulting",
                ].map(d => {
                  const selected = directions.includes(d);
                  return (
                    <button key={d} onClick={() => toggleDir(d)}
                      className="px-4 py-2.5 rounded-lg text-sm transition-all duration-200"
                      style={{
                        background: selected ? "#3B82F620" : "#0F172A",
                        border: `1px solid ${selected ? "#3B82F6" : "#334155"}`,
                        color: selected ? "#60A5FA" : "#E2E8F0",
                      }}>
                      {d}
                    </button>
                  );
                })}
              </div>
              <button onClick={() => { if (directions.length > 0) setStep(2); }}
                disabled={directions.length === 0}
                className="w-full py-3.5 rounded-xl text-sm font-semibold transition-all duration-200"
                style={{
                  background: directions.length > 0 ? "#2563EB" : "#1E293B",
                  color: directions.length > 0 ? "#FFFFFF" : "#64748B",
                  cursor: directions.length > 0 ? "pointer" : "not-allowed",
                }}>
                Continue ({directions.length} selected)
              </button>
            </div>
          )}

          {/* Step 2: Visa */}
          {step === 2 && (
            <div className="text-center">
              <h3 className="text-2xl font-serif mb-2" style={{ color: "#F1F5F9" }}>
                Do you need visa sponsorship?
              </h3>
              <p className="text-sm mb-8" style={{ color: "#CBD5E1" }}>
                We&apos;ll filter out jobs that don&apos;t sponsor.
              </p>
              <div className="space-y-3">
                {[
                  { v: true, l: "Yes, I need sponsorship", sub: "OPT / CPT / H-1B" },
                  { v: false, l: "No, I\u2019m authorized", sub: "US citizen or permanent resident" },
                ].map(o => (
                  <button key={String(o.v)} onClick={() => finish(o.v)}
                    className="w-full text-left px-5 py-4 rounded-xl transition-all duration-200"
                    style={{ background: "#0F172A", border: "1px solid #334155" }}
                    onMouseEnter={e => { e.currentTarget.style.borderColor = "#3B82F6"; e.currentTarget.style.background = "#1A2744"; }}
                    onMouseLeave={e => { e.currentTarget.style.borderColor = "#334155"; e.currentTarget.style.background = "#0F172A"; }}>
                    <span className="text-sm font-semibold block" style={{ color: "#F1F5F9" }}>{o.l}</span>
                    <span className="text-xs block mt-1" style={{ color: "#94A3B8" }}>{o.sub}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <style jsx>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(20px) scale(0.97); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
      `}</style>
    </div>
  );
}
