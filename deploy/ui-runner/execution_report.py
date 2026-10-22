"""Case-level reporting: blocked and unfinished cases can never turn green."""
from datetime import datetime
from zoneinfo import ZoneInfo

def make_report(rows, expected, started, status=None):
    passed=[r for r in rows if r['status']=='passed']
    failed=[r for r in rows if r['status']=='failed']
    blocked=[r for r in rows if r['status']=='blocked']
    unknown=max(expected-len(passed)-len(failed)-len(blocked),0)
    result=('running' if status=='running' else 'partial' if passed and (failed or blocked)
            else 'failed' if failed else 'interrupted' if blocked or unknown else 'passed')
    conclusion=('测试进行中。' if result=='running' else '本次测试全部通过。' if result=='passed' else
                f'{len(passed)} 条通过，{len(failed)} 条失败，{len(blocked)} 条受前置条件限制，{unknown} 条未执行。')
    now=datetime.now(ZoneInfo('Asia/Shanghai'))
    keys=('case_id','case_name','feature_name','status','reason')
    return {'status':result,'conclusion':conclusion,'total':expected,'passed':len(passed),'failed':len(failed),
            'blocked':len(blocked),'interrupted':unknown,'started_at':started.isoformat(),
            'finished_at':None if status=='running' else now.isoformat(),
            'duration_ms':int((now-started).total_seconds()*1000),
            'tested_features':list(dict.fromkeys(r.get('feature_name','') for r in rows if r.get('feature_name'))),
            'passed_items':[{k:r.get(k,'') for k in keys} for r in passed],
            'problem_items':[{k:r.get(k,'') for k in keys} for r in rows if r['status'] in ('failed','blocked')]}
