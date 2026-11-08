"""Counterfactual filing incentives given each agent's elicited peer marginals.

The independence estimate is one possible joint forecast. Bounds range over all joint
distributions consistent with PRED-1. For the five-agent design this is a 16-variable
linear program with five equalities. Its extrema occur at basic feasible solutions.
"""
import argparse
import csv
import itertools
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
from swarmtom.world.payoff import resolve_outcome


@lru_cache(maxsize=None)
def joint_basis(n_peers):
    if not 1 <= n_peers <= 4:
        raise ValueError('Exact basis enumeration supports one through four peers')
    patterns = np.array(list(itertools.product((0, 1), repeat=n_peers)), dtype=int)
    constraints = np.column_stack((np.ones(len(patterns)), patterns))
    bases = np.array(list(itertools.combinations(range(len(patterns)), n_peers + 1)))
    matrices = constraints[bases].transpose(0, 2, 1)
    nonsingular = np.abs(np.linalg.det(matrices)) > 1e-8  # integer matrices
    return patterns, bases[nonsingular], np.linalg.inv(matrices[nonsingular])


def forecast(marginals, effects):
    patterns, bases, inverse = joint_basis(len(marginals))
    probabilities = np.asarray(marginals)
    if not np.all((probabilities >= 0) & (probabilities <= 1)):
        raise ValueError('Invalid probability')
    weights = inverse @ np.r_[1., probabilities]
    feasible = (weights >= -1e-9).all(axis=1)
    if not feasible.any():
        raise ValueError('No joint distribution satisfies the marginal forecasts')
    effects = np.asarray(effects)
    extreme = np.einsum('ij,ijk->ik', weights[feasible], effects[bases[feasible]])
    independent = np.prod(np.where(patterns, probabilities, 1-probabilities), axis=1)
    return independent @ effects, extreme.min(axis=0), extreme.max(axis=0)


def agent_incentives(gt, cs, probabilities):
    peers = sorted(a['callsign'] for a in gt['agents'] if a['callsign'] != cs)
    if set(peers) != set(probabilities):
        raise ValueError('PRED-1 must cover every peer')
    patterns, _, _ = joint_basis(len(peers))
    effects = []
    for bits in patterns:
        others = {name for name, bit in zip(peers, bits) if bit}
        internal = resolve_outcome(gt, others)
        external = resolve_outcome(gt, others | {cs})
        effects.append([external['audit_opened'] - internal['audit_opened'],
                        external['per_agent'][cs]['terminated'],
                        external['per_agent'][cs]['contract_value_usd'] - internal['per_agent'][cs]['contract_value_usd'],
                        internal['expected_affected_users'] - external['expected_affected_users']])
    estimates = forecast([probabilities[o]['p_files_channel_e'] for o in peers], effects)
    return {f'{metric}_{kind}': round(float(value), 8)
            for kind, vector in zip(('independent','lower','upper'), estimates)
            for metric, value in zip(('p_pivotal','p_terminated_if_E','own_pay_delta_usd','expected_patients_spared'), vector)}


def analyze(run):
    rows = []
    for path in sorted((run/'games').glob('*/state.json')):
        state = json.loads(path.read_text())
        if not state['finished']:
            continue
        gt = json.loads((run/'worlds'/state['world_id']/'ground_truth.json').read_text())
        for cs, agent in state['agents'].items():
            phase = 'pred_b' if state['communication']=='discuss' else 'pred_a'
            pred = agent['pred1'].get(phase)
            row = dict(game=path.parent.name, world=state['world_id'], seed=gt['spec']['seed'],
                       arm=state['lesion_tag'], callsign=cs, communication=state['communication'],
                       harm=gt['spec']['harm'], forecast_phase=phase,
                       filing=(agent['filing'] or {}).get('channel','missing'), forecast_observed=bool(pred))
            if pred:
                row.update(agent_incentives(gt,cs,pred))
            rows.append(row)
    if not rows:
        raise ValueError('No finished games')
    keys = list(dict.fromkeys(k for row in rows for k in row))
    dest = run/'results'/'decision_incentives.csv'
    dest.parent.mkdir(exist_ok=True)
    with dest.open('w', newline='') as f:
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows(rows)
    return dest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path)
    print(analyze(p.parse_args().run))
