0008: Shared Temp Output Directory
==================================

Context
-------
Collaborating on rendering tweaks often requires exchanging generated
assets (e.g. SVGs, screenshots). Previously, ad-hoc files in the repo
caused noisy diffs or accidental commits.

Decision
--------
Create a ``tmp/`` directory (git-ignored) as the canonical place to
drop temporary outputs for review. This keeps the workspace tidy while
still letting teammates inspect files locally.

Consequences
------------
- No risk of polluting the repo history with scratch artifacts.
- Reviewers know to look in ``tmp/`` for shared visual outputs.
- CI and other tooling remain unaffected because the directory is
  ignored by git and excluded from builds.
