import type { NextAuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";

export const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  callbacks: {
    async signIn({ user, account }) {
      // Sync user to backend on every sign-in
      try {
        await fetch(`${API}/api/sync-user`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            google_id: account?.providerAccountId,
            email: user.email,
            name: user.name,
            avatar_url: user.image,
          }),
        });
      } catch (err) {
        console.error("Failed to sync user:", err);
      }
      return true;
    },
    async session({ session, token }) {
      // Attach google_id to session for frontend use
      if (session.user) {
        (session.user as any).google_id = token.sub;
      }
      return session;
    },
    async jwt({ token, account }) {
      if (account) {
        token.google_id = account.providerAccountId;
      }
      return token;
    },
  },
  pages: {
    signIn: "/",
  },
};
