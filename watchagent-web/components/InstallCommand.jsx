"use client";

import { useState } from "react";
import { motion } from "framer-motion";

export default function InstallCommand() {
  const [copied, setCopied] = useState(false);

  async function onCopy() {
    try {
      await navigator.clipboard.writeText("pip install watchagent");
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch (_err) {
      setCopied(false);
    }
  }

  return (
    <div className="flex w-full max-w-xl flex-col gap-3 sm:flex-row">
      <div className="flex-1 rounded-xl border border-line bg-panel/90 px-4 py-3 font-mono text-sm text-accent shadow-neon">
        pip install watchagent
      </div>
      <motion.button
        whileTap={{ scale: 0.97 }}
        whileHover={{ y: -2 }}
        onClick={onCopy}
        className="rounded-xl border border-accent bg-accentSoft px-5 py-3 text-sm font-semibold text-accent"
      >
        {copied ? "copied" : "copy"}
      </motion.button>
    </div>
  );
}
