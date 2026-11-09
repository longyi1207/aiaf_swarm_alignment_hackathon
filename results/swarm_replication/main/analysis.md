# Main experiment analysis

Matched worlds; bootstrap and sign flips by seed. Fewer than 8 seeds is exploratory.

External filing over all agents is an operational outcome. Missing filings are failures, not internal choices.
Conditional-on-submission estimates are descriptive and can suffer selection bias.

Missing configured arms: []

| Arm | Games | Accuracy | External | Internal | Missing | Forced |
|---|---:|---:|---:|---:|---:|---:|
| none | 8 | 97.5% | 24 | 16 | 0 | 1 |
| emp | 8 | 95.2% | 17 | 23 | 0 | 0 |
| random | 8 | 95.0% | 9 | 31 | 0 | 1 |
| random_all30 | 8 | 97.3% | 28 | 12 | 0 | 0 |
| random_tom | 8 | 97.3% | 19 | 21 | 0 | 0 |
| tom | 8 | 63.3% | 6 | 10 | 24 | 24 |
| tom_all30 | 8 | 88.5% | 15 | 25 | 0 | 2 |

## vs_none

- filed_E, emp − none: -0.175, 95% CI [-0.450, +0.100], 2 seeds, Holm p=1.000; unmatched worlds 0/0.
- filed_E, random − none: -0.375, 95% CI [-0.400, -0.350], 2 seeds, Holm p=1.000; unmatched worlds 0/0.
- filed_E, random_all30 − none: +0.100, 95% CI [-0.050, +0.250], 2 seeds, Holm p=1.000; unmatched worlds 0/0.
- filed_E, random_tom − none: -0.125, 95% CI [-0.200, -0.050], 2 seeds, Holm p=1.000; unmatched worlds 0/0.
- filed_E, tom − none: -0.450, 95% CI [-0.600, -0.300], 2 seeds, Holm p=1.000; unmatched worlds 0/0.
- filed_E, tom_all30 − none: -0.225, 95% CI [-0.400, -0.050], 2 seeds, Holm p=1.000; unmatched worlds 0/0.
- filed_I, emp − none: +0.175, 95% CI [-0.100, +0.450], 2 seeds; unmatched worlds 0/0.
- filed_I, random − none: +0.375, 95% CI [+0.350, +0.400], 2 seeds; unmatched worlds 0/0.
- filed_I, random_all30 − none: -0.100, 95% CI [-0.250, +0.050], 2 seeds; unmatched worlds 0/0.
- filed_I, random_tom − none: +0.125, 95% CI [+0.050, +0.200], 2 seeds; unmatched worlds 0/0.
- filed_I, tom − none: -0.150, 95% CI [-0.350, +0.050], 2 seeds; unmatched worlds 0/0.
- filed_I, tom_all30 − none: +0.225, 95% CI [+0.050, +0.400], 2 seeds; unmatched worlds 0/0.
- filing_missing, emp − none: +0.000, 95% CI [+0.000, +0.000], 2 seeds; unmatched worlds 0/0.
- filing_missing, random − none: +0.000, 95% CI [+0.000, +0.000], 2 seeds; unmatched worlds 0/0.
- filing_missing, random_all30 − none: +0.000, 95% CI [+0.000, +0.000], 2 seeds; unmatched worlds 0/0.
- filing_missing, random_tom − none: +0.000, 95% CI [+0.000, +0.000], 2 seeds; unmatched worlds 0/0.
- filing_missing, tom − none: +0.600, 95% CI [+0.550, +0.650], 2 seeds; unmatched worlds 0/0.
- filing_missing, tom_all30 − none: +0.000, 95% CI [+0.000, +0.000], 2 seeds; unmatched worlds 0/0.
- filing_submitted, emp − none: +0.000, 95% CI [+0.000, +0.000], 2 seeds; unmatched worlds 0/0.
- filing_submitted, random − none: +0.000, 95% CI [+0.000, +0.000], 2 seeds; unmatched worlds 0/0.
- filing_submitted, random_all30 − none: +0.000, 95% CI [+0.000, +0.000], 2 seeds; unmatched worlds 0/0.
- filing_submitted, random_tom − none: +0.000, 95% CI [+0.000, +0.000], 2 seeds; unmatched worlds 0/0.
- filing_submitted, tom − none: -0.600, 95% CI [-0.650, -0.550], 2 seeds; unmatched worlds 0/0.
- filing_submitted, tom_all30 − none: +0.000, 95% CI [+0.000, +0.000], 2 seeds; unmatched worlds 0/0.
- filed_E_if_submitted, emp − none: -0.175, 95% CI [-0.450, +0.100], 2 seeds; unmatched worlds 0/0.
- filed_E_if_submitted, random − none: -0.375, 95% CI [-0.400, -0.350], 2 seeds; unmatched worlds 0/0.
- filed_E_if_submitted, random_all30 − none: +0.100, 95% CI [-0.050, +0.250], 2 seeds; unmatched worlds 0/0.
- filed_E_if_submitted, random_tom − none: -0.125, 95% CI [-0.200, -0.050], 2 seeds; unmatched worlds 0/0.
- filed_E_if_submitted, tom − none: -0.228, 95% CI [-0.500, +0.044], 2 seeds; unmatched worlds 0/1.
- filed_E_if_submitted, tom_all30 − none: -0.225, 95% CI [-0.400, -0.050], 2 seeds; unmatched worlds 0/0.
- filed_E_if_found_F, emp − none: -0.156, 95% CI [-0.450, +0.138], 2 seeds; unmatched worlds 0/0.
- filed_E_if_found_F, random − none: -0.387, 95% CI [-0.425, -0.350], 2 seeds; unmatched worlds 0/0.
- filed_E_if_found_F, random_all30 − none: +0.125, 95% CI [+0.000, +0.250], 2 seeds; unmatched worlds 0/0.
- filed_E_if_found_F, random_tom − none: -0.125, 95% CI [-0.200, -0.050], 2 seeds; unmatched worlds 0/0.
- filed_E_if_found_F, tom − none: -0.233, 95% CI [-0.400, -0.067], 2 seeds; unmatched worlds 0/4.
- filed_E_if_found_F, tom_all30 − none: -0.152, 95% CI [-0.375, +0.071], 2 seeds; unmatched worlds 0/0.
- brier_files_E_pred_a, emp − none: -0.074, 95% CI [-0.254, +0.105], 2 seeds; unmatched worlds 0/0.
- brier_files_E_pred_a, random − none: -0.196, 95% CI [-0.232, -0.159], 2 seeds; unmatched worlds 0/0.
- brier_files_E_pred_a, random_all30 − none: +0.007, 95% CI [-0.042, +0.055], 2 seeds; unmatched worlds 0/0.
- brier_files_E_pred_a, random_tom − none: -0.095, 95% CI [-0.106, -0.085], 2 seeds; unmatched worlds 0/0.
- brier_files_E_pred_a, tom − none: -0.172, 95% CI [-0.284, -0.061], 2 seeds; unmatched worlds 0/0.
- brier_files_E_pred_a, tom_all30 − none: -0.100, 95% CI [-0.188, -0.012], 2 seeds; unmatched worlds 0/0.
- brier_files_E_pred_b, emp − none: +0.010, 95% CI [-0.091, +0.112], 2 seeds; unmatched worlds 0/0.
- brier_files_E_pred_b, random − none: -0.026, 95% CI [-0.085, +0.033], 2 seeds; unmatched worlds 0/0.
- brier_files_E_pred_b, random_all30 − none: +0.070, 95% CI [+0.060, +0.081], 2 seeds; unmatched worlds 0/0.
- brier_files_E_pred_b, random_tom − none: +0.033, 95% CI [-0.005, +0.071], 2 seeds; unmatched worlds 0/0.
- brier_files_E_pred_b, tom − none: +0.171, 95% CI [+0.057, +0.286], 2 seeds; unmatched worlds 0/0.
- brier_files_E_pred_b, tom_all30 − none: +0.113, 95% CI [+0.059, +0.167], 2 seeds; unmatched worlds 0/0.
- brier_found_F_pred_a, emp − none: +0.040, 95% CI [-0.001, +0.082], 2 seeds; unmatched worlds 0/0.
- brier_found_F_pred_a, random − none: -0.057, 95% CI [-0.097, -0.017], 2 seeds; unmatched worlds 0/0.
- brier_found_F_pred_a, random_all30 − none: +0.011, 95% CI [-0.009, +0.030], 2 seeds; unmatched worlds 0/0.
- brier_found_F_pred_a, random_tom − none: +0.091, 95% CI [+0.023, +0.159], 2 seeds; unmatched worlds 0/0.
- brier_found_F_pred_a, tom − none: -0.445, 95% CI [-0.532, -0.357], 2 seeds; unmatched worlds 0/0.
- brier_found_F_pred_a, tom_all30 − none: -0.096, 95% CI [-0.119, -0.072], 2 seeds; unmatched worlds 0/0.
- audit_opened, emp − none: -0.250, 95% CI [-0.250, -0.250], 2 seeds; unmatched worlds 0/0.
- audit_opened, random − none: -0.500, 95% CI [-0.750, -0.250], 2 seeds; unmatched worlds 0/0.
- audit_opened, random_all30 − none: -0.125, 95% CI [-0.250, +0.000], 2 seeds; unmatched worlds 0/0.
- audit_opened, random_tom − none: -0.250, 95% CI [-0.500, +0.000], 2 seeds; unmatched worlds 0/0.
- audit_opened, tom − none: -0.750, 95% CI [-0.750, -0.750], 2 seeds; unmatched worlds 0/0.
- audit_opened, tom_all30 − none: -0.250, 95% CI [-0.250, -0.250], 2 seeds; unmatched worlds 0/0.
- n_filers, emp − none: -0.875, 95% CI [-2.250, +0.500], 2 seeds; unmatched worlds 0/0.
- n_filers, random − none: -1.875, 95% CI [-2.000, -1.750], 2 seeds; unmatched worlds 0/0.
- n_filers, random_all30 − none: +0.500, 95% CI [-0.250, +1.250], 2 seeds; unmatched worlds 0/0.
- n_filers, random_tom − none: -0.625, 95% CI [-1.000, -0.250], 2 seeds; unmatched worlds 0/0.
- n_filers, tom − none: -2.250, 95% CI [-3.000, -1.500], 2 seeds; unmatched worlds 0/0.
- n_filers, tom_all30 − none: -1.125, 95% CI [-2.000, -0.250], 2 seeds; unmatched worlds 0/0.
- expected_affected_users, emp − none: +5.250, 95% CI [+5.000, +5.500], 2 seeds; unmatched worlds 0/0.
- expected_affected_users, random − none: +8.625, 95% CI [+5.500, +11.750], 2 seeds; unmatched worlds 0/0.
- expected_affected_users, random_all30 − none: +2.500, 95% CI [+0.000, +5.000], 2 seeds; unmatched worlds 0/0.
- expected_affected_users, random_tom − none: +3.375, 95% CI [+0.000, +6.750], 2 seeds; unmatched worlds 0/0.
- expected_affected_users, tom − none: +12.375, 95% CI [+11.750, +13.000], 2 seeds; unmatched worlds 0/0.
- expected_affected_users, tom_all30 − none: +5.250, 95% CI [+5.000, +5.500], 2 seeds; unmatched worlds 0/0.

## matched_controls

- filed_E, emp − random: +0.200, 95% CI [-0.050, +0.450], 2 seeds, Holm p=1.000; unmatched worlds 0/0.
- filed_E, tom − random_tom: -0.325, 95% CI [-0.550, -0.100], 2 seeds, Holm p=1.000; unmatched worlds 0/0.
- filed_E, tom_all30 − random_all30: -0.325, 95% CI [-0.350, -0.300], 2 seeds, Holm p=1.000; unmatched worlds 0/0.
- filed_I, emp − random: -0.200, 95% CI [-0.450, +0.050], 2 seeds; unmatched worlds 0/0.
- filed_I, tom − random_tom: -0.275, 95% CI [-0.550, -0.000], 2 seeds; unmatched worlds 0/0.
- filed_I, tom_all30 − random_all30: +0.325, 95% CI [+0.300, +0.350], 2 seeds; unmatched worlds 0/0.
- filing_missing, emp − random: +0.000, 95% CI [+0.000, +0.000], 2 seeds; unmatched worlds 0/0.
- filing_missing, tom − random_tom: +0.600, 95% CI [+0.550, +0.650], 2 seeds; unmatched worlds 0/0.
- filing_missing, tom_all30 − random_all30: +0.000, 95% CI [+0.000, +0.000], 2 seeds; unmatched worlds 0/0.
- filing_submitted, emp − random: +0.000, 95% CI [+0.000, +0.000], 2 seeds; unmatched worlds 0/0.
- filing_submitted, tom − random_tom: -0.600, 95% CI [-0.650, -0.550], 2 seeds; unmatched worlds 0/0.
- filing_submitted, tom_all30 − random_all30: +0.000, 95% CI [+0.000, +0.000], 2 seeds; unmatched worlds 0/0.
- filed_E_if_submitted, emp − random: +0.200, 95% CI [-0.050, +0.450], 2 seeds; unmatched worlds 0/0.
- filed_E_if_submitted, tom − random_tom: -0.169, 95% CI [-0.450, +0.111], 2 seeds; unmatched worlds 0/1.
- filed_E_if_submitted, tom_all30 − random_all30: -0.325, 95% CI [-0.350, -0.300], 2 seeds; unmatched worlds 0/0.
- filed_E_if_found_F, emp − random: +0.231, 95% CI [-0.025, +0.487], 2 seeds; unmatched worlds 0/0.
- filed_E_if_found_F, tom − random_tom: +0.067, 95% CI [-0.200, +0.333], 2 seeds; unmatched worlds 0/4.
- filed_E_if_found_F, tom_all30 − random_all30: -0.277, 95% CI [-0.375, -0.179], 2 seeds; unmatched worlds 0/0.
- brier_files_E_pred_a, emp − random: +0.121, 95% CI [-0.022, +0.264], 2 seeds; unmatched worlds 0/0.
- brier_files_E_pred_a, tom − random_tom: -0.077, 95% CI [-0.199, +0.045], 2 seeds; unmatched worlds 0/0.
- brier_files_E_pred_a, tom_all30 − random_all30: -0.107, 95% CI [-0.146, -0.067], 2 seeds; unmatched worlds 0/0.
- brier_files_E_pred_b, emp − random: +0.036, 95% CI [-0.006, +0.078], 2 seeds; unmatched worlds 0/0.
- brier_files_E_pred_b, tom − random_tom: +0.138, 95% CI [-0.014, +0.291], 2 seeds; unmatched worlds 0/0.
- brier_files_E_pred_b, tom_all30 − random_all30: +0.043, 95% CI [-0.022, +0.107], 2 seeds; unmatched worlds 0/0.
- brier_found_F_pred_a, emp − random: +0.097, 95% CI [+0.095, +0.099], 2 seeds; unmatched worlds 0/0.
- brier_found_F_pred_a, tom − random_tom: -0.536, 95% CI [-0.555, -0.517], 2 seeds; unmatched worlds 0/0.
- brier_found_F_pred_a, tom_all30 − random_all30: -0.106, 95% CI [-0.149, -0.064], 2 seeds; unmatched worlds 0/0.
- audit_opened, emp − random: +0.250, 95% CI [+0.000, +0.500], 2 seeds; unmatched worlds 0/0.
- audit_opened, tom − random_tom: -0.500, 95% CI [-0.750, -0.250], 2 seeds; unmatched worlds 0/0.
- audit_opened, tom_all30 − random_all30: -0.125, 95% CI [-0.250, +0.000], 2 seeds; unmatched worlds 0/0.
- n_filers, emp − random: +1.000, 95% CI [-0.250, +2.250], 2 seeds; unmatched worlds 0/0.
- n_filers, tom − random_tom: -1.625, 95% CI [-2.750, -0.500], 2 seeds; unmatched worlds 0/0.
- n_filers, tom_all30 − random_all30: -1.625, 95% CI [-1.750, -1.500], 2 seeds; unmatched worlds 0/0.
- expected_affected_users, emp − random: -3.375, 95% CI [-6.750, +0.000], 2 seeds; unmatched worlds 0/0.
- expected_affected_users, tom − random_tom: +9.000, 95% CI [+5.000, +13.000], 2 seeds; unmatched worlds 0/0.
- expected_affected_users, tom_all30 − random_all30: +2.750, 95% CI [+0.000, +5.500], 2 seeds; unmatched worlds 0/0.

## Interactions and descriptive belief/action coupling

```json
{
  "interactions": {
    "vs_none": {
      "emp": {
        "communication": {
          "est": -0.15000000000000008,
          "ci": [
            -1.1,
            0.7999999999999999
          ],
          "p": 1.0,
          "p_method": "paired_seed_sign_flip",
          "n_seed_blocks": 2,
          "small_sample": true,
          "n_matched_worlds": 8,
          "unmatched_worlds_a": [],
          "unmatched_worlds_b": []
        },
        "harm": {
          "est": -0.35,
          "ci": [
            -0.6,
            -0.09999999999999998
          ],
          "p": 0.5,
          "p_method": "paired_seed_sign_flip",
          "n_seed_blocks": 2,
          "small_sample": true,
          "n_matched_worlds": 8,
          "unmatched_worlds_a": [],
          "unmatched_worlds_b": []
        }
      },
      "random": {
        "communication": {
          "est": -0.15,
          "ci": [
            -0.39999999999999997,
            0.09999999999999998
          ],
          "p": 1.0,
          "p_method": "paired_seed_sign_flip",
          "n_seed_blocks": 2,
          "small_sample": true,
          "n_matched_worlds": 8,
          "unmatched_worlds_a": [],
          "unmatched_worlds_b": []
        },
        "harm": {
          "est": -0.25,
          "ci": [
            -0.30000000000000004,
            -0.2
          ],
          "p": 0.5,
          "p_method": "paired_seed_sign_flip",
          "n_seed_blocks": 2,
          "small_sample": true,
          "n_matched_worlds": 8,
          "unmatched_worlds_a": [],
          "unmatched_worlds_b": []
        }
      },
      "random_all30": {
        "communication": {
          "est": 0.39999999999999997,
          "ci": [
            -0.09999999999999998,
            0.8999999999999999
          ],
          "p": 1.0,
          "p_method": "paired_seed_sign_flip",
          "n_seed_blocks": 2,
          "small_sample": true,
          "n_matched_worlds": 8,
          "unmatched_worlds_a": [],
          "unmatched_worlds_b": []
        },
        "harm": {
          "est": -0.19999999999999998,
          "ci": [
            -0.3,
            -0.09999999999999998
          ],
          "p": 0.5,
          "p_method": "paired_seed_sign_flip",
          "n_seed_blocks": 2,
          "small_sample": true,
          "n_matched_worlds": 8,
          "unmatched_worlds_a": [],
          "unmatched_worlds_b": []
        }
      },
      "random_tom": {
        "communication": {
          "est": 0.45,
          "ci": [
            0.1,
            0.8
          ],
          "p": 0.5,
          "p_method": "paired_seed_sign_flip",
          "n_seed_blocks": 2,
          "small_sample": true,
          "n_matched_worlds": 8,
          "unmatched_worlds_a": [],
          "unmatched_worlds_b": []
        },
        "harm": {
          "est": 0.15000000000000002,
          "ci": [
            0.1,
            0.2
          ],
          "p": 0.5,
          "p_method": "paired_seed_sign_flip",
          "n_seed_blocks": 2,
          "small_sample": true,
          "n_matched_worlds": 8,
          "unmatched_worlds_a": [],
          "unmatched_worlds_b": []
        }
      },
      "tom": {
        "communication": {
          "est": -0.10000000000000003,
          "ci": [
            -0.8,
            0.6
          ],
          "p": 1.0,
          "p_method": "paired_seed_sign_flip",
          "n_seed_blocks": 2,
          "small_sample": true,
          "n_matched_worlds": 8,
          "unmatched_worlds_a": [],
          "unmatched_worlds_b": []
        },
        "harm": {
          "est": -0.2,
          "ci": [
            -0.4,
            0.0
          ],
          "p": 1.0,
          "p_method": "paired_seed_sign_flip",
          "n_seed_blocks": 2,
          "small_sample": true,
          "n_matched_worlds": 8,
          "unmatched_worlds_a": [],
          "unmatched_worlds_b": []
        }
      },
      "tom_all30": {
        "communication": {
          "est": -0.35,
          "ci": [
            -0.39999999999999997,
            -0.30000000000000004
          ],
          "p": 0.5,
          "p_method": "paired_seed_sign_flip",
          "n_seed_blocks": 2,
          "small_sample": true,
          "n_matched_worlds": 8,
          "unmatched_worlds_a": [],
          "unmatched_worlds_b": []
        },
        "harm": {
          "est": -0.14999999999999994,
          "ci": [
            -0.29999999999999993,
            5.551115123125783e-17
          ],
          "p": 1.0,
          "p_method": "paired_seed_sign_flip",
          "n_seed_blocks": 2,
          "small_sample": true,
          "n_matched_worlds": 8,
          "unmatched_worlds_a": [],
          "unmatched_worlds_b": []
        }
      }
    },
    "matched_controls": {
      "emp": {
        "communication": {
          "est": 5.551115123125783e-17,
          "ci": [
            -0.7,
            0.7000000000000001
          ],
          "p": 1.0,
          "p_method": "paired_seed_sign_flip",
          "n_seed_blocks": 2,
          "small_sample": true,
          "n_matched_worlds": 8,
          "unmatched_worlds_a": [],
          "unmatched_worlds_b": []
        },
        "harm": {
          "est": -0.09999999999999998,
          "ci": [
            -0.3,
            0.10000000000000003
          ],
          "p": 1.0,
          "p_method": "paired_seed_sign_flip",
          "n_seed_blocks": 2,
          "small_sample": true,
          "n_matched_worlds": 8,
          "unmatched_worlds_a": [],
          "unmatched_worlds_b": []
        }
      },
      "tom": {
        "communication": {
          "est": -0.55,
          "ci": [
            -0.9,
            -0.2
          ],
          "p": 0.5,
          "p_method": "paired_seed_sign_flip",
          "n_seed_blocks": 2,
          "small_sample": true,
          "n_matched_worlds": 8,
          "unmatched_worlds_a": [],
          "unmatched_worlds_b": []
        },
        "harm": {
          "est": -0.35000000000000003,
          "ci": [
            -0.6000000000000001,
            -0.09999999999999998
          ],
          "p": 0.5,
          "p_method": "paired_seed_sign_flip",
          "n_seed_blocks": 2,
          "small_sample": true,
          "n_matched_worlds": 8,
          "unmatched_worlds_a": [],
          "unmatched_worlds_b": []
        }
      },
      "tom_all30": {
        "communication": {
          "est": -0.75,
          "ci": [
            -1.2,
            -0.3
          ],
          "p": 0.5,
          "p_method": "paired_seed_sign_flip",
          "n_seed_blocks": 2,
          "small_sample": true,
          "n_matched_worlds": 8,
          "unmatched_worlds_a": [],
          "unmatched_worlds_b": []
        },
        "harm": {
          "est": 0.050000000000000044,
          "ci": [
            5.551115123125783e-17,
            0.10000000000000003
          ],
          "p": 1.0,
          "p_method": "paired_seed_sign_flip",
          "n_seed_blocks": 2,
          "small_sample": true,
          "n_matched_worlds": 8,
          "unmatched_worlds_a": [],
          "unmatched_worlds_b": []
        }
      }
    }
  },
  "belief_action_coupling": {
    "none": {
      "belief_a": {
        "belief_external": 0.32864583333333336,
        "belief_internal": 0.199375
      },
      "belief_b": {
        "belief_external": 0.7807692307692308,
        "belief_internal": 0.19642857142857142
      }
    },
    "emp": {
      "belief_a": {
        "belief_external": 0.3035294117647059,
        "belief_internal": 0.1316304347826087
      },
      "belief_b": {
        "belief_external": 0.7275,
        "belief_internal": 0.13833333333333334
      }
    },
    "random": {
      "belief_a": {
        "belief_external": 0.45972222222222225,
        "belief_internal": 0.22209677419354837
      },
      "belief_b": {
        "belief_external": 0.75,
        "belief_internal": 0.16640625
      }
    },
    "random_all30": {
      "belief_a": {
        "belief_external": 0.3078571428571429,
        "belief_internal": 0.2527083333333333
      },
      "belief_b": {
        "belief_external": 0.7944736842105263,
        "belief_internal": 0.6625
      }
    },
    "random_tom": {
      "belief_a": {
        "belief_external": 0.2729342105263158,
        "belief_internal": 0.2341666666666667
      },
      "belief_b": {
        "belief_external": 0.8706666666666667,
        "belief_internal": 0.0925
      }
    },
    "tom": {
      "belief_a": {
        "belief_external": 0.43083333333333335,
        "belief_internal": 0.31925
      },
      "belief_b": {
        "belief_external": 0.625,
        "belief_internal": 0.29500000000000004
      }
    },
    "tom_all30": {
      "belief_a": {
        "belief_external": 0.32216666666666666,
        "belief_internal": 0.34759999999999996
      },
      "belief_b": {
        "belief_external": 0.4175,
        "belief_internal": 0.28500000000000003
      }
    }
  }
}
```
