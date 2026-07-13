# Anomaly Detection Benchmark

Generated 2026-07-11T18:02:01.737826+00:00 on synthetic labeled transactions (labels: normal / unusual / fraud, unknown to every detector under test). 'unusual' and 'fraud' are both scored as the positive (anomalous) class for precision/recall/F1, since that's what production currently outputs — a single flag with no severity split. `pct_fraud_caught` shows recall computed on the fraud subset alone.

## Summary (mean across 5 seeds, all profiles)

| profile            | model                |   precision |   recall |    f1 |   false_alert_rate |   pct_fraud_caught |   n_runs |
|:-------------------|:---------------------|------------:|---------:|------:|-------------------:|-------------------:|---------:|
| biweekly_burster   | robust_zscore        |       1     |    0.693 | 0.816 |              0     |                  1 |        5 |
| biweekly_burster   | rule_based           |       0.646 |    0.941 | 0.764 |              0.019 |                  1 |        5 |
| biweekly_burster   | isolation_forest     |       0.441 |    1     | 0.611 |              0.047 |                  1 |        5 |
| biweekly_burster   | local_outlier_factor |       0.441 |    1     | 0.611 |              0.047 |                  1 |        5 |
| gig_variable       | robust_zscore        |       1     |    0.676 | 0.805 |              0     |                  1 |        5 |
| gig_variable       | rule_based           |       0.646 |    0.941 | 0.764 |              0.019 |                  1 |        5 |
| gig_variable       | isolation_forest     |       0.441 |    1     | 0.611 |              0.047 |                  1 |        5 |
| gig_variable       | local_outlier_factor |       0.441 |    1     | 0.611 |              0.047 |                  1 |        5 |
| high_earner_lumpy  | robust_zscore        |       1     |    0.709 | 0.827 |              0     |                  1 |        5 |
| high_earner_lumpy  | rule_based           |       0.646 |    0.941 | 0.764 |              0.019 |                  1 |        5 |
| high_earner_lumpy  | isolation_forest     |       0.441 |    1     | 0.611 |              0.047 |                  1 |        5 |
| high_earner_lumpy  | local_outlier_factor |       0.441 |    1     | 0.611 |              0.047 |                  1 |        5 |
| steady_earner      | robust_zscore        |       1     |    0.724 | 0.838 |              0     |                  1 |        5 |
| steady_earner      | rule_based           |       0.642 |    0.926 | 0.756 |              0.019 |                  1 |        5 |
| steady_earner      | isolation_forest     |       0.441 |    1     | 0.611 |              0.047 |                  1 |        5 |
| steady_earner      | local_outlier_factor |       0.441 |    1     | 0.611 |              0.047 |                  1 |        5 |
| student_low_volume | robust_zscore        |       1     |    0.711 | 0.827 |              0     |                  1 |        5 |
| student_low_volume | rule_based           |       0.642 |    0.926 | 0.756 |              0.019 |                  1 |        5 |
| student_low_volume | isolation_forest     |       0.441 |    1     | 0.611 |              0.047 |                  1 |        5 |
| student_low_volume | local_outlier_factor |       0.441 |    1     | 0.611 |              0.047 |                  1 |        5 |

## Winner by household profile (highest F1)

- **biweekly_burster**: robust_zscore (F1 0.82, false-alert rate 0.000)
- **gig_variable**: robust_zscore (F1 0.80, false-alert rate 0.000)
- **high_earner_lumpy**: robust_zscore (F1 0.83, false-alert rate 0.000)
- **steady_earner**: robust_zscore (F1 0.84, false-alert rate 0.000)
- **student_low_volume**: robust_zscore (F1 0.83, false-alert rate 0.000)

## Known gap this benchmark surfaces

No detector here — including production's Isolation Forest — has features that distinguish 'unusual' from 'fraud' specifically (merchant familiarity, geographic distance from typical spend, account-age-at-merchant). `pct_fraud_caught` in the detail table shows fraud is being caught largely as a side effect of being a big, unfamiliar-merchant outlier, not because any model is reasoning about fraud specifically. Next step if pursued: add merchant-familiarity and geo features and score fraud recall as its own metric, not a subset of general anomaly recall.

## Per-run detail

| model                | profile            |   seed |   precision |   recall |    f1 |   false_alert_rate |   n_flagged |   n_actual_anomalous |   pct_flagged_that_were_fraud |   pct_fraud_caught |
|:---------------------|:-------------------|-------:|------------:|---------:|------:|-------------------:|------------:|---------------------:|------------------------------:|-------------------:|
| isolation_forest     | steady_earner      |      1 |       0.517 |    1     | 0.682 |              0.041 |          29 |                   15 |                         0.034 |                  1 |
| robust_zscore        | steady_earner      |      1 |       1     |    0.667 | 0.8   |              0     |          10 |                   15 |                         0.1   |                  1 |
| local_outlier_factor | steady_earner      |      1 |       0.517 |    1     | 0.682 |              0.041 |          29 |                   15 |                         0.034 |                  1 |
| rule_based           | steady_earner      |      1 |       0.722 |    0.867 | 0.788 |              0.015 |          18 |                   15 |                         0.056 |                  1 |
| isolation_forest     | steady_earner      |      2 |       0.414 |    1     | 0.585 |              0.049 |          29 |                   12 |                         0.138 |                  1 |
| robust_zscore        | steady_earner      |      2 |       1     |    0.75  | 0.857 |              0     |           9 |                   12 |                         0.444 |                  1 |
| local_outlier_factor | steady_earner      |      2 |       0.414 |    1     | 0.585 |              0.049 |          29 |                   12 |                         0.138 |                  1 |
| rule_based           | steady_earner      |      2 |       0.611 |    0.917 | 0.733 |              0.02  |          18 |                   12 |                         0.222 |                  1 |
| isolation_forest     | steady_earner      |      3 |       0.448 |    1     | 0.619 |              0.047 |          29 |                   13 |                         0.103 |                  1 |
| robust_zscore        | steady_earner      |      3 |       1     |    0.615 | 0.762 |              0     |           8 |                   13 |                         0.375 |                  1 |
| local_outlier_factor | steady_earner      |      3 |       0.448 |    1     | 0.619 |              0.047 |          29 |                   13 |                         0.103 |                  1 |
| rule_based           | steady_earner      |      3 |       0.579 |    0.846 | 0.688 |              0.023 |          19 |                   13 |                         0.158 |                  1 |
| isolation_forest     | steady_earner      |      4 |       0.379 |    1     | 0.55  |              0.051 |          29 |                   11 |                         0.103 |                  1 |
| robust_zscore        | steady_earner      |      4 |       1     |    0.818 | 0.9   |              0     |           9 |                   11 |                         0.333 |                  1 |
| local_outlier_factor | steady_earner      |      4 |       0.379 |    1     | 0.55  |              0.051 |          29 |                   11 |                         0.103 |                  1 |
| rule_based           | steady_earner      |      4 |       0.611 |    1     | 0.759 |              0.02  |          18 |                   11 |                         0.167 |                  1 |
| isolation_forest     | steady_earner      |      5 |       0.448 |    1     | 0.619 |              0.047 |          29 |                   13 |                         0.034 |                  1 |
| robust_zscore        | steady_earner      |      5 |       1     |    0.769 | 0.87  |              0     |          10 |                   13 |                         0.1   |                  1 |
| local_outlier_factor | steady_earner      |      5 |       0.448 |    1     | 0.619 |              0.047 |          29 |                   13 |                         0.034 |                  1 |
| rule_based           | steady_earner      |      5 |       0.684 |    1     | 0.813 |              0.018 |          19 |                   13 |                         0.053 |                  1 |
| isolation_forest     | biweekly_burster   |      1 |       0.517 |    1     | 0.682 |              0.041 |          29 |                   15 |                         0.034 |                  1 |
| robust_zscore        | biweekly_burster   |      1 |       1     |    0.667 | 0.8   |              0     |          10 |                   15 |                         0.1   |                  1 |
| local_outlier_factor | biweekly_burster   |      1 |       0.517 |    1     | 0.682 |              0.041 |          29 |                   15 |                         0.034 |                  1 |
| rule_based           | biweekly_burster   |      1 |       0.722 |    0.867 | 0.788 |              0.015 |          18 |                   15 |                         0.056 |                  1 |
| isolation_forest     | biweekly_burster   |      2 |       0.414 |    1     | 0.585 |              0.049 |          29 |                   12 |                         0.138 |                  1 |
| robust_zscore        | biweekly_burster   |      2 |       1     |    0.75  | 0.857 |              0     |           9 |                   12 |                         0.444 |                  1 |
| local_outlier_factor | biweekly_burster   |      2 |       0.414 |    1     | 0.585 |              0.049 |          29 |                   12 |                         0.138 |                  1 |
| rule_based           | biweekly_burster   |      2 |       0.611 |    0.917 | 0.733 |              0.02  |          18 |                   12 |                         0.222 |                  1 |
| isolation_forest     | biweekly_burster   |      3 |       0.448 |    1     | 0.619 |              0.047 |          29 |                   13 |                         0.103 |                  1 |
| robust_zscore        | biweekly_burster   |      3 |       1     |    0.615 | 0.762 |              0     |           8 |                   13 |                         0.375 |                  1 |
| local_outlier_factor | biweekly_burster   |      3 |       0.448 |    1     | 0.619 |              0.047 |          29 |                   13 |                         0.103 |                  1 |
| rule_based           | biweekly_burster   |      3 |       0.6   |    0.923 | 0.727 |              0.023 |          20 |                   13 |                         0.15  |                  1 |
| isolation_forest     | biweekly_burster   |      4 |       0.379 |    1     | 0.55  |              0.051 |          29 |                   11 |                         0.103 |                  1 |
| robust_zscore        | biweekly_burster   |      4 |       1     |    0.818 | 0.9   |              0     |           9 |                   11 |                         0.333 |                  1 |
| local_outlier_factor | biweekly_burster   |      4 |       0.379 |    1     | 0.55  |              0.051 |          29 |                   11 |                         0.103 |                  1 |
| rule_based           | biweekly_burster   |      4 |       0.611 |    1     | 0.759 |              0.02  |          18 |                   11 |                         0.167 |                  1 |
| isolation_forest     | biweekly_burster   |      5 |       0.448 |    1     | 0.619 |              0.047 |          29 |                   13 |                         0.034 |                  1 |
| robust_zscore        | biweekly_burster   |      5 |       1     |    0.615 | 0.762 |              0     |           8 |                   13 |                         0.125 |                  1 |
| local_outlier_factor | biweekly_burster   |      5 |       0.448 |    1     | 0.619 |              0.047 |          29 |                   13 |                         0.034 |                  1 |
| rule_based           | biweekly_burster   |      5 |       0.684 |    1     | 0.813 |              0.018 |          19 |                   13 |                         0.053 |                  1 |
| isolation_forest     | gig_variable       |      1 |       0.517 |    1     | 0.682 |              0.041 |          29 |                   15 |                         0.034 |                  1 |
| robust_zscore        | gig_variable       |      1 |       1     |    0.667 | 0.8   |              0     |          10 |                   15 |                         0.1   |                  1 |
| local_outlier_factor | gig_variable       |      1 |       0.517 |    1     | 0.682 |              0.041 |          29 |                   15 |                         0.034 |                  1 |
| rule_based           | gig_variable       |      1 |       0.722 |    0.867 | 0.788 |              0.015 |          18 |                   15 |                         0.056 |                  1 |
| isolation_forest     | gig_variable       |      2 |       0.414 |    1     | 0.585 |              0.049 |          29 |                   12 |                         0.138 |                  1 |
| robust_zscore        | gig_variable       |      2 |       1     |    0.667 | 0.8   |              0     |           8 |                   12 |                         0.5   |                  1 |
| local_outlier_factor | gig_variable       |      2 |       0.414 |    1     | 0.585 |              0.049 |          29 |                   12 |                         0.138 |                  1 |
| rule_based           | gig_variable       |      2 |       0.611 |    0.917 | 0.733 |              0.02  |          18 |                   12 |                         0.222 |                  1 |
| isolation_forest     | gig_variable       |      3 |       0.448 |    1     | 0.619 |              0.047 |          29 |                   13 |                         0.103 |                  1 |
| robust_zscore        | gig_variable       |      3 |       1     |    0.615 | 0.762 |              0     |           8 |                   13 |                         0.375 |                  1 |
| local_outlier_factor | gig_variable       |      3 |       0.448 |    1     | 0.619 |              0.047 |          29 |                   13 |                         0.103 |                  1 |
| rule_based           | gig_variable       |      3 |       0.6   |    0.923 | 0.727 |              0.023 |          20 |                   13 |                         0.15  |                  1 |
| isolation_forest     | gig_variable       |      4 |       0.379 |    1     | 0.55  |              0.051 |          29 |                   11 |                         0.103 |                  1 |
| robust_zscore        | gig_variable       |      4 |       1     |    0.818 | 0.9   |              0     |           9 |                   11 |                         0.333 |                  1 |
| local_outlier_factor | gig_variable       |      4 |       0.379 |    1     | 0.55  |              0.051 |          29 |                   11 |                         0.103 |                  1 |
| rule_based           | gig_variable       |      4 |       0.611 |    1     | 0.759 |              0.02  |          18 |                   11 |                         0.167 |                  1 |
| isolation_forest     | gig_variable       |      5 |       0.448 |    1     | 0.619 |              0.047 |          29 |                   13 |                         0.034 |                  1 |
| robust_zscore        | gig_variable       |      5 |       1     |    0.615 | 0.762 |              0     |           8 |                   13 |                         0.125 |                  1 |
| local_outlier_factor | gig_variable       |      5 |       0.448 |    1     | 0.619 |              0.047 |          29 |                   13 |                         0.034 |                  1 |
| rule_based           | gig_variable       |      5 |       0.684 |    1     | 0.813 |              0.018 |          19 |                   13 |                         0.053 |                  1 |
| isolation_forest     | student_low_volume |      1 |       0.517 |    1     | 0.682 |              0.041 |          29 |                   15 |                         0.034 |                  1 |
| robust_zscore        | student_low_volume |      1 |       1     |    0.667 | 0.8   |              0     |          10 |                   15 |                         0.1   |                  1 |
| local_outlier_factor | student_low_volume |      1 |       0.517 |    1     | 0.682 |              0.041 |          29 |                   15 |                         0.034 |                  1 |
| rule_based           | student_low_volume |      1 |       0.722 |    0.867 | 0.788 |              0.015 |          18 |                   15 |                         0.056 |                  1 |
| isolation_forest     | student_low_volume |      2 |       0.414 |    1     | 0.585 |              0.049 |          29 |                   12 |                         0.138 |                  1 |
| robust_zscore        | student_low_volume |      2 |       1     |    0.75  | 0.857 |              0     |           9 |                   12 |                         0.444 |                  1 |
| local_outlier_factor | student_low_volume |      2 |       0.414 |    1     | 0.585 |              0.049 |          29 |                   12 |                         0.138 |                  1 |
| rule_based           | student_low_volume |      2 |       0.611 |    0.917 | 0.733 |              0.02  |          18 |                   12 |                         0.222 |                  1 |
| isolation_forest     | student_low_volume |      3 |       0.448 |    1     | 0.619 |              0.047 |          29 |                   13 |                         0.103 |                  1 |
| robust_zscore        | student_low_volume |      3 |       1     |    0.615 | 0.762 |              0     |           8 |                   13 |                         0.375 |                  1 |
| local_outlier_factor | student_low_volume |      3 |       0.448 |    1     | 0.619 |              0.047 |          29 |                   13 |                         0.103 |                  1 |
| rule_based           | student_low_volume |      3 |       0.579 |    0.846 | 0.688 |              0.023 |          19 |                   13 |                         0.158 |                  1 |
| isolation_forest     | student_low_volume |      4 |       0.379 |    1     | 0.55  |              0.051 |          29 |                   11 |                         0.103 |                  1 |
| robust_zscore        | student_low_volume |      4 |       1     |    0.909 | 0.952 |              0     |          10 |                   11 |                         0.3   |                  1 |
| local_outlier_factor | student_low_volume |      4 |       0.379 |    1     | 0.55  |              0.051 |          29 |                   11 |                         0.103 |                  1 |
| rule_based           | student_low_volume |      4 |       0.611 |    1     | 0.759 |              0.02  |          18 |                   11 |                         0.167 |                  1 |
| isolation_forest     | student_low_volume |      5 |       0.448 |    1     | 0.619 |              0.047 |          29 |                   13 |                         0.034 |                  1 |
| robust_zscore        | student_low_volume |      5 |       1     |    0.615 | 0.762 |              0     |           8 |                   13 |                         0.125 |                  1 |
| local_outlier_factor | student_low_volume |      5 |       0.448 |    1     | 0.619 |              0.047 |          29 |                   13 |                         0.034 |                  1 |
| rule_based           | student_low_volume |      5 |       0.684 |    1     | 0.813 |              0.018 |          19 |                   13 |                         0.053 |                  1 |
| isolation_forest     | high_earner_lumpy  |      1 |       0.517 |    1     | 0.682 |              0.041 |          29 |                   15 |                         0.034 |                  1 |
| robust_zscore        | high_earner_lumpy  |      1 |       1     |    0.667 | 0.8   |              0     |          10 |                   15 |                         0.1   |                  1 |
| local_outlier_factor | high_earner_lumpy  |      1 |       0.517 |    1     | 0.682 |              0.041 |          29 |                   15 |                         0.034 |                  1 |
| rule_based           | high_earner_lumpy  |      1 |       0.722 |    0.867 | 0.788 |              0.015 |          18 |                   15 |                         0.056 |                  1 |
| isolation_forest     | high_earner_lumpy  |      2 |       0.414 |    1     | 0.585 |              0.049 |          29 |                   12 |                         0.138 |                  1 |
| robust_zscore        | high_earner_lumpy  |      2 |       1     |    0.75  | 0.857 |              0     |           9 |                   12 |                         0.444 |                  1 |
| local_outlier_factor | high_earner_lumpy  |      2 |       0.414 |    1     | 0.585 |              0.049 |          29 |                   12 |                         0.138 |                  1 |
| rule_based           | high_earner_lumpy  |      2 |       0.611 |    0.917 | 0.733 |              0.02  |          18 |                   12 |                         0.222 |                  1 |
| isolation_forest     | high_earner_lumpy  |      3 |       0.448 |    1     | 0.619 |              0.047 |          29 |                   13 |                         0.103 |                  1 |
| robust_zscore        | high_earner_lumpy  |      3 |       1     |    0.615 | 0.762 |              0     |           8 |                   13 |                         0.375 |                  1 |
| local_outlier_factor | high_earner_lumpy  |      3 |       0.448 |    1     | 0.619 |              0.047 |          29 |                   13 |                         0.103 |                  1 |
| rule_based           | high_earner_lumpy  |      3 |       0.6   |    0.923 | 0.727 |              0.023 |          20 |                   13 |                         0.15  |                  1 |
| isolation_forest     | high_earner_lumpy  |      4 |       0.379 |    1     | 0.55  |              0.051 |          29 |                   11 |                         0.103 |                  1 |
| robust_zscore        | high_earner_lumpy  |      4 |       1     |    0.818 | 0.9   |              0     |           9 |                   11 |                         0.333 |                  1 |
| local_outlier_factor | high_earner_lumpy  |      4 |       0.379 |    1     | 0.55  |              0.051 |          29 |                   11 |                         0.103 |                  1 |
| rule_based           | high_earner_lumpy  |      4 |       0.611 |    1     | 0.759 |              0.02  |          18 |                   11 |                         0.167 |                  1 |
| isolation_forest     | high_earner_lumpy  |      5 |       0.448 |    1     | 0.619 |              0.047 |          29 |                   13 |                         0.034 |                  1 |
| robust_zscore        | high_earner_lumpy  |      5 |       1     |    0.692 | 0.818 |              0     |           9 |                   13 |                         0.111 |                  1 |
| local_outlier_factor | high_earner_lumpy  |      5 |       0.448 |    1     | 0.619 |              0.047 |          29 |                   13 |                         0.034 |                  1 |
| rule_based           | high_earner_lumpy  |      5 |       0.684 |    1     | 0.813 |              0.018 |          19 |                   13 |                         0.053 |                  1 |