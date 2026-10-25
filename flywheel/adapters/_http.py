"""Allowlisted HTTP client. This is the guard that keeps the flywheel from ever touching a live campaign.

Each adapter declares ALLOW = {(method, path_template), ...}. A request whose (method, template) is not in
that set raises before any network I/O. --dry-run logs the call and returns an empty body.
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request


class NotAllowed(Exception):
    pass


class Client:
    def __init__(self, tool, base_url, allow, headers=None, query=None, dry_run=False, min_interval=0.0):
        self.tool, self.base_url, self.allow = tool, base_url.rstrip("/"), set(allow)
        self.headers = {"Accept": "application/json", **(headers or {})}
        self.query = dict(query or {})          # e.g. Smartlead's api_key query param
        self.dry_run, self.min_interval = dry_run, min_interval
        self.calls, self._last = [], 0.0

    def get(self, template, params=None, **path_vars):
        return self._request("GET", template, params=params, path_vars=path_vars)

    def post(self, template, body=None, params=None, **path_vars):
        return self._request("POST", template, params=params, body=body, path_vars=path_vars)

    def _request(self, method, template, params=None, body=None, path_vars=None):
        if (method, template) not in self.allow:
            raise NotAllowed(f"{self.tool}: {method} {template} is not an allowlisted read endpoint")
        path = template.format(**{k: urllib.parse.quote(str(v), safe="") for k, v in (path_vars or {}).items()})
        q = {**self.query, **{k: v for k, v in (params or {}).items() if v is not None}}
        url = self.base_url + path + ("?" + urllib.parse.urlencode(q, doseq=True) if q else "")
        self.calls.append((method, url))
        if self.dry_run:
            print(f"[dry-run] {method} {_redact(url)}")
            return {}
        return self._send(method, url, body)

    def _send(self, method, url, body, retries=3):
        data = json.dumps(body).encode() if body is not None else None
        headers = {**self.headers, **({"Content-Type": "application/json"} if data else {})}
        for attempt in range(retries):
            wait = self.min_interval - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    self._last = time.monotonic()
                    raw = r.read()
                    return json.loads(raw) if raw else {}
            except urllib.error.HTTPError as e:
                self._last = time.monotonic()
                if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                    time.sleep(2 ** attempt * 5)   # ponytail: fixed backoff; none of the 4 APIs send Retry-After
                    continue
                raise
        return {}


def _redact(url):
    return urllib.parse.urlunsplit(urllib.parse.urlsplit(url)._replace(
        query="&".join(p if not p.lower().startswith("api_key=") else "api_key=***"
                       for p in urllib.parse.urlsplit(url).query.split("&") if p)))
