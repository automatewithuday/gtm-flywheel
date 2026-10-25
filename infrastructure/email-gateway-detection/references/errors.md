# Errors

## DNS (Stage 1, from `seg_status`)

| seg_status | Cause | Action | Cached? |
|---|---|---|---|
| ok | MX resolved | continue | yes |
| nxdomain | domain does not exist | drop lead, bad data | yes |
| no_mx | domain exists, no MX record | treat as unsendable, drop | yes |
| null_mx | MX is `.` (RFC 7505), domain accepts no mail | drop | yes |
| timeout | resolver did not answer in 4s | rerun later | no |
| servfail | no nameserver could answer | rerun later, then drop if repeated | no |

`seg_vendor` is empty whenever `seg_status` is not `ok`.

## Gateway bounce strings (post-send, for learning which layer failed)

Seen on SEG-protected domains. Log the full string against the lead's `seg_vendor`.

| Bounce | Meaning |
|---|---|
| `550 5.7.1 Message rejected due to content policy` | Proofpoint content or spam verdict |
| `554 rejected due to spam content` | Mimecast spam signature match |
| `550 Rejected by header based Anti-Spoofing policy` | Mimecast impostor protection, check From/domain alignment |
| `451 4.7.1 Greylisting in effect` | temporary, let the sender retry |
| `550 5.7.0 Message rejected per DMARC policy` | your DMARC alignment failed, fix DNS before sending more |
| `550 5.7.1 Service unavailable; client host blocked` | sending IP on a blocklist |
| `554 Email rejected due to security policies` | Mimecast generic, often a flagged link (Calendly, tracking domain) |

Silence (no bounce, no reply, opens drop to zero for one domain) usually means quarantine, not rejection. Gateways often quarantine silently.

## Vendor calls (Stages 2 and 3, from `detect_gateway.py` stderr)

These never change `seg_status`. The row keeps its Stage 1 values and the run continues.

| Log line | Cause | Action |
|---|---|---|
| `deepline_error ... err=...` | CLI missing, not authenticated, timeout (120s) or non-JSON output | run `deepline auth status`, rerun the stage; nothing was charged |
| `deepline_error ... status=...` | Deepline job did not complete | rerun; check `deepline billing usage` if it repeats |
| `vendor_error ... http=401` or `403` | own API key rejected | check the key in `.env`; the response body is deliberately not logged |
| `vendor_error ... http=402` or `429` | vendor account out of credits or rate limited | top up or slow down; rows keep their DNS values |
| `vendor_error ... err=...` | network failure or non-JSON body from the vendor | rerun; if it persists switch to the Deepline route by unsetting the key |
| `unmapped_vendor_value prospeo:<label>` | Prospeo named a provider not in `gateway-map.json` | look up a real MX host, add suffix and label to the map |
| `unmapped_vendor_value leadmagic:<label>` | `mx_security_gateway=true` with a label not in the map | same as above; the row is already flagged `seg_conflict=true` if DNS said `none` |
| `input needs a domain or email column` | CSV has neither column | rename the column or add one |
