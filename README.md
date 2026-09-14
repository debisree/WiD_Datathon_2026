# Priced Out

**Who can afford a healthy diet?**

An interactive dashboard covering 129 countries, built for the WiD Datathon 2026.

**Live: https://debisree.github.io/WiD_Datathon_2026/**

---

## The question

A healthy diet costs roughly the same almost everywhere. Across the 129 countries here the median is **$3.88 a day** per person, and the whole range runs from $1.90 to $6.17 in purchasing-power dollars. Yet in some countries virtually nobody can afford one and in others virtually everybody can.

The correlation between what a healthy diet costs and the share of people priced out of it is **−0.05** — effectively zero. Where almost everyone can afford a healthy diet it costs $3.21 a day; where most people are priced out it costs $3.57. What separates the two groups is income: a median of $69.12 a day against $4.31.

Food prices are not the story. Wages are. About **2.6 billion people** cannot afford a healthy diet.

## The arithmetic behind the two numbers

The dashboard shows two figures that look like they should be one, and the first page exists mainly to explain the gap between them.

Take Ethiopia:

| | |
|---|---|
| A healthy diet costs | **$3.88** a day |
| Affordable only above | **$5.17** a day |
| The typical person earns | **$4.16** a day |

Nobody spends their entire income on food. Rent, fuel, transport and other essentials come first, so a diet becomes unaffordable well before income falls to its price. Food Prices for Nutrition publishes, for each country, the share of people who cannot afford a healthy diet; read against the income distribution, that share puts Ethiopia's affordability line at $5.17 a day.

The typical Ethiopian earns $4.16 and falls $1.01 short. **74.7% of the country — 91.3 million people — cannot afford a healthy diet.** Both figures are FPN's published estimates.

## The three pages

**Affordability.** The headline cost and the share priced out, then a set of budget bars that cut one person's daily income at the 52% mark and test it against the diet's price: the typical person, you on a slider, and the income it actually takes. Below that, the same test applied to the whole population as an income distribution with the unaffordable share shaded.

**What the money buys.** The day's cost divided across the six food groups as a plate, with per-group costs in dollars benchmarked against the 128-country median. Animal-source foods take about 30% of the cost on average and reach 50% in some countries; oils and fats take about 4%.

**Trends and comparisons.** Nine years of diet-cost trends against regional peers, the cost-versus-affordability scatter, a choropleth world map, a region strip plot, and a ranked, searchable table of all 129 countries.

Every view is linked. Select a country anywhere — dropdown, map, strip, or table — and all three pages follow.

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

Sample sizes are very uneven. North America is two countries and South Asia is six, so these medians should not be read as precise regional estimates.

## Data sources

| Source | Used for |
|---|---|
| [Food Prices for Nutrition 5.0](https://datacatalog.worldbank.org/search/dataset/0061222/food-prices-for-nutrition-fpn) (World Bank, July 2026) — [methodology](https://www.worldbank.org/en/programs/icp/brief/foodpricesfornutrition) | Diet cost in local currency and 2021 PPP, food-group cost and share, cost relative to the poverty line, published unaffordability rates and headcounts, 2017–2025. CC BY 4.0. |
| [Poverty and Inequality Platform](https://pip.worldbank.org/) (World Bank) | Survey mean welfare, Gini coefficients, welfare type and survey year |
| [World Development Indicators](https://databank.worldbank.org/source/world-development-indicators) (World Bank) | GDP per capita, urban/rural shares, agricultural land, employment and value added, exchange rates, food production index |
| [Food Balance Sheets](https://www.fao.org/faostat/en/#data/FBS) (FAOSTAT) | Production, imports, exports, domestic supply |
| [World Bank country classification](https://datahelpdesk.worldbank.org/knowledgebase/articles/906519) | Region and income-group labels |

## What is published data and what we computed

Being explicit about this matters, because one of the headline numbers is not ours.

### Taken from source, unchanged

- Daily cost of a healthy diet and its split across the six food groups
- **The share and number of people unable to afford a healthy diet** — `CoHD_headcount` and `CoHD_unafford_n`, matched to each country's survey year. These are FPN's published estimates, not model output. `target.csv` also contains a `cannot_afford` column recomputed from PIP at a flat 52% food share; it diverges from the published series by 10 percentage points on average and **is not used in the dashboard**.
- Diet cost as a multiple of the poverty line
- All survey means, Gini coefficients and World Development Indicators

A healthy diet is defined by Food Prices for Nutrition as the least expensive locally available foods meeting national dietary guidelines for one adult at 2,330 kcal a day. It is a price benchmark, not a record of what anyone eats.

### Computed by us

**The affordability line.** FPN publishes the unaffordable *share* but not the income level where it falls. We locate that level by finding the income at which the published share sits in the country's PIP distribution. It is a reading of the published figure against the distribution, not an independent estimate.

**The income distribution and slider.** Microdata is not public, so each country's distribution is reconstructed as a lognormal fitted to its published mean and Gini:

```
σ = √2 · Φ⁻¹((G + 1) / 2)
μ = ln(mean) − σ² / 2
```

Validated against the published unaffordability rates: **correlation 0.999, mean absolute error 1.5 percentage points, worst case 5.0**. Percentiles are close estimates, not exact ranks — the fit smooths the real shape of the tails.

**Import dependence.** Imports ÷ domestic supply, from the Food Balance Sheets.

**One year per country.** Where several survey years exist we show the most recent. The median country's survey is 4 years old and the oldest is 9, so figures across countries are not contemporaneous.

## Coverage and limitations

- **129 of roughly 218 economies.** A country appears only where diet cost, an income distribution and the context indicators all exist.
- Food Prices for Nutrition 5.0 withholds PPP diet costs and affordability for **Argentina, Myanmar, Somalia, Sudan, Tajikistan and Thailand** over unresolved PPP assumptions.
- Coverage is strongest in Europe, Central Asia and Sub-Saharan Africa, thinnest in East Asia and the Caribbean.
- Nine small states lack boundary geometry at the map's resolution and render as dots rather than shapes.
- The dashboard reports measured values only. `model_frame.csv` and `residuals.csv` contain an exploratory model predicting unaffordability from structural indicators; only 8 of 128 countries passed its stability check, so **no predicted values are shown anywhere in the dashboard**. The files are included for transparency about what was tried.

## Repository

```
index.html          the complete dashboard — open it directly, no build step
data_cache/         source extracts
README.md
```

### data_cache

| File | Contents |
|---|---|
| `fpn.csv` | Food Prices for Nutrition 5.0 indicators, long format, 174 countries, 2017–2025 |
| `pip_baseline.csv` | Full PIP survey series |
| `pip_target_raw.csv` | PIP estimates matched to diet-cost years |
| `pip_vintage.csv` | Survey year and staleness per country |
| `wdi.csv` | 10 World Development Indicators, 217 countries, 2010–2025 |
| `import_dependence.csv` | FAOSTAT balance-sheet quantities and derived ratio |
| `countries.csv` | ISO codes, region, income group, coordinates |
| `coverage_report.csv` | Source availability matrix per country |
| `target.csv` | Assembled country-year panel |
| `model_frame.csv`, `residuals.csv` | Exploratory model and diagnostics (not used in the dashboard) |

## Running it

Open `index.html` in any browser. There is no build step, no server and no install.

Everything is embedded in the single file — the country data, 172 map outlines, both variable fonts and the artwork. It makes **no external network requests**, so it works offline and will not break if a CDN or font service changes.

## Credits

Built by **Team Manthan** for the WiD Datathon 2026.

Data © World Bank and FAO, used under their respective open licences. Food Prices for Nutrition is licensed CC BY 4.0. Dashboard design, code and illustration are original work.

©2026 Team Manthan. All rights reserved.
