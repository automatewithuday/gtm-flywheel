"""lemlist read-only adapter. Per-step + per-variant stats; interested/meetings are campaign-level (step_no 0)."""
import re
from html.parser import HTMLParser

from . import _http

TOOL = "lemlist"
BASE_URL = "https://api.lemlist.com/api"
ALLOW = {
    ("GET", "/campaigns"),
    ("GET", "/campaigns/{cid}/sequences"),
    ("GET", "/sequences/{sid}/steps/{stid}/ab-test"),
    ("GET", "/v2/campaigns/{cid}/stats"),
}


def make_client(api_key, dry_run=False, base_url=None):
    import base64
    tok = base64.b64encode(f":{api_key}".encode()).decode()  # Basic auth: empty user, key as password
    return _http.Client(TOOL, base_url or BASE_URL, ALLOW, headers={"Authorization": f"Basic {tok}"},
                        dry_run=dry_run, min_interval=0.1)  # 20 req / 2 s


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []

    def handle_starttag(self, tag, attrs=None):
        if tag in ("br", "p", "div", "li"):
            self.out.append("\n")

    handle_endtag = handle_starttag

    def handle_data(self, data):
        self.out.append(data)


def html_to_text(s):
    if not s:
        return ""
    p = _Text()
    p.feed(s)
    lines = (re.sub(r"[ \t\xa0]+", " ", l).strip() for l in "".join(p.out).split("\n"))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _channel(step_type):
    t = step_type or "email"
    return "linkedin" if t.startswith("linkedin") else t


def norm_campaigns(raw):
    return [{"tool": TOOL, "id": c["_id"], "name": c.get("name")} for c in raw if isinstance(c, dict) and "_id" in c]


def main_steps(sequences):
    """Level-0 sequence steps ordered by index. Conditional sub-sequences (level > 0) are skipped."""
    out = []
    for seq in (sequences or {}).values():
        if isinstance(seq, dict) and seq.get("level", 0) == 0:
            out += seq.get("steps", [])
    return sorted(out, key=lambda s: s.get("index", 0))


def norm_steps(campaign_id, sequences, ab_tests=None):
    """ab_tests: {stepId: ab-test response}. step_no = 1-based position in the main sequence."""
    rows = []
    for no, st in enumerate(main_steps(sequences), 1):
        base = {"tool": TOOL, "campaign_id": campaign_id, "step_no": no, "channel": _channel(st.get("type"))}
        rows.append({**base, "variant": "A", "subject": html_to_text(st.get("subject")) or None,
                     "body": html_to_text(st.get("message"))})
        b = (ab_tests or {}).get(st.get("_id"))
        if st.get("abTest") and b and b.get("message") is not None:
            rows.append({**base, "variant": "B", "subject": html_to_text(b.get("subject")) or None,
                         "body": html_to_text(b.get("message"))})
    return rows


def norm_stats(campaign_id, sequences, stats_a, stats_b, as_of):
    """Per (step, variant) sends/replies matched on (sequenceId, sequenceStep); campaign-level
    interested/meetings on pseudo-step 0 variant A (taken from the ABSelected=A response)."""
    rows = []
    for variant, raw in (("A", stats_a), ("B", stats_b)):
        if not raw:
            continue
        by_key = {(s.get("sequenceId"), s.get("sequenceStep")): s for s in raw.get("steps", [])}
        for no, st in enumerate(main_steps(sequences), 1):
            if variant == "B" and not st.get("abTest"):
                continue
            s = by_key.get((st.get("sequenceId"), st.get("sequenceStep")))
            if s is None:
                continue
            sends = (s.get("sent") or 0) + (s.get("invited") or 0)  # a step is one type; linkedin invites report 'invited'
            rows.append({"tool": TOOL, "campaign_id": campaign_id, "step_no": no, "variant": variant,
                         "as_of": as_of, "sends": sends, "replies": s.get("replied"),
                         "positive": None, "meetings": None})
    if stats_a:
        rows.append({"tool": TOOL, "campaign_id": campaign_id, "step_no": 0, "variant": "A", "as_of": as_of,
                     "sends": stats_a.get("messagesSent"), "replies": stats_a.get("replied"),
                     "positive": stats_a.get("nbLeadsInterested"), "meetings": stats_a.get("meetingBooked")})
    return rows


def _campaigns(client, limit=100):
    out, offset = [], 0
    while True:
        page = client.get("/campaigns", params={"version": "v2", "offset": offset, "limit": limit})
        if not isinstance(page, list) or not page:  # {} in dry-run
            return out
        out += page
        if len(page) < limit:
            return out
        offset += limit


def pull(client, since, until, as_of, campaign_ids=None):
    campaigns = norm_campaigns(_campaigns(client))
    if campaign_ids is not None:
        campaigns = [c for c in campaigns if c["id"] in set(campaign_ids)]
    res = {"campaigns": campaigns, "steps": [], "stats": []}
    for c in campaigns:
        cid = c["id"]
        seqs = client.get("/campaigns/{cid}/sequences", cid=cid)
        seqs = seqs if isinstance(seqs, dict) else {}
        ab = {}
        for st in main_steps(seqs):
            if st.get("abTest"):
                try:
                    ab[st["_id"]] = client.get("/sequences/{sid}/steps/{stid}/ab-test",
                                               sid=st.get("sequenceId"), stid=st["_id"])
                except Exception as e:  # 404 SEQUENCE_AB_NO_VARIANT (Email Pro only): skip variant B
                    if getattr(e, "code", None) != 404:
                        raise
        q = {"startDate": since, "endDate": until}
        stats_a = client.get("/v2/campaigns/{cid}/stats", params={**q, "ABSelected": "A"}, cid=cid)
        # B call only when some step has a variant: saves rate-limit budget
        stats_b = client.get("/v2/campaigns/{cid}/stats", params={**q, "ABSelected": "B"}, cid=cid) if ab else {}
        res["steps"] += norm_steps(cid, seqs, ab)
        res["stats"] += norm_stats(cid, seqs, stats_a, stats_b, as_of)
    return res
