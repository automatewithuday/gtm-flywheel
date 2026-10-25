"""Instantly API v2 adapter. Read-only: GET campaigns/analytics + POST /leads/list (a query, not a write); leads are paged UNFILTERED (all contacted).

Assumptions (docs examples only, never verified live):
- analytics/steps `step` is a 1-based string ("1" in the docs example); if a "0" appears we treat the response as
  0-based and add 1. `variant` is a 0-based string: "0"->A, "1"->B.
- lead email_replied_step / email_replied_variant use the same bases as analytics/steps.
- positive = lt_interest_status in {1,2,3,4}; meetings = {2,3,4} (proposed rule, owned by the user).
"""
import html.parser
import re
from . import _http

TOOL = "instantly"
BASE_URL = "https://api.instantly.ai/api/v2"
ALLOW = {("GET", "/campaigns"), ("GET", "/campaigns/{id}"), ("GET", "/campaigns/analytics/steps"),
         ("POST", "/leads/list")}  # POST /leads/list is a read-only query; the ONLY allowed POST
POSITIVE, MEETING = {1, 2, 3, 4}, {2, 3, 4}


def make_client(api_key, dry_run=False):
    return _http.Client(TOOL, BASE_URL, ALLOW, headers={"Authorization": f"Bearer {api_key}"}, dry_run=dry_run)


class _Text(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.out = []

    def handle_starttag(self, tag, attrs):
        if tag in ("br", "p", "div", "li", "tr"):
            self.out.append("\n")

    def handle_data(self, data):
        self.out.append(data)


def html_to_text(s):
    p = _Text()
    p.feed(s or "")
    lines = (re.sub(r"[ \t]+", " ", l).strip() for l in "".join(p.out).splitlines())
    return "\n".join(l for l in lines if l)


def norm_campaigns(raw):
    return [{"tool": TOOL, "id": c["id"], "name": c.get("name")} for c in (raw or {}).get("items") or []]


def norm_steps(campaign_id, raw_campaign):
    rows = []
    seqs = (raw_campaign or {}).get("sequences") or [{}]
    for i, st in enumerate(seqs[0].get("steps") or []):
        for j, v in enumerate(st.get("variants") or []):
            if v.get("v_disabled"):
                continue  # index j still counts it, so labels stay aligned with Instantly's variant numbers
            rows.append({"tool": TOOL, "campaign_id": campaign_id, "step_no": i + 1, "variant": chr(65 + j),
                         "channel": "email", "subject": v.get("subject") or "", "body": html_to_text(v.get("body"))})
    return rows


def _num(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def norm_stats(campaign_id, raw_steps_analytics, raw_leads, as_of):
    base = [r for r in raw_steps_analytics or [] if isinstance(r, dict)]
    off = _off(base)   # 0-based response -> shift to 1-based
    pos, meet = {}, {}
    for l in raw_leads or []:
        s, v, st = _num(l.get("email_replied_step")), _num(l.get("email_replied_variant")), l.get("lt_interest_status")
        if s is None or v is None or not isinstance(st, int):
            continue
        k = (s + off, v)
        pos[k] = pos.get(k, 0) + (st in POSITIVE)
        meet[k] = meet.get(k, 0) + (st in MEETING)
    rows = []
    for r in base:
        k = (_num(r.get("step")) + off, _num(r.get("variant")))
        rows.append({"tool": TOOL, "campaign_id": campaign_id, "step_no": k[0], "variant": chr(65 + k[1]),
                     "as_of": as_of, "sends": r.get("sent"), "replies": r.get("unique_replies"),
                     "positive": pos.get(k, 0), "meetings": meet.get(k, 0)})
    return rows


def _replied(l):
    return _num(l.get("email_replied_step")) is not None or (_num(l.get("email_reply_count")) or 0) > 0


def norm_leads(campaign_id, raw_leads, as_of, off=0):
    """Lead-grain rows. off = step base shift (1 if analytics is 0-based), same as norm_stats."""
    rows = []
    for l in raw_leads or []:
        st = l.get("lt_interest_status")
        st = st if isinstance(st, int) else None
        rep = _replied(l)
        s, v = _num(l.get("email_replied_step")), _num(l.get("email_replied_variant"))
        ok = rep and s is not None and v is not None
        rows.append({"tool": TOOL, "campaign_id": campaign_id, "step_no": s + off if ok else None,
                     "variant": chr(65 + v) if ok else None, "email": l.get("email"),
                     "status": None if st is None else str(st), "replied": int(rep),
                     "positive": None if st is None else int(st in POSITIVE),
                     "meeting": None if st is None else int(st in MEETING), "as_of": as_of})
    return rows


def _off(raw_steps_analytics):
    return 1 if any(_num(r.get("step")) == 0 for r in raw_steps_analytics or [] if isinstance(r, dict)) else 0


def _pages(fetch):
    after = None
    while True:
        page = fetch(after) or {}
        yield from page.get("items") or []
        after = page.get("next_starting_after")
        if not after:
            return


def pull(client, since, until, as_of, campaign_ids=None):
    camps = list(_pages(lambda a: client.get("/campaigns", {"limit": 100, "starting_after": a})))
    campaigns = norm_campaigns({"items": camps})
    if campaign_ids:
        campaigns = [c for c in campaigns if c["id"] in set(campaign_ids)]
    out = {"campaigns": campaigns, "steps": [], "stats": [], "leads": []}
    for c in campaigns:
        cid = c["id"]
        out["steps"] += norm_steps(cid, client.get("/campaigns/{id}", id=cid))
        an = client.get("/campaigns/analytics/steps", {"campaign_id": cid, "start_date": since, "end_date": until})
        leads = list(_pages(lambda a: client.post("/leads/list", {
            "campaign": cid, "limit": 100, **({"starting_after": a} if a else {})})))
        an = an if isinstance(an, list) else []
        out["stats"] += norm_stats(cid, an, leads, as_of)
        out["leads"] += norm_leads(cid, leads, as_of, _off(an))
    return out
