---
name: buying-committee-mapper
description: "Use when a qualified account list exists and more than one person per account must be contacted before any email goes out — anyone saying multithreading, buying committee, 'who should we contact at each account', title mapping, persona mapping, decision maker vs champion vs blocker, or 'which titles do we target'. Also use when reps are searching LinkedIn account by account to find who to email, since that is the list's job, not the rep's. Requires an account list that is already qualified, by icp-prompt-builder or any other method."
license: MIT
metadata:
  author: automatewithuday
  source: martechs.io
  version: "1.0"
  category: list-building
---

# Buying Committee Mapper

Qualify the account once. Then map the committee once, at the list level, by title. Reps should open an account with four names and four reasons already attached.

## Output schema (read this first)

The skill produces three files. Everything downstream (campaign-copywriting, smartlead-campaign-upload-public, list-quality-scorecard) reads these.

### 1. `committee-map.csv`

One row per person. One person per slot per account.

| Column             | Type    | Notes                                                                 |
| ------------------ | ------- | --------------------------------------------------------------------- |
| domain             | string  | Account key. Joins back to the qualified account list.                |
| company_name       | string  | Cleaned (run playbook-company-name-cleaning if raw).                  |
| headcount          | int     | From the account list. Blank allowed, see errors.                     |
| headcount_band     | enum    | `1-50`, `51-200`, `201-1000`, `1001+`                                 |
| slot               | enum    | `decision_maker`, `champion`, `influencer`, `blocker`                 |
| slot_rank          | int     | 1 = primary for that slot, 2 = backup. Never more than 2.             |
| slot_collapsed     | bool    | `true` when a slot was merged into another (see Step 3).              |
| full_name          | string  |                                                                       |
| first_name         | string  | Cleaned (playbook-first-name-cleaning).                               |
| title              | string  | Raw title as returned by the data vendor.                             |
| title_match_rule   | string  | `<slot>-<n>`: the nth pattern in that slot's band list (`dm-02` = second decision_maker pattern). |
| linkedin_url       | string  |                                                                       |
| email              | string  |                                                                       |
| email_status       | enum    | `valid`, `catch_all`, `unknown`, `not_found`                          |
| confidence         | float   | 0.0 to 1.0. Title match certainty, not email certainty. 0.95 exact title, 0.85 pattern match, x0.7 when headcount was blank. |
| copy_brief_id      | string  | `dm`, `ch`, `inf`, `blk`. Maps to the brief in committee-config.      |
| champion_confirmed | bool    | Always `false` on output. Flipped to `true` only after a real reply.  |

### 2. `committee-config.yaml` (standalone, or appended to `client-profile.yaml` if you have one)

```yaml
buying_committee:
  bands:
    - { id: "1-50",     min: 1,    max: 50 }
    - { id: "51-200",   min: 51,   max: 200 }
    - { id: "201-1000", min: 201,  max: 1000 }
    - { id: "1001+",    min: 1001, max: null }
  slots:
    decision_maker:
      owns: "budget and the final yes"
      fears: "cost, risk, a vendor that embarrasses them"
      message_gets: "cost and risk"
      titles_by_band:   # case-insensitive patterns, matched on word boundaries; list position = rule id
        "1-50":     ["founder", "ceo", "co-founder", "owner"]
        "51-200":   ["vp sales", "head of sales", "cro"]
        "201-1000": ["vp sales", "svp sales", "cro"]
        "1001+":    ["svp", "cro", "vp revenue operations"]
      negative_titles: ["assistant", "intern", "former"]
    champion:
      owns: "the problem day to day, wants to be seen solving it"
      fears: "backing something that fails internally"
      message_gets: "what they will be able to say internally"
      titles_by_band: { ... }
      negative_titles: [ ... ]
    influencer:
      owns: "the work the product touches"
      fears: "more work, a worse tool"
      message_gets: "the daily pain"
      titles_by_band: { ... }
      max_per_account: 1
    blocker:
      owns: "security, legal, procurement, IT, or the incumbent tool"
      fears: "a vendor who touches what they protect"
      message_gets: "what you will not touch"
      titles_by_band: { ... }
      collapse_below_headcount: 50
  shared_claim: "one sentence, the same across all four slots, about what changes"
  tuned_at: YYYY-MM-DD
  rounds_to_convergence: 3
```

### 3. `coverage-report.md`

Per-slot fill rate, accounts with a full committee, accounts with zero people, and the top 20 unmatched titles (the raw titles that matched no slot, with counts). The unmatched list is where the next round of matrix edits comes from.

## Why this exists

Closed-won deals carry about 67% more buyer contacts than closed-lost ones. Most teams stop at "this account fits" and then each rep works out who to contact one account at a time, between calls, from LinkedIn searches.

That research should happen once, at the list level, before the account is assigned. The same email to five people at one company is a blast. Per-slot copy is what makes it multithreading.

## Inputs required

- Qualified account list CSV with at minimum: `domain, company_name, headcount`. Industry and description help the title interview.
- Optional: `client-profile.yaml` from icp-onboarding (ICP, offer, hard filters, banned industries). Without it, the Step 2 interview collects the same facts.
- People, from either source:
  - A data vendor the operator already has credits with: Prospeo (prospeo-search-api), Blitz (blitz-list-builder), Clay (clay-playbooks), or any vendor that searches by title list plus domain list (Apollo, ZoomInfo, Sales Navigator).
  - **Or an export you already have.** The tagger only needs `domain, full_name, title` per person; rename your vendor's columns to match and skip the pulls in Step 5.

**Gate: do not run on an unqualified list.** Qualified means the list went through icp-prompt-builder, or the user confirms every account was checked against their ICP by some other method (hand review, CRM stage, a scoring model). If neither holds, stop and route them to icp-prompt-builder first. Mapping four people per account on a 60% wrong-fit list quadruples the waste.

## The loop (8 steps)

### Step 1: Load the qualified list and band it

Read the CSV and print the band distribution (the tagger in Step 6 assigns `headcount_band` itself from `headcount`, so this step is only for sizing the interview). `headcount` must be a number; a range like `51-200` is read as its low end, `5,000` as 5000.

```
Band       Accounts   Share
1-50          412      34%
51-200        501      41%
201-1000      240      20%
1001+          63       5%
```

This distribution decides how much interview time goes to each band. If 75% of accounts sit in one band, tune that band's titles first.

### Step 2: Interview for the four slots

Ask the user, one slot at a time. Do not accept titles yet. Ask for the job the slot does in the deal:

- **Decision maker**: who signs, and what makes them say no?
- **Champion**: who feels the pain enough to carry this internally, and what do they need to be able to say to their boss?
- **Influencer**: who does the work the product touches, and what is their daily complaint?
- **Blocker**: who can kill this without owning the problem (security, legal, procurement, IT, the person who owns the incumbent tool), and what are they protecting?

Capture `owns`, `fears`, and `message_gets` for each slot. Then ask for `shared_claim`: one sentence about what changes that must hold across all four messages. Different doors, same house.

### Step 3: Build the title matrix by headcount band

Now translate each slot into titles per band. Start from `references/slot-title-matrix.yaml` for the vertical closest to the user's (sales tooling, developer and security tooling, marketing and demand gen), then adjust from the interview. That file holds three verticals under one `verticals:` key, so either pass it to the tagger with `--vertical=<key>` or copy one vertical's `slots` plus the `bands` into your own `committee-config.yaml` under `buying_committee:`. `scripts/fixtures/committee-config.yaml` is the sales tooling vertical already in that loadable shape.

Rules the matrix must follow:

- Same slot, different title by band. The decision maker at 60 people is the founder. At 600 it is a VP. Never use one title list across all bands.
- Every slot has `negative_titles`. "VP Sales Engineering" must not land in the sales decision maker slot. "Former CTO" must not land anywhere.
- Below `collapse_below_headcount` (default 50), the blocker slot collapses into the decision maker (the founder is also the person who says "we will not touch that") and `slot_collapsed=true`. At very small companies the champion often collapses too. Say so in the matrix, do not pretend four distinct people exist at a 12-person company.
- `influencer.max_per_account` defaults to 1. The influencer slot is always the largest pool by volume and will swamp the send if uncapped.

Show the full matrix back to the user. Get explicit approval before spending a credit.

### Step 4: Dry run on 10 accounts (approval loop)

Pick 10 accounts across bands. For each, run the per-slot search (Step 5 logic), or if you already have an export, run the tagger on just those 10 accounts' rows. Present:

```
Domain          Band      Slot            Name          Title                     Rule   Conf
acme.com        51-200    decision_maker  J. Rivera     VP Sales                  dm-02  0.91
acme.com        51-200    champion        P. Osei       Director Sales Ops        ch-04  0.84
acme.com        51-200    influencer      K. Tan        SDR Manager               inf-01 0.78
acme.com        51-200    blocker         (none)        ...                       ...    ...
tinyco.io       1-50      decision_maker  S. Park       Founder                   dm-01  0.97
tinyco.io       1-50      blocker         S. Park       Founder (collapsed)       dm-01  0.97
```

Ask: which rows are the wrong person for the slot? Which slot is empty and should not be? Which titles are missing from the matrix?

Same convergence rule as icp-prompt-builder: **2 consecutive rounds with zero corrections**, then lock. Any correction resets the streak. Refresh the 10 accounts each round.

### Step 5: Run enrichment per slot, not per account

**Already have a people export for these accounts?** Skip this step. Rename columns to `domain, full_name, title` (plus `first_name, linkedin_url, email, email_status` if present) and go to Step 6. Map your vendor's verification labels onto `valid`, `catch_all`, `unknown`, `not_found`; any other label ranks lowest. Rows at domains not in the account list are dropped and counted in the report.

Once locked, run the full list. The order and shape of the queries matters for cost:

1. **One search per slot per band**, not one search per account. For Prospeo: `titles = matrix[slot][band]`, `domains = all accounts in that band`. That is at most 4 slots x 4 bands = 16 searches for the whole list.
2. **Pull order**: decision maker first, then champion, then blocker, then influencer. If credits run out, you have the slots that cost the most to be wrong about.
3. **Cap at `slot_rank` 1 and 2.** Two people per slot per account maximum. Rank 2 is a backup for a bounce, not a second send.
4. **Email find + verify** on the kept rows only. Never find emails for the whole search result, only for the rows that survived slot tagging.
5. Over 25K results in a single Prospeo search: use prospeo-full-export and split by band or geography.

For Blitz (SMB, owner-finding), it only fills the decision maker slot. Run it for band `1-50`, then run Prospeo for the remaining slots on bands `51-200` and up.

### Step 6: Tag, dedupe, rank

Run `scripts/tag-slots.ts` on the merged contact export. The contacts CSV needs `domain, full_name, title` and may carry `first_name, linkedin_url, email, email_status`; the accounts CSV needs `domain, company_name, headcount`. Domains are joined case-insensitively with scheme, `www.` and paths stripped, so a HubSpot `https://www.acme.com/` matches an Apollo `acme.com`.

One-time setup: `npm i yaml` in your project root (the folder that contains `.claude/`, or any folder above the skill). The script resolves the package from its own location, not from your shell's working directory. `npx tsx` needs no global install.

```
npx tsx scripts/tag-slots.ts \
  --contacts=contacts-raw.csv \
  --matrix=committee-config.yaml \
  --accounts=qualified-accounts.csv \
  --out=committee-map.csv \
  --report=coverage-report.md
```

The script:

- Assigns `slot` by matching `title` against the band's pattern list, first match wins, negatives checked first.
- A person who matches two slots keeps the higher-priority one (decision_maker > champion > blocker > influencer) and is removed from the other.
- Ranks within a slot by `confidence`, then by `email_status` (valid > catch_all > unknown), keeps the top 2.
- Writes unmatched titles with counts to the report.

Read the unmatched list. If one title appears 40 times and belongs in a slot, add it to the matrix and rerun. Do not hand-edit the CSV.

### Step 7: Read the coverage report and decide

Thresholds that mean the list is ready:

- At least 70% of accounts have a decision maker with a `valid` or `catch_all` email.
- At least 50% of accounts have two or more distinct slots filled.
- Fewer than 15% of accounts have zero people.

If a single slot is weak, widen that slot's titles for that band only. Do not loosen the whole matrix. If the decision maker slot is weak across the board, the account list itself is probably wrong (too many holding companies, too many subsidiaries), so go back to list-quality-scorecard.

### Step 8: Write the per-slot copy brief and hand off

One brief per slot. Each brief is four lines:

```
slot: decision_maker
audience: VP Sales, 51-200
opens_with: cost and risk (what this costs them today, what breaks if nothing changes)
same_claim: {shared_claim}
```

Decision maker gets cost and risk. Champion gets what they will be able to say internally. Influencer gets the daily pain. Blocker gets what you will not touch. All four carry the same `shared_claim` so the group can agree on what it is buying.

Hand off to campaign-copywriting (or whatever writes your copy) with `slot` as a custom field. It writes four variants, one per slot, not one email with four tweaks. Then smartlead-campaign-upload-public (or your sequencer's lead import) maps `slot` and `copy_brief_id` as custom fields.

Sequencing rules to pass along:

- Never send to all four slots on the same day. Stagger by at least 2 business days, decision maker last.
- When any slot replies, pause the other three at that account. The reply is now the thread.
- A title only gives you a likely champion. The real one is earned on the call, when someone starts selling it for you. Flip `champion_confirmed` to `true` then, and only then.

## Cost estimate

Costs vary by vendor and plan. Fill in your own per-credit price; the shape of the math is what matters.

```
accounts                      = 1,000
slots filled per account      = 3.1 (typical after collapse and gaps)
contacts kept                 = 3,100
search credits                = 16 searches (not 1,000)
email find credits            = 3,100 x {your_find_price}
verification                  = 3,100 x {your_verify_price}
```

Per-slot pulling costs roughly 3x to 4x the email-find credits of a one-contact-per-account pull, but almost nothing extra on search credits because the queries are tight. The savings show up in reply rate per account, not in credits. If the budget only covers one slot, run decision maker only and come back for the rest.

Claude Code usage: the tagging is a script, not a sub-agent. The interview and the 10-account dry run use Task sub-agents the same way icp-prompt-builder does.

## Errors and how to handle them

| Error                                              | Cause                                            | Fix                                                                                       |
| -------------------------------------------------- | ------------------------------------------------ | ----------------------------------------------------------------------------------------- |
| `headcount` blank on an account                    | Vendor did not return it                         | Default to band `51-200`, set `confidence` x 0.7, flag in report. Enrich headcount later. |
| Blocker slot empty at 80%+ of accounts             | No security/legal/procurement at that band       | Expected below 200 headcount. Collapse into decision maker, do not widen titles.          |
| Same person in two slots                           | Title matched two pattern lists                  | Script resolves by priority. If wrong, add the title to `negative_titles` of the loser.   |
| Influencer slot has 15 people at one account       | Uncapped pull                                    | `max_per_account` was ignored. Rerun tagger. Never upload more than 2 per slot.           |
| `email_status` catch_all on 40%+ of rows           | Catch-all domains in the list                    | Normal for enterprise. Route through email-deliverability-audit before sending volume.    |
| Titles returned in a non-English language          | Vendor returned localized titles                 | Add localized variants to the matrix for that geography. Do not translate at tag time.    |
| Prospeo returns 25K cap                            | Band plus title query too wide                   | Use prospeo-full-export, split by state or country.                                       |
| Account qualified but zero people found            | SMB with no LinkedIn footprint, or a holding co  | Route to blitz-list-builder for the owner; skip other slots; flag `no_people` in report.  |
| Decision maker at 1001+ is a CEO                   | Matrix copied small-band titles up               | At enterprise the CEO is never the decision maker for a departmental buy. Fix the band.   |
| Pattern matches "VP Sales Engineering" as sales DM | Missing negative                                 | Add `engineering` to `decision_maker.negative_titles` for that vertical.                  |

## Testing at scale

Run the loop three times before trusting the output:

1. **10 accounts** in the approval loop (Step 4). Converge.
2. **100 accounts** on the locked matrix. Check that per-slot fill rate is within 10 points of the 10-account run. If it drifts, the 10 were not representative; pick 10 new ones from the band that drifted.
3. **Full list.** Check the coverage thresholds in Step 7 and the unmatched-title list. Then send the first 200 per slot and watch bounce rate by slot. Bounces concentrated in one slot mean that slot's titles are matching stale people (common with "head of" titles at startups that have since reorganized).

## Learnings

From an MCP-adopter list run in October 2026 (security and developer-tool vendors, committee mapped from GitHub stargazer signals plus title enrichment):

- 5,170 people scored 70 or higher. Split: 1,316 exec and founder (decision maker), 607 engineering leaders (champion), 3,000 engineers (influencer), 200 security roles (blocker). The committee was sorted before anyone wrote a line of copy.
- The influencer pool was 58% of all people. Without `max_per_account`, it would have been 70% of sends and the decision-maker emails would have landed in inboxes already warmed by three engineer emails from the same domain. Cap it.
- The blocker slot (security) was small by count but had the highest reply rate per send once the message led with what we would not touch. Small slot, do not skip it.
- Engineering leaders as champions converted to calls at a higher rate than execs, but execs were the ones who replied with "loop in X". The champion is earned on the call, not assigned by the matrix.
- At accounts under 50 people the matrix collapsed to two real people most of the time. Showing four rows for a 15-person company looks thorough and is actually noise.

## Common mistakes

- **One title list for all headcounts.** The single biggest source of wrong-slot matches.
- **Running the full list before the 10-account loop converges.** Four wrong people per account instead of one.
- **Finding emails for the whole search result.** Tag first, then find emails on survivors only.
- **Writing one email and swapping the first line per slot.** That is a blast with a costume. Each slot gets its own opener and the same claim.
- **Letting reps "add a couple more" from LinkedIn.** If the matrix missed them, fix the matrix. The list is the source of truth.
- **Treating the title-assigned champion as the champion.** It is a guess until someone starts selling internally for you.

## Scripts and references

- `scripts/tag-slots.ts`: assigns slots from the matrix, dedupes, ranks, writes the map and the coverage report. Requires `npm i yaml` in your project root (CSV is handled in-script, no API keys). Accepts `--vertical=<key>` when the matrix file is `references/slot-title-matrix.yaml`. Run `npx tsx scripts/tag-slots.ts --help`.
- `scripts/fixtures/`: a 5-account, 13-contact sample (one blank headcount, one collapse, one negative-title hit). Smoke test: `npx tsx scripts/tag-slots.ts --contacts=scripts/fixtures/contacts.csv --matrix=scripts/fixtures/committee-config.yaml --accounts=scripts/fixtures/accounts.csv --out=/tmp/map.csv --report=/tmp/report.md` should write 9 rows.
- `references/slot-title-matrix.yaml`: starting matrices for three verticals (`sales_tooling`, `developer_and_security_tooling`, `marketing_and_demand_gen`). Load directly with `--vertical=<key>` for the dry run, then copy the closest one into `committee-config.yaml` and edit from the interview.

## Recommended flow

1. icp-onboarding to produce `client-profile.yaml`
2. list-builder, disco-like, blitz-list-builder, or prospeo-full-export to pull accounts
3. icp-prompt-builder to qualify them (converge, lock)
4. **buying-committee-mapper** (this skill) to map four slots per qualified account
5. list-quality-scorecard on `committee-map.csv`
6. campaign-copywriting with `slot` as the variant key (four variants)
7. smartlead-campaign-upload-public with `slot` and `copy_brief_id` as custom fields

## What to do next

**Grade the map** with list-quality-scorecard, then **write the four variants** with campaign-copywriting. If the champion slot ever fills below 40%, run playbook-name-to-other-prospects on the decision maker rows so the first email asks "is this you or someone on your team", which recovers the champion from the reply instead of the matrix.

## Related skills

- icp-prompt-builder: run FIRST unless the list is already qualified another way. This skill refuses unqualified lists.
- icp-onboarding: produces the `client-profile.yaml` this skill appends to.
- prospeo-search-api, blitz-list-builder, clay-playbooks: the per-slot pulls.
- list-quality-scorecard: grades `committee-map.csv` before upload.
- campaign-copywriting: consumes the four copy briefs.
- playbook-name-to-other-prospects: the fallback when a slot will not fill from titles.
- personalization-subagent-pattern: same approval-loop pattern, applied to per-row copy.
