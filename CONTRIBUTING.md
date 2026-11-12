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

## 4. Where things live

| Folder | What goes there |
|---|---|
| `src/beauty_expansion/extract/` | one file per source (API, scraper, Excel) |
| `src/beauty_expansion/transform/` | cleaning, geo helpers |
| `src/beauty_expansion/load/` + `sql/schema.sql` | DuckDB star schema |
| `src/beauty_expansion/analysis/` | KPIs, scoring, business case, decision, AI summary |
| `src/beauty_expansion/pipeline.py` | runs everything in order |
| `app/streamlit_app.py` | dashboard |
| `lessons/` + `LEARNING_PATH.md` | Python learning modules |

Current team tasks are the GitHub issues: https://github.com/dcineus-eugenia/beauty-expansion-analytics/issues
