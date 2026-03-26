import { useState } from "react";

export default function JsonBlock({ title, data, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="rounded-xl border border-slate-700/80 bg-slate-900/50">
      <button
        type="button"
        className="flex w-full items-center justify-between px-3 py-2 text-left text-xs font-semibold uppercase tracking-[0.14em] text-slate-300"
        onClick={() => setOpen((value) => !value)}
      >
        <span>{title}</span>
        <span>{open ? "Hide" : "Show"}</span>
      </button>
      {open ? (
        <pre className="max-h-64 overflow-auto px-3 pb-3 font-mono text-xs text-slate-200">
          {JSON.stringify(data, null, 2)}
        </pre>
      ) : null}
    </div>
  );
}
