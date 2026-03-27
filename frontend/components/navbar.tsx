"use client";

import Link from "next/link";
import { useSession, signOut } from "next-auth/react";
import { usePathname, useRouter } from "next/navigation";

export function Navbar() {
  const { data: session } = useSession();
  const pathname = usePathname();
  const router = useRouter();

  const isDashboard = pathname === "/dashboard";
  const isPricing = pathname === "/pricing";

  return (
    <header style={{ borderBottom: "1px solid #1E293B" }}>
      <nav className="max-w-7xl mx-auto px-4 md:px-6 py-3 flex items-center justify-between">
        {/* Logo — always goes home */}
        <div className="flex items-center gap-6">
          <Link href="/" className="text-xl font-bold tracking-tight hover:opacity-80 transition">
            Job<span style={{ color: "#3B82F6" }}>Pilot</span>
          </Link>

          {/* Nav links */}
          <div className="hidden md:flex items-center gap-1">
            {session && (
              <Link href="/dashboard"
                className={`text-sm px-3 py-1.5 rounded-lg transition ${
                  isDashboard
                    ? "text-white bg-white/10"
                    : "text-[#A8B8CF] hover:text-white hover:bg-white/5"
                }`}>
                Dashboard
              </Link>
            )}
            <Link href="/pricing"
              className={`text-sm px-3 py-1.5 rounded-lg transition ${
                isPricing
                  ? "text-white bg-white/10"
                  : "text-[#A8B8CF] hover:text-white hover:bg-white/5"
              }`}>
              Pricing
            </Link>
          </div>
        </div>

        {/* Right side */}
        <div className="flex items-center gap-3">
          {session ? (
            <>
              {/* Mobile nav */}
              <div className="flex md:hidden items-center gap-2">
                <Link href="/dashboard" className="text-xs text-[#A8B8CF] hover:text-white px-2 py-1">
                  Dashboard
                </Link>
              </div>
              <span className="text-xs text-[#5B6B82] hidden md:inline">
                {session.user?.name}
              </span>
              <button onClick={() => signOut({ callbackUrl: "/" })}
                className="text-xs text-[#5B6B82] hover:text-white px-2 py-1 rounded transition">
                Sign out
              </button>
            </>
          ) : (
            <Link href="/api/auth/signin"
              className="text-sm px-4 py-1.5 rounded-lg transition"
              style={{ background: "rgba(255,255,255,0.1)" }}>
              Sign in
            </Link>
          )}
        </div>
      </nav>
    </header>
  );
}
