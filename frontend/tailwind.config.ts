import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#080C14",
        surface: "#111827",
        card: "#1A2234",
        accent: "#3B82F6",
        gold: "#F59E0B",
        open: "#22C55E",
        warn: "#F59E0B",
        closed: "#EF4444",
        muted: "#94A3B8",
        border: "#1E293B",
      },
      fontFamily: {
        serif: ['"DM Serif Display"', "serif"],
        sans: ['"DM Sans"', "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
