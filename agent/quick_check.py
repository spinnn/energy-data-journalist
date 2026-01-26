from agent.schemas import PlanV1

def main():
    plan = PlanV1(
        question="Compare renewables share in Australia vs Germany since 2005",
        metric_id="renewables_share_energy",
        countries=["AUS", "deu"],
        year_start=2005,
        year_end=2023,
    )

    print("Plan created successfully:\n")
    print(plan.model_dump())

    print("\nResolved metric spec:\n")
    metric = plan.metric_spec()
    print(metric)

if __name__ == "__main__":
    main()
