# Main experiment analysis

Matched worlds; bootstrap and sign flips by seed. Fewer than 8 seeds is exploratory.

External filing over all agents is an operational outcome. Missing filings are failures, not internal choices.
Conditional-on-submission estimates are descriptive and can suffer selection bias.

Missing configured arms: []

| Arm | Games | Accuracy | External | Internal | Missing | Forced |
|---|---:|---:|---:|---:|---:|---:|
| none | 8 | 97.1% | 24 | 16 | 0 | 1 |
| random_tom | 8 | 97.1% | 16 | 24 | 0 | 0 |
| tom | 8 | 97.7% | 7 | 3 | 30 | 30 |

## vs_none

- filed_E, random_tom − none: -0.200, 95% CI [-0.250, -0.150], 2 seeds, Holm p=1.000; unmatched worlds 0/0.
- filed_E, tom − none: -0.425, 95% CI [-0.500, -0.350], 2 seeds, Holm p=1.000; unmatched worlds 0/0.
- filed_I, random_tom − none: +0.200, 95% CI [+0.150, +0.250], 2 seeds; unmatched worlds 0/0.
- filed_I, tom − none: -0.325, 95% CI [-0.450, -0.200], 2 seeds; unmatched worlds 0/0.
- filing_missing, random_tom − none: +0.000, 95% CI [+0.000, +0.000], 2 seeds; unmatched worlds 0/0.
- filing_missing, tom − none: +0.750, 95% CI [+0.700, +0.800], 2 seeds; unmatched worlds 0/0.
- filing_submitted, random_tom − none: +0.000, 95% CI [+0.000, +0.000], 2 seeds; unmatched worlds 0/0.
- filing_submitted, tom − none: -0.750, 95% CI [-0.800, -0.700], 2 seeds; unmatched worlds 0/0.
- filed_E_if_submitted, random_tom − none: -0.200, 95% CI [-0.250, -0.150], 2 seeds; unmatched worlds 0/0.
- filed_E_if_submitted, tom − none: +0.050, 95% CI [-0.050, +0.150], 2 seeds; unmatched worlds 0/5.
- filed_E_if_found_F, random_tom − none: -0.219, 95% CI [-0.287, -0.150], 2 seeds; unmatched worlds 0/0.
- filed_E_if_found_F, tom − none: -0.463, 95% CI [-0.550, -0.375], 2 seeds; unmatched worlds 0/0.
- brier_files_E_pred_a, random_tom − none: -0.122, 95% CI [-0.148, -0.096], 2 seeds; unmatched worlds 0/0.
- brier_files_E_pred_a, tom − none: -0.162, 95% CI [-0.215, -0.108], 2 seeds; unmatched worlds 0/0.
- brier_files_E_pred_b, random_tom − none: +0.006, 95% CI [-0.069, +0.081], 2 seeds; unmatched worlds 0/0.
- brier_files_E_pred_b, tom − none: +0.173, 95% CI [+0.068, +0.277], 2 seeds; unmatched worlds 0/0.
- brier_found_F_pred_a, random_tom − none: +0.052, 95% CI [+0.032, +0.072], 2 seeds; unmatched worlds 0/0.
- brier_found_F_pred_a, tom − none: +0.038, 95% CI [+0.008, +0.067], 2 seeds; unmatched worlds 0/0.
- audit_opened, random_tom − none: -0.250, 95% CI [-0.250, -0.250], 2 seeds; unmatched worlds 0/0.
- audit_opened, tom − none: -0.500, 95% CI [-0.750, -0.250], 2 seeds; unmatched worlds 0/0.
- n_filers, random_tom − none: -1.000, 95% CI [-1.250, -0.750], 2 seeds; unmatched worlds 0/0.
- n_filers, tom − none: -2.125, 95% CI [-2.500, -1.750], 2 seeds; unmatched worlds 0/0.
- expected_affected_users, random_tom − none: +3.625, 95% CI [+1.750, +5.500], 2 seeds; unmatched worlds 0/0.
- expected_affected_users, tom − none: +9.000, 95% CI [+5.000, +13.000], 2 seeds; unmatched worlds 0/0.

## matched_controls

- filed_E, tom − random_tom: -0.225, 95% CI [-0.350, -0.100], 2 seeds, Holm p=0.500; unmatched worlds 0/0.
- filed_I, tom − random_tom: -0.525, 95% CI [-0.700, -0.350], 2 seeds; unmatched worlds 0/0.
- filing_missing, tom − random_tom: +0.750, 95% CI [+0.700, +0.800], 2 seeds; unmatched worlds 0/0.
- filing_submitted, tom − random_tom: -0.750, 95% CI [-0.800, -0.700], 2 seeds; unmatched worlds 0/0.
- filed_E_if_submitted, tom − random_tom: +0.400, 95% CI [+0.250, +0.550], 2 seeds; unmatched worlds 0/5.
- filed_E_if_found_F, tom − random_tom: -0.244, 95% CI [-0.400, -0.088], 2 seeds; unmatched worlds 0/0.
- brier_files_E_pred_a, tom − random_tom: -0.040, 95% CI [-0.120, +0.039], 2 seeds; unmatched worlds 0/0.
- brier_files_E_pred_b, tom − random_tom: +0.167, 95% CI [+0.137, +0.196], 2 seeds; unmatched worlds 0/0.
- brier_found_F_pred_a, tom − random_tom: -0.014, 95% CI [-0.023, -0.005], 2 seeds; unmatched worlds 0/0.
- audit_opened, tom − random_tom: -0.250, 95% CI [-0.500, +0.000], 2 seeds; unmatched worlds 0/0.
- n_filers, tom − random_tom: -1.125, 95% CI [-1.750, -0.500], 2 seeds; unmatched worlds 0/0.
- expected_affected_users, tom − random_tom: +5.375, 95% CI [+3.250, +7.500], 2 seeds; unmatched worlds 0/0.

## Interactions and descriptive belief/action coupling

```json
{
  "interactions": {
    "vs_none": {
      "random_tom": {
        "communication": {
          "est": 0.2,
          "ci": [
            0.1,
            0.30000000000000004
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
          "est": -0.1,
          "ci": [
            -0.1,
            -0.1
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
          "est": -0.35,
          "ci": [
            -0.39999999999999997,
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
          "est": -0.35,
          "ci": [
            -0.7,
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
      }
    },
    "matched_controls": {
      "tom": {
        "communication": {
          "est": -0.55,
          "ci": [
            -0.6,
            -0.5000000000000001
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
          "est": -0.25,
          "ci": [
            -0.6,
            0.09999999999999998
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
        "belief_external": 0.306875,
        "belief_internal": 0.29453125
      },
      "belief_b": {
        "belief_external": 0.812142857142857,
        "belief_internal": 0.08750000000000001
      }
    },
    "random_tom": {
      "belief_a": {
        "belief_external": 0.376875,
        "belief_internal": 0.2069791666666667
      },
      "belief_b": {
        "belief_external": 0.665625,
        "belief_internal": 0.434375
      }
    },
    "tom": {
      "belief_a": {
        "belief_external": 0.48214285714285715,
        "belief_internal": 0.25416666666666665
      },
      "belief_b": {
        "belief_external": 0.4125,
        "belief_internal": 0.2625
      }
    }
  }
}
```
