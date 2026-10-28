"""The Router seam's real client: one wire call, a typed choice, never text.

This is the only place in the package a model is called (AC 1). Everything the
rest of the code does with a model answer goes through
:class:`agent.matching.DecisionsClient`; this module is the one implementation of
that Protocol that speaks to OpenRouter, and it is deliberately the one file
under ``agent/`` that imports ``urllib.request`` (the mechanical half of AC 1 is
``tests/test_router.py::test_urllib_request_is_imported_only_by_the_router``).

**The wire contract is pinned as configuration, not as constants scattered in
code (D1, ADR 0012).** The base URL and the model id are constructor parameters
with the values observed on 2026-10-28 as defaults. OpenRouter's own spec
composes a path that 404s -- ``.../api/v1/api/alpha/decisions``,
``.../api/v1/decisions`` and ``.../api/alpha/decisions`` all answer 404, and only
``https://openrouter.ai/api/alpha/decisions`` answers 200 -- so the base URL is a
default a test guards against ever regressing to an ``/api/v1`` spelling, rather
than something re-derived from the spec. The model id is configuration because
ADR 0012 makes a swap a model-id change **plus a threshold recalibration**; a
swap is not complete until the tuned numbers are re-measured.

**The transport is a seam (D2).** The client is handed a callable that takes an
:class:`HttpRequest` and returns the response body, so no test in the default
suite touches the network; the real :class:`UrllibTransport` is a thin wrapper
over ``urllib.request`` and is the only object that dials out. Stdlib only -- no
new dependency.

**The key comes from the environment and stays there (D3).** ``OPENROUTER_API_KEY``
is read once, at construction, and a missing key refuses *loudly at construction*
rather than at the first call mid-sweep. The key is carried only in the request's
``Authorization`` header: never in the body, never in a journal entry, never in
an exception message, never in a log line.

**The options are exactly the entries handed in (D4).** Criteria keys are the
reply ids, criteria text is each entry's own ``matching_criteria`` (never invented
prose -- the field exists so a human-approved sentence reaches the Router), and
every entry is sent, in table order, never narrowed. Narrowing by language is
routing step 3 and is not this ticket (``agent/matching.py`` D8). The ``state`` is
the normalized Comment.

**The Tail is a model choice, not a derived one (D5).** A sentinel criterion key
that cannot collide with a ``tt-``-prefixed reply id is offered alongside the
entries. A sentinel pick returns ``None``, which ``Matcher._route`` already reads
as the Tail (``OUT_OF_SCOPE``). The sentinel is *not* smuggled into
``Decisions.confidences`` -- ``_route`` refuses an id it was not handed, and the
sentinel is not a reply id.

**What makes a reading uncertain (D6).** Exactly three honest shapes return
``uncertain=True``: the answer is not a choice answer, it carries no probabilities
over the options supplied, or its chosen value is neither a supplied reply id nor
the sentinel. A malformed answer is never allowed to collapse into an *empty*
``confidences`` mapping: ``_route`` reads an empty mapping as ``OUT_OF_SCOPE``,
which would turn a Router that answered nonsense into a Comment the sweep counts
as a Tail -- so a malformed answer is uncertain (recorded, AC 3) or it raises.

**A failure is not a decision, and this is the ticket's most dangerous silent bug
(D7).** HTTP 402 (``in_flight_budget_exhausted`` -- a real mode with a positive
balance), 429, 5xx, a timeout and unparseable JSON all raise :class:`RouterUnavailable`.
They are not ``None`` (that is the Tail), not ``uncertain``, and not an empty
``confidences`` mapping. The reason: **outcomes are insert-only (ADR 0008)**, so a
Comment a failed sweep recorded as ``OUT_OF_SCOPE`` is permanently recorded as "a
reply was warranted and none fits" -- a class the sweep itself counts. A
transient failure would become a durable mis-classification.

**The transport types every wire failure, and that has to include the connection
that dies mid-read.** ``urllib`` raises more than ``URLError`` and
``TimeoutError``: a reset connection (``ConnectionResetError``, which
``http.client.RemoteDisconnected`` subclasses), a failed handshake
(``ssl.SSLError``), a body that stops early (``IncompleteRead``) and a malformed
status line are all ordinary ways for a call to fail, and all of them are
``OSError`` or ``http.client.HTTPException``. Anything the transport does not
type escapes :meth:`OpenRouterDecisions.decide`'s ``except`` clauses entirely,
which skips the journal write as well -- so an untyped failure breaks D7 *and*
D8 at once. Both families are mapped, and a test proves the mapping for each.

**The decision journal closes AC 4 durably (D8).** Today a non-escalating decision
leaves only its ``outcome`` in the sqlite record: the chosen reply id and its
confidence are lost, and only escalating outcomes reach the sink with a
``detail``. ``CommentRecord``'s schema is not touched -- the record is insert-only
and its shape is a migration -- so the Router seam owns an append-only journal
instead: one JSON line per decision (the normalized Comment, the model id, the
chosen id or the sentinel, the full probabilities, the ``uncertain``/failure
reason and the ``usage`` cost), written ``0600`` and one line per ``O_APPEND``
write, exactly as ``agent/comment_pass.EscalationSink`` writes and beside
``agent/rotation.py``'s state. **Every** decision gets exactly one entry --
chosen, tail, uncertain or failed.

**The journal is required rather than optional, because AC 4 says *every*.**
There is no journalless construction: a call site builds the account's journal
with :func:`decision_journal_path` and hands it in. A ``None`` default would have
made "every decision is recorded" a promise the client keeps only when its caller
opts in -- unenforced, unmeasurable and silently absent, which is the same shape
as the bug ADR 0019 exists to prevent. A caller with no decisions to record has
no use for this client.

**Determinism is a property of the request (D9).** The body carries no sampling
field at any level (no ``temperature``, ``top_p``, ``seed``, ...): the measurement
was that a byte-identical request produced a byte-identical answer, twice, so
temperature is never read as a matching signal and confidence is never used to
create variety. Varying a Reply is the Phrasing deck (#10), not the Router.

**No thresholds are tuned here (D10).** The client returns confidences; eligibility
stays per entry in ``agent/matching.py`` (Bar 2). The observed model returns
extreme probabilities -- 0.99 / 0.0 for the donation Question, 1.0 for
``none_of_these`` on a praise Comment -- and whether the shipped
``minimum_match_threshold`` numbers are right against that curve is an **open
measurement** (the labelled set, #9), not something this ticket settles. ADR 0012
makes the re-tuning part of a swap.

**The help/difficulty question is deliberately deferred (D11).** ``matching.py``'s
D8 says the help threshold and the difficulty signal "belong to #8", but issue
#8's acceptance criteria are about the wire call, and a second typed question is a
*routing-policy* change (it would alter how ``HELP_REQUEST`` reaches an Outcome)
with no acceptance criterion here. So question-building is the named function
:func:`build_questions`, which a second question can be added to additively, and
the second question is not built.

**There is no production call site (D12).** Nothing in the Comment pass constructs
the real client -- the pass is structurally Dry run, exactly as
``agent/write_path.py`` has no caller -- because the house pattern is that a
mechanism and the permission to use it are separate acts. One opt-in test makes a
real call, and only when ``OPENROUTER_API_KEY`` is set.
"""

from __future__ import annotations

import http.client
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from agent.matching import Decisions
from agent.reply_table import ReplyTableEntry

__all__ = (
    "API_KEY_ENV",
    "DEFAULT_BASE_URL",
    "DEFAULT_MODEL",
    "SENTINEL",
    "DecisionJournal",
    "HttpRequest",
    "MissingApiKey",
    "MissingJournal",
    "OpenRouterDecisions",
    "RouterUnavailable",
    "Transport",
    "UrllibTransport",
    "build_questions",
    "decision_journal_path",
)

# D1: the observed values, as defaults. The base URL is guarded by a test because
# the spec's own path composition 404s -- see the module docstring.
API_KEY_ENV = "OPENROUTER_API_KEY"
DEFAULT_BASE_URL = "https://openrouter.ai/api/alpha/decisions"
DEFAULT_MODEL = "typesafe/jev-1.14"

# D5: the sentinel cannot collide with a reply id because reply ids are `tt-`
# prefixed. This spelling is the one the measured response used.
SENTINEL = "none_of_these"
SENTINEL_CRITERIA = "Nothing here fits the comment"
REPLY_QUESTION_INSTRUCTIONS = "Which canned reply fits this comment?"


class MissingApiKey(RuntimeError):
    """No OpenRouter key was available at construction.

    Refused loudly at construction (D3) rather than at the first call, so a
    sweep cannot start and then die halfway through on a missing credential.
    The message never carries the key's value.
    """


class MissingJournal(RuntimeError):
    """No decision journal was supplied at construction.

    AC 4 says *every* decision records what it chose, at what confidence, or why
    it refused -- so a journalless client is refused loudly at construction
    rather than discovering, after a sweep, that nothing was written. A call site
    builds the account's journal with :func:`decision_journal_path`.
    """


class RouterUnavailable(RuntimeError):
    """The Router could not be reached, or answered with something unreadable.

    A failure is not a decision (D7): HTTP 402/429/5xx, a timeout and
    unparseable JSON all raise this rather than resolving to the Tail, to
    ``uncertain`` or to an empty confidence mapping. Resolving a failure would
    let a transient outage be recorded durably as ``OUT_OF_SCOPE`` -- a class the
    sweep counts (ADR 0008, insert-only outcomes).
    """


@dataclass(frozen=True)
class HttpRequest:
    """One outbound request: where, what headers, and the exact body bytes."""

    url: str
    headers: Mapping[str, str]
    body: bytes


class Transport(Protocol):
    """The seam: a request in, the response body text out (D2).

    Raises :class:`RouterUnavailable` for anything that is not a readable 2xx
    body. Tests hand the client a double; the default suite never dials out.
    """

    def __call__(self, request: HttpRequest) -> str: ...


class UrllibTransport:
    """The real transport: a POST over ``urllib.request``.

    ``opener`` defaults to ``urllib.request.urlopen`` and is injectable so the
    failure mapping (D7) is provable offline: an ``HTTPError`` becomes a
    :class:`RouterUnavailable` carrying its status code, and every other way the
    wire fails -- a reset connection, a failed TLS handshake, a body that stops
    early, a malformed status line -- becomes one too, rather than escaping as a
    raw ``OSError``/``http.client`` error that ``decide`` would not record.
    """

    def __init__(self, *, opener=None, timeout: float = 30.0) -> None:
        self._opener = opener or urllib.request.urlopen
        self._timeout = timeout

    def __call__(self, request: HttpRequest) -> str:
        outbound = urllib.request.Request(
            request.url,
            data=request.body,
            headers=dict(request.headers),
            method="POST",
        )
        try:
            with self._opener(outbound, timeout=self._timeout) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            # HTTPError before OSError: it subclasses URLError, which subclasses
            # OSError, so ordering is what keeps the status code legible.
            raise RouterUnavailable(f"the Router answered HTTP {exc.code}") from exc
        except (OSError, http.client.HTTPException) as exc:
            raise RouterUnavailable(f"the Router could not be reached: {exc!r}") from exc


def decision_journal_path(account: str) -> Path:
    """The account's decision journal under the state convention.

    Beside ``<account>.sqlite3``, ``<account>.rotation.json`` and
    ``<account>.escalations.jsonl``, because it is the same kind of thing:
    durable per-account state. ``DecisionJournal`` still takes an explicit
    ``path``, so tests and tools can point it at a temporary file.
    """
    from pw_session import STATE_ROOT

    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    return STATE_ROOT / f"{account}.decisions.jsonl"


class DecisionJournal:
    """Append one JSON object per decision, the way the Escalation sink writes.

    ``O_APPEND`` on a single line write, ``chmod 0600``, so the file is the same
    shape as ``agent/comment_pass.EscalationSink`` and a half-written line is
    never published. It is a log to read after the fact (AC 4), not a store to
    query, so it stays append-only and never rewrites.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append(self, entry: Mapping[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(
            self.path,
            os.O_WRONLY | os.O_CREAT | os.O_APPEND,
            0o600,
        )
        try:
            os.chmod(self.path, 0o600)
            with os.fdopen(descriptor, "a", encoding="utf-8") as stream:
                descriptor = -1
                stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
        finally:
            if descriptor >= 0:
                os.close(descriptor)


def build_questions(options: Sequence[ReplyTableEntry]) -> dict[str, Any]:
    """The typed questions for one call, built from the options handed in (D4).

    Named rather than inlined so a second question (the deferred help/difficulty
    question, D11) is additive. Criteria keys are the reply ids; the sentinel is
    added as one more key. Nothing here is narrowed, and no criteria text is
    invented: each entry carries its own ``matching_criteria``.
    """
    criteria: dict[str, str] = {
        entry.reply_id: entry.matching_criteria for entry in options
    }
    criteria[SENTINEL] = SENTINEL_CRITERIA
    return {
        "reply": {
            "type": "choice",
            "instructions": REPLY_QUESTION_INSTRUCTIONS,
            "criteria": criteria,
        }
    }


class OpenRouterDecisions:
    """The Router: one OpenRouter Decisions call per ``decide`` invocation.

    Constructed with the base URL, the model id, a transport and a journal, and
    with the key read from the environment. It returns a :class:`Decisions` over
    the options supplied, ``None`` for the Tail, or raises :class:`RouterUnavailable`.
    It never returns text of its own (AC 2) because the wire answer is a typed
    choice over the criteria it was handed, and nothing here reads a text field.

    The journal is required (AC 4): see :class:`MissingJournal`.
    """

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
        transport: Transport | None = None,
        journal: DecisionJournal,
        now=None,
    ) -> None:
        key = api_key if api_key is not None else os.environ.get(API_KEY_ENV)
        if not key:
            # The message names the variable, never a value.
            raise MissingApiKey(
                f"{API_KEY_ENV} is not set; the Router cannot be constructed "
                "without a key"
            )
        if journal is None:
            # AC 4 is "every decision records ...", so a client that records
            # nowhere is not a client this project has a use for. Refused here,
            # loudly, for the same reason the key is.
            raise MissingJournal(
                "the Router needs a decision journal; build the account's with "
                "decision_journal_path(account) -- AC 4 records every decision"
            )
        self.base_url = base_url
        self.model = model
        self._key = key
        self._transport: Transport = transport or UrllibTransport()
        self._journal = journal
        self._now = now or (lambda: datetime.now(timezone.utc))

    def decide(
        self, normalized_comment: str, options: Sequence[ReplyTableEntry]
    ) -> Decisions | None:
        request = self._request(normalized_comment, options)
        try:
            body_text = self._transport(request)
            response = json.loads(body_text)
        except RouterUnavailable as exc:
            # A failure is recorded (exactly one journal entry) and re-raised as
            # the typed failure it is -- never resolved to the Tail (D7).
            self._record(
                state=normalized_comment,
                response=None,
                chosen=None,
                probabilities={},
                uncertain=False,
                failure=str(exc),
            )
            raise
        except ValueError as exc:
            reason = f"the Router's body was not readable JSON: {exc!r}"
            self._record(
                state=normalized_comment,
                response=None,
                chosen=None,
                probabilities={},
                uncertain=False,
                failure=reason,
            )
            raise RouterUnavailable(reason) from exc
        except Exception as exc:
            # The backstop. ``Transport``'s contract is to raise
            # RouterUnavailable for anything that is not a readable 2xx body, but
            # D8 says *every* decision gets exactly one entry -- so the guarantee
            # cannot rest on every transport (or every test double) being
            # diligent. The only code inside the try is the transport call and
            # ``json.loads``, so this cannot mask a bug belonging to this module.
            reason = f"the Router call failed: {exc!r}"
            self._record(
                state=normalized_comment,
                response=None,
                chosen=None,
                probabilities={},
                uncertain=False,
                failure=reason,
            )
            raise RouterUnavailable(reason) from exc

        if not isinstance(response, dict):
            return self._uncertain(
                normalized_comment,
                None,
                None,
                {},
                "the Router's body was not a JSON object",
            )

        answer = _answer_for_reply(response)
        probabilities = _probabilities(answer)
        chosen = answer.get("choice") if isinstance(answer, dict) else None

        if not isinstance(answer, dict) or answer.get("type") != "choice":
            return self._uncertain(
                normalized_comment,
                response,
                chosen,
                probabilities,
                "the answer was not a choice answer",
            )

        options_by_id = {entry.reply_id: entry for entry in options}

        if chosen == SENTINEL:
            # D5: the sentinel pick is the Tail. Its probability is not passed on.
            self._record(
                state=normalized_comment,
                response=response,
                chosen=SENTINEL,
                probabilities=probabilities,
                uncertain=False,
                failure=None,
            )
            return None

        if chosen not in options_by_id:
            return self._uncertain(
                normalized_comment,
                response,
                chosen,
                probabilities,
                "the chosen value was neither an offered reply id nor the sentinel",
            )

        confidences: dict[str, float] = {}
        for reply_id, value in probabilities.items():
            if reply_id not in options_by_id:
                # Only ids the Router was offered are passed on. The sentinel and
                # any invented id are dropped, so ``_route`` never sees an id it
                # was not handed.
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return self._uncertain(
                    normalized_comment,
                    response,
                    chosen,
                    probabilities,
                    "a probability was not a number",
                )
            confidences[reply_id] = float(value)

        if not confidences:
            # D6: a malformed answer must not become an empty mapping, which
            # ``_route`` reads as the Tail. It is uncertain instead.
            return self._uncertain(
                normalized_comment,
                response,
                chosen,
                probabilities,
                "the answer carried no probabilities over the options supplied",
            )

        self._record(
            state=normalized_comment,
            response=response,
            chosen=chosen,
            probabilities=probabilities,
            uncertain=False,
            failure=None,
        )
        return Decisions(confidences=confidences)

    def _request(
        self, normalized_comment: str, options: Sequence[ReplyTableEntry]
    ) -> HttpRequest:
        # D9: the body carries no sampling field at any level, so two identical
        # items produce a byte-identical request.
        payload = {
            "model": self.model,
            "state": normalized_comment,
            "questions": build_questions(options),
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            # The key lives here and only here (D3).
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
        }
        return HttpRequest(url=self.base_url, headers=headers, body=body)

    def _uncertain(
        self,
        state: str,
        response: Mapping[str, Any] | None,
        chosen: Any,
        probabilities: Mapping[str, Any],
        reason: str,
    ) -> Decisions:
        """Record a refused reading and hand back an uncertain decision (D6)."""
        self._record(
            state=state,
            response=response,
            chosen=chosen,
            probabilities=probabilities,
            uncertain=True,
            failure=reason,
        )
        return Decisions(confidences={}, uncertain=True)

    def _record(
        self,
        *,
        state: str,
        response: Mapping[str, Any] | None,
        chosen: Any,
        probabilities: Mapping[str, Any],
        uncertain: bool,
        failure: str | None,
    ) -> None:
        """One journal line per decision (D8). No key is ever written here."""
        reported = response.get("model") if isinstance(response, Mapping) else None
        usage = response.get("usage") if isinstance(response, Mapping) else None
        self._journal.append(
            {
                "when": _utc(self._now()).isoformat(),
                "model": self.model,
                "model_reported": reported,
                "state": state,
                "chosen": chosen,
                "probabilities": dict(probabilities),
                "uncertain": uncertain,
                "failure": failure,
                "usage": usage,
            }
        )


def _answer_for_reply(response: Mapping[str, Any]) -> Any:
    answers = response.get("answers")
    if isinstance(answers, Mapping):
        return answers.get("reply")
    return None


def _probabilities(answer: Any) -> dict[str, Any]:
    if isinstance(answer, Mapping):
        raw = answer.get("probabilities")
        if isinstance(raw, Mapping):
            return dict(raw)
    return {}


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
