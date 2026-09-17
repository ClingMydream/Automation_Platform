"""Reviewed reference code for every mastery-course rewrite and exercise."""

REFERENCE_CODE = {
    "python-runtime": {
        "rewrite": 'print("我正在学习请求和响应")',
        "exercise": 'print("岗位：测试工程师")\nprint("目标：掌握 Python 接口自动化")',
    },
    "terminal-path": {
        "rewrite": 'mkdir scripts\nMove-Item .\\hello.py .\\scripts\\hello.py\npython .\\scripts\\hello.py',
        "exercise": 'Get-Location\ndir\nTest-Path .\\hello.py\npython .\\hello.py',
    },
    "venv-pip": {
        "rewrite": 'requests\npytest',
        "exercise": '.\\.venv\\Scripts\\Activate.ps1\npython -m pytest --version',
    },
    "request-journey": {
        "rewrite": '页面 → DNS → TCP → TLS → HTTP → 网关 → 后端 → 数据库 → 后端 → 响应 → 页面',
        "exercise": 'GET /booker/booking HTTP/1.1\nHost: 111.229.178.141\nAccept: application/json',
    },
    "url-dns": {
        "rewrite": 'url = "https://api.example.com/posts?page=2"\nprint(url)',
        "exercise": 'from urllib.parse import urlparse\nu = urlparse("http://111.229.178.141/booker/booking/1")\nprint(u.scheme, u.hostname, u.port, u.path)',
    },
    "tcp-tls": {
        "rewrite": 'Test-NetConnection 111.229.178.141 -Port 80\n# 端口可达后返回 401，说明 TCP 已连接，应检查鉴权',
        "exercise": 'Resolve-DnsName example.com\nTest-NetConnection example.com -Port 443\ncurl.exe -Iv https://example.com\ncurl.exe -i https://example.com/api',
    },
    "http-anatomy": {
        "rewrite": 'headers = {"Accept": "application/json", "X-Student": "cling"}\nresponse = requests.get(url, params={"page": 1}, headers=headers, timeout=10)',
        "exercise": 'request_record = {\n    "method": "GET", "url": url, "headers": headers,\n    "body": None, "status": response.status_code,\n    "response": response.json(),\n}',
    },
    "methods-idempotency": {
        "rewrite": 'requests.put(url, json={"firstname": "Li", "lastname": "Ming", "totalprice": 100, "depositpaid": True, "bookingdates": dates, "additionalneeds": "None"})\nrequests.patch(url, json={"lastname": "Ming"})',
        "exercise": '# 发帖通常不能盲目重试：重复 POST 可能创建两篇帖子\nrequests.post(f"{base_url}/posts", json={"content": "测试内容"}, timeout=10)',
    },
    "auth-content": {
        "rewrite": 'without_auth = requests.get(url, timeout=10)\nwith_auth = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=10)',
        "exercise": 'requests.post(url, json={"name": "测试"})\nrequests.post(url, data={"name": "测试"})\nrequests.post(url, files={"file": open("demo.txt", "rb")})',
    },
    "status-timeout-debug": {
        "rewrite": 'response = requests.get(url, timeout=(1, 30))  # 连接最多 1 秒，读取最多 30 秒',
        "exercise": 'checks = ["DNS: Resolve-DnsName", "连接: Test-NetConnection -Port 443", "TLS: curl -Iv", "401: 检查凭证", "404: 检查路径", "500: 保存 request-id 和响应", "读取超时: 检查服务耗时"]\nfor item in checks:\n    print(item)',
    },
    "python-values": {
        "rewrite": 'api_path = "/booking/1"\nexpected_status = 200\nneeds_auth = False',
        "exercise": 'actual_status = 404\nexpected_status = 200\nprint(actual_status == expected_status)  # False',
    },
    "collections-json": {
        "rewrite": 'bookings = [{"bookingid": 1, "guest": "张三"}, {"bookingid": 2, "guest": "李四"}]\nprint(bookings[1]["guest"])',
        "exercise": 'booking = {"firstname": "Jim", "lastname": "Brown"}\nfirstname = booking["firstname"]\nprint(firstname, isinstance(firstname, str))',
    },
    "conditions-loops": {
        "rewrite": 'status_codes = [200, 200, 404, 500]\nsuccess = sum(1 for code in status_codes if code < 400)\nfailed = sum(1 for code in status_codes if code >= 400)\nprint(success, failed)',
        "exercise": 'bookings = [{"bookingid": 5}, {"bookingid": 11}, {"bookingid": 20}]\nfor booking in bookings:\n    if booking["bookingid"] > 10:\n        print(booking)',
    },
    "functions": {
        "rewrite": 'def build_url(base_url, booking_id, timeout=10):\n    return f"{base_url}/booking/{booking_id}", timeout\n\nurl, timeout = build_url("http://111.229.178.141/booker", 2)',
        "exercise": 'def build_headers(token):\n    if token:\n        return {"Authorization": f"Bearer {token}"}\n    return {}\n\nprint(build_headers("test-token"))\nprint(build_headers(None))',
    },
    "modules-classes": {
        "rewrite": 'class ApiClient:\n    def __init__(self, base_url, timeout=10):\n        self.base_url = base_url\n        self.timeout = timeout',
        "exercise": 'class ApiClient:\n    def __init__(self, base_url, headers=None):\n        self.base_url = base_url\n        self.headers = {"Accept": "application/json"}\n        if headers:\n            self.headers.update(headers)',
    },
    "exceptions-logging": {
        "rewrite": 'logging.basicConfig(filename="error.log", level=logging.ERROR)\nlogging.exception("请求失败")',
        "exercise": 'try:\n    response = requests.get(url, timeout=3)\nexcept requests.Timeout:\n    print("读取超时：检查服务耗时和 timeout")\nexcept requests.ConnectionError:\n    print("连接失败：检查域名、端口和网络")',
    },
    "network-to-curl": {
        "rewrite": 'curl.exe "http://111.229.178.141/booker/booking/1" -H "Accept: application/json"',
        "exercise": 'curl.exe "https://example.com/api/posts?page=1" -H "Accept: application/json"',
    },
    "requests-get": {
        "rewrite": 'assert response.status_code == 200, f"期望 200，实际 {response.status_code}，响应：{response.text[:200]}"',
        "exercise": 'response = requests.get(f"{base_url}/booking/1", timeout=10)\nassert response.status_code == 200\ndata = response.json()\nassert isinstance(data, dict)\nassert "firstname" in data',
    },
    "requests-auth-body": {
        "rewrite": 'bad = requests.post(url, json={"firstname": ""}, timeout=10)\nprint(bad.status_code, bad.text)\ngood = requests.post(url, json=valid_payload, timeout=10)',
        "exercise": 'headers = {"Cookie": f"token={token}"}\nresponse = requests.delete(f"{base_url}/booking/{booking_id}", headers=headers, timeout=10)\nassert response.status_code == 201',
    },
    "first-pytest": {
        "rewrite": 'def test_booking_list_is_array():\n    response = requests.get(f"{BASE_URL}/booking", timeout=10)\n    assert response.status_code == 200\n    assert isinstance(response.json(), list)',
        "exercise": 'def test_unknown_booking_returns_404():\n    response = requests.get(f"{BASE_URL}/booking/999999999", timeout=10)\n    assert response.status_code == 404',
    },
    "scenario-parametrize": {
        "rewrite": '@pytest.mark.parametrize("booking_id", ["abc", -1, 999999999])\ndef test_invalid_booking_id(booking_id):\n    response = requests.get(f"{BASE_URL}/booking/{booking_id}", timeout=10)\n    assert response.status_code in (400, 404)',
        "exercise": '@pytest.mark.parametrize("page,size", [(1, 10), (0, 10), (1, 1), (1, 100), (1, 0)])\ndef test_pagination(page, size):\n    response = requests.get(URL, params={"page": page, "size": size}, timeout=10)\n    assert response.status_code in (200, 400)',
    },
    "fixture-cleanup": {
        "rewrite": '@pytest.fixture\ndef created_booking(client):\n    booking_id = client.create_booking(payload).json()["bookingid"]\n    yield booking_id\n    client.delete_booking(booking_id)',
        "exercise": 'def test_cleanup_runs_on_failure(created_booking, client):\n    booking_id = created_booking\n    try:\n        assert client.get_booking(booking_id).status_code == 200\n        assert False, "模拟用例失败"\n    finally:\n        # 真正清理由 fixture 的 yield 后代码完成\n        pass',
    },
    "framework-layers": {
        "rewrite": 'BASE_URL = "http://111.229.178.141/booker"  # config\nclass HttpClient: ...  # 通用请求\nclass BookerClient: ...  # create_booking 等业务方法\ndef test_create_booking(): ...  # 数据和断言',
        "exercise": 'test_create_booking → BookerClient.create_booking → HttpClient.request → Restful Booker 服务',
    },
    "http-client": {
        "rewrite": 'merged = {**self.session.headers, **kwargs.pop("headers", {})}\nreturn self.session.request(method, url, headers=merged, **kwargs)',
        "exercise": 'def patch(self, path, **kwargs):\n    return self.request("PATCH", path, **kwargs)',
    },
    "business-client-refactor": {
        "rewrite": 'response = booker_client.list_bookings()\nassert response.status_code == 200',
        "exercise": 'def list_bookings(self, **params):\n    return self.get("/booking", params=params)\n\ndef partial_update_booking(self, booking_id, payload, token):\n    return self.patch(f"/booking/{booking_id}", json=payload, headers={"Cookie": f"token={token}"})',
    },
    "hotel-observe": {
        "rewrite": 'changed_payload = {**payload, "bookingdates": {"checkin": "2026-10-01", "checkout": "2026-10-03"}}',
        "exercise": 'interfaces = [\n    ("查看房间", "GET", "/booking", None, 200),\n    ("创建预约", "POST", "/booking", "预约 JSON", 200),\n    ("查看预约", "GET", "/booking/{id}", None, 200),\n]',
    },
    "hotel-crud": {
        "rewrite": 'booking_id = client.create_booking(payload).json()["bookingid"]\ntry:\n    assert client.update_booking(booking_id, bad_payload, token).status_code >= 400\nfinally:\n    client.delete_booking(booking_id, token)',
        "exercise": 'booking_id = client.create_booking(payload).json()["bookingid"]\nassert client.get_booking(booking_id).status_code == 200\nassert client.update_booking(booking_id, updated, token).status_code == 200\nassert client.delete_booking(booking_id, token).status_code == 201\nassert client.get_booking(booking_id).status_code == 404',
    },
    "hotel-regression": {
        "rewrite": 'python -m venv .venv\n.\\.venv\\Scripts\\Activate.ps1\npython -m pip install -r requirements.txt\npytest -v',
        "exercise": '项目分层：tests → business client → http client → server\n切换环境：通过环境变量读取 BASE_URL\n定位失败：先看用例断言，再看请求日志、状态码和响应',
    },
    "emote-readonly-map": {
        "rewrite": 'endpoints = [{"name": "帖子列表", "auth": True, "page": "原野", "key": "data", "readonly": True}]',
        "exercise": 'curl.exe "https://example.com/api/posts?page=1&size=10" -H "Accept: application/json"\ncurl.exe "https://example.com/api/profile" -H "Authorization: Bearer <运行时Token>"',
    },
    "emote-token-pagination": {
        "rewrite": '@pytest.mark.parametrize("page", [1, 2])\ndef test_post_pages(page):\n    response = client.get_posts(page=page, size=10)\n    assert response.status_code == 200\n    assert isinstance(response.json()["data"], list)',
        "exercise": '@pytest.mark.parametrize("page,size", [(0, 10), (1, 0), (1, 101)])\ndef test_pagination_boundaries(page, size):\n    response = client.get_posts(page=page, size=size)\n    assert response.status_code in (200, 400, 422)',
    },
    "emote-regression-evidence": {
        "rewrite": 'safe_headers = {k: v for k, v in response.request.headers.items() if k.lower() not in {"authorization", "cookie"}}\nprint(safe_headers)',
        "exercise": 'def test_emote_readonly_regression(client):\n    response = client.get_posts(page=1, size=10)\n    assert response.status_code == 200\n    assert response.headers.get("Content-Type", "").startswith("application/json")\n    assert response.headers.get("request-id") or response.headers.get("x-request-id")\n    assert isinstance(response.json(), dict)',
    },
}
