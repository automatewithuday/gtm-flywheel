"""HeyReach read-only adapter. Campaign-level stats only (step_no 0); steps come from the sequence node tree.
Every read is a POST by design (except sequence), so the exact paths are allowlisted. Nothing else is callable."""
from . import _http

TOOL = "heyreach"
BASE_URL = "https://api.heyreach.io/api/public"
ALLOW = {
    ("POST", "/campaign/GetAll"),
    ("GET", "/campaign/GetCampaignSequence"),
    ("POST", "/stats/GetOverallStatsByCampaign"),
    ("POST", "/inbox/GetConversationsV3"),
}
MESSAGE_NODES = {"CONNECTION_REQUEST", "MESSAGE", "INMAIL"}
# UNVERIFIED: accepted latestAutoTagNames strings. Docs/help article say Interested / Not Interested / Generic.
POSITIVE_TAG = "Interested"


def make_client(api_key, dry_run=False, base_url=None):
    return _http.Client(TOOL, base_url or BASE_URL, ALLOW, headers={"X-API-KEY": api_key},
                        dry_run=dry_run, min_interval=0.2)  # 300 req/min


def norm_campaigns(raw):
    items = raw.get("items", []) if isinstance(raw, dict) else raw
    return [{"tool": TOOL, "id": str(c["id"]), "name": c.get("name")} for c in items or [] if "id" in c]


def _walk(node):
    """Depth-first, conditionalNode before unconditionalNode."""
    if not isinstance(node, dict):
        return
    yield node
    yield from _walk(node.get("conditionalNode"))
    yield from _walk(node.get("unconditionalNode"))


def norm_steps(campaign_id, raw):
    rows, no = [], 0
    for n in _walk(raw):
        msgs = (n.get("payload") or {}).get("messages") or []
        if n.get("nodeType") not in MESSAGE_NODES or not msgs:
            continue
        no += 1
        for i, m in enumerate(msgs):
            body = m.get("message") or m.get("body") or "" if isinstance(m, dict) else m
            rows.append({"tool": TOOL, "campaign_id": str(campaign_id), "step_no": no,
                         "variant": chr(ord("A") + i), "channel": "linkedin", "subject": None, "body": body})
    return rows


def norm_stats(overall_by_campaign, positive_counts, as_of):
    """overall_by_campaign: GetOverallStatsByCampaign response; positive_counts: {campaignId: totalCount}.
    sends = messagesSent (connection requests are NOT counted), replies = totalMessageReplies, meetings None."""
    rows = []
    for s in (overall_by_campaign or {}).get("overallStats", []) or []:
        cid = str(s["campaignId"])
        rows.append({"tool": TOOL, "campaign_id": cid, "step_no": 0, "variant": "A", "as_of": as_of,
                     "sends": s.get("messagesSent"), "replies": s.get("totalMessageReplies"),
                     "positive": positive_counts.get(cid), "meetings": None})
    return rows


def _campaigns(client, limit=100):
    out, offset = [], 0
    while True:
        page = client.post("/campaign/GetAll", body={"offset": offset, "limit": limit})
        items = page.get("items") or [] if isinstance(page, dict) else []
        out += items
        offset += limit
        if len(items) < limit or offset >= page.get("totalCount", 0):
            return out


def pull(client, since, until, as_of, campaign_ids=None):
    campaigns = norm_campaigns(_campaigns(client))
    if campaign_ids is not None:
        campaigns = [c for c in campaigns if c["id"] in {str(i) for i in campaign_ids}]
    res = {"campaigns": campaigns, "steps": [], "stats": []}
    if not campaigns:
        return res
    ids = [int(c["id"]) for c in campaigns]
    for c in campaigns:
        seq = client.get("/campaign/GetCampaignSequence", params={"campaignId": c["id"]})
        res["steps"] += norm_steps(c["id"], seq)
    overall = client.post("/stats/GetOverallStatsByCampaign",
                          body={"accountIds": [], "campaignIds": ids, "startDate": since, "endDate": until})
    # positive = all-time auto-tagged conversations (no from/to: date format unverified), unlike windowed sends/replies
    pos = {}
    for c in campaigns:
        r = client.post("/inbox/GetConversationsV3", body={
            "limit": 1, "filters": {"campaignIds": [int(c["id"])], "latestAutoTagNames": [POSITIVE_TAG]}})
        if isinstance(r, dict) and r.get("totalCount") is not None:
            pos[c["id"]] = r["totalCount"]
    res["stats"] = norm_stats(overall, pos, as_of)
    return res
