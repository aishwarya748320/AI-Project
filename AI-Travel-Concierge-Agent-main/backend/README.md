# Backend Service — Automated E-Commerce Concierge Agent
**Goal-Based AI Travel Assistant**

Academic Project Demonstration Date: **November 6, 2026**

---

## 1. Overview & Architecture

The backend is an intelligent, goal-based travel recommendation and booking engine built with **FastAPI**, **Pydantic V2**, and **SQLAlchemy**. It evaluates round-trip flight and hotel combinations across Indian corridors, validates strict hard constraints, optimizes for minimum total package cost in INR (₹), applies deterministic multi-criteria tie-breakers, revalidates candidate offers, and supports an explicit-confirmation booking workflow.

### AI Cognitive Architecture (Sense–Plan–Act)
1. **Perception & Validation**: Ingests travel requirements, airport codes, calendar dates, passenger counts, and budget.
2. **Goal Formulation**: Defines the objective function: $\min(\text{Total Package Cost})$ subject to $\text{Hard Constraints}(\text{Package}) == \text{True}$.
3. **State-Space Pruning & Candidate Generation**: Filters outbounds, returns, and hotel options matching requested cities and travel dates.
4. **Constraint Satisfaction**: Evaluates hard constraints: route continuity, chronological date order, return-after-arrival, seat capacity, room occupancy, mandatory hotel stars, mandatory stops, and budget limits.
5. **Cost Calculation**: Computes per-passenger flight fares, per-room nightly hotel rates, and party room sharing.
6. **Multi-Criteria Optimization**: Ranks valid packages by lowest cost, breaking ties deterministically (fewer flight stops $\rightarrow$ shorter duration $\rightarrow$ convenient times $\rightarrow$ higher star rating $\rightarrow$ deterministic ID).
7. **Explainability & Transparency**: Generates transparent rationale detailing constraints satisfied, itemized cost breakdowns, and explicit occupancy assumptions.

---

## 2. Prerequisites & Environment Setup

* **Operating System**: Windows 10/11 (with Windows PowerShell in VS Code)
* **Python Runtime**: Python 3.10+ (tested and verified on Python 3.13.2)
* **Database**: SQLite (default, self-contained `concierge.db`) or PostgreSQL

---

## 3. Windows PowerShell Setup Commands

Open VS Code in `E:\Projects\AI project` and open a PowerShell terminal (`Ctrl + ~`):

### Step 1: Navigate to Backend Directory
```powershell
cd "E:\Projects\AI project\backend"
```

### Step 2: Virtual Environment
```powershell
# Create virtual environment if not already present
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1
```
*(If PowerShell displays an execution policy restriction, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in your terminal session).*

### Step 3: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
```powershell
Copy-Item .env.example .env
```
Default `.env` settings:
```dotenv
DATABASE_URL=sqlite:///./concierge.db
PROVIDER_MODE=simulated
APP_ENV=development
API_V1_PREFIX=/api
CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173","http://localhost:3000"]
DEBUG=True

# Optional Amadeus Credentials (leave blank to run in simulated mode)
AMADEUS_CLIENT_ID=
AMADEUS_CLIENT_SECRET=
AMADEUS_ENV=test
AMADEUS_TIMEOUT_SECONDS=10
```

---

## 4. Database Initialization & Seeding

Run the seed script to create all tables and populate 32+ flights and 27+ hotels:
```powershell
python app/seeds/run_seed.py
```
*Output: `Successfully seeded database! Total flights: 32, Total hotels: 27`*

---

## 5. Starting the Server & Health Verification

### Launch Server
```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Health Check Verification
In a second PowerShell terminal:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health"
```
**Expected Response**:
```json
{
  "status": "online",
  "database": "healthy",
  "service": "Automated E-Commerce Concierge Agent",
  "version": "1.0.0"
}
```

Interactive API documentation is available at:
* **Swagger UI**: `http://127.0.0.1:8000/docs`
* **ReDoc**: `http://127.0.0.1:8000/redoc`

---

## 6. Endpoints Reference

All endpoints are dual-mounted with both `/api/*` (frontend contract) and `/*` (root alias):

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service and database health check |
| `POST` | `/api/recommendations` | Execute goal-based travel recommendation engine |
| `POST` | `/api/search-packages` | Endpoint alias matching identical payload |
| `GET` | `/api/recommendations/{id}` | Retrieve persisted search recommendation by UUID |
| `GET` | `/api/recommendations/history` | List recent recommendation search queries |
| `GET` | `/api/flights` | Query available flights with optional filters |
| `GET` | `/api/hotels` | Query available hotels with optional filters |
| `POST` | `/api/verify-offer` | Revalidate offer price & availability prior to booking |
| `POST` | `/api/booking/confirm` | Submit reservation (requires explicit `confirm: true`) |

---

## 7. Travel Provider Modes & Limitations

### Simulated Provider (Default — Demonstration Ready)
* **Configuration**: `PROVIDER_MODE=simulated`
* **Characteristics**: Deterministic, zero external API costs, supports Indian corridors and all grading test cases.
* **Data Source Labeling**: Every response explicitly carries `"data_source": "SIMULATED"` and `"currency": "INR"`.
* **Disclaimers**: Booking references (`SIM-RES-...`) clearly carry academic disclaimers. No actual tickets or monetary payments are processed.

### Optional Live Amadeus Adapter
* **Configuration**: `PROVIDER_MODE=amadeus` with `AMADEUS_CLIENT_ID` and `AMADEUS_CLIENT_SECRET`.
* **Capabilities**: OAuth2 token management, Flight Offers Search v2, Flight Pricing v1, and sandbox order creation.
* **Limitations**: In the Amadeus Self-Service Test environment, hotel search has limited geographic coverage and flight orders do not produce real airline tickets. If credentials are empty or fail, the adapter automatically falls back to simulated inventory without crashing.

---

## 8. Safe Booking Workflow

1. **Search**: Traveler submits requirements to `/api/recommendations` and receives candidate packages.
2. **Revalidation**: Client calls `/api/verify-offer` with `offer_id` and `expected_price`. If the offer was repriced or seats expired, the backend flags `"status": "OFFER_REPRICED"` or `"OFFER_EXPIRED"`.
3. **Explicit Confirmation**: Client calls `/api/booking/confirm`.
   * If `confirm: false`: The request is rejected (`"status": "CONFIRMATION_REQUIRED"`).
   * If `confirm: true`: Creates a tracked reservation (`SIM-RES-...`) with complete breakdown and disclaimer.

---

## 9. Automated Testing

Run the full automated test suite (39 tests):
```powershell
python -m pytest -v
```
**Test Coverage Breakdown**:
* `tests/test_agent.py` (6 tests): Agent perception, room calculation, tight budget, luxury trip, infeasible explanation, deterministic tie-breakers.
* `tests/test_api.py` (11 tests): Health, flights, hotels, scenario integration tests, 422 validation handling, history retrieval.
* `tests/test_scenarios.py` (4 tests): Unseeded routes, insufficient seats, DB disconnect simulation, strict hotel category mismatch.
* `tests/test_provider_and_booking.py` (9 tests): Provider abstraction, explicit labels, itemized calculations, offer revalidation (success, repriced, expired), booking without confirmation rejection, booking confirmation, provider rejection.
* `tests/test_amadeus_adapter.py` (9 tests): Unconfigured fallback, OAuth2 token acquisition, HTTP 401, HTTP 429 rate-limit, timeout, flight parsing, pricing detection, explicit confirmation enforcement, sandbox disclaimers.

---

## 10. Common Errors & Troubleshooting

1. **`ModuleNotFoundError: No module named 'pydantic_settings'`**:
   * *Resolution*: Ensure virtual environment is active (`.\venv\Scripts\Activate.ps1`) and run `pip install -r requirements.txt`.
2. **`Invoke-RestMethod : Unable to connect to the remote server`**:
   * *Resolution*: Ensure the Uvicorn server is running in Terminal 1 (`python -m uvicorn app.main:app --port 8000`).
3. **`HTTP 422 Unprocessable Content`**:
   * *Resolution*: Check request payload format. `adults` must be $\ge 1$, `budget` must be $> 0$, and `departure_date` must precede or equal `return_date`.
4. **`HTTP 500 Internal Server Error`**:
   * *Resolution*: Verify database file exists. Run `python app/seeds/run_seed.py` to regenerate `concierge.db`.

---

## 11. Demonstration Checklist (November 6, 2026)

- [ ] **Step 1**: Open PowerShell in `backend/` and activate virtualenv: `.\venv\Scripts\Activate.ps1`.
- [ ] **Step 2**: Run automated tests to prove 100% test passing: `python -m pytest -v` (39/39 pass).
- [ ] **Step 3**: Re-seed database if fresh state is desired: `python app/seeds/run_seed.py`.
- [ ] **Step 4**: Launch backend: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`.
- [ ] **Step 5**: Verify health endpoint: `Invoke-RestMethod http://127.0.0.1:8000/api/health`.
- [ ] **Step 6**: Demonstrate Scenarios:
  - **Scenario 1 (Tight Budget)**: Delhi $\rightarrow$ Mumbai, ₹20,000 budget, 1 adult $\rightarrow$ Agent selects cheapest package under budget.
  - **Scenario 2 (Luxury Trip)**: Delhi $\rightarrow$ Mumbai, ₹1,50,000 budget, 5★ Hotel $\rightarrow$ Agent satisfies luxury constraint within budget.
  - **Scenario 3 (Infeasible Trip)**: Delhi $\rightarrow$ Goa, ₹4,000 budget, 2 adults $\rightarrow$ Agent reports infeasible trip with rejection diagnostic summary and suggestions.
  - **Scenario 4 (Offer Verification & Booking)**: Call `/api/verify-offer` followed by `/api/booking/confirm` demonstrating explicit confirmation enforcement and academic disclaimer.
