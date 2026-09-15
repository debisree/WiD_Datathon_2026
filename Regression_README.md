# The model — what was done and what was found

Covers `02_regression_model.ipynb`. Written to be readable without a statistics background.

**Produces:** `data_cache/residuals.csv`, `data_cache/model_frame.csv`

---

## The question

Every country has some share of its population that cannot afford a healthy diet. That
share is high in poor countries and low in rich ones. No surprise there.

The interesting question is not what the number is. It is **which countries deviate from
what their economics would predict**. A country doing much better than its income level
implies is doing something right. A country doing much worse has a problem that money alone
does not explain.

Finding those countries requires a model of what is normal. The model is not the
deliverable — it is the ruler that deviation gets measured against.

---

## Step 1 — One row per country

`target.csv` holds several rows for some countries, because some ran more than one household
survey between 2017 and 2025. Only the most recent survey per country is kept.

**Why.** A regression treats every row as an independent observation. Three rows for Albania
and one for Kenya gives Albania three votes. The question is about countries, not
country-years, so each country gets one row.

---

## Sample attrition: 138 to 128

Three country counts appear across this project. They are not inconsistent — each stage
imposes a requirement the previous one did not.

| Stage | Countries | Lost | Why |
|---|---|---|---|
| Certified usable sample | **138** | — | In FPN, PIP and WDI, with a household survey under 10 years old |
| After building the outcome | **129** | 9 | 5 have no survey coinciding with a published diet cost; 4 have no PPP-denominated cost |
| After requiring complete predictors | **128** | 1 | West Bank & Gaza (PSE), missing WDI covariates |

**Where each number comes from.** 138 is the upstream sample definition, set in
`coverage_report.csv`. The other two are produced downstream — 129 in the target notebook,
128 here. Neither reduction indicates an error upstream. A country can be certified usable
and still fail these stages, because building the outcome and fitting the model each require
things that coverage alone does not guarantee.

**Almost all the loss happens when building the outcome, not when fitting.** Of the nine,
five — **Ghana, Liberia, South Sudan, Eswatini and Zimbabwe** — have no household survey
falling inside 2017–2025 in a year with a published diet cost, and the outcome requires both
in the same year. The other four have no PPP-denominated diet cost in FPN v5.0, so no
poverty line can be set for them. Local currency values exist for those but are not
comparable across countries.

**All five survey-related losses are Sub-Saharan African.** This matters, and is stated here
rather than left in a table. The upstream coverage rule was deliberately relaxed from seven
years to ten precisely to avoid excluding African countries; the same pressure reappears one
stage later, because the outcome needs a survey and a published diet cost in the *same* year,
which is a stricter condition than either alone. The resulting sample under-represents the
region the research question most concerns. It does not invalidate the results — Sub-Saharan
Africa still contributes 36 countries, the largest single region, and the model predicts it
well (fold R² +0.60) — but any regional claim should be read with the five absences in mind.

**The complete-case filter costs one country.** Only West Bank & Gaza lacks the WDI
covariates the model needs. It is dropped rather than imputed: at this sample size, imputing
a predictor pulls a country toward the sample average, making it look artificially typical
and potentially hiding a genuine outlier. Since unusual countries are the entire point,
dropping is the conservative choice.

Both notebooks print the affected countries by name when they run, so attrition is
documented rather than absorbed silently.

---

## Step 2 — Building the features

Four features come straight from the data: log GDP per capita, urban share, agricultural
land share, food production index. Two have to be constructed.

### `fx_volatility_log`

An exchange rate as a level means nothing across countries. One dollar buys 150 yen or 20
pesos, and neither number says anything about food. What matters is whether the rate is
*stable* — an unstable currency makes imported food unpredictably expensive.

So the feature is the standard deviation of year-on-year exchange rate change, then `log1p`
transformed. Without the transform, a handful of hyperinflation cases (raw maximum around 30
against a median near 0.07) would dominate the whole variable.

### `agri_excess`

This one addresses a trap worth understanding.

"Share of the economy that is agriculture" and "how poor the country is" are close to the
same measurement. Poor countries are agricultural; that is what being poor looks like
economically. Put both into a regression and they compete to explain the same variation, and
neither coefficient means anything.

The fix is to regress agricultural value added on log GDP, discard the fitted part, and keep
the residual. That residual answers a different and more useful question: **is this country
more agricultural than its income level would suggest?** It is now independent of income, so
it can contribute something of its own.

---

## Step 3 — Checking for overlap

Before fitting anything, check whether features are secretly measuring the same thing. The
tool is VIF — variance inflation factor — which asks how well each feature can be predicted
from the others. Above 10 is a problem, above 5 is a warning.

**Result.** Highest value 2.72. `agri_excess` came in at 1.01, meaning the residualisation
worked exactly as designed.

This mattered later. When GDP turned out to dominate the coefficients, collinearity had
already been ruled out as the explanation.

---

## Step 4 — Ridge regression

Ridge is ordinary regression with a penalty on large coefficients.

**Why the penalty.** With 128 observations and 6 correlated features, unpenalised
coefficients swing around when the sample changes slightly. The penalty pulls them toward
zero, accepting a little bias in exchange for much more stability. Its size is chosen by
cross-validation rather than set by hand.

**Result.** Penalty 1.1242 · in-sample R² 0.850 · mean absolute error 0.0994.

Quote the MAE in plain language: average error is about **10 percentage points of
population**. R² sounds more impressive, but it is flattered by the outcome spanning nearly
the full 0-to-1 range across countries.

---

## Step 5 — Two kinds of cross-validation

Cross-validation means hiding part of the data, training on the rest, and predicting what
was hidden. It is the only honest way to know whether a model works on data it has not seen.

Two schemes run here, answering different questions.

**Random 10-fold.** Shuffle, split into ten parts, predict each part from the other nine.
Question: *how well does this predict a country in general?*

> **Result: R² 0.810.** Against 0.850 in-sample, that is almost no overfitting. This is the
> headline number.

**Region-grouped.** Hold out an entire region at a time. Question: *does this relationship
transfer to a part of the world the model has never seen?* Much harder.

> **Result:** confusing at first glance, and a useful lesson.

### The R² lesson

The region-grouped average was **−42**, with North America at **−296**. That looks
catastrophic. It is not.

R² measures improvement over predicting the fold's own average. North America contains two
countries whose outcomes differ by less than a percentage point. Predicting their average is
near-perfect by construction, so R² divides by something close to zero and explodes.

The tell is MAE, which has no denominator. North America's MAE was **0.0515 — the best of
any fold.** The model predicted those two countries better than anywhere else.

**Always check absolute error before believing a catastrophic R².**

Underneath the artifact were two real findings:

| Region held out | R² | MAE | Reading |
|---|---|---|---|
| Sub-Saharan Africa (36) | +0.60 | 0.1155 | The model reaches the high end fine |
| Europe & Central Asia (43) | −1.34 | 0.1424 | A genuine limitation |
| North America (2) | −296 | 0.0515 | Artifact — too few countries to compute |

Europe & Central Asia is the real boundary. Its 43 countries cluster near the bottom of the
range, and once nearly everyone can afford the diet, income stops separating countries and
the model has little left to work with. This belongs in the write-up as a scope condition,
phrased as what the model can and cannot do.

---

## Step 6 — Out-of-fold residuals

The residual — observed minus predicted — is the actual finding. But *which* prediction?

An in-sample residual is contaminated. The model saw that country while fitting, so it is
partly grading its own work. It shrinks residuals unevenly, hardest for the high-leverage
countries that are often the interesting ones.

An out-of-fold prediction comes from a model that never saw the country being judged.

Random folds are used here rather than region-grouped folds. Region grouping forces
extrapolation, so the largest errors land wherever the held-out region was hardest to reach
— the outlier list would be an artifact of the fold scheme rather than a fact about
countries.

**Result.** Out-of-fold R² 0.834 · residual mean −0.001, so no systematic bias · range
−0.345 to +0.396.

---

## Step 7 — The step that turns residuals into a finding

This is the most important idea in the notebook.

With 128 countries, roughly 13 will land in the top decile of residual under **any** model.
That is arithmetic, not discovery. Reporting those 13 would be noise-mining.

So every candidate faces two tests.

**Bootstrap stability.** Resample the 128 countries with replacement, refit, record who is
extreme. Repeat 500 times. A country must be extreme in **at least 80%** of resamples. One
that is extreme in half of them cannot be told apart from luck.

**Specification stability.** Drop each of the 6 features in turn, refit, record who is
extreme. Again **80%**. This rules out outliers that exist only because one particular
variable happens to be in the model.

> **Result: 8 of 128 cleared both**, down from roughly 13. Five candidates did not survive.

The stability plot shows the survivors alone in the top-right corner with a visible gap
below them. That gap means the result does not depend on the threshold — move the cutoff to
0.7 or 0.9 and the same countries appear.

---

## Step 8 — Sorting by data quality

The 8 are then **sorted, not filtered**, on two flags: a survey older than 10 years, and a
`gap_vs_published` above 0.20, meaning the World Bank's own published figure looks like a
regional imputation rather than a measurement.

> **Result:** 0 stale · 2 likely imputed · **6 clean**

Sorting after the stability test rather than filtering before it means nothing disappears
silently. Both lists are reportable, with the caveat attached where it belongs.

The two set aside are the Philippines and Lao PDR. Both are in East Asia, which costs the
regional pattern some of its force — Indonesia now carries it alone on clean data.

---

## Steps 9 and 10 — Closing the obvious objections

**Would a tree-based model do better?** A gradient boosted model was fitted purely as a
diagnostic: **0.790 against ridge's 0.810.** It lost. So there is no hidden non-linearity
the linear model is missing — which also means the residuals reflect country behaviour
rather than a badly specified model.

**Does excluding import dependence distort the result?** Refit with it included, on the
reduced 120-country sample. Every coefficient kept its sign and near-identical magnitude.
Import dependence itself came in at −0.0021, effectively zero.

Note that 7 of the 8 countries lost when requiring that variable are African, which is why
it was held out of the main model in the first place.

---

## What was found

### Income is nearly the whole story

| Feature | Share of total coefficient weight |
|---|---|
| `gdp_pc_ppp_log` | **73.8%** |
| `fx_volatility_log` | 9.8% |
| `agri_excess` | 7.0% |
| `food_production_index` | 6.6% |
| `urban_share` | 1.8% |
| `agri_land_share` | 1.1% |
| `import_dependence` | ≈ 0 (robustness fit) |

This is a genuine result, not a shortcoming. A common assumption is that food affordability
is driven by agriculture, food systems and trade exposure. Once income is known, those
contribute almost nothing.

It also sharpens the framing: "expected unaffordability" simply means **what a country's
income level predicts**, and the outliers are countries beating or falling short of their
income.

### The model is accurate

Out-of-fold R² **0.834**, average error about **10 percentage points of population**.

### Six countries deviate robustly

**Beating their income level**

| Country | Observed | Predicted | Gap |
|---|---|---|---|
| Uzbekistan | 14.3% | 48.8% | −34.5 pts |
| Belize | 7.0% | 35.2% | −28.2 pts |
| Guinea | 47.2% | 73.3% | −26.1 pts |

**Falling short of their income level**

| Country | Observed | Predicted | Gap |
|---|---|---|---|
| Indonesia | 74.8% | 35.2% | +39.6 pts |
| Equatorial Guinea | 59.9% | 24.8% | +35.1 pts |
| Kenya | 87.7% | 61.2% | +26.5 pts |

Three in each direction. A balanced split is a better result than a one-sided one: it shows
the model is not systematically wrong in one direction, and that no narrative was
cherry-picked.

### The sharpest illustration

**Guinea and Equatorial Guinea** are West African neighbours pointing opposite ways. Guinea
is low-income and performs 26 points *better* than predicted. Equatorial Guinea is
upper-middle-income on paper and performs 35 points *worse*.

Equatorial Guinea's GDP comes almost entirely from oil, concentrated in very few hands, so
mean income badly overstates what an ordinary person has. The model sees only the average,
and the average lies.

### Every outlier is middle-income

None are low-income or high-income. Mechanically this makes sense — at the extremes the
outcome is pinned near 0 or 1 and there is no room to deviate — but it is a real scope
condition and belongs in the write-up.

---

## Known limitations

**The model can predict outside 0 to 1.** A linear model fitted to a bounded share has no
mechanism preventing this. Section 11 counts how often it happens.

**It systematically overpredicts at the low end.** Visible in the residuals-vs-fitted plot
as a sharp diagonal edge on the left. Where the true value is 0, the residual can only be
`0 − prediction`, so those points fall on a perfect line. A floor effect, not a mistake, but
it means low-unaffordability countries are consistently predicted too high. A bounded
specification such as fractional logit or beta regression would remove both this and the
out-of-range predictions.

**Europe & Central Asia transfers poorly**, for the reason given in Step 5.

**Five Sub-Saharan African countries are absent** — Ghana, Liberia, South Sudan, Eswatini
and Zimbabwe — because no household survey coincides with a published diet cost. The sample
therefore under-represents the region the question most concerns. See the attrition section.

**Six anomalies, no mechanism.** The model identifies which countries deviate. It does not
explain why. `gini_pip` sits unused in `target.csv` for every country, and Equatorial Guinea
points directly at inequality as the likely mechanism. Regressing the residuals on Gini
would move the result from *"here are six unusual countries"* to *"income predicts
affordability, and where it fails, distribution is why."*

---

## Specification summary

| | |
|---|---|
| Outcome | `cannot_afford` |
| Estimator | Ridge regression, linear |
| Sample | 128 countries, one row each, latest survey (138 certified — see attrition) |
| Features | 6 |
| Headline CV | Random 10-fold, R² 0.810 |
| Transfer test | Region-grouped, reported per fold |
| Residuals | Out-of-fold, random folds |
| Outlier criteria | ≥80% bootstrap **and** ≥80% specification |
| Quality flags | `years_stale > 10`, `abs(gap_vs_published) > 0.20` |

---

## Running

Upload to Colab and run top to bottom. Around two minutes; the 500-resample bootstrap in
Step 7 is the slowest part.

Requires `target.csv` inside `data_cache.zip` in Drive. Section 1 halts with a clear error
if it is absent. The final cell writes the updated zip back to Drive.
