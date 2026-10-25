"""Label each unique email (by content hash) with the skill's own taxonomy, once, using Claude Haiku.

Labels are parsed from the skill files at runtime so classifications stay aligned with the text humans edit:
  archetype        <- cold-email/copy-frameworks/SKILL.md         "#### Archetype N: The X"
  subject_formula  <- campaign-analytics/winning-copy-extraction   "#### Subject Line Patterns" table
  opener           <- same file                                    "#### Opening Line Patterns" table
  cta_pattern      <- same file                                    "#### CTA Patterns" table
"""
import argparse
import json
import re
from pathlib import Path

import anthropic

import db
from pull_outcomes import load_env

ROOT = Path(__file__).resolve().parent.parent
COPY_SKILL = ROOT / "cold-email" / "copy-frameworks" / "SKILL.md"
EXTRACT_SKILL = ROOT / "campaign-analytics" / "winning-copy-extraction" / "SKILL.md"
MODEL = "claude-haiku-5-5"   # bulk classification: cheap model by design (see CLAUDE.md cost rules)


def table_labels(text, heading):
    """First-column labels of the markdown table that follows `heading`."""
    m = re.search(rf"^#### {re.escape(heading)}\s*\n(.*?)(?=^#### |^### |\Z)", text, re.S | re.M)
    if not m:
        return []
    labels = []
    for line in m.group(1).splitlines():
        if line.startswith("|") and not re.match(r"^\|\s*-", line) and "Pattern" not in line.split("|")[1]:
            cell = line.split("|")[1].strip().strip("*").strip("`")
            if cell:
                labels.append(cell)
    return labels


def taxonomy():
    copy_text, extract_text = COPY_SKILL.read_text(), EXTRACT_SKILL.read_text()
    return {
        "archetype": re.findall(r"^#### Archetype \d+: (The .+)$", copy_text, re.M) + ["Other"],
        "subject_formula": table_labels(extract_text, "Subject Line Patterns") + ["Other"],
        "opener": table_labels(extract_text, "Opening Line Patterns") + ["Other"],
        "cta_pattern": table_labels(extract_text, "CTA Patterns") + ["Other"],
    }


def schema(tax):
    return {"type": "object", "additionalProperties": False,
            "required": list(tax),
            "properties": {k: {"type": "string", "enum": v} for k, v in tax.items()}}


def classify(client, tax, subject, body, model=MODEL):
    prompt = (f"Classify this cold outreach message using the exact labels given. Pick 'Other' when nothing fits.\n\n"
              f"SUBJECT: {subject or '(none)'}\n\nBODY:\n{body}")
    r = client.messages.create(
        model=model, max_tokens=512, output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema(tax)}},
        system="You label B2B cold email and LinkedIn copy for a GTM analytics pipeline. Output only the JSON.",
        messages=[{"role": "user", "content": prompt}])
    if r.stop_reason == "refusal":
        return None
    return json.loads(next(b.text for b in r.content if b.type == "text"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=db.DB_PATH)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--limit", type=int, default=500)
    ap.add_argument("--dry-run", action="store_true", help="print how many emails would be classified")
    a = ap.parse_args(argv)
    load_env()
    con = db.connect(a.db)
    todo = con.execute("""SELECT DISTINCT content_hash, subject, body FROM step
                          WHERE step_no > 0 AND body IS NOT NULL AND body != ''
                            AND content_hash NOT IN (SELECT content_hash FROM classification)
                          LIMIT ?""", (a.limit,)).fetchall()
    print(f"{len(todo)} unclassified emails (cache hits skipped)")
    if a.dry_run or not todo:
        return
    tax = taxonomy()
    client = anthropic.Anthropic()
    done = 0
    for row in todo:
        labels = classify(client, tax, row["subject"], row["body"], a.model)
        if labels is None:
            continue
        con.execute("INSERT OR REPLACE INTO classification VALUES (?,?,?,?,?,?,?,?)",
                    (row["content_hash"], labels["archetype"], labels["subject_formula"], labels["opener"],
                     labels["cta_pattern"], len(row["body"].split()), a.model, json.dumps(labels)))
        con.commit()
        done += 1
    print(f"classified {done} with {a.model}")


if __name__ == "__main__":
    main()
