Title: Text and Highlights — Modeling Strategy

Status: Proposed (stub)

Context
- `rmfiles/deps/scene_items.py` includes `Text` and `GlyphRange` types.
- We want `RemarkableNotebook.text()` and `RemarkableNotebook.highlight()` in the public API.

Decision (initial)
- Provide API methods to enqueue text and highlight events with positions, width, style, and color.
- Phase 1: Implement stroke compilation first; store text/highlight events without compiling.
- Phase 2: Extend the compiler to emit proper `Text` and `GlyphRange` blocks, including CRDT items and styles.

Consequences
- Unblocks the API shape now while allowing incremental implementation without breaking changes.

