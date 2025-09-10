0002: GitHub Pages Docs Deployment
==================================

Context
-------
- We want built HTML docs published automatically and reliably.
- Initial deploy job failed with a 404 when Pages wasn’t enabled.
- After enabling Pages, we removed the conditional guard so that deploy runs on every push to ``main``.

Decision
--------
- Use the official ``upload-pages-artifact`` + ``deploy-pages`` actions in ``.github/workflows/docs.yml``.
- Build Sphinx with ``sphinx-build -b html docs docs/_build/html`` and upload that folder.
- Deploy unconditionally on push to ``main`` now that Pages is enabled in repo settings.

Consequences
------------
- Docs publish automatically, making docs changes visible quickly.
- If Pages were to be disabled again, deploy would fail; in that scenario, reintroduce a guard or re-enable Pages.
- Docs remain independent of the main CI build; issues in docs do not block test/build unless configured.

