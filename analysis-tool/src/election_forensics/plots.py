"""Графики для всех методов. Единый стиль, backend Agg, кириллица DejaVu.

Подписи мультиязычные: каждый plot_* принимает lang ("ru" по умолчанию);
тексты — в election_forensics.i18n.LABELS.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from .data import ElectionData  # noqa: E402
from .i18n import label  # noqa: E402

plt.rcParams.update(
    {
        "figure.dpi": 150,
        "savefig.dpi": 150,
        "font.size": 9,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": "white",
    }
)

C_MAIN = "#1f77b4"
C_ACC = "#d62728"
C_OK = "#2ca02c"


def _save(fig, out_dir: Path, name: str) -> Path:
    path = out_dir / name
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_shpilkin(data: ElectionData, leader: str, res, out_dir: Path, lang: str = "ru") -> Path:
    """Распределение явки с границей честного спада; голоса лидера по явке с хвостом."""
    from scipy.ndimage import gaussian_filter1d

    from .shpilkin import votes_by_turnout

    bin_width = 0.5
    centers, h_voted = votes_by_turnout(data, None, bin_width)
    _, h_party = votes_by_turnout(data, leader, bin_width)
    hs = gaussian_filter1d(h_voted.astype(float), 2.0)
    src = label(lang, "src_controls") if res.t_cut_source == "controls" else label(lang, "src_own_q995")

    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4))
    ax = axes[0]
    ax.fill_between(centers, h_voted, step="mid", alpha=0.3, color=C_MAIN, label=label(lang, "obs"))
    ax.plot(centers, hs, color=C_MAIN, lw=1.4, label=label(lang, "smooth"))
    ax.axvline(res.t_cut, color=C_ACC, ls="--", lw=1.4,
               label=label(lang, "honest_cut", t=f"{res.t_cut:.1f}%", src=src))
    ax.set_xlabel(label(lang, "turnout_x"))
    ax.set_ylabel(label(lang, "n_voted_y"))
    ax.set_title(label(lang, "shp_dist_title", name=data.name, mode=f"{res.mode:.1f}%",
                       sigma=f"{res.sigma:.1f}"), fontsize=9)
    ax.legend(fontsize=7)

    ax = axes[1]
    ax.fill_between(centers, h_party, step="mid", alpha=0.3, color=C_MAIN,
                    label=label(lang, "votes_leader", p=leader.removeprefix("votes:")))
    ax.fill_between(centers, 0, np.where(centers > res.t_cut, h_party, 0), step="mid",
                    color=C_ACC, alpha=0.6,
                    label=label(lang, "anom_zone", n=f"{res.tail_votes_party:,}",
                                s=f"{res.tail_share_of_party:.2f}%"))
    ax.set_xlabel(label(lang, "turnout_x"))
    ax.set_ylabel(label(lang, "n_party_votes_y"))
    ax.set_title(label(lang, "shp_leader_title"), fontsize=9)
    ax.legend(fontsize=7)
    return _save(fig, out_dir, "shpilkin_core.png")


def plot_comet(data: ElectionData, parties: list[str], out_dir: Path, lang: str = "ru") -> Path:
    """Скаттерплоты «явка × результат» для лидера и оппонентов."""
    n = min(len(parties), 3)
    fig, axes = plt.subplots(1, n, figsize=(3.2 * n, 3.2), sharey=True, squeeze=False)
    t = data.turnout.to_numpy()
    sizes = np.clip(data.registered.to_numpy() / 400, 2, 90)
    for ax, p in zip(axes[0], parties[:n]):
        s = data.share(p).to_numpy()
        ax.scatter(t, s, s=sizes, alpha=0.25, color=C_MAIN, edgecolors="none")
        ax.set_xlabel(label(lang, "turnout_x"))
        ax.set_ylabel(label(lang, "party_share_y"))
        ax.set_title(p.removeprefix("votes:"), fontsize=9)
    fig.suptitle(label(lang, "comet_title", name=data.name), y=1.04, fontsize=10)
    return _save(fig, out_dir, "comet_scatter.png")


def plot_fingerprint(data: ElectionData, leader: str, fp, out_dir: Path, lang: str = "ru") -> Path:
    """2D-плотность (явка × доля лидера), взвешенная по избирателям + компоненты смеси."""
    t = data.turnout.to_numpy()
    s = data.share(leader).to_numpy()
    w = data.registered.to_numpy(dtype=float)
    ok = np.isfinite(s)
    fig, ax = plt.subplots(figsize=(4.6, 3.8))
    hb = ax.hist2d(t[ok], s[ok], bins=[80, 80], weights=w[ok], cmap="viridis",
                   cmin=1e-9, norm=matplotlib.colors.LogNorm())
    ax.plot(*fp.mean_main, "o", ms=9, mfc="none", mec="white", mew=1.6)
    ax.plot(*fp.mean_anom, "s", ms=9, mfc="none", mec=C_ACC, mew=1.6)
    ax.annotate(label(lang, "main_cluster"), fp.mean_main, textcoords="offset points",
                xytext=(8, 6), color="white", fontsize=8)
    ax.annotate(label(lang, "second_component"), fp.mean_anom, textcoords="offset points",
                xytext=(8, -12), color=C_ACC, fontsize=8)
    ax.set_xlabel(label(lang, "turnout_x"))
    ax.set_ylabel(label(lang, "leader_share_y", p=leader.removeprefix("votes:")))
    ax.set_title(label(lang, "fp_title", name=data.name, w=f"{fp.weight_anom:.3f}"), fontsize=9)
    fig.colorbar(hb[3], ax=ax, label=label(lang, "voters_cbar"))
    return _save(fig, out_dir, "fingerprint_2d.png")


def plot_integer_peaks(data: ElectionData, peaks, out_dir: Path,
                       controls: list[tuple[str, int, float, float]] | None = None,
                       lang: str = "ru") -> Path:
    """Классический рисунок Кобака: гистограмма явки с пиками на целых процентах."""
    t = data.turnout.to_numpy()
    t100 = np.round(t, 2)
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.4), gridspec_kw={"width_ratios": [2.2, 1]})

    ax = axes[0]
    bins = np.arange(0, 100.001, 0.1)
    ax.hist(t100, bins=bins, color=C_MAIN, alpha=0.8)
    for k in range(0, 101, 5):
        ax.axvline(k, color=C_ACC, lw=0.5, alpha=0.5)
    lo, hi = np.percentile(t100, [0.5, 99.5])
    ax.set_xlim(lo, hi)
    ax.set_xlabel(label(lang, "turnout_mult5_x"))
    ax.set_ylabel(label(lang, "n_units_y"))
    ax.set_title(label(lang, "units_title", name=data.name), fontsize=9)

    ax = axes[1]
    labels = [label(lang, "int_obs"), label(lang, "int_null")]
    obs_pct = peaks.observed_integer_pct
    null_pct = peaks.null_mean_pct
    ax.bar([0, 1], [obs_pct, null_pct], yerr=[0, 2 * peaks.null_sd_pct], color=[C_ACC, "grey"], capsize=4)
    for x, v in [(0, obs_pct), (1, null_pct)]:
        ax.text(x, v + 0.02, f"{v:.2f}%", ha="center", fontsize=8)
    ax.set_xticks([0, 1], labels, fontsize=8)
    ax.set_ylabel(label(lang, "int_share_y"))
    ax.set_title(label(lang, "int_title", z=f"{peaks.z_score:.1f}"), fontsize=9)
    return _save(fig, out_dir, "integer_peaks.png")


def plot_digit_test(freqs_obs: np.ndarray, expected: np.ndarray, null_band: np.ndarray,
                    test: str, label_text: str, out_dir: Path, lang: str = "ru") -> Path:
    fig, ax = plt.subplots(figsize=(4.8, 3.2))
    x = np.arange(10)
    ax.bar(x - 0.18, freqs_obs * 100, width=0.36, color=C_MAIN, label=label(lang, "obs"))
    ax.bar(x + 0.18, expected * 100, width=0.36, color="grey", alpha=0.6, label=label(lang, "expected"))
    ax.fill_between(x, null_band[0] * 100, null_band[1] * 100, color=C_MAIN, alpha=0.15,
                    label=label(lang, "mc_band"))
    ax.set_xticks(x)
    ax.set_xlabel(label(lang, "digit_x"))
    ax.set_ylabel(label(lang, "freq_y"))
    ttl_key = "digit2_ttl" if test == "benford2" else "digit_last_ttl"
    ax.set_title(label(lang, ttl_key, label=label_text), fontsize=9)
    ax.legend(fontsize=7, loc="lower left", bbox_to_anchor=(0, 1.02), ncols=3, frameon=False)
    return _save(fig, out_dir, f"digit_{test}.png")


def plot_correlations(corr_nat: pd.DataFrame, corr_dist: pd.DataFrame, leader: str,
                      out_dir: Path, lang: str = "ru") -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.8))
    ax = axes[0]
    labels = corr_nat["party"].tolist()
    ypos = np.arange(len(labels))
    colors = [C_ACC if l == leader.removeprefix("votes:") else C_MAIN for l in labels]
    ax.barh(ypos, corr_nat["pearson_w"], color=colors)
    ax.set_yticks(ypos, labels, fontsize=8)
    ax.axvline(0, color="k", lw=0.8)
    ax.set_xlabel(label(lang, "corr_w_x"))
    ax.set_title(label(lang, "corr_nat_ttl"), fontsize=9)
    ax.invert_yaxis()

    ax = axes[1]
    cols = [c for c in corr_dist.columns if c not in ("district_key", "district", "n")][:6]
    im = ax.imshow(corr_dist[cols].to_numpy(), cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(cols)), cols, rotation=45, ha="right", fontsize=7)
    ax.set_yticks(range(len(corr_dist)), corr_dist["district"], fontsize=7)
    fig.colorbar(im, ax=ax, shrink=0.85, label=label(lang, "corr_cbar"))
    ax.set_title(label(lang, "corr_dist_ttl"), fontsize=9)
    ax.grid(False)
    return _save(fig, out_dir, "correlations.png")


def plot_neighbors(neigh: pd.DataFrame, out_dir: Path, lang: str = "ru") -> Path:
    fig, ax = plt.subplots(figsize=(4.8, 3.8))
    ok = neigh["z_turnout"].notna()
    ax.scatter(neigh.loc[ok, "z_turnout"], neigh.loc[ok, "z_share"], s=8, alpha=0.35, color=C_MAIN)
    flagged = neigh[neigh["flag"]]
    ax.scatter(flagged["z_turnout"], flagged["z_share"], s=26, color=C_ACC,
               label=label(lang, "neigh_flag", n=len(flagged)))
    # подписи вразбежку, чтобы не накладывались
    for i, (_, r) in enumerate(flagged.reindex(flagged["z_share"].abs().sort_values(ascending=False).index).head(6).iterrows()):
        dy = 6 if i % 2 == 0 else -11
        ax.annotate(str(r["name"])[:20], (r["z_turnout"], r["z_share"]), fontsize=6,
                    textcoords="offset points", xytext=(5, dy))
    ax.margins(y=0.15)
    ax.axhline(0, color="k", lw=0.6); ax.axvline(0, color="k", lw=0.6)
    ax.set_xlabel(label(lang, "neigh_x"))
    ax.set_ylabel(label(lang, "neigh_y"))
    ax.set_title(label(lang, "neigh_ttl"), fontsize=9)
    ax.legend(fontsize=7, loc="lower right")
    return _save(fig, out_dir, "neighbors_outliers.png")


def plot_swing(swing: pd.DataFrame, out_dir: Path, lang: str = "ru") -> Path:
    fig, ax = plt.subplots(figsize=(4.8, 3.8))
    ax.scatter(swing["d_turnout"], swing["d_share"], s=8, alpha=0.3, color=C_MAIN)
    fl = swing[swing["flag"]]
    ax.scatter(fl["d_turnout"], fl["d_share"], s=26, color=C_ACC,
               label=label(lang, "swing_flag", n=len(fl)))
    ax.axhline(0, color="k", lw=0.6); ax.axvline(0, color="k", lw=0.6)
    ax.set_xlabel(label(lang, "swing_x"))
    ax.set_ylabel(label(lang, "swing_y"))
    ax.set_title(label(lang, "swing_ttl"), fontsize=9)
    ax.legend(fontsize=7)
    return _save(fig, out_dir, "swing_previous.png")


def plot_ml_anomalies(anom: pd.DataFrame, out_dir: Path, lang: str = "ru") -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4))
    ax = axes[0]
    ok = anom["anomaly_score"].notna()
    ax.hist(anom.loc[ok, "anomaly_score"], bins=60, color=C_MAIN, alpha=0.8)
    thr = anom.loc[ok & anom["is_anomaly"], "anomaly_score"].min()
    if np.isfinite(thr):
        ax.axvline(thr, color=C_ACC, lw=1.2, label=label(lang, "ml_thr", t=f"{thr:.3f}"))
    ax.set_xlabel(label(lang, "ml_score_x"))
    ax.set_ylabel(label(lang, "n_units_y"))
    ax.set_title(label(lang, "ml_hist_ttl"), fontsize=9)
    ax.legend(fontsize=7)

    ax = axes[1]
    ax.scatter(anom.loc[ok, "turnout"], anom.loc[ok, "share_leader"], s=6, alpha=0.3, color=C_MAIN)
    top = anom[ok].nlargest(25, "anomaly_score")
    ax.scatter(top["turnout"], top["share_leader"], s=26, color=C_ACC, label=label(lang, "ml_top25"))
    ax.set_xlabel(label(lang, "turnout_x"))
    ax.set_ylabel(label(lang, "leader_pct_y"))
    ax.set_title(label(lang, "ml_plane_ttl"), fontsize=9)
    ax.legend(fontsize=7)
    return _save(fig, out_dir, "ml_anomalies.png")


def plot_selftest(data: ElectionData, injected: ElectionData, leader: str, report,
                  out_dir: Path, lang: str = "ru") -> Path:
    from .shpilkin import votes_by_turnout

    centers, h_clean = votes_by_turnout(data, None, 0.5)
    _, h_inj = votes_by_turnout(injected, None, 0.5)
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4))
    ax = axes[0]
    ax.fill_between(centers, h_clean, step="mid", alpha=0.35, color=C_OK, label=label(lang, "st_original"))
    ax.plot(centers, h_inj, drawstyle="steps-mid", color=C_ACC, lw=1.2, label=label(lang, "st_inject"))
    ax.axvline(report.t_cut, color="k", ls="--", lw=1,
               label=label(lang, "st_cut", t=f"{report.t_cut:.0f}%"))
    ax.set_xlabel(label(lang, "turnout_x")); ax.set_ylabel(label(lang, "n_voted_y"))
    ax.set_title(label(lang, "st_inj_ttl"), fontsize=9)
    ax.legend(fontsize=7)

    ax = axes[1]
    vals = [report.clean_tail_party, report.injected_tail_party]
    ax.bar([label(lang, "st_clean_bar"), label(lang, "st_after_bar")], vals, color=[C_OK, C_ACC])
    ax.bar([label(lang, "st_after_bar")], [report.injected_added_ballots_party],
           width=0.4, color="none", edgecolor=C_MAIN, hatch="//",
           label=label(lang, "st_added", n=f"{report.injected_added_ballots_party:,}"))
    ax.set_ylim(0, max(vals) * 1.22)
    for i, v in enumerate(vals):
        ax.text(i, v, f"{v:,}", ha="center", va="bottom", fontsize=8)
    ax.set_ylabel(label(lang, "st_y"))
    ax.set_title(label(lang, "st_resp_ttl", g=f"{report.signal_growth:,.0f}"), fontsize=9)
    ax.legend(fontsize=7, loc="upper left")
    return _save(fig, out_dir, "selftest.png")


def plot_controls(elections: list[tuple[str, np.ndarray]], out_dir: Path, lang: str = "ru") -> Path:
    """Наложение распределений явки нескольких выборов (контроль)."""
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    for name, t in elections:
        ax.hist(t, bins=np.arange(0, 100.001, 0.5), histtype="step", lw=1.4, label=name, density=False)
    ax.set_xlabel(label(lang, "turnout_x"))
    ax.set_ylabel(label(lang, "controls_y"))
    ax.set_title(label(lang, "controls_ttl"), fontsize=9)
    ax.legend(fontsize=7)
    return _save(fig, out_dir, "controls_turnout.png")
