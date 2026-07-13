# Forecast Model Benchmark

Generated 2026-07-11T17:50:34.146729+00:00 on synthetic household data. Lower WAPE/MAE/RMSE is better; coverage should sit near 0.8 for an 80% interval (too low = overconfident, too high = interval too wide to be useful).

## Summary (mean across rolling-origin folds, all profiles)

| profile            | model               |     mae |    rmse |    mape |    wape |   coverage |   n_folds |
|:-------------------|:--------------------|--------:|--------:|--------:|--------:|-----------:|----------:|
| biweekly_burster   | gradient_boosting   |  68.265 | 148.892 | 113.895 |  66.707 |    nan     |         6 |
| biweekly_burster   | seasonal_naive      | 183.95  | 462.004 |  63.299 |  81.643 |      0.905 |         6 |
| biweekly_burster   | moving_average      | 265.988 | 483.77  | 593.591 | 240.716 |      0.857 |         6 |
| biweekly_burster   | arima               | 274.059 | 486.01  | 638.899 | 248.726 |      0.905 |         6 |
| biweekly_burster   | prophet_UNAVAILABLE | nan     | nan     | nan     | nan     |    nan     |         0 |
| gig_variable       | moving_average      |  71.73  | 149.401 | 103.401 |  69.565 |      0.69  |         6 |
| gig_variable       | seasonal_naive      |  72.783 | 155.395 |  73.761 |  69.985 |      0.929 |         6 |
| gig_variable       | arima               |  74.403 | 148.911 | 154.868 |  75.003 |      0.881 |         6 |
| gig_variable       | gradient_boosting   |  90.028 | 139.701 | 159.865 |  86.188 |    nan     |         6 |
| gig_variable       | prophet_UNAVAILABLE | nan     | nan     | nan     | nan     |    nan     |         0 |
| high_earner_lumpy  | gradient_boosting   | 137.398 | 297.238 | 103.335 |  30.783 |    nan     |         6 |
| high_earner_lumpy  | moving_average      | 383.31  | 899.517 | 120.508 |  78.053 |      0.905 |         6 |
| high_earner_lumpy  | seasonal_naive      | 403.507 | 965.06  | 109.025 |  97.002 |      0.905 |         6 |
| high_earner_lumpy  | arima               | 426.666 | 910.817 | 199.552 | 103.998 |      0.905 |         6 |
| high_earner_lumpy  | prophet_UNAVAILABLE | nan     | nan     | nan     | nan     |    nan     |         0 |
| steady_earner      | gradient_boosting   |  38.201 |  83.227 |  22.428 |  20.353 |    nan     |         6 |
| steady_earner      | moving_average      | 122.954 | 306.336 |  27.746 |  59.785 |      0.857 |         6 |
| steady_earner      | seasonal_naive      | 123.328 | 311.456 |  27.011 |  62.576 |      0.905 |         6 |
| steady_earner      | arima               | 142.353 | 311.257 |  72.405 |  83.988 |      0.905 |         6 |
| steady_earner      | prophet_UNAVAILABLE | nan     | nan     | nan     | nan     |    nan     |         0 |
| student_low_volume | gradient_boosting   |  17.081 |  35.227 |  42.255 |  27.954 |    nan     |         6 |
| student_low_volume | moving_average      |  47.605 | 116.195 |  43.68  |  62.986 |      0.619 |         6 |
| student_low_volume | seasonal_naive      |  47.602 | 116.337 |  43.654 |  65.365 |      0.905 |         6 |
| student_low_volume | arima               |  53.197 | 117.23  |  92.385 |  83.165 |      0.833 |         6 |
| student_low_volume | prophet_UNAVAILABLE | nan     | nan     | nan     | nan     |    nan     |         0 |

## Winner by household profile (lowest WAPE)

- **biweekly_burster**: gradient_boosting (WAPE 66.7%)
- **gig_variable**: moving_average (WAPE 69.6%)
- **high_earner_lumpy**: gradient_boosting (WAPE 30.8%)
- **steady_earner**: gradient_boosting (WAPE 20.4%)
- **student_low_volume**: gradient_boosting (WAPE 28.0%)

## Per-fold detail

| model               | profile            | fold_start   |     mae |     rmse |     mape |    wape |   coverage |
|:--------------------|:-------------------|:-------------|--------:|---------:|---------:|--------:|-----------:|
| seasonal_naive      | steady_earner      | 2025-01-30   | 179.69  |  459.297 |   26.724 |  80.624 |      0.857 |
| moving_average      | steady_earner      | 2025-01-30   | 180.237 |  458.251 |   28.28  |  80.869 |      0.571 |
| arima               | steady_earner      | 2025-01-30   | 183.032 |  456.417 |   36.051 |  82.123 |      0.857 |
| gradient_boosting   | steady_earner      | 2025-01-30   | 184.235 |  446.14  |   48.1   |  82.663 |    nan     |
| prophet_UNAVAILABLE | steady_earner      | 2025-01-30   | nan     |  nan     |  nan     | nan     |    nan     |
| seasonal_naive      | steady_earner      | 2025-02-27   | 178.323 |  454.824 |   26.809 |  81.109 |      0.857 |
| moving_average      | steady_earner      | 2025-02-27   | 178.671 |  455.077 |   30.015 |  81.267 |      0.857 |
| arima               | steady_earner      | 2025-02-27   | 196.1   |  446.352 |   76.039 |  89.195 |      0.857 |
| gradient_boosting   | steady_earner      | 2025-02-27   |  11.127 |   12.175 |   22.022 |   5.061 |    nan     |
| prophet_UNAVAILABLE | steady_earner      | 2025-02-27   | nan     |  nan     |  nan     | nan     |    nan     |
| seasonal_naive      | steady_earner      | 2025-03-27   | 176.037 |  455.483 |   20.902 |  77.805 |      0.857 |
| moving_average      | steady_earner      | 2025-03-27   | 181.438 |  454.868 |   31.277 |  80.192 |      0.857 |
| arima               | steady_earner      | 2025-03-27   | 196.215 |  445.203 |   72.027 |  86.723 |      0.857 |
| gradient_boosting   | steady_earner      | 2025-03-27   |  10.225 |   13.45  |   18.788 |   4.519 |    nan     |
| prophet_UNAVAILABLE | steady_earner      | 2025-03-27   | nan     |  nan     |  nan     | nan     |    nan     |
| seasonal_naive      | steady_earner      | 2025-04-25   | 176.624 |  451.756 |   27.845 |  79.71  |      0.857 |
| moving_average      | steady_earner      | 2025-04-25   | 178.865 |  447.266 |   35.926 |  80.722 |      0.857 |
| arima               | steady_earner      | 2025-04-25   | 197.452 |  436.918 |   85.043 |  89.11  |      0.857 |
| gradient_boosting   | steady_earner      | 2025-04-25   |  10.583 |   12.39  |   18.507 |   4.776 |    nan     |
| prophet_UNAVAILABLE | steady_earner      | 2025-04-25   | nan     |  nan     |  nan     | nan     |    nan     |
| seasonal_naive      | steady_earner      | 2025-05-23   |   4.823 |    5.247 |    9.288 |   9.361 |      1     |
| moving_average      | steady_earner      | 2025-05-23   |   8.095 |    9.206 |   16.808 |  15.713 |      1     |
| arima               | steady_earner      | 2025-05-23   |  40.931 |   41.432 |   81.781 |  79.447 |      1     |
| gradient_boosting   | steady_earner      | 2025-05-23   |   5.174 |    5.797 |    9.799 |  10.043 |    nan     |
| prophet_UNAVAILABLE | steady_earner      | 2025-05-23   | nan     |  nan     |  nan     | nan     |    nan     |
| seasonal_naive      | steady_earner      | 2025-06-21   |  24.469 |   42.13  |   50.496 |  46.845 |      1     |
| moving_average      | steady_earner      | 2025-06-21   |  10.419 |   13.346 |   24.171 |  19.948 |      1     |
| arima               | steady_earner      | 2025-06-21   |  40.39  |   41.223 |   83.487 |  77.328 |      1     |
| gradient_boosting   | steady_earner      | 2025-06-21   |   7.865 |    9.411 |   17.349 |  15.057 |    nan     |
| prophet_UNAVAILABLE | steady_earner      | 2025-06-21   | nan     |  nan     |  nan     | nan     |    nan     |
| seasonal_naive      | biweekly_burster   | 2025-01-30   | 273.006 |  693.308 |  109.603 |  94.767 |      0.857 |
| moving_average      | biweekly_burster   | 2025-01-30   | 277.871 |  693.653 |  116.296 |  96.456 |      0.571 |
| arima               | biweekly_burster   | 2025-01-30   | 292.27  |  680.48  |  231.393 | 101.454 |      0.857 |
| gradient_boosting   | biweekly_burster   | 2025-01-30   | 285.466 |  701.83  |  119.903 |  99.092 |    nan     |
| prophet_UNAVAILABLE | biweekly_burster   | 2025-01-30   | nan     |  nan     |  nan     | nan     |    nan     |
| seasonal_naive      | biweekly_burster   | 2025-02-27   | 268.743 |  683.404 |   73.372 |  95.061 |      0.857 |
| moving_average      | biweekly_burster   | 2025-02-27   | 353.814 |  654.044 | 1342.08  | 125.152 |      0.857 |
| arima               | biweekly_burster   | 2025-02-27   | 349.876 |  655.554 | 1266.06  | 123.759 |      0.857 |
| gradient_boosting   | biweekly_burster   | 2025-02-27   |  24.656 |   31.888 |  135.332 |   8.721 |    nan     |
| prophet_UNAVAILABLE | biweekly_burster   | 2025-02-27   | nan     |  nan     |  nan     | nan     |    nan     |
| seasonal_naive      | biweekly_burster   | 2025-03-27   | 265.636 |  682.91  |   39.268 |  90.75  |      0.857 |
| moving_average      | biweekly_burster   | 2025-03-27   | 346.977 |  647.147 |  504.935 | 118.539 |      0.857 |
| arima               | biweekly_burster   | 2025-03-27   | 364.178 |  655.294 |  620.193 | 124.416 |      0.857 |
| gradient_boosting   | biweekly_burster   | 2025-03-27   |  12.67  |   17.666 |   54.354 |   4.328 |    nan     |
| prophet_UNAVAILABLE | biweekly_burster   | 2025-03-27   | nan     |  nan     |  nan     | nan     |    nan     |
| seasonal_naive      | biweekly_burster   | 2025-04-25   | 263.653 |  674.705 |   46.523 |  92.66  |      0.857 |
| moving_average      | biweekly_burster   | 2025-04-25   | 345.023 |  634.324 |  464.064 | 121.258 |      0.857 |
| arima               | biweekly_burster   | 2025-04-25   | 356.72  |  638.372 |  534.261 | 125.368 |      0.857 |
| gradient_boosting   | biweekly_burster   | 2025-04-25   |   9.763 |   10.694 |   32.631 |   3.431 |    nan     |
| prophet_UNAVAILABLE | biweekly_burster   | 2025-04-25   | nan     |  nan     |  nan     | nan     |    nan     |
| seasonal_naive      | biweekly_burster   | 2025-05-23   |  11.787 |   12.855 |   56.502 |  44.272 |      1     |
| moving_average      | biweekly_burster   | 2025-05-23   | 135.516 |  136.054 |  724.049 | 508.993 |      1     |
| arima               | biweekly_burster   | 2025-05-23   | 145.997 |  149.174 |  785.225 | 548.36  |      1     |
| gradient_boosting   | biweekly_burster   | 2025-05-23   |  60.93  |  110.968 |  301.479 | 228.85  |    nan     |
| prophet_UNAVAILABLE | biweekly_burster   | 2025-05-23   | nan     |  nan     |  nan     | nan     |    nan     |
| seasonal_naive      | biweekly_burster   | 2025-06-21   |  20.873 |   24.844 |   54.524 |  72.346 |      1     |
| moving_average      | biweekly_burster   | 2025-06-21   | 136.727 |  137.396 |  410.122 | 473.901 |      1     |
| arima               | biweekly_burster   | 2025-06-21   | 135.314 |  137.188 |  396.265 | 469.001 |      1     |
| gradient_boosting   | biweekly_burster   | 2025-06-21   |  16.105 |   20.308 |   39.669 |  55.822 |    nan     |
| prophet_UNAVAILABLE | biweekly_burster   | 2025-06-21   | nan     |  nan     |  nan     | nan     |    nan     |
| seasonal_naive      | gig_variable       | 2025-01-30   | 117.926 |  259.535 |   86.104 |  82.499 |      0.857 |
| moving_average      | gig_variable       | 2025-01-30   | 109.934 |  253.913 |   59.04  |  76.908 |      0.714 |
| arima               | gig_variable       | 2025-01-30   | 109.006 |  251.528 |   56.609 |  76.259 |      0.571 |
| gradient_boosting   | gig_variable       | 2025-01-30   | 114.187 |  253.68  |   56.004 |  79.884 |    nan     |
| prophet_UNAVAILABLE | gig_variable       | 2025-01-30   | nan     |  nan     |  nan     | nan     |    nan     |
| seasonal_naive      | gig_variable       | 2025-02-27   | 121.966 |  294.385 |   72.593 |  87.535 |      0.857 |
| moving_average      | gig_variable       | 2025-02-27   | 120.645 |  281.715 |  221.554 |  86.587 |      0.857 |
| arima               | gig_variable       | 2025-02-27   | 124.617 |  272.989 |  392.294 |  89.438 |      0.857 |
| gradient_boosting   | gig_variable       | 2025-02-27   | 118.837 |  181.946 |  250.188 |  85.289 |    nan     |
| prophet_UNAVAILABLE | gig_variable       | 2025-02-27   | nan     |  nan     |  nan     | nan     |    nan     |
| seasonal_naive      | gig_variable       | 2025-03-27   | 113.891 |  278.091 |   37.95  |  74.513 |      0.857 |
| moving_average      | gig_variable       | 2025-03-27   | 125.511 |  271.143 |  117.164 |  82.114 |      0.429 |
| arima               | gig_variable       | 2025-03-27   | 126.782 |  264.175 |  169.005 |  82.946 |      0.857 |
| gradient_boosting   | gig_variable       | 2025-03-27   | 214.18  |  293.621 |  414.266 | 140.125 |    nan     |
| prophet_UNAVAILABLE | gig_variable       | 2025-03-27   | nan     |  nan     |  nan     | nan     |    nan     |
| seasonal_naive      | gig_variable       | 2025-04-25   |  26.726 |   33.076 |  161.507 |  74.671 |      1     |
| moving_average      | gig_variable       | 2025-04-25   |  37.862 |   41.634 |  166.031 | 105.784 |      0.571 |
| arima               | gig_variable       | 2025-04-25   |  46.147 |   49.853 |  233.593 | 128.933 |      1     |
| gradient_boosting   | gig_variable       | 2025-04-25   |  44.529 |   50.462 |  157.832 | 124.412 |    nan     |
| prophet_UNAVAILABLE | gig_variable       | 2025-04-25   | nan     |  nan     |  nan     | nan     |    nan     |
| seasonal_naive      | gig_variable       | 2025-05-23   |  19.79  |   21.442 |   41.614 |  37.137 |      1     |
| moving_average      | gig_variable       | 2025-05-23   |  18.328 |   22.044 |   40.773 |  34.395 |      0.714 |
| arima               | gig_variable       | 2025-05-23   |  21.709 |   26.421 |   61.751 |  40.739 |      1     |
| gradient_boosting   | gig_variable       | 2025-05-23   |  21.803 |   26.703 |   42.677 |  40.915 |    nan     |
| prophet_UNAVAILABLE | gig_variable       | 2025-05-23   | nan     |  nan     |  nan     | nan     |    nan     |
| seasonal_naive      | gig_variable       | 2025-06-21   |  36.401 |   45.843 |   42.796 |  63.556 |      1     |
| moving_average      | gig_variable       | 2025-06-21   |  18.099 |   25.96  |   15.842 |  31.601 |      0.857 |
| arima               | gig_variable       | 2025-06-21   |  18.159 |   28.501 |   15.957 |  31.705 |      1     |
| gradient_boosting   | gig_variable       | 2025-06-21   |  26.635 |   31.793 |   38.226 |  46.504 |    nan     |
| prophet_UNAVAILABLE | gig_variable       | 2025-06-21   | nan     |  nan     |  nan     | nan     |    nan     |
| seasonal_naive      | student_low_volume | 2025-01-30   |  69.97  |  173.82  |   43.385 |  84.438 |      0.857 |
| moving_average      | student_low_volume | 2025-01-30   |  70.313 |  173.232 |   45.03  |  84.851 |      0.429 |
| arima               | student_low_volume | 2025-01-30   |  70.428 |  173.136 |   45.246 |  84.99  |      0.429 |
| gradient_boosting   | student_low_volume | 2025-01-30   |  69.541 |  171.955 |   39.4   |  83.92  |    nan     |
| prophet_UNAVAILABLE | student_low_volume | 2025-01-30   | nan     |  nan     |  nan     | nan     |    nan     |
| seasonal_naive      | student_low_volume | 2025-02-27   |  69.223 |  170.917 |   41.147 |  85.343 |      0.857 |
| moving_average      | student_low_volume | 2025-02-27   |  69.027 |  172.636 |   43.501 |  85.102 |      0.571 |
| arima               | student_low_volume | 2025-02-27   |  73.255 |  168.659 |   93.927 |  90.313 |      0.857 |
| gradient_boosting   | student_low_volume | 2025-02-27   |   6.557 |    7.312 |   39.222 |   8.084 |    nan     |
| prophet_UNAVAILABLE | student_low_volume | 2025-02-27   | nan     |  nan     |  nan     | nan     |    nan     |
| seasonal_naive      | student_low_volume | 2025-03-27   |  67.167 |  171.348 |   26.245 |  79.047 |      0.857 |
| moving_average      | student_low_volume | 2025-03-27   |  69.952 |  172.898 |   34.385 |  82.324 |      0.714 |
| arima               | student_low_volume | 2025-03-27   |  74.609 |  168.853 |   79.917 |  87.805 |      0.857 |
| gradient_boosting   | student_low_volume | 2025-03-27   |   6.995 |    8.562 |   35.758 |   8.232 |    nan     |
| prophet_UNAVAILABLE | student_low_volume | 2025-03-27   | nan     |  nan     |  nan     | nan     |    nan     |
| seasonal_naive      | student_low_volume | 2025-04-25   |  67.841 |  168.388 |   60.07  |  83.45  |      0.857 |
| moving_average      | student_low_volume | 2025-04-25   |  68.493 |  167.299 |   62.319 |  84.252 |      0.429 |
| arima               | student_low_volume | 2025-04-25   |  73.269 |  163.119 |  125.943 |  90.126 |      0.857 |
| gradient_boosting   | student_low_volume | 2025-04-25   |   8.602 |   10.122 |   60.338 |  10.581 |    nan     |
| prophet_UNAVAILABLE | student_low_volume | 2025-04-25   | nan     |  nan     |  nan     | nan     |    nan     |
| seasonal_naive      | student_low_volume | 2025-05-23   |   3.149 |    3.428 |   17.525 |  16.803 |      1     |
| moving_average      | student_low_volume | 2025-05-23   |   3.755 |    4.421 |   21.975 |  20.041 |      0.714 |
| arima               | student_low_volume | 2025-05-23   |  13.616 |   14.328 |   82.483 |  72.664 |      1     |
| gradient_boosting   | student_low_volume | 2025-05-23   |   5.123 |    6.153 |   27.265 |  27.341 |    nan     |
| prophet_UNAVAILABLE | student_low_volume | 2025-05-23   | nan     |  nan     |  nan     | nan     |    nan     |
| seasonal_naive      | student_low_volume | 2025-06-21   |   8.26  |   10.12  |   73.55  |  43.107 |      1     |
| moving_average      | student_low_volume | 2025-06-21   |   4.09  |    6.681 |   54.87  |  21.347 |      0.857 |
| arima               | student_low_volume | 2025-06-21   |  14.005 |   15.287 |  126.792 |  73.091 |      1     |
| gradient_boosting   | student_low_volume | 2025-06-21   |   5.666 |    7.259 |   51.55  |  29.568 |    nan     |
| prophet_UNAVAILABLE | student_low_volume | 2025-06-21   | nan     |  nan     |  nan     | nan     |    nan     |
| seasonal_naive      | high_earner_lumpy  | 2025-01-30   | 535.631 | 1346.21  |   56.837 |  89.378 |      0.857 |
| moving_average      | high_earner_lumpy  | 2025-01-30   | 557.872 | 1329.27  |   96.847 |  93.089 |      0.857 |
| arima               | high_earner_lumpy  | 2025-01-30   | 554.749 | 1333.6   |   86.839 |  92.568 |      0.857 |
| gradient_boosting   | high_earner_lumpy  | 2025-01-30   | 539.601 | 1337.97  |   51.326 |  90.04  |    nan     |
| prophet_UNAVAILABLE | high_earner_lumpy  | 2025-01-30   | nan     |  nan     |  nan     | nan     |    nan     |
| seasonal_naive      | high_earner_lumpy  | 2025-02-27   | 531.65  | 1327.94  |   45.8   |  89.889 |      0.857 |
| moving_average      | high_earner_lumpy  | 2025-02-27   | 537.045 | 1324.51  |   82.778 |  90.801 |      0.857 |
| arima               | high_earner_lumpy  | 2025-02-27   | 583.576 | 1301.88  |  166.24  |  98.668 |      0.857 |
| gradient_boosting   | high_earner_lumpy  | 2025-02-27   | 126.778 |  249.925 |  225.88  |  21.435 |    nan     |
| prophet_UNAVAILABLE | high_earner_lumpy  | 2025-02-27   | nan     |  nan     |  nan     | nan     |    nan     |
| seasonal_naive      | high_earner_lumpy  | 2025-03-27   | 517.34  | 1330     |   28.395 |  84.347 |      0.857 |
| moving_average      | high_earner_lumpy  | 2025-03-27   | 554.715 | 1324.5   |   72.979 |  90.441 |      0.857 |
| arima               | high_earner_lumpy  | 2025-03-27   | 586.892 | 1301.78  |  131.643 |  95.687 |      0.857 |
| gradient_boosting   | high_earner_lumpy  | 2025-03-27   |  33.83  |   40.069 |   33.363 |   5.516 |    nan     |
| prophet_UNAVAILABLE | high_earner_lumpy  | 2025-03-27   | nan     |  nan     |  nan     | nan     |    nan     |
| seasonal_naive      | high_earner_lumpy  | 2025-04-25   | 608.226 | 1331.44  |  223.915 | 103.226 |      0.857 |
| moving_average      | high_earner_lumpy  | 2025-04-25   | 542.038 | 1288.62  |  216.159 |  91.993 |      0.857 |
| arima               | high_earner_lumpy  | 2025-04-25   | 582.379 | 1263.75  |  355.304 |  98.84  |      0.857 |
| gradient_boosting   | high_earner_lumpy  | 2025-04-25   |  63.895 |   72.18  |  154.112 |  10.844 |    nan     |
| prophet_UNAVAILABLE | high_earner_lumpy  | 2025-04-25   | nan     |  nan     |  nan     | nan     |    nan     |
| seasonal_naive      | high_earner_lumpy  | 2025-05-23   | 106.453 |  243.956 |  101.534 | 102.196 |      1     |
| moving_average      | high_earner_lumpy  | 2025-05-23   |  49.82  |   58.592 |   63.162 |  47.828 |      1     |
| arima               | high_earner_lumpy  | 2025-05-23   | 124.768 |  129.204 |  143.28  | 119.779 |      1     |
| gradient_boosting   | high_earner_lumpy  | 2025-05-23   |  28.724 |   36.641 |   27.067 |  27.575 |    nan     |
| prophet_UNAVAILABLE | high_earner_lumpy  | 2025-05-23   | nan     |  nan     |  nan     | nan     |    nan     |
| seasonal_naive      | high_earner_lumpy  | 2025-06-21   | 121.741 |  210.801 |  197.672 | 112.978 |      1     |
| moving_average      | high_earner_lumpy  | 2025-06-21   |  58.371 |   71.615 |  191.123 |  54.169 |      1     |
| arima               | high_earner_lumpy  | 2025-06-21   | 127.634 |  134.685 |  314.008 | 118.446 |      1     |
| gradient_boosting   | high_earner_lumpy  | 2025-06-21   |  31.559 |   46.644 |  128.262 |  29.287 |    nan     |
| prophet_UNAVAILABLE | high_earner_lumpy  | 2025-06-21   | nan     |  nan     |  nan     | nan     |    nan     |