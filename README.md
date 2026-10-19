# Indian IPO Research & Data Analysis Platform

An institutional-grade, data-driven research, analysis, and decision-support platform designed specifically for the Indian Initial Public Offering (IPO) ecosystem (Mainboard & SME).

> **CRITICAL DISCLAIMER & MANDATORY OPERATING PRINCIPLE**  
> **No Guaranteed Returns:** This platform is strictly a research, historical backtesting, and decision-support system. Any reference to a **"40% return" or target scenario represents a conditional analytical hypothesis/target scenario**, NOT a guaranteed return, prediction, or financial advice. The platform does not execute automated trading, make definitive profit claims, or fabricate unverified financial metrics. All investments in public equity and IPOs carry substantial market risk, including potential loss of principal.

---

## 1. Project Purpose

The primary objective of this platform is to eliminate emotional bias and speculative hype around Indian IPOs by combining structured financial fundamental analysis, rigorous valuation benchmarking, real-time demand metrics, and indicative market sentiment into a reproducible, data-driven decision-support framework.

Key focus areas include:
- **Comprehensive Due Diligence:** Analyzing Red Herring Prospectuses (RHP), audited financial statements, capital structures, and disclosed risk factors.
- **Valuation Benchmarking:** Comparing IPO issue prices against industry peers and sector price-to-earnings (P/E) and price-to-book (P/B) multiples.
- **Demand & Sentiment Synthesis:** Integrating verified exchange subscription data (QIB, NII, Retail) with indicative Grey Market Premium (GMP) data.
- **Scenario & Upside Analysis:** Evaluating multi-scenario listing performance (Conservative, Base, Optimistic) and stress-testing conditions under which high-alpha scenarios (e.g., 40%+ listing gains) may materialize.
- **Historical Backtesting:** Tracking long-term listing day and post-listing performance against original research theses to iteratively refine selection criteria.

---

## 2. Platform Architecture & Capabilities (Phase 10)

The platform is implemented as a modular Python package with a production-grade FastAPI REST API and native interactive Web Dashboard:

- **Core Analytics & Recommendation Engine (`src/ipo_platform/recommendation`):** Multi-factor scoring model (0-100 score) evaluating financials, valuation (P/E relative to peers), subscription multiples (QIB, NII, Retail), and GMP sentiment with deterministic veto rules.
- **Backtest Validation Engine (`src/ipo_platform/backtest`):** Historical validation verifying recommendation efficacy against real listing day returns.
- **Portfolio Strategy Engine (`src/ipo_platform/portfolio`):** Institutional capital allocation with strict risk constraints (max 35% single-IPO cap, max 40% sector cap, total capital conservation, cash remainder).
- **FastAPI REST API Platform (`src/ipo_platform/api`):** Enterprise REST layer with dependency injection, DTO validation, and observability.
- **Native Single-Page Web Dashboard (`src/ipo_platform/api/routes/dashboard.py`):** Interactive zero-dependency HTML5/CSS/JavaScript interface delivered directly at `GET /` and `GET /dashboard`.
- **Security & Authorization (`src/ipo_platform/security`):** JWT authentication, API-key management, hierarchical RBAC (`READ_ONLY`, `OPERATOR`, `ADMIN`), rate limiting with Redis fail-safe support, and HTTP security headers.
- **Storage & Relational Ingestion (`src/ipo_platform/db`, `src/ipo_platform/io`):** SQLAlchemy ORM models, Alembic migrations, and JSON ingestors.

---

## 3. REST API Contract & Endpoints

| Method | Endpoint | Minimum Role | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Public | Interactive Web Dashboard Single-Page Application |
| `GET` | `/dashboard` | Public | Web Dashboard alias |
| `GET` | `/health` | Public | Subsystem diagnostic health probe (Database, Redis, Notifications) |
| `GET` | `/ipos` | `READ_ONLY` | Paginated listing of active/closed IPO offerings |
| `GET` | `/ipos/{ipo_id}` | `READ_ONLY` | Comprehensive master record for a specific IPO |
| `POST` | `/recommendation/evaluate` | `OPERATOR` | Evaluate multi-factor recommendation from IPO record or ID |
| `POST` | `/recommendation/validate` | `OPERATOR` | Historical cohort backtest validation against listing day outcomes |
| `POST` | `/portfolio/allocate` | `OPERATOR` | Institutional portfolio capital allocation with diversification caps |
| `GET` | `/metrics` | `ADMIN` | Prometheus-style telemetry counters, gauges, and request latency timers |

---

## 4. Authentication & RBAC

The API supports dual enterprise authentication methods:
1. **Bearer JWT Tokens:** Passed via `Authorization: Bearer <jwt_token>` header. Supports cryptographic signature verification, expiration enforcement, and revocation store checks.
2. **API Keys:** Passed via `X-API-Key: <api_key>` header.

### Role Hierarchy
- **`READ_ONLY`:** Permitted access to IPO listings, details, and health probes. Mutations and heavy evaluations are denied (HTTP 403).
- **`OPERATOR`:** All `READ_ONLY` permissions + recommendation evaluations, backtest validations, and portfolio allocations.
- **`ADMIN`:** All `OPERATOR` permissions + telemetry `/metrics` and administrative operations.

---

## 5. Local Setup & Execution

### Prerequisites
- Python 3.10+ (verified and tested on Python 3.12.10)
- **MySQL 8.0+** (authoritative Primary System of Record with binary logging enabled for CDC)
- **Redis 7.0+** (distributed lock engine, token revocation store, and rate limiter)
- **Apache Kafka + Debezium Connect** (Change Data Capture streaming pipeline; integration verified via Docker Compose)
- *Note:* Elasticsearch, Kibana, and Spring Boot are strictly out of scope and are not utilized.

### 1. Installation
```bash
pip install -r requirements.txt
pip install -e .
```

### 2. Environment Configuration
Copy `.env.example` to `.env` and configure your environment variables:
```bash
cp .env.example .env
```

### 3. Database Schema Migrations
Apply Alembic migrations to set up the 14 core domain tables and operational tables:
```bash
python -m ipo_platform.cli migrate
```

### 4. Run Web Dashboard & REST API
```bash
# Launch FastAPI REST server with embedded single-page dashboard
python -m ipo_platform.cli serve --host 0.0.0.0 --port 8000
# or directly with uvicorn
python -m uvicorn ipo_platform.api.app:app --host 0.0.0.0 --port 8000 --reload
```
Once started, access the Web Dashboard in your browser at:
**`http://localhost:8000/`** or **`http://localhost:8000/dashboard`**

API Documentation (when `DOCS_ENABLED=true`):
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 5. Run CLI Operations
```bash
# Display CLI help
python -m ipo_platform.cli --help

# Generate morning daily intelligence briefing
python -m ipo_platform.cli briefing --date 2026-10-14

# Execute historical strategy backtest
python -m ipo_platform.cli backtest

# Synchronize offerings from exchange feeds
python -m ipo_platform.cli sync-sources
```

### 6. Run Automated Test Suite
```bash
# Run comprehensive test suite via unittest (226 tests)
python -m unittest discover -s tests -p "test_*.py"

# Or run via pytest
pytest -q
```

---

## 6. Governance & Data Principles

1. **Source Attribution:** Every quantitative datapoint must be accompanied by its primary or secondary source and timestamp.
2. **Missing Data Transparency:** Never synthesize or hallucinate financial figures. If a metric is not published or disclosed, label it as `"Not available"`.
3. **No Guaranteed Returns:** This platform is strictly an analytical decision-support and research engine. Public IPO investments involve substantial market risk.

