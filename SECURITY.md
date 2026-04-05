# SECURITY.md

# Security Documentation — FinanceTracker

> **Project:** personal-finance-tracker
> **Application Type:** Full-Stack Web (FastAPI + HTML/JS)
> **Last Updated:** 2025
> **Maintainer:** FinanceTracker Development Team

---

## 1. Security Controls Implemented

### 1.1 Authentication & Authorization

| Status | Detail |
|--------|--------|
| ⚠️ **Not Implemented** | FinanceTracker currently operates as a **single-user personal application** with no authentication layer. All API endpoints in `backend/main.py` are publicly accessible to anyone who can reach the server. |

**Risk:** If deployed on a network-accessible host (non-localhost), any user on the network can read, create, edit, or delete financial transactions.

**Recommendation:** Implement authentication before any non-local deployment (see Section 4).

---

### 1.2 Input Validation & Sanitization

| Control | Location | Detail |
|---------|----------|--------|
| **Pydantic model validation** | `backend/main.py` — request models | All incoming transaction payloads are validated via Pydantic `BaseModel` schemas. Field types (amounts, dates, descriptions) are enforced at the framework level. |
| **`field_validator` / `model_validator`** | `backend/main.py` | Custom validators are applied using `@field_validator` and `@model_validator` decorators to enforce business rules (e.g., non-negative amounts, valid date ranges). |
| **Query parameter typing** | `backend/main.py` — `Query(...)` annotations | FastAPI's `Query` dependency with `Annotated` types enforces type coercion for all filter parameters (date range, category). |
| **⚠️ SQL query construction** | `backend/main.py`, line 281 | A dynamic SQL query is constructed via string formatting — see Section 2 for full details. |

---

### 1.3 CORS Policy

| Status | Detail |
|--------|--------|
| ⚠️ **Not Explicitly Configured** | No `CORSMiddleware` is registered in `backend/main.py`. FastAPI defaults to **no CORS headers**, which prevents cross-origin browser requests. This is acceptable for a same-origin deployment (static files served via `StaticFiles` mount) but must be explicitly configured if the frontend is ever served from a separate origin. |

**Current architecture:** The frontend (`frontend/index.html`) is served directly by FastAPI via `StaticFiles`, making it same-origin. No external origins require CORS access.

---

### 1.4 Rate Limiting

| Status | Detail |
|--------|--------|
| ❌ **Not Implemented** | No rate limiting middleware (e.g., `slowapi`) is present in `backend/main.py`. All API endpoints are unbounded. |

This is a low-risk gap for a personal single-user tool on localhost, but represents a hardening opportunity for any networked deployment.

---

### 1.5 Secrets Management

| Control | Detail |
|---------|--------|
| **No hardcoded credentials found** | A review of `backend/main.py` found no hardcoded passwords, API keys, or tokens. |
| **SQLite database** | The application uses a local SQLite database file. The path is configured in `backend/main.py`. No database credentials are required or stored. |
| **Docker Compose** | `docker-compose.yml` does not include any secret environment variables. If secrets are added in the future, use Docker secrets or a `.env` file excluded from version control. |

**Recommendation:** Add a `.env` file pattern with a corresponding `.gitignore` entry before introducing any credentials (e.g., a secret key for JWT signing).

---

### 1.6 HTTPS Enforcement

| Status | Detail |
|--------|--------|
| ⚠️ **Not Enforced at Application Level** | The application runs plain HTTP as configured in `Dockerfile` and `docker-compose.yml`. There is no TLS termination, HTTPS redirect middleware, or `HTTPSRedirectMiddleware` registered in `backend/main.py`. |

**Current risk:** Acceptable for localhost personal use. **Unacceptable** for any deployment over a network. All transaction data (financial amounts, categories, dates) would be transmitted in plaintext.

**Recommendation:** Place the application behind a reverse proxy (nginx/Caddy) with TLS, or add `HTTPSRedirectMiddleware` in `backend/main.py`.

---

### 1.7 Dependency Management

| Control | Location | Detail |
|---------|----------|--------|
| **Pinned dependencies** | `backend/requirements.txt` | Dependencies should be pinned to exact versions (e.g., `fastapi==x.y.z`) to prevent supply-chain drift. |
| **Minimal dependency footprint** | `backend/requirements.txt` (3 lines) | The backend has a very small dependency surface, reducing CVE exposure. |
| **No known CVEs detected** | Safety scan results | The Safety dependency scan returned **no CVE findings** for the declared dependencies (see Section 2). |
| **Docker base image** | `Dockerfile` | Ensure the base image is regularly updated and pinned to a specific digest for reproducibility. |

---

## 2. Static Analysis Results

Scans were performed using **Bandit** (Python AST security linter) and **Safety** (dependency CVE checker).

### 2.1 Bandit Findings

| # | Rule ID | Severity | File | Line | Description | Status |
|---|---------|----------|------|------|-------------|--------|
| 1 | **B608** | 🟡 **MEDIUM** | `backend/main.py` | 281 | Possible SQL injection vector through string-based query construction | ⚠️ **Open — Requires Remediation** |

#### B608 — Detail & Remediation Guidance

**Finding:**
```
backend/main.py, line 281
Rule: B608 — Possible SQL injection via string-based query construction
Severity: MEDIUM
```

**Description:**
At line 281 in `backend/main.py`, a SQL query is being assembled using Python string operations (f-string or `%` formatting, or concatenation) rather than parameterized placeholders. If any user-controlled value (such as a `category` filter string, date range, or description) is interpolated directly into the query string, an attacker could manipulate the SQL statement.

**Example of the vulnerable pattern:**
```python
# ❌ Vulnerable — do not use
query = f"SELECT * FROM transactions WHERE category = '{category}'"
conn.execute(query)
```

**Correct remediation — use parameterized queries exclusively:**
```python
# ✅ Safe — parameterized query
query = "SELECT * FROM transactions WHERE category = ?"
conn.execute(query, (category,))
```

For dynamic `WHERE` clause construction (e.g., optional filters for date range AND category), build the clause with placeholder tokens and accumulate parameters in a list:

```python
# ✅ Safe dynamic filter construction
conditions = []
params = []

if category:
    conditions.append("category = ?")
    params.append(category)

if date_from:
    conditions.append("date >= ?")
    params.append(date_from)

where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
query = f"SELECT * FROM transactions {where_clause} ORDER BY date DESC"
conn.execute(query, params)
```

**Accepted Risk?** **No.** This finding must be remediated before any networked deployment. Even in a personal tool, SQL injection in a finance application can result in complete data loss or corruption via a malicious link (CSRF-style attack if authentication is added later).

---

### 2.2 Safety (Dependency CVE) Findings

| # | Package | CVE | Severity | Status |
|---|---------|-----|----------|--------|
| — | — | — | — | ✅ **No vulnerabilities found** |

The Safety scan returned no known CVEs for the packages declared in `backend/requirements.txt`. This should be re-run on every dependency update and as part of any CI/CD pipeline.

---

## 3. OWASP Top 10 Alignment

Assessment based on OWASP Top 10 (2021 edition) applied to the FinanceTracker application.

| OWASP ID | Title | Status | Notes |
|----------|-------|--------|-------|
| **A01:2021** | Broken Access Control | ⚠️ **Mitigated (Partial)** | No authentication or authorization is implemented. Acceptable only for strict localhost use. Any networked deployment is fully exposed. See §1.1. |
| **A02:2021** | Cryptographic Failures | ⚠️ **Mitigated (Partial)** | No HTTPS enforcement at the application layer. Data in transit is unencrypted over HTTP. SQLite data at rest is not encrypted. No passwords or tokens are stored. |
| **A03:2021** | Injection | ⚠️ **Mitigated (Partial)** | Pydantic validation reduces injection surface. However, **B608** finding at `backend/main.py:281` indicates a SQL injection risk that must be remediated. No template rendering; no HTML injection risk from backend. |
| **A04:2021** | Insecure Design | ✅ **Addressed** | Application scope is minimal and well-defined. No sensitive business logic beyond CRUD operations. Pydantic enforces data contracts. |
| **A05:2021** | Security Misconfiguration | ⚠️ **Mitigated (Partial)** | No CORS misconfiguration (defaults to deny). No debug mode flags observed. Docker setup should enforce non-root user in container (verify `Dockerfile`). No unnecessary endpoints exposed. |
| **A06:2021** | Vulnerable and Outdated Components | ✅ **Addressed** | Safety scan returned zero CVEs. Dependency footprint is minimal (3 packages). Regular re-scanning recommended. |
| **A07:2021** | Identification and Authentication Failures | ⚠️ **Not Applicable (Single-User)** | No authentication system exists by design for personal use. Becomes **critical risk** if deployed beyond localhost. |
| **A08:2021** | Software and Data Integrity Failures | ✅ **Addressed** | No deserialization of untrusted data. Pydantic models parse and validate all input. CSV export is generated server-side with no external input to the generation logic. |
| **A09:2021** | Security Logging and Monitoring Failures | ✅ **Addressed** | `logging` is configured in `backend/main.py` with structured format (`%(asctime)s %(levelname)s %(name)s`). Logger `finance_tracker` is instantiated. Ensure errors and critical operations (delete, edit) are logged at appropriate levels. |
| **A10:2021** | Server-Side Request Forgery (SSRF) | ✅ **Not Applicable** | The application makes no outbound HTTP requests. No URL fetch, webhook, or remote resource loading in `backend/main.py`. |

---

## 4. Recommended Hardening Steps

### 🔴 Critical — Remediate Before Any Networked Deployment

- **Fix SQL Injection (B608) in `backend/main.py:281`.**
  Replace string-interpolated SQL with parameterized queries using SQLite's `?` placeholder syntax throughout all dynamic query construction, especially in transaction filtering logic (date range, category filters).

- **Add authentication to all API endpoints.**
  Implement HTTP Basic Auth (minimum) or JWT Bearer token authentication using FastAPI's `Depends` security utilities. Consider `fastapi-users` or a hand-rolled `OAuth2PasswordBearer` flow in `backend/main.py`. Without this, any user on the same network can access all financial data.

### 🟡 High — Implement for Hardened Deployment

- **Enforce HTTPS.**
  Add `HTTPSRedirectMiddleware` from `fastapi.middleware.httpsredirect` in `backend/main.py`, or preferably terminate TLS at an nginx/Caddy reverse proxy layer defined in `docker-compose.yml`.

- **Add rate limiting to the API.**
  Integrate `slowapi` (a FastAPI-compatible rate limiter) in `backend/main.py` to protect endpoints — particularly the CSV export endpoint (`/export`) and transaction listing, which could be abused to exfiltrate data rapidly.

- **Validate and sanitize the `category` field more strictly.**
  Enforce an allowlist of valid category values (e.g., `Food`, `Rent`, `Salary`) using a Pydantic `Enum` type in `backend/main.py` rather than accepting arbitrary strings. This reduces both injection surface and data quality issues.

- **Sanitize CSV export output in `backend/main.py`.**
  Protect against CSV injection (formula injection) by prefixing cell values starting with `=`, `+`, `-`, or `@` with a single quote or space. This prevents malicious formulas from executing when the exported file is opened in Excel or Google Sheets.
  ```python
  # Example guard in CSV generation
  FORMULA_CHARS = ('=', '+', '-', '@', '\t', '\r')
  def sanitize_csv_cell(value: str) -> str:
      if value and value[0] in FORMULA_CHARS:
          return "'" + value
      return value
  ```

### 🟢 Medium — Best Practice Improvements

- **Run the container as a non-root user.**
  Add `USER appuser` to the `Dockerfile` after creating a dedicated system user. Running as root inside a container is a container escape risk escalator.

- **Pin Docker base image to a specific digest** in `Dockerfile` (e.g., `python:3.12-slim@sha256:...`) to prevent supply-chain attacks via mutable tags.

- **Integrate Bandit and Safety into CI/CD.**
  Add `bandit -r backend/` and `safety check -r backend/requirements.txt` as pipeline steps in a `Jenkinsfile` or GitHub Actions workflow. The current Jenkins configuration is not configured (`Jenkins not run`). Fail the build on any HIGH or CRITICAL finding.

- **Add `Content-Security-Policy` and security headers** to HTTP responses.
  Add a middleware in `backend/main.py` or configure the reverse proxy to set:
  - `Content-Security-Policy: default-src 'self'`
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: no-referrer`

- **Scope CORS explicitly** when/if the frontend is decoupled.
  If `frontend/index.html` is ever served from a separate origin, configure `CORSMiddleware` in `backend/main.py` with an explicit `allow_origins` allowlist rather than a wildcard.

- **Implement soft-delete for transactions** rather than hard `DELETE` to maintain an audit trail of financial records. Add a `deleted_at` timestamp column to the SQLite schema.

- **Add a `.gitignore` entry for the SQLite database file** (`*.db`, `*.sqlite3`) to prevent accidental commit of personal financial data to version control.

- **Periodically re-run Safety** against `backend/requirements.txt` as new CVEs are disclosed. Consider automating this with `dependabot` or a scheduled CI job.

---

*This document should be reviewed and updated whenever dependencies are upgraded, new endpoints are added, or the deployment environment changes from localhost to a networked host.*