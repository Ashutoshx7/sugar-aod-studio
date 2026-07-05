# Architecture

```
aodstudio/
├── main.py            entry point: dependency check, theme setup, Gtk.main
├── __main__.py        `python3 -m aodstudio`
├── core/              foundations shared by everything
│   ├── spec.py        ActivitySpec — the validated generation request
│   ├── licenses.py    license texts and metadata
│   └── projects.py    list/reopen previously generated projects
├── llm/               talking to models
│   ├── providers.py   provider clients (OpenRouter, Gemini, OpenAI, …)
│   ├── credentials.py local API-key store
│   └── enhance.py     expand short prompts into detailed briefs
├── generation/        idea → activity.py
│   ├── pipeline.py    orchestrates enhance → RAG → plan → code → package
│   ├── prompts.py     planner prompts
│   ├── rag.py         local retrieval over installed Sugar activities
│   ├── codegen.py     code-generation prompts and response extraction
│   ├── generator.py   plan normalization, project assembly, .xo packaging
│   ├── validator.py   safety + quality validation of generated code
│   ├── refine.py      SEARCH/REPLACE refinement patches
│   └── templates.py   local template renderer (offline fallback)
├── service/           background execution and persistence
│   ├── service.py     public facade (get_service): submit, watch, cancel
│   ├── queue.py       worker queue
│   ├── jobs.py        persistent job records
│   └── sessions.py    prompt/refinement conversations and revisions
├── packaging/
│   └── flatpak.py     buildable Flatpak sources / best-effort bundles
├── preview/
│   └── runner.py      run generated activities in-process, shell-free
└── ui/
    ├── window.py      top-level window
    ├── ring.py        Sugar-style home ring layout (ported from jarabe)
    ├── theme.py       studio CSS
    └── panel.py       the whole studio UI (home, create, studio views)
```

**Layering** (imports point downward only, module-level):
`ui` → `service` → `generation` → `llm` → `core`, with `packaging` and
`preview` as leaves used by `ui`/`generation`. `llm/providers` reaches
into `generation/codegen+prompts` for response extraction — a
deliberate exception with no module-level cycle.

A test (`tests/test_studio.py`) enforces that no `jarabe` (Sugar
shell) module is ever imported: the studio depends on the Sugar
*toolkit* only.

## Correspondence with the Sugar shell fork

The same experience runs embedded in the
[Sugar fork](https://github.com/Ashutoshx7/sugar) (`aod-activity-on-demand`
branch), which keeps flat module names. When porting changes between
the two:

| Sugar fork (`src/jarabe/…`) | Studio |
|---|---|
| `model/aodspec.py` | `core/spec.py` |
| `model/aodlicenses.py` | `core/licenses.py` |
| `model/aodprojects.py` | `core/projects.py` |
| `model/aodllm.py` | `llm/providers.py` |
| `model/aodcredentials.py` | `llm/credentials.py` |
| `model/aodenhance.py` | `llm/enhance.py` |
| `model/aodpipeline.py` | `generation/pipeline.py` |
| `model/aodgenerator.py` | `generation/generator.py` |
| `model/aodcodegen.py` | `generation/codegen.py` |
| `model/aodprompts.py` | `generation/prompts.py` |
| `model/aodrag.py` | `generation/rag.py` |
| `model/aodrefine.py` | `generation/refine.py` |
| `model/aodvalidator.py` | `generation/validator.py` |
| `model/aodtemplates.py` | `generation/templates.py` |
| `model/aodservice.py` | `service/service.py` |
| `model/aodjobs.py` | `service/jobs.py` |
| `model/aodqueue.py` | `service/queue.py` |
| `model/aodsessions.py` | `service/sessions.py` |
| `model/aodflatpak.py` | `packaging/flatpak.py` |
| `model/aodpreview.py` | `preview/runner.py` |
| `desktop/homebox.py` (panel part) | `ui/panel.py` (+ `ring.py`, `theme.py`) |
