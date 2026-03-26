/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./app/**/*.{js,jsx,ts,tsx}",
        "./components/**/*.{js,jsx,ts,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                bg: "#05070b",
                panel: "#0b1118",
                panelAlt: "#0f1722",
                line: "#1b2a38",
                accent: "#3eff84",
                accentSoft: "#1dff7033",
            },
            fontFamily: {
                display: ["Space Grotesk", "ui-sans-serif", "system-ui"],
                mono: ["IBM Plex Mono", "ui-monospace", "SFMono-Regular", "monospace"],
            },
            boxShadow: {
                neon: "0 0 0 1px rgba(62, 255, 132, 0.4), 0 0 28px rgba(62, 255, 132, 0.14)",
            },
            backgroundImage: {
                "grid-fade": "linear-gradient(to right, rgba(62,255,132,0.06) 1px, transparent 1px), linear-gradient(to bottom, rgba(62,255,132,0.06) 1px, transparent 1px)",
            },
        },
    },
    plugins: [],
};