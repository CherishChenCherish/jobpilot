import "./globals.css";
import type { Metadata } from "next";
import { SessionProvider } from "@/components/session-provider";

export const metadata: Metadata = {
  title: "JobPilot — Land Interviews, Not Just ATS Scores",
  description: "AI-powered job application tool that optimizes for interview rate, not keyword matching.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900 antialiased">
        <SessionProvider>{children}</SessionProvider>
      </body>
    </html>
  );
}
