from __future__ import annotations

import datetime as dt
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

import duckdb
import requests


# ---- Phase 1 constants ----

DATASET_ID = "owid_energy"

# OWID energy data is publicly hosted in the owid/energy-data repo.
# We use the canonical "owid-energy-data.csv" file from the repository.
#
# If OWID changes location/name later, update this constant only.
OWID_ENERGY_CSV_URL = (
    "https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv"
)

DEFAULT_CACHE_DIR = Path("data/owid")
DEFAULT_CACHE_FILE = "owid-energy-data.csv"

DEFAULT_DUCKDB_PATH = Path("data/owid/energy.duckdb")

TABLE_NAME = "energy_raw"

REQUIRED_COLUMNS = {"year", "country", "iso_code"}


@dataclass(frozen=True)
class SourceMetadata:
    dataset_id: str
    url: str
    accessed_at_utc: str
    local_path: str
    sha256: str


def get_dataset_url() -> str:
    return OWID_ENERGY_CSV_URL


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download_dataset(
    cache_dir: Path = DEFAULT_CACHE_DIR,
    filename: str = DEFAULT_CACHE_FILE,
    force: bool = False,
    timeout_sec: int = 60,
) -> Tuple[Path, SourceMetadata]:
    """
    Download the OWID energy CSV to a local cache (data/owid/ by default).

    Returns:
      (csv_path, source_metadata)
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    csv_path = cache_dir / filename

    url = get_dataset_url()

    if csv_path.exists() and not force:
        sha = _sha256_file(csv_path)
        meta = SourceMetadata(
            dataset_id=DATASET_ID,
            url=url,
            accessed_at_utc=dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            local_path=str(csv_path),
            sha256=sha,
        )
        return csv_path, meta

    resp = requests.get(url, timeout=timeout_sec)
    resp.raise_for_status()

    csv_path.write_bytes(resp.content)

    sha = _sha256_file(csv_path)
    meta = SourceMetadata(
        dataset_id=DATASET_ID,
        url=url,
        accessed_at_utc=dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        local_path=str(csv_path),
        sha256=sha,
    )
    return csv_path, meta


def connect_duckdb(db_path: Path = DEFAULT_DUCKDB_PATH) -> duckdb.DuckDBPyConnection:
    """
    Connect to a persistent DuckDB database file under data/owid by default.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(db_path))


def load_energy_raw(
    conn: duckdb.DuckDBPyConnection,
    csv_path: Path,
    table_name: str = TABLE_NAME,
    replace: bool = False,
) -> None:
    """
    Load CSV into DuckDB as a table.

    - replace=False: will only create if table doesn't exist
    - replace=True: will drop+recreate

    Uses read_csv_auto for convenience (Phase 1).
    """
    if replace:
        conn.execute(f"DROP TABLE IF EXISTS {table_name}")

    # If table exists and replace=False, do nothing
    exists = conn.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [table_name],
    ).fetchone()[0]
    if exists and not replace:
        return

    # Create from CSV
    # We set sample_size=-1 to scan whole file for type inference (slower but safer for Phase 1).
    conn.execute(
        f"""
        CREATE TABLE {table_name} AS
        SELECT * FROM read_csv_auto(?, sample_size=-1)
        """,
        [str(csv_path)],
    )


def inspect_schema(
    conn: duckdb.DuckDBPyConnection,
    table_name: str = TABLE_NAME,
) -> Dict[str, str]:
    """
    Return {column_name: duckdb_type}.
    """
    rows = conn.execute(
        f"PRAGMA table_info('{table_name}')"
    ).fetchall()
    # pragma returns: (cid, name, type, notnull, dflt_value, pk)
    return {r[1]: r[2] for r in rows}


def validate_required_columns(
    conn: duckdb.DuckDBPyConnection,
    table_name: str = TABLE_NAME,
    required: Optional[set[str]] = None,
) -> None:
    required = required or set(REQUIRED_COLUMNS)
    schema = inspect_schema(conn, table_name)
    missing = sorted([c for c in required if c not in schema])
    if missing:
        raise RuntimeError(
            f"Missing required columns in {table_name}: {missing}. "
            f"Found columns: {sorted(schema.keys())[:30]}..."
        )


def get_year_bounds(
    conn: duckdb.DuckDBPyConnection,
    table_name: str = TABLE_NAME,
) -> Tuple[Optional[int], Optional[int]]:
    """
    Return (min_year, max_year) from the dataset.
    """
    row = conn.execute(
        f"SELECT MIN(year) AS min_year, MAX(year) AS max_year FROM {table_name}"
    ).fetchone()
    if not row:
        return None, None
    return row[0], row[1]


def ensure_loaded(
    force_download: bool = False,
    replace_table: bool = False,
    db_path: Path = DEFAULT_DUCKDB_PATH,
    cache_dir: Path = DEFAULT_CACHE_DIR,
) -> Tuple[duckdb.DuckDBPyConnection, SourceMetadata]:
    """
    One-call convenience:
    - download (or reuse cached) CSV
    - connect DuckDB
    - load into energy_raw (create if missing)
    - validate required columns

    Returns:
      (conn, source_metadata)
    """
    csv_path, meta = download_dataset(cache_dir=cache_dir, force=force_download)

    conn = connect_duckdb(db_path=db_path)
    load_energy_raw(conn, csv_path, replace=replace_table)
    validate_required_columns(conn)

    return conn, meta
