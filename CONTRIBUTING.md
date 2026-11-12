# Contributing

How the team works on this repo. Read it once before your first commit.

## 1. One-time setup (15 min)

You need: Git, Python 3.12, VS Code, a GitHub account that has accepted the repo invitation.

```bash
# macOS: brew install python@3.12 git      Windows: install Python 3.12 from python.org and Git from git-scm.com
git clone https://github.com/dcineus-eugenia/beauty-expansion-analytics.git
cd beauty-expansion-analytics
python3.12 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
python -m beauty_expansion.pipeline  # first run downloads data, ~5 min
python -m pytest -q                  # all tests must pass
streamlit run app/streamlit_app.py   # dashboard on http://localhost:8501
```

Optional, for the real Claude summary: copy `.env.example` to `.env` and paste an Anthropic API key. **Never commit `.env`.**

Open the folder in VS Code and pick the `.venv` interpreter when asked.

## 2. Daily workflow

Never push to `main` directly. One task = one branch = one pull request.

```bash
git checkout main && git pull                     # start from the latest version
git checkout -b fragrance/market-data             # branch name: <topic>/<short-task>
# ... work, run the pipeline, check the dashboard ...
git add <files you changed>
git commit -m "Add Comext perfume imports for candidates"
git push -u origin fragrance/market-data
gh pr create --fill                               # or open the link GitHub prints
```

Then ask one teammate to review the pull request. Merge once it is approved and the pipeline runs.

If `main` moved while you worked: `git pull origin main` on your branch, fix conflicts, commit, push.

## 3. Rules

- **Small commits, clear messages**, written in English, in the imperative: "Add perfume price per ml", not "update".
- **Every number has a source.** Manual figures go in `data/manual/` with the source URL in `data/manual/README.md`.
- **Don't commit generated data** (`data/raw`, `data/interim`, `data/processed`, `*.duckdb`): the pipeline rebuilds them. `.gitignore` already handles this.
- **Before opening a pull request**, run `python -m beauty_expansion.pipeline` and open the dashboard: both must work.
- **Simulated data is labelled as simulated**, everywhere it appears.
- Put new settings (weights, assumptions) in `src/beauty_expansion/config.py`, not hard-coded in a function.

## 4. Keeping the data coherent

Five people write to the same pipeline, so the data rules are enforced by code, not by memory.

- **One definition per file.** Every output file in `data/processed/` has a contract in
  `src/beauty_expansion/contracts.py`: grain (what one row is), key, column types, units and allowed ranges.
  Read [`docs/DATA_CONTRACTS.md`](docs/DATA_CONTRACTS.md) before you produce or read a file.
- **The pipeline checks itself.** Write outputs through the contracts:
  ```python
  contracts.validate("fragrance_market.csv", df).to_csv(config.PROCESSED / "fragrance_market.csv", index=False)
  ```
  A wrong column, unit, country code or duplicate stops the pipeline with a clear message.
- **Units are in the column names:** `_eur` euros, `_meur` millions of euros, `_pct` percent 0–100,
  `_rate`/`_share`/`_margin`/`_cagr` fractions 0–1, `_km`, `_per_100k`. Countries are always `country_code`,
  ISO 2 letters (`FR`, `NL`, `AT`, `IE`, `FI`, `NO`), taken from `config.COUNTRIES`, never typed by hand.
- **Changing a contract** (new column, new file) happens in the same pull request as the code, then regenerate the docs:
  `python -m beauty_expansion.contracts --markdown > docs/DATA_CONTRACTS.md`. Changes to `config.py`,
  `contracts.py`, `sql/schema.sql` and `data/manual/` need the data owner's review (`.github/CODEOWNERS`).
- **Shared inputs, never copies.** Read other teammates' outputs from `data/processed/` (or with
  `contracts.read(file)`); never copy numbers into your code or slides by hand. Slides quote the dashboard.
- **Before every pull request:** `python -m beauty_expansion.pipeline` then `python -m pytest -q`.
  GitHub runs the tests again on the pull request (Actions tab); a red cross means don't merge.
- **If your change moves a result** (ranking, NPV, payback, decision), write the before/after in the pull request
  and in the README correction log. Results changing is fine; results changing silently is not.

## 5. Where things live

| Folder | What goes there |
|---|---|
| `src/beauty_expansion/extract/` | one file per source (API, scraper, Excel) |
| `src/beauty_expansion/transform/` | cleaning, geo helpers |
| `src/beauty_expansion/load/` + `sql/schema.sql` | DuckDB star schema |
| `src/beauty_expansion/analysis/` | KPIs, scoring, business case, decision, AI summary |
| `src/beauty_expansion/contracts.py` | data contracts of every output file |
| `src/beauty_expansion/pipeline.py` | runs everything in order |
| `tests/` | pytest suite, run on every pull request |
| `app/streamlit_app.py` | dashboard |
| `lessons/` + `LEARNING_PATH.md` | Python learning modules |

Current team tasks are the GitHub issues: https://github.com/dcineus-eugenia/beauty-expansion-analytics/issues
