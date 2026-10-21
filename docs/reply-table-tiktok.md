# Reply table: @benooicb on TikTok

Drafted 2026-10-21 from a harvested corpus of real Comments. **Every Variant below is a spelling
that actually appears in the corpus**; nothing is invented. `reply_id`s are stable; the
`approved_reply` text is the part that needs the Account holder's sign-off before it can be
posted. Nothing is blocked on facts any more — where the answer was unknown, the outcome is
Escalation rather than a guess.

## What the corpus is, and what it is not

Comments read from `@benooicb`'s posts with a logged-out **headed** browser, harvested
2026-10-21.

**228 Comments across 15 Posts.** Three Posts are pinned and carry 660K–989K views; the rest run
from 251 to 21K. The comment sections are overwhelmingly Malay, Islamic-framed, and short.

Two limits worth stating before anything below is trusted:

- **The reads are far shallower than they looked, and the numbers are now known.** Most Posts
  returned exactly 20 Comments, which is the **first page**, not the section. Two measurements
  on 2026-10-21 put the real gap: TikTok's own comment response reports `total: 569` for one of
  these Posts, and a driven read of that same Post recovered **78** before the response started
  coming back empty with `has_more: 0`. So the harvest read roughly **14% of that section**, and
  the table's Variant lists are built on a few per cent of a few Posts' heads. The corpus is a
  real sample and not a representative one. The unexplained remainder — 569 reported against 78
  retrievable logged-out — is unresolved, and may be replies counted in the total, or a
  logged-out ceiling.
- **The sample skews to recent and popular.** Old buried Comments, and anything below the fold
  on a busy Post, are absent. The Variant list will grow.

## The shape that matters

**The great majority of Comments need no answer at all.** The dominant Comment is a doa, a
blessing, or a bare `Alhamdulillah`. A table sized for the majority would be a table of
acknowledgements; the useful work is in the minority, and the minority is where the risk is.

## Intents

| `intent` | what it is | in the corpus | outcome |
|---|---|---|---|
| `DOA_BLESSING` | a prayer or blessing for a person or the work | dominant | Canned reply |
| `PRAISE_ENCOURAGE` | praise or encouragement to keep going | common | Canned reply |
| `GREETING` | a salutation carrying nothing else | common | Canned reply |
| `DOA_REQUEST` | **the commenter asking to be prayed for** | common | Canned reply |
| `BENEFICIARY_THANKS` | thanks from someone the organisation has helped | occasional | Canned reply |
| `CONVERT_CONGRATS` | a blessing aimed at a new Muslim | one Post | Canned reply |
| `JOIN_ENQUIRY` | asking how to become a member or volunteer | occasional | **Escalate.** No answer to give. |
| `DONATION_ENQUIRY` | asking how to contribute | occasional | Canned reply — approved 2026-10-21 |
| `ZAKAT_SEDEKAH_ENQUIRY` | asking about zakat, sedekah or infaq by name | none yet | Canned reply — same text as donation |
| `HELP_REQUEST` | **a person asking the organisation for help** | common, on ziarah Posts | **Escalate. Never a Canned reply.** |
| `OUT_OF_SCOPE` | unrelated, emoji-only, spam, follow-for-follow | common | no reply |

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

- `approved_reply`: *Aamiin. Semoga Allah permudahkan segala urusan tuan/puan.* **needs sign-off**
- `matching_criteria`: a prayer or blessing with no request in it
- `known_variants` (real, from the corpus):
  - `alhamdulillah utk saudara baru moga Allah memberi cahaya kepada hambanya aminnn3 yralamin`
  - `Alhandullillah. Semoga Allah melimpahi rahmat keatas Gary.`
  - `Alhamdulillah... Semoga En Gary terus istiqamah dgn Islam hingga ke jannah.. Aamiinn`
  - `alhamdulllah semuga dipermudahkan segala urusan`
  - `Moga dipemudahkan urusan gary n bro ben`
  - `semuga semua urusan keluarga hashimah selesai dgn baik,amin`
  - `Smoga cpat2 baik dan smoga dipermudahkan segalanya aamiin`
  - `semoga Allah berikan kesembuhan buat mereka..aamiin`
  - `Semoga urusan pakcik ni dipermudahkan Allah Swt...`
  - `semoga dipermudahkan`
  - `Semoga Allah angkat derajat Bro Ben🤲🤲🤲`

The variants are the point. The same blessing arrives as `Alhamdulillah`, `Alhandullillah`,
`Alhamdulillaah`, `Alhamdulillah`, `Alhamdulilleh`, `alhamdulllah`, `Alhamdulilah`,
`Alhamdulillah` — and `semoga` as `semuga`, `smoga`, `moga`, `smg`, and dropped altogether in
`amin`/`aamiin`/`Amin`/`a.miin`. Normalization has to fold those without touching the Comment as
stored.

---

### `tt-doa-002` — `DOA_BLESSING`, English or mixed

- `language`: en
- `approved_reply`: *Aamiin. Thank you for your doa.* **needs sign-off**
- `known_variants`:
  - `Alhamdulillah, Bro Ben ,all the praise to our Almighty Alloh. keep it up till ur last breath. Aamieen.`
  - `Jazakallah Khairan Kathira semoga Allah permudahkan segala urusan dunia dan akhiratnya pada saudara 2saudari 2 semua amin ya Allah amin ya Rabbal Alam`
  - `Bro Ben. With your good and kind hearted, may Allah bless you bro Ben.`
  - `to be honestly you are the best. Tkasih ya Allah Aamiinn.`

The second and fourth are Malay and English in one Comment; a language detector that forces one
class will misroute them, which `docs/reply-routing.md` already forbids.

---

### `tt-praise-001` — `PRAISE_ENCOURAGE`, Malay

- `approved_reply`: *Terima kasih. Semoga Allah membalas budi baik tuan/puan.* **needs sign-off**
- `matching_criteria`: praise or encouragement with no request and no explicit doa
- `known_variants`:
  - `kerja yg mulia.. teruskan perjuangan anda`
  - `waalaikumsalam.. syabas sahabat teruskan usaha yg murni itu..`
  - `terbaik bro Ben. Keep it up till it last breath. Amieen Ya Alloh.`
  - `waalaikumusalam... tahniah tuan. teruskan perjuangan tuan.`
  - `terbaik`
  - `Terbaik bro ben.`
  - `betul Abang baik keren`
  - `terima kasih insan baik`
  - `الحمدالله!! تروسكن اسها مورني` *(Jawi)*

`terbaik` alone is one of the most frequent bodies in the corpus. It is a complete Comment and
needs a reply that does not read as sarcasm when repeated twenty times in one section.

---

### `tt-greet-001` — `GREETING`, Malay

- `approved_reply`: *Waalaikumussalam warahmatullahi wabarakatuh.* **needs sign-off**
- `matching_criteria`: a salutation carrying no other content
- `known_variants`:
  - `assalamualaikum sahabat lama`
  - `salam tuan`
  - `Assalammualakum`
  - `ASSALAMUALAIKUM`
  - `Assalamuaalaikum terbaik`
  - `waalaikumussalam wbt`
  - `waalaikummussalam warahmatullahiwabarokatuh`
  - `Waalaikumusalam... Alhamdulillah`
  - `a.mualaikum bro.terbaik`
  - `Waalaikummusalam`

`a.mualaikum` is a real spelling in the corpus and no reasonable normalizer predicts it. It is
the case for matching on Jev's typed decision over a Normalized Comment rather than on a
dictionary of known forms.

---

### `tt-doareq-001` — `DOA_REQUEST`, Malay

- `approved_reply`: *Aamiin, semoga Allah makbulkan hajat tuan/puan.* **needs sign-off**
- `matching_criteria`: **the commenter asking to be prayed for** — a request whose object is the
  commenter's own wish, not the organisation's help
- `known_variants`:
  - `Tolong DOAKAN saya jgk utk ke sana 😭😭😭`
  - `Doakan sy dan keluarga juga dpat menunaikan haji dan Umrah satu hari nnti`
  - `Doakan saya , semoga Allah izinkan saya ziarah ke tanah suci juga.. Saya teringin sangat moga dijemput kesana.`
  - `Doakan juga saya dan suami menjadi tetamu Allah`
  - `Semoga saya juga berpeluang menjadi tetamu Allah`
  - `moga saya d jemput ke sana..🤲🤲`
  - `doakan sy Kaya raya utk Bantu org lain🙏🏻`
  - `Ninie Salim: ya Allah.. semoga saya pun dapat pergi juga nanti🤲🏻`
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

- `approved_reply`: *Alhamdulillah. Terima kasih kembali.* **needs sign-off**
- `matching_criteria`: thanks from someone the organisation has already helped
- `known_variants`:
  - `syukur alhamdulilah terima kasih datang melawat ayah saya Dan bantuan pampers semoga Allah permudahkan semua urusan`
  - `Alhamdulillah Terbaik En.Ben Oi tolong Keluarga dlm kesusahan`
  - `syukur Alhamdulilah,terima kasih Bro Ben Ooi`
  - `Alhamdulillah bro ben dan terima kasih kerana membantu insan insan yg memerlukan bantuan.`
  - `halim: terima kasih jadi orang baikkk`
  - `Intan kaseh: Tkaseh tuan srmoga abg sehat hendak nya`
  - `terima kasih insan baik`

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

- `approved_reply`: *Alhamdulillah. Semoga Allah kekalkan tuan/puan dalam hidayah-Nya.* **needs sign-off**
- `known_variants`:
  - `ahlan wa sahlan ilal islam.`
  - `waalaikumussalam wbt terima kasih syukur Alhamdulillaah selamat masuk Islam senyum ceria ye semoga kekal sampai akhir hayat`
  - `Alhamdulillah. bertuahnya. Kembali kpd fitrah`
- **Post-scoped.** Eligible only on a Post whose caption is a conversion post. Elsewhere
  `ahlan wa sahlan` is a greeting.

---

### `tt-join-001` — `JOIN_ENQUIRY`, Malay — **Escalate. Never a Canned reply.**

*Decided by the Account holder 2026-10-21.* Not a posted entry: the agent recognises it, posts
nothing, and hands it to a human. ADR 0016 carries the decision.

- `approved_reply`: **none, and none is wanted.** Deciding to escalate resolved the blocking
  fact rather than answering it — the agent no longer needs to know how someone joins, because
  it is not going to say.
- `known_variants`:
  - `Sy nk join pertubuhan ni boleh tak 😁`
  - `Saya nak join bleh x`
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
- `known_variants`:
  - `bagaimana kalo kita nak menyumbang`
  - `Assalammualakum Tuan nk tanya mcm mna klu kita nk buat Sumbangan ikhlas`
- `minimum_match_threshold`: to be calibrated
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
- `known_variants`: **none in the corpus.** This Intent is predicted from the Account's subject
  matter, not observed, and its Variant list stays empty until real Comments supply spellings.
  The entry is otherwise live, so the first real Comment matches against
  `matching_criteria` alone.
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

| `reply_id` | Phrasings | note |
|---|---|---|
| `tt-doa-001` | 3–4 | the highest-volume Intent in the corpus, so repetition here is the most visible |
| `tt-doa-002` | 3–4 | as above |
| `tt-praise-001` | 3–4 | |
| `tt-greet-001` | 2 | see below — the only entry where "vary" means something different |
| `tt-doareq-001` | 3–4 | |
| `tt-thanks-001` | 3–4 | |
| `tt-convert-001` | 3–4 | |
| `tt-donate-001` | 2+ **shared set** | see below — this and the zakat entry share one set |
| `tt-zakat-001` | 2+ **shared set** | see below — this and the donation entry share one set |
| `tt-join-001` | — | Escalates. There is no text to vary. |
| `HELP_REQUEST` | — | Escalates. There is no text to vary. |

One alternate is not worth having: two Phrasings produce a visible A/B alternation, which a
reader notices faster than they notice repetition at low volume.

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

**Every Phrasing needs its own sign-off**, because a Phrasing is approved text under ADR 0015.
The count in the table above is the size of the sign-off, not the number of entries.

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

**This is not a rare edge case; it is a substantial share of the corpus on those Posts.** The
design predicted it from the captions, and the harvest confirms it in volume. Every one of the
first four contains the same words as the routine `JOIN_ENQUIRY`, and two of them are
indistinguishable from it by keyword. A table that answers the enquiry answers the plea.

**The agent's silence is not the deliverable — the human's answer is.** An escalated Comment
nobody reads is the same as no system at all, so the Escalation sink has to be something the
Account holder actually watches.

---

## Safe fallbacks for ambiguous Comments

`docs/reply-routing.md` sets the four-way fallback. What the corpus adds is where the boundaries
actually fall, because the ambiguous cases here are not evenly distributed — they cluster on
exactly the Comments where a wrong reply does public harm.

**Two thresholds, not one.** The `minimum_match_threshold` on an entry decides whether a Canned
reply may be posted. A second, deliberately much lower **help threshold** decides whether a
human is needed. They are different questions and collapsing them into one number is the mistake
this section exists to prevent.

The asymmetry is the whole argument, and it is the same one ADR 0014 makes:

- A **false positive** — escalating a Comment that was really routine — costs a human one skim.
- A **false negative** — posting `Sy nk join pertubuhan ni boleh tak`'s canned link under
  `macam mana nak mohon. sy oku fizikal and now tgah hadapi risiko buta kekal` — is a public
  failure by an organisation whose stated purpose is helping that person.

So the help threshold is set to catch, not to be precise. **Any evidence of a person in
difficulty plus any kind of ask routes to a human, at any confidence.**

| Situation | Outcome |
|---|---|
| One Intent matches above threshold; no difficulty signal | Canned reply |
| **Any difficulty signal** (own or a named third party's) **plus an ask**, even at low confidence | **Escalate** |
| Two mutually exclusive Intents both match above threshold | **Escalate** — never pick the higher |
| `nak mohon` with nothing else to disambiguate it | **Escalate** |
| Tense/direction unclear: thanks for help, or a plea for help | **Escalate** |
| Language or script not confidently read | **Escalate** |
| No Intent matches; no difficulty signal | Tail reply, or nothing |
| Tail would need a fact the Account holder has not approved | **Escalate** |
| The Post is a welfare-ziarah Post and the Comment is not confidently routine | **Escalate** |

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
  spam to filter — but it is worth knowing the corpus is not 228 independent voices.

## Sign-off: the nine `approved_reply` texts

Everything the agent can post. Read this list and nothing else; each line is the complete text.
Approve, edit, or strike.

| `reply_id` | Intent | text as it would be posted | status |
|---|---|---|---|
| `tt-doa-001` | `DOA_BLESSING` (ms) | *Aamiin. Semoga Allah permudahkan segala urusan tuan/puan.* | needs sign-off |
| `tt-doa-002` | `DOA_BLESSING` (en) | *Aamiin. Thank you for your doa.* | needs sign-off |
| `tt-praise-001` | `PRAISE_ENCOURAGE` | *Terima kasih. Semoga Allah membalas budi baik tuan/puan.* | needs sign-off |
| `tt-greet-001` | `GREETING` | *Waalaikumussalam warahmatullahi wabarakatuh.* | needs sign-off |
| `tt-doareq-001` | `DOA_REQUEST` | *Aamiin, semoga Allah makbulkan hajat tuan/puan.* | needs sign-off |
| `tt-thanks-001` | `BENEFICIARY_THANKS` | *Alhamdulillah. Terima kasih kembali.* | needs sign-off |
| `tt-convert-001` | `CONVERT_CONGRATS` | *Alhamdulillah. Semoga Allah kekalkan tuan/puan dalam hidayah-Nya.* | needs sign-off |
| `tt-donate-001` | `DONATION_ENQUIRY` | *Alhamdulillah. Terima kasih kerana support.*<br><br>*Maybank*<br>*5570 9082 5174*<br>*Pertubuhan Kebajikan dan Pembangunan Insan Pulau Pinang* | **approved by the Account holder 2026-10-21** |
| `tt-zakat-001` | `ZAKAT_SEDEKAH_ENQUIRY` | same text as `tt-donate-001` | **approved by the Account holder 2026-10-21** |

Two `Approved` rows are the Account holder's own words and are recorded verbatim. The seven
drafted rows above them are mine and are the ones that need a decision.

Not in this table, because there is no text: `HELP_REQUEST` and `JOIN_ENQUIRY` both Escalate.

Approving a row above approves that entry's **canonical text** — the first of its Phrasings.
Under ADR 0017 each entry also needs alternates so the same words do not repeat, and those are a
second sign-off. Approving these nine first is the right order: it settles what the agent is
allowed to say before deciding how many ways it may say it. The per-entry requirement is in
§ Variation above.

## Phrasings drafted for sign-off

Under ADR 0017 each entry needs alternates so the same words do not repeat. These are drafted for
the seven entries whose canonical text is mine. The two Account-holder entries are not drafted
here and are addressed at the end of this section.

**These are deliberately close to each other, and that is the point.** A person answering the
same kind of Comment twenty times says nearly the same thing with small differences, and that
near-repeat is what a person looks like. Text varying *widely* from one Reply to the next reads
as a phrasebook being sampled — a machine signal in its own right, and a louder one than the
repetition it was meant to avoid. The target is the smallest difference that avoids an exact
repeat, not the largest.

Row 1 of each set is the canonical text already in the sign-off table above. Approve, edit, or
strike any row.

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

*If the shorter form reads as curt on this Account, strike row 2 and the entry ships a deck of
one — which is a legitimate outcome, not a gap.*

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

*Row 2 is the one to look at hardest.* Congratulating someone on embracing Islam is ordinary
usage here, but it is a stronger thing to say than a blessing, so it is the row most likely to
want striking.

**A limit on who can judge these.** I drafted the Malay, and I am not the authority on it. The
difference between `makbulkan`, `perkenankan` and `dimakbulkan` is idiomatic, not mechanical, and
the same is true of the register in every set above. These want a native read before sign-off —
mine is a proposal that a Malay speaker should correct.

### `tt-donate-001` and `tt-zakat-001` — one shared set, frames drafted

**Resolved 2026-10-21: donating and zakat are the same thing here**, so these two entries point
at one shared Phrasing set and share one rotation.

The bank, account number and payee are the Account holder's verbatim words, identical in every
row, and never reworded, reformatted or reconstructed. Only the courtesy line above the block
varies, and rows 2 and 3 are drafted for sign-off.

| # | text as it would be posted |
|---|---|
| 1 | *Alhamdulillah. Terima kasih kerana support.*<br><br>*Maybank*<br>*5570 9082 5174*<br>*Pertubuhan Kebajikan dan Pembangunan Insan Pulau Pinang* |
| 2 | *Alhamdulillah. Terima kasih kerana support. Sumbangan boleh disalurkan ke akaun berikut:*<br><br>*(block as row 1, verbatim)* |
| 3 | *Alhamdulillah, terima kasih atas sokongan. Boleh salurkan sumbangan ke akaun berikut:*<br><br>*(block as row 1, verbatim)* |

Row 1 is the canonical text, already approved by the Account holder. Rows 2 and 3 are mine and
need sign-off. They add only a line saying where the details go, and assert nothing row 1 does
not already assert — but they are still words posted under the organisation's name, so they are
the Account holder's to approve or strike.

**If rows 2 and 3 are struck, the set holds one Phrasing and the duplicate comes back**: a Post
carrying both a donation question and a zakat question gets the same reply twice. One approved
alternate is enough to prevent it, and that is a knowing choice rather than an oversight.

*The zakat-validity question from `tt-zakat-001` is untouched by this and still stands* — the
subject of whether a payment counts as valid zakat is a religious one, and the reply makes no
claim either way.

## Still to do

1. Sign-off on the seven drafted texts in the table above.
2. Calibrate `minimum_match_threshold` per entry against the corpus rather than guessing it.
3. **Re-harvest, now that both read errors have a known fix.** Pagination works: driving the
   comment panel's own scroll container to its end loads the next page — 20 → 40 → 60 → 77 → 78
   on the Post measured, with the API cursor advancing `0, 20, 40, 60, 80`. `scrollIntoView` on
   the last item, which the harvester used, does nothing. Identity works: `cid` arrives in the
   page's own `/api/comment/list/` response alongside `total`, `cursor` and `has_more`.
   **But a driven read still stopped at 78 against a reported `total` of 569**, with the
   response returning empty and `has_more: 0` from cursor 80 onward. That gap has to be
   explained — replies counted in the total, or a logged-out ceiling — before a re-harvest is
   worth the compute. The Adapter also has to consume that response rather than parse DOM rows,
   and check what it read against `total` before a pass is believed.
   See `docs/research/comment-identity.md`.
4. **Author the Phrasings.** Per ADR 0017 and § Variation, each Canned reply needs 2–4 approved
   alternates so no text repeats, with rotation state kept durably per entry. `tt-greet-001`
   varies between existing salam formulas rather than drafted sentences, and `tt-donate-001`
   with `tt-zakat-001` need Phrasings shared across the pair or a zakat-specific frame — both
   the Account holder's words to supply, not a drafting job.
