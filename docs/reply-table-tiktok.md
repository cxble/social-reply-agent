# Reply table: @benooicb on TikTok

Drafted 2026-10-21 from a harvested corpus of real Comments. **Every Variant below is a spelling
that actually appears in the corpus**; nothing is invented. `reply_id`s are stable. **All nine
`approved_reply` texts and every Phrasing row were approved by the Account holder on
2026-10-21** — nothing in this table is blocked on a fact or on permission.

## What the corpus is, and what it is not

Comments read from `@benooicb`'s posts with a logged-out **headed** browser, harvested
2026-10-21. The current corpus is **1,423 top-level Comments across 9 Posts**, taken from the
page's own `comment/list` response rather than scraped out of the DOM — which is what first made
the size of these sections visible.

Three Posts are pinned and carry 660K–989K views; the rest run from 251 to 21K. The comment
sections are overwhelmingly Malay, Islamic-framed, and short.

**`total` counts top-level Comments plus their replies, and nothing else.** Confirmed exactly on
six small Posts, where `top-level + replies == total`: 13+13=26, 3+3=6, 7+9=16, 4+4=8, 6+4=10,
30+30=62. `has_filtered_comments` was 0 and no deleted marker appeared on any Post, so the
remainder is neither filtered nor deleted. It is Comments the Platform never served.

**The reads are still short on the big Posts.** Reported `total` against what a driven read
actually recovered:

| Post | read | `total` | stopped at | note |
|---|---|---|---|---|
| 7625819611426016530 | 468 | 1,519 | cursor 460 | `has_more` still **1** — never terminated |
| 7630307398703435015 | 470 | 2,348 | cursor 460 | terminated, 1,292 unaccounted |
| 7667016655641382152 | 224 | 485 | cursor 240 | 12 unaccounted |
| 7646191853557140744 | 180 | 569 | cursor 200 | 213 unaccounted |
| **7638968441851907336** | **50** | **2,712** | **cursor 60** | `has_more: 0` — see below |

**`has_more: 0` is not proof that a read finished.** On `7638968441851907336` the stream ended at
cursor 60 with **50 of 2,712** Comments read, and reported `has_more: 0` exactly as a complete
read does — no captcha string, no challenge page, nothing in the log. That is the same failure
ADR 0006 handles for the Session, arriving through a door ADR 0006 does not watch: a truncated
read is indistinguishable from a finished one **unless the count is checked against `total`**. So
a read is complete when its count agrees with `total`, and not when `has_more` says 0.

**Deeper reads are a strict superset of shallow ones, and they change the mix.** Re-reading one
Post at depth recovered all 21 distinct texts the shallow read had found — none lost — plus 69
more. The extra Comments are not more of the same: the share made up of bare formulae rose from
**20% to 39%**. TikTok serves the substantive Comments first and the one-word ones after, so
**Variant lists built on page one are not merely short, they are biased toward the long
Comments.**

Two further limits:

- **The sample skews to recent and popular.** Old buried Comments, and anything below the fold on
  a busy Post, are absent. The Variant list will grow.
- **Every harvest so far has run without a Session** (`~/.config/social-bot/state/` holds no
  jar), and the truncations above are what that costs. The agent consumes a Session and never
  repairs one — ADR 0006 — but reading anonymously was never the design, and the truncated counts
  are the reason to stop treating it as equivalent.

## The shape that matters

**The great majority of Comments need no answer at all.** The dominant Comment is a doa, a
blessing, or a bare `Alhamdulillah`. A table sized for the majority would be a table of
acknowledgements; the useful work is in the minority, and the minority is where the risk is.

## Intents

| `intent` | what it is | in the corpus (n=1,423) | outcome |
|---|---|---|---|
| `DOA_BLESSING` | a prayer or blessing for a person or the work | **364 — 26%** | Canned reply |
| `GREETING` | a salutation carrying nothing else | **140 — 10%** | Canned reply |
| `PRAISE_ENCOURAGE` | praise or encouragement to keep going | 47 — 3% | Canned reply |
| `BENEFICIARY_THANKS` | thanks from someone the organisation has helped | 30 — 2% | Canned reply |
| `DOA_REQUEST` | **the commenter asking to be prayed for** | undercounted — see below | Canned reply |
| `HELP_REQUEST` | **a person asking the organisation for help** | 41 by keyword, **4 real** — see below | **Escalate. Never a Canned reply.** |
| `JOIN_ENQUIRY` | asking how to become a member or volunteer | 4 | **Escalate.** No answer to give. |
| `CONVERT_CONGRATS` | a blessing aimed at a new Muslim | 2 matched, on a Post carrying 180 Comments | Canned reply |
| `DONATION_ENQUIRY` | asking how to contribute | 1 | Canned reply — approved 2026-10-21 |
| `ZAKAT_SEDEKAH_ENQUIRY` | asking about zakat, sedekah or infaq by name | **0 real** | Canned reply — same text as donation |
| `OUT_OF_SCOPE` | **a reply was warranted and no entry fits** — condolence, complaint, testimony | **14 — 1.8%** by reading; the keyword pass's 516 were mostly `NO_REPLY` | no reply — **Escalated** (ADR 0018) |

The counts are a crude keyword pass, not the Router, and are given to show shape rather than to
be trusted per-Intent. Two of them are known to be wrong in instructive ways, below.

**Every count in this table is a keyword estimate and every one of them is now superseded.**
`docs/labelled-set-tiktok.md` labels 564 distinct Comments by hand and gives the real rates:
`OUT_OF_SCOPE` collapses to 1.8%, `DOA_BLESSING` to 17.7%, and 61.1% of rows turn out to need no
reply at all. Read the numbers below as the shape the keyword pass saw; read the labelled set for
what the corpus means.

**`OUT_OF_SCOPE` was the table's largest line, and the name was doing two jobs.** 516 Comments —
36% of the corpus — carry nothing to match on, which is a fact about the keyword pass and not about
the corpus:

**Those 516 are two classes, and the labelled set split them — settled in ADR 0018.** Most are
*correctly silent*: the design working, not a hole in coverage. `docs/labelled-set-tiktok.md` calls
that **`NO_REPLY`** and measures it at **61.1% of rows**. `OUT_OF_SCOPE` proper — **a reply was
warranted and no entry fits**: condolence, testimony, complaint — is **1.8%**. The rest of this
section is about the `NO_REPLY` class. Both go unanswered, and they are opposites in the only way
that matters: a `NO_REPLY` Comment receives nothing at all and is **never Escalated**, while a Tail
Comment is Escalated, because 61.1% of a corpus routed to a human is how the Escalation sink stops
being read (ADR 0014's own warning). The old name is why the 36% below should not be read as a gap.

- **231 (16%) are a bare religious formula and nothing else**: `alhamdulillah` alone 114 times,
  `alhamdulilah` 20, `aamiin` 28, `syukur alhamdulillah` 8, `alhamdulillah aamiin` 8,
  `alhamdulillah allahuakbar` 5, `allahuakbar` 5, `subhanallah` 3, `masyaallah` 3, plus
  `alhamdullillah`, `alhamdulillaah`, `alhmdulillah`, `masyallah`, `allahuakhbar`, `alhamdulilleh`,
  `ammin`, `aamin3`, and `aamiin aamiin aamiin aamiin aamiin aamiin aamiin`.
- **285 (20%) have no text at all** — sticker and emoji-only Comments, which normalize to nothing.

**A bare `alhamdulillah` belongs here and not in `DOA_BLESSING`, and this is worth stating because
the table previously left it ambiguous** — the shape section called bare `Alhamdulillah` the
dominant Comment while the Intent table gave it nowhere to go. `tt-doa-001`'s text is
*Aamiin. Semoga Allah permudahkan segala urusan tuan/puan.* Answering a bare `alhamdulillah` with
`Aamiin` is a non-sequitur: the Commenter is not praying for anyone, they are acknowledging God.
It is neither a blessing to agree with nor a request to grant. So it gets no reply.

**And it is where the volume is** — on the conversion Post bare formulae are **39%** of the
section, and a table that answered them would be posting 114 identical acknowledgements into one
comment section. Deciding that these need no reply is what keeps the rest of the table small.

`DOA_REQUEST` and `HELP_REQUEST` are the two the captions could not have predicted, and they
pull in opposite directions: one asks for prayer and is answered automatically, the other asks
for material help and must not be.

**Every entry that can be posted is written to be safe when it is wrong.** The replies below are
short, warm, and claim nothing beyond what the Account holder approved: no process, no address,
no religious ruling, no promise of action. A reply that says only `Aamiin` cannot misstate a
fact, and where a fact is needed the entry is either filled from the Account holder's own words
or left blocked. That rule is what makes the fallback ladder below cost so little.

## The entries

Field meanings are in `docs/reply-routing.md`.

**A Reply may state only facts the Account holder approved** — ADR 0015. That is why one of the
entries below is the Account holder's own words rather than drafted text, and why two are
empty. An `approved_reply` here is not a suggestion for a model to elaborate on; it is the
complete set of things the agent is permitted to assert about this organisation.

---

### `tt-doa-001` — `DOA_BLESSING`, Malay

- `approved_reply`: *Aamiin. Semoga Allah permudahkan segala urusan tuan/puan.* **approved by the Account holder 2026-10-21**
- `matching_criteria`: a prayer or blessing with no request in it
- `known_variants` — **364 Comments matched this Intent and 312 of them are distinct.** There is
  no small dictionary here. The forms that recur:
  - `aamiin` — **28**. The whole Comment, alone.
  - `semoga cepat sembuh` — **9**, plus `semoga cpt sembuh kami semua doa aamiin`,
    `semoga cepat sembuh insyaallah aamiin`, `semoga cepat sembuh aameen²`,
    `smg cepat sembuh ibu dan ayah nya smg allah sembuhkan segala penyakit nya dan sehat selalu`
  - `alhamdulillah aamiin` — 8
  - `semoga dipermudahkan` — 3 · `semoga di permudahkan segala urusan` — 3 · `semoga dipermudahkan segala urusan` — 3
  - `aamiin ya allah` — 2 · `semoga allah permudahkan urusan` — 2
  - `alhamdulillah utk saudara baru moga Allah memberi cahaya kepada hambanya aminnn3 yralamin`
  - `Alhandullillah. Semoga Allah melimpahi rahmat keatas Gary.`
  - `alhamdulllah semuga dipermudahkan segala urusan`
  - `Moga dipemudahkan urusan gary n bro ben`
  - `semoga Allah melimpahkan rahmat kepada anda dan gary`
  - `semuga dpermudahkan` · `dipermudahkan urusan` · `semuga allah mudahkan urusan hashimah` ·
    `semuga dmurahkan rezeki hasimah untuk menjaga ibu bapa` · `smuga diprmudahkn allah sgl urusan mreka` ·
    `ya allah dipermudahkan segala urusan dan diberi kesihatan yang baik` ·
    `semugo allahpermudah segala usannya` · `Semoga urusan pakcik ni dipermudahkan Allah Swt...`

**`semoga cepat sembuh` is a sub-class the canonical text is the wrong shape for.** It is a
blessing for a **third party who is ill** — an `ayah`, a `mak`, a parent — not for the person
writing it. *Aamiin. Semoga Allah permudahkan segala urusan tuan/puan* agrees with the prayer and
then addresses the Commenter, who is not the one who is sick. The `Aamiin` carries it; the second
sentence is aimed at the wrong person. Under ADR 0017 this is what an alternate Phrasing is for,
and it is the strongest case in the table for one of `tt-doa-001`'s alternates being phrased
neutrally enough to fit both.

The spellings are the point. `semoga` arrives as `semuga`, `smoga`, `smg`, `semugo`, `smuga`,
`moga`; `alhamdulillah` as `alhamdulilah`, `alhamdulillah`, `alhamdullillah`, `alhmdulillah`,
`alhamdullilah`, `alhamdulillaah`, `alhamdulilleh`, `allhamdulilah`, `alhamdullah`, `alhamduliallah`;
and `aamiin` as `amin`, `amiin`, `aamin`, `ammin`, `aaminn`, `ameen`, `aamin3`, `a.miin` — once as
`aamiin aamiin aamiin aamiin aamiin aamiin aamiin`. Normalization has to fold those without
touching the Comment as stored.

---

### `tt-doa-002` — `DOA_BLESSING`, English or mixed

- `language`: en
- `approved_reply`: *Aamiin. Thank you for your doa.* **approved by the Account holder 2026-10-21**
- `known_variants` — **almost none exist, and measuring that is the finding.** The corpus is
  **98.6% Malay**: of 1,423 Comments, **20 contain any English word at all.** Every one of those
  20 that is a blessing is an English *clause* inside a Malay Comment:
  - `Alhamdulillah, Bro Ben ,all the praise to our Almighty Alloh. keep it up till ur last breath. Aamieen.`
  - `terbaik bro Ben. Keep it up till it last breath. Amieen Ya Alloh.`
  - `Bro Ben. With your good and kind hearted, may Allah bless you bro Ben.`
  - `to be honestly you are the best. Tkasih ya Allah Aamiinn.`
  - `i appreciate what you are doing..ben. i.pray for yr good health..aamiin`
  - `Jazakallah Khairan Kathira semoga Allah permudahkan segala urusan dunia dan akhiratnya pada saudara 2saudari 2 semua amin ya Allah amin ya Rabbal Alam`
  - `good job. semuga dipermudahkan segala urusan Perubatan Dan kembali sihat`
  - `terima kasih sahabat dengan perhatian sahabat thanks for your kindness semoga di permudahkan segala urusan dan...`

**The corpus does not contain this Intent; it predicts it.** Not one English body in the corpus is
a Comment written in English. This entry is therefore in the same position as `tt-zakat-001` —
live on `matching_criteria`, with a Variant list resting on a handful of real cases rather than on
a population — and it is worth saying that plainly instead of presenting eight samples as a
distribution.

**This is why the language test cannot be a per-Comment classifier.** A detector that reads each
Comment and picks a language would see Malay, route to `tt-doa-001`, and answer `keep it up till
ur last breath` with *Aamiin. Semoga Allah permudahkan segala urusan tuan/puan.* What has to be
classified is **the language the blessing itself is in**, and that is a judgement the Router makes
with both entries in front of it. `docs/reply-routing.md` already forbids forcing one class on a
mixed Comment; this entry is what that rule exists for.

**Two of the twenty are not blessings and must not match:** `Walakomsalam from Myanmar 🇲🇲 Allah
bless you` is a greeting (`tt-greet-001`), and `you reply me` asks for a reply — a Comment about
the agent's absence, which no entry in this table answers.

---

### `tt-praise-001` — `PRAISE_ENCOURAGE`, Malay

- `approved_reply`: *Terima kasih. Semoga Allah membalas budi baik tuan/puan.* **approved by the Account holder 2026-10-21**
- `matching_criteria`: praise or encouragement with no request and no explicit doa
- `known_variants` — **47 Comments matched, 32 distinct**:
  - `terbaik` — **12**. The whole Comment, alone — and as `terbaikk`, `terbaik bro ben` (2),
    `abg terbaikk`, `tuann terbaik`, `terbaik adik`, `terbaik bro bo`, `terbaik sahabat rezeki tu`
  - `mantap` — 3
  - `alhamdulillah terbaik` — 2, plus `alhamduliillah terbaik bro ben`, `alhamdulillah bro ben terbaik`,
    `alhamdulillah terbaik saudara islam ku terus istiqamah`
  - `kerja yang mulia teruskan perjuangan anda`
  - `teruskan ben` · `hebat perjalanan hidup tuan` ·
    `good job semuga dipermudahkan segala urusan perubatan dan kembali sihat`
  - `subhanallah dpt ibadat dlm raudah yang terbaik`
  - `terbaik bro ben keep it up till it last breath amieen ya alloh`
  - `betul abang baik keren`
  - `الحمدالله!! تروسكن اسها مورني` *(Jawi)*

`terbaik` **alone** is the most frequent body in this Intent — 12 of 47 — and it is a complete
Comment. The constraint the text has to meet is not accuracy but that it does not read as sarcasm
the tenth time it appears in one section.

---

### `tt-greet-001` — `GREETING`, Malay

- `approved_reply`: *Waalaikumussalam warahmatullahi wabarakatuh.* **approved by the Account holder 2026-10-21**
- `matching_criteria`: a salutation carrying no other content
- `known_variants` — **140 Comments matched this Intent and 92 are distinct. It is 10% of the
  whole corpus, and the largest single body is one word:**
  - `salam` — **27**. The entire Comment.
  - `salam wbt` — 5 · `waalaikum salam` — 4 · `walaikumsalam` — 3 · `salam alhamdulillah` — 3 ·
    `waalaikumusalam` — 3 · `salam wbt alhamdulillah` — 3
  - `waalaikummussalam` — 2 · `salam selamat pagi` — 2 · `walaikumusalam` — 2 ·
    `waalaikumusalam alhamdulillah` — 2 · `walaikumusalam alhamdulillah` — 2 ·
    `waalaikummusalam` — 2 · `waalaikummussalam warahmatullahiwabarokatuh` — 2
  - `assalamualaikum sahabat lama` · `ASSALAMUALAIKUM` · `Assalammualakum` · `assalamulaikum` ·
    `asllm allkm` · `wslm` · `wassalam` · `salam wrbt` · `salam takziah` · `salam tuan` ·
    `a.mualaikum bro.terbaik` · `ben bagi salam terbaik` ·
    `asalamualaikom syukur saudara dapat menarik untuk saudara kita bukan islam syukur dapat`

`a.mualaikum` is a real spelling and no reasonable normalizer predicts it, which is the case for
matching on Jev's typed decision over a Normalized Comment rather than on a dictionary of known
forms.

**This is the entry where the Phrasing count matters most and it is currently the smallest — 2.**
`salam` alone arrives **27 times**, and the table's plan of two canonical forms means a section
where those 27 Replies alternate `Waalaikumussalam warahmatullahi wabarakatuh` /
`Waalaikumussalam` / `Waalaikumussalam warahmatullahi wabarakatuh` … A two-item deck is not a
rotation, it is an A/B test a reader can see. ADR 0017 says the count should be 3–4, and this
needs it more than the other entries do, not less.

It is also cheaper here than anywhere else, because the entry varies only between **existing
canonical formulas** and never between drafted sentences. The set those can be drawn from is
larger than the two currently listed — `Waalaikumussalam warahmatullahi wabarakatuh`,
`Waalaikumussalam warahmatullah`, `Waalaikumussalam`, and the long spelling
`Waalaikummussalam warahmatullahiwabarokatuh` are all real and all attested in the corpus as
*incoming* text. Widening the deck to four is a matter of listing forms that already exist, not of
writing anything.

---

### `tt-doareq-001` — `DOA_REQUEST`, Malay

- `approved_reply`: *Aamiin, semoga Allah makbulkan hajat tuan/puan.* **approved by the Account holder 2026-10-21**
- `matching_criteria`: **the commenter asking to be prayed for** — a request whose object is the
  commenter's own wish, not the organisation's help
- `known_variants` — the corpus is much thinner here than the captions suggested, and the forms
  it does contain are all one shape: `tolong doa` + a wish.
  - `Tolong DOAKAN saya jgk utk ke sana 😭😭😭`
  - `tolong doa saya jgk untuk ke sana`
  - `tolong doakn saya sahabat untuk saya dn suami dpt pergi buat umrah`
  - `salam shbt tolong doa saya dpt rezeki untuk mengerjakan umrah ye`
  - `doa kan saya semoga dapat menunaikan haji`
  - `w slm sya teringin nak pergi umrah tapi tak mampu doa kan tuk sya`
  - `Doakan sy dan keluarga juga dpat menunaikan haji dan Umrah satu hari nnti`
  - `Doakan saya , semoga Allah izinkan saya ziarah ke tanah suci juga.. Saya teringin sangat moga dijemput kesana.`
  - `Doakan juga saya dan suami menjadi tetamu Allah`
  - `Semoga saya juga berpeluang menjadi tetamu Allah`
  - `moga saya d jemput ke sana..🤲🤲`
  - `doakan sy Kaya raya utk Bantu org lain🙏🏻`
  - `Ninie Salim: ya Allah.. semoga saya pun dapat pergi juga nanti🤲🏻`

**`tolong doa` is the form that makes this Intent hard, and it is the common one.** Four of the
thirteen variants begin with `tolong` — *help* — and the object that follows is `doa`. So the word
that carries the escalation signal in `HELP_REQUEST` is present in a Comment that must be
answered with `Aamiin`. What discriminates is not `tolong` but **what the person is asking for**:
prayer costs nothing to give, material help is the organisation's to decide. A keyword list keyed
on `tolong` gets this backwards on the most frequent form.
- **Common, and Post-specific.** On the Umrah Post it is the dominant Intent. It is a request,
  so a naive "contains a request → escalate" rule would escalate this whole Post's section, and
  that would be wrong: this is routine, and the community answers it with `Aamiin`.
- **Why this one is answered and `HELP_REQUEST` is not.** Both are requests. This one asks for
  *prayer*, which costs the organisation nothing to give, cannot be given wrongly, and is what
  the surrounding section is already doing. `HELP_REQUEST` asks for *material help*, which only
  a human can decide to give. The reply here therefore promises nothing — `Aamiin, semoga Allah
  makbulkan hajat tuan/puan` agrees with the wish and commits the organisation to no action.
- **Empathy is in the verb, not the length.** `Tolong DOAKAN saya jgk utk ke sana 😭😭😭` is
  someone who wants something badly and is asking a stranger for it. A reply of one warm line
  is right; a longer one that thanks them for commenting is not, because it answers the
  comment rather than the person. `Aamiin` first is the whole trick — it grants the wish before
  anything else is said.
- **Answering this at all is also the mitigation for the ambiguity above.** When the Router
  cannot tell a `DOA_REQUEST` from a `HELP_REQUEST`, escalating is safe on both counts: a
  needless escalation costs a human a skim, and the alternative is an automated `Aamiin` posted
  under a plea for a wheelchair. The ladder below is built on exactly that asymmetry.

---

### `tt-thanks-001` — `BENEFICIARY_THANKS`, Malay

- `approved_reply`: *Alhamdulillah. Terima kasih kembali.* **approved by the Account holder 2026-10-21**
- `matching_criteria`: thanks from someone the organisation has already helped
- `known_variants` — **30 Comments matched, 25 distinct**:
  - `terima kasih orang baik` — **5**, plus `trima kaseh orang baik` and `terima kasih jadi orang baikkk`
  - `terima kasih bro ben` — 2, plus `terima kasih bro ben ooi orang baikk mudah2an semuga allah mpermudahkan urusan`
  - `alhamdulillah terima kasih bro ben` · `terima kasih ben alhandulillah`
  - `alhamdulillah terima kasih atas keperihatinan`
  - `terima kasih` — alone
  - `syukur alhamdulilah terima kasih datang melawat ayah saya Dan bantuan pampers semoga Allah permudahkan semua urusan`
  - `alhamdulillah terima kasih bro ben atas lawatan kak farina semoga rezeki dan diberkati allah`
  - `Alhamdulillah Terbaik En.Ben Oi tolong Keluarga dlm kesusahan`
  - `syukur Alhamdulilah,terima kasih Bro Ben Ooi`
  - `Alhamdulillah bro ben dan terima kasih kerana membantu insan insan yg memerlukan bantuan.`
  - `Intan kaseh: Tkaseh tuan srmoga abg sehat hendak nya`
  - `walaikkum salam sahabat yang sopptive terima kasih`
  - `macam saya dulu ayah tak boleh berjalan sekarang kenangan yang saya rindu terima kasih allah`
  - `tweu_313 terima kasih ben memudahkan orang dlm susah`

**Note the frequency shape, which is the opposite of `tt-doa-001`.** Here the recurring bodies are
generic (`terima kasih orang baik`, `terima kasih bro ben`) and the *specific* ones appear once
each. That matters for the text: `Alhamdulillah. Terima kasih kembali.` is right for the five
that say only thanks, and for the ones that name a visit or a pampers delivery it is still right —
what would be wrong is a reply that pretends to recognise the detail, or one that reads as though
the organisation is meeting these people for the first time.

**The first variant names a real beneficiary** (`ayah saya`, and pampers the organisation bought).
That person is in the corpus, identifiable, and the Reply must not treat them as a stranger —
which is another argument for the Threshold and the Tail, not for a keyword.

**This is the one entry where the reply must not be generic.** These people have already been
helped by the organisation, in person, and they are writing to say thank you. `Alhamdulillah.
Terima kasih kembali` is right: it returns the thanks and adds no new claim. What would be wrong
is a reply that reads like the reply to a stranger — it tells someone the organisation drove to
their father's house that they were not recognised. Where the Comment names a specific act
(`datang melawat ayah saya`, `bantuan pampers`), the reply still does not invent a detail about
it; warmth without specifics is safe, and false specifics are not.

**It also borders `HELP_REQUEST`, and the border runs the other way.** Some of these Comments
mention hardship — `tolong Keluarga dlm kesusahan` — while *thanking* for help already given. A
Router reading only for distress will read the past tense as a present plea here. The
discriminator is tense and direction: thanks for help received is answered; a request for help
not yet given escalates. When the two cannot be separated, the ladder below escalates.

---

### `tt-convert-001` — `CONVERT_CONGRATS`, Malay

- `approved_reply`: *Alhamdulillah. Semoga Allah kekalkan tuan/puan dalam hidayah-Nya.* **approved by the Account holder 2026-10-21**
- `known_variants` — **the keyword pass found only 2, and the population is a Post rather than a
  vocabulary**:
  - `ahlan wa sahlan ilal islam.`
  - `waalaikumussalam wbt terima kasih syukur Alhamdulillaah selamat masuk Islam senyum ceria ye semoga kekal sampai akhir hayat`
  - `walaikumsallam sodara semualaf alhamdulillah allah permudahkan`
  - `Alhamdulillah. bertuahnya. Kembali kpd fitrah`
  - `Alhamdulillah... Semoga En Gary terus istiqamah dgn Islam hingga ke jannah.. Aamiinn, semoga mereka yang kembali ke agama fitrah terus mndpt bimbingan yg sewajarnya.. Aamiinn`
  - `Alhamdulillah ugama yang fitrah 🥰🥰🥰🥰🥰🥰🥰`

- **Post-scoped.** Eligible only on a Post whose caption is a conversion post. Elsewhere
  `ahlan wa sahlan` is a greeting — and the scoping is doing most of the work here, because
  `alhamdulillah` **alone** is the commonest body in the entire corpus (114×) and asserts nothing
  about a conversion. A keyword that could route on `alhamdulillah` would send a third of the
  corpus to this entry.
- **`fitrah` means the conversion, not zakat.** Three of the Comments above are the same formula
  from the conversion Post, and all three used `fitrah` in the sense of *the natural religion*
  someone has returned to. They are also, word for word, the three false positives that made the
  zakat entry's keyword pass return zero true positives — see `tt-zakat-001`. The word belongs to
  this entry and must never be a signal for that one.

---

### `tt-join-001` — `JOIN_ENQUIRY`, Malay — **Escalate. Never a Canned reply.**

*Decided by the Account holder 2026-10-21.* Not a posted entry: the agent recognises it, posts
nothing, and hands it to a human. ADR 0016 carries the decision.

- `approved_reply`: **none, and none is wanted.** Deciding to escalate resolved the blocking
  fact rather than answering it — the agent no longer needs to know how someone joins, because
  it is not going to say.
- `known_variants` — 4 matched in the corpus, and they are one formula with `join` and `sertai`
  swapped in and out:
  - `Sy nk join pertubuhan ni boleh tak 😁`
  - `Saya nak join bleh x` · `saya nak sertai bleh tak`
  - `saya nak sertai pertubuhan ni boleh tak`
  - `assalammualaikum boleh ke sekiranya saya nak sertai pertubuhan kebajikan modal insan pada siapa...`
  - `Mr khai: kepala batas pulau pinang` — a follow-up giving his location, in the same thread
- `matched_but_not_this_intent`:
  - `macam mana nak mohon. sy oku fizikal and now tgah hadapi risiko buta kekal. from klang`
  - `MCM mna nak moham saya OKU pesakit stroke`

The last two contain `nak mohon`/`nak moham`, the same words as the enquiry, and are help
requests. They are listed here only to record that they must **not** match.

**Escalating this Intent defuses the boundary problem below.** The two Intents were hard to
separate and both now route to a human, so a Comment that lands on the wrong one of the pair
still reaches the right place. The analysis is kept because it is **not** idle: the same words
appear in `DOA_REQUEST`, which *is* answered, and telling a request for prayer from an enquiry
about joining is still a decision the Router has to get right. What changed is the cost of
getting it wrong — an error between these two is now invisible instead of public.

#### Why this one is worth a human

The organisation is a registered body with members, and answering "how do I join" correctly
means describing a process — who to contact, what is needed, whether there is a fee, whether
membership is even open. None of that is a fact the agent holds, and a canned `DM kami` is a
non-answer that teaches the person the organisation does not reply. Membership is also the point
at which a stranger becomes part of the organisation, which is a decision for the organisation.

#### The boundary between this Intent and `HELP_REQUEST`

`nak mohon` is the trap. *Mohon* is "apply", and the same word asks to apply to **join** the
organisation and to apply **for assistance** from it. `Sy nk join pertubuhan ni boleh tak` is a
membership enquiry. `macam mana nak mohon. sy oku fizikal and now tgah hadapi risiko buta kekal`
is a blind man asking to be helped. The overlapping vocabulary is not a coincidence and not a
formatting problem — it is what both requests are actually called.

**The discriminating question is not what words appear; it is whether the person is asking to
give or to receive.**

- **`JOIN_ENQUIRY` — wants to give.** They are offering their own effort to the organisation's
  work. Their own circumstances are not the subject of the Comment.
- **`HELP_REQUEST` — wants to receive.** They describe their own difficulty, or a named third
  party's, and ask the organisation to act on it.
- **`DOA_REQUEST` — wants neither; asks for prayer.** This is the one the test has to keep out
  of both, because it is the one that gets answered.

The signals that settle it, in the corpus:

| Signal | Pulls toward |
|---|---|
| `nak join`, `nak sertai`, `nk jadi ahli`, with nothing about themselves | `JOIN_ENQUIRY` — escalate |
| a first-person difficulty: `saya OKU`, `saya sakit`, `tak boleh`, `susah`, `tak ada yg membantu` | `HELP_REQUEST` — escalate |
| a named third party in difficulty: `Bantulah Farina`, `tolong keluarga saya` | `HELP_REQUEST` — escalate |
| an ask for the organisation to act: `tolong ziarah`, `bantulah` | `HELP_REQUEST` — escalate |
| `doakan`, `moga`, a wish with no difficulty and no offer of effort | `DOA_REQUEST` — **reply** |
| a location offered as context for joining (`kepala batas pulau pinang`) | `JOIN_ENQUIRY` |
| a location offered as context for needing help (`from klang`, `tanjung tokong`) | `HELP_REQUEST` |

The last two rows are the same fact — where the person lives — carrying opposite meaning
depending on which question it answers. That is the clearest evidence that this boundary cannot
be a keyword list, and it is why it is a Router decision over typed options with a confidence,
not a term-match.

**`nak mohon` alone is not enough to choose.** A Comment containing it and nothing else is
ambiguous. Ambiguity here resolves to Escalation — which, since both Intents now escalate, is
also the answer a correct match would have produced.

---

### `tt-donate-001` — `DONATION_ENQUIRY`, Malay

- `language`: ms
- `approved_reply` — **supplied by the Account holder 2026-10-21 and approved**:

  > Alhamdulillah. Terima kasih kerana support.
  >
  > Maybank
  > 5570 9082 5174
  > Pertubuhan Kebajikan dan Pembangunan Insan Pulau Pinang

- `matching_criteria`: a Comment asking how to contribute, give, or send money
- `known_variants` — **1 clean instance in the corpus, plus one the keyword pass misrouted**:
  - `bagaimana kalau kita nak sumbang`
  - `bagaimana kalo kita nak menyumbang`
  - `Assalammualakum Tuan nk tanya mcm mna klu kita nk buat Sumbangan ikhlas`
  - `tolong bagi account no persatuan walaupun sikit saya nak bantu insyaa allah` — the crude
    matcher sent this to `HELP_REQUEST`, on the word `tolong`
- **The misroute is the instructive one.** This Comment is a person asking for the account number,
  and it carries the same `tolong` that four `DOA_REQUEST` Comments carry and that the real help
  requests carry. The word is not the signal; what follows it is — an account number is asked for,
  not assistance.
- `minimum_match_threshold`: **0.90** — the consequential tier (ADR 0019). The highest in the
  table, because this is the entry that publishes a bank, an account number and a payee
- **The account holder name in the reply matches the organisation in the bio**, which is the
  consistency check that this is the organisation's own account and not a third party's.
- **The reply text is fixed.** The account number, the bank, and the payee are approved facts,
  and the agent may not paraphrase, reformat, or reconstruct them from a model's memory. A
  transposed digit here sends a donor's money to a stranger.

**A note on posting an account number in public.** Replies are public, and a public donation
reply is where impersonation happens: a third party can post a *different* account number under
the same Post and rely on the commenter not checking. The organisation's own reply is
trustworthy; the comment section around it now is not. That is a reason to pin the reply, or to
keep the account number in a pinned Comment the reply points at, and it is worth deciding
deliberately rather than by default.

---

### `tt-zakat-001` — `ZAKAT_SEDEKAH_ENQUIRY`, Malay

*Decided by the Account holder 2026-10-21:* a zakat or sedekah enquiry gets the **same reply as
a donation enquiry**, because the money goes to the same account.

- `language`: ms
- `approved_reply` — the Account holder's own text, identical to `tt-donate-001`:

  > Alhamdulillah. Terima kasih kerana support.
  >
  > Maybank
  > 5570 9082 5174
  > Pertubuhan Kebajikan dan Pembangunan Insan Pulau Pinang

- `matching_criteria`: a Comment that names zakat, sedekah or infaq and asks how to pay it
- `known_variants`: **none in the corpus — and the corpus is now the evidence, not a gap.** The
  crude keyword pass matched four Comments against this Intent and **all four are false
  positives**, which is a stronger claim than "none seen yet":
  - `Alhamdulillah... Semoga En Gary terus istiqamah dgn Islam hingga ke jannah.. Aamiinn, semoga mereka yang kembali ke agama fitrah terus mndpt bimbingan yg sewajarnya.. Aamiinn`
  - `Alhamdulillah. bertuahnya. Kembali kpd fitrah`
  - `Alhamdulillah ugama yang fitrah 🥰🥰🥰🥰🥰🥰🥰`
  - `@Ben Ooi assalamualaikum.. Abg yang terlantar ni dah meninggal kan kita semua. Sedekah kan Al-Fatihah buat Salim Bin Othman. Semoga Allah menempatkan nya bersama hambaNya yg beriman.. aamiin`
- **All four false positives come from two words, and neither means money here.** The first three
  are the *same conversion formula* from the conversion Post: `fitrah` as **the natural religion**
  someone has returned to — which is `tt-convert-001`'s subject, not a zakat fund. The fourth is a
  takziah asking that **al-Fatihah be recited** for the deceased: `sedekah` as *hadiah pahala*, a
  religious gift, with no money in it.
- **So `fitrah` and `sedekah` must not be keywords.** In this corpus `fitrah` is a conversion word
  every single time and `sedekah` appears once, in a funeral formula. A term-match on either sends
  a conversion blessing or a condolence to an entry that carries a bank account number. What the
  entry can safely match on is `zakat`, `infaq`/`infak`, and a form of `sumbang` — the words that
  name money in Malay and have no second religious sense here.
- This Intent is predicted from the Account's subject matter, not observed, and its Variant list
  stays empty until real Comments supply spellings. The entry is otherwise live, so the first real
  Comment matches against `matching_criteria` alone.
- **The shared reply is a deliberate decision, not an oversight.** It is recorded here so that
  nobody later "fixes" the duplication by writing a zakat-specific reply.
- **One thing to confirm with the Account holder.** A zakat payer may read an account given in
  answer to a zakat question as a *zakat fund* — and whether a payment is valid zakat depends on
  who may receive it, which is a religious question and not a banking one. If the account is not
  a zakat fund, the payer is the one who carries that. The reply as supplied does not claim to
  be one, so this is not a defect; it is the one point where the answer given in answer to
  *sedekah* and to *zakat* may need to differ, and the Account holder is the only one who can
  say. Until they say otherwise, both get the same text.

---

## Variation

Per ADR 0017, a Canned reply holds several approved Phrasings and rotation picks one, so the
same text does not repeat. This is what each entry needs.

| `reply_id` | Phrasings | matched | most on one Post | note |
|---|---|---|---|---|
| `tt-doa-001` | 3–4 | 364 | **169** | the highest-volume Intent in the corpus, so repetition here is the most visible |
| `tt-doa-002` | 3–4 | ~8 clauses | — | thin; see the entry |
| `tt-praise-001` | 3–4 | 47 | 16 | |
| `tt-greet-001` | 2 (approved) | 140 | **78** | see below — the only entry where "vary" means something different |
| `tt-doareq-001` | 3–4 | 2 clean (+7 misrouted) | 2 | see § Escalation — the weak `tolong` pass fires before this Intent and steals them |
| `tt-thanks-001` | 3–4 | 30 | 13 | |
| `tt-convert-001` | 3–4 | 2 + ~180 on the Post | Post-scoped | |
| `tt-donate-001` | 2+ **shared set** | 1 clean | 1 | this and the zakat entry share one set |
| `tt-zakat-001` | 2+ **shared set** | 0 | 0 | this and the donation entry share one set |
| `tt-join-001` | — | 4 | 2 | Escalates. There is no text to vary. |
| `HELP_REQUEST` | — | 4 real of 41 | 1 | Escalates. There is no text to vary. |

One alternate is not worth having: two Phrasings produce a visible A/B alternation, which a
reader notices faster than they notice repetition at low volume.

**The column that matters is "most on one Post", not the corpus total.** A reader sees one
comment section, not nine, and the Comments that draw a given reply are not spread evenly — they
pile onto whichever Post the Intent is about. So the number to design against is the peak:

| Intent | on its heaviest Post | a 4-Phrasing deck means |
|---|---|---|
| `DOA_BLESSING` | **169** | each Phrasing posts **~42 times** |
| `GREETING` | **78** | each Phrasing posts **~39 times** on a 2-deck, ~20 on a 4 |
| `PRAISE_ENCOURAGE` | 16 | each posts 4 times |
| `BENEFICIARY_THANKS` | 13 | each posts 3 times |

**Variation reduces visible repetition; at these volumes it cannot remove it.** 169 blessing
Comments on one Post answered from four Phrasings is 42 identical Replies in a section anyone
can scroll, and no feasible deck size fixes that — 10 Phrasings would still mean 17 each, and each
Phrasing costs a sign-off. What actually limits what a reader sees is that the Replies are
top-level and interleaved among hundreds of Comments rather than stacked together, and that most
readers never open all of them. That is worth stating plainly, because ADR 0017 reads as though
rotation solves repetition, and here it only breaks the *adjacent* run — which is still worth
doing, since two identical Replies side by side is the shape that reads as a bot.

**So the ordering to fix by peak, not by total, is `tt-doa-001` first** — 169 on its heaviest Post
is more than twice any other entry's, and it is the one deck whose size the corpus most clearly
argues for. `tt-greet-001` is the closest second (78 on its heaviest, from a deck of two), and
widening it is open rather than settled.

**`tt-greet-001` is the entry where "vary" means something else.** The reply is the salam, which
is a fixed formula rather than a sentence anyone drafts. It cannot be paraphrased — there is no
looser way to say it — but it has a small set of canonical forms of different lengths
(`Waalaikumussalam warahmatullahi wabarakatuh`, `Waalaikumussalam`, and their common spellings).
So this entry varies between formulas that already exist, and never between newly written
sentences. It is the one entry where a Phrasing invented by drafting would be a mistake.

**`tt-donate-001` and `tt-zakat-001` share one Phrasing set — resolved 2026-10-21.** The Account
holder's position is that donating and zakat are one thing here: one account, one reply. As
separate entries they would each carry their own rotation, so a Post holding one donation
question and one zakat question would get the identical reply twice. Pointing both at a **single
shared set** removes that — one deck, so the second Reply draws a different Phrasing.

**The shared set needs at least two Phrasings to do any work.** A shared deck of one still posts
the same words twice, so the resolution is structural only once an alternate exists. That
alternate is the courtesy line, never the bank block.

**Every Phrasing needs its own sign-off**, because a Phrasing is approved text under ADR 0015 —
the count in the table above is the size of that sign-off, not the number of entries. All of them
were approved by the Account holder 2026-10-21.

## Escalation: `HELP_REQUEST` and `JOIN_ENQUIRY`

Neither is a posted entry. The agent recognises them, posts nothing, and hands them to a human.
ADR 0014 carries the `HELP_REQUEST` decision and ADR 0016 the `JOIN_ENQUIRY` one, and the two
reasons are different: one is about harm, the other about the organisation being the right
answerer.

Real `HELP_REQUEST` Comments, all from welfare-ziarah Posts:

- `saya OKU juga tak ada yg membantu.hospitel tk leh wat apa² saya penyakit saraf susah pergi mana² tak boleh pendengaran.adk beradik tnk ambil tahu masalah saya` — a disabled person with a nerve condition, deaf, whose siblings will not help
- `macam mana nak mohon. sy oku fizikal and now tgah hadapi risiko buta kekal. from klang`
- `MCM mna nak moham saya OKU pesakit stroke`
- `Sy oku fizikal sakit Parkinson deses dgn minor stroke sebelah kanan`
- `Bantulah Farina saudara Ben . Dia tak boleh uruskan dirinya.` — a third party asking help for someone else
- `salam tuan, saya ank pulau pinang, tanjung tokong, mohon klu boleh tolong ziarah tanah2 perkuburan islam seminar penang`
- `tisu basah 3 ..4 helai ..derita pn dlm keadaan Gini x mampu di tanggung oleh kaum lelaki sekalipun..sumbangan dan pendapatan skim habis kepada rawatan` — treatment costs a man cannot carry

**This is not a rare edge case; it is a substantial share of the corpus on those Posts.** The
design predicted it from the captions, and the harvest confirms it in volume. Every one of the
first four contains the same words as the routine `JOIN_ENQUIRY`, and two of them are
indistinguishable from it by keyword. A table that answers the enquiry answers the plea.

**The agent's silence is not the deliverable — the human's answer is.** An escalated Comment
nobody reads is the same as no system at all, so the Escalation sink has to be something the
Account holder actually watches.

#### What a keyword pass does to this Intent, measured

The crude matcher the analysis ran found **41 Comments** for `HELP_REQUEST` — all 41 distinct — and
**4 of them are real**. The breakdown is the whole argument for a Router in one table:

| what they are | n | examples |
|---|---|---|
| **a real help request** | **4** | `saya OKU juga tak ada yg membantu…tak boleh pendengaran` · `Bantulah Farina saudara Ben` · `mohon klu boleh tolong ziarah tanah2 perkuburan islam` · `sumbangan dan pendapatan skim habis kepada rawatan` |
| `DOA_REQUEST` — an Intent the table **answers** | 7 | `Tolong DOAKAN saya jgk utk ke sana` · `tlg doakn sy` · `tolong doakn sy sahabat untuk sy dn suami dpt pergi buat umrah` |
| `DONATION_ENQUIRY` | 1 | `tolong bagi account no persatuan, walaupun sikit saya nk membantu` |
| **"how do I help him?"** — no Intent covers this | 2 | `camna cara leh bantu dia` · `BRO Ben mcm mana nak Bantu beliau.` |
| an offer, or an exhortation to others | 2 | `Hadir membantu` · `mari lah samawi kita membantu setakat mampu kita utk sesama insan` |
| blessings, thanks, praise, reminders | 25 | `allah murahkan rezeki hamba yg membantu` · `semoga ramai yang membantu` · `ok tuan tq bantuanya` · `TLG banyakkan selawat` |

**The 4 real ones are matched by accident.** Each carries a plea *and* the word `bantu`/`membantu`
inside the pleading clause; the 25 in the last row carry the same word and are blessings. Nothing
in the keyword distinguishes `tak ada yg membantu` from `semoga ramai yang membantu` except who is
suffering and who is being praised — a reading of the sentence, not a term in it.

**`tolong doa` is the misroute that will happen most.** Seven of the 41 are `DOA_REQUEST`, and five
of those open with `tolong`/`tlg`. Those are Comments the table **answers**, so a keyword pass
sends an answered Intent into the escalation queue — the agent falls silent on precisely the
Comments its Malay prayers were written for.

**The errors are not symmetric, and only one direction can hurt someone.** A `DOA_REQUEST` landing
on `HELP_REQUEST` costs nothing: both end in a human's hands, and the person waiting does not care
which queue they are in. The reverse does. A plea carrying `bantu` that lands on `DONATION_ENQUIRY`
gets answered — automatically, publicly, with no human in the loop — by posting the organisation's
**bank account number** to someone who asked for welfare help. That is the one error in this table
the agent can make to a stranger unrecoverably, and it is why the boundary is drawn as **give or
receive** rather than as a word list.

**One class here has no Intent at all, and that is now the decision.** `camna cara leh bantu dia`
and `BRO Ben mcm mana nak Bantu beliau` are readers asking how *they* can help a case in the Post —
a would-be donor or volunteer, which is the opposite of a plea. **Decided 2026-10-21: the class is
left to the Tail and Escalates as a gap to close**, rather than being given an Intent of its own.
It is the audience the organisation most wants, and answering it is the organisation's own words —
a canned acknowledgement would spend the approach on a formality — so it goes to a person by
design. What the decision forbids is the current *accidental* behaviour: the class must not be
swept into `HELP_REQUEST`'s Variants. A contributor and a person in difficulty are opposites, and
routing both the same way is how the first one is lost. An entry may be written for it later; that
is ordinary maintenance, not a re-opening of this.

---

## Safe fallbacks for ambiguous Comments

`docs/reply-routing.md` sets the four-way fallback. What the corpus adds is where the boundaries
actually fall, because the ambiguous cases here are not evenly distributed — they cluster on
exactly the Comments where a wrong reply does public harm.

**Two thresholds, not one.** The `minimum_match_threshold` on an entry decides whether a Canned
reply may be posted. A second, deliberately much lower **help threshold** decides whether a
human is needed. They are different questions and collapsing them into one number is the mistake
this section exists to prevent.

**The entry thresholds are now set and tiered by what a wrong Reply costs — ADR 0019.** The rule,
and the defaults it produces, are: **0.90** for the two entries that publish a bank account
(`DONATION_ENQUIRY`, `ZAKAT_SEDEKAH_ENQUIRY`), **0.80** for the acknowledgement classes, **0.20**
for the help threshold, and a **0.50 floor** no entry may sit below. The heights are justified by
the measured size of each class rather than by caution: the money-moving Intents are **0.3% of
rows**, so demanding near-certainty there costs almost no coverage, while the acknowledgement tier
is **34.9%** and is the bulk of the work worth doing.

The asymmetry is the whole argument, and it is the same one ADR 0014 makes:

- A **false positive** — escalating a Comment that was really routine — costs a human one skim.
- A **false negative** — posting `Sy nk join pertubuhan ni boleh tak`'s canned link under
  `macam mana nak mohon. sy oku fizikal and now tgah hadapi risiko buta kekal` — is a public
  failure by an organisation whose stated purpose is helping that person.

So the help threshold is set to catch, not to be precise. **Any evidence of a person in
difficulty plus any kind of ask routes to a human, at any confidence.**

| Situation | Outcome |
|---|---|
| **The Comment presents nothing addressed to the organisation** — a bare formula, an emoji, a mention, a support tag, chatter between commenters | **No reply** — nothing posted and nothing Escalated (ADR 0018) |
| One Intent matches above threshold; no difficulty signal | Canned reply |
| **Any difficulty signal** (own or a named third party's) **plus an ask**, even at low confidence | **Escalate** |
| Two mutually exclusive Intents both match above threshold | **Escalate** — never pick the higher |
| `nak mohon` with nothing else to disambiguate it | **Escalate** |
| Tense/direction unclear: thanks for help, or a plea for help | **Escalate** |
| Language or script not confidently read | **Escalate** |
| No Intent matches; no difficulty signal | **Tail Comment** — a reply was warranted and none fits, so **Escalate**; nothing at all if the Comment presented nothing |
| Tail would need a fact the Account holder has not approved | **Escalate** |
| The Post is a welfare-ziarah Post and the Comment is not confidently routine | **Escalate** |
| The Comment's identifier cannot be read immediately before writing | **Escalate** — never matched on its text (ADR 0019) |

**Escalate is a real outcome with a real cost, so it must not be a dumping ground.** Every row
above routes to a human, and ADR 0014 already records that the Escalation sink has to be
watched. A ladder that escalates a third of the section is not safe, it is abandoned — the
human stops reading it, and the system has effectively answered nothing while looking busy. The
target is few escalations, each one worth reading.

**Never resolve ambiguity by guessing and never by silence.** Guessing posts a wrong fact or a
wrong tone under the organisation's name. Silence drops a person who asked for help. Both are
worse than the human reading one extra Comment, which is the entire reason Escalation exists as
a distinct outcome rather than as an error path.

**The ambiguity is not a defect in the table.** `DOA_REQUEST`, `HELP_REQUEST`,
`BENEFICIARY_THANKS` and `JOIN_ENQUIRY` overlap because the people writing them are describing
the same few things — a wish, a hardship, a thank-you, an offer to help — in the same few words,
in a comment box with no form and no fields. The table cannot remove that overlap; it can only
refuse to resolve it silently.

---

## What is not here

- **Chinese and Tamil.** `docs/reply-routing.md` says both are earned by mining rather than
  assumed. The corpus contains none.
- **Jawi as a language.** Jawi Comments appear (`الحمدالله!!`), and they are Malay in Arabic
  script, not a separate language. They are Variants, not their own `language`. Normalization
  has to transliterate to match them at all — an open question the corpus raised, not answered.
- **Reply-to-a-Reply.** Everything above answers a top-level Comment. Deferred.
- **The Account's own Comments.** The harvest picked up `Bro Ben Ooi · Creator` rows on two
  Posts — the organisation's own replies, listed as items. The Adapter must exclude Comments
  authored by the Account, or the agent will consider replying to itself.
- **One Commenter posting a near-identical blessing on many Posts** (`Mariam binti yassin`
  appears on four). The Replied set is per-Comment, so this is answered per-Comment and is not
  spam to filter — but it is worth knowing the 1,423 Comments are not 1,423 independent voices:
  an `alhamdulillah` at 114× and a `salam` at 27× are a handful of people writing the same thing
  once each, and the effective vocabulary of this audience is far smaller than the row count
  suggests.

## Sign-off: the nine `approved_reply` texts

Everything the agent can post. Read this list and nothing else; each line is the complete text.
Approve, edit, or strike.

| `reply_id` | Intent | text as it would be posted | status |
|---|---|---|---|
| `tt-doa-001` | `DOA_BLESSING` (ms) | *Aamiin. Semoga Allah permudahkan segala urusan tuan/puan.* | **approved by the Account holder 2026-10-21** |
| `tt-doa-002` | `DOA_BLESSING` (en) | *Aamiin. Thank you for your doa.* | **approved by the Account holder 2026-10-21** |
| `tt-praise-001` | `PRAISE_ENCOURAGE` | *Terima kasih. Semoga Allah membalas budi baik tuan/puan.* | **approved by the Account holder 2026-10-21** |
| `tt-greet-001` | `GREETING` | *Waalaikumussalam warahmatullahi wabarakatuh.* | **approved by the Account holder 2026-10-21** |
| `tt-doareq-001` | `DOA_REQUEST` | *Aamiin, semoga Allah makbulkan hajat tuan/puan.* | **approved by the Account holder 2026-10-21** |
| `tt-thanks-001` | `BENEFICIARY_THANKS` | *Alhamdulillah. Terima kasih kembali.* | **approved by the Account holder 2026-10-21** |
| `tt-convert-001` | `CONVERT_CONGRATS` | *Alhamdulillah. Semoga Allah kekalkan tuan/puan dalam hidayah-Nya.* | **approved by the Account holder 2026-10-21** |
| `tt-donate-001` | `DONATION_ENQUIRY` | *Alhamdulillah. Terima kasih kerana support.*<br><br>*Maybank*<br>*5570 9082 5174*<br>*Pertubuhan Kebajikan dan Pembangunan Insan Pulau Pinang* | **approved by the Account holder 2026-10-21** |
| `tt-zakat-001` | `ZAKAT_SEDEKAH_ENQUIRY` | same text as `tt-donate-001` | **approved by the Account holder 2026-10-21** |

**All nine are approved.** The seven drafted rows were approved by the Account holder on
2026-10-21, on the same day as the two Account-holder rows above them, which are recorded
verbatim. Every row in this table is cleared to post.

Not in this table, because there is no text: `HELP_REQUEST` and `JOIN_ENQUIRY` both Escalate.

Approving a row above approves that entry's **canonical text** — the first of its Phrasings.
Under ADR 0017 each entry also needs alternates so the same words do not repeat; those are the
sets in the section below, and they were approved in the same sign-off. The canonical text still
matters most, because it is what an entry posts when nothing else is available.

**One caveat the Account holder should know about, since it cannot be signed away by approval.**
The Malay in the drafted rows is mine, and I am not the authority on it — the difference between
`makbulkan`, `perkenankan` and `dimakbulkan` is idiomatic rather than mechanical, and the same is
true of the register in every set below. Approval settles *permission*; it does not make the
phrasing native. A Malay speaker's read is still worth having before this runs at volume, and
editing a row afterwards is ordinary maintenance rather than a re-opening of the decision.

## Phrasings

**Every row below was approved by the Account holder 2026-10-21**, in the same sign-off as the
canonical texts. Under ADR 0017 each entry needs alternates so the same words do not repeat.
These sets cover the seven entries whose canonical text is drafted; the two Account-holder
entries are addressed at the end of this section.

**These are deliberately close to each other, and that is the point.** A person answering the
same kind of Comment twenty times says nearly the same thing with small differences, and that
near-repeat is what a person looks like. Text varying *widely* from one Reply to the next reads
as a phrasebook being sampled — a machine signal in its own right, and a louder one than the
repetition it was meant to avoid. The target is the smallest difference that avoids an exact
repeat, not the largest.

Row 1 of each set is the canonical text already in the sign-off table above.

### `tt-doa-001` — `DOA_BLESSING`, Malay

| # | text as it would be posted |
|---|---|
| 1 | *Aamiin. Semoga Allah permudahkan segala urusan tuan/puan.* |
| 2 | *Aamiin. Terima kasih atas doanya, semoga Allah permudahkan urusan tuan/puan.* |
| 3 | *Aamiin ya Allah. Moga segala urusan tuan/puan dipermudahkan.* |
| 4 | *Aamiin. Semoga Allah permudahkan segala urusan tuan/puan, dunia dan akhirat.* |

### `tt-doa-002` — `DOA_BLESSING`, English or mixed

| # | text as it would be posted |
|---|---|
| 1 | *Aamiin. Thank you for your doa.* |
| 2 | *Aamiin. Thank you for the doa, we really appreciate it.* |
| 3 | *Aamiin. Jazakallahu khairan for your doa.* |
| 4 | *Aamiin. Thank you, and may Allah make things easy for you too.* |

### `tt-praise-001` — `PRAISE_ENCOURAGE`

| # | text as it would be posted |
|---|---|
| 1 | *Terima kasih. Semoga Allah membalas budi baik tuan/puan.* |
| 2 | *Terima kasih banyak. Semoga Allah membalas kebaikan tuan/puan.* |
| 3 | *Terima kasih atas sokongan. Moga Allah balas jasa baik tuan/puan.* |
| 4 | *Terima kasih. Semoga Allah membalas budi baik tuan/puan dengan yang lebih baik.* |

### `tt-greet-001` — `GREETING`, Malay — **existing formulas only**

Two, and no more, because the salam is a fixed formula rather than a sentence anyone drafts.
Both rows are formulas that already exist; neither is newly written, and no row here may be.

| # | text as it would be posted |
|---|---|
| 1 | *Waalaikumussalam warahmatullahi wabarakatuh.* |
| 2 | *Waalaikumussalam.* |

*Row 2 was kept: the shorter form is in the approved deck. If it later reads as curt on this
Account, striking it ships a deck of one, which is a legitimate outcome rather than a gap.*

*The deck stays at two, and § Variation holds the arithmetic that argues for widening it* —
`salam` alone arrives **78 times on its heaviest Post**, so two forms alternate visibly. The
fixed-formula reasoning above was preferred to widening; that remains an open item rather than
something the sign-off settled.

### `tt-doareq-001` — `DOA_REQUEST`

| # | text as it would be posted |
|---|---|
| 1 | *Aamiin, semoga Allah makbulkan hajat tuan/puan.* |
| 2 | *Aamiin. Moga Allah makbulkan hajat tuan/puan.* |
| 3 | *Aamiin ya Allah, semoga hajat tuan/puan dimakbulkan.* |
| 4 | *Aamiin, semoga Allah perkenankan hajat tuan/puan.* |

*Every row promises no action beyond the doa itself* — the rule `docs/reply-routing.md` sets for
this Intent. A row that offered to do something would not be a Phrasing of this entry.

### `tt-thanks-001` — `BENEFICIARY_THANKS`

| # | text as it would be posted |
|---|---|
| 1 | *Alhamdulillah. Terima kasih kembali.* |
| 2 | *Alhamdulillah. Sama-sama, terima kasih kembali.* |
| 3 | *Alhamdulillah, terima kasih. Moga Allah permudahkan urusan tuan/puan.* |
| 4 | *Alhamdulillah. Terima kasih kembali, semoga Allah memberkati tuan/puan.* |

### `tt-convert-001` — `CONVERT_CONGRATS`

| # | text as it would be posted |
|---|---|
| 1 | *Alhamdulillah. Semoga Allah kekalkan tuan/puan dalam hidayah-Nya.* |
| 2 | *Alhamdulillah, tahniah. Moga Allah kekalkan tuan/puan dalam hidayah-Nya.* |
| 3 | *Alhamdulillah. Semoga Allah tetapkan tuan/puan dalam hidayah-Nya.* |
| 4 | *Alhamdulillah, syukur. Moga Allah kekalkan tuan/puan dalam hidayah-Nya.* |

*Row 2 is the one to watch.* Congratulating someone on embracing Islam is ordinary usage here, but
it is a stronger thing to say than a blessing, so it is the row that would be struck first if any
of these turn out to read wrong at volume.

**A limit on who can judge these.** The Malay here is mine, not a native authority's — see the
caveat in § Sign-off. Approval settles permission; a Malay speaker's read is still worth having,
and it is tracked in § Still to do rather than assumed away by the sign-off.

### `tt-donate-001` and `tt-zakat-001` — one shared set

**Resolved 2026-10-21: donating and zakat are the same thing here**, so these two entries point
at one shared Phrasing set and share one rotation.

The bank, account number and payee are the Account holder's verbatim words, identical in every
row, and never reworded, reformatted or reconstructed. Only the courtesy line above the block
varies, and rows 2 and 3 were approved in the same sign-off as the rest.

| # | text as it would be posted |
|---|---|
| 1 | *Alhamdulillah. Terima kasih kerana support.*<br><br>*Maybank*<br>*5570 9082 5174*<br>*Pertubuhan Kebajikan dan Pembangunan Insan Pulau Pinang* |
| 2 | *Alhamdulillah. Terima kasih kerana support. Sumbangan boleh disalurkan ke akaun berikut:*<br><br>*(block as row 1, verbatim)* |
| 3 | *Alhamdulillah, terima kasih atas sokongan. Boleh salurkan sumbangan ke akaun berikut:*<br><br>*(block as row 1, verbatim)* |

Row 1 is the canonical text. Rows 2 and 3 are drafted and **approved by the Account holder
2026-10-21**. They add only a line saying where the details go, and assert nothing row 1 does not
already assert — but they are still words posted under the organisation's name, so the approval is
what makes them usable.

**With rows 2 and 3 approved, the shared set holds three Phrasings and the duplicate is gone**: a
Post carrying both a donation question and a zakat question now draws different courtesy lines
over the same verbatim block, which is what the shared set was for. Had they been struck, the set
would hold one and the duplicate would come back.

*The zakat-validity question from `tt-zakat-001` is untouched by this and still stands* — the
subject of whether a payment counts as valid zakat is a religious one, and the reply makes no
claim either way.

## Still to do

1. **Sign-off: done, 2026-10-21.** All nine `approved_reply` texts and every Phrasing row were
   approved by the Account holder. What remains is not approval but the **native read** — the
   Malay in the table is mine and the differences between `makbulkan`, `perkenankan` and
   `dimakbulkan` are idiomatic rather than mechanical. A Malay speaker should read the eight sets
   in § Phrasings at some point; editing a row afterwards is ordinary maintenance, not a
   re-opening of the decision. Nothing is blocked on it.
2. **The hand-labelled set is built, 2026-10-21 — see `docs/labelled-set-tiktok.md`.** **564 distinct
   Comments** were labelled (drawn as 692 candidates in two sets — `random`, 401, for base rates;
   `boundary`, 291, exhaustive over the contested families). All 128 Comments drawn into both sets
   were labelled twice, in two passes, and **agree**. It answers the second half of what this item
   asked — the Intent set's vocabulary held up, with two exceptions it could not name (condolence
   for the deceased, and the "states disability without asking" family, which is where the two
   `UNCERTAIN` rows went) and comments not in Malay at all. `tools/score_threshold.py` sweeps
   `minimum_match_threshold` against it and reports false replies on silence separately from
   precision. **The threshold itself is now decided — ADR 0019** — but as a *rule* rather than a
   calibrated number: per entry, tiered by what a wrong Reply costs (0.90 / 0.80 / 0.20) with a
   0.50 floor, below its threshold a Comment taking the unmatched path rather than a cheaper
   answer. The numbers have now been measured: `tools/run_router_sweep.py` drove Jev over the
   labelled set and `tools/score_threshold.py` replayed it. The Acknowledgement number was the
   only tier posting false replies on silence, so it moved from 0.65 to 0.80 (ADR 0019); the
   Consequential and Escalation-gates numbers are confirmed, but on scored populations in single
   digits — too thin to carry a rate.
   - **The no-reply policy is settled — ADR 0018.** What this table called `OUT_OF_SCOPE` at 36%
     was two classes: **`NO_REPLY`**, correctly silent and **61.1% of rows**, and `OUT_OF_SCOPE`
     proper, a genuine coverage gap at **1.8%**. The label was renamed from `TAIL` because the
     glossary's **Tail** is the gap — the opposite — and `NO_REPLY` now receives nothing at all and
     is never Escalated, while a Tail Comment is Escalated. § Safe fallbacks and § Intents are
     updated; `tools/apply_labels.py` and `tools/score_threshold.py` carry the new vocabulary, and
     the harness no longer counts `OUT_OF_SCOPE` as a Comment that should get a Canned reply.
3. **The read gap is understood; the truncation is no longer a mystery.** `total` counts top-level
   Comments **plus their replies** and nothing else — proven by exact arithmetic on six small Posts
   (13+13=26, 3+3=6, 7+9=16, 4+4=8, 6+4=10, 30+30=62) — with `has_filtered_comments: 0` and no
   deleted marker on any Post. So the unaccounted remainder is Comments TikTok never served, not
   deleted or filtered ones. And `has_more: 0` is not evidence that a read finished: Post
   `7638968441851907336` reported `has_more: 0` at cursor 60 with 50 of 2,712 read. A read is
   complete when its count agrees with `total`, full stop. What stays open is not the gap but the
   **depth bias**: deeper reads are a strict superset of shallow ones and shift the mix (bare
   formulae 20% → 39%), so a pass that stops early reports a *different* corpus. The Adapter must
   consume the page's own `comment/list` response and check its count against `total` before a pass
   is believed. **No further harvest is needed for this table.**
4. **Rotation state, not the Phrasings themselves.** The Phrasings are approved and listed; what
   does not exist yet is the thing that rotates them — per ADR 0017 each entry's deck needs its
   rotation kept durably, so the same row is not drawn twice in a row. Two open choices: whether
   `tt-greet-001` stays a deck of two (see its note) and whether `tt-doa-001` is widened, since it
   is the entry the peak-volume arithmetic most clearly argues for.
5. **The "how do I help him?" class is decided: a Tail entry, not an Intent.** `camna cara leh
   bantu dia` and `BRO Ben mcm mana nak Bantu beliau` are readers asking how to contribute to a case
   in the Post — the opposite of a plea. Decided 2026-10-21: the class stays uncovered by a Canned
   reply and **Escalates as a Tail Comment**, so a person answers the audience the organisation most
   wants in the organisation's own words. The operative consequence is negative and matters more
   than the label: **its words must not be swept into `HELP_REQUEST`'s Variants**, because the
   current silent behaviour is exactly that, and a contributor filed as a person in difficulty is
   lost. See § `HELP_REQUEST`.
6. **The three holes in ADR 0006 are written down, 2026-10-21.** The ADR now records, under § The
   three holes this left: that a challenge which is *not a page state* is detected by the read's
   count failing to agree with `total` (a **Truncated read**, which stops the pass and leaves a
   marker); that a captcha arriving mid-post leaves the Reply an **Unknown outcome**, recorded as
   its own state and never blind-retried, because a retry is how the same Reply is posted twice;
   and that Reconciliation has **three** verdicts, with "cannot tell" actioned by nothing, because
   collapsing it into "no Reply here" re-posts every Reply the agent has ever made. All three are
   in spec issue #1 as user stories 81–83 and as Failure behaviours, which was the stated
   precondition for `/to-tickets`.
