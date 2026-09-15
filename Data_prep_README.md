# Priced Out: handoff to modelling

**Goal in one line:** predict how unaffordable a healthy diet is in each country from that country's economic structure, then use the countries the model gets wrong as the finding.

The residuals are the point, not the fit. Countries doing much better than their structure predicts are worth naming; so are the ones doing worse.

---

## The files

| File | What it is | Use |
|---|---|---|
| `fpn.csv` | Diet costs, World Bank FPN v5.0 | Half the target |
| `pip_baseline.csv` | Income distributions, World Bank PIP | Other half of the target |
| `wdi.csv` | Structural indicators, long format | Features |
| `countries.csv` | ISO3, region, income group | Grouping for cross-validation |
| `coverage_report.csv` | Which countries are usable | Sample definition |
| `pip_vintage.csv` | Survey year per country | Data quality column |
| `import_dependence.csv` | Cereal imports / domestic supply | Robustness only, see below |

All keyed on `iso3`. All long format: `iso3, year, indicator, value`.

---

## Read this before modelling

**1. The target variable does not exist yet.**

`fpn.csv` gives the cost of a healthy diet per person per day in PPP dollars (`CoHD_PPP`).
`pip_baseline.csv` gives income distributions.

Neither is the outcome. The outcome is the share of each country's population that cannot afford the diet, and it is built by querying the PIP API at a poverty line equal to that country's diet cost:

```
GET {PIP_BASE}/pip?country={iso3}&year={y}&povline={CoHD_PPP for that country}&ppp_version=2021
```

The returned `headcount` is the target. `ppp_version=2021` is not optional; FPN v5.0 uses 2021 PPPs and a mismatch produces wrong numbers that look reasonable.

`CoHD_headcount` in `fpn.csv` is the World Bank's own published version of this. Do not use it as the target. Use it as a comparison: the World Bank imputes it from regional aggregates where country data is missing, so the gap between your computed value and theirs is a useful measure of which countries are estimate rather than measurement.

**2. The sample is 138, not 170.**

152 countries have FPN, PIP and WDI. 138 of those have a household survey less than 10 years old. Filter on `coverage_report.csv` where `usable == True`.

At n=138 with 6 to 8 features, use ridge or elastic net. Gradient boosting will overfit and grouped CV will not fully catch it. If a flexible model does not beat the regularised linear one out of sample, that is a legitimate result worth reporting, not a failure.

Cross-validate grouped by country, never at random. Add a second split grouped by region to test transfer.

**3. Food group data is 2021 only.**

The total diet cost runs 2017 to 2025. The six food group costs (`CoHD_ss_PPP`, `CoHD_v_PPP`, `CoHD_f_PPP`, `CoHD_asf_PPP`, `CoHD_lns_PPP`, `CoHD_of_PPP`) exist for 2021 alone, 161 countries.

So anything about which food group binds, or clustering countries by cost profile, is a single-year cross-section. It cannot be turned into a trend.

---

## Features

From `wdi.csv`, use these six:

- `gdp_pc_ppp`
- `urban_share`
- `agri_land_share`
- `agri_value_added_share`
- `agri_employment_share`
- `food_production_index`

Dropped deliberately:

- `gini_wdi` covers only 73 of 161. PIP returns a Gini that is consistent with the income distributions already in use.
- `rural_share` is 100 minus `urban_share`. Perfectly collinear.
- `exchange_rate_lcu_usd` as a level is not comparable across countries. Use volatility instead: standard deviation of year-on-year percent change, then `log1p` to handle the hyperinflation tail (raw max is 30, median 0.07).

`import_dependence.csv` is held back on purpose. Including it costs 11 countries, 8 of them low-income Sub-Saharan African, which is exactly the group the question is about. Fit the main model without it, then refit on the 141 with it included and show the coefficients hold. That is a robustness paragraph, not a constraint on the main model.

---

## Known gaps

- FAOSTAT was intermittently unreachable during the build. Import dependence comes from the bulk Food Balance Sheets file dated October 2025, which predates FPN v5.0.
- FPN v5.0 withholds PPP-denominated indicators for Argentina, Myanmar, Somalia, Sudan, Tajikistan and Thailand. Local currency values are still available for those six.
- The "dropped, with reason" table in the coverage report is still computed against the four-source definition including FBS, so it shows 141 rather than 152. Cosmetic.
