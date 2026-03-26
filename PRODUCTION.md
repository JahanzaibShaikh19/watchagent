# Production Rollout Guide

## 1) Pre-flight checks

Run these locally from repository root:

```bash
python -m compileall watchagent license-server
python -m build --sdist --wheel
cd dashboard-ui && npm run build
cd ../watchagent-web && npm run build
```

## 2) Publish Python package to PyPI

1. Ensure PyPI trusted publishing is configured for this repository and environment name `pypi`.
2. Create a GitHub Release (tag like `v0.1.0`).
3. GitHub Actions workflow in [publish.yml](.github/workflows/publish.yml) publishes automatically.

## 3) Deploy license backend to Railway

Service root: [license-server](license-server)

Required variables:

- STRIPE_SECRET_KEY
- STRIPE_PRICE_ID
- STRIPE_WEBHOOK_SECRET
- SENDGRID_API_KEY
- WATCHAGENT_FROM_EMAIL
- WATCHAGENT_SUCCESS_URL
- WATCHAGENT_CANCEL_URL
- WATCHAGENT_LICENSE_SECRET

Deployment files:

- [Dockerfile](license-server/Dockerfile)
- [railway.json](license-server/railway.json)

Post-deploy:

1. Set Stripe webhook URL to `/api/stripe/webhook`.
2. Verify endpoints:
   - `/api/license/validate`
   - `/api/license/activate`
   - `/api/license/status`

## 4) Deploy landing page to Vercel

Project root: [watchagent-web](watchagent-web)

Config files:

- [vercel.json](watchagent-web/vercel.json)
- [next.config.js](watchagent-web/next.config.js)

Required variable:

- NEXT_PUBLIC_STRIPE_CHECKOUT_URL

## 5) Deploy dashboard API (if hosting remotely)

Set these variables where API runs:

- WATCHAGENT_LICENSE_API
- SENDGRID_API_KEY (if email alerts enabled)
- WATCHAGENT_ALERT_FROM_EMAIL (optional)
- WATCHAGENT_DASHBOARD_URL (for alert links)

Run:

```bash
uvicorn watchagent.dashboard_api:app --host 0.0.0.0 --port 8000
```

## 6) Final go-live checks

- Verify license activation with a real key.
- Verify Stripe checkout and webhook delivery.
- Verify SendGrid email delivery.
- Verify dashboard loads for Pro plan and is blocked for Free plan.
- Verify export endpoint works for Pro plan.
- Verify alerts (Slack/email) on a simulated crash.

## 7) Launch tasks

Track completion in [LAUNCH.md](LAUNCH.md).
