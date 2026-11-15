# Comex dashboards and slide deck

Self-contained HTML files: open them in a browser, no install, no internet needed.

| File | What it is |
|---|---|
| `dashboard_comex.html` | Dashboard with tabs: Synthèse, Marché, Prix et marge, Parfum, Rentabilité, Concurrence, Synthèse IA, Instructions |
| `dashboard_comex_v2.html` | One-page dashboard and an Instructions page |
| `slides_comex.html` | 12-slide Comex deck. Arrow keys to navigate, Cmd + P to export a PDF |
| `Sephora_Europe_2027_Comex.pptx` | Same deck as PowerPoint (one image per slide, no speaker notes). Edit the HTML, rebuild, then export |

Filters (country, sales scenario, FR/EN) update every tab.

## Rebuild

```bash
python -m beauty_expansion.pipeline      # refresh data/processed
python app/comex/build_dashboard.py      # inject the outputs into the templates
python app/comex/export_pptx.py          # optional: refresh the PPTX (needs Chrome, poppler, python-pptx)
```

`build_dashboard.py` reads `data/processed/*.csv`, `decision.json` and `ai_summary.json`, then writes the three
HTML files from `template.html`, `template_v2.html` and `template_slides.html`. It prints a reminder when the deck
changed and the PPTX needs a new export.

The figures quoted in the slide text (weights, scores, growth, plan size, plan B, rent lever…) come from the data.
The build also checks every qualitative claim written in the templates (for example "biggest market", "first under
every weighting", "same price as France") and the configuration the Instructions pages describe. If one no longer
holds, it stops with the list of sentences to rewrite.

The rent condition on the recommendation slide is the share of prime rent at which the model's store payback meets
the 4-year target, found by bisection on `business_case.unit_economics` (rounded down to 5 points).

The "Test de résistance parfum" slide re-runs Natalia's check (PR #10, `fragrance_breakeven.py`) at build time:
fragrance-focus scores and the Dutch fragrance level at which Ireland overtakes.

## Limits

- The AI summary shows the rule-based fallback until the pipeline runs with `ANTHROPIC_API_KEY`.
- The generated HTML embeds pipeline outputs; they are committed so the team can open them without running anything.
