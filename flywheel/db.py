"""SQLite store for outreach outcomes. One file, stdlib only.

Normalized row shapes (plain dicts) every adapter must emit:
  campaign: {tool, id, name}
  step:     {tool, campaign_id, step_no, variant, channel, subject, body}
            step_no 0 = campaign-level pseudo-step for tools without per-step stats
            variant is a short label: "A", "B", ... ("A" when the tool has no variants)
  stat:     {tool, campaign_id, step_no, variant, as_of, sends, replies, positive, meetings}
            positive / meetings may be None when the tool does not expose them
  lead:     {tool, campaign_id, step_no, variant, email, status, replied, positive, meeting, as_of}
            email is hashed on insert (lead_key); only email_hash + domain are stored. step_no/variant may be None.
  signal:   {domain, type, party, event_date, source_url}   (party: first | second | third)
"""
import hashlib
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "outcomes.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS campaign (
  tool TEXT NOT NULL, id TEXT NOT NULL, name TEXT,
  PRIMARY KEY (tool, id));
CREATE TABLE IF NOT EXISTS step (
  tool TEXT NOT NULL, campaign_id TEXT NOT NULL, step_no INTEGER NOT NULL, variant TEXT NOT NULL,
  channel TEXT, subject TEXT, body TEXT, content_hash TEXT NOT NULL,
  PRIMARY KEY (tool, campaign_id, step_no, variant));
CREATE TABLE IF NOT EXISTS stat (
  tool TEXT NOT NULL, campaign_id TEXT NOT NULL, step_no INTEGER NOT NULL, variant TEXT NOT NULL,
  as_of TEXT NOT NULL, sends INTEGER, replies INTEGER, positive INTEGER, meetings INTEGER,
  PRIMARY KEY (tool, campaign_id, step_no, variant, as_of));
CREATE TABLE IF NOT EXISTS lead_outcome (
  tool TEXT NOT NULL, campaign_id TEXT NOT NULL, step_no INTEGER, variant TEXT,
  email_hash TEXT NOT NULL, domain TEXT, status TEXT, replied INTEGER, positive INTEGER, meeting INTEGER, as_of TEXT NOT NULL,
  PRIMARY KEY (tool, campaign_id, email_hash));
CREATE TABLE IF NOT EXISTS signal (
  domain TEXT NOT NULL, type TEXT NOT NULL, party TEXT NOT NULL, event_date TEXT NOT NULL, source_url TEXT,
  PRIMARY KEY (domain, type, event_date));
CREATE TABLE IF NOT EXISTS classification (
  content_hash TEXT PRIMARY KEY, archetype TEXT, subject_formula TEXT, opener TEXT,
  cta_pattern TEXT, word_count INTEGER, model TEXT, raw_json TEXT);
"""


FREEMAIL = {"gmail.com", "googlemail.com", "yahoo.com", "hotmail.com", "outlook.com", "live.com", "icloud.com",
            "aol.com", "proton.me", "protonmail.com", "gmx.com", "yandex.com", "me.com", "msn.com"}


def lead_key(email):
    """(email_hash, domain) for a lead. Raw email never reaches the database."""
    e = (email or "").strip().lower()
    if "@" not in e:
        return None, None
    return hashlib.sha256(e.encode()).hexdigest()[:16], e.split("@", 1)[1]


def content_hash(subject, body):
    return hashlib.sha256(f"{subject or ''}\n---\n{body or ''}".encode()).hexdigest()[:16]


def connect(path=DB_PATH):
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def upsert(con, rows):
    """rows = {"campaigns": [...], "steps": [...], "stats": [...]} as produced by an adapter."""
    con.executemany(
        "INSERT OR REPLACE INTO campaign (tool,id,name) VALUES (:tool,:id,:name)",
        rows.get("campaigns", []))
    con.executemany(
        "INSERT OR REPLACE INTO step (tool,campaign_id,step_no,variant,channel,subject,body,content_hash) "
        "VALUES (:tool,:campaign_id,:step_no,:variant,:channel,:subject,:body,:content_hash)",
        [{**s, "channel": s.get("channel", "email"), "content_hash": content_hash(s.get("subject"), s.get("body"))}
         for s in rows.get("steps", [])])
    con.executemany(
        "INSERT OR REPLACE INTO stat (tool,campaign_id,step_no,variant,as_of,sends,replies,positive,meetings) "
        "VALUES (:tool,:campaign_id,:step_no,:variant,:as_of,:sends,:replies,:positive,:meetings)",
        [{"positive": None, "meetings": None, **s} for s in rows.get("stats", [])])
    leads = []
    for l in rows.get("leads", []):
        h, dom = lead_key(l.get("email"))
        if h:
            leads.append({"step_no": None, "variant": None, "replied": None, "positive": None, "meeting": None, **l, "email_hash": h, "domain": dom})
    con.executemany(
        "INSERT OR REPLACE INTO lead_outcome (tool,campaign_id,step_no,variant,email_hash,domain,status,replied,positive,meeting,as_of) "
        "VALUES (:tool,:campaign_id,:step_no,:variant,:email_hash,:domain,:status,:replied,:positive,:meeting,:as_of)", leads)
    con.executemany(
        "INSERT OR REPLACE INTO signal (domain,type,party,event_date,source_url) "
        "VALUES (:domain,:type,:party,:event_date,:source_url)",
        [{"source_url": None, **s, "domain": (s["domain"] or "").strip().lower()} for s in rows.get("signals", [])])
    con.commit()
