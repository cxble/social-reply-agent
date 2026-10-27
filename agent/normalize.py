"""Normalization for TikTok Comments, and the bare-formula test.

This is the Normalization step `docs/reply-routing.md` describes: fold the informal
Malay/English spellings that actually appear in the corpus down to a canonical
form, so that `semuga`, `smoga`, `smg` and `moga` are one thing to match on.

Two rules the corpus forced:

  1. Collapse 3+ repeats before the dictionary runs, so `bagusss` -> `baguss` and
     `aaminnn` -> `aaminn` rather than needing an entry per spelling.
  2. Never touch the Comment as stored. Normalization is derived, and the Reply
     quotes nothing from it.

`bare_interjection` exists because 231 Comments (16%) are a religious formula and
nothing else. They are `OUT_OF_SCOPE` -- answered with nothing -- and the test has
to be "every word is a formula word", not "contains a formula word", or
`alhamdulillah semoga cepat sembuh` would be swept in with bare `alhamdulillah`.

This module is the implementation; `tools/normalize.py` is the shim that lets the
tools under `tools/` import it when run as scripts.
"""

from __future__ import annotations

import re

# Informal spellings seen in Malaysian comment sections. Every entry should be
# traceable to a real Comment -- this is drafted from the corpus, not guessed.
NORMALIZE = {
    "x": "tak", "takde": "tak ada", "takdak": "tak ada",
    "nk": "nak", "nok": "nak", "na": "nak",
    "sy": "saya", "aku": "saya", "aq": "saya", "sye": "saya",
    "yg": "yang", "utk": "untuk", "untk": "untuk",
    "dgn": "dengan", "dgan": "dengan",
    "klu": "kalau", "kalo": "kalau", "kalu": "kalau",
    "mcm": "macam", "mcm2": "macam-macam", "cmne": "macam mana", "mcmne": "macam mana",
    "mcmana": "macam mana", "mcm mana": "macam mana",
    "bgtau": "beritahu", "bg": "bagi", "lg": "lagi", "skrg": "sekarang",
    "tq": "terima kasih", "ty": "terima kasih", "tqq": "terima kasih",
    "thx": "terima kasih", "thanks": "terima kasih", "thank you": "terima kasih",
    "t kasih": "terima kasih", "terima kasih byk": "terima kasih banyak",
    "tlg": "tolong", "pls": "tolong", "please": "tolong",
    "moga": "semoga", "smga": "semoga", "smoga": "semoga",
    "amin": "aamiin", "aminn": "aamiin", "aamin": "aamiin", "ameen": "aamiin",
    "aamiin ya rabbal alamin": "aamiin",
    "assalamualaikum": "salam", "assalamualikum": "salam", "asalamualaikum": "salam",
    "salamualaikum": "salam", "salam sejahtera": "salam", "aslm": "salam",
    "waalaikumussalam": "salam", "waalaikumsalam": "salam", "wsalam": "salam",
    "org": "orang",
    "sumbangan": "sumbang", "menyumbang": "sumbang",
    "donate": "sumbang", "donation": "sumbang", "infak": "infaq",
    "sedeqah": "sedekah", "zakatt": "zakat",
    "bantuan": "bantu", "menbantu": "bantu", "membantu": "bantu",
    "kesusahan": "susah", "susahhh": "susah",
    "penderitaan": "derita",
    "muallaf": "mualaf", "syahadah": "syahadah",
    "masuk islam": "masuk islam", "peluk islam": "masuk islam",
    "join": "sertai", "sertai lah": "sertai",
    "keahlian": "ahli", "member": "ahli",
    # `doakan` is the *request* form and `doa` is the noun. Folding them together
    # -- which an earlier version of this dictionary did -- erases the one signal
    # DOA_REQUEST depends on: `doakan saya` ("pray for me") and `doa saya` ("my
    # prayer") would normalize identically. The benefactive `-kan` is kept as its
    # own token so the two stay apart.
    #
    # Open, not settled: whether that separation is the right boundary is one of the
    # questions the DOA_REQUEST architecture ticket has to evaluate. The entry stays
    # as-is until that ticket decides; do not fold it here on the way past.
    "doakan": "doa kan", "doakanlah": "doa kan", "doadoakan": "doa kan",
    "doakn": "doa kan",
    "murah rezeki": "rezeki",
    "insya allah": "insyaallah",
}

# Bare religious formulae. A Comment made only of these asserts nothing about the
# organisation, asks for nothing, and is not a blessing *of* anyone.
CORE = set("""
alhamdulillah alhamdulilah alhamdulillaah alhamdulilleh alhamdullillah
allhamdulilah alhamdullah alhamdullihah alhamduliallah
masyaallah masya allah maasyaallah subhanallah subhanallaah
allahuakbar allah huakbar allahu akbar allahhuakbar allahuakhbar allahuakbarr
syukur syukron amin aamiin ammin aaminn ameen insyaallah bismillah
astaghfirullah tabarokallah tabarokaallah
""".split())


def normalize(text: str) -> str:
    t = text.lower()
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"(\w)\1{2,}", r"\1\1", t)  # collapse 3+ repeats
    for key, value in NORMALIZE.items():
        t = re.sub(rf"\b{re.escape(key)}\b", value, t)
    return re.sub(r"\s+", " ", t).strip()


def bare_interjection(text: str) -> bool:
    """True when *every* word is a formula word and there is at least one."""
    words = normalize(text).split()
    return bool(words) and all(word in CORE for word in words)


def is_empty(text: str) -> bool:
    """Emoji-only and sticker Comments normalize to nothing."""
    return normalize(text) == ""
