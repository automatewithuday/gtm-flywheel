"""Shared helpers for all Plays: env, disk cache, spend ledger, HTTP/CLI wrappers, CSV, dedupe, suppression."""
import argparse, csv, hashlib, json, math, os, re, subprocess, sys, tempfile, time
from collections import defaultdict
from datetime import date
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / ".cache" / "calls.jsonl"


# ---- env ----
def load_env():
    # Vendored into GTM-Skills: the repo .env lives several folders up, so search upward from the working directory first.
    from dotenv import find_dotenv
    load_dotenv(find_dotenv(usecwd=True) or ROOT / ".env")


def env(name, required=True):
    load_env()  # idempotent; lets scripts that forget load_env() still read .env
    v = os.environ.get(name, "")
    if required and not v:
        raise RuntimeError(f"{name} is not set (put it in .env; see .env.example)")
    return v or None


# ---- disk cache ----
def _sha(key):
    return hashlib.sha256(key.encode()).hexdigest()


def cached(key, fn, max_age_days=None):
    """Return fn() once per key; replays from .cache/calls.jsonl at $0. Stale entries (older than max_age_days) refetch."""
    k, hit = _sha(key), None
    if CACHE_PATH.exists():
        for line in CACHE_PATH.read_text().splitlines():  # ponytail: full-file scan per call, fine to ~100k entries
            try:
                e = json.loads(line)
            except ValueError:
                continue  # truncated line from a killed run
            if e["k"] == k:
                hit = e  # last write wins
    if hit and (max_age_days is None or time.time() - hit["t"] <= max_age_days * 86400):
        return hit["v"]
    v = fn()
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CACHE_PATH.open("a") as f:
        f.write(json.dumps({"k": k, "t": time.time(), "v": v}) + "\n")
    return v


# ---- spend ledger ----
SPENT = {"usd": 0.0, "calls": [], "cap": None, "dry_run": False}


class SpendCapExceeded(RuntimeError):
    pass


def set_cap(usd):
    SPENT["cap"] = usd


def set_dry_run(flag):
    SPENT["dry_run"] = bool(flag)


def spend(usd, label):
    """Record a call. Raises before the call that would push (real + planned) spend over the cap."""
    planned = sum(c["usd"] for c in SPENT["calls"] if c["planned"])
    projected = SPENT["usd"] + planned + usd
    if SPENT["cap"] is not None and projected > SPENT["cap"]:
        raise SpendCapExceeded(f"{label}: projected ${projected:.4f} would exceed cap ${SPENT['cap']:.4f}; aborting before the call")
    dry = SPENT["dry_run"]
    SPENT["calls"].append({"label": label, "usd": usd, "planned": dry})
    if not dry:
        SPENT["usd"] += usd


def report():
    by = defaultdict(float)
    for c in SPENT["calls"]:
        by[c["label"]] += c["usd"]
    planned = sum(c["usd"] for c in SPENT["calls"] if c["planned"])
    head = f"planned ${planned:.4f} (dry-run, nothing spent)" if SPENT["dry_run"] else f"spent ${SPENT['usd']:.4f}"
    return head + f" over {len(SPENT['calls'])} calls; by label: " + ", ".join(f"{k} ${v:.4f}" for k, v in sorted(by.items()))


def _call(key, usd, label, fn, max_age_days=None):
    """Common path for every paid wrapper: dry-run records and returns None; else cached, spending only on a miss."""
    if SPENT["dry_run"]:
        spend(usd, label)  # ponytail: dry-run counts a cached call at full price (conservative)
        return None

    def run():
        spend(usd, label)
        try:
            return fn()
        except Exception:
            SPENT["usd"] -= usd  # the call failed: nothing was billed, so the ledger must not count it
            SPENT["calls"].pop()
            raise

    return cached(key, run, max_age_days)


# ---- API wrappers ----
def _json_key(*a):
    return json.dumps(a, sort_keys=True, default=str)


def getleads(method, path, json=None, params=None, usd=0.0, label="getleads"):
    # Verified against https://app.getleads.io/openapi.json: paths under /api/v1, Bearer auth accepted.
    def fn():
        r = httpx.request(method, "https://app.getleads.io" + path, json=json, params=params, timeout=120,
                          headers={"Authorization": f"Bearer {env('GETLEADS_API_KEY')}"})
        r.raise_for_status()
        return r.json()

    return _call(_json_key("getleads", method, path, json, params), usd, label, fn)


def apify(actor, run_input, max_usd):
    """Run an actor synchronously and return dataset items. actor like 'user~name'. Apify enforces maxTotalChargeUsd."""
    def fn():
        # token as a query param: verified live 21 Oct 2026 (a Bearer header got 403 on run-sync-get-dataset-items)
        r = httpx.post(f"https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items",
                       params={"maxTotalChargeUsd": max_usd, "token": env("APIFY_API_TOKEN")}, json=run_input, timeout=330)
        if r.status_code >= 400:  # never let httpx's URL (which carries the token) into the exception text
            raise RuntimeError(f"apify {actor}: HTTP {r.status_code}: {r.text[:300]}")
        return r.json()

    return _call(_json_key("apify", actor, run_input, max_usd), max_usd, f"apify:{actor}", fn)


def _deepline(argv):
    p = subprocess.run(argv, capture_output=True, text=True)
    if p.returncode:
        cause = p.stderr.strip()[-300:]
        try:  # `tools execute` prints a JSON envelope with the real cause on stdout; stderr is progress noise
            err = (json.loads(p.stdout) or {}).get("error")
            if err:
                cause = (err.get("message") if isinstance(err, dict) else str(err))[:300]
        except ValueError:
            pass
        m = re.search(r"play/[\w./-]+/run/[\w-]+", p.stderr + p.stdout)
        if m:  # the CLI's stderr hides the cause; `runs get` has it (billing cap, provider error, ...)
            g = subprocess.run(["deepline", "runs", "get", m.group(0)], capture_output=True, text=True)
            err = next((ln.strip() for ln in g.stdout.splitlines() if ln.strip().startswith("error:")), "")
            cause = f"{err or cause}  (details: deepline runs get {m.group(0)})"
        raise RuntimeError(f"{' '.join(argv[:4])} failed ({p.returncode}): {cause}")
    return json.loads(p.stdout)


DEEPLINE_CREDIT_USD = 0.10  # EDIT ME: USD per Deepline credit on your plan; used to turn the USD estimate into a hard --max-credits


def deepline_play(play_id, *, csv_path=None, input=None, usd_estimate=0.0):
    # argv from `deepline plays run --help` (v0.3.397): --input <json|@file>, --json, --max-credits. csv goes in the play input as "csv".
    payload = dict(input or {})
    if csv_path:
        payload["csv"] = str(csv_path)
    argv = ["deepline", "plays", "run", play_id, "--input", json.dumps(payload), "--json"]
    # Hard cap enforced by Deepline itself: the REMAINING ledger budget when --cap-usd is set (the estimate is only a
    # forecast; real rows cost 1-5 credits each), else the estimate. Observed: 8 real rows burned 13 credits.
    budget = SPENT["cap"] - SPENT["usd"] if SPENT.get("cap") is not None else usd_estimate
    if budget > 0:
        argv += ["--max-credits", str(max(1, math.floor(round(budget / DEEPLINE_CREDIT_USD, 6))))]
    # cache on content, not on the temp path in argv
    ident = dict(payload)
    if csv_path:
        ident["csv"] = hashlib.sha256(Path(csv_path).read_bytes()).hexdigest()

    def export_rows(run_id, partial=False):
        with tempfile.TemporaryDirectory() as td:  # rows live in a dataset: `runs export` is free and returns every row
            out = Path(td) / "rows.json"
            _deepline(["deepline", "runs", "export", run_id, "--format", "json", "--out", str(out), "--json", "--allow-empty"])
            return {"run_id": run_id, "rows": json.loads(out.read_text()), "partial": partial}

    def run_and_export():
        try:
            env_ = _deepline(argv)  # `plays run --json` returns a run envelope (run.id, rowOutcomes, datasets), not the rows
        except RuntimeError as e:
            m = re.search(r"play/[\w./-]+/run/[\w-]+", str(e))
            if not m:
                raise
            # the run halted (usually Deepline's own --max-credits). Rows it finished are already paid for: salvage them.
            res = export_rows(m.group(0), partial=True)
            if not res["rows"]:
                raise
            print(f"WARN deepline: run halted ({str(e)[:120]}...); salvaged {len(res['rows'])} rows, unfinished ones stay misses", file=sys.stderr)
            return res
        run_id = (env_.get("run") or {}).get("id") if isinstance(env_, dict) else None
        if not run_id or not env_.get("datasets"):
            return env_
        return export_rows(run_id)

    return _call(_json_key("play-rows", play_id, ident), usd_estimate, f"deepline:{play_id}", run_and_export)


def deepline_action(action_id, params, usd_estimate, max_age_days=None):
    # No `deepline actions run` exists in 0.3.397; the equivalent is `deepline tools execute <id> --input <json> --json`.
    # Estimate-only cap (no per-call credit flag).
    argv = ["deepline", "tools", "execute", action_id, "--input", json.dumps(params), "--json"]
    out = _call(_json_key("action", argv), usd_estimate, f"deepline:{action_id}", lambda: _deepline(argv), max_age_days)
    # `tools execute --json` wraps the tool's payload in a job envelope {job_id, status: "completed", toolResponse: {rawV2, raw}}.
    # Return the payload so callers never mistake the job status for a verdict (observed: MillionVerifier result lives in rawV2.result).
    if isinstance(out, dict) and isinstance(out.get("toolResponse"), dict):
        tr = out["toolResponse"]
        return tr.get("rawV2") or tr.get("raw") or tr
    return out


# ---- CSV ----
def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fieldnames=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# ---- email status ----
STATUS = ("verified", "catch_all", "unknown", "not_found")
VERIFIER_MAP = {
    "valid": "verified", "ok": "verified", "deliverable": "verified", "verified": "verified", "catch_all": "catch_all", "valid_catch_all": "catch_all", "unknown": "unknown", "risky": "catch_all",
    **{k: "discard" for k in ("invalid", "undeliverable", "disposable", "spamtrap", "abuse", "do_not_mail")},
}


def normalize_status(raw):
    """Deepline email_status -> verified|catch_all|unknown|discard. Unmapped values become 'unknown' (never goes live)."""
    return VERIFIER_MAP.get(str(raw or "").strip().lower(), "unknown")


# ---- list hygiene ----
def dedupe(rows, keys):
    """First wins, case-insensitive. `keys` is ONE composite key (ALL listed columns must match). To dedupe on two key
    sets, call twice, e.g. dedupe(dedupe(rows, ["linkedin_url"]), ["first_name", "last_name", "company_domain"]).
    Rows with any blank key part are kept (they can't be identified)."""
    seen, out = set(), []
    for r in rows:
        k = tuple((r.get(c) or "").strip().lower() for c in keys)
        if all(k):
            if k in seen:
                continue
            seen.add(k)
        out.append(r)
    return out


_TRUE = {"1", "true", "yes", "y", "t"}
_OPEN_STAGES = {"open", "proposal", "negotiation"}
_FREEMAIL = {"gmail.com", "outlook.com", "hotmail.com", "yahoo.com", "icloud.com", "proton.me", "protonmail.com"}


def _li(u):
    return (u or "").strip().lower().split("?")[0].rstrip("/")


def suppress(rows, crm_rows, touched_days=14, today=None):
    """Return (kept, dropped). Drop a row matching (email | linkedin_url | domain) a CRM row that is an open opp,
    in a sequence, a customer, or touched within touched_days. Dropped rows get `suppress_reason`."""
    today = today or date.today()
    idx = {"email": {}, "li": {}, "domain": {}}
    for n, c in enumerate(crm_rows, 2):  # n = CSV line number (header is line 1)
        reasons = []
        if (c.get("stage") or "").strip().lower() in _OPEN_STAGES:
            reasons.append("open_opportunity")
        if (c.get("in_sequence") or "").strip().lower() in _TRUE:
            reasons.append("in_sequence")
        if (c.get("is_customer") or "").strip().lower() in _TRUE:
            reasons.append("customer")
        lt = (c.get("last_touched") or "").strip()[:10]
        try:
            age = (today - date.fromisoformat(lt)).days if lt else None
        except ValueError:
            who = c.get("email") or c.get("linkedin_url") or c.get("domain") or "?"
            raise SystemExit(f"CRM export line {n} ({who}): last_touched {lt!r} is not ISO YYYY-MM-DD")
        if age is not None and age <= touched_days:
            reasons.append(f"touched_within_{touched_days}d")
        if not reasons:
            continue
        email = (c.get("email") or "").strip().lower()
        dom = (c.get("domain") or email.split("@")[-1]).strip().lower()
        for table, val in (("email", email), ("li", _li(c.get("linkedin_url"))), ("domain", dom)):
            if val and not (table == "domain" and val in _FREEMAIL):
                idx[table].setdefault(val, reasons[0])  # ponytail: reports first reason only
    kept, dropped = [], []
    for r in rows:
        email = (r.get("email") or "").strip().lower()
        dom = (r.get("company_domain") or r.get("domain") or email.split("@")[-1]).strip().lower()
        why = idx["email"].get(email) or idx["li"].get(_li(r.get("linkedin_url"))) or idx["domain"].get(dom)
        (dropped if why else kept).append({**r, "suppress_reason": why} if why else r)
    return kept, dropped


def batches(rows, size):
    for i in range(0, len(rows), size):
        yield rows[i:i + size]


# ---- CLI ----
def cli_common(parser):
    parser.add_argument("--dry-run", action="store_true", help="print planned calls + cost estimate; spend nothing")
    parser.add_argument("--cap-usd", type=float, help="abort before any call that would exceed this total")
    parser.add_argument("--out", help="output path")
    parser.add_argument("--selftest", action="store_true", help="run offline self-test and print OK")
    return parser


def apply_cli(args):
    """Wire parsed cli_common flags into the ledger."""
    set_dry_run(args.dry_run)
    if args.cap_usd is not None:
        set_cap(args.cap_usd)


# ---- selftest ----
def _reset(cap=None, dry=False):
    SPENT.update(usd=0.0, calls=[], cap=cap, dry_run=dry)


def selftest():
    import tempfile
    global CACHE_PATH
    CACHE_PATH = Path(tempfile.mkdtemp()) / "calls.jsonl"

    # cache hit/miss/max_age
    n = []
    f = lambda: n.append(1) or len(n)
    assert cached("a", f) == 1 and cached("a", f) == 1 and len(n) == 1
    assert cached("b", f) == 2
    assert cached("a", f, max_age_days=1) == 1 and len(n) == 2  # fresh
    time.sleep(0.01)
    assert cached("a", f, max_age_days=0.0000001) == 3 and len(n) == 3  # stale -> refetch
    assert cached("a", f) == 3  # newest entry wins
    with CACHE_PATH.open("a") as fh:
        fh.write('{"k": "trunc\n')  # corrupt line must not break later hits
    assert cached("a", f) == 3 and cached("b", f) == 2 and len(n) == 3

    # ledger: cap at the right projection
    _reset(cap=1.0)
    spend(0.6, "x"); spend(0.4, "x")  # exactly at cap is allowed
    try:
        spend(0.01, "y"); raise AssertionError("cap not enforced")
    except SpendCapExceeded as e:
        assert "y" in str(e) and "1.01" in str(e) and "1.00" in str(e), str(e)
    assert abs(SPENT["usd"] - 1.0) < 1e-9 and "x $1.0000" in report()
    # dry-run: planned, not counted, cap on projection, wrappers return None
    _reset(cap=1.0, dry=True)
    assert getleads("POST", "/api/v1/enrich/from-linkedin", json={}, usd=0.4, label="gl") is None
    assert apify("u~a", {}, 0.4) is None
    assert SPENT["usd"] == 0.0 and len(SPENT["calls"]) == 2 and all(c["planned"] for c in SPENT["calls"])
    try:
        deepline_action("some_action", {}, 0.4); raise AssertionError("dry-run cap not enforced")
    except SpendCapExceeded:
        pass
    d0 = Path(tempfile.mkdtemp())
    (d0 / "x.csv").write_text("a\n1\n")
    assert deepline_play("p", csv_path=d0 / "x.csv", usd_estimate=0.1) is None and "planned" in report()
    # live path: spends only on cache miss
    _reset(cap=None)
    k = []
    assert _call("live", 0.5, "t", lambda: k.append(1) or "r") == "r" and _call("live", 0.5, "t", lambda: 1 / 0) == "r"
    assert SPENT["usd"] == 0.5 and k == [1]
    # deepline_play: same CSV bytes at two paths -> one call; --max-credits = floor(remaining budget / DEEPLINE_CREDIT_USD),
    # or floor(estimate / price) when no cap is set
    global _deepline
    real_dl, argvs = _deepline, []
    _deepline = lambda argv: argvs.append(argv) or {"rows": []}
    try:
        _reset()
        d1, d2 = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp())
        for d in (d1, d2):
            (d / "in.csv").write_text("a\n1\n")
        deepline_play("pp", csv_path=d1 / "in.csv", usd_estimate=0.25); deepline_play("pp", csv_path=d2 / "in.csv", usd_estimate=0.25)
        assert len(argvs) == 1 and argvs[0][argvs[0].index("--max-credits") + 1] == "2", argvs  # cache hit across paths; floor(2.5)
        (d2 / "in.csv").write_text("a\n2\n"); deepline_play("pp", csv_path=d2 / "in.csv", usd_estimate=0.25)
        assert len(argvs) == 2  # different content -> miss
        deepline_play("free", input={"k": 1}); assert "--max-credits" not in argvs[-1]
        _reset(cap=2.0); spend(0.5, "x")  # with a cap, the hard limit is the REMAINING budget: (2.0-0.5)/0.10 = 15 credits
        deepline_play("pp", input={"k": 2}, usd_estimate=0.25); assert argvs[-1][argvs[-1].index("--max-credits") + 1] == "15", argvs[-1]
        # deepline_action unwraps the job envelope: the caller sees the tool payload, never status="completed"
        _deepline = lambda argv: {"job_id": "j", "status": "completed", "toolResponse": {"rawV2": {"result": "ok"}, "raw": {"result": "ok"}}}
        assert deepline_action("mv", {"email": "a@b.c"}, 0.01) == {"result": "ok"}
        _deepline = lambda argv: {"plain": 1}
        assert deepline_action("other", {"k": 1}, 0.01) == {"plain": 1}
    finally:
        _deepline = real_dl
    _reset()

    # normalize_status
    for raw, want in [("valid", "verified"), ("catch_all", "catch_all"), ("valid_catch_all", "catch_all"), ("unknown", "unknown"),
                      ("invalid", "discard"), ("disposable", "discard"), ("spamtrap", "discard"), ("abuse", "discard"),
                      ("do_not_mail", "discard"), ("VALID", "verified"), ("VERIFIED", "verified"), ("ok", "verified"), ("deliverable", "verified"), ("risky", "catch_all"), ("undeliverable", "discard"), ("weird", "unknown"), (None, "unknown")]:
        assert normalize_status(raw) == want, raw

    # dedupe
    rows = [{"first_name": "A", "last_name": "B", "company_domain": "X.com", "linkedin_url": "L1"},
            {"first_name": "a", "last_name": "b", "company_domain": "x.com", "linkedin_url": "l1"},
            {"first_name": "c", "last_name": "d", "company_domain": "y.com", "linkedin_url": ""},
            {"first_name": "c", "last_name": "d", "company_domain": "y.com", "linkedin_url": ""},
            {"first_name": "e", "last_name": "f", "company_domain": "z.com", "linkedin_url": "L1"}]
    r1 = dedupe(rows, ["linkedin_url"])
    assert [r["first_name"] for r in r1] == ["A", "c", "c"]  # first wins, blanks kept
    assert [r["first_name"] for r in dedupe(r1, ["first_name", "last_name", "company_domain"])] == ["A", "c"]

    assert len(dedupe([{"a": "1", "b": "x"}, {"a": "1", "b": "y"}, {"a": "1", "b": "X"}], ["a", "b"])) == 2  # both must match

    # suppress: each of four reasons + a kept row
    t = date(2026, 10, 21)
    crm = [{"email": "o@a.com", "stage": "open"},
           {"email": "s@b.com", "in_sequence": "TRUE"},
           {"linkedin_url": "https://linkedin.com/in/cust/", "is_customer": "true"},
           {"domain": "recent.com", "last_touched": "2026-10-10"},
           {"email": "old@old.com", "last_touched": "2026-01-01", "stage": "won"}]
    people = [{"email": "O@a.com"}, {"email": "s@b.com"}, {"linkedin_url": "https://LINKEDIN.com/in/cust?x=1"},
              {"email": "someone@recent.com"}, {"email": "old@old.com"}]
    kept, dropped = suppress(people, crm, today=t)
    assert kept == [{"email": "old@old.com"}]
    assert [d["suppress_reason"] for d in dropped] == ["open_opportunity", "in_sequence", "customer", "touched_within_14d"]
    assert suppress([{"email": "n@n.com"}], [{"email": "n@n.com", "stage": "Negotiation"}], today=t)[0] == []  # open|proposal|negotiation, any case
    try:
        suppress(people, [{"email": "bad@x.com", "last_touched": "10/21/2026"}], today=t); raise AssertionError("bad date accepted")
    except SystemExit as e:
        assert "line 2" in str(e) and "bad@x.com" in str(e) and "YYYY-MM-DD" in str(e)

    # batches + csv round trip
    assert list(batches([1, 2, 3, 4, 5], 2)) == [[1, 2], [3, 4], [5]]
    p = Path(tempfile.mkdtemp()) / "sub" / "o.csv"
    write_csv(p, [{"a": "1", "b": "x"}]); assert read_csv(p) == [{"a": "1", "b": "x"}]
    # cli
    a = cli_common(argparse.ArgumentParser()).parse_args(["--dry-run", "--cap-usd", "2"])
    assert a.dry_run and a.cap_usd == 2.0
    print("OK")


if __name__ == "__main__":
    a = cli_common(argparse.ArgumentParser(description=__doc__)).parse_args()
    if a.selftest:
        selftest()
    else:
        print("nothing to do; use --selftest")
        sys.exit(2)
