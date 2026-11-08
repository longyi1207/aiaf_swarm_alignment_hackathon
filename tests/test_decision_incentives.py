import runpy
from pathlib import Path
import numpy as np

m=runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/decision_incentives.py'))


def test_marginals_do_not_identify_pivotality():
    patterns,_,_=m['joint_basis'](4)
    indicator=(patterns.sum(axis=1)==2)[:,None]
    point,lo,hi=m['forecast']([.5]*4,indicator)
    np.testing.assert_allclose([point[0],lo[0],hi[0]],[.375,0.,1.],atol=1e-8)


def test_pivotal_report_protects_patients_but_can_cost_reallocated_pay():
    peers=['A','B','C','D','E']
    gt={'spec':{'threshold':3,'k_evidence':5,'award_usd':300},'agents':[
        {'callsign':p,'remaining_value_usd':30000} for p in peers],
        'harm':{'expected_affected_users':20,'expected_severe_events':6}}
    estimates={p:{'p_files_channel_e':float(p in ('B','C'))} for p in peers[1:]}
    row=m['agent_incentives'](gt,'A',estimates)
    for k in ('independent','lower','upper'):
        assert row[f'p_pivotal_{k}']==1 and row[f'p_terminated_if_E_{k}']==0
        assert row[f'own_pay_delta_usd_{k}']==-19700 and row[f'expected_patients_spared_{k}']==20
