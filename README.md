# Priced Out

**Who can afford a healthy diet?**

An interactive dashboard covering 129 countries. WiD Datathon 2026 — Team Manthan.

**Live → https://debisree.github.io/WiD_Datathon_2026/**

---

## Finding

A healthy diet costs roughly the same everywhere. Whether people can buy one does not.

- Diet cost across the 129 countries: median **$3.88** a day, range **$1.90–$6.17** (2021 PPP).
- Correlation between diet cost and the share priced out: **−0.05**. Effectively none.
- Where fewer than 5% are priced out the diet costs **$3.21**; where more than 60% are, **$3.57** — slightly *more*, not less.
- Median daily income in those two groups: **$69.12** against **$4.31**.

Prices are not what separates them. Incomes are. Across the countries shown, **2.58 billion people** cannot afford a healthy diet.

## Reading the dashboard

Ethiopia, reference year 2021:

| | |
|---|---:|
| A healthy diet costs | **$3.88** a day |
| Affordable at incomes above | **$5.17** a day |
| The typical person earns | **$4.16** a day |
| Priced out | **74.7%** — 91.3 million people |

The gap between the first two lines is the point. Rent, fuel and transport come first, so a diet becomes unaffordable well before income falls to its sticker price.

**Three pages.**

- **Affordability** — headline cost and share priced out; income bars against the affordability line; the whole population as an income distribution, with a slider to place yourself.
- **What the money buys** — the day's cost split across six food groups, each benchmarked against the 128-country median. Animal-source foods average **28.9%** of diet cost (range 16–52%); oils and fats **4.9%**.
- **Trends and comparisons** — nine-year price trends against regional peers, the cost-versus-affordability scatter, a choropleth map, a region strip plot, and a ranked table.

Selecting a country anywhere updates all three pages.

## Regional picture

| Region | Countries | Median priced out |
|---|---:|---:|
| Sub-Saharan Africa | 36 | 64% |
| Latin America & Caribbean | 18 | 28% |
| South Asia | 6 | 26% |
| Middle East & North Africa | 13 | 25% |
| East Asia & Pacific | 11 | 17% |
| Europe & Central Asia | 43 | 9% |
| North America | 2 | 4% |

Sample sizes are very uneven; these are not precise regional estimates.

## Sources

- **World Bank. 2026. *Food Prices for Nutrition*, version 5.0.** Washington, DC. [Data Catalog](https://datacatalog.worldbank.org/search/dataset/0061222/food-prices-for-nutrition-fpn) · [DataHub](https://www.worldbank.org/en/programs/icp/brief/foodpricesfornutrition). CC BY 4.0.
  Indicators: `CoHD_PPP`, `CoHD_headcount`, `CoHD_unafford_n`, `CoHD_pov`, and the six food-group series `CoHD_*_PPP` / `CoHD_*_prop`.
- **World Bank. *Poverty and Inequality Platform* (PIP).** [pip.worldbank.org](https://pip.worldbank.org/)
  Survey mean welfare, Gini coefficient, welfare type, survey year.
- **World Bank. *World Development Indicators*.** [DataBank](https://databank.worldbank.org/source/world-development-indicators)
  GDP per capita, urban and rural shares, agricultural land, employment and value added, exchange rates, food production index.
- **FAO. *Food Balance Sheets*.** [FAOSTAT](https://www.fao.org/faostat/en/#data/FBS)
  Production, imports, exports, domestic supply.
- Region and income-group labels follow the [World Bank country classification](https://datahelpdesk.worldbank.org/knowledgebase/articles/906519).

## Definitions

- **Healthy diet** — the least expensive combination of locally available foods meeting food-based dietary guidelines for one representative adult at 2,330 kcal a day. A price benchmark, not observed consumption.
- **Priced out** — the share of a population unable to afford a healthy diet once non-food essentials are met. FPN's published `CoHD_headcount`; the headcount is `CoHD_unafford_n`.
- **Dollars** — 2021 purchasing power parity, per person per day. Comparable across countries; not market exchange rates.

## Method

**Published, unchanged.** Diet cost, share and number priced out, poverty-line ratio and food-group split are FPN figures, matched to each country's reference year. No modelling.

**Derived.**

- **Affordability line.** FPN publishes the unaffordable *share* but not the income at which it falls. We locate that income within the country's PIP distribution, modelled as a lognormal fitted to its published mean and Gini:

  ```
  σ    = √2 · Φ⁻¹((G + 1) / 2)
  μ    = ln(mean) − σ² / 2
  line = exp(μ + σ · Φ⁻¹(published share))
  ```

  A positional reading of FPN's published figure, not an independent estimate.

- **Income percentiles.** The page-one slider uses the same lognormal. Validated against PIP's own headcounts: **r = 0.999, mean absolute error 1.5 pp, maximum 5.1 pp.** Read a percentile as a close estimate, not an exact rank.

- **Import dependence.** Imports ÷ domestic supply, from the Food Balance Sheets.

**Not used.** `target.csv` carries a `cannot_afford` column recomputed from PIP at a flat 52% food share. It diverges from FPN's published series by **10.2 pp on average** (maximum 39 pp) and changes the country ranking. The dashboard reports the published series; `cannot_afford` and `gap_vs_published` are retained for transparency.

## Coverage and limits

- **129 of 217 economies.** Included only where diet cost, an income distribution and the context indicators all exist.
- **Reference years differ**, spanning 2017–2025. Figures are not contemporaneous; the median income survey is 4 years old, the oldest 9.
- **Six countries excluded at source.** FPN 5.0 withholds PPP diet costs and affordability for Argentina, Myanmar, Somalia, Sudan, Tajikistan and Thailand over unresolved PPP assumptions.
- **Regional medians rest on uneven samples** — 43 countries in Europe and Central Asia against 2 in North America.
- **Totals are partial**, summed across the 129 countries shown at differing reference years. Not global estimates.
- **One food-group split missing** (Iran). Nine small states render as points rather than shapes on the map.
- **No predicted values appear anywhere.** An exploratory model of unaffordability was built and discarded — 8 of 128 countries passed its stability check. `model_frame.csv` and `residuals.csv` are retained for transparency.

## Repository

```
index.html      complete dashboard — open directly, no build step
data_cache/     source extracts
README.md
```

| File | Contents |
|---|---|
| `fpn.csv` | FPN 5.0 indicators, long format, 174 countries, 2017–2025 |
| `pip_baseline.csv` | Full PIP survey series |
| `pip_target_raw.csv` | PIP estimates matched to diet-cost years |
| `pip_vintage.csv` | Survey year and staleness per country |
| `wdi.csv` | 10 WDI indicators, 217 countries, 2010–2025 |
| `import_dependence.csv` | FAOSTAT balance-sheet quantities and derived ratio |
| `countries.csv` | ISO codes, region, income group, coordinates |
| `coverage_report.csv` | Source availability matrix |
| `target.csv` | Assembled country-year panel |
| `model_frame.csv`, `residuals.csv` | Discarded model and diagnostics |

**Running it.** Open `index.html` in any browser — no build step, no server, no install. Country data, 172 map outlines, both variable fonts and all artwork are embedded; the file makes **no external network requests**.

## Credits

Built by **Team Manthan** for the WiD Datathon 2026.

Data © World Bank and FAO under their respective open licences; *Food Prices for Nutrition* is CC BY 4.0. Dashboard design, code and illustration are original work.

©2026 Team Manthan. All rights reserved.
