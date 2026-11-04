import json
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from fastapi import HTTPException
from app.modules.ui_automation import task_content as ai
from app.modules.ui_automation import router
from app.modules.online_preview import router as preview


def test_git_versions_are_discovered_from_real_branch_names(monkeypatch):
    monkeypatch.setattr(preview, 'list_preview_branches', lambda: ['dev-20260811-1.9.1', 'dev-20260930-1.9.2', 'main', '1.9.1-test'])
    monkeypatch.setattr(preview, '_deployed_revision', lambda: {'branch': 'dev-20260930-1.9.2', 'sha': 'test-sha'})
    result = router.studio_versions()
    assert [r['version'] for r in result['versions']] == ['1.9.2', '1.9.1']
    assert result['deployed']['sha'] == 'test-sha'


def test_ai_not_configured_does_not_generate_fake_content(monkeypatch):
    monkeypatch.setattr(ai, 'get_settings', lambda: SimpleNamespace(deepseek_api_key=None))
    with pytest.raises(HTTPException) as error:
        ai.generate_task_content(ai.TaskContentInput(task_a='善意', task_b='善意'))
    assert error.value.status_code == 503


def test_ai_uses_both_daily_tasks_and_validates_all_four_fields(monkeypatch):
    monkeypatch.setattr(ai, 'get_settings', lambda: SimpleNamespace(deepseek_api_key='test-only'))
    content = {'post_a': 'A任务模拟内容', 'post_b': 'B任务模拟内容', 'comment_a_to_b': '回应B任务', 'comment_b_to_a': '回应A任务'}
    response = Mock(); response.json.return_value = {'choices': [{'message': {'content': json.dumps(content)}}]}
    sent = []
    monkeypatch.setattr(ai.httpx, 'post', lambda *args, **kw: sent.append(kw) or response)
    payload = ai.TaskContentInput(task_a='记录今天的小进步', task_b='回应朋友的善意')
    assert ai.generate_task_content(payload) == content
    prompt = sent[0]['json']['messages'][-1]['content']
    assert '小进步' in prompt and '善意' in prompt and 'test-only' not in prompt
    response.json.return_value = {'choices': [{'message': {'content': '{}'}}]}
    with pytest.raises(HTTPException) as error:
        ai.generate_task_content(payload)
    assert error.value.status_code == 502


def test_generated_post_body_drops_runtime_metadata_prefix(monkeypatch):
    monkeypatch.setattr(ai, 'get_settings', lambda: SimpleNamespace(deepseek_api_key='test-only'))
    text = '2026-11-04 08:57:50 [自动化测试] 测试模拟：今天把发现的小错误及时改正。'
    result = {key:text for key in ['post_a','post_b','comment_a_to_b','comment_b_to_a']}
    response = Mock();response.json.return_value = {'choices':[{'message':{'content':json.dumps(result)}}]}
    monkeypatch.setattr(ai.httpx, 'post', lambda *args, **kwargs: response)
    assert set(ai.generate_task_content(ai.TaskContentInput(task_a='小错误',task_b='小错误')).values()) == {'今天把发现的小错误及时改正。'}
