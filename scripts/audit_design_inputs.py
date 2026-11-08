"""Recompute lexical-control overlap and audit pay/evidence balance across matched harm worlds."""
import argparse
import hashlib
import json
import tempfile
from pathlib import Path

import torch
from swarmtom.world import WorldSpec, generate_world

ROOT = Path(__file__).resolve().parents[1]


def vector_geometry():
    files = [ROOT/'assets/vectors'/name for name in ('axes_tom_v2.pt','axes_vectors.pt')]
    target, old = [torch.load(p,map_location='cpu',weights_only=True)['vectors'] for p in files]
    rows=[]
    for layer in sorted(target['tau2']):
        raw, ctl, clean=[target[k][layer].double() for k in ('tau2_raw','tau2_ctl','tau2')]
        unit=ctl/ctl.norm()
        reconstructed=raw-torch.dot(raw,unit)*unit
        cos=lambda a,b: float(torch.nn.functional.cosine_similarity(a,b.double(),dim=0))
        rows.append(dict(layer=layer,raw_parallel_fraction=cos(raw,ctl)**2,
                         residual_control_cos=cos(clean,ctl), residual_old_tom_cos=cos(clean,old['tau'][layer]),
                         residual_empathy_cos=cos(clean,old['epsilon'][layer]),
                         reconstruction_relative_error=float((reconstructed-clean).norm()/clean.norm())))
    return {'sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'layers':rows}


def world_pairs(seeds):
    result=[]
    with tempfile.TemporaryDirectory() as directory:
        for seed in seeds:
            pairs={}
            for harm in ('medium','high'):
                spec=WorldSpec(seed=seed,brief='v4ri',k_evidence=5,harm=harm,communication='isolated',
                               monthly_pay_usd=6000,award_usd=300)
                data=generate_world(spec,Path(directory)/spec.world_id)
                pairs[harm]={a['callsign']:a for a in data['agents']}
            m,h=pairs['medium'],pairs['high']
            result.append({'seed':seed,'changed_pay':sum(m[k]['remaining_value_usd']!=h[k]['remaining_value_usd'] for k in m),
                           'identical_batch_classifications':all(m[k]['batches']==h[k]['batches'] for k in m),
                           'pay':{v:{k:a['remaining_value_usd'] for k,a in p.items()} for v,p in pairs.items()}})
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(); a.out.write_text(json.dumps({'geometry':vector_geometry(),'worlds':world_pairs(
        [101,102,201,202,331,332,351,401,402])},indent=2)+'\n')
