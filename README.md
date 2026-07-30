# AI Personal Finance Platform — Project Guide

A standalone reference for this project: what it is, why it's built the
way it is, and what needs to exist, in what order, to build it.

---

## 1. What this is

A self-hosted, AI-assisted personal finance platform. It pulls in your
financial transactions (starting from CSV exports, later from a live bank
connection), understands and categorizes them, and over time acts as a
financial coach — answering questions like "can I afford this?" or "where
did my money go this month?"

It runs entirely on infrastructure you own and control — no financial data
leaves your own network unless a feature explicitly requires it.

The project has two intertwined goals:
1. A genuinely useful personal finance tool.
2. A hands-on rebuild of the underlying home infrastructure, done from
   scratch for real understanding rather than inherited from a prior
   AI-assisted build. An existing homelab repo is used as a reference for
   ideas and structure, but not copied — the point is understanding why
   each piece exists, not saving time.

---

## 2. Core principles

These apply throughout the build, not just at the start.

- **API-first** — one FastAPI backend, multiple possible clients (CLI,
  web, eventually mobile). The backend is the actual application;
  everything else just talks to it.
- **Local-first / self-hosted** — everything runs on hardware you own
  (a Pi, a mini PC, a spare laptop), not a rented server.
- **Modular, swappable parts** — the transaction import mechanism, the
  storage layer, the bank connection, are all interchangeable without
  rewriting the rest of the system (e.g. a `TransactionProvider`
  abstraction that CSV and later a bank API both implement).
- **Deterministic finance logic, AI only where it adds value** — actual
  money math (totals, budgets, statistics) is never done by AI. AI
  handles judgment calls: categorizing an unfamiliar merchant,
  describing a pattern in plain language, answering open-ended
  questions.
- **Every stage produces something usable** — no stage should end with
  only plumbing and nothing to show for it.
- **Infra only grows when the app needs it** — no monitoring stack, no
  staging environment, no CI/CD pipeline until there's something real
  enough to justify them.

---

## 3. What the finished system looks like

- A personal database of transactions, accounts, and categories.
- CSV import as the reliable baseline, plus a live bank connection later.
- Automatic categorization: known merchants sort themselves via rules;
  unknown ones get an AI-suggested category you confirm once, which then
  becomes a permanent rule.
- Deterministic reports and dashboards: spending by category, income vs.
  expenses, trends, largest purchases.
- Budgets with warnings when you're close to or over a limit.
- A conversational assistant that answers real questions about your own
  spending and can forecast ahead — always grounded in real transaction
  data, never invented.
- Multiple clients: CLI first, then a web dashboard, eventually a phone
  app — all talking to the same backend.
- Running continuously on your own hardware, with monitoring, backups,
  and a safe staging step before changes reach the version you rely on.

---

## 4. Build order

Each step assumes the previous ones are genuinely working, not just
started.

### 1. Domain core + CSV import
No infra yet. Build `Account`, `Transaction`, and `Category` models,
CSV import, and rule-based categorization ("merchant contains SPAR →
Groceries") entirely as a local Python project (`uv`, plain scripts).
End result: a real spending report generated from your own bank's
exported CSV, run locally. Target: 2–3 weekends. No Docker, no AI yet.

### 2. Base infra — single machine
One always-on box (Pi / mini PC / old laptop). Set up fresh: Ubuntu
Server, your own Ansible inventory and control node (written from
scratch — reference the old repo's `setup_servers.yml` for shape only,
don't copy it), Docker + Docker Compose, and an Nginx reverse proxy.
Nothing else yet — no Portainer, no Homer, no monitoring stack; there's
only one service worth managing at this point.

### 3. REST API
Wrap the domain logic from Step 1 in FastAPI + SQLModel, so it's
reachable over a network instead of only as local scripts. Endpoints:
`/transactions`, `/accounts`, `/categories`, `/health`, `/version`. This
is what makes a CLI, a web UI, and eventually a phone app all possible
later — they'll just be different clients of this same API.

### 4. CLI
A Typer-based command-line tool wrapping the API/domain layer: `sync`,
`transactions`, `report`, `dashboard`, `categories`. This becomes the
primary way to use and test the system during development, before any
graphical interface exists.

### 5. First deployment
Containerize the application, push a versioned image (never `latest`
in production), and deploy it via Step 2's Nginx + Compose setup on the
single machine. First point where the infra and the app actually meet.

### 6. Observability
Add Prometheus, Grafana, and Loki now that there's a real API emitting
metrics and logs worth watching — not set up speculatively beforehand.
Reference the old repo's monitoring playbook for structure.

### 7. Bank API integration
CSV stays primary, not a fallback. Prototype **GoCardless Bank Account
Data** specifically — it's the realistic option for personal (non
business) use, with a free tier, but expect a small limit on free bank
connections and roughly 90-day re-authentication (a PSD2 SCA
requirement, not a GoCardless-specific limitation). Check whether BAWAG
exposes retail open banking directly before assuming an aggregator is
needed at all. Build this as a swappable `TransactionProvider`
implementation so a dead end here doesn't block anything else.
**From this point on: bank credentials are encrypted at rest, no
exceptions.**

### 8. Staging environment
A second machine (or a staging Compose stack on the same box) so
changes can be tested before touching the version you actually rely on.
Promotion workflow: deploy → test on staging → promote to prod,
conceptually modeled on the old repo's two-laptop setup but rebuilt
yourself.
**Non-negotiable before this step: a working SQLite backup/restore
plan** — real financial history now exists and needs to survive a disk
failure.

### 9. CI/CD
Decision point: the old repo uses Jenkins; the stated direction from
your AAP/CasC work at SVC was GitHub Actions with a self-hosted runner.
Starting fresh is the natural point to standardize on the toolchain you
actually want long-term rather than defaulting to Jenkins because it's
already there. Pipeline: lint (Ruff) → type check → unit tests →
integration tests → build container → security scan → push versioned
image → deploy to staging → promote to prod.

### 10. Analytics
Deterministic only, no AI: monthly spending, income vs. expenses,
spending trends, largest purchases, cash flow.

### 11. AI categorization
Rules always run first. AI only suggests a category for merchants no
rule matches; you confirm once, and the app creates a permanent rule
from it — the AI's role shrinks over time as the rule set grows.

### 12. Budgets
Monthly and per-category budgets, remaining budget tracking, and
overspend/warning alerts.

### 13. AI insights + forecasting
Open-ended questions get answered — why a month was expensive, what
changed, end-of-month and cash-flow predictions. Every insight must
reference real transaction data; nothing generic or invented.

### 14. Web dashboard
A full graphical frontend: charts, reports, budgets, goals, and an AI
chat interface, becoming the primary day-to-day client.
**Non-negotiable: if this or the API is ever exposed outside your LAN,
WireGuard-based remote access is set up before that exposure, not
after.**

### 15+. Long-term, unscheduled
Financial coach conversations, savings/house/vacation goal tracking,
behavioral analysis (impulse buying, subscription creep, spending
spikes), a native Android app, additional data sources (PayPal, email
receipts, investment accounts, crypto, cash), and eventually expansion
beyond finance into a broader personal data platform (calendar, tasks,
email, health, documents). Revisit once Steps 1–14 are real and in
daily use, rather than committing to any of it now.

---

## 5. Standing rules

- Real money calculations are never left to AI judgment — only
  categorization, explanation, and conversation are.
- Nothing moves to the next step until the current one is genuinely
  working, not just scaffolded.
- Bank credentials and financial history are treated as sensitive from
  the moment they exist — encrypted storage and a backup plan are not
  optional extras.
- Infrastructure is built to be understood, even where a working
  reference already exists to compare against — write it yourself,
  even when copying would be faster.