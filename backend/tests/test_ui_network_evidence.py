import importlib.util
from pathlib import Path
from types import SimpleNamespace

path = Path(__file__).resolve().parents[2] / 'deploy/ui-runner/network_evidence.py'
spec = importlib.util.spec_from_file_location('network_evidence', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_business_failure_is_captured_and_secrets_are_redacted():
    recorder = module.NetworkEvidence(['private-value'])
    recorder.case_id, recorder.step = 3, '保存资料'
    request = SimpleNamespace(resource_type='fetch', method='POST',
        url='https://user:pass@example.org/api/profile?token=private-value&mode=edit',
        post_data='{"nickname":"demo","password":"private-value"}')
    recorder.request(request)
    response = SimpleNamespace(request=request, status=200,
        headers={'content-type':'application/json'},
        json=lambda: {'success':False,'code':409,'message':'duplicate','token':'private-value'})
    recorder.response(response)
    row = recorder.for_case(3)[0]
    assert row['category'] == 'business'
    assert row['response_body']['code'] == 409
    assert row['request_body']['nickname'] == 'demo'
    assert 'private-value' not in str(row) and 'user:pass' not in str(row)
    assert recorder.for_case(4) == []


def test_success_is_ignored_and_network_failure_keeps_parameters():
    recorder = module.NetworkEvidence()
    request = SimpleNamespace(resource_type='xhr', method='GET',
        url='https://example.org/api/items?page=2',post_data=None,failure='net::ERR_TIMED_OUT')
    recorder.request(request)
    recorder.response(SimpleNamespace(request=request,status=200,headers={},json=lambda: {}))
    assert recorder.rows == []
    recorder.request(request)
    recorder.failed(request)
    assert recorder.rows[0]['query'] == {'page':'2'}
    assert recorder.rows[0]['category'] == 'network'


def test_form_credentials_and_unknown_payloads_are_not_exposed():
    assert module.decode_body('password=secret&name=demo')['password'] == '[redacted]'
    assert module.decode_body('raw sensitive text') == '[non-JSON body omitted]'
