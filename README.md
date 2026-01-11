# Energy Data Journalist (Phase 1)

This project explores a tightly scoped **data journalism–style analytics agent**.

Given a natural-language question about energy trends, the system:

- plans a structured analysis
- generates and safely executes SQL over public data
- produces charts and a short narrative
- records reproducible run artifacts

Phase 1 is deliberately constrained to:
- a single public dataset (Our World in Data – Energy)
- one analysis per run
- no dataset joins or autonomous actions

The goal is not to build a general-purpose agent, but to demonstrate
**applied AI system design**: bounded tool use, validation, observability,
and explainability.

## Project status

🚧 **Phase 1 – Design & implementation in progress**

See:
- `docs/phase1_spec.md` for the Phase 1 design
- `agent/` for planning and orchestration logic
- `tools/` for data access and execution
- `ui/` for the Streamlit interface
- `eval/` for evaluation scaffolding

## Data source

All analyses in Phase 1 use publicly available data from:

- **Our World in Data – Energy dataset**
  https://github.com/owid/energy-data

Data is downloaded and cached locally at runtime and is not committed to the repository.

## AI assistance disclosure

This project is developed with the assistance of large language models
for code generation and iteration. All system design decisions,
constraints, and evaluation logic are defined and validated by the author.
