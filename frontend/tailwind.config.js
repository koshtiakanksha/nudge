/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#16231E",        // near-black green-ink, body text
        paper: "#F6F3EC",      // warm paper background
        moss: "#2F5D50",       // deep moss green, primary
        moss2: "#3D7568",      // lighter moss for hover
        clay: "#C1622D",       // burnt clay/terracotta accent (alerts, CTAs)
        gold: "#C9A24B",       // muted gold, used sparingly for highlights
        line: "#DDD6C5",       // hairline border on paper
        slate: "#5B6760",      // secondary text
      },
      fontFamily: {
        display: ["var(--font-display)", "serif"],
        body: ["var(--font-body)", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      borderRadius: {
        sm: "4px",
        md: "8px",
        lg: "14px",
      },
    },
  },
  plugins: [],
};
