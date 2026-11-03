# AI Travel Concierge Agent — Backend Service

### Automated E-Commerce Concierge Agent — AI Travel Planning Assistant

An intelligent goal-based AI travel planning backend service that recommends optimized flight and hotel packages using constraint satisfaction, cost optimization, and simulated booking workflows.

---

## 📌 Problem Statement

Planning multi-city travel requires evaluating combinatorially large numbers of flight and hotel pairings across budgets, calendar dates, and user preferences. Travelers face information overload, volatile pricing, and complex trade-offs between flight convenience and hotel quality. This project provides a robust, deterministic, and explainable AI backend agent that solves this constraint optimization problem.

---

## 🎯 Project Objectives

1. **Goal-Based Agent**: Formulate the recommendation task as an explicit goal optimization problem: minimize total package cost subject to strict constraint satisfaction.
2. **Hard Constraint Satisfaction**: Eliminate infeasible combinations (route continuity, chronological ordering, seat capacity, room occupancy, mandatory hotel stars, budget limits).
3. **Deterministic Optimization & Tie-Breaking**: Apply transparent multi-criteria tie-breakers (stops, duration, departure convenience, star rating, identifier).
4. **Transparent Explainability**: Provide clear mathematical cost breakdowns and actionable diagnostic reasons when a query is infeasible.
5. **Safe Booking Workflow**: Implement a two-phase offer verification and explicit user confirmation protocol before generating reservation identifiers.
6. **Independent Backend Service**: Expose clean REST endpoints via FastAPI for frontend and external client integrations.

---

## 🌟 Key Features

- **Goal-Based Intelligent Agent**: 7-stage cognitive pipeline (Perception, Goal Formulation, Candidate Generation, Constraint Satisfaction, Cost Calculation, Optimization, and Explanation).
- **Hard Constraints Enforcement**: Validates route continuity, temporal departure/return ordering, hotel location matching, daily room availability, seat capacity, budget ceilings, and hotel star requirements.
- **Deterministic Multi-Criteria Tie-Breaking**:
  1. Primary: Lowest total package cost in INR (₹)
  2. Tie-breaker 1: Fewer total flight stops
  3. Tie-breaker 2: Shorter total travel duration
  4. Tie-breaker 3: More convenient departure/arrival times
  5. Tie-breaker 4: Higher hotel star rating
  6. Tie-breaker 5: Deterministic identifier fallback
- **Transparent Cost Calculation**: Accurate formulas for per-passenger flight fares, per-room nightly hotel rates, party room sharing, and budget savings.
- **Diagnostic Infeasible Reporting**: When no package satisfies all constraints, the agent categorizes rejections (budget exceeded, star mismatch, lack of seats) and provides actionable adjustment suggestions.
- **Offer Revalidation & Two-Phase Booking**: Re-verifies inventory price and availability (`/api/verify-offer`) and requires explicit confirmation (`confirm: true`) for reservations (`/api/booking/confirm`).
- **Provider Abstraction**: Pluggable provider architecture with a zero-dependency offline Simulated Provider and an optional Amadeus API adapter.

---

## 🧠 AI Architecture & Working Methodology

### Cognitive Pipeline (Sense–Plan–Act)

```
┌────────────────────────────────────────────────────────┐
│               1. PERCEPTION & VALIDATION               │
│  Validate origin/dest, dates, adults, rooms, budget    │
├────────────────────────────────────────────────────────┤
│               2. GOAL FORMULATION                      │
│  Objective: min(Total Package Cost)                    │
│  Subject to: Hard Constraints(Package) == True         │
├────────────────────────────────────────────────────────┤
│        3. STATE-SPACE PRUNING & CANDIDATE GEN          │
│  Filter flights by route/date → Filter city hotels     │
│  Generate candidate combinations (outbound × return × hotel) │
├────────────────────────────────────────────────────────┤
│            4. CONSTRAINT SATISFACTION (CSP)            │
│  Prune candidates violating route continuity, timing,  │
│  seat capacity, room occupancy, stars, or budget       │
├────────────────────────────────────────────────────────┤
│              5. COST CALCULATION                       │
│  Compute per-passenger flight fares, nightly hotel     │
│  room rates, party room-sharing, and total cost        │
├────────────────────────────────────────────────────────┤
│         6. MULTI-CRITERIA OPTIMIZATION                 │
│  Rank valid packages: Cost → Stops → Duration →       │
│  Convenience → Star Rating → Deterministic ID          │
├────────────────────────────────────────────────────────┤
│          7. EXPLAINABILITY & TRANSPARENCY              │
│  Generate itemized cost breakdown, decision rationale, │
│  or diagnostic infeasible suggestions                  │
└────────────────────────────────────────────────────────┘
```

---

## 🛠️ Technology Stack

| Component | Technology | Description |
|---|---|---|
| **Language & Runtime** | Python 3.10+ (tested on Python 3.13) | Core backend logic & agent |
| **Web Framework** | FastAPI (>= 0.115.0) | High-performance asynchronous REST API |
| **Validation & Settings** | Pydantic V2 & Pydantic-Settings | Strict request/response schemas & configuration |
| **ORM & Database** | SQLAlchemy 2.0 & Alembic | Relational mapping for SQLite / PostgreSQL |
| **Testing** | pytest & HTTPX TestClient | Automated unit and integration test suite |
| **ASGI Server** | Uvicorn | Production-ready ASGI server |
| **External Integration** | Requests & Amadeus Adapter | Optional travel API adapter with simulated fallback |

---

## 📁 Repository Folder Structure

```text
AI-Travel-Concierge-Agent/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI entrypoint, CORS, lifespan & error handlers
│   │   ├── config.py                   # Pydantic Settings & environment variable loader
│   │   ├── database.py                 # SQLAlchemy engine, session maker, and Base
│   │   ├── agent/                      # Independent Goal-Based Intelligent Agent
│   │   │   ├── agent.py                # ConciergeAgent orchestrator (Stages 1–7)
│   │   │   ├── constraints.py          # Hard & soft constraint satisfiers
│   │   │   ├── optimizer.py            # Cost minimizer & deterministic tie-breakers
│   │   │   ├── explainer.py            # Decision rationale & diagnostic suggestions
│   │   │   ├── types.py                # Agent DTOs and data models
│   │   │   └── __init__.py
│   │   ├── api/                        # REST route handlers
│   │   │   ├── health.py               # GET /api/health
│   │   │   ├── flights.py              # GET /api/flights
│   │   │   ├── hotels.py               # GET /api/hotels
│   │   │   ├── recommendations.py      # POST /api/recommendations, GET /api/recommendations/{id}
│   │   │   ├── booking.py              # POST /api/verify-offer, POST /api/booking/confirm
│   │   │   └── __init__.py
│   │   ├── models/                     # SQLAlchemy ORM models
│   │   │   ├── flight.py               # Flight inventory entity
│   │   │   ├── hotel.py                # Hotel & daily availability entities
│   │   │   ├── booking.py              # Reservation entity
│   │   │   ├── recommendation.py       # Recommendation history persistence
│   │   │   └── __init__.py
│   │   ├── schemas/                    # Pydantic request & response validation schemas
│   │   │   ├── flight.py
│   │   │   ├── hotel.py
│   │   │   ├── booking.py
│   │   │   ├── recommendation.py
│   │   │   └── __init__.py
│   │   ├── services/                   # Travel provider adapters
│   │   │   ├── provider_interface.py   # Abstract provider contract
│   │   │   ├── simulated_provider.py   # Offline simulated flight/hotel provider
│   │   │   ├── amadeus_provider.py     # Amadeus test sandbox adapter with fallback
│   │   │   └── __init__.py
│   │   └── seeds/                      # Seed inventory and runner
│   │       ├── seed_data.py            # Flights & hotels across Indian corridors
│   │       ├── inventory_service.py    # Dynamic route inventory generator
│   │       └── run_seed.py             # CLI database populator
│   ├── tests/                          # Automated test suite (57 pytest cases)
│   │   ├── conftest.py
│   │   ├── test_agent.py               # Agent logic & constraint satisfaction tests
│   │   ├── test_api.py                 # REST endpoint integration tests
│   │   ├── test_scenarios.py           # Infeasible & failure edge cases
│   │   ├── test_provider_and_booking.py# Provider abstraction & booking verification
│   │   └── test_amadeus_adapter.py     # Amadeus adapter unit tests & error handling
│   ├── alembic/                        # Alembic database migrations
│   ├── alembic.ini
│   ├── requirements.txt                # Python backend dependencies
│   ├── pytest.ini                      # Pytest configuration
│   ├── .env.example                    # Environment configuration template
│   └── README.md                       # Dedicated backend technical documentation
├── docker-compose.yml                  # PostgreSQL database container definition
├── .gitignore                          # Git exclusions (ignores .env, venv, cache, db, frontend)
└── README.md                           # Main repository documentation
```

---

## 🚀 Backend Setup & Execution Instructions

### Prerequisites
- **Python**: 3.10+ (tested and verified on Python 3.13)
- **Database**: SQLite (default zero-dependency, auto-created) or PostgreSQL (optional via Docker Compose)

---

### Step-by-Step Setup (Windows PowerShell)

```powershell
# 1. Navigate to the backend directory
cd backend

# 2. Create a virtual environment
python -m venv venv

# 3. Activate the virtual environment
.\venv\Scripts\Activate.ps1

# 4. Install all backend dependencies
pip install -r requirements.txt

# 5. Create environment configuration from template
Copy-Item .env.example .env

# 6. Initialize database and seed simulated travel inventory
python -m app.seeds.run_seed

# 7. Start the FastAPI backend server
python -m uvicorn app.main:app --reload
```

> **macOS / Linux Alternative:**
> ```bash
> cd backend
> python3 -m venv venv
> source venv/bin/activate
> pip install -r requirements.txt
> cp .env.example .env
> python -m app.seeds.run_seed
> python -m uvicorn app.main:app --reload
> ```

---

## 🌐 API Verification & Interactive Documentation

Once the server is running on `http://127.0.0.1:8000`:

- **Health Check**:
  ```powershell
  Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health"
  ```
  Expected Response:
  ```json
  {
    "status": "online",
    "database": "healthy",
    "service": "Automated E-Commerce Concierge Agent",
    "version": "1.0.0"
  }
  ```

- **Interactive Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🧪 Running Automated Tests

Run the complete test suite (57 test cases):

```powershell
cd backend
python -m pytest -v
```

### Test Coverage Highlights

| Test File | Tests | Focus Areas |
|---|---|---|
| `test_agent.py` | 10 | Perception validation, room sharing calculations, tight-budget optimization, luxury fulfillment, infeasible explanations, deterministic tie-breaking |
| `test_api.py` | 13 | Health endpoint, flight/hotel filtering, scenario 1/2/3 integration, 422 input validation, recommendation history, UTF-8 rupee (₹) encoding |
| `test_scenarios.py` | 4 | Unseeded routes, group seat exhaustion, database connection failures, strict hotel star category mismatches |
| `test_provider_and_booking.py` | 21 | Provider interface abstraction, offer price revalidation, expired offers, explicit confirmation enforcement (`confirm: true`), duplicate booking prevention |
| `test_amadeus_adapter.py` | 9 | Unconfigured fallback, OAuth2 token acquisition, 401 unauthorized handling, 429 rate limit handling, timeout handling, flight parsing, sandbox disclaimers |

---

## 📋 API Endpoints Reference

All endpoints are dual-mounted under both `/api/*` and the root path:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check verifying service status and database connectivity |
| `GET` | `/api/flights` | Query available flights (filters: `origin`, `destination`, `date`, `airline`, `max_stops`) |
| `GET` | `/api/hotels` | Query available hotels (filters: `city`, `star_rating`, `max_price`, `amenity`) |
| `POST` | `/api/recommendations` | Execute goal-based recommendation agent and return ranked travel packages |
| `GET` | `/api/recommendations/{id}` | Retrieve a previously saved recommendation by UUID |
| `GET` | `/api/recommendations/history` | List recent recommendation search histories |
| `POST` | `/api/verify-offer` | Revalidate offer price and inventory availability prior to booking |
| `POST` | `/api/booking/confirm` | Submit reservation (requires explicit `confirm: true`) |

---

## ⚙️ Environment Variables

The backend uses Pydantic Settings configured via `backend/.env`. A complete template is provided in `backend/.env.example`:

| Variable | Default Value | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./concierge.db` | SQLAlchemy connection string (SQLite default, PostgreSQL supported) |
| `PROVIDER_MODE` | `simulated` | Inventory provider: `simulated` (default) or `amadeus` |
| `APP_ENV` | `development` | Application environment (`development` / `production`) |
| `API_V1_PREFIX` | `/api` | API route prefix |
| `CORS_ORIGINS` | `["http://localhost:5173", ...]` | Allowed CORS origins for frontend clients |
| `DEBUG` | `True` | Enable debug logs |
| `AMADEUS_CLIENT_ID` | `""` | Optional Amadeus API key (leave blank for simulated mode) |
| `AMADEUS_CLIENT_SECRET` | `""` | Optional Amadeus API secret |
| `AMADEUS_ENV` | `test` | Amadeus environment (`test` / `production`) |
| `AMADEUS_TIMEOUT_SECONDS` | `10` | HTTP request timeout for external APIs |

---

## ⚠️ Simulated Provider & Academic Disclaimer

> **IMPORTANT DISCLAIMER**:  
> The default travel provider operates entirely with **simulated inventory**. All flight schedules, seat inventories, hotel rooms, and prices are dynamically generated for academic and demonstration purposes. Booking references generated by this service (`SIM-RES-...`) are academic artifacts.  
> **No actual airline tickets or hotel bookings are made, and no monetary transactions occur.**  
> When the optional Amadeus adapter is enabled, it connects to the Amadeus Self-Service **Test Sandbox**, which also produces test-only reservations without real-world validity.

---

## 👥 Team Collaboration Guide

This repository contains the backend service. Teammates can clone the repository, run the backend locally, and work on their assigned features using Git feature branches.

### 1. Clone the Repository

```bash
git clone https://github.com/Kanakachala-boom/AI-Travel-Concierge-Agent.git
cd AI-Travel-Concierge-Agent
```

### 2. Create a Feature Branch

Always create a dedicated feature branch before starting work:

```bash
git checkout -b feature/your-assigned-task
```

### 3. Commit and Push Changes

```bash
git add .
git commit -m "Describe your changes clearly"
git push -u origin feature/your-assigned-task
```

After pushing, open a **Pull Request (PR)** on GitHub targeting the `main` branch.

### 4. Adding Collaborators

To give teammates push and pull access:
1. Navigate to the repository on GitHub: [https://github.com/Kanakachala-boom/AI-Travel-Concierge-Agent](https://github.com/Kanakachala-boom/AI-Travel-Concierge-Agent)
2. Click **Settings** → **Collaborators**
3. Click **Add people** and enter each teammate's GitHub username or email address
4. Teammates must accept the invitation sent to their email or GitHub notifications

### 5. Branch Naming Conventions

| Branch Prefix | Purpose | Example |
|---|---|---|
| `feature/` | New functionality or endpoints | `feature/user-profiles` |
| `bugfix/` | Bug fixes and patches | `bugfix/flight-filter-tz` |
| `test/` | Adding or updating tests | `test/add-stress-tests` |
| `docs/` | Documentation improvements | `docs/update-api-specs` |

---

## 🔒 Security & Contribution Rules

- **Never commit `.env` files** or any real API keys, passwords, or database credentials.
- The `.gitignore` is configured to exclude virtual environments (`venv/`), database files (`*.db`, `*.sqlite3`), local caches, and secrets.
- Always use `.env.example` as the reference template for environment configuration.
- Run tests (`python -m pytest -v`) before committing any code changes.

---

## 📄 License & Attribution

This project is developed for academic purposes as part of the **Automated E-Commerce Concierge Agent** course project.
