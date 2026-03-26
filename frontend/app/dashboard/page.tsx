"use client";

import { useSession, signOut } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect, useState, useRef, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5002";

type Job = {
  company: string;
  title: string;
  location: string;
  remote: boolean;
  apply_url: string;
  job_board: string;
  recommended_cv: string;
  audit: {
    status: string;
    confidence: string;
    reason: string;
    posting_age_days: number | null;
    degree_match: string;
    visa: string;
  };
  cover_letter?: {
    text: string;
    word_count: number;
    score: number;
    needs_review: boolean;
    gates: Record<string, boolean>;
  };
};

type SearchResult = {
  search_id: number | null;
  jobs: Job[];
  audit_summary: {
    jobs_searched: number;
    jobs_verified: number;
    cl_generated: number;
    avg_cl_score: number;
  };
};

type Phase = "idle" | "parsing" | "searching" | "verifying" | "generating" | "done";

export default function Dashboard() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);

  const [user, setUser] = useState<any>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [profile, setProfile] = useState<any>(null);
  const [result, setResult] = useState<SearchResult | null>(null);
  const [expandedCL, setExpandedCL] = useState<number | null>(null);
  const [copied, setCopied] = useState<number | null>(null);
  const [dragover, setDragover] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Preferences
  const [jobType, setJobType] = useState("intern_2026");
  const [directions, setDirections] = useState<string[]>(["DS/ML", "Health Informatics"]);
  const [visaNeeded, setVisaNeeded] = useState(true);

  useEffect(() => {
    if (status === "unauthenticated") router.push("/");
  }, [status, router]);

  useEffect(() => {
    fetch(`${API}/api/me`)
      .then((r) => r.json())
      .then(setUser)
      .catch(() => setUser({ name: "User", plan: "free", searches_used: 0 }));
  }, []);

  // ── Upload handler ────────────────────────────────────
  const handleUpload = useCallback(async (file: File) => {
    setError(null);
    setPhase("parsing");
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API}/api/parse`, { method: "POST", body: formData });
      const data = await res.json();
      if (data.error) {
        setError(data.error);
        setPhase("idle");
        return;
      }
      setProfile(data.profile);
      setPhase("idle");
    } catch (e) {
      setError("Upload failed. Please try again.");
      setPhase("idle");
    }
  }, []);

  // ── Search handler ────────────────────────────────────
  const handleSearch = useCallback(async () => {
    if (!profile) return;

    // Quota check
    if (user?.plan === "free" && user?.searches_used >= 3) {
      setError("Free plan limit reached (3 searches). Upgrade to Pro for unlimited.");
      return;
    }

    setError(null);
    setPhase("searching");

    // Simulate progress
    setTimeout(() => setPhase("verifying"), 2000);
    setTimeout(() => setPhase("generating"), 8000);

    try {
      const res = await fetch(`${API}/api/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          google_id: (session?.user as any)?.google_id,
          profile,
          prefs: { directions, job_type: jobType, visa_needed: visaNeeded },
        }),
      });
      const data = await res.json();
      if (data.error) {
        setError(data.error === "quota_exceeded" ? "Free plan limit reached. Upgrade to Pro." : data.error);
        setPhase("idle");
        return;
      }
      setResult(data);
      setPhase("done");
      if (user) setUser({ ...user, searches_used: (user.searches_used || 0) + 1 });
    } catch (e) {
      setError("Search failed. Please try again.");
      setPhase("idle");
    }
  }, [profile, directions, jobType, visaNeeded, session, user]);

  // ── Download handler ──────────────────────────────────
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
    } catch (e) {
      setError("Download failed.");
    }
  }, [result, profile]);

  // ── Copy CL ───────────────────────────────────────────
  const copyCL = (idx: number, text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(idx);
    setTimeout(() => setCopied(null), 2000);
  };

  // ── Direction toggle ──────────────────────────────────
  const toggleDir = (d: string) => {
    setDirections((prev) =>
      prev.includes(d) ? prev.filter((x) => x !== d) : [...prev, d]
    );
  };

  if (status === "loading") return <div className="flex items-center justify-center min-h-screen text-muted">Loading...</div>;

  const quota = user?.plan === "free" ? `${user?.searches_used || 0} / 3 free searches` : "Pro — Unlimited";
  const isProcessing = phase !== "idle" && phase !== "done";

  return (
    <main className="min-h-screen">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-border max-w-7xl mx-auto">
        <div className="text-xl font-bold">Job<span className="text-accent">Pilot</span></div>
        <div className="flex items-center gap-4">
          <span className="text-xs px-3 py-1 rounded-full bg-surface border border-border text-muted">{quota}</span>
          <span className="text-sm text-muted">{session?.user?.name || user?.name}</span>
          <button onClick={() => signOut()} className="text-xs text-muted hover:text-white">Sign out</button>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-8">
        {error && (
          <div className="mb-6 p-4 bg-closed/10 border border-closed/30 rounded-lg text-closed text-sm">
            {error}
            <button onClick={() => setError(null)} className="ml-4 underline">Dismiss</button>
          </div>
        )}

        {/* ═══ STATE 1: Upload + Prefs ═══ */}
        {phase === "idle" && !result && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Upload zone */}
            <div>
              <h2 className="text-2xl font-serif mb-6">
                {profile ? "Profile ready" : "Upload your resume"}
              </h2>

              {!profile ? (
                <div
                  className={`upload-zone rounded-xl p-12 text-center cursor-pointer ${dragover ? "dragover" : ""}`}
                  onClick={() => fileRef.current?.click()}
                  onDragOver={(e) => { e.preventDefault(); setDragover(true); }}
                  onDragLeave={() => setDragover(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setDragover(false);
                    const f = e.dataTransfer.files[0];
                    if (f) handleUpload(f);
                  }}
                >
                  <div className="text-4xl mb-4">&#128196;</div>
                  <p className="text-muted mb-2">Drop your PDF or DOCX here</p>
                  <p className="text-xs text-muted">or click to browse</p>
                  <input ref={fileRef} type="file" accept=".pdf,.docx,.doc" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) handleUpload(f); }} />
                </div>
              ) : (
                <div className="bg-surface rounded-xl p-6 border border-open/30">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-open text-sm font-semibold">&#10003; Parsed</span>
                    <button onClick={() => { setProfile(null); setResult(null); }} className="text-xs text-muted hover:text-white">Re-upload</button>
                  </div>
                  <div className="text-lg font-semibold">{profile.name || "Unknown"}</div>
                  <div className="text-sm text-muted mt-1">
                    {profile.degree_level} &bull; {profile.skills?.length || 0} skills &bull; {profile.strongest_metrics?.length || 0} metrics
                  </div>
                  {profile._mock && <div className="mt-2 text-xs text-warn">Mock mode — API unavailable. Results will be template-based.</div>}
                </div>
              )}
            </div>

            {/* Preferences */}
            <div>
              <h2 className="text-2xl font-serif mb-6">Search preferences</h2>
              <div className="bg-surface rounded-xl p-6 border border-border space-y-6">
                {/* Job type */}
                <div>
                  <label className="text-sm text-muted mb-2 block">Job type</label>
                  <div className="flex gap-2">
                    {[
                      { value: "intern_2026", label: "Internship 2026" },
                      { value: "new_grad_2027", label: "Full-time 2027" },
                    ].map((opt) => (
                      <button
                        key={opt.value}
                        onClick={() => setJobType(opt.value)}
                        className={`px-4 py-2 rounded-lg text-sm transition ${
                          jobType === opt.value ? "bg-accent text-white" : "bg-card text-muted hover:text-white"
                        }`}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Directions */}
                <div>
                  <label className="text-sm text-muted mb-2 block">Directions</label>
                  <div className="flex flex-wrap gap-2">
                    {["DS/ML", "Health Informatics", "Business Analytics"].map((d) => (
                      <button
                        key={d}
                        onClick={() => toggleDir(d)}
                        className={`px-3 py-1.5 rounded-full text-sm transition border ${
                          directions.includes(d) ? "border-accent text-accent bg-accent/10" : "border-border text-muted hover:border-muted"
                        }`}
                      >
                        {d}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Visa */}
                <div className="flex items-center gap-3">
                  <input type="checkbox" checked={visaNeeded} onChange={(e) => setVisaNeeded(e.target.checked)} className="accent-accent" />
                  <label className="text-sm text-muted">Need visa sponsorship (OPT/CPT/H1B)</label>
                </div>

                {/* CTA */}
                <button
                  onClick={handleSearch}
                  disabled={!profile || isProcessing}
                  className={`w-full py-3 rounded-lg text-lg font-bold transition ${
                    profile ? "btn-gold" : "bg-card text-muted cursor-not-allowed"
                  }`}
                >
                  {isProcessing ? "Processing..." : "Find My Jobs"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ═══ STATE 2: Processing ═══ */}
        {isProcessing && (
          <div className="max-w-2xl mx-auto py-16">
            <h2 className="text-2xl font-serif mb-10 text-center">Finding your best matches...</h2>
            <div className="flex justify-between mb-12">
              {[
                { key: "parsing", label: "Resume parsed" },
                { key: "searching", label: "Searching jobs" },
                { key: "verifying", label: "Verifying postings" },
                { key: "generating", label: "Writing CLs" },
              ].map((s, i) => {
                const phases: Phase[] = ["parsing", "searching", "verifying", "generating"];
                const currentIdx = phases.indexOf(phase);
                const stepIdx = i;
                const cls = stepIdx < currentIdx ? "step-done" : stepIdx === currentIdx ? "step-active" : "step-pending";
                const icon = stepIdx < currentIdx ? "\u2713" : stepIdx === currentIdx ? "\u21BB" : "\u25CB";

                return (
                  <div key={s.key} className={`flex flex-col items-center gap-2 ${cls}`}>
                    <div className="text-2xl">{icon}</div>
                    <div className="text-xs">{s.label}</div>
                  </div>
                );
              })}
            </div>
            <div className="bg-surface rounded-xl p-6 border border-border">
              <div className="text-xs text-muted font-mono space-y-1">
                {phase === "searching" && <div>Searching Greenhouse, Lever, and company sites...</div>}
                {phase === "verifying" && (
                  <>
                    <div className="text-open">&#10003; Search complete — verifying postings...</div>
                    <div>Checking if each job is still accepting applications...</div>
                  </>
                )}
                {phase === "generating" && (
                  <>
                    <div className="text-open">&#10003; Verification complete</div>
                    <div>Generating cover letters for verified positions...</div>
                  </>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ═══ STATE 3: Results ═══ */}
        {phase === "done" && result && (
          <div>
            {/* Summary header */}
            <div className="flex items-center justify-between mb-8">
              <div>
                <h2 className="text-3xl font-serif">
                  {result.jobs.filter((j) => j.audit?.status === "\u2713 Open").length} verified open positions
                </h2>
                <p className="text-muted text-sm mt-1">
                  {result.audit_summary.jobs_searched} searched &bull; {result.audit_summary.jobs_verified} verified &bull; {result.audit_summary.cl_generated} cover letters
                </p>
              </div>
              <div className="flex gap-3">
                <button onClick={handleDownload} className="btn-gold flex items-center gap-2">
                  &#128229; Download Excel
                </button>
                <button onClick={() => { setResult(null); setPhase("idle"); }} className="btn-blue">
                  New Search
                </button>
              </div>
            </div>

            {/* Job cards */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {result.jobs.map((job, idx) => (
                <div key={idx} className="job-card">
                  {/* Header */}
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <div className="font-semibold">{job.company}</div>
                      <div className="text-sm text-muted">{job.title}</div>
                    </div>
                    <span className="text-xs px-2 py-0.5 rounded bg-surface text-muted">{job.job_board}</span>
                  </div>

                  {/* Location */}
                  <div className="text-xs text-muted mb-3">
                    &#128205; {job.location} {job.remote ? " \u00B7 Remote" : ""}
                  </div>

                  {/* Badges */}
                  <div className="flex flex-wrap gap-2 mb-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      job.audit?.status === "\u2713 Open" ? "badge-open" :
                      job.audit?.status === "\u2717 Closed" ? "badge-closed" : "badge-warn"
                    }`}>
                      {job.audit?.status || "Unknown"}
                    </span>
                    {job.audit?.posting_age_days !== null && job.audit?.posting_age_days !== undefined && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-surface text-muted border border-border">
                        {job.audit.posting_age_days}d ago
                      </span>
                    )}
                    {job.audit?.degree_match === "ok" && (
                      <span className="text-xs px-2 py-0.5 rounded-full badge-open">Degree &#10003;</span>
                    )}
                    {job.audit?.visa === "confirmed" && (
                      <span className="text-xs px-2 py-0.5 rounded-full badge-open">Visa &#10003;</span>
                    )}
                  </div>

                  {/* CV recommendation */}
                  <div className="text-xs text-muted mb-3">
                    CV: <span className="text-accent">{job.recommended_cv || "V1-DS"}</span>
                    {job.cover_letter && (
                      <span className="ml-2">
                        &bull; CL Score: <span className={job.cover_letter.score >= 4 ? "text-open" : "text-warn"}>
                          {job.cover_letter.score}/5
                        </span>
                        {job.cover_letter.needs_review && <span className="ml-1 text-warn">(needs review)</span>}
                      </span>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2 mt-4">
                    {job.cover_letter && (
                      <button
                        onClick={() => setExpandedCL(expandedCL === idx ? null : idx)}
                        className="text-xs px-3 py-1.5 rounded bg-surface border border-border text-muted hover:text-white transition"
                      >
                        {expandedCL === idx ? "Hide CL \u25B4" : "Cover Letter \u25BE"}
                      </button>
                    )}
                    {job.cover_letter && (
                      <button
                        onClick={() => copyCL(idx, job.cover_letter!.text)}
                        className="text-xs px-3 py-1.5 rounded bg-surface border border-border text-muted hover:text-white transition"
                      >
                        {copied === idx ? "Copied \u2713" : "Copy"}
                      </button>
                    )}
                    <a
                      href={job.apply_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs px-3 py-1.5 rounded bg-accent text-white hover:bg-accent/80 transition ml-auto"
                    >
                      Apply &rarr;
                    </a>
                  </div>

                  {/* Expanded cover letter */}
                  {expandedCL === idx && job.cover_letter && (
                    <div className="mt-4 p-4 bg-bg rounded-lg border border-border">
                      <pre className="text-sm text-muted whitespace-pre-wrap font-sans leading-relaxed">
                        {job.cover_letter.text}
                      </pre>
                      <div className="mt-3 flex gap-4 text-xs text-muted">
                        <span>{job.cover_letter.word_count} words</span>
                        <span>Score: {job.cover_letter.score}/5</span>
                        <span>Gates: {Object.entries(job.cover_letter.gates || {}).filter(([, v]) => v).length}/5</span>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
