# Comex dashboards and slide deck

Self-contained HTML files: open them in a browser, no install, no internet needed.

| File | What it is |
|---|---|
| `dashboard_comex.html` | Dashboard with tabs: Synthèse, Marché, Prix et marge, Parfum, Rentabilité, Concurrence, Synthèse IA, Instructions |
| `dashboard_comex_v2.html` | One-page dashboard and an Instructions page |
| `slides_comex.html` | 12-slide Comex deck. Arrow keys to navigate, Cmd + P to export a PDF |
| `Sephora_Europe_2027_Comex.pptx` | Same deck as PowerPoint, with the speaker script in the notes. Slides are images, so edit the HTML and rebuild |

Filters (country, sales scenario, FR/EN) update every tab.

## Rebuild

```bash
python -m beauty_expansion.pipeline      # refresh data/processed
python app/comex/build_dashboard.py      # inject the outputs into the templates
```

`build_dashboard.py` reads `data/processed/*.csv`, `decision.json` and `ai_summary.json`, then writes the three
HTML files from `template.html`, `template_v2.html` and `template_slides.html`. The PPTX is exported by hand from
the HTML deck (print to PDF, one image per slide).

The "Test de résistance parfum" slide re-runs Natalia's check (PR #10, `fragrance_breakeven.py`) at build time:
fragrance-focus scores and the Dutch fragrance level at which Ireland overtakes.

## Limits

- The AI summary shows the rule-based fallback until the pipeline runs with `ANTHROPIC_API_KEY`.
- The generated HTML embeds pipeline outputs; they are committed so the team can open them without running anything.
