## What this changes

<!-- One or two sentences. Link the issue: "Closes #2" -->

## Data checklist

- [ ] `python -m beauty_expansion.pipeline` runs to the end and prints "data contracts: all files pass"
- [ ] `python -m pytest -q` passes
- [ ] New or changed output columns are in `src/beauty_expansion/contracts.py`, and `docs/DATA_CONTRACTS.md` is regenerated
- [ ] Units follow the naming rule (`_eur`, `_meur`, `_pct` 0–100, `_rate`/`_share` 0–1, `country_code` ISO 2 letters)
- [ ] Every new manual figure has a source URL (`data/manual/`), and simulated data is labelled as simulated
- [ ] New assumptions live in `config.py` with a comment, not hard-coded
- [ ] I opened the dashboard and my change looks right

## Effect on results

<!-- Did the ranking, NPV, payback or decision change? Paste the before/after numbers. "None" is a fine answer. -->
