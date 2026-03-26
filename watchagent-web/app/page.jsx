"use client";

import { motion } from "framer-motion";
import InstallCommand from "../components/InstallCommand";
import SectionReveal from "../components/SectionReveal";

const features = [
  {
    title: "Step Timeline",
    text: "See every decision your agent made, in order, with timestamps and tool context.",
  },
  {
    title: "Loop Detector",
    text: "Catch infinite loops before they burn budget, with warnings while the run is still live.",
  },
  {
    title: "Crash Explainer",
    text: "Get an AI-written explanation of the failure and immediate next fixes.",
  },
];

const stripeUrl = process.env.NEXT_PUBLIC_STRIPE_CHECKOUT_URL || "https://buy.stripe.com/test_watchagent_pro";

export default function HomePage() {
  return (
    <main className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 grid-overlay bg-grid-fade opacity-45" />

      <section className="scanline relative mx-auto flex min-h-screen w-full max-w-6xl flex-col justify-center px-6 pb-20 pt-24 sm:px-10">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: [0.2, 0.65, 0.25, 1] }}
          className="mb-5 inline-flex w-fit items-center gap-3 rounded-full border border-line bg-panel px-4 py-2 text-xs uppercase tracking-[0.2em] text-slate-300"
        >
          <span className="glow-dot bg-accent" />
          watchagent terminal mode: live
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 36 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.85, delay: 0.08, ease: [0.2, 0.65, 0.25, 1] }}
          className="max-w-4xl text-balance text-4xl font-bold leading-tight text-white sm:text-6xl"
        >
          Finally - a debugger for AI agents
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.85, delay: 0.16, ease: [0.2, 0.65, 0.25, 1] }}
          className="mt-6 max-w-2xl text-lg text-slate-300"
        >
          See exactly what your agent is thinking, where it gets stuck, and how much it costs.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 28 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.75, delay: 0.22 }}
          className="mt-10"
        >
          <InstallCommand />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 28 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.75, delay: 0.3 }}
          className="mt-6"
        >
          <a
            href="#demo"
            className="inline-flex rounded-xl border border-line bg-panelAlt px-5 py-3 text-sm font-semibold text-slate-100 transition hover:border-accent hover:text-accent"
          >
            View Demo
          </a>
        </motion.div>
      </section>

      <SectionReveal className="mx-auto w-full max-w-6xl px-6 py-20 sm:px-10">
        <h2 className="text-3xl font-bold text-white sm:text-4xl">Your agent crashed. Now what?</h2>
        <div className="mt-8 grid gap-6 md:grid-cols-2">
          <div className="rounded-2xl border border-rose-400/30 bg-rose-500/10 p-6">
            <p className="font-mono text-sm uppercase tracking-[0.2em] text-rose-200">Before watchagent</p>
            <p className="mt-3 text-slate-200">Blank terminal, no trace, no root cause, no confidence.</p>
          </div>
          <div className="rounded-2xl border border-accent/40 bg-accent/5 p-6">
            <p className="font-mono text-sm uppercase tracking-[0.2em] text-accent">After watchagent</p>
            <p className="mt-3 text-slate-100">Full step timeline, cost visibility, and AI explains exactly why it failed.</p>
          </div>
        </div>
      </SectionReveal>

      <SectionReveal className="mx-auto w-full max-w-6xl px-6 py-20 sm:px-10" delay={0.05}>
        <div id="demo" className="overflow-hidden rounded-3xl border border-line bg-panel">
          <div className="flex items-center justify-between border-b border-line px-5 py-3">
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-slate-400">Live demo</p>
            <p className="font-mono text-xs text-accent">agent running to crash to explain</p>
          </div>
          <div className="p-4">
            <video
              className="h-auto w-full rounded-2xl border border-line bg-black"
              autoPlay
              muted
              loop
              playsInline
              poster="/demo-poster.png"
              controls
            >
              <source src="/watchagent-demo.mp4" type="video/mp4" />
            </video>
            <p className="mt-3 text-sm text-slate-400">
              Drop your GIF or MP4 into public/watchagent-demo.mp4 before deploy.
            </p>
          </div>
        </div>
      </SectionReveal>

      <SectionReveal className="mx-auto w-full max-w-6xl px-6 py-20 sm:px-10" delay={0.08}>
        <h3 className="text-3xl font-bold text-white">Features</h3>
        <div className="mt-8 grid gap-5 md:grid-cols-3">
          {features.map((feature, index) => (
            <motion.article
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              className="rounded-2xl border border-line bg-panelAlt p-6"
            >
              <p className="font-mono text-xs uppercase tracking-[0.2em] text-accent">0{index + 1}</p>
              <h4 className="mt-3 text-xl font-semibold text-white">{feature.title}</h4>
              <p className="mt-3 text-slate-300">{feature.text}</p>
            </motion.article>
          ))}
        </div>
      </SectionReveal>

      <SectionReveal className="mx-auto w-full max-w-6xl px-6 py-20 sm:px-10" delay={0.1}>
        <h3 className="text-3xl font-bold text-white">Install</h3>
        <pre className="mt-6 overflow-x-auto rounded-2xl border border-line bg-panel p-5 font-mono text-sm text-slate-200">
{`pip install watchagent

from watchagent import watch

@watch(name="my-agent")
def my_agent(task):
    ...

watchagent serve  # opens dashboard`}
        </pre>
      </SectionReveal>

      <SectionReveal className="mx-auto w-full max-w-6xl px-6 py-20 sm:px-10" delay={0.12}>
        <h3 className="text-3xl font-bold text-white">Pricing</h3>
        <div className="mt-8 grid gap-6 md:grid-cols-2">
          <div className="rounded-2xl border border-line bg-panel p-6">
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-slate-400">Free</p>
            <p className="mt-4 text-3xl font-bold text-white">Solo devs</p>
            <p className="mt-2 text-slate-300">Forever free</p>
          </div>

          <div className="rounded-2xl border border-accent bg-accent/10 p-6 shadow-neon">
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-accent">Pro</p>
            <p className="mt-4 text-3xl font-bold text-white">$15/month</p>
            <p className="mt-2 text-slate-200">Teams + advanced features</p>
            <a
              href={stripeUrl}
              className="mt-6 inline-flex rounded-xl border border-accent bg-accent/20 px-5 py-3 text-sm font-semibold text-accent transition hover:bg-accent/30"
            >
              Checkout with Stripe
            </a>
          </div>
        </div>
      </SectionReveal>

      <footer className="mx-auto mt-16 w-full max-w-6xl border-t border-line px-6 py-10 sm:px-10">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-slate-500">watchagent.dev</p>
          <div className="flex items-center gap-5 text-sm text-slate-300">
            <a className="transition hover:text-accent" href="https://github.com/watchagent/watchagent" target="_blank" rel="noreferrer">
              GitHub
            </a>
            <a className="transition hover:text-accent" href="https://x.com/watchagent" target="_blank" rel="noreferrer">
              Twitter
            </a>
            <a className="transition hover:text-accent" href="https://docs.watchagent.dev" target="_blank" rel="noreferrer">
              Docs
            </a>
          </div>
        </div>
      </footer>
    </main>
  );
}
