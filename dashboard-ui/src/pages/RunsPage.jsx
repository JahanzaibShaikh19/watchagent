import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { deleteRun, getLicenseStatus, getRuns, getStats, openLiveStream } from "../api";
import StatusBadge from "../components/StatusBadge";
import StatsBar from "../components/StatsBar";

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  return date.toLocaleString();
}

export default function RunsPage() {
  const [stats, setStats] = useState(null);
  const [runs, setRuns] = useState([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [license, setLicense] = useState(null);
  const [dashboardLocked, setDashboardLocked] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    let ignore = false;

    async function load() {
      const licenseData = await getLicenseStatus();
      if (ignore) return;
      setLicense(licenseData);

      if (licenseData.plan !== "PRO") {
        setDashboardLocked(true);
        setStats(null);
        setRuns([]);
        setTotal(0);
        return;
      }

      setDashboardLocked(false);
      const [statsData, runsData] = await Promise.all([getStats(), getRuns(page, 25)]);
      if (ignore) return;
      setStats(statsData);
      setRuns(runsData.items);
      setTotal(runsData.total);
    }

    load().catch(console.error);

    const source = dashboardLocked
      ? { close: () => {} }
      : openLiveStream((event) => {
          if (event.type === "run_started" || event.type === "run_finished") {
            load().catch(console.error);
          }
        });

    return () => {
      ignore = true;
      source.close();
    };
  }, [page, dashboardLocked]);

  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / 25)), [total]);

  async function onDelete(event, id) {
    event.stopPropagation();
    await deleteRun(id);
    const runsData = await getRuns(page, 25);
    setRuns(runsData.items);
    setTotal(runsData.total);
  }

  return (
    <main className="mx-auto min-h-screen max-w-7xl px-4 py-8 sm:px-8">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-4xl font-semibold tracking-tight text-white">watchagent runs</h1>
          <p className="mt-1 text-sm text-slate-300">Live operational view of your agents.</p>
        </div>
        <div className="flex items-center gap-2">
          {license?.plan === "PRO" ? (
            <>
              <a href="http://127.0.0.1:8000/api/runs/export?format=json" className="rounded-xl bg-cyan-500/20 px-3 py-2 text-xs font-semibold text-cyan-100 ring-1 ring-cyan-400/40">
                export json
              </a>
              <a href="http://127.0.0.1:8000/api/runs/export?format=csv" className="rounded-xl bg-cyan-500/20 px-3 py-2 text-xs font-semibold text-cyan-100 ring-1 ring-cyan-400/40">
                export csv
              </a>
            </>
          ) : null}
          <Link to="/" className="rounded-xl bg-accent/20 px-4 py-2 text-sm font-semibold text-accent ring-1 ring-accent/50">
            refresh
          </Link>
        </div>
      </header>

      <StatsBar stats={stats} />

      {dashboardLocked ? (
        <section className="mt-6 rounded-2xl border border-amber-400/40 bg-amber-500/10 p-4 text-amber-100">
          <h2 className="text-lg font-semibold">Pro feature locked</h2>
          <p className="mt-1 text-sm">
            The web dashboard is part of watchagent Pro. Activate your license to unlock live runs, detail timeline, replay, and export.
          </p>
          <p className="mt-2 text-xs text-amber-200">Current plan: {license?.plan ?? "FREE"}</p>
        </section>
      ) : null}

      <section className="mt-6 overflow-hidden rounded-2xl border border-slate-700/70 bg-panel shadow-glow">
        <table className="w-full border-collapse text-left text-sm">
          <thead className="bg-panelSoft text-xs uppercase tracking-[0.14em] text-slate-300">
            <tr>
              <th className="px-4 py-3">Agent</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Duration</th>
              <th className="px-4 py-3">Cost</th>
              <th className="px-4 py-3">Timestamp</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr
                key={run.agent_id}
                className="cursor-pointer border-t border-slate-800/80 transition hover:bg-slate-900/40"
                onClick={() => navigate(`/runs/${run.agent_id}`)}
              >
                <td className="px-4 py-3 font-medium text-white">{run.agent_name}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={run.status} />
                </td>
                <td className="px-4 py-3 text-slate-200">{run.duration_ms == null ? "-" : `${run.duration_ms} ms`}</td>
                <td className="px-4 py-3 text-slate-200">${(run.total_cost ?? 0).toFixed(6)}</td>
                <td className="px-4 py-3 text-slate-300">{formatDate(run.start_time)}</td>
                <td className="px-4 py-3 text-right">
                  {run.status !== "RUNNING" ? (
                    <button
                      type="button"
                      className="rounded-md bg-rose-500/20 px-3 py-1 text-xs font-semibold text-rose-300 ring-1 ring-rose-400/40"
                      onClick={(event) => onDelete(event, run.agent_id)}
                    >
                      delete
                    </button>
                  ) : null}
                </td>
              </tr>
            ))}
            {!runs.length && !dashboardLocked ? (
              <tr className="border-t border-slate-800/80">
                <td className="px-4 py-6 text-slate-400" colSpan={6}>No runs found.</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </section>

      <footer className="mt-4 flex items-center justify-between text-sm text-slate-300">
        <button type="button" className="rounded-lg border border-slate-600 px-3 py-1" onClick={() => setPage((v) => Math.max(1, v - 1))}>
          previous
        </button>
        <span>
          page {page} / {totalPages}
        </span>
        <button
          type="button"
          className="rounded-lg border border-slate-600 px-3 py-1"
          onClick={() => setPage((v) => Math.min(totalPages, v + 1))}
        >
          next
        </button>
      </footer>
    </main>
  );
}
