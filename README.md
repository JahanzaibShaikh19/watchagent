# watchagent

watchagent is a debugger and monitor for AI agents.

Core dependencies: anthropic, click, rich, and sqlite3 (built into Python standard library).

## Install

```bash
pip install watchagent
```

## Quickstart

```python
from watchagent import watch, logger

@watch(name="my-agent", timeout=120, loop_limit=10)
def my_agent(task):
    logger.step("Searching web", data={"query": task})
    logger.tool_call("browser", input={"query": task}, output={"hits": 3})
    logger.llm_call("claude-sonnet-4", input_tokens=450, output_tokens=180)
    logger.decision("Route A chosen", reason="fastest path")
    return {"done": True}

my_agent("Find 3 product ideas")
```

Launch the dashboard:

```bash
watchagent serve
```

Production rollout checklist and deployment sequence:

- [PRODUCTION.md](PRODUCTION.md)

## CLI

```bash
watchagent list
watchagent show <id>
watchagent cost
watchagent serve
watchagent activate <license-key>
watchagent license-status
watchagent config --slack-webhook <url>
watchagent config --alert-email <email>
watchagent config --team-add <email>
watchagent export --format json --output ./runs.json
```

Data is stored locally in `~/.watchagent/logs.db`.

## Plans

### Free (default)

- 1 active monitored agent at a time
- 7 days log retention
- Terminal CLI only
- Local SQLite storage

### Pro ($15/month)

- Unlimited active monitored agents
- 90 days log retention
- Full web dashboard
- Replay mode
- Slack + email crash alerts
- Team sharing up to 5 members
- CSV/JSON export

## License activation

Activate once on the machine:

```bash
watchagent activate <license-key>
```

License checks run on startup and support a 7-day offline grace period.
Encrypted license data is stored in `~/.watchagent/config.json`.

## Dashboard

`watchagent serve` starts:

- FastAPI backend on `http://127.0.0.1:8000`
- React + Vite dashboard on `http://127.0.0.1:3001`

Backend endpoints:

- `GET /api/runs` paginated runs list
- `GET /api/runs/{id}` run detail
- `GET /api/runs/{id}/steps` run steps
- `GET /api/stats` total runs, success rate, monthly cost
- `GET /api/runs/live` SSE stream for live updates
- `DELETE /api/runs/{id}` delete run

The dashboard streams live events and updates timeline steps in real time for running agents.

## Alerts

Configure Slack and email alerts:

```bash
watchagent config --slack-webhook https://hooks.slack.com/services/...
watchagent config --alert-email ops@example.com
```

Set environment variable for SendGrid delivery:

```bash
SENDGRID_API_KEY=<your_sendgrid_key>
```

On crash, alerts include agent name, error, AI explanation, and a run dashboard link.

## License server + Stripe

A separate FastAPI service for Railway is available in `license-server/`.
It provides:

- `POST /api/license/validate`
- `POST /api/license/activate`
- `GET /api/license/status`
- `POST /api/stripe/checkout`
- `POST /api/stripe/webhook`

Webhook flow: successful Stripe checkout issues a license key and emails it via SendGrid.

Crash analysis uses the Anthropic Messages API when `ANTHROPIC_API_KEY` is set;
otherwise watchagent stores a local fallback explanation.
