import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getLicenseStatus, getRun, getRunReplay, getRunSteps, openLiveStream } from "../api";
import JsonBlock from "../components/JsonBlock";
import StatusBadge from "../components/StatusBadge";

function stepCardClass(step) {
  if (step.kind === "TOOL_CALL") return "border-blue-400/50 bg-blue-500/10";
  if (step.kind === "LLM_CALL") return "border-cyan-400/50 bg-cyan-500/10";
  if (step.kind === "LOOP_DETECTED") return "border-orange-400/50 bg-orange-500/10";
  return "border-slate-700 bg-slate-900/40";
}

function readStepDurationMs(current, previous) {
  if (!current?.timestamp || !previous?.timestamp) return null;
  const t1 = new Date(previous.timestamp).getTime();
  const t2 = new Date(current.timestamp).getTime();
  if (Number.isNaN(t1) || Number.isNaN(t2)) return null;
  return Math.max(0, t2 - t1);
}

export default function RunDetailPage() {
  const { id } = useParams();
  const [license, setLicense] = useState(null);
  const [run, setRun] = useState(null);
  const [steps, setSteps] = useState([]);
  const [replayFrames, setReplayFrames] = useState([]);
  const [replayIndex, setReplayIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);

  useEffect(() => {
    let closed = false;

    async function load() {
      const licenseData = await getLicenseStatus();
      if (closed) return;
      setLicense(licenseData);

      if (licenseData.plan !== "PRO") {
        return;
      }

      const [runDetail, stepData, replayData] = await Promise.all([getRun(id), getRunSteps(id), getRunReplay(id)]);
      if (closed) return;
      setRun(runDetail);
      setSteps(stepData.items || []);
      setReplayFrames(replayData.items || []);
    }

    load().catch(console.error);

    const source = license?.plan === "PRO"
      ? openLiveStream((event) => {
          if (event.type === "step" && event.run_id === id) {
            setSteps((prev) => [...prev, event.step]);
          }
          if (event.type === "run_finished" && event.run_id === id) {
            load().catch(console.error);
          }
        })
      : { close: () => {} };

    let intervalId;
    if (run?.status === "RUNNING") {
      intervalId = window.setInterval(() => {
        load().catch(console.error);
      }, 2000);
    }

    return () => {
      closed = true;
      source.close();
      if (intervalId) window.clearInterval(intervalId);
    };
  }, [id, run?.status, license?.plan]);

  useEffect(() => {
    if (!isPlaying || replayFrames.length === 0) {
      return undefined;
    }
    const ms = Math.max(200, Math.floor(1200 / speed));
    const timer = window.setInterval(() => {
      setReplayIndex((current) => {
        if (current >= replayFrames.length - 1) {
          setIsPlaying(false);
          return current;
        }
        return current + 1;
      });
    }, ms);
    return () => window.clearInterval(timer);
  }, [isPlaying, replayFrames.length, speed]);

  const orderedSteps = useMemo(() => steps || [], [steps]);

  if (!license) {
    return <main className="mx-auto max-w-6xl p-8 text-slate-200">loading...</main>;
  }

  if (license.plan !== "PRO") {
    return (
      <main className="mx-auto max-w-6xl p-8 text-amber-100">
        <h1 className="text-2xl font-semibold">Pro feature locked</h1>
        <p className="mt-2 text-sm">Run detail and replay mode are available on watchagent Pro.</p>
      </main>
    );
  }

  if (!run) {
    return <main className="mx-auto max-w-6xl p-8 text-slate-200">loading...</main>;
  }

  const selectedFrame = replayFrames[replayIndex] || null;

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-4 py-8 sm:px-8">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link to="/" className="text-sm text-accent">&larr; back to runs</Link>
          <h1 className="mt-1 text-3xl font-semibold text-white">{run.agent_name}</h1>
          <p className="text-sm text-slate-300">run id: {run.agent_id}</p>
        </div>
        <div className="rounded-2xl bg-panel p-4 shadow-glow">
          <StatusBadge status={run.status} />
          <p className="mt-2 text-sm text-slate-300">duration: {run.duration_ms == null ? "running" : `${run.duration_ms} ms`}</p>
          <p className="text-sm text-slate-300">total cost: ${(run.total_cost ?? 0).toFixed(6)}</p>
        </div>
      </header>

      <section className="mb-6 rounded-2xl bg-panel p-4 shadow-glow">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Replay</h2>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="rounded-lg bg-cyan-500/20 px-3 py-2 text-sm font-semibold text-cyan-100 ring-1 ring-cyan-500/50"
              onClick={() => setIsPlaying((v) => !v)}
              disabled={!replayFrames.length}
            >
              {isPlaying ? "pause" : "play"}
            </button>
            <select
              className="rounded-lg bg-slate-900 px-2 py-2 text-sm text-slate-200 ring-1 ring-slate-600"
              value={speed}
              onChange={(event) => setSpeed(Number(event.target.value))}
            >
              <option value={1}>1x</option>
              <option value={2}>2x</option>
              <option value={4}>4x</option>
            </select>
          </div>
        </div>
        <div className="mt-3 text-sm text-slate-300">
          frame: {replayFrames.length ? replayIndex + 1 : 0} / {replayFrames.length}
        </div>
        {selectedFrame ? (
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <JsonBlock title={`state at step ${selectedFrame.step_index}`} data={selectedFrame.state} defaultOpen />
            <JsonBlock title="available options" data={selectedFrame.options || []} defaultOpen />
          </div>
        ) : (
          <p className="mt-3 text-sm text-slate-400">No replay data captured for this run.</p>
        )}
        {selectedFrame ? (
          <p className="mt-2 text-sm text-cyan-100">
            At step {selectedFrame.step_index}, agent had these options: {(selectedFrame.options || []).length ? selectedFrame.options.join(", ") : "No explicit options logged"}.
          </p>
        ) : null}
        <div className="mt-3">
          <input
            type="range"
            min={0}
            max={Math.max(0, replayFrames.length - 1)}
            value={Math.min(replayIndex, Math.max(0, replayFrames.length - 1))}
            onChange={(event) => setReplayIndex(Number(event.target.value))}
            className="w-full"
          />
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold text-white">Timeline</h2>
        {orderedSteps.map((step, index) => (
          <article key={`${step.timestamp}-${index}`} className={`rounded-2xl border p-4 ${stepCardClass(step)}`}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm uppercase tracking-[0.14em] text-slate-300">{step.kind}</p>
                <p className="text-lg font-medium text-white">{step.message}</p>
              </div>
              <div className="text-right text-xs text-slate-300">
                <p>{new Date(step.timestamp).toLocaleString()}</p>
                <p>
                  duration: {readStepDurationMs(step, orderedSteps[index - 1]) == null ? "-" : `${readStepDurationMs(step, orderedSteps[index - 1])} ms`}
                </p>
              </div>
            </div>

            {step.kind === "LLM_CALL" ? (
              <div className="mt-3 rounded-lg bg-slate-900/40 p-3 text-sm text-cyan-100">
                model: {step.data?.model} | tokens: {(step.data?.input_tokens ?? 0) + (step.data?.output_tokens ?? 0)} | cost: ${Number(step.data?.cost ?? 0).toFixed(6)}
              </div>
            ) : null}

            <div className="mt-3 grid gap-3 md:grid-cols-2">
              <JsonBlock title="input data" data={step.data?.input ?? step.data} />
              <JsonBlock title="output data" data={step.data?.output ?? {}} />
            </div>
          </article>
        ))}
      </section>

      {run.crash_analysis ? (
        <section className="mt-6 rounded-2xl border border-rose-400/40 bg-rose-500/10 p-4">
          <h2 className="text-lg font-semibold text-rose-100">Crash analysis (Claude)</h2>
          <pre className="mt-2 whitespace-pre-wrap text-sm text-rose-50">{run.crash_analysis}</pre>
        </section>
      ) : null}
    </main>
  );
}
