# The browser is a separate process, reached over CDP, so that it can move hosts

Chromium runs as its own service with a persistent profile per Account, and the Platform agents connect to it rather than launching it.

The user has one machine today and wants the browser to be able to run elsewhere later. That is the entire reason for the split. `launch_persistent_context` is a launch API and cannot cross a host boundary, so a design in which each agent starts its own browser would have to be rewritten to move. Paying one indirection now buys a migration that is a configuration change.

**Consequences.**

- The cookie jar is written when a Session closes. With a long-lived remote browser that moment may never arrive, so saving has to be driven by the agent rather than by a shutdown hook. Without this, the agent regresses to the silent-logout failure that the profile-plus-jar design exists to solve.
- Each Account needs its own Chromium process, because the profile carries the login. One browser shared between Accounts would share a Session.
- Three browsers resident at once do not fit on the current machine, so a browser is started for a Comment pass and stopped afterwards.
- Running the browser in a container makes it more detectable, not less: no GPU, headless by default, and a network stack that reads as infrastructure. The dry run and the Daily cap are what absorb that.
