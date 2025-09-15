from datetime import datetime

project = "rm-files"
author = "Jacob Oscarson"
copyright = f"{datetime.now():%Y}, {author}"

extensions = [
    "myst_parser",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
linkcheck_ignore = [
    # Ignore external links in ADRs that may be unavailable in restricted CI
    r"https://github.com/ddvk/rmapi",
]

# MyST configuration
myst_enable_extensions = [
    "colon_fence",
]
