# What the Router costs

Research note. Figures observed 2026-10-21. Kept because the cost question decided a vendor, and the numbers decay slowly enough to be worth not re-deriving.

## Jev is billed per input token, and output is free

`https://openrouter.ai/api/v1/models/typesafe/jev-1.14/endpoints`:

```json
"pricing": { "prompt": "0.000000042", "completion": "0", "discount": 0 }
```

- `$0.000000042` per input token = **$0.042 per 1M input tokens**
- **$0.00 per output token**
- The object carries only `prompt`, `completion`, `discount` — no per-request, image or cache field. There is no per-request price.

TypeSafe's own docs agree, and OpenRouter adds no markup:

> Price (per Btok / per Mtok) \$42 / \$0.042 — **You pay per input token. Output tokens are free.**
> — `https://docs.typesafe.ai/models`

> Input tokens: **$0.042 / MTok**. Output tokens: **FREE (too cheap to meter).**
> — `https://typesafe.ai/blog/introducing-system-one-models-and-jev`

Billing basis is proved, not inferred, by OpenRouter's own example response for `POST /api/alpha/decisions`: `{"cost": 1.9992e-05, "input_tokens": 476, "output_tokens": 70}`, where `476 × 0.000000042 = 1.9992e-05` exactly and the 70 output tokens contribute nothing.

**There is no free tier**, confirmed across the docs index, the models page, the pricing post and the enterprise page. Volume pricing is unpublished; only *"higher limits are available on custom and enterprise plans"* — a limits change, not a price change.

## Cost at volume

Real classification calls, measured by OpenRouter's own cookbooks (`classify-reddit-comments-with-jev`: *"$0.00057 for the captured run… 27 comments, about $0.021 per 1,000"*; `jev-classification`: 609.9 input tokens/item), run **~500–610 input tokens per Comment**. Take **$0.0211 per 1,000 Comments** — which is what ~500 input tokens costs, and input tokens are the whole bill (see the correction at the foot of this note). Our own calls land on both sides of it: **$0.0156/1,000** for a narrow option set (371 tokens) and **$0.0265/1,000** for the full shipped table (632 tokens).

| Comments/day | Calls/month | Jev cost/month | +5.5% OpenRouter credit fee |
|---|---|---|---|
| 300 | 9,000 | $0.19 | $0.20 |
| 900 | 27,000 | $0.57 | $0.60 |
| 3,000 | 90,000 | $1.90 | $2.00 |
| 10,000 | 300,000 | $6.33 | $6.68 |
| 100,000 | 3,000,000 | $63 | $67 |

**Cost is not a constraint at any volume under consideration.** At the paced ceiling this machine can reach (~600–900 Comments/day) the Router costs well under a dollar a month.

## Generation is not the expensive primitive

The cheapest usable generative models on a 300-token prompt → 50-token reply:

| Model | In /M | Out /M | Per call |
|---|---|---|---|
| `ibm-granite/granite-4.0-h-micro` | $0.017 | $0.112 | $0.0000107 |
| `openai/gpt-oss-20b` | $0.018 | $0.090 | $0.0000099 |
| `inclusionai/ling-3.0-flash` | $0.021 | $0.063 | $0.0000095 |
| `mistralai/mistral-nemo` | $0.029 | $0.030 | $0.0000102 |

A real Jev classification call is **$0.0000211–0.0000256**, so a short generation call is roughly **half** the cost of one Jev call. Since Tail Comments are a minority of Comments, the Tail is cheaper than the Router, not more expensive. The intuition that writing Reply text would dominate the bill is wrong.

The asymmetry favours Jev for pure classification: because Jev's output is free, the cheapest generative models are *more* expensive per request than Jev when doing the same classification job, since each charges for the label it emits.

## OpenRouter does have a `decisions` output modality

The default `/api/v1/models` listing returns only models whose output includes `text` — the OpenAPI spec says so verbatim: *"Filter models by output modality… Defaults to `text`."* Jev is decisions-only, so it is filtered out of that listing entirely.

Querying `?output_modalities=decisions` returns **27 decision models from 13 makers**, all input-token-billed with free output, all on the same documented Decisions API:

| Model | $/M in | vs Jev |
|---|---|---|
| `respan/span-01-lite` | $0.00 | free |
| `inception/mercury-decide:free` | $0.00 | free |
| `perplexity/pplx-decider-flash-v1.2`, `respan/span-02` | $0.010 | 76% cheaper |
| `liquid/d1`, `inception/mercury-decide`, `respan/span-01`, `perplexity/pplx-decider-v1.2` | $0.020 | 52% cheaper |
| `cloudflare/clef-flash` | $0.021–0.038 | 10–50% cheaper |
| **`typesafe/jev-1.14` / `1.13`** | **$0.042** | — |
| `microsoft/microsoft-decision-1`, `liquid/d1-ultra`, `jaredpalmer/kev-4b`, `togethercomputer/tev1-4b-experimental` | $0.042 | identical |
| `openai/gpt-6-luna-decisions` $0.10 · `cloudflare/clef-omni` $0.15 · `cloudflare/clef` $0.24 | | pricier |

Switching model is a `model` field change plus re-tuning thresholds: *"Probabilities differ between models on the same question, so pick thresholds again for each model you try."*

**The free options cannot carry this workload.** `:free` variants are capped at 20 req/min and **50 req/day** (under 10 credits) or **1,000 req/day**, so `inception/mercury-decide:free` cannot serve a thousand Comments a day regardless of its price. Whether `respan/span-01-lite`'s published `$0` is a true zero or an unpublished price is unverified.

## Non-OpenRouter alternatives: none is both cheaper and equivalent

- **Jina AI** — the only true match: `POST https://api.jina.ai/v1/classify` takes caller-supplied `labels` (up to 256) and returns softmax probabilities. Price is not published as visible text (`jina.ai/pricing` → 404); its packs imply **~$0.045–0.050/1M**, i.e. more than Jev.
- **Cohere Classify** — **deprecated**, effective 2025-09-15. No published price.
- **Voyage AI** — no classifier product; rerank is relevance ranking, not a typed choice.
- **Hugging Face** zero-shot-classification — takes `candidate_labels`, but is billed by compute time, so there is no per-request price to compare.
- **AWS Bedrock** — no classification endpoint.
- **Routers** — NotDiamond is $0.05/M routed (pricier than Jev, no confidence); Martian's pricing page is 404; RouteLLM has no hosted API; Portkey is a $49/mo deterministic gateway. OpenRouter's own `auto` returns only the chosen model name and **no confidence**, which would leave the Router unable to Escalate on low confidence at all — a correctness loss, not a cost saving.

## Gotchas that touch the design

| Item | Finding |
|---|---|
| **`in_flight_budget_exhausted`** | OpenRouter holds an *estimated* cost per in-flight request and rejects with **402** before reaching the provider, **even with a positive balance**. A real risk once concurrency exists. |
| **Prompt caching** | None. `"supports_implicit_caching": false`. A normalisation cache in front of the Router is therefore ours to build, not something the provider does. |
| **Batch discount** | None. `typesafe/jev-1.14:batch` resolves but has **0 endpoints**. |
| **Long context** | Free — same per-token rate. Requests over ~32,000 bytes, or any image, auto-run in a slower mode. |
| **Images** | Billed as ordinary input tokens; no separate charge. |
| **Failed / fallback attempts** | Not billed. |
| **Rate limits** | TypeSafe: per-org, tokens/sec *and* requests/sec, 429 on breach. Higher tiers change limits, not price. |
| **OpenRouter credit fee** | **5.5% Standard / 8% Business on credit purchases**, never on individual requests — a surcharge on the whole bill, not per call. |

## Not verified

- Whether `respan/span-01-lite`'s or the rerankers' published `$0` is a true free tier or an unpublished price.
- Whether `respan/span-01-lite` carries `:free` request limits, since it lacks the `:free` suffix.
- TypeSafe enterprise/volume pricing — unpublished, and `console.typesafe.ai` is behind a Cloudflare challenge, so "no free tier" rests on public docs rather than account pages.
- No published billing increment or per-request minimum was found, which is not the same as proving none exists.

## Corrected 2026-10-28, when ticket #8 made real calls

- **The "No model calls were executed" line that stood here is no longer true.** Ticket #8's
  `agent/router.py` made live calls against `typesafe/jev-1.14`, and the billing basis above is
  now confirmed rather than inferred: `usage.cost == input_tokens × 4.2e-08` **exactly**, in all
  three observed calls (371 → 1.5582e-05, 476 → 1.9992e-05, 632 → 2.6544e-05). Output tokens are
  free, as the pricing table says.
- **So the cost per call is the size of the option set**, not a flat rate: every criterion
  offered is tokens on the wire. The relevant figure today is the **full shipped table — 11
  criteria, 632 input tokens, $0.0265 per 1,000 Comments**, which is *above* the note's $0.0211
  rather than below it. Narrowing options by language (routing step 3, not yet built) would move
  it back down toward $0.0156. Cost is not a constraint at any of these figures; the note's
  table simply should not be read as conservative in every direction.
- **The endpoint is not under `/api/v1`.** This note cited `POST /api/alpha/decisions`
  correctly, but the OpenAPI spec's own `servers` (`https://openrouter.ai/api/v1`) composes to a
  path that **404s**, as do `/api/v1/decisions` and `/api/v1/api/alpha/decisions`. Only
  `https://openrouter.ai/api/alpha/decisions` answers 200. `agent/router.py` pins that URL and a
  test fails if it regresses to an `/api/v1` spelling.
- **A byte-identical request returned a byte-identical answer, twice** — the measurement AC 5
  rests on. Jev's request/response contract is now verified by observation, not only by the spec.
  Observed answers also vary in how many criteria they name: one call returned only the chosen id
  and the sentinel, another returned all eleven at `0` except the chosen one. Both are readable
  under the same rule (only ids the Router was offered are passed on).

## Sources

`https://openrouter.ai/api/v1/models/typesafe/jev-1.14/endpoints` · `https://openrouter.ai/typesafe/jev-1.14` · `https://openrouter.ai/api/v1/models?output_modalities=decisions` · `https://openrouter.ai/openapi.json` · `https://openrouter.ai/pricing` · `https://openrouter.ai/docs/api_reference/limits.md` · `https://openrouter.ai/docs/guides/community/jev` · `https://openrouter.ai/docs/cookbook/evaluate-and-optimize/classify-reddit-comments-with-jev` · `https://openrouter.ai/docs/cookbook/evaluate-and-optimize/jev-classification` · `https://docs.typesafe.ai/models` · `https://typesafe.ai/blog/introducing-system-one-models-and-jev` · `https://jina.ai/classifier/` · `https://docs.cohere.com/docs/deprecations` · `https://docs.voyageai.com/docs/pricing` · `https://www.notdiamond.ai/pricing`

All read 2026-10-21.
