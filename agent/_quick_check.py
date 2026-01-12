from agent.schemas import PlanV1

p = PlanV1(
    question="Compare renewables share in Australia vs Germany since 2005",
    metric_id="renewables_share_energy",
    countries=["AUS", "deu"],
    year_start=2005,
    year_end=2023,
)
print(p.model_dump())
print(p.metric_spec())
