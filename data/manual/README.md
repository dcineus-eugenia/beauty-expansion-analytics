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

## Fragrance shipping rules (issue #4)

Collected on 2026-11-13. These rules affect supply from the Düren hub (Germany); they don't change the score.
The ADR figures come from the UK regulator's guide (HSE) and an ADR 2025 lookup table. Nobody has read them in the UNECE text itself, because unece.org blocks automated access. Before using them for a real shipment, check ADR 2025 chapters 3.2 (Table A) and 3.4.

1. **Perfume is a dangerous good.** Alcohol-based fragrance travels as **UN 1266 "Perfumery products"**, class 3 (flammable liquid), packing group II or III, under the ADR agreement for road transport. The EU applies ADR to road, rail and inland waterway transport through Directive 2008/68/EC.
2. **Retail bottles can ship as "limited quantities"** (ADR chapter 3.4): up to 5 L per inner packaging for UN 1266 (Table A, column 7a), packages up to 30 kg gross (20 kg for shrink-wrapped trays), marked with the limited-quantity diamond. Once these conditions are met, the other ADR requirements don't apply, so trucks from Düren can serve the Netherlands and Austria like an ordinary parcel flow. A transport unit carrying 8 tonnes or more of such packages still needs the limited-quantity vehicle marking (ADR 3.4.13).
3. **Ireland goes by sea**, and ships apply the IMDG Code, which has its own limited-quantity regime. The UK land bridge adds customs transit formalities since Brexit (see `logistics_hubs.csv`).
4. **Norway is in the EEA but outside the EU customs union.** ADR applies there too, but every shipment needs an EU export declaration and a Norwegian import declaration. Norway charges no customs duty on cosmetics, but it levies 25 % import VAT, paid in NOK.

Sources: UNECE, ADR 2025, official text (https://unece.org/transport/standards/transport/dangerous-goods/adr-2025-agreement-concerning-international-carriage, not opened); UK Health and Safety Executive, ADR limited-quantity exemptions: 30 kg / 20 kg limits, column 7a, vehicle marking (https://www.hse.gov.uk/CDG/manual/exemptions.htm); ADR 2025 lookup for UN 1266: class 3, F1, limited quantity 5 L, P001 (https://adr-tool.com/626/un-1266); Hong Kong Fire Services Department, UN 1266 packing group II entry, limited quantity 5 L (https://es.hkfsd.gov.hk/dg/en/dangerous_goods/detail/231/); Directive 2008/68/EC (https://eur-lex.europa.eu/eli/dir/2008/68/oj); IMO, IMDG Code (https://www.imo.org/en/OurWork/Safety/Pages/DangerousGoods-default.aspx); Norwegian Customs (https://www.toll.no/en/goods/cosmetics).
