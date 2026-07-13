# Budget Recommendation Evaluation

Generated 2026-07-11T19:10:56.939130+00:00.

Running against the **real Claude API** — latency and estimated cost reflect actual calls.

## Rubric

- **category_grounding**: 1.0 = every allocated category was actually in the input (no invented categories)
- **within_budget**: allocations don't exceed the computed spendable amount
- **non_negotiables_covered**: fraction of required categories actually funded
- **reasoning_cites_real_numbers**: does the prose explanation's numbers match the real buffer/spendable figures, or could it have said anything plausible-sounding?
- **agreement_correlation**: Spearman correlation between historical category spend and allocated amount (do bigger historical categories get bigger budgets?)
- **consistency**: same input run 3x — fraction of runs producing the same allocations

## Summary (mean across all scenarios)

|   category_grounding |   within_budget |   non_negotiables_covered |   reasoning_cites_real_numbers |   agreement_correlation |   consistency |   latency_seconds |   est_cost_usd |
|---------------------:|----------------:|--------------------------:|-------------------------------:|------------------------:|--------------:|------------------:|---------------:|
|                0.852 |               1 |                         1 |                              1 |                       1 |         0.571 |             5.503 |          0.004 |

## Per-scenario detail

|   scenario_idx |   category_grounding | within_budget   |   non_negotiables_covered |   reasoning_cites_real_numbers |   agreement_correlation |   consistency |   latency_seconds |   est_cost_usd |
|---------------:|---------------------:|:----------------|--------------------------:|-------------------------------:|------------------------:|--------------:|------------------:|---------------:|
|              0 |                1     | True            |                         1 |                              1 |                       1 |         1     |             5.371 |          0.005 |
|              1 |                0.833 | True            |                         1 |                              1 |                       1 |         0.667 |             5.35  |          0.005 |
|              2 |                1     | True            |                         1 |                              1 |                       1 |         0.333 |             5.896 |          0.005 |
|              3 |                0.8   | True            |                         1 |                              1 |                       1 |         0.667 |             4.411 |          0.004 |
|              4 |                1     | True            |                         1 |                              1 |                       1 |         0.333 |             5.222 |          0.005 |
|              5 |                1     | True            |                         1 |                              1 |                     nan |         0.333 |             6.184 |          0.004 |
|              6 |                0.333 | True            |                         1 |                              1 |                       1 |         0.667 |             6.085 |          0.004 |