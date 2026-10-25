"""Offline tests for Stages 2 and 3. Fixtures are trimmed real Deepline responses (Sept 2026)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import detect_gateway as vm  # noqa: E402

GMAP = vm.load_map()

PROSPEO_PFIZER = {"status": "completed", "toolResponse": {"rawV2": {"error": False, "free_enrichment": False, "company": {
    "domain": "pfizer.com", "email_tech": {"domain": "pfizer.com", "mx_provider": "Proofpoint"}}}},
    "billing": {"credits_charged": 0.55}}
LM_PFIZER = {"status": "completed", "toolResponse": {"rawV2": {
    "email": "info@pfizer.com", "email_status": "unknown", "mx_record": "mxb-00013f02.gslb.pphosted.com",
    "mx_provider": "Proofpoint", "mx_gateway": "Proofpoint", "mx_gateway_type": "Email Security Gateway",
    "mx_security_gateway": True}}, "billing": {"credits_charged": 0}}
LM_MSFT = {"status": "completed", "toolResponse": {"rawV2": {
    "email": "info@microsoft.com", "email_status": "invalid", "mx_record": "microsoft-com.mail.protection.outlook.com",
    "mx_provider": "Microsoft 365", "mx_gateway": "Microsoft 365", "mx_gateway_type": "Cloud Mailbox Host",
    "mx_security_gateway": False}}, "billing": {"credits_charged": 0.09}}


def row(**kw):
    base = {"domain": "acme.com", "email": "a@acme.com", "seg_vendor": "unknown", "mailbox_provider": "other",
            "seg_source": "dns", "mailbox_source": "", "seg_status": "ok", "mx_hosts": "mail.acme.com",
            "seg_checked_at": "2026-09-22T00:00:00+00:00", "seg_conflict": "false"}
    base.update(kw)
    return base


def test_prospeo_field_path():
    assert vm.parse_prospeo(PROSPEO_PFIZER) == "Proofpoint"


def test_leadmagic_fields_pass_through():
    lm = vm.parse_leadmagic(LM_PFIZER)
    assert (lm["mx_gateway"], lm["mx_security_gateway"], lm["email_status"]) == ("Proofpoint", True, "unknown")


def test_stage2_fills_unknown():
    r = row()
    vm.apply_prospeo(r, "Proofpoint", GMAP)
    assert (r["seg_vendor"], r["seg_source"]) == ("proofpoint", "prospeo")


def test_stage2_google_means_no_gateway():
    r = row()
    vm.apply_prospeo(r, "Google", GMAP)
    assert (r["seg_vendor"], r["mailbox_provider"], r["mailbox_source"]) == ("none", "google", "prospeo")


def test_stage2_unmapped_stays_unknown():
    r = row()
    vm.apply_prospeo(r, "Some Self Hosted Thing", GMAP)
    assert r["seg_vendor"] == "unknown" and r["vendor_raw"] == "prospeo:Some Self Hosted Thing"


def test_stage2_never_touches_resolved_rows():
    r = row(seg_vendor="mimecast")
    vm.apply_prospeo(r, "Proofpoint", GMAP)
    assert r["seg_vendor"] == "mimecast"


def test_stage3_agree_no_conflict():
    r = row(seg_vendor="proofpoint")
    vm.apply_leadmagic(r, vm.parse_leadmagic(LM_PFIZER), GMAP)
    assert (r["seg_conflict"], r["seg_vendor"], r["email_status"]) == ("false", "proofpoint", "unknown")


def test_stage3_conflict_dns_none_vendor_gateway():
    r = row(seg_vendor="none", mailbox_provider="microsoft")
    vm.apply_leadmagic(r, vm.parse_leadmagic(LM_PFIZER), GMAP)
    assert (r["seg_conflict"], r["seg_vendor"]) == ("true", "none")  # keep DNS value


def test_stage3_conflict_dns_gateway_vendor_none():
    r = row(seg_vendor="proofpoint")
    vm.apply_leadmagic(r, vm.parse_leadmagic(LM_MSFT), GMAP)
    assert r["seg_conflict"] == "true" and r["seg_vendor"] == "proofpoint"


def test_stage3_conflict_different_gateway():
    r = row(seg_vendor="mimecast")
    vm.apply_leadmagic(r, vm.parse_leadmagic(LM_PFIZER), GMAP)
    assert r["seg_conflict"] == "true" and r["seg_vendor"] == "mimecast"


def test_stage3_cloud_host_label_is_not_a_gateway():
    # mx_gateway="Microsoft 365" with mx_security_gateway=false must map to none, not conflict
    r = row(seg_vendor="none", mailbox_provider="microsoft")
    vm.apply_leadmagic(r, vm.parse_leadmagic(LM_MSFT), GMAP)
    assert r["seg_conflict"] == "false"


LM_DEBIAN = {"status": "completed", "toolResponse": {"rawV2": {
    "email": "info@debian.org", "email_status": "unknown", "mx_record": "mailly.debian.org",
    "mx_provider": "Other", "mx_gateway": None, "mx_gateway_type": None, "mx_security_gateway": False}},
    "billing": {"credits_charged": 0.09}}


def test_stage3_self_hosted_no_gateway_is_none_not_unknown():
    r = row(domain="debian.org")
    vm.apply_leadmagic(r, vm.parse_leadmagic(LM_DEBIAN), GMAP)
    assert (r["seg_vendor"], r["seg_source"], r["mailbox_provider"]) == ("none", "leadmagic", "other")


def test_stage3_fills_still_unknown():
    r = row()
    vm.apply_leadmagic(r, vm.parse_leadmagic(LM_MSFT), GMAP)
    assert (r["seg_vendor"], r["seg_source"], r["mailbox_provider"], r["mailbox_source"]) == \
        ("none", "leadmagic", "microsoft", "leadmagic")


def test_run_end_to_end_offline_with_cache_writeback():
    calls = []

    def fake(tool, inp):
        calls.append((tool, inp))
        if tool == "prospeo_enrich_company":
            return PROSPEO_PFIZER, 0.55
        return LM_PFIZER, 0.0

    rows = [row(domain="pfizer.com", email="a@pfizer.com"), row(domain="pfizer.com", email="b@pfizer.com"),
            row(domain="acme.com", seg_vendor="mimecast", email="")]
    cache = {"pfizer.com": dict(rows[0])}
    stats = vm.run(rows, "23", GMAP, call=fake, cache=cache, only_unknown=False)
    assert [c[0] for c in calls] == ["prospeo_enrich_company"] + ["leadmagic_email_validation"] * 3
    assert calls[0][1] == {"company_website": "pfizer.com"}  # one Prospeo call for two rows on one domain
    assert calls[3][1] == {"email": "info@acme.com"}  # --all cross-checks email-less rows via the domain
    assert rows[0]["seg_vendor"] == rows[1]["seg_vendor"] == "proofpoint"
    assert rows[2]["seg_vendor"] == "mimecast" and rows[2]["seg_conflict"] == "true"  # LeadMagic says proofpoint
    assert cache["pfizer.com"]["seg_vendor"] == "proofpoint" and cache["pfizer.com"]["seg_source"] == "prospeo"
    assert stats["credits"]["prospeo"] == 0.55 and stats["conflicts"] == 1


def test_name_lookup_case_insensitive():
    assert vm.name_lookup("PROOFPOINT", GMAP) == ("proofpoint", None)
    assert vm.name_lookup("Google Workspace", GMAP) == ("none", "google")
    assert vm.name_lookup("nope", GMAP) == (None, None)


def test_stage3_default_only_unknown_and_domain_fallback():
    calls = []

    def fake(tool, inp):
        calls.append(inp)
        return LM_PFIZER, 0.0

    rows = [row(domain="pfizer.com", email=""), row(domain="pfizer.com", email=""),
            row(domain="known.com", seg_vendor="mimecast", email="x@known.com")]
    stats = vm.run(rows, "3", GMAP, call=fake)
    assert calls == [{"email": "info@pfizer.com"}]  # one call per domain, known row untouched
    assert rows[0]["seg_vendor"] == rows[1]["seg_vendor"] == "proofpoint"
    assert rows[0]["seg_source"] == "leadmagic" and rows[0]["email_status"] == ""
    assert rows[2]["seg_vendor"] == "mimecast" and stats["calls"]["leadmagic"] == 1


def test_one_command_runs_dns_inline(tmp_path, monkeypatch):
    import mx_lookup
    # fake DNS: pfizer behind proofpoint, acme self-hosted (unknown), then LeadMagic fills acme
    class FakeDns:
        def mx(self, d):
            return [(10, "mx0a.pphosted.com")] if d == "pfizer.com" else [(10, "mail.acme.com")]

        def txt(self, d):
            return []
    monkeypatch.setattr(mx_lookup, "DnsClient", lambda *a, **k: FakeDns())
    monkeypatch.setattr(vm, "deepline", lambda tool, inp: (LM_MSFT, 0.09))
    src = tmp_path / "in.csv"
    src.write_text("domain\npfizer.com\nacme.com\n")
    out, cache = tmp_path / "out.csv", tmp_path / "c.json"
    assert vm.main(["--in", str(src), "--out", str(out), "--cache", str(cache)]) == 0
    import csv, json
    got = {r["domain"]: r for r in csv.DictReader(open(out))}
    assert got["pfizer.com"]["seg_vendor"] == "proofpoint" and got["pfizer.com"]["seg_source"] == "dns"
    assert got["acme.com"]["seg_vendor"] == "none" and got["acme.com"]["mailbox_provider"] == "microsoft"
    assert json.load(open(cache))["acme.com"]["seg_source"] == "leadmagic"  # paid answer cached


def test_byok_direct_calls_use_verified_endpoints(monkeypatch):
    import io, json, urllib.request
    seen = []

    class Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=0):
        seen.append((req.full_url, req.method, dict(req.header_items()), json.loads(req.data)))
        body = {"email": "a@x.com", "email_status": "valid", "credits_consumed": 0.25, "mx_security_gateway": False,
                "mx_provider": "Google Workspace"} if "leadmagic" in req.full_url else \
               {"error": False, "free_enrichment": False, "company": {"email_tech": {"mx_provider": "Mimecast"}}}
        return Resp(json.dumps(body).encode())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("PROSPEO_API_KEY", "pk-test")
    monkeypatch.setenv("LEADMAGIC_API_KEY", "lm-test")
    resp, credits = vm.vendor_call("prospeo_enrich_company", {"company_website": "x.com"})
    assert vm.parse_prospeo(resp) == "Mimecast" and credits == 1.0
    resp, credits = vm.vendor_call("leadmagic_email_validation", {"email": "a@x.com"})
    assert vm.parse_leadmagic(resp)["mx_provider"] == "Google Workspace" and credits == 0.25
    url, method, headers, body = seen[0]
    assert (url, method, body) == ("https://api.prospeo.io/enrich-company", "POST", {"data": {"company_website": "x.com"}})
    assert headers.get("X-key") == "pk-test"  # urllib capitalises header names
    url, method, headers, body = seen[1]
    assert (url, method, body) == ("https://api.leadmagic.io/v1/people/email-validation", "POST", {"email": "a@x.com"})
    assert headers.get("X-api-key") == "lm-test"


def test_no_key_routes_to_deepline(monkeypatch):
    monkeypatch.delenv("LEADMAGIC_API_KEY", raising=False)
    monkeypatch.setattr(vm, "deepline", lambda tool, inp: ({"via": "deepline"}, 0.0))
    assert vm.vendor_call("leadmagic_email_validation", {"email": "a@x.com"})[0] == {"via": "deepline"}


def test_load_env_does_not_override_existing(tmp_path, monkeypatch):
    monkeypatch.setenv("LEADMAGIC_API_KEY", "from-env")
    monkeypatch.delenv("PROSPEO_API_KEY", raising=False)
    (tmp_path / ".env").write_text("# keys\nLEADMAGIC_API_KEY=from-file\nPROSPEO_API_KEY=\"pk\"\n")
    vm.load_env(tmp_path / ".env")
    import os
    assert os.environ["LEADMAGIC_API_KEY"] == "from-env" and os.environ["PROSPEO_API_KEY"] == "pk"
