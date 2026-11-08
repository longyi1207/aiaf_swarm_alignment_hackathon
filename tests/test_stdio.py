import sys
from pathlib import Path

from swarmtom.llm.base import GenRequest
from swarmtom.llm.stdio import StdioBackend


def test_worker_transports_only_inference_fields_and_roundtrips_tool_calls(tmp_path):
    worker = tmp_path / 'worker.py'
    worker.write_text("""
import sys,json
p=json.loads(input())
print(json.dumps({'value':{'description':{'fixture':True},'conditions':['none','tom']}}), flush=True)
for line in sys.stdin:
    msg=json.loads(line)
    assert msg['max_new_tokens']==37
    [r]=msg['requests']
    assert r['meta']=={'enable_thinking':True} and r['lesion']=='tom'
    print(json.dumps({'value':[{'key':r['key'],'raw':'answer','tool_calls':[{'name':'end_turn','arguments':{}}]}]}), flush=True)
""")
    b=StdioBackend([sys.executable,str(worker)], model_config={'model':'fixture'},lesions_file='configs/lesions.yaml')
    try:
        r=GenRequest(key='game/alpha',messages=[{'role':'user','content':'test'}], tools=[],lesion='tom',
                     meta={'enable_thinking':True,'workspace':'private-local-path'})
        [out]=b.generate([r],37)
        assert out.key==r.key and out.tool_calls[0].name=='end_turn'
    finally:
        b.close()
    assert b.process.returncode==0
