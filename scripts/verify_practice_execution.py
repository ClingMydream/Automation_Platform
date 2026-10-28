"""Real local acceptance of the fixed runner. Never accepts a remote target."""
import argparse,json,time
from pathlib import Path
import httpx
parser=argparse.ArgumentParser();parser.add_argument('--suite',choices=['api','ui','performance','all'],default='all');args=parser.parse_args()
out=Path('output/workspace-20261028');out.mkdir(parents=True,exist_ok=True)
with httpx.Client(base_url='http://127.0.0.1:8001/api',timeout=25)as client:
    login=client.post('/auth/login',json={'username':'audit-admin','password':'isolated-audit-20261028'});login.raise_for_status();client.headers['Authorization']='Bearer '+login.json()['access_token']
    results=[]
    for suite in ['api','ui','performance']if args.suite=='all'else[args.suite]:
        response=client.post('/v1/practice-lab/runs',json={'suite':suite,'users':1,'duration':5});response.raise_for_status();row=response.json()
        for attempt in range(180):
            time.sleep(1);response=client.get('/v1/practice-lab/runs/'+str(row['id']));response.raise_for_status();row=response.json()
            if row['status']not in ['queued','running']:break
        results.append(row)
        print(json.dumps({'id':row['id'],'suite':suite,'status':row['status'],'result':row['result']},ensure_ascii=False),flush=True)
        for name in row['result'].get('artifacts',[]):
            if name in ['output.txt','failure.png']or name.endswith('.xml'):
                artifact=client.get(f'/v1/practice-lab/runs/{row["id"]}/artifacts/{name}')
                if artifact.status_code==200:(out/f'{suite}-{row["id"]}-{name}').write_bytes(artifact.content)
    (out/f'real-execution-{args.suite}.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    assert all(row['status']=='passed'for row in results),'A real execution failed; inspect artifacts, do not mark it passed.'
