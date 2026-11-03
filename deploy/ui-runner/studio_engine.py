"""Serial UI scenario engine with explicit steps, isolated evidence and honest results."""
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright
from execution_report import make_report
from network_evidence import NetworkEvidence, scrub
from studio_flows import EmotePages, TestDataRequired


def execute_studio(task, callback, root):
    run_id = task['run_id']
    directory = Path(root) / f'run-{run_id}'
    directory.mkdir(parents=True, exist_ok=True)
    started = datetime.now(ZoneInfo('Asia/Shanghai'))
    credentials = task.get('credentials', {})
    secrets = [str(v) for group in credentials.values() if isinstance(group, dict) for v in group.values() if v]
    network = NetworkEvidence(secrets)
    rows, timeline, artifacts = [], [], []
    total = sum(len(c['steps']) for c in task['cases']) or 1
    completed = 0
    viewport = {'width':390,'height':844} if task.get('viewport') == 'mobile' else {'width':1440,'height':900}
    state_dir = Path(root) / 'studio-auth'
    state_dir.mkdir(mode=0o700, exist_ok=True)
    account = credentials.get('account_a', {})
    identity = task['base_url'] + '|' + str(account.get('username', ''))
    state = state_dir / (hashlib.sha256(identity.encode()).hexdigest() + '.json')

    def artifact(path, kind):
        artifacts.append({'kind':kind,'name':path.name,'stored_name':str(path.relative_to(root)),
                          'content_type':'image/png' if kind=='screenshot' else 'video/webm',
                          'size_bytes':path.stat().st_size})

    def emit(status, label, error=''):
        callback(run_id, status=status, current_step=label, progress=round(completed/total*100),
                 error_message=error, artifacts=artifacts,
                 result_summary={'engine':'studio-v2','timeline':timeline,'case_results':rows,
                                 'network_issues':network.rows,
                                 'report':make_report(rows,len(task['cases']),started,'running' if status=='running' else status)})

    emit('running','准备测试环境')
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,
            args=['--no-sandbox','--disable-dev-shm-usage'])
        context = None
        try:
            explicit_login = any(s['action']=='login' for c in task['cases'] for s in c['steps'])
            if not explicit_login:
                options = {'viewport':viewport}
                if state.exists() and time.time()-state.stat().st_mtime < 86400:
                    options['storage_state'] = str(state)
                prep = browser.new_context(**options)
                page = prep.new_page()
                network.bind(page)
                pages = EmotePages(page,task['base_url'],credentials)
                renewed=False
                if 'storage_state' not in options:
                    pages.login()
                    renewed=True
                else:
                    try:
                        pages.home()
                    except Exception:
                        pages.login();renewed=True
                if renewed:
                    prep.storage_state(path=str(state));state.chmod(0o600)
                prep.close()
            context_options = {'viewport':viewport,'record_video_dir':str(directory/'raw-video'),'record_video_size':viewport}
            if not explicit_login:
                context_options['storage_state'] = str(state)
            context = browser.new_context(**context_options)
            context.set_default_timeout(20000)
            context.set_default_navigation_timeout(45000)
            page = context.new_page()
            network.bind(page)
            pages = EmotePages(page,task['base_url'],credentials)
            for case in task['cases']:
                case_id = case['id']
                network.case_id = case_id
                case_started = time.monotonic()
                row = {'case_id':case_id,'case_name':case['name'],'feature_name':case.get('feature_name',case['name']),
                       'status':'passed','reason':''}
                for number, step in enumerate(case['steps'],1):
                    network.step = step.get('label',step['action'])
                    tick = time.monotonic()
                    event = {'case_id':case_id,'case_name':case['name'],'step_index':number,
                             'name':network.step,'action':step['action']}
                    emit('running',case['name']+' · '+network.step)
                    try:
                        action = step['action']
                        pages.perform(step)
                        if action=='login':
                            context.storage_state(path=str(state));state.chmod(0o600)
                        event['status'] = 'passed'
                    except Exception as error:
                        failure_status='blocked' if isinstance(error,TestDataRequired) else 'failed'
                        row.update(status=failure_status,reason=scrub(str(error),secrets))
                        event.update(status=failure_status,error=row['reason'])
                        failure = directory / f'case-{case_id}-failure.png'
                        try:
                            page.screenshot(path=str(failure),full_page=False)
                            artifact(failure,'screenshot')
                        except Exception as capture_error:
                            row['screenshot_error'] = scrub(str(capture_error),secrets)
                        break
                    finally:
                        event['duration_ms'] = round((time.monotonic()-tick)*1000)
                        timeline.append(event)
                        completed += 1
                if row['status']=='passed':
                    image = directory / f'case-{case_id}-key.png'
                    page.screenshot(path=str(image),full_page=False);artifact(image,'screenshot')
                row['duration_ms'] = round((time.monotonic()-case_started)*1000)
                row['network_issues'] = network.for_case(case_id)
                row['checks'] = list(pages.checks)
                pages.checks.clear()
                rows.append(row)
                emit('running',case['name']+' · '+('通过' if row['status']=='passed' else '失败'))
                if row['status']!='passed':
                    failed_video=page.video
                    context.close()
                    if failed_video:
                        destination=directory/f'case-{case_id}-video.webm'
                        Path(failed_video.path()).replace(destination);artifact(destination,'video')
                    context=None
                    if case is task['cases'][-1]:
                        continue
                    recovery={**context_options}
                    if state.exists():recovery['storage_state']=str(state)
                    context=browser.new_context(**recovery)
                    context.set_default_timeout(20000)
                    page=context.new_page();network.bind(page)
                    pages=EmotePages(page,task['base_url'],credentials)
            video = page.video if context else None
            if context:
                context.close();context=None
            if video:
                destination = directory/'run-video.webm'
                source=Path(video.path())
                if source.is_file():
                    source.replace(destination);artifact(destination,'video')
            completed = total
            emit('passed' if len(rows)==len(task['cases']) and all(r['status']=='passed' for r in rows) else 'failed','执行完成')
        except Exception as error:
            if 'page' in locals() and not page.is_closed():
                try:
                    image=directory/f"case-{task['cases'][0]['id']}-preparation-failure.png"
                    page.screenshot(path=str(image),full_page=False);artifact(image,'screenshot')
                except Exception:
                    pass
            emit('failed','执行未完成',scrub(str(error),secrets))
        finally:
            if context:
                context.close()
            browser.close()
