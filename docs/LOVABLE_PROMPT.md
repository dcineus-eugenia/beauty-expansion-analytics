# Lovable prompt: interactive Comex presentation

Paste everything below the line into a new Lovable project. All figures come from the pipeline outputs in
`data/processed/` (run of 13 November 2026). If you re-run the pipeline and a figure changes, update it here first.

**Credits:** a project and its credits belong to one Lovable workspace, so one person must build the whole
project. On the free plan (5 credits a day), the build may stop before the end. Each day, send the message
"Continue and finish the remaining items of the brief, then run the tests and the TypeScript check."
until every item is done.

---

Build an interactive, dynamic web PRESENTATION (slide deck + live dashboards) for a student case study: "Sephora · European expansion 2027–2029 — which new country, Go/No-Go?". It will be presented orally to a jury (Comex role-play) at Eugenia School. Frontend only, no backend/auth/database needed: all data is static and embedded below in a typed data file (src/data/study.ts). Use every figure exactly as given; do not invent, recompute or round differently.

## Language
French by default, with an FR / EN toggle in the top bar. All UI text in both languages. French number format in FR (76 M€, 2,5 Md€, 9,7 %), English format in EN (€76M, €2.5bn, 9.7%).

## Visual style — inspired by premium beauty retail (black & white editorial)
- Strict black (#000000 / #111111) and white (#FFFFFF), with light greys (#F5F5F5, #E5E5E5, #6B6B6B). ONE accent for highlights/the winning country: a deep rose/red #C8102E used sparingly.
- Signature motif: thin vertical black-and-white stripes (repeating-linear-gradient) used as decorative bands on the cover, section dividers and the final slide.
- Typography: a bold geometric uppercase sans for headings with wide letter-spacing ("Montserrat" 700/800), clean sans for body ("Inter"). Big numbers in bold.
- Generous whitespace, sharp corners (no rounded cards), thin 1px black borders, minimal shadows. Luxury-editorial feel.
- Do NOT use the real Sephora logo or flame icon: write the word SEPHORA as a plain bold uppercase wordmark in text. Small footer note on every slide: "Student case study — Eugenia School. Not affiliated with Sephora or LVMH. Internal store data simulated."

## Navigation
Full-screen 16:9 slides (designed at 1920×1080 and scaled to the window) with keyboard arrows (←/→, space), progress bar at top, slide counter, a thumbnail/outline menu (key "G"), speaker notes (key "N") and a "Present" fullscreen button. Smooth transitions (framer-motion: fade/slide, numbers count up, bars grow on enter). Interactive charts with Recharts: hover tooltips, toggles, filters. Never use a dual-axis chart. Also a route /dashboard showing all charts on one scrollable page with tabs (one tab per topic: Context, Ranking, KPIs, Fragrance, Business case).

## Slides (11) and data

1. COVER — eyebrow "COMEX · STRATÉGIE 2027–2029". Title: "Où Sephora doit-elle ouvrir en Europe ?" / "Where should Sephora open in Europe?". Subtitle: "Étude data de 5 pays sans magasin Sephora, et un Go/No-Go" / "A data study of 5 countries without a Sephora store, and a Go/No-Go". Footer "Damien, Jude, Kevin, Natalia, Stephen · Eugenia School · Projet Data Analytics · Novembre 2026" (EN: "… · Data Analytics project · November 2026"). Stripe band.

2. CONTEXT (kicker 01) — "Sephora domine en France, mais la croissance du groupe s’essouffle". 4 animated KPI tiles: ≈330 stores in France; €2.5bn French revenue 2024 (≈6.9% of French personal-care spend); 9.7% LVMH Selective Retailing operating margin 2025 (4.5% in 2021); +0.5% Selective Retailing revenue growth 2025 (vs +26% in 2022, accent tile). Chart LVMH Selective Retailing 2021–2025: revenue M€ [11754, 14852, 17885, 18262, 18348] as bars and operating margin % [4.5, 5.3, 7.8, 7.6, 9.7] as a SEPARATE small line chart below. Question box: "Ouvrir des magasins Sephora dans un nouveau pays européen est-il réalisable et rentable ?"

3. SCOPE (kicker 02) — "S’étendre, c’est viser un pays encore sans magasin Sephora". An interactive Europe map (d3-geo + topojson-client with world-atlas topojson from a CDN, framed on Europe): France = benchmark (black), already-present countries in grey (Germany since 2017, Belgium June 2026, Luxembourg, Switzerland, Sweden, Denmark, Spain, Italy, Portugal), the 5 candidates highlighted: Netherlands, Austria, Ireland, Finland, Norway. Hover shows status. Note: "La seule boutique Sephora de l’île d’Irlande est à Belfast (Royaume-Uni)."

4. DATA (kicker 03) — "Sept sources, un schéma en étoile, une commande" / "Seven sources, one star schema, one command". Animated flow diagram: Eurostat API (8 series, 6 countries) · OpenStreetMap API (6,420 stores in continental Europe) · price scraper (17 products × 4 countries + 1,381 perfumes) · Eurostat Comext customs + Statistics Norway (fragrance HS 3303, 2019–2025) · LVMH Excel + releases 2021–2025 · cited manual figures (VAT, tax, rents, hubs) · simulated internal DB (330 stores, 2,000 SKUs) → DuckDB star schema (dimensions: country, date, indicator, brand, category, store; facts: macro indicators, competitor stores, prices, store P&L, catalogue, group financials, trade, KPIs, business case) → Streamlit dashboard + Claude AI summary. Small caption: "Data contracts and 78 automated tests check every file."

5. KPI METHOD (kicker 04) — "Dix KPI, cinq axes, des poids fixés avant les résultats". Interactive donut of axis weights: Market 30% (CAGR 12, spend per capita 10, market size 8), Price & margin 20% (gross margin after VAT/logistics/customs 20), Network 20% (catchment density 10, prime rent 10), Operations 15% (hub distance 8, trade friction 7), Assortment 15% (catalogue eligible 8, personal-care share 7). Clicking an axis shows its KPIs. Note: price level not scored separately to avoid double counting.

6. RANKING (kicker 05, key interactive slide) — "Les Pays-Bas arrivent premiers quelle que soit la pondération". Horizontal bar chart of total score /100: NL 79.7, AT 74.9, IE 74.4, FI 34.0, NO 26.7 (winner in accent, others grey). WEIGHT SIMULATOR: 5 sliders (one per axis, default 30/20/20/15/15, normalised to 100) that recompute total = Σ axis_score × weight live, using these axis scores (0–100), order Market, Price & margin, Network, Operations, Assortment:
   NL: 85.6, 100.0, 31.7, 100.0, 84.8
   AT: 75.1, 97.8, 33.5, 78.4, 95.8
   IE: 67.0, 73.1, 79.1, 64.0, 95.3
   FI: 0.0, 15.2, 81.8, 53.2, 43.9
   NO: 34.3, 0.0, 82.1, 0.0, 0.0
   Plus a radar chart comparing countries on the 5 axes (toggle countries). Preset buttons for the 6 tested scenarios; each sets the sliders to these axis weights (%) and shows its official result:
   - Base: 30 / 20 / 20 / 15 / 15 — NL 79.7, gap 4.8 vs AT
   - Market first: 69.6 / 4.3 / 8.7 / 8.7 / 8.7 — NL 83.2, gap 9.6 vs AT
   - Margin first: 12.5 / 41.7 / 29.2 / 8.3 / 8.3 — NL 83.8, gap 13.5 vs IE
   - Low risk / operations: 13.0 / 4.3 / 8.7 / 43.5 / 30.4 — NL 86.8, gap 7.0 vs AT
   - Equal weights: 30 / 10 / 20 / 20 / 20 — NL 79.4, gap 5.7 vs IE
   - Fragrance focus: 30 / 20 / 20 / 15 / 15, but the market axis is measured on fragrance, so show these totals instead of the slider result: NL 78.1, IE 71.2, AT 63.6, FI 41.7, NO 34.4 — gap 6.8 vs IE
   Under the selector, always show the official result of the selected preset with the caption "Résultat officiel du pipeline ; les curseurs donnent une approximation par axe." / "Official pipeline result; sliders give an axis-level approximation."

7. KPI EXPLORER (kicker 06) — "Un marché grand, riche et proche, mais déjà bien servi". Dropdown to pick a KPI, bar chart across countries with France as dashed reference line. Data (FR benchmark, NL, AT, IE, FI, NO):
   market size M€: 36547, 12780, 7059, 3838, 2854, 2845
   spend per capita €: 530, 710, 770, 700, 510, 520
   market CAGR 2019–24 %: 2.8, 5.8, 5.5, 6.4, 2.5, 5.8
   gross margin after tax %: 45.6, 45.6, 45.5, 43.7, 39.6, 38.5
   VAT %: 20, 21, 20, 23, 25.5, 25
   distance to nearest EU hub km: 361, 219, 730, 1071, 1326, 1480
   selective stores per 100k (top-5 cities catchment): 7.6, 4.6, 2.3, 1.1, 2.4, 1.7
   prime rent €/m²/yr: 12519, 2800, 5520, 3024, 1224, 2057
   catalogue eligible %: 100, 91.4, 95.6, 98.5, 79.5, 62.5
   Eurostat price level index (FR=100): 100, 116.7, 112.4, 135.3, 127.7, 144.9
   market leader (share of selective stores): FR Yves Rocher 42%, NL ICI PARIS XL 37%, AT Marionnaud 41%, IE Rituals 53%, FI KICKS 36%, NO KICKS 33%
   4 insight cards: Market + (NL €12.8bn, +5.8%/yr, €710/head vs €530 FR); Operations + (219 km from the Düren hub already serving Sephora Germany; 45.6% margin = France); Competition − (4.6 selective stores/100k; ICI Paris XL 37%, then Douglas); Hidden finding (black card): "Price levels are 12–45% above France, yet the same 17 products cost the same online (scraped index 100 in FR, NL, AT, IE). Margins must not assume local price levels."
   Small city table for NL catchment: Amsterdam 4.2, Rotterdam 3.6, The Hague 5.3, Utrecht 5.6, Eindhoven 5.7 stores/100k.

8. FRAGRANCE DEEP-DIVE (kicker 07) — "Le parfum confirme les Pays-Bas" / "Fragrance confirms the Netherlands".
   Left: bar chart "Marché du parfum par habitant, 2025 (€)" with a toggle per capita / market size / growth (2019–25 or 2022–25), NL in accent, others grey, France shown as "n/a, exportateur net / net exporter". Data (NL, AT, IE, FI, NO), apparent consumption = customs imports − exports of HS 3303 (customs values, not retail sales):
   per capita €: 25.3, 24.0, 28.8, 7.6, 18.0
   market M€: 457.1, 220.4, 156.5, 42.7, 100.5
   CAGR 2019–2025 %: 16.3, 7.4, 12.9, 16.4, 21.3
   CAGR 2022–2025 %: 10.1, 10.0, 10.2, 19.4, 23.9
   France: net exporter (exports €8.1bn vs imports €0.8bn in 2025), not measurable with trade data.
   Below it, grouped bars "L’effet Rotterdam / The Rotterdam effect", Netherlands 2019–2025, M€: raw imports [864.8, 854.4, 943.3, 1412.0, 1318.5, 1584.9, 1914.4]; apparent consumption [185.1, 257.5, 157.0, 342.1, 274.5, 335.5, 457.1].
   Right: 4 cards:
   - Marché / Market: "25 € par habitant aux Pays-Bas (Irlande 29 €). La croissance de 16 %/an est flattée par une base 2019 faible : 10 %/an depuis 2022, comme l’Autriche et l’Irlande." / "€25 per inhabitant in the Netherlands (Ireland €29). The 16%/yr growth is flattered by a weak 2019: 10%/yr since 2022, like Austria and Ireland."
   - Rotterdam: "1,9 Md€ importés en 2025, dont 76 % réexportés : le vrai marché est d’environ 457 M€." / "€1.9bn imported in 2025, 76% re-exported: the real market is about €457M."
   - Prix / Price: "Même prix en ligne dans les 4 pays (1,38 €/ml). La TVA plus élevée réduit le prix HT : −0,8 % aux Pays-Bas, −2,4 % en Irlande." / "Same online price in all 4 countries (€1.38/ml). Higher VAT lowers the ex-VAT price: −0.8% in the Netherlands, −2.4% in Ireland."
   - Concurrence / Competition: "2,1 parfumeries pour 100 000 hab. (France 2,5). ICI Paris XL en tête, les 3 premières chaînes détiennent 62 % des boutiques. 90 % de la gamme parfum vendable (catalogue simulé)." / "2.1 perfumeries per 100k (France 2.5). ICI Paris XL leads, the top 3 chains hold 62% of shops. 90% of the fragrance range sellable (simulated catalogue)."
   Dark banner: "Scénario « Focus parfum » : les Pays-Bas restent premiers (78,1), 6,8 points devant l’Irlande ; l’Autriche passe 3e." / "“Fragrance focus” scenario: the Netherlands stay first (78.1), 6.8 points ahead of Ireland; Austria drops to 3rd."
   Source line: "Eurostat Comext DS-045409 (HS 3303) · Statistics Norway 08801 · LOOKFANTASTIC · OpenStreetMap · simulated internal catalogue".
   Extra data for the dashboard Fragrance tab:
   - Prices (LOOKFANTASTIC online, 9 brands, 1,381 single bottles, scraped November 2026; no site in Finland or Norway): median €/ml incl. VAT 1.38 in FR, NL, AT, IE; like-for-like price index vs France = 100 in all four; ex-VAT index FR 100, NL 99.2, AT 100.0, IE 97.6; products FR 299, NL 396, AT 306 (Carolina Herrera and Jean Paul Gaultier not on the Austrian site), IE 380.
   - Competition (OpenStreetMap perfumeries + perfumery chains; shares are of shops, not of sales): FR 1738 shops, 2.52 per 100k, top-3 chains 51%, leader Nocibé · NL 382, 2.12, 62%, ICI PARIS XL · AT 156, 1.70, 57%, Marionnaud · IE 16, 0.29, 25%, The Perfume Shop (small sample, under-mapped) · FI 23, 0.41, 91%, KICKS (small sample) · NO 51, 0.91, 71%, KICKS (small sample).
   - Sellable French fragrance SKUs (SIMULATED catalogue, label it): FR 100%, NL 90.0% (exclusive local distributors 10.0%), AT 94.8% (exclusive 5.2%), IE 98.6% (exclusive 1.4%), FI 82.4% (labels not translated 10.4%, exclusive 7.3%), NO 54.6% (alcohol approval pending 26.6%, labels 10.4%, exclusive 8.5%).

9. AI BRICK (kicker 08) — "Claude rédige le commentaire. La règle prend la décision." Animated 3-step flow: Input (computed KPIs, ranking, sensitivity, business case, decision) → Claude Opus 5.5 (structured JSON: headline, summary, insights, risks, conditions, chart comments) → Output (executive summary + a comment under each dashboard chart). Guardrails: uses only given figures; country & recommendation fixed by the written rule; server-side fallback + rule-based summary if no API key. Mock "AI summary" card typing out: "GO CONDITIONNEL – Pays-Bas : meilleur score (79,7), VAN positive de 76 M€, délai de retour 4,9 ans au-dessus de l’objectif de 4 ans." / "CONDITIONAL GO – Netherlands: highest score (79.7), positive NPV €76M, payback 4.9 yrs above the 4-year target."

10. BUSINESS CASE (kicker 09) — "15 magasins aux Pays-Bas créent de la valeur, lentement". Country selector (NL default; AT, IE, FI, NO) and scenario toggle (pessimistic / base / optimistic). KPI tiles: NPV, payback, capex, revenue 2029. Charts: revenue bars + free-cash-flow bars (separate charts, negative FCF in grey, positive in accent), cumulative FCF line.
   Yearly plan (base), M€ — stores open 3, 8, 15, 15, 15 for 2027–2031 for all countries:
   NL revenue 13.3, 39.3, 78.6, 90.7, 95.1 · EBITDA 0.4, 2.3, 5.8, 9.6, 11.0 · FCF −6.6, −9.6, −11.3, 7.8, 8.9
   AT revenue 14.5, 42.7, 85.3, 98.4, 103.2 · EBITDA −1.0, −1.3, −0.7, 3.4, 4.9 · FCF −8.2, −13.3, −17.5, 3.3, 4.4
   IE revenue 13.8, 40.8, 81.5, 94.0, 98.6 · EBITDA 0.5, 2.6, 6.3, 10.0, 11.4 · FCF −6.6, −9.5, −10.9, 9.0, 10.1
   FI revenue 10.6, 31.2, 62.3, 71.9, 75.4 · EBITDA 0.2, 1.4, 3.5, 6.0, 6.9 · FCF −6.5, −9.8, −12.2, 5.3, 6.1
   NO revenue 9.7, 28.5, 57.1, 65.8, 69.0 · EBITDA −0.9, −1.8, −2.4, −0.3, 0.5 · FCF −7.4, −12.6, −17.6, −0.3, 0.5
   Scenario summary (NPV M€ / payback yrs) pessimistic | base | optimistic, and capex M€:
   NL: 19.9 / 9.8 | 76.1 / 4.94 | 103.7 / 4.01 — capex 34.9
   AT: −58.7 / never | 16.2 / never | 48.0 / 6.95 — capex 36.0
   IE: 27.8 / 8.7 | 89.8 / 4.53 | 120.6 / 3.71 — capex 35.8
   FI: 4.6 / never | 43.6 / 6.58 | 62.7 / 5.29 — capex 33.4
   NO: −68.1 / never | −26.3 / never | −5.4 / never — capex 32.6
   Assumptions footer: 350 m² stores, rent 45% of prime (P.C. Hooftstraat for NL), WACC 8%, Eurostat labour cost, new-entrant factor 85%, opening inventory 90 days, terminal growth 1%.

11. DECISION (kicker 10) — black slide with stripe band: "GO CONDITIONNEL : LES PAYS-BAS". Rule checks with check/cross icons + text: ✓ NPV positive €76M; ✓ still positive at −20% sales (€20M); ✗ payback 4.9 yrs vs 4-yr target. Plan B: Ireland (better store economics, NPV €90M, payback 4.5 yrs, but smaller market, 1,071 km from an EU hub). Conditions for a full GO: rents ≤ €1,260/m² (45% of prime); 2027 pilot of 3 stores (Amsterdam, Rotterdam, Utrecht) reaching 70% of target in year 1; exclusive brands + loyalty vs ICI Paris XL and Douglas; secure the ~9% of sales held by local exclusive distributors. Timeline graphic: 2027 pilot 3 stores → Q1 2028 decision gate → 2028–2029 roll-out to 15 stores. Next steps: real store data, broker rent quotes, brand contract review.

## Speaker notes (one per slide, in the selected language)
1 Introduce the team (Damien, Jude, Kevin, Natalia, Stephen) and the question: which country, Go or No-Go; give the answer up front. · 2 France is saturated; margin improves but growth is near zero. · 3 Only 5 comparable European countries have no store. · 4 Seven sources merged in DuckDB, reproducible in one command; data contracts keep the team's files consistent. · 5 Weights frozen before the results to avoid bias. · 6 Move the sliders: the Netherlands stay first in all 6 scenarios. · 7 Stress the price finding: same online price everywhere. · 8 Team deep-dive: Kevin (market), Stephen (prices), Jude (competition), Natalia (dashboard). Fragrance confirms the choice; trap avoided: Dutch raw imports overstate the market fourfold because of Rotterdam. · 9 AI comments, it does not decide. · 10 Show the pessimistic case: NL NPV still positive. · 11 Conclude: conditional Go, decision gate Q1 2028, Ireland as Plan B.

## Quality
Responsive (laptop projector and mobile), accessible (contrast, labels not color-only, aria labels). Add Vitest tests that pin the key figures of study.ts (ranking totals, scenario gaps, business case, fragrance). Before finishing, run the tests and the TypeScript check, fix every error, and check that all 11 slides and /dashboard render without console errors.
