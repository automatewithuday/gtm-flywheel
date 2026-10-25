
## Smartlead
Source: docs only (no live call made). Base `https://server.smartlead.ai/api/v1`, auth `api_key` query param, 60 req/min standard (client min_interval 1.0s).

Endpoints used (read-only): `GET /campaigns/`, `GET /campaigns/{id}/sequences`, `GET /campaigns/{id}/sequence-analytics?start_date&end_date`. `GET /leads/fetch-categories` is allowlisted but not called yet.
Mapping: stat.sends=`sent_count`, replies=`reply_count`, positive=`positive_reply_count` (current lead-category sentiment = positive, so it can change after the fact; as_of snapshots are ours), meetings=None (no meeting counter at any granularity).
Steps with no `sequence_variants` emit variant "A" from the step's own subject/email_body; stats fall back to `total_stats` as "A". Follow-ups use `follow_up_subject` when `subject` is empty. Bodies are stored as text (HTML stripped).

Unverified:
- Variant join: `sequence_variants[].id` == `sequence-analytics.variants[].id` is NOT stated in the docs; fallback is `variant_label`, then order. `variant_name` "Variant A" vs `variant_label` "A" naming is inferred.
- Fixture values are invented; only the field shapes come from docs. Campaign list example values are paraphrased.
- Whether `/campaigns/` is paginated, and whether archived campaigns appear.
- `/campaigns/{id}/statistics` and `/leads-statistics` shapes (docs contradict / empty) are not used.
- Meetings could only be derived at campaign level from lead categories (name-dependent, per-account); not implemented.

## Instantly
API v2, base `https://api.instantly.ai/api/v2`, `Authorization: Bearer <key>`. Rate limit 100 req/s, 6000 req/min per workspace (429 on breach, no Retry-After documented). Pagination: `limit` (max 100) + `starting_after` = previous `next_starting_after`.

Endpoints used (allowlist): GET /campaigns, GET /campaigns/{id}, GET /campaigns/analytics/steps (campaign_id, start_date, end_date), POST /leads/list (read-only query; the only allowed POST).

Mapping: `sequences[0].steps[i].variants[j]` -> step_no i+1, variant chr(65+j); `v_disabled` variants skipped (index still counted). sends = `sent`, replies = `unique_replies`. positive = leads with `lt_interest_status` in {1,2,3,4}, meetings = {2,3,4}, grouped by (`email_replied_step`, `email_replied_variant`). The positive/meeting set is a proposed qualification rule: owner to confirm. Status codes: 0 OOO, 1 Interested, 2 Meeting Booked, 3 Meeting Completed, 4 Won, -1 Not Interested, -2 Wrong Person, -3 Lost, -4 No Show.

Unverified (docs only, no live call made): (1) analytics `step` base (docs example shows "1"; adapter shifts +1 if a "0" appears); (2) `variant` "0"->A; (3) lead `email_replied_step/variant` share those bases; (4) `FILTER_VAL_REPLIED` name and semantics (one filtered pass chosen over 4 interest filters to save calls; a lead given a status manually without replying is missed); (5) lead `email_replied_*` is last-reply only, so multi-reply leads count once at their last step; (6) steps analytics has no campaign_id, so one call per campaign; (7) fixtures are hand-built from the documented schema, not real responses.

## lemlist
- Base `https://api.lemlist.com/api`; Basic auth, empty user, key as password; 20 req/2 s (min_interval 0.1).
- Allowlisted GETs: `/campaigns?version=v2`, `/campaigns/{cid}/sequences`, `/sequences/{sid}/steps/{stid}/ab-test`, `/v2/campaigns/{cid}/stats` (startDate/endDate, ABSelected).
- Granularity: per step + per variant (A from sequences, B from ab-test endpoint; Email Pro, 404 skipped). Only level-0 sequence steps; conditional sub-sequences ignored. step_no = 1-based position.
- Stats matched on (sequenceId, sequenceStep). sends = sent + invited (LinkedIn invites report `invited`). Step-level positive/meetings = None.
- Pseudo-step 0 / "A": messagesSent, replied, nbLeadsInterested, meetingBooked from the ABSelected=A response. The B call is made only if some step has abTest.
- UNVERIFIED: whether ABSelected=A filters the top-level totals (would undercount interested/meetings) and whether it filters steps[]; index (1-based) vs sequenceStep (0-based) offset; step objects are image-documented, fields taken from endpoint examples. Fixtures are invented values with documented field names.
- Not covered: activities endpoint (per-step interested attribution unreliable: sequenceStep absent on some activities).

## HeyReach
- Base `https://api.heyreach.io/api/public`; header `X-API-KEY`; 300 req/min (min_interval 0.2). Reads are POSTs; allowlisted: POST `/campaign/GetAll`, GET `/campaign/GetCampaignSequence?campaignId=`, POST `/stats/GetOverallStatsByCampaign`, POST `/inbox/GetConversationsV3`.
- Campaign-level only. Steps: DFS of the sequence tree (conditionalNode first); CONNECTION_REQUEST/MESSAGE/INMAIL nodes with non-empty payload.messages become steps, one row per message (A, B, ...). No per-variant stats exist.
- Pseudo-step 0 / "A": sends = messagesSent (connection requests and InMail NOT counted), replies = totalMessageReplies, positive = GetConversationsV3 totalCount with latestAutoTagNames ["Interested"] per campaign, meetings None. Positive is all-time (no from/to), while sends/replies are windowed by since/until.
- UNVERIFIED: accepted auto-tag strings ("Interested"; docs also mention "Not Interested", "Generic", blog says "Negative"); date format of from/to on V3; whether payload.messages items are plain strings (adapter also accepts {message|body}); GetAll example was type-placeholder JSON, fixture values invented; auto-tag counts in GetOverallStats claimed by help article but absent from docs examples.
- Message text is not HTML-stripped (LinkedIn plain text assumed).
