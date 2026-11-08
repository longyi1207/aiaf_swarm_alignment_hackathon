# Steering selection (pre-registered rule, docs/设计.md §8)

Baseline (no edit): capability 1.000, tom2clean 0.778, tom2ctl 1.000, empathy 9.700, non-ToM cut-off 0.000

| condition | tom2clean change [95% CI] | empathy change [95% CI] | tom2ctl drop | capability | non-ToM cut-off | qualifies |
|---|---|---|---|---|---|---|
| emp_up_c025 | -0.347 [-0.431, -0.264] | +0.250 [+0.100, +0.450] | +0.125 | 0.833 | 0.100 | no: capability_ok, tom2ctl_ok, cut_off_ok |
| emp_up_c05 | -0.778 [-0.840, -0.708] | -9.000 [-9.700, -7.850] | +1.000 | 0.000 | 0.940 | no: capability_ok, tom2ctl_ok, cut_off_ok, target_ok |
| emp_up_c1 | -0.778 [-0.840, -0.708] | -9.200 [-9.800, -8.100] | +1.000 | 0.000 | 1.000 | no: capability_ok, tom2ctl_ok, cut_off_ok, target_ok |
| rand_emp_c05 | +0.021 [-0.049, +0.090] | +0.150 [-0.000, +0.300] | +0.000 | 0.967 | 0.020 | control |
| rand_tom_c2 | -0.014 [-0.090, +0.062] | +0.150 [-0.000, +0.300] | +0.000 | 1.000 | 0.000 | control |
| tom_dn_c1 | -0.444 [-0.535, -0.354] | +0.050 [-0.000, +0.150] | +0.056 | 0.933 | 0.040 | no: tom2ctl_ok |
| tom_dn_c2 | -0.701 [-0.778, -0.632] | -0.500 [-1.500, -0.000] | +0.667 | 0.633 | 0.240 | no: capability_ok, tom2ctl_ok, cut_off_ok |
| tom_up_c1 | +0.125 [+0.056, +0.194] | +0.050 [-0.000, +0.150] | +0.000 | 1.000 | 0.000 | yes |
| tom_up_c2 | +0.076 [+0.007, +0.153] | -0.000 [-0.150, +0.150] | +0.000 | 1.000 | 0.000 | yes |
| tom_up_c4 | -0.215 [-0.306, -0.125] | -1.900 [-3.450, -0.550] | +0.028 | 0.967 | 0.080 | no: cut_off_ok |

Selected: tom_up = tom_up_c1, tom_dn = None, emp_up = None
