"use client";

import { useSession, signOut } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, useRef, useCallback, Suspense } from "react";
import { useOnboarding, OnboardingModal } from "@/components/onboarding";

const API = process.env.NEXT_PUBLIC_API_URL || "https://jobpilot-v1.up.railway.app";

type Audit = {
  status: string;
  confidence: string;
  reason: string;
  posting_age_days: number | null;
  ghost_risk: string;
  degree_match: string;
  visa: string;
  needs_manual_check: boolean;
};

type CoverLetter = {
  text: string;
  word_count: number;
  score: number;
  max_score: number;
  needs_review: boolean;
  gates: Record<string, boolean>;
  tone: string;
};

type Job = {
  company: string;
  title: string;
  location: string;
  remote: boolean;
  apply_url: string;
  job_board: string;
  recommended_cv: string;
  audit: Audit;
  cover_letter?: CoverLetter;
};

type AuditSummary = {
  jobs_searched: number;
  jobs_verified: number;
  jobs_open: number;
  jobs_unverified: number;
  cl_generated: number;
  avg_cl_score: number;
  max_cl_score: number;
  drop_reasons: Record<string, number>;
  cl_status?: string;
};

type SearchResult = {
  search_id: number | null;
  jobs: Job[];
  audit_summary: AuditSummary;
  errors: string[] | null;
};

type Phase = "idle" | "uploading" | "parsed" | "searching" | "verifying" | "generating" | "done";

// ── Confidence badge component ──────────────────────────
function ConfBadge({ level, label }: { level: string; label: string }) {
  const cls = level === "high" ? "text-open border-open/30 bg-open/10"
    : level === "medium" ? "text-warn border-warn/30 bg-warn/10"
    : "text-closed border-closed/30 bg-closed/10";
  return <span className={`text-[10px] px-1.5 py-0.5 rounded border ${cls}`}>{label}: {level}</span>;
}

// ── Status badge ────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
  const cls = status.includes("Open") ? "badge-open"
    : status.includes("Closed") ? "badge-closed" : "badge-warn";
  return <span className={`text-xs px-2 py-0.5 rounded-full ${cls}`}>{status}</span>;
}

function DashboardInner() {
  const { data: session, status: authStatus } = useSession();
  const router = useRouter();
  const searchParams = useSearchParams();
  const fileRef = useRef<HTMLInputElement>(null);

  const [user, setUser] = useState<any>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [profile, setProfile] = useState<any>(null);
  const [result, setResult] = useState<SearchResult | null>(null);
  const [expandedCL, setExpandedCL] = useState<number | null>(null);
  const [copied, setCopied] = useState<number | null>(null);
  const [dragover, setDragover] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [progressLog, setProgressLog] = useState<string[]>([]);
  const [showAudit, setShowAudit] = useState(false);

  // Onboarding
  const { showOnboarding, onboardingData, completeOnboarding } = useOnboarding();

  // Preferences (pre-filled from onboarding if available)
  const [jobType, setJobType] = useState("intern_2026");
  const [degreeTarget, setDegreeTarget] = useState("masters");
  const [directions, setDirections] = useState<string[]>(["DS/ML", "Health Informatics"]);
  const [customDirection, setCustomDirection] = useState("");
  const [visaNeeded, setVisaNeeded] = useState(true);
  const [prefsInitialized, setPrefsInitialized] = useState(false);

  // Pre-fill from onboarding answers
  useEffect(() => {
    if (onboardingData && !prefsInitialized) {
      if (onboardingData.jobType && onboardingData.jobType !== "both") setJobType(onboardingData.jobType);
      if (onboardingData.directions?.length) setDirections(onboardingData.directions);
      setVisaNeeded(onboardingData.visaNeeded);
      setPrefsInitialized(true);
    }
  }, [onboardingData, prefsInitialized]);

  useEffect(() => { if (authStatus === "unauthenticated") router.push("/"); }, [authStatus, router]);

  useEffect(() => {
    fetch(`${API}/api/me`).then(r => r.json()).then(setUser)
      .catch(() => setUser({ name: "User", plan: "free", searches_used: 0 }));
  }, []);

  // Stripe upgrade toast
  useEffect(() => {
    if (searchParams.get("upgraded") === "1") {
      setToast("Welcome to Pro! Unlimited searches unlocked.");
      setTimeout(() => setToast(null), 5000);
      window.history.replaceState({}, "", "/dashboard");
    }
  }, [searchParams]);

  // ── Upload ────────────────────────────────────────────
  const handleUpload = useCallback(async (file: File) => {
    setError(null);
    setPhase("uploading");
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch(`${API}/api/parse`, { method: "POST", body: formData });
      const data = await res.json();
      if (data.error) { setError(data.error); setPhase("idle"); return; }
      setProfile(data.profile);
      setPhase("parsed");
    } catch { setError("Upload failed. Check your connection and try again."); setPhase("idle"); }
  }, []);

  // ── Search + per-job CL generation ──────────────────
  const [clsLoading, setClsLoading] = useState(false);  // kept for header display
  const [generatingCL, setGeneratingCL] = useState<number | null>(null);  // index of job currently generating CL

  const handleSearch = useCallback(async () => {
    if (!profile) return;
    if (user?.plan === "free" && (user?.searches_used || 0) >= 3) {
      setError("You've used all 3 free searches. Upgrade to Pro for unlimited.");
      return;
    }
    setError(null);
    setPhase("searching");
    setProgressLog(["Searching Greenhouse, Lever, and company career pages..."]);

    const timer1 = setTimeout(() => {
      setPhase("verifying");
      setProgressLog(prev => [...prev, "Verifying each posting is still accepting applications..."]);
    }, 3000);

    try {
      // PHASE 1: Search + verify (fast, ~15s)
      const searchBody = JSON.stringify({
        google_id: (session?.user as any)?.google_id,
        profile, prefs: { directions, job_type: jobType, degree_target: degreeTarget, visa_needed: visaNeeded },
      });
      const res = await fetch(`${API}/api/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: searchBody,
      });
      clearTimeout(timer1);
      const text = await res.text();
      let data;
      try {
        data = JSON.parse(text);
      } catch {
        // Server returned HTML (timeout/502) instead of JSON
        if (text.includes("<!doctype") || text.includes("<!DOCTYPE") || text.includes("<html")) {
          setError("Search timed out. The server took too long. Please try again with fewer directions selected.");
          setPhase("parsed");
          return;
        }
        // Try cleaning control characters
        try { data = JSON.parse(text.replace(/[\x00-\x1f\x7f]/g, ' ')); }
        catch { setError("Invalid response from server. Please try again."); setPhase("parsed"); return; }
      }
      if (data.error === "quota_exceeded") {
        setError("Free plan limit reached. Upgrade to Pro for unlimited searches.");
        setPhase("parsed");
        return;
      }

      // Show jobs immediately (no CLs yet)
      setResult(data);
      setPhase("done");
      if (user) setUser({ ...user, searches_used: (user.searches_used || 0) + 1 });

      // No automatic CL generation — user clicks "Write CL" per job
    } catch (err) {
      clearTimeout(timer1);
      setError(`Search failed: ${err instanceof Error ? err.message : "Unknown error"}. Please try again.`);
      setPhase("parsed");
    }
  }, [profile, directions, jobType, degreeTarget, visaNeeded, session, user]);

  // ── Generate CL for one job (on-demand) ─────────────
  const handleGenerateCL = useCallback(async (idx: number) => {
    if (!result || !profile || generatingCL !== null) return;
    const job = result.jobs[idx];
    if (!job || job.cover_letter?.text) return;  // already has CL

    setGeneratingCL(idx);
    try {
      const res = await fetch(`${API}/api/generate-cls`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jobs: [job], profile }),
      });
      const text = await res.text();
      let data;
      try { data = JSON.parse(text); }
      catch { data = JSON.parse(text.replace(/[\x00-\x1f\x7f]/g, ' ')); }

      if (data.cover_letters?.[0]?.cover_letter) {
        setResult(prev => {
          if (!prev) return prev;
          const updated = { ...prev, jobs: [...prev.jobs] };
          updated.jobs[idx] = { ...updated.jobs[idx], cover_letter: data.cover_letters[0].cover_letter };
          return updated;
        });
        setExpandedCL(idx);  // Auto-expand the CL
      }
    } catch {
      setError("Cover letter generation failed. Please try again.");
    }
    setGeneratingCL(null);
  }, [result, profile, generatingCL]);

  // ── Download ──────────────────────────────────────────
  const handleDownload = useCallback(async () => {
    if (!result?.jobs) return;
    try {
      const res = await fetch(`${API}/api/export-direct`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jobs: result.jobs, name: profile?.name || "User" }),
      });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `JobPilot_${(profile?.name || "User").replace(/\s/g, "_")}_${new Date().toISOString().slice(0, 10)}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch { setError("Download failed."); }
  }, [result, profile]);

  const copyCL = (idx: number, text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(idx);
    setTimeout(() => setCopied(null), 2000);
  };

  const toggleDir = (d: string) => setDirections(prev => prev.includes(d) ? prev.filter(x => x !== d) : [...prev, d]);

  if (authStatus === "loading") return <div className="flex items-center justify-center min-h-screen text-muted">Loading...</div>;

  const quota = user?.plan === "free" ? `${user?.searches_used || 0} of 3 free searches used` : "Pro \u2014 Unlimited";
  const isProcessing = ["searching", "verifying", "generating", "uploading"].includes(phase);

  return (
    <main className="min-h-screen">
      {/* Onboarding modal (CHANGE 2: first-time user) */}
      {showOnboarding && <OnboardingModal onComplete={completeOnboarding} />}

      {/* Toast */}
      {toast && (
        <div className="fixed top-4 right-4 z-50 bg-open/20 border border-open/40 text-open px-4 py-3 rounded-lg text-sm shadow-lg animate-fade-in">
          {toast}
        </div>
      )}

      {/* Header */}
      <header className="flex items-center justify-between px-4 md:px-6 py-4 border-b border-border max-w-7xl mx-auto">
        <div className="text-xl font-bold">Job<span className="text-accent">Pilot</span></div>
        <div className="flex items-center gap-3">
          <span className="text-[11px] px-2.5 py-1 rounded-full bg-surface border border-border text-muted hidden sm:inline">{quota}</span>
          <span className="text-sm text-muted hidden md:inline">{session?.user?.name || user?.name}</span>
          <button onClick={() => signOut()} className="text-xs text-muted hover:text-white">Sign out</button>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 md:px-6 py-6 md:py-8">
        {error && (
          <div className="mb-6 p-4 bg-closed/10 border border-closed/30 rounded-lg text-sm flex items-start gap-3">
            <span className="text-closed shrink-0 mt-0.5">!</span>
            <div className="text-closed/90">{error}</div>
            <button onClick={() => setError(null)} className="text-closed/50 hover:text-closed ml-auto text-xs shrink-0">dismiss</button>
          </div>
        )}

        {/* ═══ UPLOAD + PREFS (idle or parsed) ═══ */}
        {(phase === "idle" || phase === "parsed" || phase === "uploading") && !result && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 md:gap-8">
            {/* Left: Upload / Profile */}
            <div>
              <h2 className="text-2xl font-serif mb-5">
                {phase === "parsed" ? "Your profile" : "Upload your resume"}
              </h2>

              {phase === "uploading" && (
                <div className="upload-zone rounded-xl p-12 text-center">
                  <div className="text-2xl step-active">...</div>
                  <p className="text-muted mt-2">Parsing your resume...</p>
                </div>
              )}

              {phase === "idle" && (
                <div
                  className={`upload-zone rounded-xl p-10 md:p-12 text-center cursor-pointer ${dragover ? "dragover" : ""}`}
                  onClick={() => fileRef.current?.click()}
                  onDragOver={e => { e.preventDefault(); setDragover(true); }}
                  onDragLeave={() => setDragover(false)}
                  onDrop={e => { e.preventDefault(); setDragover(false); const f = e.dataTransfer.files[0]; if (f) handleUpload(f); }}
                >
                  <div className="text-4xl mb-3 opacity-50"></div>
                  <p className="text-muted mb-1">Drop your PDF or DOCX here</p>
                  <p className="text-xs text-muted/60">or click to browse &middot; max 10MB</p>
                  <input ref={fileRef} type="file" accept=".pdf,.docx,.doc" className="hidden"
                    onChange={e => { const f = e.target.files?.[0]; if (f) handleUpload(f); }} />
                </div>
              )}

              {/* ── Parsed profile card (Moment 1: show what we understood) ── */}
              {phase === "parsed" && profile && (
                <div className="bg-surface rounded-xl border border-border overflow-hidden">
                  {/* Confidence header */}
                  <div className={`px-5 py-3 flex items-center justify-between ${
                    profile.extraction_confidence?.score >= 80 ? "bg-open/10 border-b border-open/20" :
                    profile.extraction_confidence?.score >= 50 ? "bg-warn/10 border-b border-warn/20" :
                    "bg-closed/10 border-b border-closed/20"
                  }`}>
                    <span className="text-sm font-semibold">
                      {profile.extraction_confidence?.score >= 80 ? "\u2713 Profile parsed successfully" :
                       profile.extraction_confidence?.score >= 50 ? "\u26A0 Partial extraction \u2014 review below" :
                       "\u26A0 Low confidence \u2014 please check all fields"}
                    </span>
                    <span className="text-xs text-muted">
                      {profile.extraction_confidence?.score || "?"}% confidence
                    </span>
                  </div>

                  <div className="p-5 space-y-4">
                    {/* Name + contact */}
                    <div>
                      <div className="text-lg font-semibold">{profile.name || "Name not found"}</div>
                      <div className="text-sm text-muted">{profile.email} &middot; {profile.phone}</div>
                    </div>

                    {/* Education */}
                    <div>
                      <div className="text-xs text-muted mb-1 flex items-center gap-2">
                        Education
                        <ConfBadge level={profile.extraction_confidence?.education || "low"} label="conf" />
                      </div>
                      <div className="text-sm">
                        {profile.degree_level} &middot; {(profile.universities || []).join(", ") || "Not found"}
                      </div>
                      {profile.gpa && <div className="text-xs text-muted">GPA: {profile.gpa}</div>}
                    </div>

                    {/* Skills */}
                    <div>
                      <div className="text-xs text-muted mb-1.5 flex items-center gap-2">
                        Skills ({(profile.skills || []).length})
                        <ConfBadge level={profile.extraction_confidence?.skills || "low"} label="conf" />
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {(profile.skills || []).slice(0, 15).map((s: string) => (
                          <span key={s} className="text-[11px] px-2 py-0.5 rounded bg-card border border-border text-muted">{s}</span>
                        ))}
                        {(profile.skills || []).length > 15 && (
                          <span className="text-[11px] px-2 py-0.5 text-muted">+{(profile.skills || []).length - 15} more</span>
                        )}
                      </div>
                    </div>

                    {/* Metrics */}
                    <div>
                      <div className="text-xs text-muted mb-1.5 flex items-center gap-2">
                        Strongest metrics ({(profile.strongest_metrics || []).length})
                        <ConfBadge level={profile.extraction_confidence?.metrics || "low"} label="conf" />
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {(profile.strongest_metrics || []).slice(0, 8).map((m: string, i: number) => (
                          <span key={i} className="text-[11px] px-2 py-0.5 rounded bg-accent/10 border border-accent/20 text-accent">{m}</span>
                        ))}
                      </div>
                    </div>

                    {/* Work history */}
                    <div>
                      <div className="text-xs text-muted mb-1.5 flex items-center gap-2">
                        Experience ({(profile.work_history || []).length} entries)
                        <ConfBadge level={profile.extraction_confidence?.experience || "low"} label="conf" />
                      </div>
                      {(profile.work_history || []).map((w: any, i: number) => (
                        <div key={i} className="text-sm mb-1">
                          <span className="text-white">{w.company}</span>
                          <span className="text-muted"> &middot; {w.title} &middot; {w.duration}</span>
                        </div>
                      ))}
                    </div>

                    {/* Warnings */}
                    {profile._warnings?.length > 0 && (
                      <div className="bg-warn/5 border border-warn/20 rounded-lg p-3">
                        <div className="text-xs text-warn font-semibold mb-1">Extraction notes:</div>
                        {profile._warnings.map((w: string, i: number) => (
                          <div key={i} className="text-xs text-warn/80">&bull; {w}</div>
                        ))}
                      </div>
                    )}

                    {/* Re-upload */}
                    <button onClick={() => { setProfile(null); setPhase("idle"); }}
                      className="text-xs text-muted hover:text-accent transition">
                      ← Upload a different resume
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Right: Preferences */}
            <div>
              <h2 className="text-2xl font-serif mb-5">Search preferences</h2>
              <div className="bg-surface rounded-xl p-5 md:p-6 border border-border space-y-5">
                {/* Job type */}
                <div>
                  <label className="text-xs text-muted mb-2 block">What are you looking for?</label>
                  <div className="flex flex-wrap gap-2">
                    {[
                      { v: "intern_2026", l: "Summer 2026 Internship" },
                      { v: "new_grad_2027", l: "Full-time 2027" },
                      { v: "co_op_2026", l: "Co-op / Part-time" },
                    ].map(o => (
                      <button key={o.v} onClick={() => setJobType(o.v)}
                        className={`px-4 py-2 rounded-lg text-sm transition ${jobType === o.v ? "bg-accent text-white" : "bg-card text-muted hover:text-white"}`}>
                        {o.l}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Degree level */}
                <div>
                  <label className="text-xs text-muted mb-2 block">Target degree level</label>
                  <div className="flex flex-wrap gap-2">
                    {[
                      { v: "undergrad", l: "Undergraduate" },
                      { v: "masters", l: "Master\u2019s" },
                      { v: "phd", l: "PhD" },
                    ].map(o => (
                      <button key={o.v} onClick={() => setDegreeTarget(o.v)}
                        className={`px-4 py-2 rounded-lg text-sm transition ${degreeTarget === o.v ? "bg-accent text-white" : "bg-card text-muted hover:text-white"}`}>
                        {o.l}
                      </button>
                    ))}
                  </div>
                  <p className="text-[10px] text-muted/50 mt-1">We filter out jobs requiring a higher degree than selected</p>
                </div>

                {/* Directions */}
                <div>
                  <label className="text-xs text-muted mb-2 block">Directions (select all that apply)</label>
                  <div className="flex flex-wrap gap-2">
                    {[
                      "DS/ML", "Data Engineering", "Software Engineering",
                      "Health Informatics", "Business Analytics", "Product Management",
                      "Quantitative Finance", "Research / NLP", "Consulting",
                    ].map(d => (
                      <button key={d} onClick={() => toggleDir(d)}
                        className={`px-3 py-1.5 rounded-full text-sm transition border ${
                          directions.includes(d) ? "border-accent text-accent bg-accent/10" : "border-border text-muted hover:border-muted"
                        }`}>{d}</button>
                    ))}
                  </div>
                  {/* Custom direction input */}
                  <div className="flex gap-2 mt-2">
                    <input
                      type="text"
                      value={customDirection}
                      onChange={e => setCustomDirection(e.target.value)}
                      onKeyDown={e => {
                        if (e.key === "Enter" && customDirection.trim()) {
                          toggleDir(customDirection.trim());
                          setCustomDirection("");
                        }
                      }}
                      placeholder="Add custom direction..."
                      className="flex-1 bg-card border border-border rounded-lg px-3 py-1.5 text-sm text-white placeholder-muted/40 focus:border-accent outline-none"
                    />
                    <button
                      onClick={() => { if (customDirection.trim()) { toggleDir(customDirection.trim()); setCustomDirection(""); } }}
                      className="px-3 py-1.5 rounded-lg text-sm bg-card border border-border text-muted hover:text-accent hover:border-accent transition"
                    >+</button>
                  </div>
                </div>

                {/* Visa */}
                <label className="flex items-center gap-3 cursor-pointer">
                  <input type="checkbox" checked={visaNeeded} onChange={e => setVisaNeeded(e.target.checked)} className="accent-accent w-4 h-4" />
                  <span className="text-sm text-muted">I need visa sponsorship (OPT / CPT / H-1B)</span>
                </label>

                {/* CTA */}
                <button onClick={handleSearch} disabled={phase !== "parsed" || isProcessing}
                  className={`w-full py-3.5 rounded-lg text-base font-bold transition ${
                    phase === "parsed" ? "btn-gold" : "bg-card text-muted/40 cursor-not-allowed"
                  }`}>
                  {isProcessing ? "Searching..." : phase === "parsed" ? "Find My Jobs" : "Upload resume first"}
                </button>

                {/* Mobile quota */}
                <div className="text-center text-xs text-muted sm:hidden">{quota}</div>
              </div>
            </div>
          </div>
        )}

        {/* ═══ PROCESSING — animated progress bar ═══ */}
        {isProcessing && phase !== "uploading" && (
          <div className="max-w-lg mx-auto py-20 md:py-28 px-4">
            <h2 className="text-2xl md:text-3xl font-serif mb-10 text-center" style={{ color: "#F0F4F8" }}>
              Finding your best matches
            </h2>

            {/* Animated progress bar */}
            {(() => {
              const steps = ["searching", "verifying", "generating"];
              const ci = steps.indexOf(phase);
              const pct = ci < 0 ? 10 : ((ci + 1) / steps.length) * 100 - 10;
              return (
                <div className="mb-8">
                  {/* Bar track */}
                  <div className="h-2 rounded-full overflow-hidden" style={{ background: "#1E293B" }}>
                    <div className="h-full rounded-full transition-all duration-1000 ease-out relative"
                      style={{ width: `${pct}%`, background: "linear-gradient(90deg, #3B82F6, #60A5FA)" }}>
                      {/* Shimmer effect */}
                      <div className="absolute inset-0 rounded-full" style={{
                        background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent)",
                        animation: "shimmer 1.5s infinite",
                      }} />
                    </div>
                  </div>
                  {/* Step labels under bar */}
                  <div className="flex justify-between mt-3">
                    {[
                      { k: "searching", l: "Searching jobs" },
                      { k: "verifying", l: "Verifying postings" },
                      { k: "generating", l: "Writing cover letters" },
                    ].map((s, i) => {
                      const isDone = i < ci;
                      const isActive = i === ci;
                      return (
                        <span key={s.k} className="text-xs font-medium transition-all duration-300" style={{
                          color: isDone ? "#4ADE80" : isActive ? "#F0F4F8" : "#3D4A5C",
                        }}>
                          {isDone && <span style={{ color: "#4ADE80" }}>{"\u2713 "}</span>}
                          {s.l}
                        </span>
                      );
                    })}
                  </div>
                </div>
              );
            })()}

            {/* Live log */}
            <div className="rounded-xl p-5 font-mono text-xs space-y-2" style={{ background: "#0A0F1A", border: "1px solid #1E293B" }}>
              {progressLog.map((line, i) => (
                <div key={i} className="transition-all duration-300" style={{
                  color: i < progressLog.length - 1 ? "#4ADE80" : "#60A5FA",
                }}>
                  {i < progressLog.length - 1 ? "\u2713 " : "\u25B8 "}{line}
                </div>
              ))}
              <div style={{ color: "#3D4A5C" }} className="mt-3">{"This usually takes 30\u201360 seconds..."}</div>
            </div>

            <style jsx>{`
              @keyframes shimmer {
                0% { transform: translateX(-100%); }
                100% { transform: translateX(200%); }
              }
            `}</style>
          </div>
        )}

        {/* ═══ RESULTS (Moment 3: verification = the product's promise) ═══ */}
        {phase === "done" && result && (
          <div>
            {/* Summary */}
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-6">
              <div>
                <h2 className="text-2xl md:text-3xl font-serif">
                  {result.audit_summary?.jobs_open || 0} verified open positions
                </h2>
                <p className="text-muted text-sm mt-1">
                  {result.audit_summary?.jobs_searched} searched &middot;
                  {result.audit_summary?.jobs_verified} passed verification
                  {result.audit_summary?.cl_generated ? (
                    <span> &middot; {result.audit_summary.cl_generated} cover letters written</span>
                  ) : (
                    <span className="ml-1" style={{ color: "#60A5FA" }}> &middot; Click "Write Cover Letter" on any job</span>
                  )}
                </p>
                {result.errors && result.errors.length > 0 && (
                  <p className="text-warn text-xs mt-1">! {result.errors[0]}</p>
                )}
              </div>
              <div className="flex gap-2 shrink-0">
                <button onClick={handleDownload} className="btn-gold flex items-center gap-2 text-sm">
                  Download Excel
                </button>
                <button onClick={() => { setResult(null); setPhase("parsed"); }} className="btn-blue text-sm">
                  New search
                </button>
              </div>
            </div>

            {/* Audit summary (collapsible) */}
            <button onClick={() => setShowAudit(!showAudit)}
              className="text-xs text-muted hover:text-accent mb-4 flex items-center gap-1 transition">
              {showAudit ? "\u25B4" : "\u25BE"} Verification audit
              <span className="text-muted/40 ml-1">({result.audit_summary?.jobs_open} open, {result.audit_summary?.jobs_unverified || 0} unverified)</span>
            </button>
            {showAudit && result.audit_summary && (
              <div className="bg-surface rounded-xl p-4 border border-border mb-6 text-xs text-muted space-y-1">
                <div>Avg CL score: {result.audit_summary.avg_cl_score}/{result.audit_summary.max_cl_score || 6}</div>
                {Object.entries(result.audit_summary.drop_reasons || {}).map(([reason, count]) => (
                  <div key={reason}>Dropped {count}x: {reason}</div>
                ))}
              </div>
            )}

            {/* Best match highlight (no CL dependency) */}
            {result.jobs.length > 0 && result.jobs[0]?.audit?.status?.includes("Open") && (
              <div className="mb-6 bg-gradient-to-r from-accent/10 via-surface to-surface rounded-2xl border border-accent/30 p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs text-accent font-semibold uppercase tracking-wider mb-1">Top match</div>
                    <div className="text-lg font-semibold">{result.jobs[0].company} &mdash; {result.jobs[0].title}</div>
                    <div className="text-xs text-muted mt-1">{result.jobs[0].location}</div>
                  </div>
                  <div className="flex gap-2 shrink-0">
                    {!result.jobs[0].cover_letter?.text && (
                      <button onClick={() => handleGenerateCL(0)}
                        disabled={generatingCL !== null}
                        className="text-xs px-4 py-2 rounded-lg bg-accent/10 border border-accent/30 text-accent hover:bg-accent/20 transition">
                        {generatingCL === 0 ? "Writing..." : "Write CL"}
                      </button>
                    )}
                    <a href={result.jobs[0].apply_url} target="_blank" rel="noopener noreferrer"
                      className="btn-gold text-sm">Apply</a>
                  </div>
                </div>
              </div>
            )}

            {/* Job cards grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {result.jobs.map((job, idx) => (
                <div key={idx} className="job-card">
                  <div className="flex items-start justify-between mb-2">
                    <div className="min-w-0">
                      <div className="font-semibold truncate">{job.company}</div>
                      <div className="text-sm text-muted truncate">{job.title}</div>
                    </div>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface text-muted/60 shrink-0 ml-2">{job.job_board}</span>
                  </div>

                  <div className="text-xs text-muted mb-3">
                    {job.location}{job.remote ? " \u00B7 Remote" : ""}
                  </div>

                  {/* Badges row */}
                  <div className="flex flex-wrap gap-1.5 mb-3">
                    <StatusBadge status={job.audit?.status || "\u26A0 Unverified"} />
                    {job.audit?.confidence && job.audit.confidence !== "high" && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-surface border border-border text-muted"
                        title={job.audit.reason}>
                        conf: {job.audit.confidence}
                      </span>
                    )}
                    {job.audit?.posting_age_days != null && (
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full border ${
                        job.audit.posting_age_days > 60 ? "border-closed/30 text-closed" :
                        job.audit.posting_age_days > 30 ? "border-warn/30 text-warn" :
                        "border-border text-muted"
                      }`}>{job.audit.posting_age_days}d ago</span>
                    )}
                    {job.audit?.degree_match === "ok" && <span className="text-[10px] px-1.5 py-0.5 rounded-full badge-open">Degree ✓</span>}
                    {job.audit?.visa === "confirmed" && <span className="text-[10px] px-1.5 py-0.5 rounded-full badge-open">Visa ✓</span>}
                    {job.audit?.visa === "no_sponsor" && <span className="text-[10px] px-1.5 py-0.5 rounded-full badge-closed">No visa</span>}
                    {job.audit?.ghost_risk === "high" && <span className="text-[10px] px-1.5 py-0.5 rounded-full badge-warn">Ghost risk</span>}
                  </div>

                  {/* Why this status */}
                  {job.audit?.status?.includes("Unverified") && job.audit?.reason && (
                    <div className="text-[10px] text-warn/70 mb-2 italic">
                      Why unverified: {job.audit.reason}
                    </div>
                  )}

                  {/* CV + CL score */}
                  <div className="text-xs text-muted mb-3">
                    Resume: <span className="text-accent">{job.recommended_cv || "V1-DS"}</span>
                    {job.cover_letter && (
                      <span className="ml-2">
                        &middot; CL: <span className={job.cover_letter.score >= 5 ? "text-open" : job.cover_letter.score >= 4 ? "text-accent" : "text-warn"}>
                          {job.cover_letter.score}/{job.cover_letter.max_score}
                        </span>
                        {job.cover_letter.needs_review && <span className="ml-1 text-warn text-[10px]">(review)</span>}
                      </span>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2 mt-auto pt-2 border-t border-border/50">
                    {job.cover_letter?.text ? (
                      <>
                        <button onClick={() => setExpandedCL(expandedCL === idx ? null : idx)}
                          className="text-xs px-3 py-1.5 rounded bg-card border border-border text-muted hover:text-white hover:border-accent/50 transition">
                          {expandedCL === idx ? "Hide CL \u25B4" : "Cover Letter \u25BE"}
                        </button>
                        <button onClick={() => copyCL(idx, job.cover_letter!.text)}
                          className={`text-xs px-3 py-1.5 rounded border transition ${
                            copied === idx ? "bg-open/10 border-open/30 text-open" : "bg-card border-border text-muted hover:text-white"
                          }`}>
                          {copied === idx ? "Copied \u2713" : "Copy CL"}
                        </button>
                      </>
                    ) : generatingCL === idx ? (
                      <span className="text-xs px-3 py-1.5 text-muted step-active">Writing...</span>
                    ) : (
                      <button onClick={() => handleGenerateCL(idx)}
                        disabled={generatingCL !== null}
                        className={`text-xs px-3 py-1.5 rounded border transition ${
                          generatingCL !== null ? "bg-card border-border text-muted/30 cursor-not-allowed"
                          : "bg-accent/10 border-accent/30 text-accent hover:bg-accent/20"
                        }`}>
                        Write Cover Letter
                      </button>
                    )}
                    <a href={job.apply_url} target="_blank" rel="noopener noreferrer"
                      className="text-xs px-3 py-1.5 rounded bg-accent/90 text-white hover:bg-accent transition ml-auto">
                      Apply &rarr;
                    </a>
                  </div>

                  {/* Expanded CL */}
                  {expandedCL === idx && job.cover_letter?.text && (
                    <div className="mt-4 p-4 bg-bg rounded-lg border border-border/50">
                      <pre className="text-sm text-muted/90 whitespace-pre-wrap font-sans leading-relaxed">{job.cover_letter.text}</pre>
                      <div className="mt-3 flex flex-wrap gap-3 text-[10px] text-muted/50">
                        <span>{job.cover_letter.word_count}w</span>
                        <span>Score {job.cover_letter.score}/{job.cover_letter.max_score}</span>
                        <span>Tone: {job.cover_letter.tone}</span>
                        {Object.entries(job.cover_letter.gates || {}).map(([g, v]) => (
                          <span key={g} className={v ? "text-open/50" : "text-closed/50"}>{g}: {v ? "\u2713" : "\u2717"}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {result.jobs.length === 0 && (
              <div className="text-center py-16 text-muted">
                <div className="text-4xl mb-4 opacity-30"></div>
                <p>No jobs passed verification for your criteria.</p>
                <p className="text-sm mt-2">Try broadening your search directions or disabling visa filtering.</p>
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  );
}

export default function Dashboard() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-screen text-muted">Loading...</div>}>
      <DashboardInner />
    </Suspense>
  );
}
