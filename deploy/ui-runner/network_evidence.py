"""Bounded, step-scoped browser request evidence. Never stores auth headers."""
import json
import re
import time
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

PRIVATE = re.compile(r'password|token|cookie|authorization|secret|credential|phone|mobile|email|verification|otp|api[_-]?key|access[_-]?key', re.I)


def scrub(value, secrets=()):
    if isinstance(value, dict):
        return {k: '[redacted]' if PRIVATE.search(str(k)) else scrub(v, secrets) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub(v, secrets) for v in value[:100]]
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(str(secret), '[redacted]')
        return value[:12000]
    return value


def safe_url(url, secrets=()):
    p = urlsplit(url)
    query = [(k, '[redacted]' if PRIVATE.search(k) or k.lower()=='code' else scrub(v, secrets)) for k, v in parse_qsl(p.query, keep_blank_values=True)]
    return urlunsplit((p.scheme, p.netloc.rsplit('@', 1)[-1], scrub(p.path, secrets), urlencode(query), ''))


def decode_body(raw, secrets=()):
    if not raw:
        return None
    try:
        value=json.loads(raw)
        if isinstance(value,dict) and 'code' in value:
            value['code']='[redacted]'
        return scrub(value, secrets)
    except (ValueError, TypeError):
        if '=' in raw:
            return scrub(dict(parse_qsl(raw, keep_blank_values=True)), secrets)
        # Unknown text or multipart data may contain credentials; omit its body.
        return '[non-JSON body omitted]'


class NetworkEvidence:
    def __init__(self, secrets=(), limit=80):
        self.secrets, self.limit = tuple(secrets), limit
        self.pending, self.rows = {}, []
        self.case_id, self.step = None, ''

    def bind(self, page):
        page.on('request', self.request)
        page.on('response', self.response)
        page.on('requestfailed', self.failed)

    def request(self, request):
        if request.resource_type not in ('fetch', 'xhr'):
            return
        if len(self.pending) >= self.limit:
            self.pending.pop(next(iter(self.pending)))
        self.pending[id(request)] = {
            'case_id': self.case_id, 'step': self.step, 'method': request.method,
            'url': safe_url(request.url, self.secrets),
            'query': decode_body(urlsplit(request.url).query, self.secrets),
            'request_body': decode_body(request.post_data, self.secrets),
            '_start': time.monotonic(),
        }

    def response(self, response):
        row = self.pending.pop(id(response.request), None)
        if not row:
            return
        body = None
        try:
            if 'json' in response.headers.get('content-type', ''):
                body = response.json()
        except Exception:
            pass
        business_error = isinstance(body, dict) and (body.get('success') is False or
            isinstance(body.get('data'),dict) and body['data'].get('success') is False)
        if response.status >= 400 or business_error:
            row.update(status=response.status, response_body=scrub(body, self.secrets),
                       category='business' if business_error and response.status < 400 else 'http')
            self._append(row)

    def failed(self, request):
        row = self.pending.pop(id(request), None)
        if row:
            row.update(category='network', error=scrub(request.failure or 'network error', self.secrets))
            self._append(row)

    def _append(self, row):
        row['duration_ms'] = round((time.monotonic() - row.pop('_start')) * 1000)
        self.rows.append(row)
        self.rows = self.rows[-self.limit:]

    def for_case(self, case_id):
        return [r for r in self.rows if r['case_id'] == case_id]
