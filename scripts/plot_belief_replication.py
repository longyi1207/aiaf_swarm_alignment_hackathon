"""Render a two-panel figure from the paired belief report."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def render(report, out):
    conditions = [('none','Baseline'),('tom2_L6','ToM L6'),('rand2_L6','Random L6')]
    fig, (left,right) = plt.subplots(1,2,figsize=(10.5,3.6),layout='constrained',width_ratios=[1.3,1])
    positions = range(len(conditions))
    for axis in (left,right):
        axis.set_yticks(list(positions),[label for _,label in conditions])
        axis.set_ylim(2.55,-.55)
        axis.spines[['top','right','left']].set_visible(False)
        axis.tick_params(axis='y',length=0)
    for i,(key,_) in enumerate(conditions):
        r=report[key]
        offset=0
        for n,color,fg,label in [(r['original_correct'],'#176a69','white','Correct'),
                                 (r['original_finished']-r['original_correct'],'#eeb867','#24282b','Wrong'),
                                 (r['original_truncated'],'#ced3dc','#24282b','Unfinished')]:
            left.barh(i,n,left=offset,color=color,height=.56,label=label if i==0 else None)
            if n:
                left.text(offset+n/2,i,str(n),ha='center',va='center',color=fg,fontsize=9)
            offset+=n
        effect=r['repair_minus_control']
        x=100*effect['delta_accuracy'];lo,hi=[100*v for v in effect['scenario_bootstrap_95']]
        right.errorbar(x,i,xerr=[[x-lo],[hi-x]],fmt='o',color='#22587b',capsize=4)
    left.set(xlim=(0,90),xlabel='Original questions (90 per condition)',title='Answer status at 4,096 tokens')
    left.legend(loc='upper center',bbox_to_anchor=(.5,-.19),frameon=False,ncol=3,fontsize=9)
    right.axvline(0,color='#777777',linestyle=':',zorder=0)
    right.set(xlim=(-45,75),xlabel='Difference of accuracy changes (pp)',title='Visibility repair minus control edit')
    right.text(.5,-.25,'18 paired edits per group · 6 scenario blocks · 95% bootstrap intervals',
               transform=right.transAxes,ha='center',fontsize=8)
    fig.suptitle('Belief reasoning with the layer-six intervention',fontsize=14,weight='bold')
    fig.savefig(out,dpi=180,bbox_inches='tight')
    plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('report',type=Path);p.add_argument('output',type=Path)
    args=p.parse_args();render(json.loads(args.report.read_text()),args.output)
