# SmogShield AI: Urban Family Air Defense & Smog Navigator

> **GenAI-powered family air defense and smog assistant** designed for urban Indian families navigating severe winter air pollution (PM2.5/PM10 crises). Built with FastAPI, Google Gemini (`gemini-3.8-flash`), React 18, and Vite.

---

## Overview

SmogShield AI is built specifically for working parents, school-age children, and budget-conscious urban Indian households facing toxic winter smog crises in Delhi NCR and Indo-Gangetic plains. It bridges verified environmental data with practical, low-cost household actions and culturally attuned conversational guidance.

### Core Capabilities

1. **Air Quality Dashboard (Phase 2 & 3)**: Official CPCB National AQI (NAQI) calculation with explicit data provenance (`PROVIDER_REPORTED`, `CALCULATED`, `SIMULATED_DEMO`), criteria pollutant sub-indices (PM2.5, PM10, NO2, CO, O3, SO2), and configurable freshness tracking (Fresh, Stale, Expired).
2. **Personalized Daily Activity Planner (Phase 4)**: Condition-based scheduling for school commutes, outdoor play, work travel, and senior walks—without arbitrary static time windows.
3. **Indoor Air Advisor (Phase 4)**: Clean Air Delivery Rate (CADR) room-sizing calculator, step-by-step affordable DIY Corsi-Rosenthal fan-filter instructions, damp cleaning protocols, condition-based window ventilation alerts, and evidence-based plant reality checks.
4. **Green Alternatives & Sustainable Transport (Phase 5)**: Documented CO2 emission comparisons (ARAI & CEA benchmarks) based on distance and passenger occupancy, alongside qualitative in-transit particulate exposure guidance.
5. **Environmental Impact Tracker (Phase 5)**: Transparent cumulative CO2 savings and commute optimization with explicit formulas and zero vanity metrics.
6. **AI Conversational Assistant (Phase 6)**: Grounded Google Gemini integration (`gemini-3.8-flash`) delivering trilingual (English, Hindi, and natural Hinglish) advice with strict deterministic public health guardrails and non-medical disclosures.

---

## System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Frontend (React 18 + Vite)                       │
│  - Responsive Tailwind UI (Desktop / Tablet / Mobile)                  │
│  - Trilingual Switcher (English / Hindi / Hinglish)                   │
│  - Decoupled Authoritative Guidance Card (Rendered Directly)           │
│  - Chat History (In-memory, Bounded 6 Messages / 3 Turns)              │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / REST (JSON)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       Backend (FastAPI + Pydantic v2)                   │
│  ├── /api/v1/aqi         ── CPCB NAQI Engine & Station Ingestion       │
│  ├── /api/v1/planner     ── Daily Activity & Public Health Engine      │
│  ├── /api/v1/advisor     ── CADR & Indoor Air Quality Engine           │
│  ├── /api/v1/transport   ── ARAI/CEA Emission Comparison Engine        │
│  ├── /api/v1/impact      ── Cumulative Carbon Savings Ledger           │
│  └── /api/v1/assistant   ── Context Assembly & Conversational Engine   │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │ Authoritative Context          │ Rate-Limited REST
                    ▼                                ▼
┌───────────────────────────────────────┐ ┌──────────────────────────────┐
│  Phase 2-5 Deterministic Services     │ │ Google Gemini REST API       │
│  - CPCB NAQI Breakpoint Engine (2014) │ │ Model: gemini-3.8-flash      │
│  - NCDC/MoHFW Health Guidelines (2025)│ │ Timeout: 10.0s monotonic     │
│  - Bounded Semaphore Concurrency (10) │ │ System Instructions Locked   │
└───────────────────────────────────────┘ └──────────────────────────────┘
```

### Deterministic Public Health Fallback Architecture

To ensure public safety during smog emergencies:
- Public health advisories and protective actions are computed **deterministically** by backend engines directly from official National Centre for Disease Control (NCDC, 2025) and CPCB tables.
- The generative AI layer (`gemini-3.8-flash`) provides natural language explanation and contextual answers, but **cannot override, alter, or dilute** deterministic guidance.
- If the Gemini API key is missing, network calls fail, quota is exceeded, or timeout occurs, the backend activates its **deterministic fallback engine**, delivering full authoritative public health guidance and audited citations in English, Hindi, or Hinglish with zero UI failure.

---

## Tech Stack

| Layer | Technologies | Standards / Guidelines |
|---|---|---|
| **Frontend** | React 18, Vite 5, TypeScript 5, Tailwind CSS 3 | Responsive mobile-first design, WCAG-compliant contrast |
| **Backend** | Python 3.12+, FastAPI, Pydantic v2, HTTPX | Async concurrency, sliding-window rate limiting |
| **Generative AI** | Google Gemini API (`gemini-3.8-flash`) | Strict role mapping (`user` / `model`), immutable system instructions |
| **Environmental Standards** | CPCB NAQI Guidelines (2014), NCDC MoHFW Health Advisories (2025) | Indian national air quality breakpoints, ARAI/CEA emission factors |
| **Testing** | Pytest, FastAPI TestClient | 261 unit & integration tests (all verified via mocked backends; no live API calls) |

---

## Quickstart Guide

### Prerequisites
- Python 3.12+
- Node.js 18+ and npm
- (Optional) Google Gemini API Key from Google AI Studio

### 1. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env

# Run test suite to verify installation (261 passing tests)
pytest tests/ -q

# Start backend server
uvicorn app.main:app --reload --port 8000
```

The backend API will be available at `http://localhost:8000`.
- Health Check: `http://localhost:8000/api/v1/health`
- Assistant Health Check: `http://localhost:8000/api/v1/assistant/health`
- OpenAPI Swagger Docs: `http://localhost:8000/docs`

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment variables
cp .env.example .env

# Verify production build
npm run build

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173`.

---

## Environment Variables

### Backend Configuration (`backend/.env`)

| Variable | Description | Default / Example |
|---|---|---|
| `APP_NAME` | Service name | `SmogShield AI Backend` |
| `APP_ENV` | Application environment (`development`, `production`) | `development` |
| `API_V1_PREFIX` | Prefix for API routes | `/api/v1` |
| `CORS_ORIGINS` | Permitted browser origins | `["http://localhost:5173", "http://localhost:3000"]` |
| `DEMO_MODE` | Offline simulated demo data toggle | `false` |
| `GEMINI_API_KEY` | Google Gemini API Key | *(Optional; falls back to deterministic engine if empty)* |
| `GEMINI_MODEL` | Gemini model name | `gemini-3.8-flash` |
| `ASSISTANT_SMOKE_TEST_TOKEN` | Secret token for operator diagnostic smoke test (sent via `X-Operator-Token` header) | *(Optional; disables smoke test if empty)* |
| `TRUSTED_PROXY_IPS` | Trusted reverse proxy IPs for `X-Forwarded-For` | `[]` |
| `DATA_GOV_IN_API_KEY` | CPCB data.gov.in API Key | *(Optional)* |
| `OPENAQ_API_KEY` | OpenAQ v3 API Key | *(Optional)* |
| `FRESH_THRESHOLD_HOURS`| Hours before data is marked stale | `4.0` |
| `STALE_THRESHOLD_HOURS`| Hours before data is marked expired | `24.0` |

### Frontend Configuration (`frontend/.env`)

| Variable | Description | Default |
|---|---|---|
| `VITE_API_BASE_URL` | Base URL for backend API v1 endpoints | `http://localhost:8000/api/v1` |
| `VITE_APP_TITLE` | Application Title | `SmogShield AI` |

---

## Privacy, Safety & Guardrails

- **Data Transmission to Google Gemini**: When the Gemini API key is configured and the AI service is available, user-written questions, bounded conversation history (max 6 messages), and anonymized environmental context parameters (station ID, room geometry, travel mode) are transmitted to Google Gemini for natural language explanation. Private session bearer tokens (e.g. `X-Session-ID`, `X-Operator-Token`) are **never** transmitted to Gemini. Unnecessary personal identifiers are not intentionally added to the Gemini request context. **Users should avoid entering sensitive personal information** (medical records, addresses, government IDs) in assistant messages.
- **Untrusted History Handling**: Previous conversation messages are explicitly treated by the backend as unverified conversational context, never as ground truth or authoritative facts.
- **Strict Role Mapping**: Client-sent history is restricted strictly to `user` and `assistant`. In Gemini REST requests, these are mapped strictly to `user` and `model`. `system` role injection from clients is rejected with HTTP 422.
- **Rate Limiting**: In-memory sliding-window limiter restricts chat requests to 15 requests/minute per client IP (with trusted right-to-left `X-Forwarded-For` traversal).
- **Non-Medical Disclaimer**: All assistant responses and views include an explicit public health disclaimer stating that guidance is based on CPCB and NCDC advisories, not clinical medical diagnosis or prescription.

---

## Operator Diagnostic Smoke Test

The backend includes a dedicated diagnostic endpoint for operators to test Gemini API connectivity:
- **Endpoint**: `POST /api/v1/assistant/smoke-test`
- **Protection**: Protected by `X-Operator-Token` header. The backend compares this against the configured `ASSISTANT_SMOKE_TEST_TOKEN` using constant-time comparison.
- **Fails Closed**: If `ASSISTANT_SMOKE_TEST_TOKEN` is unset or blank, returns `503 Service Unavailable`.
- **Pre-Auth Rate Limiting**: Max 3 requests per 10 minutes per IP before checking credentials, preventing token brute-force attempts.
- **Frontend Isolation**: Ordinary UI controls and users never have access to this endpoint.

---

## Competition Demonstration Plan

### Scenario 1: Air Quality Crisis & Family Protection (English)
1. Navigate to **AQI Dashboard**: View demo station readings for Delhi ITO (simulated AQI ~340, Very Poor, `SIMULATED_DEMO` provenance). Note pollutant breakdown (dominant PM2.5). *(When `DEMO_MODE=true` or using mock provider; for live readings, configure `DATA_GOV_IN_API_KEY`.)*
2. Open **AI Assistant**: Notice the top readiness pill showing model status (`gemini-3.8-flash`).
3. Select Quick Suggestion or ask: *"Is it safe for my 8-year-old child to play football outside right now?"*
4. Observe the **Authoritative Guidance Card**: Action Priority (`STRICT_AVOIDANCE`), NCDC recommendations for schoolchildren, and certified mask guidance.
5. Review the **Grounded Citations**: Official data sources from CPCB NAQI 2014 and NCDC 2025.

### Scenario 2: Multilingual Hindi & Hinglish Experience
1. Switch language toggle to **हिंदी**:
   - Ask: *"क्या मैं बाहर टहलने जा सकता हूँ?"*
   - Verify prompt response in clear, culturally fluent Hindi advising vulnerable groups and elderly against morning walks during winter temperature inversions.
2. Switch language toggle to **Hinglish**:
   - Ask: *"Bhai kya morning walk safe hai?"*
   - Verify natural conversational Hinglish response while public health guardrails remain strictly intact.

### Scenario 3: Resilience & Deterministic Fallback Demonstration
1. Disconnect or omit `GEMINI_API_KEY`.
2. Send any air pollution or travel question.
3. Observe that the application **does not crash or show an empty screen**:
   - Authoritative Public Health guidance is immediately rendered from the local deterministic engine.
   - Assistant displays a structured fallback explanation with full CPCB/NCDC citations.
   - Amber status badge clearly informs the user that deterministic fallback mode is active.

---

## Known Limitations

1. **Air Quality Sensors**: SmogShield AI relies on official outdoor monitoring stations (CPCB / OpenAQ). In the absence of a personal indoor air sensor, indoor estimates are based on geometrical room volume, Clean Air Delivery Rate (CADR), and standard air-exchange physics formulas without claiming unverified sensor precision.
2. **Medical Diagnosis**: Recommendations are strictly public health advisories and exposure-reduction tactics. They do not constitute individualized clinical treatment or prescriptions for respiratory illnesses.
3. **Session Persistence**: Chat history is session-bound in client memory. Refreshing the browser resets the conversation state, ensuring maximum user privacy.
4. **Live Gemini API Verification**: The Gemini REST client is implemented and verified using mocked tests. Live Gemini API connectivity has not yet been verified because `GEMINI_API_KEY` and `ASSISTANT_SMOKE_TEST_TOKEN` are not configured. Once credentials are provisioned, run the operator smoke test (`POST /api/v1/assistant/smoke-test` with `X-Operator-Token` header) to confirm live connectivity. The application remains fully functional through deterministic features while Gemini is unavailable.

---

## License

MIT License. Designed and developed for urban family health defense.
