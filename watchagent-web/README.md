# watchagent-web

Landing page for watchagent, built with Next.js 14, Tailwind CSS, and Framer Motion.

## Local development

1. Install dependencies:
   npm install
2. Start dev server:
   npm run dev
3. Open http://localhost:3000

## Build

npm run build
npm run start

## Stripe button

Set the checkout URL in Vercel environment variables:

- NEXT_PUBLIC_STRIPE_CHECKOUT_URL=https://buy.stripe.com/your-live-link

## Demo media

Drop your demo file into:

- public/watchagent-demo.mp4

Optional poster image:

- public/demo-poster.png

## Deploy to Vercel

Deployment config files included:

- `vercel.json`
- `next.config.js`

1. Import this folder as a Vercel project root: watchagent-web
2. Set framework preset: Next.js
3. Add environment variable: NEXT_PUBLIC_STRIPE_CHECKOUT_URL
4. Deploy
