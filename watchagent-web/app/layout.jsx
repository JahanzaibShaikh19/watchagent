import "./globals.css";

export const metadata = {
  title: "watchagent - debugger for AI agents",
  description:
    "See exactly what your agent is thinking, where it gets stuck, and how much it costs.",
  metadataBase: new URL("https://watchagent.dev"),
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
