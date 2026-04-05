# FinanceTracker — Track your income and expenses with ease

![Python Version](https://img.shields.io/badge/python-3.11-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
![Build Status](https://img.shields.io/badge/build-passing-brightgreen)

## Overview

FinanceTracker is a lightweight, full-stack personal finance web application built with FastAPI and vanilla HTML/JS. It lets you log income and expense transactions, assign categories, and visualise your financial health through an at-a-glance dashboard. All data persists across sessions in a database, and you can export your full transaction history to a spreadsheet-ready CSV at any time.

## Features

- **Log transactions** — record income or expense entries with amount, date, and a free-text description
- **Category tagging** — assign each transaction a category (e.g. Food, Rent, Salary) for organised tracking
- **Filter & search** — browse transaction history filtered by date range and/or category
- **Category breakdown** — summary view showing cumulative totals per category
- **Dashboard overview** — live income vs. expense comparison and running net balance
- **CSV export** — download all transactions as a CSV file compatible with Excel, Google Sheets, and LibreOffice
- **Edit & delete** — modify or remove any existing transaction at any time

## Prerequisites

| Dependency | Minimum Version | Notes |
|---|---|---|
| [Docker](https://docs.docker.com/get-docker/) | 24.x | Required for containerised setup |
| [Docker Compose](https://docs.docker.com/compose/) | 2.x | Bundled with Docker Desktop |
| [Python](https://www.python.org/downloads/) | 3.11 | Required for local setup only |
| [Make](https://www.gnu.org/software/make/) | 3.8 | Optional, simplifies commands |

## Quick Start

### Using Docker (recommended)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/personal-finance-tracker.git
cd personal-finance-tracker

# 2. Copy and configure environment variables
cp .env.example .env
# Edit .env with your preferred values (see Configuration section)

# 3. Build and start all services
docker compose up --build

# 4. Open the app
open http://localhost:8000
```

### Running Locally (without Docker)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/personal-finance-tracker.git
cd personal-finance-tracker

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install backend dependencies
pip install -r backend/requirements.txt

# 4. Copy and configure environment variables
cp .env.example .env

# 5. Start the backend
make run
# or directly:
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 6. Open frontend/index.html in your browser
open frontend/index.html
```

## API Reference

| Method | Path | Description | Auth Required |
|--------|------|-------------|:-------------:|
| `GET` | `/api/transactions` | List all transactions (supports `?category=` & `?start=`/`?end=` filters) | No |
| `POST` | `/api/transactions` | Create a new income or expense transaction | No |
| `GET` | `/api/transactions/{id}` | Retrieve a single transaction by ID | No |
| `PUT` | `/api/transactions/{id}` | Update an existing transaction | No |
| `DELETE` | `/api/transactions/{id}` | Delete a transaction | No |
| `GET` | `/api/summary` | Dashboard totals — total income, expenses, and net balance | No |
| `GET` | `/api/categories` | List all available categories | No |
| `GET` | `/api/export/csv` | Download full transaction history as a CSV file | No |

> **Note:** Authentication is not enabled by default. It is strongly recommended to add an auth layer before any public deployment.

## Configuration

Copy `.env.example` to `.env` and adjust values as needed before starting the application.

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy-compatible database connection string | `sqlite:///./finance.db` |
| `APP_HOST` | Host address the API server binds to | `0.0.0.0` |
| `APP_PORT` | Port the API server listens on | `8000` |
| `DEBUG` | Enable FastAPI debug/reload mode (`true`/`false`) | `false` |
| `CSV_DELIMITER` | Field delimiter used in CSV exports | `,` |
| `ALLOWED_ORIGINS` | Comma-separated list of CORS origins | `http://localhost:8000` |

## Testing

The test suite uses **pytest**. Run it with Make or directly:

```bash
# Using Make
make test

# Or directly (activate your venv first)
pip install -r backend/requirements.txt
pytest backend/ -v --tb=short
```

Test coverage is reported to the terminal. To generate an HTML coverage report:

```bash
pytest backend/ --cov=backend --cov-report=html
open htmlcov/index.html
```

Latest security scan results: **Bandit + Safety — HIGH: 0 | MEDIUM: 1 | LOW: 0 — ✅ Passed**

## Security

Please review our [SECURITY.md](SECURITY.md) for information on supported versions, how to report a vulnerability responsibly, and our disclosure policy. Do not open a public GitHub issue for security concerns.

## License

This project is licensed under the [MIT License](LICENSE).