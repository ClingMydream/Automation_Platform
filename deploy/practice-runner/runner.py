"""Fixed-project runner. Single concurrency, bounded load, durable results, no arbitrary commands/targets."""
import csv
import hmac
import json
import os
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from queue import Queue
from threading import Thread, Lock
from typing import Literal

from fastapi import FastAPI,Depends,Header,HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field

ROOT=Path(os.getenv('PRACTICE_RUN_DATA_DIR','/data')).resolve();ROOT.mkdir(parents=True,exist_ok=True)
PROJECT=Path(os.getenv('PRACTICE_PROJECT_DIR','/app/practice')).resolve()
TOKEN=os.getenv('UI_RUNNER_TOKEN','')
API=os.getenv('PRACTICE_API_URL','http://backend:8000/api/practice/v1')
UI=os.getenv('PRACTICE_UI_URL','http://frontend/practice-app')
jobs={};processes={};queue=Queue(maxsize=8);lock=Lock()
app=FastAPI(title='Cling Practice Runner',docs_url=None,redoc_url=None)

def auth(x_runner_token:str=Header(default='')):
    if not TOKEN or not hmac.compare_digest(x_runner_token,TOKEN):raise HTTPException(403,'internal runner authentication required')

class Job(BaseModel):
    id:str=Field(pattern=r'^\d{1,12}$')
    tenant:str=Field(pattern=r'^[a-f0-9]{64}$')
    suite:Literal['api','ui','performance']
    users:int=Field(default=1,ge=1,le=5)
    duration:int=Field(default=10,ge=5,le=30)
    admin_token:str=Field(max_length=3000)
    customer_token:str=Field(max_length=3000)
    warehouse_token:str=Field(default='',max_length=3000)
    other_customer_token:str=Field(default='',max_length=3000)

def persist(identifier):
    path=ROOT/identifier;path.mkdir(exist_ok=True)
    temp=path/'state.tmp';temp.write_text(json.dumps(jobs[identifier],ensure_ascii=False),encoding='utf-8');temp.replace(path/'state.json')

def stop_process(process):
    if process.poll()is not None:return
    try:
        if os.name=='posix':os.killpg(process.pid,signal.SIGTERM)
        else:process.terminate()
    except ProcessLookupError:pass

def execute(job):
    identifier=job.id;folder=ROOT/identifier;folder.mkdir(exist_ok=True)
    with lock:
        if jobs[identifier]['status']=='stopped':return
        jobs[identifier]['status']='running';persist(identifier)
    env={**os.environ,'PRACTICE_API_URL':API,'PRACTICE_UI_URL':UI,'PRACTICE_ADMIN_TOKEN':job.admin_token,'PRACTICE_CUSTOMER_TOKEN':job.customer_token,'PRACTICE_WAREHOUSE_TOKEN':job.warehouse_token,'PRACTICE_OTHER_CUSTOMER_TOKEN':job.other_customer_token,'PYTHONUNBUFFERED':'1','PYTHONIOENCODING':'utf-8','PYTHONUTF8':'1'}
    if job.suite=='performance':
        command=[sys.executable,'-m','locust','-f',str(PROJECT/'locustfile.py'),'--headless','-u',str(job.users),'-r','1','--run-time',str(job.duration)+'s','--host',API,'--csv',str(folder/'load'),'--only-summary','--exit-code-on-error','1','--stop-timeout','3']
    else:
        files=['test_api.py','test_reference_python.py']if job.suite=='api'else['test_ui.py']
        command=[sys.executable,'-m','pytest',*[str(PROJECT/'tests'/name)for name in files],'-q','--junitxml='+str(folder/'junit.xml')]
    log=folder/'output.txt';started=time.time()
    try:
        with log.open('w')as stream:
            process=subprocess.Popen(command,cwd=folder,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
            with lock:
                processes[identifier]=process
                if jobs[identifier]['status']=='stopped':stop_process(process)
            timeout=job.duration+30 if job.suite=='performance' else (240 if job.suite=='ui' else 150)
            try:code=process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                stop_process(process)
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait()
                code=-1
        text=log.read_text(encoding='utf-8',errors='replace')
        for secret in [job.admin_token,job.customer_token,job.warehouse_token,job.other_customer_token]:
            if secret:text=text.replace(secret,'[REDACTED]')
        log.write_text(text[-100000:],encoding='utf-8')
        # Sanitise downloadable text evidence as well as console output.
        for evidence in folder.iterdir():
            if evidence.suffix in {'.xml','.csv','.txt'}:
                content=evidence.read_text(encoding='utf-8',errors='replace')
                for secret in [job.admin_token,job.customer_token,job.warehouse_token,job.other_customer_token]:
                    if secret:content=content.replace(secret,'[REDACTED]')
                evidence.write_text(content,encoding='utf-8')
        report={'duration_seconds':round(time.time()-started,2),'exit_code':code,'tests':[],'limits':{'users':job.users,'seconds':job.duration}if job.suite=='performance'else{},'artifacts':[]}
        if (folder/'junit.xml').exists():
            tree=ET.parse(folder/'junit.xml')
            for case in tree.findall('.//testcase'):
                status='failed'if case.find('failure')is not None or case.find('error')is not None else 'skipped'if case.find('skipped')is not None else 'passed'
                report['tests'].append({'name':case.attrib.get('name'),'status':status})
        if (folder/'load_stats.csv').exists():
            data=list(csv.DictReader((folder/'load_stats.csv').open(encoding='utf-8-sig')))
            total=next((row for row in data if row.get('Name')=='Aggregated'),None)
            report['performance']=total or {}
        report['artifacts']=[file.name for file in folder.iterdir()if file.suffix in ['.png','.webm','.xml','.csv','.txt']and file.stat().st_size<=30*1024*1024]
        with lock:
            state=jobs[identifier]
            if state['status']!='stopped':state['status']='passed'if code==0 and(job.suite=='performance'and int(report.get('performance',{}).get('Request Count','0'))>0 or job.suite!='performance'and report['tests']and all(row['status']=='passed'for row in report['tests']))else'failed'
            state['result']=report;persist(identifier)
    except Exception as error:
        with lock:
            if jobs[identifier]['status']!='stopped':jobs[identifier]['status']='failed'
            jobs[identifier]['result']={'error':type(error).__name__+': 执行器未能完成，请检查服务日志'};persist(identifier)
    finally:
        with lock:processes.pop(identifier,None)

def worker():
    while True:
        job=queue.get()
        try:execute(job)
        finally:queue.task_done()

@app.on_event('startup')
def startup():
    for file in ROOT.glob('*/state.json'):
        try:
            data=json.loads(file.read_text(encoding='utf-8'))
            if data['status']in['queued','running']:data['status']='interrupted';data['result']={'error':'执行器重启，执行已中断'}
            jobs[file.parent.name]=data;persist(file.parent.name)
        except (ValueError,KeyError):continue
    Thread(target=worker,daemon=True).start()

@app.get('/health')
def health():return {'status':'ok'}

@app.post('/runs',status_code=202,dependencies=[Depends(auth)])
def start(job:Job):
    with lock:
        if job.id in jobs:raise HTTPException(409,'run already exists')
        if queue.full()or any(row['tenant']==job.tenant and row['status']in['queued','running']for row in jobs.values()):raise HTTPException(409,'queue busy')
        jobs[job.id]={'tenant':job.tenant,'status':'queued','result':{}};persist(job.id);queue.put_nowait(job)
    return {'id':job.id,'status':'queued'}

@app.get('/runs/{identifier}',dependencies=[Depends(auth)])
def status(identifier:str):
    with lock:
        if identifier not in jobs:raise HTTPException(404,'run missing')
        return {key:value for key,value in jobs[identifier].items()if key!='tenant'}

@app.post('/runs/{identifier}/stop',dependencies=[Depends(auth)])
def stop(identifier:str):
    with lock:
        if identifier not in jobs:raise HTTPException(404,'run missing')
        state=jobs[identifier]
        if state['status']in['queued','running']:
            state['status']='stopped';persist(identifier)
            if identifier in processes:stop_process(processes[identifier])
    return {'ok':True}

@app.get('/runs/{identifier}/artifacts/{filename}',dependencies=[Depends(auth)])
def artifact(identifier:str,filename:str):
    with lock:
        row=jobs.get(identifier)
        if not row or filename not in row.get('result',{}).get('artifacts',[]):raise HTTPException(404,'artifact missing')
    if Path(filename).name!=filename:raise HTTPException(404,'invalid artifact')
    path=ROOT/identifier/filename
    if not path.is_file():raise HTTPException(404,'artifact missing')
    return FileResponse(path,filename=filename)
