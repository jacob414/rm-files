rm-files Documentation
======================

Welcome to rm-files' documentation.

.. toctree::
   :maxdepth: 2
   :caption: Contents

   decisions/index

Overview
--------

rm-files provides a small API for constructing ReMarkable
``.rm`` (lines v6) files using the upstream ``rmscene`` library.

Quickstart
----------

.. code-block:: bash

   make venv
   source .venv/bin/activate
   python gen.py

This generates ``triangle.rm`` using the high-level notebook API.
