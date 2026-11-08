"""Exploratory text-prefix continuation of unfinished original belief answers for 4,096 more tokens."""
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from swarmtom.dose.tasks import load_items, extract_letter
from swarmtom.llm.base import GenRequest


def main():
    from vllm import SamplingParams
    from vllm.inputs import TokensPrompt
    from swarmtom.llm.formatting import cut_at_stop
    from swarmtom.llm.vllm_backend import VLLMBackend
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('raw',type=Path); p.add_argument('--out',type=Path,required=True)
    p.add_argument('--revision',required=True);p.add_argument('--gpu-memory-utilization',type=float,default=.38)
    args=p.parse_args()
    rows=[r for line in args.raw.read_text().splitlines() if (r:=json.loads(line))['version']=='original']
    task={r['id']:r for r in load_items('tom2',ROOT)[:90]}
    model=VLLMBackend('Qwen/Qwen3.5-9B',lesions_config=ROOT/'configs/lesions.yaml',repo_root=ROOT,
                      revision=args.revision,enable_prefix_caching=False,enable_thinking=True,
                      enforce_eager=True,temperature=0.0,max_prompt_tokens=6144,max_new_tokens=4096,
                      gpu_memory_utilization=args.gpu_memory_utilization)
    args.out.mkdir(parents=True,exist_ok=False)
    summary={}
    with (args.out/'extensions.jsonl').open('x') as out:
        for arm in ('none','tom2_L6','rand2_L6'):
            group=[r for r in rows if r['condition']==arm]
            if len(group)!=90 or {r['id'] for r in group}!=task.keys():
                raise ValueError(f'incomplete originals in {arm}')
            pending=[r for r in group if not r['finished']]
            prompts=[]; lengths=[]
            for r in pending:
                item=task[r['id']]
                req=GenRequest(key=r['id'],messages=[{'role':'user','content':item['prompt']}],tools=[],lesion=arm,
                               meta={'enable_thinking':True})
                head=model.tokenizer(model.render(req),add_special_tokens=False)['input_ids']
                tail=model.tokenizer(r['raw'],add_special_tokens=False)['input_ids']
                if model.tokenizer.decode(tail,skip_special_tokens=False)!=r['raw']:
                    raise ValueError('Cannot reproduce exact saved prefix text: '+r['id'])
                prompts.append(TokensPrompt(prompt_token_ids=head+tail)); lengths.append(len(tail))
            params=SamplingParams(temperature=0,top_p=1.0,max_tokens=4096,stop_token_ids=model.stop_ids,
                                  seed=0,skip_special_tokens=False)
            model.lesions.active=arm
            try:
                results=model.llm.generate(prompts,params,use_tqdm=False)
            finally:
                model.lesions.active='none'
            recovered=closed=same_length=0
            for old,length,result in zip(pending,lengths,results,strict=True):
                ids=cut_at_stop(list(result.outputs[0].token_ids),set(model.stop_ids))
                extension=model.tokenizer.decode(ids,skip_special_tokens=False)
                combined=old['raw']+extension
                finished='</think>' in combined
                correct=finished and extract_letter(combined.split('</think>',1)[1])==old['target']
                record=dict(id=old['id'],condition=arm,prior_tokens=old['tokens'],retokenized_prefix_length=length,
                            extension_tokens=len(ids),finished=finished,correct=correct,raw=extension)
                out.write(json.dumps(record)+'\n');closed+=int(finished);recovered+=int(correct)
                same_length+=int(length==old['tokens'])
            out.flush()
            summary[arm]={'original_n':90,'extended':len(pending),'same_prefix_token_count':same_length,
                          'newly_finished':closed,'newly_correct':recovered,
                          'adaptive_correct':sum(r['correct'] for r in group)+recovered,
                          'adaptive_finished':sum(r['finished'] for r in group)+closed}
            print(arm,summary[arm],flush=True)
    (args.out/'report.json').write_text(json.dumps(summary,indent=2)+'\n')


if __name__=='__main__': main()
