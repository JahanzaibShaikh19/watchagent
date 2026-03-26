const COLOR_BY_STATUS = {
  SUCCESS: "bg-emerald-500/20 text-emerald-300 ring-emerald-500/50",
  FAILED: "bg-rose-500/20 text-rose-300 ring-rose-500/50",
  TIMEOUT: "bg-orange-500/20 text-orange-300 ring-orange-500/50",
  RUNNING: "bg-yellow-500/20 text-yellow-300 ring-yellow-500/50"
};

export default function StatusBadge({ status }) {
  const className = COLOR_BY_STATUS[status] || "bg-slate-600/20 text-slate-200 ring-slate-500/50";
  return (
    <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ring-1 ${className}`}>
      {status}
    </span>
  );
}
