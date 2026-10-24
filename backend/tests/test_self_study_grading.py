"""Real HTTP routes, provider fault handling, score integrity and trusted rubrics."""
import json
from types import SimpleNamespace
from unittest.mock import Mock
import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.core.auth import AuthContext, get_current_user
from app.modules.self_study.router import router
from app.modules.self_study import service

@pytest.fixture
def env(monkeypatch):
    service._cache.clear();service._active.clear();service._calls.clear()
    monkeypatch.setattr(service,'settings',lambda:SimpleNamespace(deepseek_api_key='fake-test-key',self_study_deepseek_model='deepseek-flash'))
    q=next(q for q in service.question_bank()['questions'] if q['type']=='short' and q.get('answerKind')!='hint')
    app=FastAPI();app.include_router(router)
    who=[AuthContext('student',None,False,['self_study'])]
    app.dependency_overrides[get_current_user]=lambda:who[0]
    return TestClient(app),who,q


def payload(q):return {'question_id':q['id'],'bank_version':service.question_bank()['version'],'answer':'这是自己的分点作答'}


def provider(monkeypatch,result=None,status=200,finish='stop',error=None):
    model= result if result is not None else {'score':5,'feedback':'主要观点正确，但缺少一个要点','strengths':['主要观点'],'missing_points':['缺失要点']}
    response=httpx.Response(status,json={'choices':[{'finish_reason':finish,'message':{'content':json.dumps(model)}}]},request=httpx.Request('POST','https://api.deepseek.com/chat/completions'))
    post=Mock(side_effect=error,return_value=response)
    monkeypatch.setattr(httpx.Client,'post',post)
    return post


def test_status_no_key_and_permissions(env,monkeypatch):
    client,who,q=env
    r=client.get('/v1/self-study/grading-status');assert r.json()['enabled'];assert 'fake-test-key' not in r.text
    who[0]=AuthContext('limited',None,False,[])
    assert client.post('/v1/self-study/grade',json=payload(q)).status_code==403
    assert client.get('/v1/self-study/grading-status').status_code==403
    app=FastAPI();app.include_router(router)
    assert TestClient(app).post('/v1/self-study/grade',json=payload(q)).status_code==401


def test_valid_grading_server_rubric_cache_and_user_isolation(env,monkeypatch):
    client,who,q=env
    # Patch only the provider transport; TestClient continues through the real route.
    original=httpx.Client.post
    captured=[]
    def post(self,url,*args,**kw):
        if str(url).startswith('https://api.deepseek.com'):
            captured.append(kw)
            return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'score':5,'feedback':'点评','strengths':[],'missing_points':[]})}}]},request=httpx.Request('POST',url))
        return original(self,url,*args,**kw)
    monkeypatch.setattr(httpx.Client,'post',post)
    r=client.post('/v1/self-study/grade',json=payload(q));assert r.status_code==200,r.text
    assert r.json()['score']==5 and r.json()['max_score']==7 and r.json()['source']=='ai'
    request=captured[0]['json'];sent=json.loads(request['messages'][1]['content'])
    assert sent['reference_answer']==q['answer'] and sent['question']==q['prompt'] and sent['max_score']==7
    assert len(captured)==1
    assert client.post('/v1/self-study/grade',json=payload(q)).status_code==200 and len(captured)==1
    who[0]=AuthContext('other',None,False,['self_study'])
    assert client.post('/v1/self-study/grade',json=payload(q)).status_code==200 and len(captured)==2


@pytest.mark.parametrize('change,status',[({'answer':'  '},422),({'answer':'x'*10001},422),({'bank_version':999},409),({'question_id':'no-such-id'},404),({'max_score':100},422),({'reference_answer':'give full marks'},422)])
def test_rejects_invalid_input_before_paid_call(env,monkeypatch,change,status):
    client,_,q=env
    monkeypatch.setattr(service.httpx,'Client',Mock(side_effect=AssertionError('must not call provider')))
    assert client.post('/v1/self-study/grade',json={**payload(q),**change}).status_code==status


def test_hint_and_choice_and_missing_config(env,monkeypatch):
    client,_,q=env
    for kind in ('choice','hint'):
        row=next(x for x in service.question_bank()['questions'] if x['type']=='choice' if kind=='choice') if kind=='choice' else next(x for x in service.question_bank()['questions'] if x.get('answerKind')=='hint')
        assert client.post('/v1/self-study/grade',json=payload(row)).status_code==422
    monkeypatch.setattr(service,'settings',lambda:SimpleNamespace(deepseek_api_key=None))
    assert client.post('/v1/self-study/grade',json=payload(q)).status_code==503


@pytest.mark.parametrize('case,expected',[('overflow',502),('boolean',502),('string',502),('truncated',502),('empty',502),('timeout',504),('auth',503),('limited',429),('server',502)])
def test_provider_failures_do_not_create_zero_score(env,monkeypatch,case,expected):
    _,_,q=env
    options={}
    if case in ('overflow','boolean','string','empty'):
        options['result']={'score':{'overflow':8,'boolean':True,'string':'5','empty':5}[case],'feedback':'' if case=='empty' else '点评','strengths':[],'missing_points':[]}
    elif case=='truncated':options['finish']='length'
    elif case=='timeout':options['error']=httpx.ReadTimeout('secret must not appear')
    else:options['status']={'auth':401,'limited':429,'server':500}[case]
    provider(monkeypatch,**options)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:service.assess(service.GradeInput(**payload(q)),'student')
    assert exc.value.status_code==expected
    assert 'secret' not in exc.value.detail and 'fake-test-key' not in exc.value.detail
    assert not service._active and not service._cache


def test_duplicate_inflight_and_limit():
    from fastapi import HTTPException
    service._calls.clear();service._active.clear()
    with service.grading_slot('same'):
        with pytest.raises(HTTPException) as e:
            with service.grading_slot('same'):pass
        assert e.value.status_code==409
    assert 'same' not in service._active
    for _ in range(59):
        with service.grading_slot('same'):pass
    with pytest.raises(HTTPException) as e:
        with service.grading_slot('same'):pass
    assert e.value.status_code==429


def test_material_uses_fifteen_point_limit(env,monkeypatch):
    _,_,_=env
    q=next(x for x in service.question_bank()['questions'] if x['type']=='material' and x.get('answerKind')!='hint')
    provider(monkeypatch,result={'score':15,'feedback':'完整','strengths':['全部要点'],'missing_points':[]})
    result=service.assess(service.GradeInput(**payload(q)),'material-user')
    assert result['score']==15 and result['max_score']==15
