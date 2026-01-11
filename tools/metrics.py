from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


DATASET_OWID_ENERGY = "owid_energy"


@dataclass(frozen=True)
class MetricSpec:
    """
    A curated metric exposed to the agent.

    - metric_id: stable internal identifier used by the planner
    - column: the column name in energy_raw (as loaded from OWID CSV)
    - unit: human-readable unit for narratives/UI
    - description: human-readable description for narratives/UI
    - category: grouping for presentation/organization (optional)
    """

    metric_id: str
    column: str
    unit: str
    description: str
    category: str


class MetricRegistry:
    """
    Phase 1: A small curated set of metrics. This is intentionally NOT a general OWID catalog.

    Design goal:
    - The LLM selects *metric_id* only (stable).
    - We can later remap metric_id -> column if OWID column names change.
    """

    def __init__(self) -> None:
        self._datasets: Dict[str, Dict[str, MetricSpec]] = {
            DATASET_OWID_ENERGY: {
                # --- Energy consumption ---
                "energy_per_capita": MetricSpec(
                    metric_id="energy_per_capita",
                    column="energy_per_capita",
                    unit="kWh per person per year",
                    description="Primary energy consumption per person.",
                    category="consumption",
                ),
                "primary_energy_consumption": MetricSpec(
                    metric_id="primary_energy_consumption",
                    column="primary_energy_consumption",
                    unit="TWh per year",
                    description="Total primary energy consumption.",
                    category="consumption",
                ),
                # --- Energy mix (shares of primary energy) ---
                "renewables_share_energy": MetricSpec(
                    metric_id="renewables_share_energy",
                    column="renewables_share_energy",
                    unit="percent of primary energy",
                    description="Share of primary energy from renewables.",
                    category="energy_mix",
                ),
                "fossil_share_energy": MetricSpec(
                    metric_id="fossil_share_energy",
                    column="fossil_share_energy",
                    unit="percent of primary energy",
                    description="Share of primary energy from fossil fuels.",
                    category="energy_mix",
                ),
                "coal_share_energy": MetricSpec(
                    metric_id="coal_share_energy",
                    column="coal_share_energy",
                    unit="percent of primary energy",
                    description="Share of primary energy from coal.",
                    category="energy_mix",
                ),
                "oil_share_energy": MetricSpec(
                    metric_id="oil_share_energy",
                    column="oil_share_energy",
                    unit="percent of primary energy",
                    description="Share of primary energy from oil.",
                    category="energy_mix",
                ),
                "gas_share_energy": MetricSpec(
                    metric_id="gas_share_energy",
                    column="gas_share_energy",
                    unit="percent of primary energy",
                    description="Share of primary energy from gas.",
                    category="energy_mix",
                ),
                "nuclear_share_energy": MetricSpec(
                    metric_id="nuclear_share_energy",
                    column="nuclear_share_energy",
                    unit="percent of primary energy",
                    description="Share of primary energy from nuclear.",
                    category="energy_mix",
                ),
                # --- Electricity mix (shares of electricity generation) ---
                # Note: These columns must exist in your loaded CSV for queries to work.
                # If your OWID energy CSV uses different names, just update 'column' here.
                "solar_share_elec": MetricSpec(
                    metric_id="solar_share_elec",
                    column="solar_share_elec",
                    unit="percent of electricity generation",
                    description="Share of electricity generation from solar.",
                    category="electricity_mix",
                ),
                "wind_share_elec": MetricSpec(
                    metric_id="wind_share_elec",
                    column="wind_share_elec",
                    unit="percent of electricity generation",
                    description="Share of electricity generation from wind.",
                    category="electricity_mix",
                ),
                "hydro_share_elec": MetricSpec(
                    metric_id="hydro_share_elec",
                    column="hydro_share_elec",
                    unit="percent of electricity generation",
                    description="Share of electricity generation from hydro.",
                    category="electricity_mix",
                ),
            }
        }

    def dataset_ids(self) -> List[str]:
        return sorted(self._datasets.keys())

    def metric_ids(self, dataset_id: str) -> List[str]:
        self._assert_dataset(dataset_id)
        return sorted(self._datasets[dataset_id].keys())

    def get(self, dataset_id: str, metric_id: str) -> MetricSpec:
        self._assert_dataset(dataset_id)
        ds = self._datasets[dataset_id]
        if metric_id not in ds:
            raise KeyError(
                f"Unknown metric_id='{metric_id}' for dataset_id='{dataset_id}'. "
                f"Supported: {sorted(ds.keys())}"
            )
        return ds[metric_id]

    def maybe_get(self, dataset_id: str, metric_id: str) -> Optional[MetricSpec]:
        try:
            return self.get(dataset_id, metric_id)
        except KeyError:
            return None

    def _assert_dataset(self, dataset_id: str) -> None:
        if dataset_id not in self._datasets:
            raise KeyError(
                f"Unknown dataset_id='{dataset_id}'. Supported: {sorted(self._datasets.keys())}"
            )


# A global default registry instance (simple + good enough for Phase 1).
DEFAULT_METRIC_REGISTRY = MetricRegistry()
