"""Offline tests: no network needed. Run with `python -m pytest tests/`."""
import sys
from pathlib import Path

import dns.resolver

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import mx_lookup as m  # noqa: E402

GMAP = m.load_map()


class Fake:
    def __init__(self, mx=None, txt=None, exc=None):
        self._mx, self._txt, self._exc = mx or [], txt or [], exc

    def mx(self, d):
        if self._exc:
            raise self._exc
        return self._mx

    def txt(self, d):
        return self._txt


def run(**kw):
    return m.classify("acme.com", Fake(**kw), GMAP)


def test_proofpoint_behind_m365_via_spf():
    r = run(mx=[(10, "mx0a-001.pphosted.com")], txt=["v=spf1 include:spf.protection.outlook.com -all"])
    assert (r["seg_vendor"], r["mailbox_provider"], r["mailbox_source"]) == ("proofpoint", "microsoft", "dns_spf")


def test_mimecast():
    assert run(mx=[(10, "eu-smtp-inbound-1.mimecast.com")])["seg_vendor"] == "mimecast"


def test_direct_google_no_gateway():
    r = run(mx=[(1, "aspmx.l.google.com")])
    assert (r["seg_vendor"], r["mailbox_provider"], r["mailbox_source"]) == ("none", "google", "dns_mx")


def test_cisco_ironport():
    assert run(mx=[(10, "mx1.hc1234-56.iphmx.com")])["seg_vendor"] == "cisco"


def test_unknown_self_hosted_goes_to_stage2():
    r = run(mx=[(10, "mail.acme.com")])
    assert (r["seg_vendor"], r["mailbox_provider"]) == ("unknown", "other")


def test_suffix_does_not_overmatch():
    # notmimecast.com must not be read as mimecast
    assert run(mx=[(10, "mx.notmimecast.com")])["seg_vendor"] == "unknown"


def test_null_mx():
    assert run(mx=[(0, "")])["seg_status"] == "null_mx"


def test_nxdomain():
    assert run(exc=dns.resolver.NXDOMAIN())["seg_status"] == "nxdomain"


def test_domain_parsing():
    assert m.domain_of({"email": "Jane@WWW.Acme.com"}) == "acme.com"


def test_dns_tools_from_txt_tokens_and_spf():
    r = run(mx=[(1, "aspmx.l.google.com")], txt=[
        "google-site-verification=abc", "ms=ms123", "docusign=1", "atlassian-domain-verification=a",
        "atlassian-domain-verification=b", "00d36000000kfwn=1tbpm0000000sqj",
        "v=spf1 include:_spf.google.com include:mail.zendesk.com include:sendgrid.net ~all"])
    assert r["dns_tools"] == "atlassian|docusign|google_search_console|microsoft_365|salesforce|sendgrid|zendesk"
    assert run(mx=[(1, "aspmx.l.google.com")])["dns_tools"] == ""


def test_cache_entry_without_dns_tools_is_refreshed():
    rows = [{"domain": "acme.com"}]
    old = {"seg_vendor": "none", "mailbox_provider": "google", "seg_source": "dns", "mailbox_source": "dns_mx",
           "seg_status": "ok", "mx_hosts": "aspmx.l.google.com", "seg_checked_at": "2099-01-01T00:00:00+00:00",
           "seg_conflict": "false"}
    cache = {"acme.com": dict(old)}
    client = Fake(mx=[(1, "aspmx.l.google.com")], txt=["docusign=1"])
    assert m.tag_rows(rows, cache, client=client, gmap=GMAP) == 1
    assert rows[0]["dns_tools"] == cache["acme.com"]["dns_tools"] == "docusign"
