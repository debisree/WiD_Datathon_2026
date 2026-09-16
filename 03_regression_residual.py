#!/usr/bin/env python3
"""
Priced Out - regression runner.

Fits one of five regression methods to predict `cannot_afford` from the 6
model_frame.csv features, evaluates it with 10-fold cross-validation, and
writes predictions + three diagnostic plots to ~/priced_out/outputs_<method>/.

Usage:
    python run_regression.py --method linear_ridge
    python run_regression.py --method fractional_logit --seed 1
    python run_regression.py --method gradient_boosting
    python run_regression.py --method beta_regression
    python run_regression.py --method weighted_ridge
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.othermod.betareg import BetaModel
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.lines import Line2D
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler

FEATURES = ['gdp_pc_ppp_log', 'urban_share', 'agri_land_share', 'agri_excess',
            'food_production_index', 'fx_volatility_log']
TARGET = 'cannot_afford'
ALPHAS = np.logspace(-3, 3, 60)

DATA_PATH = Path.home() / 'priced_out' / 'data_cache' / 'model_frame.csv'
PRICED_OUT_DIR = Path.home() / 'priced_out'

METHOD_TITLES = {
    'linear_ridge': 'Linear ridge regression',
    'fractional_logit': 'Fractional logit (quasi-binomial GLM)',
    'gradient_boosting': 'Gradient boosting',
    'beta_regression': 'Beta regression',
    'weighted_ridge': 'Weighted ridge (inverse income-group variance)',
}

# --------------------------------------------------------------------------
# Per-method fit/predict. Each takes raw (unscaled) train/test feature blocks
# and the training target, and returns predictions on the test block.
# --------------------------------------------------------------------------

def fit_predict_linear_ridge(X_tr, y_tr, X_te, groups_tr=None, seed=0):
    scaler = StandardScaler().fit(X_tr)
    ridge = RidgeCV(alphas=ALPHAS)
    ridge.fit(scaler.transform(X_tr), y_tr)
    return ridge.predict(scaler.transform(X_te))


def fit_predict_weighted_ridge(X_tr, y_tr, X_te, groups_tr, seed=0):
    """Ridge with inverse-variance weights by income group, correcting the
    heteroskedasticity found across income groups (variance shrinks toward
    the 0%/100% ends of the outcome)."""
    groups_tr = pd.Series(groups_tr).reset_index(drop=True)
    y_tr_s = pd.Series(y_tr).reset_index(drop=True)
    group_var = y_tr_s.groupby(groups_tr).transform('var').to_numpy()
    group_var = np.where(~np.isfinite(group_var) | (group_var <= 1e-6), 1e-6, group_var)
    weights = 1.0 / group_var
    weights = weights / weights.mean()

    scaler = StandardScaler().fit(X_tr)
    ridge = RidgeCV(alphas=ALPHAS)
    ridge.fit(scaler.transform(X_tr), y_tr, sample_weight=weights)
    return ridge.predict(scaler.transform(X_te))


def fit_predict_fractional_logit(X_tr, y_tr, X_te, groups_tr=None, seed=0):
    """Quasi-binomial GLM, logit link. Predictions are bounded to (0, 1) by
    construction, unlike an unbounded linear model."""
    scaler = StandardScaler().fit(X_tr)
    Xtr_c = sm.add_constant(scaler.transform(X_tr), has_constant='add')
    Xte_c = sm.add_constant(scaler.transform(X_te), has_constant='add')
    model = sm.GLM(y_tr, Xtr_c, family=sm.families.Binomial()).fit()
    return model.predict(Xte_c)


def fit_predict_beta_regression(X_tr, y_tr, X_te, groups_tr=None, seed=0):
    """Beta regression on a proportion outcome. Beta support is the open
    interval (0, 1), so boundary values (exact 0 or 1) are squeezed inside it
    with the standard Smithson & Verkuilen (2006) transform before fitting;
    residuals are still computed against the untransformed actual value."""
    n = len(y_tr)
    y_tr_t = (y_tr * (n - 1) + 0.5) / n

    scaler = StandardScaler().fit(X_tr)
    Xtr_c = sm.add_constant(scaler.transform(X_tr), has_constant='add')
    Xte_c = sm.add_constant(scaler.transform(X_te), has_constant='add')
    model = BetaModel(y_tr_t, Xtr_c).fit(disp=False)
    return model.predict(Xte_c)


def fit_predict_gradient_boosting(X_tr, y_tr, X_te, groups_tr=None, seed=0):
    gbm = GradientBoostingRegressor(random_state=seed, n_estimators=300, max_depth=2)
    gbm.fit(X_tr, y_tr)
    return gbm.predict(X_te)


FIT_PREDICT = {
    'linear_ridge': fit_predict_linear_ridge,
    'fractional_logit': fit_predict_fractional_logit,
    'gradient_boosting': fit_predict_gradient_boosting,
    'beta_regression': fit_predict_beta_regression,
    'weighted_ridge': fit_predict_weighted_ridge,
}

# --------------------------------------------------------------------------
# Cross-validation
# --------------------------------------------------------------------------

def run_cv(method, seed):
    mdf = pd.read_csv(DATA_PATH)
    X = mdf[FEATURES].to_numpy()
    y = mdf[TARGET].to_numpy()
    groups = mdf['income_group'].to_numpy()
    n = len(mdf)

    kf = KFold(n_splits=10, shuffle=True, random_state=seed)
    fit_predict = FIT_PREDICT[method]

    oof_pred = np.empty(n)
    fold_id = np.empty(n, dtype=int)
    fold_rows = []

    for i, (tr, te) in enumerate(kf.split(X, y), start=1):
        pred = fit_predict(X[tr], y[tr], X[te], groups_tr=groups[tr], seed=seed)
        oof_pred[te] = pred
        fold_id[te] = i
        yt = y[te]
        fold_rows.append({
            'fold': i,
            'n_test': len(te),
            'r2': r2_score(yt, pred),
            'mae': mean_absolute_error(yt, pred),
            'rmse': float(np.sqrt(np.mean((yt - pred) ** 2))),
        })

    folds = pd.DataFrame(fold_rows)

    out = mdf[['iso3', 'country', 'region', 'income_group']].copy()
    out['fold'] = fold_id
    out['actual'] = y
    out['predicted'] = oof_pred
    out['residual'] = out['actual'] - out['predicted']
    out['abs_error'] = out['residual'].abs()
    out['sq_error'] = out['residual'] ** 2

    return out, folds


# --------------------------------------------------------------------------
# Palette (validated: see dataviz skill palette.md / validate_palette.js)
# --------------------------------------------------------------------------
SURFACE, INK, INK_SEC, INK_MUTED = '#fcfcfb', '#0b0b0b', '#52514e', '#898781'
GRID, BASELINE = '#e1e0d9', '#c3c2b7'
BLUE, RED = '#2a78d6', '#d03b3b'
MAE_HUE, RMSE_HUE = '#6da7ec', '#184f95'

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Helvetica Neue', 'Arial', 'DejaVu Sans'],
    'figure.facecolor': SURFACE,
    'axes.facecolor': SURFACE,
    'savefig.facecolor': SURFACE,
})


def _rounded_bar(ax, x, y0, y1, width, color, radius):
    height = y1 - y0
    if abs(height) < 1e-9:
        return
    ax.add_patch(FancyBboxPatch(
        (x - width / 2, min(y0, y1)), width, abs(height),
        boxstyle=f'round,pad=0,rounding_size={radius}',
        linewidth=0, facecolor=color, zorder=3, mutation_aspect=1,
    ))


def plot_fold_cv_errors(folds, method, out_path, n_countries):
    title = METHOD_TITLES[method]
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(17.5, 6.0))
    fig.subplots_adjust(top=0.68, bottom=0.12, left=0.045, right=0.98, wspace=0.26)

    mean_r2, mean_mae, mean_rmse = folds['r2'].mean(), folds['mae'].mean(), folds['rmse'].mean()
    worst_r2_fold = folds.loc[folds['r2'].idxmin(), 'fold']
    best_r2_fold = folds.loc[folds['r2'].idxmax(), 'fold']
    worst_mae_fold = folds.loc[folds['mae'].idxmax(), 'fold']
    best_mae_fold = folds.loc[folds['mae'].idxmin(), 'fold']
    worst_rmse_fold = folds.loc[folds['rmse'].idxmax(), 'fold']
    best_rmse_fold = folds.loc[folds['rmse'].idxmin(), 'fold']

    def style_axis(ax, ymax, mean_val, y_fmt):
        ax.set_xlim(0.3, 10.7)
        ax.set_ylim(0, ymax)
        ax.set_xticks(folds['fold'])
        ax.set_xticklabels(folds['fold'].astype(int), color=INK_SEC, fontsize=9.5)
        ax.tick_params(axis='x', length=0)
        ax.tick_params(axis='y', length=0, colors=INK_SEC, labelsize=9.5)
        ax.yaxis.set_major_formatter(y_fmt)
        for s in ('top', 'right', 'left'):
            ax.spines[s].set_visible(False)
        ax.spines['bottom'].set_color(BASELINE)
        ax.yaxis.grid(True, color=GRID, linewidth=1, zorder=0)
        ax.set_axisbelow(True)
        ax.axhline(mean_val, color=INK_MUTED, linewidth=1.3, linestyle=(0, (4, 2)), zorder=2)
        ax.annotate(f'mean {mean_val:.3f}', (0.98, 0.94), xycoords='axes fraction',
                    ha='right', va='top', fontsize=8.6, color=INK_MUTED)

    for _, r in folds.iterrows():
        color = RED if r['fold'] == worst_r2_fold else BLUE
        _rounded_bar(ax1, r['fold'], 0, r['r2'], 0.62, color, 0.045)
    style_axis(ax1, 1.14, mean_r2, plt.FuncFormatter(lambda v, p: f'{v:.1f}'))
    ax1.set_title('R² by fold', loc='left', fontsize=12.5, fontweight='bold', color=INK, pad=10)
    for fold_id, tag, color in [(best_r2_fold, 'best', INK), (worst_r2_fold, 'worst', RED)]:
        row = folds.loc[folds['fold'] == fold_id].iloc[0]
        ax1.annotate(f"{row['r2']:.2f} — {tag}", (fold_id, row['r2']), xytext=(0, 7),
                     textcoords='offset points', ha='center', fontsize=9.3, fontweight='bold',
                     color=color, zorder=4)
    ax1.set_xlabel('fold', color=INK_SEC, fontsize=9.5, labelpad=6)

    for _, r in folds.iterrows():
        color = RED if r['fold'] == worst_mae_fold else BLUE
        _rounded_bar(ax2, r['fold'], 0, r['mae'], 0.62, color, 0.0035)
    style_axis(ax2, max(0.20, folds['mae'].max() * 1.15), mean_mae,
               plt.FuncFormatter(lambda v, p: f'{v:.2f}'))
    ax2.set_title('Mean absolute error by fold', loc='left', fontsize=12.5, fontweight='bold',
                  color=INK, pad=10)
    for fold_id, tag in [(best_mae_fold, 'best'), (worst_mae_fold, 'worst')]:
        row = folds.loc[folds['fold'] == fold_id].iloc[0]
        color = RED if tag == 'worst' else INK
        ax2.annotate(f"{row['mae']:.3f} — {tag}", (fold_id, row['mae']), xytext=(0, 7),
                     textcoords='offset points', ha='center', fontsize=9.3, fontweight='bold',
                     color=color, zorder=4)
    ax2.set_xlabel('fold', color=INK_SEC, fontsize=9.5, labelpad=6)

    for _, r in folds.iterrows():
        color = RED if r['fold'] == worst_rmse_fold else BLUE
        _rounded_bar(ax3, r['fold'], 0, r['rmse'], 0.62, color, 0.004)
    style_axis(ax3, max(0.22, folds['rmse'].max() * 1.15), mean_rmse,
               plt.FuncFormatter(lambda v, p: f'{v:.2f}'))
    ax3.set_title('RMSE by fold', loc='left', fontsize=12.5, fontweight='bold', color=INK, pad=10)
    for fold_id, tag in [(best_rmse_fold, 'best'), (worst_rmse_fold, 'worst')]:
        row = folds.loc[folds['fold'] == fold_id].iloc[0]
        color = RED if tag == 'worst' else INK
        ax3.annotate(f"{row['rmse']:.3f} — {tag}", (fold_id, row['rmse']), xytext=(0, 7),
                     textcoords='offset points', ha='center', fontsize=9.3, fontweight='bold',
                     color=color, zorder=4)
    ax3.set_xlabel('fold', color=INK_SEC, fontsize=9.5, labelpad=6)

    legend_handles = [
        Line2D([], [], marker='s', ls='', mfc=BLUE, mec='none', ms=10, label='fold error'),
        Line2D([], [], marker='s', ls='', mfc=RED, mec='none', ms=10, label='worst fold (that metric)'),
        Line2D([], [], color=INK_MUTED, lw=1.3, ls=(0, (4, 2)), label='mean across folds'),
    ]
    fig.legend(handles=legend_handles, loc='upper center', ncol=3, frameon=False,
               bbox_to_anchor=(0.5, 0.855), fontsize=9.5, labelcolor=INK_SEC,
               handletextpad=0.6, columnspacing=1.6)

    fig.text(0.06, 0.96, f'Random 10-fold cross-validation — {title}',
              fontsize=15, fontweight='bold', color=INK, ha='left', va='top')
    fig.text(0.06, 0.915,
              f'Predicting cannot_afford · {n_countries} countries, 6 features · '
              'each fold holds out 12–13 countries',
              fontsize=10.5, color=INK_SEC, ha='left', va='top')
    fig.text(0.06, 0.02, 'Source: model_frame.csv, out-of-fold predictions, '
             f'KFold(10, shuffle=True, random_state={SEED_FOR_CAPTION[0]}).',
             fontsize=8, color=INK_MUTED)

    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def plot_best_worst_countries(country_df, method, out_path):
    title = METHOD_TITLES[method]
    worst = country_df.sort_values('abs_error', ascending=False).head(5).copy()
    best = country_df.sort_values('abs_error', ascending=True).head(5).copy()
    d = pd.concat([worst, best], ignore_index=True)

    gap = 0.9
    xpos = list(range(5)) + [5 + gap + i for i in range(5)]
    d['x'] = xpos

    fig, ax = plt.subplots(figsize=(12.5, 6.6))
    fig.subplots_adjust(top=0.76, bottom=0.20, left=0.07, right=0.97)
    WIDTH = 0.52

    for _, r in d.iterrows():
        color = RED if r['residual'] > 0 else BLUE
        lo, hi = sorted([r['predicted'], r['actual']])
        height = hi - lo
        x = r['x']
        if height < 0.006:
            ax.plot([x - WIDTH / 2, x + WIDTH / 2], [r['actual'], r['actual']],
                    color=color, lw=3.4, solid_capstyle='round', zorder=3)
        else:
            ax.add_patch(FancyBboxPatch(
                (x - WIDTH / 2, lo), WIDTH, height,
                boxstyle='round,pad=0,rounding_size=0.05',
                linewidth=0, facecolor=color, zorder=3, mutation_aspect=1,
            ))
        ax.plot([x - WIDTH / 2 - 0.06, x - WIDTH / 2], [r['predicted'], r['predicted']],
                color=INK_MUTED, lw=1.6, zorder=4, solid_capstyle='round')
        ax.plot([x + WIDTH / 2, x + WIDTH / 2 + 0.06], [r['actual'], r['actual']],
                color=INK, lw=1.6, zorder=4, solid_capstyle='round')
        gap_pts = (r['actual'] - r['predicted']) * 100
        ax.annotate(f'{gap_pts:+.1f} pts', (x, hi + 0.025), ha='center', va='bottom',
                    fontsize=9, fontweight='bold', color=color, zorder=5)

    ax.set_xticks(d['x'])
    ax.set_xticklabels(d['country'], rotation=32, ha='right', fontsize=10, color=INK)
    ax.tick_params(axis='x', length=0)

    ax.annotate('WORST 5 — LARGEST MISS', (2, 1.11), ha='center', va='bottom',
                fontsize=10.5, fontweight='bold', color=RED, annotation_clip=False)
    ax.annotate('BEST 5 — SMALLEST MISS', (7 + gap, 1.11), ha='center', va='bottom',
                fontsize=10.5, fontweight='bold', color=BLUE, annotation_clip=False)
    ax.axvline((4 + (5 + gap)) / 2, color=GRID, lw=1.2, zorder=0)

    ax.set_ylim(-0.04, 1.16)
    ax.set_xlim(-0.7, 9 + gap + 0.7)
    ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f'{v:.0%}' if 0 <= v <= 1 else ''))
    ax.set_ylabel('Share of population unable to afford a healthy diet', color=INK_SEC,
                  fontsize=10.3, labelpad=8)
    ax.yaxis.grid(True, color=GRID, linewidth=1, zorder=0)
    ax.set_axisbelow(True)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    ax.spines['left'].set_color(BASELINE)
    ax.spines['bottom'].set_color(BASELINE)
    ax.tick_params(axis='y', colors=INK_SEC, labelsize=9.5, length=0)

    legend_handles = [
        Line2D([], [], marker='s', ls='', mfc=BLUE, mec='none', ms=11, label='Observed better than predicted'),
        Line2D([], [], marker='s', ls='', mfc=RED, mec='none', ms=11, label='Observed worse than predicted'),
        Line2D([], [], color=INK_MUTED, lw=1.6, label='predicted (open)'),
        Line2D([], [], color=INK, lw=1.6, label='observed (close)'),
    ]
    fig.legend(handles=legend_handles, loc='upper center', ncol=4, frameon=False,
               bbox_to_anchor=(0.55, 0.895), fontsize=9.3, labelcolor=INK_SEC,
               handletextpad=0.5, columnspacing=1.4)

    fig.text(0.045, 0.965, f'The best-predicted and worst-predicted countries, out of fold — {title}',
              fontsize=14.5, fontweight='bold', color=INK, ha='left', va='top')
    fig.text(0.045, 0.925, 'Each candle spans predicted to observed',
              fontsize=10.3, color=INK_SEC, ha='left', va='top')
    fig.text(0.045, 0.012, 'Source: model_frame.csv, out-of-fold predictions, KFold(10, shuffle=True).',
              fontsize=8, color=INK_MUTED)

    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def plot_income_group_errors(country_df, method, out_path):
    title = METHOD_TITLES[method]
    ORDER = ['Low income', 'Lower middle income', 'Upper middle income', 'High income']
    grp = country_df.groupby('income_group').apply(lambda d: pd.Series({
        'n': len(d),
        'bias': d['residual'].mean(),
        'mae': d['abs_error'].mean(),
        'rmse': np.sqrt((d['residual'] ** 2).mean()),
        'r2': 1 - (d['residual'] ** 2).sum() / ((d['actual'] - d['actual'].mean()) ** 2).sum(),
    }), include_groups=False).reindex(ORDER).reset_index().rename(columns={'index': 'income_group'})

    SHORT = {'Low income': 'Low income', 'Lower middle income': 'Lower\nmiddle income',
             'Upper middle income': 'Upper\nmiddle income', 'High income': 'High income'}
    grp['label'] = grp['income_group'].map(SHORT) + grp['n'].astype(int).map(lambda n: f'\n(n={n})')

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15.5, 6.4))
    fig.subplots_adjust(top=0.72, bottom=0.14, left=0.055, right=0.98, wspace=0.28)
    x = np.arange(4)
    W = 0.5

    bias_lim = max(0.035, grp['bias'].abs().max() * 1.4)
    for xi, r in zip(x, grp.itertuples()):
        color = RED if r.bias > 0 else BLUE
        _rounded_bar(ax1, xi, 0, r.bias, W, color, 0.0015)
        off, va = (6, 'bottom') if r.bias >= 0 else (-6, 'top')
        ax1.annotate(f'{r.bias:+.3f}', (xi, r.bias), xytext=(0, off), textcoords='offset points',
                     ha='center', va=va, fontsize=9.7, fontweight='bold', color=color, zorder=4)
    ax1.axhline(0, color=BASELINE, lw=1.2, zorder=2)
    ax1.set_ylim(-bias_lim, bias_lim)
    ax1.set_title('Bias (mean residual)', loc='left', fontsize=12.5, fontweight='bold', color=INK, pad=10)
    ax1.set_ylabel('observed − predicted', color=INK_SEC, fontsize=9.8, labelpad=6)
    ax1.annotate('under-predicts', (3.6, bias_lim * 0.78), fontsize=8, color=INK_MUTED, ha='right',
                 annotation_clip=False)
    ax1.annotate('over-predicts', (3.6, -bias_lim * 0.78), fontsize=8, color=INK_MUTED, ha='right',
                 annotation_clip=False)

    w2 = 0.32
    mae_lim = max(0.22, (grp['rmse'].max()) * 1.15)
    for xi, r in zip(x, grp.itertuples()):
        _rounded_bar(ax2, xi - w2 / 2 - 0.02, 0, r.mae, w2, MAE_HUE, 0.003)
        _rounded_bar(ax2, xi + w2 / 2 + 0.02, 0, r.rmse, w2, RMSE_HUE, 0.003)
        ax2.annotate(f'{r.mae:.3f}', (xi - w2 / 2 - 0.02, r.mae), xytext=(0, 5), textcoords='offset points',
                     ha='center', fontsize=8.6, fontweight='bold', color=MAE_HUE, zorder=4)
        ax2.annotate(f'{r.rmse:.3f}', (xi + w2 / 2 + 0.02, r.rmse), xytext=(0, 5), textcoords='offset points',
                     ha='center', fontsize=8.6, fontweight='bold', color=RMSE_HUE, zorder=4)
    ax2.set_ylim(0, mae_lim)
    ax2.set_title('Absolute error', loc='left', fontsize=12.5, fontweight='bold', color=INK, pad=10)
    ax2.set_ylabel('error (share of population)', color=INK_SEC, fontsize=9.8, labelpad=6)

    r2_lo = min(-0.6, grp['r2'].min() * 1.15)
    for xi, r in zip(x, grp.itertuples()):
        color = BLUE if r.r2 >= 0 else RED
        _rounded_bar(ax3, xi, 0, r.r2, W, color, 0.02)
        off, va = (6, 'bottom') if r.r2 >= 0 else (-6, 'top')
        ax3.annotate(f'{r.r2:+.2f}', (xi, r.r2), xytext=(0, off), textcoords='offset points',
                     ha='center', va=va, fontsize=9.7, fontweight='bold', color=color, zorder=4)
    ax3.axhline(0, color=BASELINE, lw=1.2, zorder=2)
    ax3.set_ylim(r2_lo, max(0.6, grp['r2'].max() * 1.4))
    ax3.set_title('R²  (vs. group-mean baseline)', loc='left', fontsize=12.5, fontweight='bold',
                  color=INK, pad=10)

    for ax in (ax1, ax2, ax3):
        ax.set_xlim(-0.65, 3.65)
        ax.set_xticks(x)
        ax.set_xticklabels(grp['label'], fontsize=9.6, color=INK_SEC)
        ax.tick_params(axis='x', length=0)
        ax.tick_params(axis='y', colors=INK_SEC, labelsize=9, length=0)
        for s in ('top', 'right'):
            ax.spines[s].set_visible(False)
        ax.spines['left'].set_color(BASELINE)
        ax.spines['bottom'].set_visible(False)
        ax.yaxis.grid(True, color=GRID, linewidth=1, zorder=0)
        ax.set_axisbelow(True)

    leg1 = [Line2D([], [], marker='s', ls='', mfc=BLUE, mec='none', ms=10, label='over-predicts (favourable gap)'),
            Line2D([], [], marker='s', ls='', mfc=RED, mec='none', ms=10, label='under-predicts')]
    fig.legend(handles=leg1, loc='upper left', bbox_to_anchor=(0.055, 0.895), ncol=1,
               frameon=False, fontsize=8.8, labelcolor=INK_SEC, handletextpad=0.5)
    leg2 = [Line2D([], [], marker='s', ls='', mfc=MAE_HUE, mec='none', ms=10, label='MAE'),
            Line2D([], [], marker='s', ls='', mfc=RMSE_HUE, mec='none', ms=10, label='RMSE')]
    fig.legend(handles=leg2, loc='upper left', bbox_to_anchor=(0.40, 0.895), ncol=1,
               frameon=False, fontsize=8.8, labelcolor=INK_SEC, handletextpad=0.5)
    leg3 = [Line2D([], [], marker='s', ls='', mfc=BLUE, mec='none', ms=10, label='beats baseline (R²>0)'),
            Line2D([], [], marker='s', ls='', mfc=RED, mec='none', ms=10, label='worse than baseline (R²<0)')]
    fig.legend(handles=leg3, loc='upper left', bbox_to_anchor=(0.735, 0.895), ncol=1,
               frameon=False, fontsize=8.8, labelcolor=INK_SEC, handletextpad=0.5)

    fig.text(0.045, 0.965, f'Out-of-fold error by income group — {title}', fontsize=15.5,
              fontweight='bold', color=INK, ha='left', va='top')
    fig.text(0.045, 0.925,
              'Predicting cannot_afford · bias and R² can flip sign across the income scale',
              fontsize=10.3, color=INK_SEC, ha='left', va='top')
    fig.text(0.045, 0.02, 'Source: model_frame.csv, out-of-fold predictions, KFold(10, shuffle=True).',
              fontsize=8, color=INK_MUTED)

    fig.savefig(out_path, dpi=220)
    plt.close(fig)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

SEED_FOR_CAPTION = [0]  # set from main(), read by plot_fold_cv_errors


def main():
    parser = argparse.ArgumentParser(description='Run a regression method on the priced_out data.')
    parser.add_argument('--method', required=True,
                         choices=['linear_ridge', 'fractional_logit', 'gradient_boosting',
                                  'beta_regression', 'weighted_ridge'])
    parser.add_argument('--seed', type=int, default=0, help='Random seed for the 10-fold split '
                         '(and for gradient_boosting\'s own randomness).')
    args = parser.parse_args()

    SEED_FOR_CAPTION[0] = args.seed

    country_df, folds = run_cv(args.method, args.seed)

    out_dir = PRICED_OUT_DIR / f'outputs_{args.method}'
    out_dir.mkdir(parents=True, exist_ok=True)

    pred_path = out_dir / 'predictions.csv'
    country_df.to_csv(pred_path, index=False)

    plot_fold_cv_errors(folds, args.method, out_dir / 'fold_cv_errors.png', len(country_df))
    plot_best_worst_countries(country_df, args.method, out_dir / 'best_worst_countries.png')
    plot_income_group_errors(country_df, args.method, out_dir / 'income_group_errors.png')

    pooled_r2 = 1 - country_df['sq_error'].sum() / ((country_df['actual'] - country_df['actual'].mean()) ** 2).sum()
    n_oob = int(((country_df['predicted'] < 0) | (country_df['predicted'] > 1)).sum())

    print(f'method: {args.method}  (seed={args.seed})')
    print(f'countries: {len(country_df)}')
    print(f'pooled out-of-fold R2 : {pooled_r2:.4f}')
    print(f"pooled out-of-fold MAE: {country_df['abs_error'].mean():.4f}")
    print(f"pooled out-of-fold RMSE: {np.sqrt(country_df['sq_error'].mean()):.4f}")
    print(f'predictions outside [0,1]: {n_oob} of {len(country_df)}')
    print()
    print(f'wrote {pred_path}')
    print(f'wrote {out_dir / "fold_cv_errors.png"}')
    print(f'wrote {out_dir / "best_worst_countries.png"}')
    print(f'wrote {out_dir / "income_group_errors.png"}')


if __name__ == '__main__':
    main()
