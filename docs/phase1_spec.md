## Phase 1 Deliverable

**A single-run “Data Journalist” agent** that takes a user question about energy trends and produces:

1. a **validated plan** (structured JSON)
2. **SQL** executed against a local DuckDB copy of OWID energy data
3. **1–2 charts** rendered in Streamlit
4. a **short narrative** with explicit data source + date range
5. an output bundle containing: plan, SQL, results summary, and metadata for reproducibility

**Non-goals (Phase 1):**

* dataset discovery across OWID
* joining datasets
* multi-turn chat memory
* automatic “self-improvement” loops
* scheduled refresh jobs / deployment

---

## User Experience

### Streamlit UI (single screen)

* Input: “What do you want to investigate?” (text box)
* Button: **Run analysis**
* Outputs (in order):

  * **Plan** (expandable)
  * **Charts** (1–2)
  * **Narrative** (headline + bullets + short paragraph)
  * **SQL** (expandable)
  * **Sources** (OWID dataset URL + accessed_at)
  * **Run artifacts** (link/path to saved JSON bundle)

### CLI (optional but nice)

```bash
python -m agent.run --question "Compare solar electricity share in Australia vs Germany since 2005"
```

---

## Hard Constraints (these keep Phase 1 tight)

### Data

* Single dataset: **OWID energy CSV** (cached locally)
* Single table: `energy_raw`
* Canonical keys: `iso_code`, `country`, `year`

### Analysis scope

* Up to **3 countries** per run
* Year range bounded (default: 1990–latest)
* One metric per run (choose from curated registry)
* Two views max:

  * Time-series line chart (required)
  * Optional summary bar chart (latest year or growth)

### Safety

* SQL is executed only against DuckDB
* SQL must be **SELECT-only** (no DDL/DML)
* All tool calls are executed by Python, not the model

---

## Architecture (Phase 1)

### Modules

1. `tools/owid_energy.py`

* `get_dataset_url()`
* `download_dataset(force=False) -> Path`
* `ensure_duckdb_loaded() -> conn`
* `inspect_schema() -> {col: type}`

2. `agent/planner.py`

* `plan(question) -> PlanV1` (pydantic validated)
* Only returns metric_id from registry, countries, year range, and chart specs

3. `agent/sql_generator.py`

* `generate_sql(plan, schema) -> SQLBundleV1`
* Produces:

  * `timeseries_sql` (required)
  * `summary_sql` (optional)

4. `agent/executor.py`

* Runs:

  * dataset load
  * SQL execution
  * basic validations (non-empty, expected columns)
  * produces `RunResultV1`

5. `agent/reporter.py`

* Generates narrative from:

  * plan
  * computed summary stats (min/max/latest/CAGR-ish)
  * source metadata

6. `ui/app.py`

* Orchestrates plan → SQL → execute → charts → narrative
* Shows artifacts + debugging panels

---

## Data Contract (Phase 1)

### Required columns in `energy_raw`

* `year` (INT)
* `country` (STRING)
* `iso_code` (STRING)

### Metric registry (curated)

Plan must reference a **metric_id** that maps to a column name.

Example minimal set to start (you can adjust names to match actual CSV columns in your version):

**Energy consumption**

* `energy_per_capita`
* `primary_energy_consumption`

**Energy mix**

* `renewables_share_energy`
* `fossil_share_energy`
* `coal_share_energy`
* `gas_share_energy`
* `oil_share_energy`
* `nuclear_share_energy`

**Electricity mix (if present in CSV)**

* `solar_share_elec`
* `wind_share_elec`
* `hydro_share_elec`

Each metric includes:

* column name
* unit
* description
* preferred chart type (“line”)

---

## Plan Schema (Phase 1)

### `PlanV1` (pydantic)

```json
{
  "plan_version": "1",
  "dataset_id": "owid_energy",
  "question": "...",
  "metric_id": "renewables_share_energy",
  "countries": ["AUS", "DEU"],
  "year_start": 2005,
  "year_end": 2023,
  "views": [
    {"view_id": "timeseries", "type": "line"},
    {"view_id": "summary", "type": "bar", "mode": "latest_year"}
  ]
}
```

Rules:

* `countries`: ISO-3 codes only (UI can accept names, but plan stores ISO)
* `views[0]` must be `timeseries` line chart
* max 2 views

---

## SQL Contract (Phase 1)

### Time-series SQL (required)

Must return:

* `year`
* `iso_code`
* `country`
* `value`

Example shape:

```sql
SELECT
  year,
  iso_code,
  country,
  <metric_column> AS value
FROM energy_raw
WHERE iso_code IN ('AUS','DEU')
  AND year BETWEEN 2005 AND 2023
  AND <metric_column> IS NOT NULL
ORDER BY year, iso_code;
```

### Summary SQL (optional)

Either:

* latest year per country, or
* growth between start/end (simple delta)

---

## Validation Rules (Phase 1)

These are what separate “toy” from “system”:

### Plan validation

* metric_id exists in registry
* countries <= 3
* year_start <= year_end
* year_end not in the future
* dataset_id == `owid_energy`

### SQL validation

* must begin with `SELECT`
* must not contain `;` (optional)
* must not contain keywords: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `CREATE`, `ALTER`, `COPY`

### Result validation

* time-series query returns >= 2 rows
* required columns exist
* at least 1 country has data coverage over multiple years
* otherwise: return a graceful “insufficient data” narrative

---

## Outputs & Reproducibility

Each run writes a bundle to:

`runs/<timestamp>__<slug>.json`

Includes:

* `question`
* `plan`
* `sql_bundle`
* `summary_stats`
* `source_metadata` (dataset URL + accessed_at + local file hash)
* `chart_specs` (minimal)
* `narrative`

This is your “journalistic artifact” and doubles as evidence in interviews.

---

## Evaluation (Phase 1)

Golden set: `eval/golden_set.jsonl` with 5–10 questions.

Scoring:

* plan validity rate
* SQL execution success rate
* non-empty results rate
* narrative includes:

  * countries
  * metric description
  * time range
  * data source
