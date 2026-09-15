# Target construction — `cannot_afford`

Covers `01_build_target.ipynb`. Sits between data acquisition and the regression model.

**Produces:** `data_cache/target.csv`, containing the outcome variable for the model.

---

## What the target is

`cannot_afford` — the share of a country's population that cannot afford a healthy diet.

It exists in none of the prepared files. Two inputs are required and neither is the answer
alone: `fpn.csv` supplies the cost of a healthy diet per person per day in PPP dollars
(`CoHD_PPP`), and PIP supplies income distributions. The outcome emerges from comparing
them at a country-specific threshold.

### The key step

A diet is not unaffordable simply because it costs more than a person earns — nobody spends
all income on food. The affordability convention compares diet cost against the portion of
income plausibly available for food, taken as 52% from observed food spending in low-income
countries (Herforth et al.). Dividing by that share converts the diet cost into the income
level at which the diet becomes affordable:

```
line = CoHD_PPP / 0.52
```

PIP is then queried at that line, once per country-year:

```
GET {PIP_BASE}/pip
    ?country={iso3}
    &year={y}
    &povline={line}
    &ppp_version=2021
    &fill_gaps=false
    &welfare_type=all
```

The returned `headcount` becomes `cannot_afford`.

---

## Settings

| Setting | Value | Rationale |
|---|---|---|
| `PPP_VERSION` | 2021 | Required, not a preference. FPN v5.0 is denominated in 2021 PPPs; a mismatch produces wrong numbers that look reasonable. |
| `FOOD_BUDGET_SHARE` | 0.52 | Food budget share convention. Raises the poverty line from the diet cost to the income level at which the diet is affordable. |
| `fill_gaps` | false | Real household surveys only, no interpolated years. |
| `welfare_type` | all | Both income- and consumption-based surveys returned, then resolved. |
| `MIN_YEAR` | 2017 | First year FPN publishes the cost of a healthy diet. |

---

## Sample

Starts from `coverage_report.csv` where `usable == True`: 138 countries with FPN, PIP and
WDI coverage plus a household survey under 10 years old.

Two reductions happen inside the notebook, both reported in its output.

**Six countries have no PPP-denominated CoHD.** FPN v5.0 withholds PPP indicators for
Argentina, Myanmar, Somalia, Sudan, Tajikistan and Thailand. Local currency values exist
but are not comparable across countries.

**Some countries have no survey inside 2017–2025**, since the query grid requires a real
survey year and a published diet cost in the same year.

The model uses a country-level cross-section. Because several countries were surveyed more
than once in the window, `target.csv` holds more rows than countries. The `is_latest` flag
marks each country's most recent survey; earlier surveys are retained for sensitivity checks
rather than discarded.

### The country count changes here

| Stage | Countries | Why |
|---|---|---|
| Certified usable | **138** | Set upstream in `coverage_report.csv` |
| After this notebook | **129** | Loses 9 — 5 lack a coinciding survey, 4 lack a PPP diet cost |
| After the model's complete-case filter | **128** | Loses 1 — West Bank & Gaza, missing WDI covariates |

Most of the attrition happens here, not at the modelling stage. Five countries — **Ghana,
Liberia, South Sudan, Eswatini and Zimbabwe** — have no household survey falling inside
2017–2025 in a year with a published diet cost, and the outcome requires both in the same
year. Four more have no PPP-denominated diet cost, so no poverty line can be set for them.

All five survey-related losses are Sub-Saharan African. The upstream coverage rule was
relaxed from seven years to ten specifically to avoid excluding African countries; requiring
a survey and a published cost in the *same* year reintroduces that pressure. Worth carrying
into the modelling write-up as a limitation.

This is not an error in the upstream sample definition. A country can be certified usable and
still fail here, because coverage alone does not guarantee a PPP-denominated cost and a
coinciding survey. The affected countries are printed by name in section 3.

---

## Resolving multiple records per query

One query can return several records for a country-year:

- **Reporting level** — national, urban, rural. National preferred.
- **Welfare type** — income or consumption. Consumption preferred where both exist.

Welfare type is kept as a column, since income- and consumption-based surveys are not
strictly comparable.

`is_interpolated` and `estimation_type` are also captured. Both should indicate a genuine
survey observation throughout, given `fill_gaps=false`, and serve as a direct check rather
than an inference.

---

## `CoHD_headcount` is a diagnostic, not the target

`fpn.csv` contains `CoHD_headcount`, the World Bank's own version of this quantity. It is
**not** used as the outcome, because it is imputed from regional aggregates wherever
country data is missing.

It is retained as `gap_vs_published`, the difference between computed and published values.
Large gaps identify countries whose published figure is estimate rather than measurement,
and the column carries into the modelling stage so those countries can be separated from
substantive findings.

Divergence concentrates in upper-middle-income countries in Europe and Latin America —
Romania, Chile, Bulgaria and Costa Rica among the largest, with published values near 0.5
against computed values under 0.2. A published figure implying half the population of an EU
member state cannot afford a healthy diet is the signature of regional imputation, not a
configuration error.

Section 8 breaks the gap down by region and income group. Geographic clustering confirms
imputation; a scattered pattern with no structure would instead point to a configuration
problem.

> **Results.** Country-years compared: `___`. Correlation: `___`.
> Median gap: `___`. Mean absolute gap: `___`.

---

## Output schema

`target.csv`, one row per country-year:

| Column | Meaning |
|---|---|
| `iso3`, `year` | Keys |
| `cannot_afford` | **The target.** Share unable to afford a healthy diet |
| `is_latest` | Marks the cross-section used for modelling |
| `cohd_ppp` | Cost of a healthy diet, PPP $/day |
| `povline_used` | Poverty line queried, equals `cohd_ppp / 0.52` |
| `mean_income` | Mean income or consumption, PPP $/day |
| `gini_pip` | Returned by PIP. Descriptive only — not a model feature |
| `welfare_type` | income or consumption |
| `reporting_level` | national, urban or rural |
| `is_interpolated`, `estimation_type` | Confirms the observation is a real survey |
| `published` | World Bank's `CoHD_headcount`, comparison only |
| `gap_vs_published` | Computed minus published — the imputation flag |
| `years_stale` | Age of the country's most recent survey — quality control |
| `country`, `region`, `income_group` | Labels. `region` supplies the CV groups |

> **Results.** Rows: `___`. Countries: `___`. Cross-section (`is_latest`): `___`.
> Median target: `___`. Countries on surveys older than 10 years: `___`.

---

## What this hands to the model

| Role | Column |
|---|---|
| Outcome | `cannot_afford` |
| CV grouping | `region` |
| Data quality control | `years_stale` |
| Imputation flag | `gap_vs_published` |
| Sample filter | `is_latest` |

Features come from `wdi.csv` and are built in the modelling notebook, not here:
`gdp_pc_ppp_log`, `urban_share`, `agri_land_share`, `agri_excess`,
`food_production_index`, `fx_volatility_log`.

Two of those need constructing rather than reading. `agri_excess` is the residual of
agricultural value added regressed on log GDP per capita, which strips out the part that
merely restates income level. `fx_volatility_log` is `log1p` of the standard deviation of
year-on-year exchange rate change — computed in the acquisition notebook but never saved,
so it is rebuilt downstream.

`gini_pip` arrives free with every query and is stored, but is not a feature: the agreed
specification excludes inequality measures.

Dropped deliberately, per the agreed specification: `gini_wdi` (73/161 coverage),
`rural_share` (exact complement of `urban_share`), `agri_employment_share`
(r = 0.81 with agricultural value added), and `import_dependence` (costs 11 countries, 8
of them African — robustness check only).

---

## The stale cache trap

Section 1 unzips `data_cache.zip` from Drive, and that zip carries any
`pip_target_raw.csv` from a previous run. The query loop resumes from that cache by design,
so a changed setting in section 2 will appear to have no effect — the notebook returns the
earlier run's numbers unchanged, to four decimal places.

Two safeguards:

1. **The cache reset sits immediately after the unzip**, not before section 1. Deleting the
   file before the unzip accomplishes nothing, since the unzip restores it.
2. **A verification cell follows the query loop.** It checks that
   `povline_used / cohd_ppp` equals `1 / FOOD_BUDGET_SHARE` — 1.923 at the current setting
   — for every row, and raises an error otherwise. Stale results halt the notebook rather
   than propagating silently.

Running top to bottom is always safe. Partial re-runs starting after section 1 are not,
unless the cache is cleared by hand.

---

## Running

Upload to Colab, run top to bottom. Roughly six minutes, dominated by ~500 API calls in
section 6.

Checkpoints:

- **Section 1** prints `removed stale query cache` on any run after the first.
- **Section 4** sends one query and halts on an empty response, before the full loop.
- **Section 6** shows no resume line, and the verification cell prints `OK` with a ratio of
  1.923.
- **Section 8** reports agreement with the published series.
- **Section 10** pushes the updated zip back to Drive. Skipping it leaves the modelling
  notebook reading stale data.

---

## Notes

`spl` and `spr` in the PIP response are the societal poverty line and rate — a different
concept from this target and not to be confused with it.

The 0.52 divisor was briefly dropped during development, on a reading of the handoff note
that gave the poverty line as the diet cost itself. The agreed specification includes it.
Any output where `povline_used / cohd_ppp` equals 1.0 predates that correction and should
be discarded.
