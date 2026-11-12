# Manual data

Files typed in by hand from public documents that have no API. Each row keeps its source URL.
These files are committed to Git, unlike `data/raw/`, which the pipeline regenerates.
Collected on 2026-11-11/12.

| File | Content | Sources |
|------|---------|---------|
| `lvmh_selective_retailing_financials.csv` | LVMH Selective Retailing revenue & profit from recurring operations, 2021–2025 (M€). French number format (`14 852`), `;` separator. **Selective Retailing = Sephora + DFS + Le Bon Marché**; LVMH does not publish Sephora alone. | LVMH annual results press releases |
| `country_facts.csv` | Standard VAT rate, corporate tax rate, customs duty on cosmetics, EU customs union membership, currency, prime high-street retail rent (€/m²/year). | European Commission VAT rates; OECD corporate tax statistics; Irish Revenue (Pillar Two 15 % for groups > €750 m); Norwegian Customs (no duty on cosmetics); Cushman & Wakefield *Main Streets Across the World 2025* |
| `logistics_hubs.csv` | Sephora's known European distribution hubs with coordinates. | Sephora job posting (Saran), Arvato and DHL press releases |
| `sephora_presence.csv` | Which European countries already have Sephora stores, which defines the candidate list. | OpenStreetMap + press (WWD, RetailDetail, Irish Times) |
