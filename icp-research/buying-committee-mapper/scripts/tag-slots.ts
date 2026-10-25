#!/usr/bin/env tsx
/**
 * Tag every contact with a buying-committee slot, dedupe, rank, and write the
 * coverage report. See ../SKILL.md, Step 6.
 *
 * Usage:
 *   npx tsx scripts/tag-slots.ts \
 *     --contacts=contacts-raw.csv \
 *     --matrix=committee-config.yaml \
 *     --accounts=qualified-accounts.csv \
 *     --out=committee-map.csv \
 *     --report=coverage-report.md
 *
 * contacts CSV: domain, full_name, title [, first_name, linkedin_url, email, email_status]
 * accounts CSV: domain, company_name, headcount
 * matrix YAML:  the `buying_committee:` block from committee-config.yaml (top level or nested)
 *
 * Requires: npm i yaml
 */

import { readFileSync, writeFileSync } from "fs";

// ---------- CLI ----------

const args = Object.fromEntries(
  process.argv.slice(2).map((a) => {
    const [k, ...v] = a.replace(/^--/, "").split("=");
    return [k, v.join("=")];
  }),
);

if ("help" in args || !args.contacts || !args.matrix || !args.accounts) {
  console.error(`usage: npx tsx scripts/tag-slots.ts --contacts=F --matrix=F --accounts=F [--out=committee-map.csv] [--report=coverage-report.md] [--vertical=NAME]

  contacts CSV  domain, full_name, title  [+ first_name, linkedin_url, email, email_status]  (any vendor export works)
  accounts CSV  domain, company_name, headcount
  matrix YAML   a buying_committee: block, or references/slot-title-matrix.yaml with --vertical=<key> to pick one
  headcount     a number; a range like "51-200" is read as its low end
  Domains are joined case-insensitively; scheme, www. and paths are stripped on both sides.
  Needs the yaml package: run \`npm i yaml\` in your project root (any folder above this script).`);
  process.exit("help" in args ? 0 : 1);
}
const OUT = args.out || "committee-map.csv";
const REPORT = args.report || "coverage-report.md";

// ---------- CSV (RFC 4180, no deps) ----------

function parseCsv(text: string): Record<string, string>[] {
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) {
      if (c === '"') {
        if (text[i + 1] === '"') { cell += '"'; i++; } else q = false;
      } else cell += c;
    } else if (c === '"') q = true;
    else if (c === ",") { row.push(cell); cell = ""; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(cell); rows.push(row); row = []; cell = "";
    } else cell += c;
  }
  if (cell !== "" || row.length) { row.push(cell); rows.push(row); }
  const [header, ...body] = rows.filter((r) => r.some((x) => x !== ""));
  const keys = header.map((h) => h.trim().toLowerCase());
  return body.map((r) => Object.fromEntries(keys.map((k, i) => [k, (r[i] ?? "").trim()])));
}

function toCsv(rows: Record<string, unknown>[], cols: string[]): string {
  const esc = (v: unknown) => {
    const s = v === undefined || v === null ? "" : String(v);
    return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [cols.join(","), ...rows.map((r) => cols.map((c) => esc(r[c])).join(","))].join("\n") + "\n";
}

// ---------- Matrix ----------

type Slot = "decision_maker" | "champion" | "blocker" | "influencer";
const PRIORITY: Slot[] = ["decision_maker", "champion", "blocker", "influencer"]; // higher first
const PREFIX: Record<Slot, string> = { decision_maker: "dm", champion: "ch", influencer: "inf", blocker: "blk" };

interface SlotCfg {
  titles_by_band: Record<string, string[]>;
  negative_titles?: string[];
  max_per_account?: number;
  collapse_below_headcount?: number;
}
interface Matrix {
  bands: { id: string; min: number; max: number | null }[];
  slots: Record<Slot, SlotCfg>;
}

async function loadMatrix(path: string): Promise<Matrix> {
  let YAML: { parse: (s: string) => unknown };
  try {
    YAML = await import("yaml");
  } catch {
    console.error("Missing dependency `yaml`: run `npm i yaml` in your project root (any folder above this script) and retry.");
    process.exit(1);
  }
  const doc = YAML.parse(readFileSync(path, "utf8")) as Record<string, unknown>;
  let m = (doc.buying_committee ?? doc) as Matrix;
  const verticals = doc.verticals as Record<string, { slots: Matrix["slots"] }> | undefined;
  if (verticals) {
    const v = verticals[args.vertical ?? ""];
    if (!v) { console.error(`${path} has verticals; pass --vertical=<${Object.keys(verticals).join("|")}>`); process.exit(1); }
    m = { bands: m.bands, slots: v.slots };
  }
  if (!m.bands || !m.slots) {
    console.error(`${path}: expected a buying_committee block with bands and slots`);
    process.exit(1);
  }
  return m;
}

const DEFAULT_BAND = "51-200";
function bandFor(headcount: string, bands: Matrix["bands"]): { band: string; blank: boolean } {
  const n = parseInt(headcount.replace(/,/g, "").match(/\d+/)?.[0] ?? "", 10); // "51-200" -> 51, "5,000" -> 5000
  if (!n) return { band: DEFAULT_BAND, blank: true };
  const b = bands.find((x) => n >= x.min && (x.max === null || n <= x.max));
  return { band: b ? b.id : DEFAULT_BAND, blank: !b };
}

const domainKey = (d: string) => d.toLowerCase().trim().replace(/^https?:\/\//, "").replace(/^www\./, "").replace(/\/.*$/, "");
const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9&+ ]+/g, " ").replace(/\s+/g, " ").trim();
const rx = (p: string) => new RegExp(`(^|[^a-z0-9])${p.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}([^a-z0-9]|$)`, "i");

function matchSlot(title: string, band: string, slots: Matrix["slots"]): { slot: Slot; rule: string; conf: number } | null {
  const t = norm(title);
  if (!t) return null;
  for (const slot of PRIORITY) {
    const cfg = slots[slot];
    if (!cfg) continue;
    if ((cfg.negative_titles ?? []).some((n) => rx(norm(n)).test(t))) continue;
    const patterns = cfg.titles_by_band?.[band] ?? [];
    for (let i = 0; i < patterns.length; i++) {
      const p = norm(patterns[i]);
      if (t === p) return { slot, rule: `${PREFIX[slot]}-${String(i + 1).padStart(2, "0")}`, conf: 0.95 };
      if (rx(p).test(t)) return { slot, rule: `${PREFIX[slot]}-${String(i + 1).padStart(2, "0")}`, conf: 0.85 };
    }
  }
  return null;
}

// ---------- Main ----------

const EMAIL_RANK: Record<string, number> = { valid: 3, catch_all: 2, unknown: 1, not_found: 0 };
const COLS = [
  "domain", "company_name", "headcount", "headcount_band", "slot", "slot_rank", "slot_collapsed",
  "full_name", "first_name", "title", "title_match_rule", "linkedin_url", "email", "email_status",
  "confidence", "copy_brief_id", "champion_confirmed",
];

async function main() {
  const matrix = await loadMatrix(args.matrix);
  const accounts = parseCsv(readFileSync(args.accounts, "utf8"));
  const contacts = parseCsv(readFileSync(args.contacts, "utf8"));
  const acct = new Map(accounts.map((a) => [domainKey(a.domain ?? ""), a]));

  const unmatched = new Map<string, number>();
  let skipped = 0;
  let blankHeadcount = 0;
  const tagged: Record<string, unknown>[] = [];

  for (const c of contacts) {
    const a = acct.get(domainKey(c.domain ?? ""));
    if (!a) { skipped++; continue; } // not a qualified account
    const { band, blank } = bandFor(a.headcount ?? "", matrix.bands);
    const m = matchSlot(c.title ?? "", band, matrix.slots);
    if (!m) {
      const k = (c.title ?? "").trim() || "(blank)";
      unmatched.set(k, (unmatched.get(k) ?? 0) + 1);
      continue;
    }
    if (blank) blankHeadcount++;
    tagged.push({
      domain: a.domain, company_name: a.company_name ?? "", headcount: a.headcount ?? "", headcount_band: band,
      slot: m.slot, slot_rank: 0, slot_collapsed: false,
      full_name: c.full_name ?? "", first_name: c.first_name ?? "", title: c.title ?? "", title_match_rule: m.rule,
      linkedin_url: c.linkedin_url ?? "", email: c.email ?? "", email_status: c.email_status || "unknown",
      confidence: +(m.conf * (blank ? 0.7 : 1)).toFixed(2), copy_brief_id: PREFIX[m.slot], champion_confirmed: false,
    });
  }

  // Rank within (domain, slot), keep top N.
  const groups = new Map<string, Record<string, unknown>[]>();
  for (const r of tagged) {
    const k = `${r.domain}\u0000${r.slot}`;
    (groups.get(k) ?? groups.set(k, []).get(k)!).push(r);
  }
  const out: Record<string, unknown>[] = [];
  for (const [k, rows] of groups) {
    const slot = k.split("\u0000")[1] as Slot;
    const cap = Math.min(2, matrix.slots[slot]?.max_per_account ?? 2);
    rows.sort((x, y) =>
      (y.confidence as number) - (x.confidence as number) ||
      (EMAIL_RANK[y.email_status as string] ?? 0) - (EMAIL_RANK[x.email_status as string] ?? 0));
    rows.slice(0, cap).forEach((r, i) => out.push({ ...r, slot_rank: i + 1 }));
  }

  // Collapse blocker into decision maker below the threshold.
  const collapseBelow = matrix.slots.blocker?.collapse_below_headcount ?? 50;
  const byDomain = new Map<string, Record<string, unknown>[]>();
  for (const r of out) (byDomain.get(r.domain as string) ?? byDomain.set(r.domain as string, []).get(r.domain as string)!).push(r);
  for (const [domain, rows] of byDomain) {
    const hc = parseInt((rows[0].headcount as string).replace(/,/g, "").match(/\d+/)?.[0] ?? "", 10);
    const hasBlocker = rows.some((r) => r.slot === "blocker");
    const dm = rows.find((r) => r.slot === "decision_maker" && r.slot_rank === 1);
    if (hc && hc < collapseBelow && !hasBlocker && dm) {
      const row = { ...dm, slot: "blocker", slot_rank: 1, slot_collapsed: true, copy_brief_id: "blk" };
      out.push(row); rows.push(row);
    }
  }

  out.sort((x, y) =>
    String(x.domain).localeCompare(String(y.domain)) ||
    PRIORITY.indexOf(x.slot as Slot) - PRIORITY.indexOf(y.slot as Slot) ||
    (x.slot_rank as number) - (y.slot_rank as number));
  writeFileSync(OUT, toCsv(out, COLS));

  // ---------- Report ----------
  const nAcc = accounts.length;
  const pct = (n: number) => (nAcc ? `${((100 * n) / nAcc).toFixed(0)}%` : "n/a");
  const slotFill = (s: Slot, pred: (r: Record<string, unknown>) => boolean = () => true) =>
    new Set(out.filter((r) => r.slot === s && pred(r)).map((r) => r.domain)).size;
  const slotsPerDomain = new Map<string, Set<string>>();
  for (const r of out) (slotsPerDomain.get(r.domain as string) ?? slotsPerDomain.set(r.domain as string, new Set()).get(r.domain as string)!).add(r.slot as string);
  const full = [...slotsPerDomain.values()].filter((s) => s.size === 4).length;
  const twoPlus = [...slotsPerDomain.values()].filter((s) => s.size >= 2).length;
  const zero = nAcc - slotsPerDomain.size;
  const dmEmail = slotFill("decision_maker", (r) => r.email_status === "valid" || r.email_status === "catch_all");

  const top = [...unmatched.entries()].sort((a, b) => b[1] - a[1]).slice(0, 20);
  const report = [
    `# Coverage report`,
    ``,
    `Accounts: ${nAcc}. Contacts in: ${contacts.length}. Skipped (domain not in accounts CSV): ${skipped}. Rows out: ${out.length}.`,
    ``,
    `## Per-slot fill (accounts with at least one person)`,
    ``,
    `| Slot | Accounts | Share |`,
    `|---|---|---|`,
    ...PRIORITY.map((s) => `| ${s} | ${slotFill(s)} | ${pct(slotFill(s))} |`),
    ``,
    `## Readiness (Step 7 thresholds)`,
    ``,
    `- Decision maker with valid/catch_all email: ${dmEmail} (${pct(dmEmail)}) — need 70%`,
    `- Two or more slots filled: ${twoPlus} (${pct(twoPlus)}) — need 50%`,
    `- Zero people: ${zero} (${pct(zero)}) — need under 15%`,
    `- Full four-slot committee: ${full} (${pct(full)})`,
    `- Rows tagged with blank headcount (defaulted to ${DEFAULT_BAND}, confidence x0.7): ${blankHeadcount}`,
    ``,
    `## Top unmatched titles`,
    ``,
    `| Title | Count |`,
    `|---|---|`,
    ...top.map(([t, n]) => `| ${t.replace(/\|/g, "/")} | ${n} |`),
    ``,
  ].join("\n");
  writeFileSync(REPORT, report);
  console.log(`wrote ${OUT} (${out.length} rows) and ${REPORT}`);
}

main();
