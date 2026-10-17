# Figures for the public page of the repository site — one set per language
# (pt, en), data from data/legislativas2025_mai/results_all.csv (freguesias,
# level=3). Run from the project directory:
#   uv run python scripts/build_site_figures.py
# Output: <repo>/site/portugal-2025/img/<lang>/{turnout,comet,selftest}.png
#         and the paradox figures (px_rules, px_counterfactuals,
#         px_autarquicas, px_runoff) — analysis: scripts/analyze_paradoxes.py
# Label numbers cross-checked against analysis/paradoxes/metrics.json
# (shpilkin, selftest) and analysis/metrics.json.
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas", "matplotlib"]
# ///
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "site" / "portugal-2025" / "img"
OUT.mkdir(parents=True, exist_ok=True)

BLUE = "#3b82c4"
DARK = "#16324f"
RED = "#c0392b"
GREEN = "#1e8e5a"
GREY = "#8a97a5"
# Honest-decline boundary — q99.5 of the control elections (see
# REPORT_statistical_fraud_analysis.md, section 1 and
# analysis/metrics.json → shpilkin.t_cut).
CUT = 78.6424600948544

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.edgecolor": GREY,
        "axes.labelcolor": DARK,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "xtick.color": DARK,
        "ytick.color": DARK,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
)

T = {
"en": {
    "turnout_title": "Turnout, parish by parish: one bell curve — and nothing above ~79%",
    "turnout_xlabel": "Turnout, % of registered voters",
    "turnout_ylabel": "Voters",
    "cut_label": "honest-decline boundary (78.6%, set by control elections)",
    "box": ("above the line: 7,779 voters = 0.13% of ballots cast.\n"
            "The 80–100% zone — exactly where ballot-stuffing lands — is empty."),
    "comet_title": "Turnout vs leading-party (AD) share — no “comet tail”",
    "comet_xlabel": "Turnout, %",
    "comet_ylabel": "AD share, % of votes cast",
    "comet_legend": "average by turnout group",
    "comet_box": ("The AD share stays flat across the whole turnout range\n"
                  "(weighted correlation −0.09); there is no separate cloud\n"
                  "of high-turnout, high-share parishes."),
    "selftest_title": "Self-test: inject synthetic stuffing — every alarm fires (signal ×18)",
    "selftest_ylabel": "estimated AD votes in the anomalous zone",
    "clean_label": "clean data\n14,589",
    "injected_label": "after injection\n255,496",
    "added_label": "ballots injected: 131,629",
},
"pt": {
    "turnout_title": "Afluência, freguesia a freguesia: uma curva em sino — e nada acima de ~79%",
    "turnout_xlabel": "Afluência, % dos eleitores inscritos",
    "turnout_ylabel": "Votantes",
    "cut_label": "fronteira do declínio honesto (78,6%, fixada pelas eleições de controlo)",
    "box": ("acima da linha: 7 779 votantes = 0,13% dos boletins.\n"
            "A faixa de 80–100% — precisamente onde cai a inflação de votos — está vazia."),
    "comet_title": "Afluência vs. percentagem do AD (líder) — sem «cauda de cometa»",
    "comet_xlabel": "Afluência, %",
    "comet_ylabel": "Percentagem do AD, % dos boletins",
    "comet_legend": "média por grupos de afluência",
    "comet_box": ("A percentagem do AD mantém-se estável em toda a gama de afluência\n"
                  "(correlação ponderada −0,09); não há nuvem separada\n"
                  "de afluência alta com percentagem alta."),
    "selftest_title": "Auto-teste: injeção de fraude sintética — todos os alarmes disparam (sinal ×18)",
    "selftest_ylabel": "votos estimados do AD na zona anómala",
    "clean_label": "dados limpos\n14 589",
    "injected_label": "após injeção\n255 496",
    "added_label": "boletins injetados: 131 629",
},
}

df = pd.read_csv(ROOT / "data" / "legislativas2025_mai" / "results_all.csv", encoding="utf-8-sig")
df = df[df["level"] == 3].copy()  # freguesias (mainland + Madeira + Azores)
party_cols = [c for c in df.columns if c.startswith("votes:")]
df["valid"] = df[party_cols].sum(axis=1)
# AD coalition: PPD/PSD.CDS-PP on the mainland, plus PPM in the Azores (cf. AGENTS.md).
df["ad"] = df["votes:PPD/PSD.CDS-PP"].fillna(0) + df["votes:PPD/PSD.CDS-PP.PPM"].fillna(0)
df["turnout"] = 100.0 * df["voted"] / df["registered_voters"]
df["ad_share"] = 100.0 * df["ad"] / df["voted"]

# Checksums against analysis/metrics.json. The Shpilkin tail is computed
# over 0.5 p.p. bins (bin centers > t_cut) — as in analysis-tool.
edges = np.arange(0.0, 100.0 + 0.5, 0.5)
centers = 0.5 * (edges[:-1] + edges[1:])
h_voted, _ = np.histogram(df["turnout"], bins=edges, weights=df["voted"])
h_ad, _ = np.histogram(df["turnout"], bins=edges, weights=df["ad"])
mask = centers > CUT
assert len(df) == 3092, len(df)
assert int(df["registered_voters"].sum()) == 9_265_493
assert int(df["voted"].sum()) == 5_965_446
assert int(h_voted[mask].sum()) == 7_779, int(h_voted[mask].sum())
assert int(h_ad[mask].sum()) == 2_980, int(h_ad[mask].sum())
print(f"checks ok: 3 092 parishes; tail zone: {int(h_voted[mask].sum()):,} voters "
      f"({h_voted[mask].sum()/df['voted'].sum()*100:.2f}%), AD {int(h_ad[mask].sum()):,}")


def fig_turnout(lang: str, tr: dict) -> None:
    fig, ax = plt.subplots(figsize=(9.6, 4.0), dpi=150)
    ax.hist(df["turnout"], bins=np.arange(0, 100.75, 0.75), weights=df["voted"],
            color=BLUE, alpha=0.85, edgecolor="white", linewidth=0.3)
    ax.axvline(CUT, color=RED, linestyle="--", linewidth=1.6)
    ax.text(CUT - 1.2, ax.get_ylim()[1] * 0.94, tr["cut_label"], color=RED,
            fontsize=10, ha="right")
    ax.text(
        0.865,
        0.58,
        tr["box"],
        transform=ax.transAxes,
        color=DARK,
        fontsize=10,
        ha="center",
        bbox=dict(boxstyle="round,pad=0.4", fc="#f4f7fa", ec=GREY, lw=0.8),
    )
    ax.set_xlim(0, 100)
    ax.set_xlabel(tr["turnout_xlabel"])
    ax.set_ylabel(tr["turnout_ylabel"])
    ax.set_title(tr["turnout_title"])
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / lang / "turnout.png")
    plt.close(fig)


def fig_comet(lang: str, tr: dict) -> None:
    fig, ax = plt.subplots(figsize=(9.6, 4.8), dpi=150)
    ax.scatter(df["turnout"], df["ad_share"], s=df["registered_voters"] / 450,
               color=BLUE, alpha=0.18, linewidths=0)
    bins = list(range(30, 85, 3))
    d = df[(df["turnout"] >= bins[0]) & (df["turnout"] < bins[-1])].copy()
    d["bin"] = pd.cut(d["turnout"], bins)
    m = d.groupby("bin", observed=True).apply(
        lambda g: pd.Series(
            {
                "x": (g["turnout"] * g["registered_voters"]).sum() / g["registered_voters"].sum(),
                "y": (g["ad_share"] * g["voted"]).sum() / g["voted"].sum(),
                "n": len(g),
            }
        ),
        include_groups=False,
    )
    m = m[m["n"] >= 20]
    ax.plot(m["x"], m["y"], color=DARK, linewidth=2.6, marker="o", markersize=5, zorder=5,
            label=tr["comet_legend"])
    ax.text(
        0.03,
        0.95,
        tr["comet_box"],
        transform=ax.transAxes,
        fontsize=10,
        va="top",
        color=DARK,
        bbox=dict(boxstyle="round,pad=0.45", fc="#f4f7fa", ec=GREY, lw=0.8),
    )
    ax.legend(loc="upper right", fontsize=10, framealpha=0.9)
    ax.set_xlim(25, 85)
    ax.set_ylim(0, 80)
    ax.set_xlabel(tr["comet_xlabel"])
    ax.set_ylabel(tr["comet_ylabel"])
    ax.set_title(tr["comet_title"])
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / lang / "comet.png")
    plt.close(fig)


def fig_selftest(lang: str, tr: dict) -> None:
    # Numbers from analysis/metrics.json → selftest (injection: +10% of
    # parishes, turnout +5–35 p.p., 60–95% of the added ballots for AD).
    clean, added, injected = 14_589, 131_629, 255_496
    fig, ax = plt.subplots(figsize=(9.6, 4.0), dpi=150)
    ax.bar([0], [clean], width=0.55, color=GREEN, zorder=3)
    ax.bar([1], [injected], width=0.55, color=RED, zorder=3)
    ax.bar([1], [added], width=0.55, facecolor="none", edgecolor=BLUE,
           hatch="///", linewidth=1.4, zorder=4, label=tr["added_label"])
    ax.text(0, clean + 6000, tr["clean_label"], ha="center", fontsize=11, color=DARK)
    ax.text(1, injected + 6000, tr["injected_label"], ha="center", fontsize=11, color=DARK)
    ax.set_xticks([0, 1], ["", ""])
    ax.set_xlim(-0.6, 1.6)
    ax.set_ylim(0, 300_000)
    ax.set_ylabel(tr["selftest_ylabel"])
    ax.set_title(tr["selftest_title"])
    ax.legend(loc="upper left", fontsize=10, framealpha=0.9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / lang / "selftest.png")
    plt.close(fig)


# ── paradox figures (analysis/paradoxes/metrics.json) ────────────────────────

PX = json.loads((ROOT / "analysis" / "paradoxes" / "metrics.json").read_text())
TABLES_CSV = ROOT / "analysis" / "paradoxes" / "tables" / "autarquicas_frustrated.csv"

ORANGE = "#e0812f"   # AD / centre-right bloc
PINK = "#cc4b5e"     # PS / left bloc
NAVY = "#2c5f8a"     # CH
YELLOW = "#c9a227"   # IL
LIGHT = "#d7dee5"    # others


def pct(v: float, lang: str) -> str:
    s = f"{v:.1f}".replace(".", "," if lang == "pt" else ".")
    return f"{s}%"


PXT = {
"en": {
    "rules_title": "Same votes, three counting rules — the winner depends on the rule",
    "rules_a_title": "PS vs CH: who is ahead?",
    "rules_a_cats": ["national votes", "D'Hondt seats, 22 círculos (actual)",
                     "seats, one national district"],
    "rules_a_ann": "PS ahead by 4,313 votes\nCH ahead by 2 seats\ntie",
    "rules_b_title": "AD: 33% of the votes become…",
    "rules_b_cats": ["votes", "D'Hondt\nseats", "FPTP:\nconcelhos", "FPTP:\nfreguesias"],
    "rules_xlabel": "% (votes or seats)",
    "cf_title": "Coalition arithmetic — seats for the same votes under alternative alliances",
    "cf_rows": ["actual result\n(22 D'Hondt círculos)", "AD + CH united right",
                "left united\n(PS+BE+PCP+PAN+L)", "IL does not run",
                "AD split PSD/CDS\n(as in 2022)"],
    "cf_majority": "majority: 116",
    "cf_ann_1": "AD+CH: 154 — constitutional majority",
    "cf_ann_2": "united left (84) overtakes AD (81)",
    "cf_ann_3": "the AD split costs it 4 seats",
    "cf_seg_ur": "AD / AD+CH", "cf_seg_ul": "PS / united left", "cf_seg_ch": "CH",
    "cf_seg_il": "IL", "cf_seg_rest": "others",
    "cf_xlabel": "seats (of 230)",
    "aut_title": "Real plurality races (câmaras, 12.10.2025):\nthe winning list vs the opposing bloc",
    "aut_sub": "of 308 câmaras: 142 winners (46%) without a majority;\nin 49 the opposing bloc combined has more votes",
    "aut_w": "winning list", "aut_b": "opposing bloc combined",
    "aut_xlabel": "% of valid votes",
    "run_c_title": "First round: the eliminated centre\nheld 39.8% of valid votes",
    "run_c_top2": "advanced to the runoff",
    "run_c_out": "eliminated — 39.8% combined",
    "run_c_xlabel": "% of valid votes, 1st round (18.01.2026)",
    "run_b_title": "Between the rounds, blank and\nnull ballots surged",
    "run_b_l1": "1st round", "run_b_l2": "runoff (08.02.2026)",
    "run_b_blank": "blank", "run_b_null": "null",
    "run_b_ylabel": "ballots",
    "run_b_note": "blank ×2.9 (+113,538), null +33,316,\nturnout fell by 262,687",
},
"pt": {
    "rules_title": "Os mesmos votos, três regras de contagem — o vencedor depende da regra",
    "rules_a_title": "PS vs. CH: quem está à frente?",
    "rules_a_cats": ["votos nacionais", "mandatos D'Hondt, 22 círculos (real)",
                     "mandatos, um círculo único nacional"],
    "rules_a_ann": "PS à frente por 4 313 votos\nCH à frente por 2 mandatos\nempate",
    "rules_b_title": "O AD: 33% dos votos transformam-se em…",
    "rules_b_cats": ["votos", "mandatos\nD'Hondt", "FPTP:\nconcelhos", "FPTP:\nfreguesias"],
    "rules_xlabel": "% (votos ou mandatos)",
    "cf_title": "Aritmética das coligações — mandatos com os mesmos votos sob alianças alternativas",
    "cf_rows": ["resultado real\n(22 círculos D'Hondt)", "AD + CH unidos",
                "esquerda unida\n(PS+BE+PCP+PAN+L)", "sem o IL",
                "AD dividida PSD/CDS\n(como em 2022)"],
    "cf_majority": "maioria: 116",
    "cf_ann_1": "AD+CH: 154 — maioria constitucional",
    "cf_ann_2": "a esquerda unida (84) ultrapassa o AD (81)",
    "cf_ann_3": "a divisão do AD custa-lhe 4 mandatos",
    "cf_seg_ur": "AD / AD+CH", "cf_seg_ul": "PS / esquerda unida", "cf_seg_ch": "CH",
    "cf_seg_il": "IL", "cf_seg_rest": "outras",
    "cf_xlabel": "mandatos (de 230)",
    "aut_title": "Corridas maioritárias reais (câmaras, 12.10.2025):\nlista vencedora vs. bloco oposto",
    "aut_sub": "em 308 câmaras: 142 vencedores (46%) sem maioria;\nem 49 o bloco oposto agregado tem mais votos",
    "aut_w": "lista vencedora", "aut_b": "bloco oposto agregado",
    "aut_xlabel": "% dos votos válidos",
    "run_c_title": "1.ª volta: o centro eliminado\ntinha 39,8% dos votos válidos",
    "run_c_top2": "passaram à 2.ª volta",
    "run_c_out": "eliminados — 39,8% em conjunto",
    "run_c_xlabel": "% dos votos válidos, 1.ª volta (18.01.2026)",
    "run_b_title": "Entre as duas voltas, brancos\ne nulos dispararam",
    "run_b_l1": "1.ª volta", "run_b_l2": "2.ª volta (08.02.2026)",
    "run_b_blank": "brancos", "run_b_null": "nulos",
    "run_b_ylabel": "boletins",
    "run_b_note": "brancos ×2,9 (+113 538), nulos +33 316,\nabstenção +262 687",
},
}

# checksums against the analysis
assert PX["referendum"]["ps_seats"] == 58 and PX["referendum"]["ch_seats"] == 60
assert PX["fptp"]["freguesias"]["wins"]["AD"] == 2343
assert PX["autarquicas"]["frustrated_count"] == 49
assert PX["presidential"]["centrists_share"] > 0.39


def _party_color(family: str) -> str:
    return {"socialist": PINK, "left": PINK, "communist": "#8f2d3c",
            "green": PINK, "right": ORANGE, "far_right": NAVY,
            "liberal": YELLOW}.get(family, GREY)


def fig_px_rules(lang: str, t: dict) -> None:
    ref = PX["referendum"]
    freg, conc = PX["fptp"]["freguesias"], PX["fptp"]["concelhos"]
    fig, (axa, axb) = plt.subplots(1, 2, figsize=(9.6, 4.2), dpi=150,
                                   gridspec_kw={"width_ratios": [1.05, 1]})
    # panel A — PS vs CH under three rules (MAI valid total: 6,057,972)
    rest_valid = 6_057_972 - ref["ps_votes"] - ref["ch_votes"]
    assert rest_valid == 3_177_897
    total = ref["ps_votes"] + ref["ch_votes"] + rest_valid
    rules = [
        (100 * ref["ps_votes"] / total, 100 * ref["ch_votes"] / total),
        (100 * ref["ps_seats"] / 230, 100 * ref["ch_seats"] / 230),
        (56 / 230 * 100, 56 / 230 * 100),
    ]
    assert abs(rules[0][0] - 23.8) < 0.1 and abs(rules[1][1] - 26.1) < 0.1
    y = list(range(len(rules)))
    h = 0.32
    for k, (color, name) in enumerate(((PINK, "PS"), (NAVY, "CH"))):
        vals = [r[k] for r in rules]
        axa.barh([i + (k - 0.5) * h for i in y], vals, height=h, color=color,
                 alpha=0.9, zorder=3, label=name)
        for i, v in enumerate(vals):
            axa.text(v + 0.5, i + (k - 0.5) * h, pct(v, lang), va="center",
                     fontsize=9.5, color=color, fontweight="bold")
    axa.axvline(50, color=DARK, linestyle="--", linewidth=1.2, zorder=2)
    anns = t["rules_a_ann"].split("\n")
    for i, a in enumerate(anns):
        axa.text(99, i + 0.42, a, fontsize=8.8, color=DARK, ha="right",
                 fontweight="bold" if i < 2 else "normal")
    axa.set_yticks(y, t["rules_a_cats"], fontsize=9.5)
    axa.invert_yaxis()
    axa.set_xlim(0, 100)
    axa.set_xlabel(t["rules_xlabel"], fontsize=10)
    axa.set_title(t["rules_a_title"], fontsize=11.5)
    axa.legend(fontsize=9.5, framealpha=0.9, loc="upper center",
               bbox_to_anchor=(0.5, -0.22), ncol=2)
    axa.spines[["top", "right"]].set_visible(False)
    # panel B — AD amplification
    ad = [33.15, 100 * 91 / 230,
          100 * conc["wins"]["AD"] / conc["n_districts"],
          100 * freg["wins"]["AD"] / freg["n_districts"]]
    assert abs(ad[3] - 75.8) < 0.1
    cols = [LIGHT, ORANGE, ORANGE, ORANGE]
    axb.bar(range(4), ad, width=0.62, color=cols, zorder=3)
    for i, v in enumerate(ad):
        axb.text(i, v + 1.6, pct(v, lang), ha="center", fontsize=10.5,
                 color=DARK, fontweight="bold")
    axb.axhline(50, color=DARK, linestyle="--", linewidth=1.2, zorder=2)
    axb.set_xticks(range(4), t["rules_b_cats"], fontsize=8.6)
    axb.set_ylim(0, 92)
    axb.set_ylabel(t["rules_xlabel"], fontsize=10)
    axb.set_title(t["rules_b_title"], fontsize=11.5)
    axb.spines[["top", "right"]].set_visible(False)
    fig.suptitle(t["rules_title"], fontsize=13, fontweight="bold", color=DARK)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(OUT / lang / "px_rules.png")
    plt.close(fig)


def fig_px_counterfactuals(lang: str, t: dict) -> None:
    cf = PX["counterfactuals"]
    # stacked segments per scenario: [UR/AD, PS/UL, CH, IL, rest] summing to 230
    scen = [
        ("actual", [91, 58, 60, 9, 12], None),
        ("AD+CH united right", [154, 57, 0, 9, 10], "cf_ann_1"),
        ("Left united (PS+BE+PCP+PAN+L)", [81, 84, 55, 9, 1], "cf_ann_2"),
        ("IL does not run", [95, 60, 62, 0, 13], None),
        ("AD splits (PSD/CDS as in 2022)", [87, 61, 61, 9, 12], "cf_ann_3"),
    ]
    tot = {k: sum(v) for k, v in
           ((s[0], s[1]) for s in scen)}
    assert set(tot.values()) == {230}, tot
    colors = [ORANGE, PINK, NAVY, YELLOW, LIGHT]
    fig, ax = plt.subplots(figsize=(9.6, 4.8), dpi=150)
    y = list(range(len(scen)))
    left = np.zeros(len(scen))
    for k in range(5):
        vals = np.array([s[1][k] for s in scen], dtype=float)
        ax.barh(y, vals, left=left, height=0.6, color=colors[k],
                alpha=0.92, zorder=3, label=t[f"cf_seg_{['ur','ul','ch','il','rest'][k]}"])
        for i, v in enumerate(vals):
            if v >= 25:
                ax.text(left[i] + v / 2, i, f"{v:.0f}", ha="center", va="center",
                        fontsize=10, fontweight="bold",
                        color="white" if k != 4 else DARK, zorder=5)
        left += vals
    ax.axvline(116, color=DARK, linestyle="--", linewidth=1.6, zorder=4)
    ax.text(116, len(scen) - 0.32, t["cf_majority"], ha="center", fontsize=9.5,
            color=DARK)
    for i, s in enumerate(scen):
        if s[2]:
            ax.text(233, i, t[s[2]], fontsize=9.6, color=DARK,
                    va="center", fontweight="bold")
    ax.set_yticks(y, t["cf_rows"], fontsize=9.5)
    ax.invert_yaxis()
    ax.set_ylim(len(scen) - 0.25, -1.15)
    ax.set_xlim(0, 300)
    ax.set_xticks(range(0, 231, 50))
    ax.set_xlabel(t["cf_xlabel"], fontsize=10)
    ax.set_title(t["cf_title"], fontsize=13, fontweight="bold", color=DARK, pad=14)
    ax.legend(fontsize=9.5, framealpha=0.9, ncol=5, loc="upper center",
              bbox_to_anchor=(0.42, -0.14))
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / lang / "px_counterfactuals.png", bbox_inches="tight")
    plt.close(fig)


def fig_px_autarquicas(lang: str, t: dict) -> None:
    aut = pd.read_csv(TABLES_CSV, encoding="utf-8-sig")
    aut = aut[aut["frustrated"]].sort_values("registered", ascending=False).head(10)
    aut = aut.iloc[::-1]  # largest at the top
    fig, ax = plt.subplots(figsize=(9.6, 5.2), dpi=150)
    y = list(range(len(aut)))
    valid = aut["winner_votes"] / aut["winner_share"]
    bw = 100 * aut["loser_bloc_votes"] / valid
    wsh = 100 * aut["winner_share"]
    for i, (b, w) in enumerate(zip(bw, wsh)):
        ax.plot([w, b], [i, i], color=GREY, linewidth=2.2, alpha=0.55, zorder=2)
    ax.scatter(wsh, y, s=95, color=[_party_color(f) for f in aut["winner_family"]],
               zorder=3, label=t["aut_w"])
    ax.scatter(bw, y, s=95, color=DARK, zorder=3, label=t["aut_b"])
    for i, (b, w, name) in enumerate(zip(bw, wsh, aut["winner"])):
        ax.text(w - 1.2, i + 0.3, pct(w, lang), ha="right", fontsize=8.8,
                color=DARK)
        ax.text(b + 1.2, i + 0.3, pct(b, lang), ha="left", fontsize=8.8,
                color=DARK)
    ax.set_yticks(y, [f"{c}  ·  {name}" for c, name in
                      zip(aut["concelho"], aut["winner"])], fontsize=9.5)
    ax.axvline(50, color=DARK, linestyle="--", linewidth=1.4, zorder=1)
    ax.set_xlim(20, 72)
    ax.set_xlabel(t["aut_xlabel"], fontsize=10)
    ax.set_title(f"{t['aut_title']}\n{t['aut_sub']}", fontsize=11.5,
                 fontweight="bold", color=DARK)
    ax.legend(fontsize=9.5, framealpha=0.9, loc="upper center",
              bbox_to_anchor=(0.5, -0.14), ncol=2)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / lang / "px_autarquicas.png")
    plt.close(fig)


def fig_px_runoff(lang: str, t: dict) -> None:
    pres = PX["presidential"]
    r1 = pres["first_round"]
    valid1 = pres["valid1"]
    cands = [("Seguro", PINK), ("Ventura", NAVY), ("Cotrim", YELLOW),
             ("Gouveia", "#4a9d8f"), ("Mendes", ORANGE)]
    others = valid1 - sum(r1[c] for c, _ in cands)
    fig, (axa, axb) = plt.subplots(1, 2, figsize=(9.6, 4.4), dpi=150,
                                   gridspec_kw={"width_ratios": [1.25, 1]})
    y = list(range(len(cands) + 1))
    vals = [100 * r1[c] / valid1 for c, _ in cands] + [100 * others / valid1]
    assert abs(sum(vals[:3]) - 70.5) < 0.5
    cols = [c for _, c in cands] + [LIGHT]
    axa.barh(y, vals, color=cols, alpha=0.92, height=0.62, zorder=3)
    for i, v in enumerate(vals):
        axa.text(v + 0.6, i, pct(v, lang), va="center", fontsize=10,
                 color=DARK, fontweight="bold")
    axa.axhline(1.5, color=DARK, linewidth=1.6, zorder=4)
    axa.text(34.4, 0.62, t["run_c_top2"], fontsize=9.5, color=DARK,
             fontweight="bold", ha="right")
    axa.text(34.4, 3.42, t["run_c_out"], fontsize=9.5, color="#7a3b46",
             fontweight="bold", ha="right")
    axa.set_yticks(y, [c for c, _ in cands] + [t["cf_seg_rest"]], fontsize=10.5)
    axa.invert_yaxis()
    axa.set_xlim(0, 35)
    axa.set_xlabel(t["run_c_xlabel"], fontsize=10)
    axa.set_title(t["run_c_title"], fontsize=11)
    axa.spines[["top", "right"]].set_visible(False)
    # panel B — blank / null surge
    x = [0, 1]
    width = 0.32
    for k, (key, lab, color) in enumerate((
            ("blank", t["run_b_blank"], GREY), ("null", t["run_b_null"], "#5b6b7b"))):
        v1, v2 = r1[key], pres["second_round"][key]
        axb.bar([i + (k - 0.5) * width for i in x], [v1, v2], width=width,
                color=color, alpha=0.9, zorder=3, label=lab)
        for i, v in enumerate((v1, v2)):
            axb.text(i + (k - 0.5) * width, v + 4000, f"{v / 1000:.0f}k",
                     ha="center", fontsize=9.5, color=DARK)
    axb.set_xticks(x, [t["run_b_l1"], t["run_b_l2"]], fontsize=9.5)
    axb.set_ylim(0, 212000)
    axb.set_ylabel(t["run_b_ylabel"], fontsize=10)
    axb.set_title(t["run_b_title"], fontsize=11)
    axb.legend(fontsize=9.5, framealpha=0.9, loc="center left")
    axb.text(0.98, 0.97, t["run_b_note"], ha="right", va="top", fontsize=9,
             color=DARK, transform=axb.transAxes)
    axb.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / lang / "px_runoff.png")
    plt.close(fig)


for lang, tr in T.items():
    (OUT / lang).mkdir(parents=True, exist_ok=True)
    fig_turnout(lang, tr)
    fig_comet(lang, tr)
    fig_selftest(lang, tr)
    pxt = PXT[lang]
    fig_px_rules(lang, pxt)
    fig_px_counterfactuals(lang, pxt)
    fig_px_autarquicas(lang, pxt)
    fig_px_runoff(lang, pxt)
    print(f"{lang}: turnout, comet, selftest, px_rules, px_counterfactuals, "
          f"px_autarquicas, px_runoff -> site/portugal-2025/img/{lang}/")
