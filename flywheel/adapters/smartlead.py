"""Smartlead read-only adapter. Auth = api_key query param. Never calls anything outside ALLOW."""
from html.parser import HTMLParser

from . import _http

TOOL = "smartlead"
BASE_URL = "https://server.smartlead.ai/api/v1"
ALLOW = {("GET", "/campaigns/"), ("GET", "/campaigns/{id}/sequences"),
         ("GET", "/campaigns/{id}/sequence-analytics"), ("GET", "/campaigns/{id}/leads"),
         ("GET", "/leads/fetch-categories")}
LEAD_LIMIT = 100


def make_client(api_key, dry_run=False, base_url=None):
    return _http.Client(TOOL, base_url or BASE_URL, ALLOW, query={"api_key": api_key}, dry_run=dry_run, min_interval=1.0)


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []

    def handle_data(self, d):
        self.out.append(d)

    def handle_starttag(self, tag, a):
        if tag in ("br", "p", "div", "li"):
            self.out.append("\n")


def _text(html):
    p = _Text()
    p.feed(html or "")
    t = p.out and "".join(p.out).replace("\xa0", " ")
    return "\n".join(l.strip() for l in (t or "").splitlines() if l.strip())


def _items(raw):
    """Unwrap {data: [...]} / bare list / {} (dry-run)."""
    if isinstance(raw, dict):
        raw = raw.get("data")
    return raw if isinstance(raw, list) else []


def _label(name, i):
    n = (name or "").strip()
    if n.lower().startswith("variant "):
        n = n[8:].strip()
    return n or chr(65 + i)


def norm_campaigns(raw):
    return [{"tool": TOOL, "id": str(c["id"]), "name": c.get("name")} for c in _items(raw)]


def norm_steps(campaign_id, raw_sequences):
    rows = []
    for s in _items(raw_sequences):
        subj = s.get("subject") or s.get("follow_up_subject") or ""
        variants = s.get("sequence_variants") or [
            {"variant_name": "A", "subject": subj, "email_body": s.get("email_body")}]
        for i, v in enumerate(variants):
            rows.append({"tool": TOOL, "campaign_id": str(campaign_id), "step_no": int(s["seq_number"]),
                         "variant": _label(v.get("variant_name"), i), "channel": "email",
                         # variant subject may be blank on follow-ups: inherit the step's
                         "subject": v.get("subject") or subj, "body": _text(v.get("email_body"))})
    return rows


def norm_stats(campaign_id, raw_analytics, as_of, raw_sequences=None):
    # id join (unverified): sequence_variants[].id == analytics variants[].id; else analytics label, else order.
    idmap = {v["id"]: _label(v.get("variant_name"), i)
             for s in _items(raw_sequences) for i, v in enumerate(s.get("sequence_variants") or [])}
    data = raw_analytics.get("data") if isinstance(raw_analytics, dict) else None
    rows = []
    for s in (data or {}).get("sequences") or []:
        vs = s.get("variants") or []
        pairs = [(_label(idmap.get(v.get("id")) or v.get("variant_label"), i), v.get("stats") or {})
                 for i, v in enumerate(vs)] or [("A", s.get("total_stats") or {})]
        for label, st in pairs:
            rows.append({"tool": TOOL, "campaign_id": str(campaign_id), "step_no": int(s["seq_number"]),
                         "variant": label, "as_of": as_of, "sends": int(st.get("sent_count") or 0),
                         "replies": int(st.get("reply_count") or 0),
                         "positive": int(st.get("positive_reply_count") or 0), "meetings": None})
    return rows


def norm_leads(campaign_id, raw_leads_pages, categories, as_of):
    """categories = {id: {name, sentiment_type}}. Smartlead has no lead->variant link: step_no/variant None."""
    rows = []
    for page in raw_leads_pages:
        for m in _items(page):
            cid = m.get("lead_category_id")
            cat = (categories or {}).get(cid) or {}
            name = cat.get("name")
            rows.append({"tool": TOOL, "campaign_id": str(campaign_id), "step_no": None, "variant": None,
                         "email": (m.get("lead") or {}).get("email"), "status": name,
                         "replied": int(cid is not None), "positive": int(cat.get("sentiment_type") == "positive"),
                         "meeting": int("meeting" in (name or "").lower()), "as_of": as_of})
    return rows


def _lead_pages(client, cid):
    pages, off = [], 0
    while True:
        page = client.get("/campaigns/{id}/leads", {"offset": off, "limit": LEAD_LIMIT}, id=cid)
        pages.append(page)
        if len(_items(page)) < LEAD_LIMIT:
            return pages
        off += LEAD_LIMIT


def pull(client, since, until, as_of, campaign_ids=None):
    out = {"campaigns": [], "steps": [], "stats": [], "leads": []}
    out["campaigns"] = norm_campaigns(client.get("/campaigns/"))
    if campaign_ids is not None:
        keep = {str(c) for c in campaign_ids}
        out["campaigns"] = [c for c in out["campaigns"] if c["id"] in keep]
    cats = {c["id"]: c for c in _items(client.get("/leads/fetch-categories")) if "id" in c} if out["campaigns"] else {}
    for c in out["campaigns"]:
        seqs = client.get("/campaigns/{id}/sequences", id=c["id"])
        ana = client.get("/campaigns/{id}/sequence-analytics", {"start_date": since, "end_date": until}, id=c["id"])
        out["steps"] += norm_steps(c["id"], seqs)
        out["stats"] += norm_stats(c["id"], ana, as_of, seqs)
        out["leads"] += norm_leads(c["id"], _lead_pages(client, c["id"]), cats, as_of)
    return out
