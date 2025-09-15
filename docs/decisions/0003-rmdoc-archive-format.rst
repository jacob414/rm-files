.. ADR Template (copy as a starting point)

The .rmdoc notebook package format
==================================

Context
-------
So far I have been using the `rmapi` (https://github.com/ddvk/rmapi) to transfer files to and from my ReMarkable.

I use `rmapi` version v0.0.29.

When downloading a notebook, a `.rmdoc` file arrives at my computer. I
have found that it's a ZIP-archive with several files in it.

Illustrative CLI session
++++++++++++++++++++++++

This is a transcript from my CLI that provides clues about the `.rmdoc` format:

.. code-block:: shell

    tmp $ unzip Sample.rmdoc
    Archive:  Sample.rmdoc
     extracting: 62477a1b-de36-4b37-a9cb-d57e595b51e1.content
     extracting: 62477a1b-de36-4b37-a9cb-d57e595b51e1.metadata
     extracting: 62477a1b-de36-4b37-a9cb-d57e595b51e1/5a1aa9a2-b72a-4a0e-9bab-44b179bdd1fa.rm
    (.venv) zipfly:~/src/oss/rm-files/sample-files/tmp main
    tmp $ tree
    .
    ├── 62477a1b-de36-4b37-a9cb-d57e595b51e1
    │   └── 5a1aa9a2-b72a-4a0e-9bab-44b179bdd1fa.rm
    ├── 62477a1b-de36-4b37-a9cb-d57e595b51e1.content
    ├── 62477a1b-de36-4b37-a9cb-d57e595b51e1.metadata
    └── Sample.rmdoc

    2 directories, 4 files
    (.venv) zipfly:~/src/oss/rm-files/sample-files/tmp main
    tmp $ file 62477a1b-de36-4b37-a9cb-d57e595b51e1/5a1aa9a2-b72a-4a0e-9bab-44b179bdd1fa.rm
    62477a1b-de36-4b37-a9cb-d57e595b51e1/5a1aa9a2-b72a-4a0e-9bab-44b179bdd1fa.rm: reMarkable tablet page (v6), 1404 x 1872, 25 layer(s)

    tmp $ cat 62477a1b-de36-4b37-a9cb-d57e595b51e1.content

.. code-block:: json

    {
    "cPages": {
        "lastOpened": {
            "timestamp": "1:1",
            "value": "5a1aa9a2-b72a-4a0e-9bab-44b179bdd1fa"
        },
        "original": {
            "timestamp": "0:0",
            "value": -1
        },
        "pages": [
            {
                "id": "5a1aa9a2-b72a-4a0e-9bab-44b179bdd1fa",
                "idx": {
                    "timestamp": "1:2",
                    "value": "ba"
                },
                "template": {
                    "timestamp": "1:1",
                    "value": "seyes"
                }
            }
        ],
        "uuids": [
            {
                "first": "20b88d6c-19b8-5d27-a0b1-0b067ec0a5e9",
                "second": 1
            }
        ]
    },
    "coverPageNumber": -1,
    "customZoomCenterX": 0,
    "customZoomCenterY": 936,
    "customZoomOrientation": "portrait",
    "customZoomPageHeight": 1872,
    "customZoomPageWidth": 1404,
    "customZoomScale": 1,
    "documentMetadata": {
    },
    "extraMetadata": {
        "LastActiveTool": "primary",
        "LastBallpointColor": "Black",
        "LastBallpointSize": "2",
        "LastBallpointv2Color": "Black",
        "LastBallpointv2Size": "2",
        "LastCalligraphyColor": "Black",
        "LastCalligraphySize": "3",
        "LastEraseSectionColor": "Black",
        "LastEraseSectionSize": "2",
        "LastEraserColor": "Black",
        "LastEraserSize": "2",
        "LastEraserTool": "EraseSection",
        "LastFinelinerv2Color": "Black",
        "LastFinelinerv2Size": "2",
        "LastHighlighterv2Color": "HighlighterGray",
        "LastHighlighterv2Size": "1",
        "LastMarkerv2Color": "Gray",
        "LastMarkerv2Size": "3",
        "LastPaintbrushv2Color": "Black",
        "LastPaintbrushv2Size": "1",
        "LastPen": "Finelinerv2",
        "LastPencilColor": "Black",
        "LastPencilSize": "2",
        "LastPencilv2Color": "Black",
        "LastPencilv2Size": "3",
        "LastSelectionToolColor": "Black",
        "LastSelectionToolSize": "2",
        "LastShadingMarkerColor": "ArgbCode",
        "LastShadingMarkerColorCode": "1075912220",
        "LastShadingMarkerSize": "2",
        "LastSharpPencilv2Color": "Black",
        "LastSharpPencilv2Size": "2",
        "SecondaryCalligraphyColor": "Gray",
        "SecondaryCalligraphySize": "1",
        "SecondaryFinelinerv2Color": "Black",
        "SecondaryFinelinerv2Size": "2",
        "SecondaryHighlighterv2Color": "HighlighterYellow",
        "SecondaryHighlighterv2Size": "1",
        "SecondaryMarkerv2Color": "Black",
        "SecondaryMarkerv2Size": "3",
        "SecondaryPaintbrushv2Color": "Gray",
        "SecondaryPaintbrushv2Size": "1",
        "SecondaryPen": "Highlighterv2",
        "SecondaryPencilv2Color": "Black",
        "SecondaryPencilv2Size": "3",
        "SecondaryShadingMarkerColor": "ArgbCode",
        "SecondaryShadingMarkerColorCode": "1075912220",
        "SecondaryShadingMarkerSize": "3",
        "SecondarySharpPencilv2Color": "Black",
        "SecondarySharpPencilv2Size": "1"
    },
    "fileType": "notebook",
    "fontName": "",
    "formatVersion": 2,
    "lineHeight": -1,
    "margins": 125,
    "orientation": "portrait",
    "pageCount": 1,
    "pageTags": [
    ],
    "sizeInBytes": "20494",
    "tags": [
    ],
    "textAlignment": "justify",
    "textScale": 1,
    "zoomMode": "bestFit"
    }

Decision
--------

This information given in the CLI transcript of the last section should
provide what's needed to support the `.rmdoc` format.

Consequences
------------
Positive/negative outcomes, follow-up tasks, trade-offs.

Positive outcomes
+++++++++++++++++

  - The format is enclosed in a Zip file.
  - Shelling out to the OS `file` tool will provide some initial
    information to reverse-engineer the `.rm` format.
  - Transfering a Notebook to the ReMarkable should be easy using the user installed program `rmapi`.

Trade-offs
++++++++++

Shelling out to OS tools and a custom program will make this program difficult to port to non-posix OS'es.
