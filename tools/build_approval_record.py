"""Build the reviewed representation of the approval record from the document.

Usage: build_approval_record.py <repo-root> <output-path>

Never reads reply-tables/tiktok.json: the record is derived from
docs/reply-table-tiktok.md alone, so comparing the two is a real check.

Its output is *reviewed* before it is committed, not trusted because it was
generated. Re-running it against a changed document produces a diff to read --
never overwrite tests/fixtures/approval_record_tiktok.json without reading that
diff, because the fixture is what the production table is checked against and a
mechanically accepted regeneration would launder a wrong transcription into an
approved one.
"""
import json, pathlib, re, sys

W = pathlib.Path(sys.argv[1])
OUT = pathlib.Path(sys.argv[2])
sys.path.insert(0, str(W))
from agent.normalize import bare_interjection  # noqa: E402

DOC = W / "docs" / "reply-table-tiktok.md"
lines = DOC.read_text().splitlines()

def spans(line):
    return re.findall(r"`([^`]+)`", line)

def find_line(text, lo, hi):
    """Line number of a quoted string, allowing for the document's wrapping."""
    joined = " ".join(lines[lo - 1:hi])
    needle = text if len(text) <= 25 else text[:25]
    i = joined.find(needle)
    if i < 0:
        return []
    pos = 0
    for n in range(lo, hi + 1):
        seg = lines[n - 1]
        if i < pos + len(seg):
            return [n]
        pos += len(seg) + 1
    return [hi]

SECTIONS = {
    "tt-doa-001": (140, 179), "tt-doa-002": (180, 214), "tt-praise-001": (215, 238),
    "tt-greet-001": (239, 276), "tt-doareq-001": (277, 323), "tt-thanks-001": (324, 370),
    "tt-convert-001": (371, 395), "tt-join-001": (396, 473), "tt-donate-001": (474, 512),
    "tt-zakat-001": (513, 559),
}
PHRASINGS = {
    "tt-doa-001": (830, 838), "tt-doa-002": (839, 847), "tt-praise-001": (848, 856),
    "tt-greet-001": (857, 874), "tt-doareq-001": (875, 886), "tt-thanks-001": (887, 895),
    "tt-convert-001": (896, 912), "tt-donate-001": (913, 941), "tt-zakat-001": (913, 941),
}
META = {
    "tt-doa-001": ("DOA_BLESSING", "ms", "approved", 0.65),
    "tt-doa-002": ("DOA_BLESSING", "en", "approved", 0.65),
    "tt-praise-001": ("PRAISE_ENCOURAGE", "ms", "approved", 0.65),
    "tt-greet-001": ("GREETING", "ms", "approved", 0.65),
    "tt-doareq-001": ("DOA_REQUEST", "ms", "approved", 0.65),
    "tt-thanks-001": ("BENEFICIARY_THANKS", "ms", "approved", 0.65),
    "tt-convert-001": ("CONVERT_CONGRATS", "ms", "approved", 0.65),
    "tt-join-001": ("JOIN_ENQUIRY", "ms", "escalate", 0.2),
    "tt-donate-001": ("DONATION_ENQUIRY", "ms", "approved", 0.9),
    "tt-zakat-001": ("ZAKAT_SEDEKAH_ENQUIRY", "ms", "approved", 0.9),
}
# Verbatim from the document's own `matching_criteria` bullets where it has one.
CRITERIA = {
    "tt-doa-001": ("a prayer or blessing with no request in it", "verbatim", 143),
    "tt-praise-001": ("praise or encouragement with no request and no explicit doa", "verbatim", 218),
    "tt-greet-001": ("a salutation carrying no other content", "verbatim", 242),
    "tt-doareq-001": ("the commenter asking to be prayed for — a request whose object is the commenter's own wish, not the organisation's help", "verbatim", 280),
    "tt-thanks-001": ("thanks from someone the organisation has already helped", "verbatim", 327),
    "tt-donate-001": ("a Comment asking how to contribute, give, or send money", "verbatim", 485),
    "tt-zakat-001": ("a Comment that names zakat, sedekah or infaq and asks how to pay it", "verbatim", 527),
}
# Routing prose only: the document states these Intents but gives no `matching_criteria`
# bullet, so these are derived summaries and are not asserted verbatim.
DERIVED = {
    "tt-doa-002": "a prayer or blessing written in English or mixed English-Malay, with no request in it",
    "tt-convert-001": "congratulating or blessing someone on embracing Islam; eligible only on a conversion Post",
    "tt-join-001": "a commenter asking to join, participate in, or become part of the organisation's work",
}
EXCLUDE = {
    "tt-doareq-001": [("tolong doa", "prose_descriptor_not_a_variant")],
    "tt-donate-001": [("HELP_REQUEST", "documented_cross_reference"),
                      ("tolong", "prose_descriptor_not_a_variant")],
    "tt-join-001": [("macam mana nak mohon. sy oku fizikal and now tgah hadapi risiko buta kekal. from klang", "matched_but_not_this_intent"),
                    ("MCM mna nak moham saya OKU pesakit stroke", "matched_but_not_this_intent")],
    "tt-zakat-001": [("Alhamdulillah... Semoga En Gary terus istiqamah dgn Islam hingga ke jannah.. Aamiinn, semoga mereka yang kembali ke agama fitrah terus mndpt bimbingan yg sewajarnya.. Aamiinn", "documented_false_positive"),
                     ("Alhamdulillah. bertuahnya. Kembali kpd fitrah", "documented_false_positive"),
                     ("Alhamdulillah ugama yang fitrah 🥰🥰🥰🥰🥰🥰🥰", "documented_false_positive"),
                     ("@Ben Ooi assalamualaikum.. Abg yang terlantar ni dah meninggal kan kita semua. Sedekah kan Al-Fatihah buat Salim Bin Othman. Semoga Allah menempatkan nya bersama hambaNya yg beriman.. aamiin", "documented_false_positive")],
    "tt-doa-002": [("Walakomsalam from Myanmar 🇲🇲 Allah bless you", "documented_not_this_intent"),
                   ("you reply me", "documented_not_this_intent")],
}
FIELD_WORDS = {"approved_reply", "matching_criteria", "known_variants", "language",
               "minimum_match_threshold", "reply_id", "intent", "approved_phrasings",
               "matched_but_not_this_intent"}
JUNK = {"join", "sertai", "fitrah", "tt-donate-001"}

def variant_block(rid):
    a, b = SECTIONS[rid]
    start = next(n for n in range(a, b + 1) if lines[n - 1].startswith("- `known_variants`"))
    found = []
    for n in range(start, b + 1):
        line = lines[n - 1]
        stripped = line.strip()
        if n > start:
            if not stripped:
                continue
            if re.match(r"^\s*-\s+\*\*", line):   # prose bullet ends the list
                break
            if line[:1].isspace() or stripped.startswith("- "):
                pass                              # bullet or its wrapped continuation
            else:
                break                             # flush-left prose ends the list
        for t in spans(line):
            if t in FIELD_WORDS or t in JUNK or len(t) < 3:
                continue
            found.append({"text": t, "doc_lines": [n]})
    excl_map = {t: r for t, r in EXCLUDE.get(rid, [])}
    keep, dropped = [], []
    for o in found:
        if o["text"] in excl_map:
            continue
        if bare_interjection(o["text"]):
            dropped.append({"text": o["text"], "reason": "bare_formula_is_no_reply_adr_0018",
                            "doc_lines": o["doc_lines"]})
        else:
            keep.append({**o, "label": "observed"})
    for text, reason in EXCLUDE.get(rid, []):
        dl = find_line(text, a, b)
        dropped.append({"text": text, "reason": reason, "doc_lines": dl})
    return keep, dropped

def phrasings_of(rid):
    if rid not in PHRASINGS:
        return []
    a, b = PHRASINGS[rid]
    rows = []
    for n in range(a, b + 1):
        m = re.match(r"^\|\s*(\d+)\s*\|\s*(.*?)\s*\|\s*$", lines[n - 1])
        if m:
            rows.append((n, m.group(2)))
    if rid == "tt-zakat-001":
        rows = [(n, t) for n, t in rows]
    out = []
    for n, cell in rows:
        t = cell.strip().replace("*", "").replace("<br>", "\n")
        out.append({"text": t, "doc_lines": [n]})
    # rows the document abbreviates by reference
    # "The bank, account number and payee are the Account holder's verbatim words,
    # identical in every row ... Only the courtesy line above the block varies."
    # So the referenced block is row 1's text *below* its courtesy line.
    block = out[0]["text"].split("\n\n", 1)[1] if out and "\n\n" in out[0]["text"] else ""
    for item in out:
        if item["text"].rstrip().endswith("(block as row 1, verbatim)"):
            head = item["text"].split("\n")[0].strip()
            item["text"] = head + "\n\n" + block
            item["expanded_from_reference"] = True
    return out

def sign_off(rid):
    for n in range(779, 802):
        line = lines[n - 1]
        if line.startswith("| `%s`" % rid):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            text = cells[2].replace("*", "").replace("<br>", "\n")
            if text.startswith("same text as"):
                return None
            return {"text": text, "doc_lines": [n]}
    return None

record = []
for rid, (a, b) in SECTIONS.items():
    intent, lang, status, thr = META[rid]
    if rid in CRITERIA:
        crit, src, cl = CRITERIA[rid]
        crit_doc = [cl]
    else:
        crit, src, crit_doc = DERIVED[rid], "derived", []
    keep, dropped = variant_block(rid)
    rec = {
        "reply_id": rid, "intent": intent, "language": lang, "status": status,
        "doc_lines": [a, b],
        "matching_criteria": crit, "matching_criteria_source": src, "matching_criteria_doc_lines": crit_doc,
        "minimum_match_threshold": thr,
        "approved_phrasings": phrasings_of(rid),
        "known_variants": keep,
        "variants_not_carried": dropped,
    }
    so = sign_off(rid)
    if so is None and rid == "tt-zakat-001":
        donor = next(r for r in record if r["reply_id"] == "tt-donate-001")
        rec["sign_off_text"] = donor["sign_off_text"]
        rec["sign_off_doc_lines"] = donor["sign_off_doc_lines"]
        rec["sign_off_is_reference"] = True
    else:
        rec["sign_off_text"] = so["text"] if so else None
        rec["sign_off_doc_lines"] = so["doc_lines"] if so else []
    record.append(rec)

payload = {
    "note": "Reviewed representation of docs/reply-table-tiktok.md for transcription fidelity tests. "
            "Derived from the document only, never from reply-tables/tiktok.json. Every string carries "
            "the document lines it came from.",
    "source_document": "docs/reply-table-tiktok.md",
    "intents_with_no_text": ["HELP_REQUEST", "JOIN_ENQUIRY"],
    "entries": record,
    # The document states the numbers' uncertainty once, for the whole table (line
    # 961), so the record carries it once too rather than on each entry.
    "threshold_status": "provisional",
    "threshold_status_doc_lines": [961],
    "threshold_status_note": (
        "The document states the numbers' uncertainty once, for the whole table, not per entry: "
        "'Those numbers are provisional, because they are claims about Jev's per-Comment "
        "confidences and the Router does not exist in this repository.' There is therefore no "
        "per-entry calibration status, and the production table carries none."
    ),
}
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
print("wrote", OUT)
for rec in record:
    print("%-16s %-24s %-11s phrasings %d  variants %2d  not-carried %2d" % (
        rec["reply_id"], rec["intent"], rec["status"],
        len(rec["approved_phrasings"]), len(rec["known_variants"]), len(rec["variants_not_carried"])))
