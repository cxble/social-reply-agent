"""The structural No-reply test, decided from a Comment's own text.

ADR 0018 splits the two ways a Comment can go unanswered: a **Tail** (a Reply was
warranted and no entry fits -- a gap, Escalated) and **NO_REPLY** (nothing was
addressed to the organisation -- silence is the design working, and nobody is
shown it). The two are told apart at runtime, before the Router is consulted,
because 61.1% of the corpus is NO_REPLY and routing that share to a human is how
the Escalation sink stops being read (ADR 0014).

The test here is the one ADR 0018 names, and it is deliberately *not* "did an
entry match": **"does this Comment present anything addressed to the
organisation?"** A Comment with nothing to answer gets nothing at any confidence;
a Comment that asked something and was not understood is a Tail and Escalates,
however low the confidence. Widening this test to swallow a plea is the failure
ADR 0018 spends its length forbidding, so when the shape is ambiguous this module
returns ``None`` and lets the Router decide. ``@org berapa harga`` is a mention
*and* a question: it presents something, so it must reach the Router.

Three shapes are decidable from a Comment's text today:

* a bare formula or interjection (``agent.normalize.bare_interjection`` -- 16% of
  the corpus, and the reason that helper exists);
* an emoji-only or sticker-only Comment (``agent.normalize.is_empty``); and
* a Comment that is nothing but mentions or support tags.

**Chatter between commenters is not decidable from a Comment's text, and this
module does not guess it.** It is a structural fact about the page -- one person
replying to another -- and ``agent.adapters.tiktok.Comment`` carries no field for
it. It is named here rather than detected: the Adapter's structure (ticket #16)
has to carry the reply-to relationship before this shape can be recognised, and a
word-level heuristic for it would be exactly the kind of rule ADR 0018 forbids.

Not in this ticket either (D8): the help threshold and the difficulty signal are
a second typed question to the Router that does not exist yet (#8), and language
detection (routing step 3) is #28-30. This module answers one question only.
"""

from __future__ import annotations

import re
from enum import Enum

from agent.normalize import bare_interjection, is_empty

__all__ = ("NoReplyReason", "no_reply_reason")


class NoReplyReason(Enum):
    """Why a Comment presents nothing addressed to the organisation.

    A bare bool would throw the reason away; the reason is what the record and
    the Escalation sink need to stay auditable (ADR 0019: Dry run records which
    bar refused a Comment, and silence is indistinguishable from a crash unless
    the decision to stay silent was written down).
    """

    BARE_FORMULA = "bare formula"
    EMPTY = "emoji-only or sticker-only"
    MENTION_OR_SUPPORT_TAG = "mention or support tag"


# A mention is ``@`` followed by a handle; a support tag is ``#`` followed by a
# tag word. Both are the whole Comment when the Comment is nothing else. The
# patterns are intentionally narrow: a token that is not exactly a handle or a
# tag is left to the Router.
_MENTION = re.compile(r"@[A-Za-z0-9_.]+")
_SUPPORT_TAG = re.compile(r"#[A-Za-z0-9_]+")


def no_reply_reason(text: str) -> NoReplyReason | None:
    """The reason *text* is a No-reply Comment, or ``None`` to reach the Router.

    ``None`` means "this Comment may present something addressed to the
    organisation, or this module cannot tell" -- both go to the Router, because
    guessing silence for a plea is the failure ADR 0018 names.
    """
    if bare_interjection(text):
        return NoReplyReason.BARE_FORMULA
    if is_empty(text):
        return NoReplyReason.EMPTY
    if _mentions_or_support_tags_only(text):
        return NoReplyReason.MENTION_OR_SUPPORT_TAG
    return None


def _mentions_or_support_tags_only(text: str) -> bool:
    """True when every word-bearing token is a mention or a support tag.

    Removing the mentions and tags must leave no word character at all, so a
    mention that also carries a question (``@org berapa harga``) is not swallowed.
    At least one mention or tag must be present, so an emoji-only or
    punctuation-only Comment is not mistaken for this shape.
    """
    if not (_MENTION.search(text) or _SUPPORT_TAG.search(text)):
        return False
    remainder = _SUPPORT_TAG.sub(" ", _MENTION.sub(" ", text))
    return re.search(r"\w", remainder) is None
