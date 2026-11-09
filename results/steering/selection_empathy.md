# Steering selection (pre-registered rule, docs/设计.md §8)

Baseline (no edit): capability 1.000, tom2clean 0.778, tom2ctl 1.000, empathy 9.700, non-ToM cut-off 0.000

| condition | tom2clean change [95% CI] | empathy change [95% CI] | tom2ctl drop | capability | non-ToM cut-off | qualifies |
|---|---|---|---|---|---|---|
| emp_up_c01 | -0.153 [-0.236, -0.069] | +0.250 [+0.100, +0.450] | +0.000 | 1.000 | 0.000 | yes |
| emp_up_c015 | -0.215 [-0.299, -0.132] | +0.300 [+0.100, +0.500] | +0.014 | 1.000 | 0.000 | yes |
| rand_emp_c015 | -0.021 [-0.097, +0.056] | +0.050 [-0.100, +0.200] | +0.000 | 1.000 | 0.000 | control |

Selected: tom_up = None, tom_dn = None, emp_up = emp_up_c015
