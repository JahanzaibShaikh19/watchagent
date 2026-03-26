export default function StatsBar({ stats }) {
  const items = [
    { label: "Total Runs", value: stats?.total_runs ?? 0 },
    { label: "Success Rate", value: `${stats?.success_rate ?? 0}%` },
    { label: `Cost (${stats?.month ?? "-"})`, value: `$${(stats?.total_cost_month ?? 0).toFixed(6)}` }
  ];

  return (
    <section className="grid gap-3 sm:grid-cols-3">
      {items.map((item) => (
        <div key={item.label} className="rounded-2xl bg-panel p-4 shadow-glow">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-400">{item.label}</p>
          <p className="mt-1 text-2xl font-semibold text-white">{item.value}</p>
        </div>
      ))}
    </section>
  );
}
