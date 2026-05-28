import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg: {
          base: "#0B1020",
          surface: "#0F172A",
          elevated: "#111827",
          overlay: "#172033",
          border: "#1E2A3A",
        },
        accent: {
          cyan: "#00C2FF",
          green: "#7CFFB2",
          yellow: "#FFCC66",
          red: "#FF6B6B",
          orange: "#FF9500",
          purple: "#A78BFA",
        },
        node: {
          healthy: "#7CFFB2",
          probing: "#FFCC66",
          stressed: "#FF9500",
          compromised: "#FF6B6B",
          encrypted: "#A78BFA",
          recovering: "#00C2FF",
          isolated: "#64748B",
          offline: "#374151",
        },
        text: {
          primary: "#E2E8F0",
          secondary: "#94A3B8",
          muted: "#475569",
          dim: "#334155",
        },
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Menlo", "monospace"],
      },
      fontSize: {
        "2xs": ["0.625rem", { lineHeight: "0.875rem" }],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "ping-slow": "ping 2s cubic-bezier(0, 0, 0.2, 1) infinite",
        "fade-in": "fadeIn 0.2s ease-out",
        "slide-in-right": "slideInRight 0.25s ease-out",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideInRight: {
          "0%": { transform: "translateX(16px)", opacity: "0" },
          "100%": { transform: "translateX(0)", opacity: "1" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
