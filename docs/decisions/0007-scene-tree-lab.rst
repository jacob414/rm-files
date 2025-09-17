==========================================
ADR 0007: Scene Tree Lab Explorer
==========================================

Status
======

Accepted - 2025-02-14


Context
=======

We frequently rely on the optional ``rmscene`` dependency to decode
ReMarkable ``.rm`` files. When debugging new primitives or studying the
device format we need a fast way to inspect the decoded structures in a
human-friendly way. The previous workflow involved sprinkling ``print``
statements or dropping into a debugger, which made it hard to share
findings and slowed iteration.


Decision
========

Add a lightweight lab script (``lab_rm_reader.py``) that loads a sample
``.rm`` file into ``rmscene``'s ``SceneTree`` and walks the structure.
The walker summarises key objects (groups, CRDT sequence items, lines,
points, LWW values) with concise, well-indented output so developers can
spot hierarchy issues at a glance.


Consequences
============

* The lab script lives outside the distributed package and has no stable
  API guarantees. It is intentionally loose so experiments remain easy.
* The documentation now points to the script so new contributors know
  where to start when exploring decoded scenes.
* Future tooling (for example, JSON emitters or visualisers) can reuse
  the same traversal strategy.
