"""Play 1: email waterfall. GetLeads -> LeadMagic -> Prospeo -> FullEnrich (order via --providers), verify, stop rule. Never guesses emails from name patterns."""
import argparse, contextlib, io, sys, tempfile, time
from pathlib import Path

from outbound import common as c

GETLEADS_CREDIT_USD = 0.0  # set to your plan's per-credit price (charged per hit only)
DEEPLINE_FIND_USD = 0.15   # per-row estimate AND the hard --max-credits basis (1.5 credits/row). Deepline reports avg 1.07, max 5.06 credits/row for this play; a single provider call was observed at 1.56. Too low = the play halts on RUN_BILLING_CAP_EXCEEDED.
VERIFY_USD = 0.003
BOUNCEBAN_USD = 0.02
FULLENRICH_USD = 0.035  # observed 0.35 credits for one contact; FullEnrich bills on match, max observed 164 credits per 50-row call
LEADMAGIC_USD = 0.034   # 0.34 credits per result (deepline tools describe leadmagic_email_finder)
PROSPEO_USD = 0.055     # 0.55 credits per result (deepline tools describe prospeo_enrich_person)
# Provider order = the waterfall. Cheapest first; GetLeads charges only on a hit. Edit here or pass --providers.
PROVIDERS = "getleads,leadmagic,prospeo,fullenrich"
PER_ROW_CAP_USD = 0.15     # default total cap = rows x this, when --cap-usd is not given
OUT_COLS = ["email", "email_status", "email_provider", "verifier", "mx_class", "domain_match", "miss_reason"]


def _domain_match(email, company_domain):
    """'yes' when the email's domain is the company domain (or shares its main label: clorox.com ~ thecloroxcompany.com),
    'no' otherwise. A verifier proves the mailbox exists, not that it is the right person: review 'no' rows by hand."""
    ed = (email.rsplit("@", 1)[-1] if email else "").lower().strip()
    cd = (company_domain or "").lower().strip().removeprefix("www.")
    if not ed or not cd:
        return ""
    e, c = ed.split(".")[0], cd.split(".")[0]
    return "yes" if ed == cd or (len(e) >= 4 and e in cd) or (len(c) >= 4 and c in ed) else "no"


def _norm(raw):
    return c.normalize_status(raw)  # the ONLY producer of "verified": a vendor verdict field run through the shared map


def _first(d, *keys):
    for k in keys:
        if d.get(k):
            return d[k]
    return None


def _items(out, *keys):
    """Pull the row list out of a CLI/REST JSON payload (shape unverified: list, or dict holding a list)."""
    if isinstance(out, list):
        return out
    for k in (*keys, "rows", "results", "data", "output"):
        v = (out or {}).get(k) if isinstance(out, dict) else None
        if isinstance(v, list):
            return v
        if isinstance(v, dict):
            return _items(v, *keys)
    return []


def _keys(d):
    """Match keys of a result/row: normalized linkedin url (if echoed) and (first, last, domain)."""
    ks = []
    li = c._li(d.get("linkedin_url") or d.get("linkedinUrl"))
    if li:
        ks.append(("li", li))
    n = tuple((d.get(k) or "").strip().lower() for k in ("first_name", "last_name"))
    dom = (d.get("company_domain") or d.get("domain") or "").strip().lower()
    if all(n) and dom:
        ks.append(("name", *n, dom))
    return ks


def _match(name, rows, out, res, to_cand):
    """Aligned candidate list, matched by echoed key (never by position). Unmatched rows stay {} (pending)."""
    if out is None:  # dry-run: wrapper recorded the planned call
        return [{} for _ in rows]
    if rows and not res:
        raise RuntimeError(f"{name}: empty or unrecognized result for {len(rows)} rows after the call was made: {str(out)[:200]}")
    if len(res) != len(rows):
        print(f"WARN {name}: {len(res)} results for {len(rows)} rows; unmatched rows stay pending", file=sys.stderr)
    by = {}
    for d in res:
        for k in _keys(d) if isinstance(d, dict) else []:
            by.setdefault(k, d)
    cands = []
    for r in rows:
        d = next((by[k] for k in _keys(r) if k in by), None)
        cands.append(to_cand(d) if d else {})
    if rows and not any(k in by for r in rows for k in _keys(r)):
        raise RuntimeError(f"{name}: {len(res)} results but none matched an echoed key for {len(rows)} rows after the call was made: {str(out)[:200]}")
    return cands


def _gl_cand(item):
    d = (item.get("data") or {}) if item.get("success") else {}
    em = _first(d, "email", "work_email", "professional_email")
    if not em and isinstance(d.get("emails"), list) and d["emails"]:
        e0 = d["emails"][0]
        em = e0.get("email") if isinstance(e0, dict) else e0
    if not em:
        return {}
    c.spend(GETLEADS_CREDIT_USD, "getleads:credit")  # 1 credit per success only
    return {"email": em, "provider": "getleads", "raw_status": _first(d, "email_status")}


def find_getleads(rows):
    """One candidate dict (or {}) per row, aligned. Candidate: email, provider, raw_status, miss_reason."""
    out = c.getleads("POST", "/api/v1/enrich/from-linkedin",
                     json={"items": [{"linkedin_url": r["linkedin_url"]} for r in rows], "limit_per_item": 1},
                     usd=0.0, label="getleads:enrich")
    return _match("getleads", rows, out, _items(out, "results"), _gl_cand)  # results echo linkedinUrl


def find_deepline(rows):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "in.csv"
        c.write_csv(p, rows, ["first_name", "last_name", "company_domain", "linkedin_url"])
        out = c.deepline_play("prebuilt/person-to-email-batch", csv_path=p, usd_estimate=DEEPLINE_FIND_USD * len(rows))
    halted = isinstance(out, dict) and out.get("partial")  # run hit Deepline's cap: unfinished rows are retryable, not misses

    def cand(d):
        x = _cand(d, "deepline")
        if halted and not x.get("email") and not x.get("miss_reason"):
            x["miss_reason"] = "deepline_halted"
        return x
    return _match("deepline", rows, out, _items(out), cand)


def _lm_cand(d):
    """LeadMagic rawV2 (verified live): flat {email, status: valid|catch_all|not_found, mx_gateway_type, mx_security_gateway}."""
    if not d or not d.get("email"):
        return {"miss_reason": (d or {}).get("message") or "leadmagic:not_found"}
    mx = "security_gateway" if d.get("mx_security_gateway") else (d.get("mx_gateway_type") or "")
    return {"email": d["email"], "provider": "leadmagic", "raw_status": d.get("status"), "mx_class": mx}


def _per_row(name, rows, call):
    """Call a per-row provider; one row's provider error (bad input, 422) must not abort the provider for the whole batch."""
    out = []
    for r in rows:
        try:
            out.append(call(r))
        except c.SpendCapExceeded:
            raise
        except RuntimeError as e:
            print(f"ERROR {name} row {r.get('first_name')} {r.get('last_name')}: {str(e)[:120]}", file=sys.stderr)
            out.append({"miss_reason": f"{name}:error: {str(e)[:80]}"})
    return out


def find_leadmagic(rows):
    """One call per row (name + domain). Each call is cached by its input, so re-runs are free."""
    # ponytail: sequential subprocess per row (~3 s each); parallelise if 150-row batches feel slow
    return _per_row("leadmagic", rows, lambda r: _lm_cand(c.deepline_action(
        "leadmagic_email_finder", {"first_name": r["first_name"], "last_name": r["last_name"], "domain": r["company_domain"]}, LEADMAGIC_USD))
        if r.get("company_domain") else {"miss_reason": "leadmagic:needs_domain"})  # name-only lookups are guesses


def _prospeo_cand(d):
    """Prospeo rawV2 (verified live): {person: {email: {email, status: VERIFIED|..., verification_method}}}."""
    em = (((d or {}).get("person") or {}).get("email") or {}) if isinstance(d, dict) else {}
    if not em.get("email"):
        return {"miss_reason": (d or {}).get("error") or "prospeo:not_found"}
    return {"email": em["email"], "provider": "prospeo", "raw_status": em.get("status"), "mx_class": em.get("email_mx_provider") or "",
            "company_domain": ((d.get("company") or {}).get("domain") or (d.get("company") or {}).get("website") or "")}  # fills a blank row domain


def find_prospeo(rows):
    """One call per row: LinkedIn URL (highest accuracy) plus name and domain so Prospeo can cross-check the company."""
    def params(r):  # send only what we have: an empty company_domain is rejected by the provider
        p = {"first_name": r["first_name"], "last_name": r["last_name"]}
        if (r.get("company_domain") or "").strip():
            p["company_domain"] = r["company_domain"].strip()
        if r.get("linkedin_url"):
            p["linkedin_url"] = r["linkedin_url"]
        return p
    return _per_row("prospeo", rows, lambda r: _prospeo_cand(c.deepline_action("prospeo_enrich_person", params(r), PROSPEO_USD)))


def _fe_rows(out):
    """FullEnrich batch -> rows shaped for _match: input echoes professional_network_url/first_name/last_name/company_domain."""
    rows = []
    for d in (out or {}).get("data") or []:
        inp, ci = d.get("input") or {}, d.get("contact_info") or {}
        best = ci.get("most_probable_work_email") or {}
        rows.append({"linkedin_url": inp.get("professional_network_url"), "first_name": inp.get("first_name"),
                     "last_name": inp.get("last_name"), "company_domain": inp.get("company_domain"),
                     "email": best.get("email"), "status": best.get("status")})
    return rows


def _fe_cand(d):
    if not d.get("email"):
        return {"miss_reason": "fullenrich:not_found"}
    return {"email": d["email"], "provider": "fullenrich", "raw_status": d.get("status")}  # HIGH_PROBABILITY etc -> verifier decides


def find_fullenrich(rows):
    """Bulk (<=50) async job; waits, then polls fullenrich_get_result (free) until FINISHED."""
    data = [{k: v for k, v in {"first_name": r["first_name"], "last_name": r["last_name"], "domain": (r.get("company_domain") or "").strip(),
                               "linkedin_url": r.get("linkedin_url") or "", "enrich_fields": ["contact.emails"]}.items() if v} for r in rows]
    out = c.deepline_action("fullenrich_bulk_enrich", {"name": "play-1", "data": data, "max_wait_ms": 90000}, FULLENRICH_USD * len(rows))
    for _ in range(20):  # ponytail: up to ~2 min of polling; a batch still IN_PROGRESS after that stays a miss and reruns later
        if out is None or (out.get("status") or "").upper() == "FINISHED":
            break
        time.sleep(6)
        out = c.deepline_action("fullenrich_get_result", {"enrichment_id": out.get("id")}, 0.0, max_age_days=0.0001) or out
    return _match("fullenrich", rows, out, _fe_rows(out), _fe_cand)


FINDERS = {"getleads": find_getleads, "leadmagic": find_leadmagic, "prospeo": find_prospeo, "fullenrich": find_fullenrich,
           "deepline-play": find_deepline}  # deepline-play = Deepline's own prebuilt waterfall (vendor order not yours)


def _cand(d, default_provider):
    em = _first(d, "email", "most_probable_work_email")
    if isinstance(em, dict):
        em = em.get("email")
    if not em:
        return {"miss_reason": d.get("miss_reason")}
    validated = d.get("email_validated")  # Deepline returns a boolean: True = passed validation before being returned
    raw = "valid" if validated is True else (None if validated is False else _first(d, "email_status"))
    return {"email": em, "provider": d.get("email_source") or default_provider,
            "raw_status": raw, "miss_reason": d.get("miss_reason"), "mx_class": d.get("email_route")}


def verify(email):
    """MillionVerifier; catch_all -> BounceBan once. Returns (status, verifier)."""
    mv = c.deepline_action("millionverifier_verify_email", {"email": email}, VERIFY_USD, max_age_days=30) or {}
    # MillionVerifier verdict field is `result` (ok | catch_all | invalid | unknown | disposable); never read a job `status`
    st = _norm(_first(mv, "result", "email_status"))
    if st != "catch_all":
        return st, "millionverifier"
    bb = c.deepline_action("bounceban_verify_single", {"email": email}, BOUNCEBAN_USD, max_age_days=30) or {}
    # ponytail: BounceBan may answer status=verifying; we keep catch_all rather than poll (never goes live either way)
    b = _norm(_first(bb, "email_status", "result"))
    return (b if b in ("verified", "discard") else "catch_all"), "millionverifier+bounceban"


def _resolve(cand):
    """Candidate -> (status, verifier). Provider-declared valid skips the verifier."""
    st = _norm(cand.get("raw_status"))
    if st == "verified":
        return st, "provider"
    return verify(cand["email"])


def run(rows, finders):
    """rows -> output rows (same order, never dropped). finders: [(name, fn)]; stops at the first non-discard verdict."""
    res = [{**r, "email": "", "email_status": "not_found", "email_provider": "", "verifier": "", "mx_class": "", "domain_match": "", "miss_reason": ""} for r in rows]
    pending = list(range(len(rows)))
    try:
        for name, fn in finders:
            if not pending:
                break
            sub = [rows[i] for i in pending if name != "getleads" or rows[i].get("linkedin_url")]
            idx = [i for i in pending if name != "getleads" or rows[i].get("linkedin_url")]
            if not sub:
                continue
            try:
                found = list(fn(sub))
            except c.SpendCapExceeded:
                raise  # our own ledger cap: handled below, aborts the whole run
            except RuntimeError as e:  # provider failed (billing cap, bad shape, outage): keep the rows, record why, try the next provider
                msg = f"provider_error:{name}: {str(e)[:160]}"
                for i in idx:
                    res[i]["miss_reason"] = msg
                print(f"ERROR {name}: {e}", file=sys.stderr)
                continue
            for i, cand in zip(idx, found):
                if not cand or not cand.get("email"):
                    if cand and cand.get("miss_reason"):
                        res[i]["miss_reason"] = str(cand["miss_reason"])
                    continue
                if cand.get("company_domain") and not (rows[i].get("company_domain") or "").strip():
                    rows[i]["company_domain"] = res[i]["company_domain"] = cand["company_domain"]  # learned from the provider (Play 3 engagers)
                st, ver = _resolve(cand)
                if st == "discard":
                    res[i]["miss_reason"] = f"{name}:discarded"
                    continue
                res[i].update(email=cand["email"], email_status=st, email_provider=cand.get("provider") or name,
                              verifier=ver, mx_class=cand.get("mx_class") or "", miss_reason="",
                              domain_match=_domain_match(cand["email"], rows[i].get("company_domain")))
                pending.remove(i)
    except c.SpendCapExceeded as e:
        for i in pending:
            res[i]["miss_reason"] = "cap_aborted"
        print(f"CAP: {e}", file=sys.stderr)
        return res, True
    return res, False


def summarize(n_in, n_dedup, out, aborted):
    n = len(out) or 1
    pct = {k: 100 * sum(r["email_status"] == k for r in out) / n for k in c.STATUS}
    prov = {}
    for r in out:
        if r["email"]:
            prov[r["email_provider"]] = prov.get(r["email_provider"], 0) + 1
    vcalls = sum(1 for k in c.SPENT["calls"] if "millionverifier" in k["label"] or "bounceban" in k["label"])
    lines = ["# Play 1 report", "", f"- rows in: {n_in}, after dedupe: {n_dedup} (removed {n_in - n_dedup})",
             *[f"- {k}: {pct[k]:.1f}%" for k in c.STATUS],
             "- hits per provider: " + (", ".join(f"{k} {v}" for k, v in sorted(prov.items())) or "none"),
             f"- verifier calls: {vcalls}", f"- spend: {c.report()}"]
    if c.SPENT["dry_run"]:
        lines.append("- DRY RUN: nothing was called, so the percentages above are meaningless")
    if aborted:
        lines.append("- ABORTED by spend cap: unprocessed rows are not_found with miss_reason=cap_aborted")
    lines.append("- Send only `verified` to Smartlead; `catch_all`/`unknown` go to the LinkedIn-only track.")
    return "\n".join(lines) + "\n", pct


def main(argv=None):
    ap = c.cli_common(argparse.ArgumentParser(description=__doc__))
    ap.add_argument("input", nargs="?")
    ap.add_argument("--batch", type=int, default=150)
    ap.add_argument("--providers", default=PROVIDERS, help=f"waterfall order, comma list of {','.join(FINDERS)} (default {PROVIDERS})")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.input or not a.out:
        ap.error("input CSV and --out are required")
    c.apply_cli(a)
    rows = c.read_csv(a.input)
    need = ["first_name", "last_name", "company_domain", "linkedin_url"]
    if missing := [k for k in need if rows and k not in rows[0]]:
        raise SystemExit(f"{a.input}: missing required column(s): {', '.join(missing)} (need {','.join(need)})")
    ded = c.dedupe(c.dedupe(rows, ["linkedin_url"]), ["first_name", "last_name", "company_domain"])
    print(f"dedupe: {len(rows)} -> {len(ded)} rows ({len(rows) - len(ded)} removed)")
    if a.cap_usd is None:
        c.set_cap(len(ded) * PER_ROW_CAP_USD)
    names = [n.strip() for n in a.providers.split(",") if n.strip()]
    if bad := [n for n in names if n not in FINDERS]:
        raise SystemExit(f"--providers: unknown {bad}; choose from {','.join(FINDERS)}")
    finders = [(n, FINDERS[n]) for n in names]
    out, aborted = [], False
    for b in c.batches(ded, a.batch):
        if aborted:  # rows are never dropped
            out += [{**r, "email": "", "email_status": "not_found", "email_provider": "", "verifier": "", "mx_class": "", "domain_match": "", "miss_reason": "cap_aborted"} for r in b]
            continue
        if a.dry_run:
            c.spend(VERIFY_USD * len(b), "deepline:verify(est)")
        res, aborted = run(b, finders)
        out += res
    cols = list(dict.fromkeys([k for r in ded for k in r] + OUT_COLS))
    dest = str(a.out) + (".dryrun" if a.dry_run else "")  # a dry run must never overwrite real output
    c.write_csv(dest + (".csv" if a.dry_run else ""), out, cols)
    text, _ = summarize(len(rows), len(ded), out, aborted)
    errs = sum(1 for r in out if str(r.get("miss_reason", "")).startswith("provider_error:"))
    if errs:
        text += f"- PROVIDER ERRORS: {errs} rows hit a provider failure (see miss_reason); output written, exit 1\n"
    Path(dest + ".report.md").write_text(text)
    print(text, end="")
    return 1 if errs else 0


def selftest():
    global find_getleads, find_deepline, verify
    real = (find_getleads, find_deepline, verify)
    mk = lambda n: [{"first_name": f"f{i}", "last_name": "l", "company_domain": f"d{i}.com", "linkedin_url": f"li{i}"} for i in range(n)]
    calls = []

    def fake(table):  # finder returning {row first_name: candidate}
        return lambda rows: [table.get(r["first_name"], {}) for r in rows]

    def go(rows, gl, dl, ver, cap=None):
        global find_getleads, find_deepline, verify
        c._reset(cap=cap)
        calls.clear()
        find_getleads, find_deepline = fake(gl), fake(dl)
        verify = lambda e: (calls.append(e), ver[e])[1]
        return run(rows, [("getleads", find_getleads), ("deepline", find_deepline)])

    V, U, D = ("verified", "millionverifier"), ("unknown", "millionverifier"), ("discard", "x")
    cand = lambda e, p="getleads": {"email": e, "provider": p}
    # valid first provider stops: deepline never asked about f0
    out, ab = go(mk(1), {"f0": cand("a@x.com")}, {"f0": cand("WRONG@x.com")}, {"a@x.com": V})
    assert out[0]["email"] == "a@x.com" and out[0]["email_status"] == "verified" and out[0]["email_provider"] == "getleads" and calls == ["a@x.com"] and not ab
    # unknown stops
    out, _ = go(mk(1), {"f0": cand("u@x.com")}, {"f0": cand("WRONG@x.com")}, {"u@x.com": U})
    assert out[0]["email_status"] == "unknown" and calls == ["u@x.com"]
    # discard -> fall through -> second provider hit
    out, _ = go(mk(1), {"f0": cand("bad@x.com")}, {"f0": cand("good@y.com", "prospeo")}, {"bad@x.com": D, "good@y.com": V})
    assert out[0]["email"] == "good@y.com" and out[0]["email_provider"] == "prospeo" and out[0]["miss_reason"] == "" and calls == ["bad@x.com", "good@y.com"]
    # exhausted -> not_found, never constructed, rows kept
    out, _ = go(mk(2), {}, {"f1": {"miss_reason": "no_match"}}, {})
    assert [r["email_status"] for r in out] == ["not_found"] * 2 and out[1]["miss_reason"] == "no_match" and out[0]["email"] == ""
    # row without linkedin_url skips getleads but still reaches deepline
    rows = mk(1); rows[0]["linkedin_url"] = ""
    out, _ = go(rows, {"f0": cand("no@x.com")}, {"f0": cand("d@x.com", "p")}, {"d@x.com": V})
    assert out[0]["email"] == "d@x.com"
    # provider-declared valid skips the verifier; email at another company is flagged domain_match=no
    out, _ = go(mk(1), {"f0": {**cand("v@x.com"), "raw_status": "valid"}}, {}, {})
    assert out[0]["verifier"] == "provider" and calls == [] and out[0]["domain_match"] == "no"
    out, _ = go(mk(1), {"f0": cand("v@d0.com")}, {}, {"v@d0.com": V})
    assert out[0]["domain_match"] == "yes"
    assert _domain_match("eric@example.com", "theexamplecompany.com") == "yes" and _domain_match("a@othercompany.com", "example-foods.com") == "no"
    assert _domain_match("k@example-sun.com", "www.example-sun.com") == "yes" and _domain_match("", "x.com") == ""
    # provider parsers, fixtures copied from real responses (out/probe/*.json, 21 Oct 2026)
    lm = {"email": "ada@example-fitness.com", "status": "valid", "mx_gateway_type": "Cloud Mailbox Host", "mx_security_gateway": False}
    assert _lm_cand(lm) == {"email": "ada@example-fitness.com", "provider": "leadmagic", "raw_status": "valid", "mx_class": "Cloud Mailbox Host"}
    assert _lm_cand({"email": None, "message": "no match"})["miss_reason"] == "no match" and not _lm_cand(None).get("email")
    pr = {"person": {"email": {"status": "VERIFIED", "email": "grace@example-toys.com", "email_mx_provider": "Microsoft"}}}
    assert _prospeo_cand(pr) == {"email": "grace@example-toys.com", "provider": "prospeo", "raw_status": "VERIFIED", "mx_class": "Microsoft", "company_domain": ""}
    assert _prospeo_cand({**pr, "company": {"domain": "hasbro.com"}})["company_domain"] == "hasbro.com"
    # a row with no company_domain learns it from the provider; LeadMagic is skipped for such rows
    blank = [{"first_name": "f0", "last_name": "l", "company_domain": "", "linkedin_url": "li0"}]
    assert find_leadmagic(blank)[0]["miss_reason"] == "leadmagic:needs_domain"
    # one row's provider error does not abort the provider for the other rows
    orig = c.deepline_action
    def flaky(aid, p, u, **k):
        if p.get("first_name") == "f0": raise RuntimeError("minimum requirements")
        return {"person": {"email": {"email": "ok@d1.com", "status": "VERIFIED"}}}
    c.deepline_action = flaky
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            got = find_prospeo(mk(2))
    finally:
        c.deepline_action = orig
    assert got[0]["miss_reason"].startswith("prospeo:error") and got[1]["email"] == "ok@d1.com"
    out, _ = go(blank, {}, {"f0": {**cand("e@learned.com", "prospeo"), "company_domain": "learned.com"}}, {"e@learned.com": V})
    assert out[0]["company_domain"] == "learned.com" and out[0]["domain_match"] == "yes"
    assert _resolve(_prospeo_cand(pr)) == ("verified", "provider") and not _prospeo_cand({"person": {"email": None}}).get("email")
    fe = {"status": "FINISHED", "data": [{"input": {"professional_network_url": "https://www.linkedin.com/in/ada-lovelace", "first_name": "Ada",
          "last_name": "Lovelace", "company_domain": "example-media.com"}, "contact_info": {"most_probable_work_email": {"email": "ada@other-employer.de", "status": "HIGH_PROBABILITY"}}}]}
    fr = _fe_rows(fe); assert fr[0]["email"] == "ada@other-employer.de" and fr[0]["linkedin_url"].endswith("/ada-lovelace")
    cands = _match("fullenrich", [{"first_name": "Ada", "last_name": "Lovelace", "company_domain": "example-media.com", "linkedin_url": "https://www.linkedin.com/in/ada-lovelace/"}], fe, fr, _fe_cand)
    assert cands[0]["email"] == "ada@other-employer.de" and cands[0]["raw_status"] == "HIGH_PROBABILITY" and _norm("HIGH_PROBABILITY") == "unknown"
    assert all(n in FINDERS for n in PROVIDERS.split(","))
    # a provider that raises (billing cap, bad shape) keeps the rows, records why, and the next provider still runs
    c._reset(); calls.clear()
    def boom(rows): raise RuntimeError("RUN_BILLING_CAP_EXCEEDED")
    find_getleads, find_deepline, verify = boom, fake({"f0": cand("ok@x.com", "deepline")}), (lambda e: V)
    with contextlib.redirect_stderr(io.StringIO()):
        out, ab = run(mk(2), [("getleads", find_getleads), ("deepline", find_deepline)])
    assert not ab and out[0]["email"] == "ok@x.com" and out[1]["email_status"] == "not_found"
    assert out[1]["miss_reason"].startswith("provider_error:getleads: RUN_BILLING_CAP")
    # run()-level catch-all: stops, second provider untouched, BounceBan once
    find_getleads, find_deepline, verify = real
    seen2, dl = [], []
    orig = c.deepline_action
    c.deepline_action = lambda aid, p, u, **k: seen2.append(aid) or ({"result": "catch_all"} if aid.startswith("million") else {"result": "risky"})
    try:
        c._reset()
        out, _ = run(mk(1), [("getleads", fake({"f0": cand("c@x.com")})), ("deepline", lambda r: dl.append(r) or [cand("WRONG@x.com")])])
    finally:
        c.deepline_action = orig
    assert out[0]["email_status"] == "catch_all" and out[0]["email"] == "c@x.com" and dl == [] and seen2.count("bounceban_verify_single") == 1
    # dedupe before spend: duplicates never reach a provider
    dup = mk(2) + [dict(mk(1)[0])]
    ded0 = c.dedupe(c.dedupe(dup, ["linkedin_url"]), ["first_name", "last_name", "company_domain"])
    asked = []
    find_getleads = lambda r: asked.extend(x["first_name"] for x in r) or [{}] * len(r)
    run(ded0, [("getleads", find_getleads)])
    assert asked == ["f0", "f1"]
    # matching: reordered results, unmatched rows pending, empty -> raises, generic "status" never short-circuits
    rws = mk(2)
    res = [{"linkedinUrl": "LI1/", "success": True, "data": {"email": "b@x.com", "status": "valid"}}]
    with contextlib.redirect_stderr(io.StringIO()):
        cs = _match("t", rws, {"r": 1}, res, _gl_cand)
    assert cs[0] == {} and cs[1]["email"] == "b@x.com" and cs[1]["raw_status"] is None
    with contextlib.redirect_stderr(io.StringIO()):
        cs = _match("t", rws, {"r": 1}, [{"first_name": "F1", "last_name": "L", "company_domain": "D1.com", "email": "n@x.com"}], lambda d: _cand(d, "dl"))
    assert cs[0] == {} and cs[1]["email"] == "n@x.com"
    try:
        _match("deepline", rws, {"weird": 1}, [], _cand); raise AssertionError("empty result must raise")
    except RuntimeError as e:
        assert "deepline" in str(e) and "weird" in str(e)
    assert _match("t", rws, None, [], _cand) == [{}, {}]  # dry-run
    try:
        _match("deepline", rws, {"zzz": 1}, [{"email": "q@x.com"}], _cand); raise AssertionError("no-key-match must raise")
    except RuntimeError as e:
        assert "deepline" in str(e) and "none matched" in str(e) and "zzz" in str(e)
    # real verify(): catch-all calls BounceBan exactly once; plain valid never does
    find_getleads, find_deepline, verify = real
    seen = []
    orig = c.deepline_action
    def fa(aid, params, usd, **k):
        seen.append(aid)
        return {"result": "catch_all"} if aid.startswith("million") else {"result": "risky"}
    c.deepline_action = fa
    try:
        c._reset()
        assert verify("c@x.com") == ("catch_all", "millionverifier+bounceban") and seen == ["millionverifier_verify_email", "bounceban_verify_single"]
        seen.clear(); c.deepline_action = lambda a, p, u, **k: seen.append(a) or {"result": "ok"}
        assert verify("o@x.com") == ("verified", "millionverifier") and len(seen) == 1
    finally:
        c.deepline_action = orig
    # cap abort mid-batch keeps processed rows, output has every row
    def capped(rows):
        c.spend(0.1, "x")
        return [cand(f"{r['first_name']}@x.com") for r in rows]
    c._reset(cap=0.05)
    find_getleads = lambda rows: [cand("done@x.com")] + [None] * (len(rows) - 1)
    find_deepline = capped
    verify = lambda e: ("verified", "m")
    with contextlib.redirect_stderr(io.StringIO()):
        out, ab = run(mk(3), [("getleads", find_getleads), ("deepline", find_deepline)])
    assert ab and len(out) == 3 and out[0]["email"] == "done@x.com" and out[1]["miss_reason"] == "cap_aborted" and out[2]["email_status"] == "not_found"
    find_getleads, find_deepline, verify = real
    # dedupe before spend + report sums to 100
    rows = mk(2) + [dict(mk(1)[0])] + [{**mk(2)[1], "linkedin_url": ""}]
    ded = c.dedupe(c.dedupe(rows, ["linkedin_url"]), ["first_name", "last_name", "company_domain"])
    assert len(ded) == 2
    out = [{"email": "a", "email_status": s, "email_provider": "p"} for s in ("verified", "catch_all", "unknown", "not_found", "verified", "not_found", "verified")]
    text, pct = summarize(9, 7, out, False)
    assert abs(sum(pct.values()) - 100) < 1e-9 and "removed 2" in text
    # dry-run end to end: planned, nothing spent, every row kept
    td = Path(tempfile.mkdtemp())
    c.write_csv(td / "in.csv", mk(3) + mk(1))
    c._reset()
    with contextlib.redirect_stdout(io.StringIO()):
        assert main([str(td / "in.csv"), "--out", str(td / "o.csv"), "--dry-run"]) == 0
    assert c.SPENT["usd"] == 0.0 and len(c.read_csv(td / "o.csv.dryrun.csv")) == 3 and (td / "o.csv.dryrun.report.md").exists()
    assert not (td / "o.csv").exists() and not (td / "o.csv.report.md").exists()  # real artifacts untouched
    c.write_csv(td / "bad.csv", [{"first_name": "a", "company_domain": "x.com"}])
    try:
        main([str(td / "bad.csv"), "--out", str(td / "b.csv"), "--dry-run"]); raise AssertionError("missing columns accepted")
    except SystemExit as e:
        assert "last_name" in str(e) and "linkedin_url" in str(e)
    c._reset()
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
