# The Router is a decisions API, and Jev is its current occupant

The Router reaches a decisions API that returns a typed answer over options we supply. Jev is the occupant v1 uses, and the model id is configuration rather than a constant.

The choice is settled by measurement, not taste. Jev bills **$0.042 per 1M input tokens with output free** — roughly **$0.021 per 1,000 Comments** — so a 3,000-Comment day costs about **$1.90 a month** and a 10,000-Comment day about **$6.33**. The alternative that motivated a switch, `razorback16/openjev`, cannot run on the deployment machine at all: its documented backends are vLLM on NVIDIA hardware and MLX on Apple silicon, and its default model is 26B against a machine with 768 MiB of free RAM. Hosting it would cost one to three orders of magnitude more than the calls it replaces, so the cheaper-looking option is the more expensive one.

**The constraint on any replacement is confidence, not price.** Twenty-six other decision models sit behind the same wire API, and several are cheaper, but a Router that returns only a chosen label cannot Escalate — and ADR 0002's design rests on a calibrated confidence deciding when a Comment is left for the user instead. OpenRouter's own `auto` routing returns a chosen model and no confidence, and adopting it would silently convert every low-confidence Comment into a confident-sounding Reply. A replacement must therefore return probabilities we can threshold against, and its thresholds must be re-tuned, because probabilities differ between models on the same question.

**Consequences.**

- Vendor risk is not concentration in TypeSafe. It is the decisions API as a category, and that category has 27 members today.
- The free tiers are not a fallback: `:free` decision models cap at 50–1,000 requests a day, below this system's own ceiling, so a free model cannot carry the workload at any price.
- A model swap is a configuration change plus a threshold recalibration, and the recalibration is the part that goes wrong. A swap is not complete until Verdicts have been re-checked against the new Router.
- `in_flight_budget_exhausted` — HTTP 402, returned while the balance is positive when OpenRouter's estimate of in-flight spend is exceeded — is a real failure mode once concurrency exists, and it has nothing to do with running out of credit.
- No prompt caching is available, so the cache that keeps a repeated Comment from reaching the Router at all is ours to build rather than something the provider supplies.
- Cost is not a reason to prefer a weaker Router. At this volume the Router is under a dollar a month, so every remaining argument about it is about correctness.
