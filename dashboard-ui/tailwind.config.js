/** @type {import('tailwindcss').Config} */
export default {
    content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
    theme: {
        extend: {
            colors: {
                bg: "#09121d",
                panel: "#132336",
                panelSoft: "#1a2f47",
                accent: "#5eead4"
            },
            fontFamily: {
                sans: ["Sora", "Segoe UI", "sans-serif"],
                mono: ["JetBrains Mono", "Consolas", "monospace"]
            },
            boxShadow: {
                glow: "0 0 0 1px rgba(94,234,212,0.35), 0 20px 40px rgba(2,6,23,0.45)"
            }
        }
    },
    plugins: []
};