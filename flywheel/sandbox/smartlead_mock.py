"""Local Smartlead API sandbox. Serves the documented payload shapes over real HTTP so the adapter can be
exercised end to end without an account. Logs every request (Postman-console style), requires the api_key
query param, paginates leads, can inject 429s, and answers 405 to anything that is not a GET.

  uv run sandbox/smartlead_mock.py                       # http://127.0.0.1:8787/api/v1
  uv run sandbox/smartlead_mock.py --rate-limit-every 5  # every 5th request is a 429, to watch the retry

Payloads come from tests/fixtures/smartlead/*.json (built from the public docs; values are invented).
"""
import argparse
import json
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "smartlead"
PREFIX = "/api/v1"


def _load(name):
    p = FIXTURES / name
    return json.loads(p.read_text()) if p.exists() else None


class Handler(BaseHTTPRequestHandler):
    server_version = "SmartleadSandbox/0.1"

    def log_message(self, *_):           # silence default stderr noise; we log JSON lines ourselves
        pass

    def _log(self, status, note=""):
        q = {k: ("***" if k == "api_key" else v) for k, v in self.query.items()}
        entry = {"ts": round(time.time(), 3), "method": self.command, "path": self.path_only, "query": q, "status": status}
        if note:
            entry["note"] = note
        self.server.log.append(entry)
        if self.server.echo:
            print(json.dumps(entry), flush=True)

    def _send(self, status, body, ctype="application/json"):
        data = (json.dumps(body) if ctype == "application/json" else body).encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _parse(self):
        u = urlsplit(self.path)
        self.path_only = u.path
        self.query = {k: v[-1] for k, v in parse_qs(u.query).items()}

    def do_GET(self):
        self._parse()
        self.server.count += 1
        if self.server.rate_limit_every and self.server.count % self.server.rate_limit_every == 0:
            self._log(429, "injected rate limit")
            return self._send(429, "Too many requests", "text/plain")
        key = self.query.get("api_key")
        if not key or (self.server.api_key and key != self.server.api_key):
            self._log(401)
            return self._send(401, {"message": "Invalid or missing api_key"})
        path = self.path_only[len(PREFIX):] if self.path_only.startswith(PREFIX) else None
        if path is None:
            self._log(404); return self._send(404, {"message": "not found"})
        m_camp = re.fullmatch(r"/campaigns/(\d+)/(sequences|sequence-analytics|leads)", path)
        if path == "/campaigns/":
            body = _load("campaigns.json")
        elif path == "/leads/fetch-categories":
            body = _load("categories.json")
        elif m_camp:
            cid, kind = m_camp.groups()
            if kind == "sequences":
                body = _load(f"sequences_{cid}.json")
            elif kind == "sequence-analytics":
                if not (self.query.get("start_date") and self.query.get("end_date")):
                    self._log(400, "start_date/end_date required"); return self._send(400, {"message": "start_date and end_date are required"})
                body = _load(f"sequence_analytics_{cid}.json")
            else:
                full = _load(f"leads_{cid}.json")
                if full is None:
                    self._log(404); return self._send(404, {"message": "campaign not found"})
                off, lim = int(self.query.get("offset", 0)), min(int(self.query.get("limit", 100)), 100)
                rows = full.get("data", [])
                body = {"total_leads": str(len(rows)), "offset": off, "limit": lim, "data": rows[off:off + lim]}
        else:
            body = None
        if body is None:
            self._log(404); return self._send(404, {"message": "not found"})
        self._log(200)
        self._send(200, body)

    def _refuse(self):
        self._parse()
        self.server.count += 1
        self._log(405, "WRITE ATTEMPT refused by sandbox")
        self._send(405, {"message": "sandbox is read-only: the flywheel must never send this"})

    do_POST = do_PUT = do_PATCH = do_DELETE = _refuse


def serve(port=8787, api_key=None, rate_limit_every=0, echo=True):
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    srv.log, srv.count, srv.api_key, srv.rate_limit_every, srv.echo = [], 0, api_key, rate_limit_every, echo
    srv.base_url = f"http://127.0.0.1:{srv.server_address[1]}{PREFIX}"
    return srv


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--api-key", help="require this exact key (default: any non-empty api_key)")
    ap.add_argument("--rate-limit-every", type=int, default=0, metavar="N")
    a = ap.parse_args(argv)
    srv = serve(a.port, a.api_key, a.rate_limit_every)
    print(f"Smartlead sandbox at {srv.base_url}  (Ctrl-C to stop)\n"
          f"  export SMARTLEAD_BASE_URL={srv.base_url} SMARTLEAD_API_KEY=sandbox", file=sys.stderr)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
