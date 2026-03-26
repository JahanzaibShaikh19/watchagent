# watchagent License Server (Railway)

FastAPI service for Pro licensing and Stripe checkout.

## Endpoints

- `POST /api/license/validate`
- `POST /api/license/activate`
- `GET /api/license/status?license_key=<key>`
- `POST /api/stripe/checkout`
- `POST /api/stripe/webhook`

## Railway Deploy

Set environment variables:

- `STRIPE_SECRET_KEY`
- `STRIPE_PRICE_ID`
- `STRIPE_WEBHOOK_SECRET`
- `SENDGRID_API_KEY`
- `WATCHAGENT_FROM_EMAIL`
- `WATCHAGENT_SUCCESS_URL`
- `WATCHAGENT_CANCEL_URL`
- `WATCHAGENT_LICENSE_SECRET`

Config files included:

- `Dockerfile`
- `railway.json`
- `.env.example`

Run:

```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

Stripe webhook should point to:

- `https://<railway-domain>/api/stripe/webhook`

## Docker local run

```bash
docker build -t watchagent-license .
docker run --rm -p 8000:8000 --env-file .env.example watchagent-license
```
