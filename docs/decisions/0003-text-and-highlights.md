Title: Text and Highlights — Modeling Strategy

Status: Accepted (phase 1)

Context
- `rmfiles/deps/scene_items.py` includes `Text` and `GlyphRange` types.
- We want `RemarkableNotebook.text()` and `RemarkableNotebook.highlight()` in the public API.

Decision (phase 1)
- Provide API method `RemarkableNotebook.text(...)` to enqueue text as root text blocks (`RootTextBlock`) with position and width.
- Defer highlight (`GlyphRange`) to a follow-up phase; API shape may be `highlight(text, rectangles, color=...)`.
- Keep the compiler pure; continue to reuse our existing block assembly for layers and lines and then append root text blocks.

Consequences
- Unblocks the API shape now while allowing incremental implementation without breaking changes.
