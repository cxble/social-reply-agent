# Facebook runs in draft mode, and automatic posting is a separate unbuilt path

Facebook is in scope for finding Comments and preparing Replies, but the agent does not post there.

Facebook writes require signed `fb_dtsg` and `jazoest` parameters, and the page runs "Ghost Owl" anti-tampering. That makes it the most defended of the three Platforms and the worst place to spend the user's account on an unproven write. Draft mode keeps the Platform in scope and exercises the Router and the Reply table against real Comments without a write path that has never run.

**Consequences.**

- **Draft mode is not a dry run of the write path, and promoting it is not a configuration change.** It exercises reads only. Everything on the write side, meaning the post action, confirming the Reply landed, and recording it in the Replied set, is unbuilt and unproven for Facebook. Turning it on is new work, so nothing downstream should be planned as if the flag already existed.
- Because the write path cannot be exercised, the read path has to carry the whole burden of proving the Adapter, which is why live read-only tests matter here more than on the other Platforms.
