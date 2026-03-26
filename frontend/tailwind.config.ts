import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        page: "#060A13",
        surface: "#0F1629",
        raised: "#182036",
        overlay: "#1E293B",
        card: "#182036",      // alias for raised
        border: "#1E293B",
        "border-hover": "#334155",
        accent: "#3B82F6",
        "accent-hover": "#2563EB",
        gold: "#F59E0B",
        open: "#22C55E",
        warn: "#F59E0B",
        closed: "#EF4444",
        muted: "#A8B8CF",     // now higher contrast than before
      },
      fontFamily: {
        serif: ['"DM Serif Display"', "Georgia", "serif"],
        sans: ['"DM Sans"', "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
