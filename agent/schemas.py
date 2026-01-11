from __future__ import annotations

import datetime as dt
import re
from typing import Literal, Optional, Sequence

from pydantic import BaseModel, Field, field_validator, model_validator

from tools.metrics import DATASET_OWID_ENERGY, DEFAULT_METRIC_REGISTRY


ISO3_RE = re.compile(r"^[A-Z]{3}$")


class ViewLine(BaseModel):
    """
    Phase 1: Required view.
    """
    view_id: Literal["timeseries"] = "timeseries"
    type: Literal["line"] = "line"


class ViewBar(BaseModel):
    """
    Phase 1: Optional second view.
    """
    view_id: Literal["summary"] = "summary"
    type: Literal["bar"] = "bar"
    mode: Literal["latest_year", "delta"] = "latest_year"


ViewSpec = ViewLine | ViewBar


class PlanV1(BaseModel):
    """
    A tightly-scoped plan produced by the planner LLM (or by the UI in early dev).

    Contract:
    - one dataset (Phase 1) -> owid_energy
    - one metric (from curated registry)
    - <= 3 countries (ISO3)
    - year range is validated
    - first view is always the timeseries line chart
    - optional second view is a summary bar chart
    """
    plan_version: Literal["1"] = "1"

    dataset_id: Literal["owid_energy"] = DATASET_OWID_ENERGY
    question: str = Field(..., min_length=5, max_length=500)

    metric_id: str = Field(..., min_length=3, max_length=80)

    # Store ISO3 codes in the plan (UI can accept names, but plan is canonical).
    countries: list[str] = Field(..., min_length=1, max_length=3)

    year_start: int = Field(..., ge=1800, le=2500)
    year_end: int = Field(..., ge=1800, le=2500)

    views: list[ViewSpec] = Field(default_factory=lambda: [ViewLine()])

    # Optional free-form notes for traceability/debugging (not used by agent logic)
    notes: Optional[str] = Field(default=None, max_length=500)

    @field_validator("metric_id")
    @classmethod
    def validate_metric_id(cls, v: str) -> str:
        # fail fast if the metric isn't supported
        _ = DEFAULT_METRIC_REGISTRY.get(DATASET_OWID_ENERGY, v)
        return v

    @field_validator("countries")
    @classmethod
    def validate_countries(cls, countries: Sequence[str]) -> list[str]:
        if not countries:
            raise ValueError("countries must contain at least one ISO3 code")

        cleaned: list[str] = []
        for c in countries:
            if not isinstance(c, str):
                raise ValueError("countries must be a list of strings (ISO3 codes)")
            cc = c.strip().upper()
            if not ISO3_RE.match(cc):
                raise ValueError(
                    f"Invalid country code '{c}'. Phase 1 requires ISO3 codes like 'AUS', 'DEU'."
                )
            cleaned.append(cc)

        # enforce uniqueness while preserving order
        seen = set()
        uniq = []
        for c in cleaned:
            if c not in seen:
                uniq.append(c)
                seen.add(c)

        if len(uniq) > 3:
            raise ValueError("Phase 1 supports up to 3 countries")
        return uniq

    @model_validator(mode="after")
    def validate_years_and_views(self) -> "PlanV1":
        current_year = dt.datetime.now().year

        if self.year_start > self.year_end:
            raise ValueError("year_start must be <= year_end")

        # "Future" years are almost always wrong for OWID annual datasets.
        # Allow a small buffer (e.g. early-year publication quirks) if you want, but keep it strict for Phase 1.
        if self.year_end > current_year:
            raise ValueError(
                f"year_end ({self.year_end}) is in the future relative to current year ({current_year})"
            )

        # Views: must start with the required timeseries line view.
        if not self.views:
            raise ValueError("views must contain at least the timeseries line view")

        first = self.views[0]
        if not isinstance(first, ViewLine):
            raise ValueError("views[0] must be the timeseries line view")

        if len(self.views) > 2:
            raise ValueError("Phase 1 supports at most 2 views (timeseries + optional summary)")

        # If there is a second view, it must be the summary bar view.
        if len(self.views) == 2 and not isinstance(self.views[1], ViewBar):
            raise ValueError("views[1], if provided, must be the summary bar view")

        return self

    def metric_spec(self):
        """
        Convenience: resolve metric_id -> MetricSpec from registry.
        """
        return DEFAULT_METRIC_REGISTRY.get(self.dataset_id, self.metric_id)
