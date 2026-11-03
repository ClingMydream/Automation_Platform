import importlib.util
from pathlib import Path
import pytest

pytest.importorskip('playwright.sync_api', reason='Requires the UI runner test environment')
path = Path(__file__).resolve().parents[2] / 'deploy/ui-runner/studio_flows.py'
spec = importlib.util.spec_from_file_location('watering_test_flows', path)
flows = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flows)


def test_successful_watering_branch():
    assert flows.watering_outcome({'success': True, 'code': 200,
        'data': {'success': True, 'message': '浇水成功！'}})[0] == 'watered'


@pytest.mark.parametrize('body', [
    {'success': True, 'code': 200, 'data': {'success': False, 'error': '24小时内您已对该用户浇过水，将于21小时后可浇水'}},
    {'success': False, 'code': 400, 'message': '24小时内已经浇过水了'},
])
def test_already_watered_branch_is_passed(body):
    assert flows.watering_outcome(body)[0] == 'cooldown'


@pytest.mark.parametrize('body,http_ok', [
    ({'success': False, 'code': 401, 'message': '未登录'}, True),
    ({'success': True, 'data': {'success': False, 'error': '余额不足'}}, True),
    ({'success': False, 'message': '服务器异常'}, False),
    ({'success': True, 'data': None}, True),
])
def test_other_failures_are_not_converted_to_success(body, http_ok):
    with pytest.raises(AssertionError):
        flows.watering_outcome(body, http_ok)
