# InvestorIQ AI — Frontend

React 19 + TypeScript + Vite UI for the AI-Powered Investor Intelligence
Platform. It provides three screens backed by the FastAPI backend:

- **Dashboard** (`/`) — financial overview with KPIs, comparison charts
  (Recharts) and company scorecards.
- **AI Research** (`/research`) — conversational RAG-based Q&A over the
  ingested annual reports.
- **Ingest Reports** (`/ingestion`) — drag-and-drop upload of annual
  reports with `{year}_{company}` filename validation.

## Stack

- Vite 8 + React 19 + TypeScript (strict)
- Tailwind CSS v4 (dark, financial-grade theme)
- Recharts for dashboards
- lucide-react icons

## Development

```bash
npm install
npm run dev
```

The Vite dev server proxies `/api/*` to the FastAPI backend on
`http://localhost:8000`. Open http://localhost:5173.

## Production

```bash
npm run build
```

Outputs a static bundle to `dist/`. Point `VITE_API_URL` at the backend
base URL when not using the dev proxy.

## Scripts

| Script            | Purpose                     |
| ----------------- | --------------------------- |
| `npm run dev`     | Start the Vite dev server   |
| `npm run build`   | Type-check + production build |
| `npm run preview` | Preview the production build |
| `npm run lint`    | Run Oxlint                  |