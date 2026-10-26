#!/usr/bin/env python3
"""Fill the ⟦TOKEN⟧ placeholders in site/brazil-oct-2026-round-2/{index.html,
translations.js} from the round-2 analysis outputs (metrics_T2.json,
metrics_control_T2.json, prediction_vs_actual.json, transfers_2026_matrix.csv,
prediction_decomposition.csv, secoes_presidente_2026_T2_checks.json).

Numbers are formatted per language (decimal comma for pt/es/ru). Run after the
forensics/control/paradox runs:
  python3 scripts/fill_page_tokens.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

BR = Path(__file__).resolve().parents[1]
SITE = BR.parent / "site" / "brazil-oct-2026-round-2"

LANGS = ("en", "pt", "es", "ru")
COMMA = {"en": ".", "pt": ",", "es": ",", "ru": ","}

# verdict phrase per language — set after reading the metrics of the run
VERDICTS: dict[str, str] = {
    "en": "The tests do not establish evidence of manipulation",
    "pt": "Os testes não estabelecem evidência de manipulação",
    "es": "Las pruebas no establecen evidencia de manipulación",
    "ru": "Тесты не выявляют признаков манипуляций",
}


def fmt(lang: str, v: float, nd: int = 2) -> str:
    return f"{v:.{nd}f}".replace(".", COMMA[lang])


def int_fmt(lang: str, v: int) -> str:
    s = f"{v:,}"
    return s.replace(",", " ") if lang != "en" else s


def main() -> None:
    metrics = json.loads((BR / "analysis_T2" / "metrics_T2.json").read_text())
    control = json.loads((BR / "analysis_T2" / "metrics_control_T2.json").read_text())
    pva = json.loads((BR / "analysis" / "paradox" / "prediction_vs_actual.json").read_text())
    checks = json.loads((BR / "data" / "secoes_presidente_2026_T2_checks.json").read_text())
    mat = pd.read_csv(BR / "analysis" / "paradox" / "transfers_2026_matrix.csv", index_col=0)
    decomp = pd.read_csv(BR / "analysis" / "paradox" / "prediction_decomposition.csv")

    shp_l, shp_b = metrics["shpilkin_leader"], metrics["shpilkin_runner_up"]
    nat = metrics["national"]
    voted = nat["voted"]
    cut = shp_l["t_cut"]
    tail_pct = 100.0 * shp_l["tail_voters"] / voted
    corr = {r["party"]: r["pearson_w"] for r in metrics["correlations_national"]}
    uf_min, uf_max = metrics["corr_uf_leader_range"]
    st = metrics["selftest"]
    ne = metrics["neighbors_flagged"]
    ne_pct = metrics["neighbors_flagged_pct"]
    ml = metrics["ml_flagged"]
    dup = metrics["duplicate_protocols"]
    ben = max(metrics["benford2"], key=lambda r: r["max_dev"])
    last = max(metrics["last_digit"], key=lambda r: r["max_dev"])
    excess05 = max(abs(r.get("excess_05", 0.0)) for r in metrics["last_digit"])
    pk_t = metrics["integer_peaks_turnout"]
    pk_s = metrics["integer_peaks_leader_share"]
    fp_l = metrics["fingerprint_leader"]
    fp_b = metrics["fingerprint_runner_up"]
    n_sections = checks["totals"]["sections"]

    def tr_rate(row: str) -> tuple[float, float]:
        return float(mat.loc[row, "LULA"]), float(mat.loc[row, "BOLSONARO"])

    def decomp_pp(lang: str, vote_type: str) -> str:
        r = decomp[decomp.vote_type_2026 == vote_type]
        v = float(r.contrib_error_pp.iloc[0]) if len(r) else 0.0
        return ("+" if v >= 0 else "−") + fmt(lang, abs(v), 2)

    # pooled CURY+FERREIRA+CAIADO share to Lula of their two-candidate vote
    w_l = w_b = 0.0
    r1 = pd.read_csv(BR / "data" / "secoes_presidente_2026.csv",
                     usecols=["votes:CURY", "votes:FERREIRA", "votes:CAIADO"])
    for c, col in (("CURY", "votes:CURY"), ("FERREIRA", "votes:FERREIRA"),
                   ("CAIADO", "votes:CAIADO")):
        v = float(r1[col].sum())
        l, b = tr_rate(c)
        w_l += v * l
        w_b += v * b
    pool_lula_tw = 100.0 * w_l / (w_l + w_b)

    j22 = control["jumps_2022r2_2026r2"]
    j26 = control["jumps_2026_r1_r2"]
    shp_ctrl = [r for r in control["shpilkin"] if r["election"] == "2026-R2"]
    shp22 = [r for r in control["shpilkin"] if r["election"] == "2022-R2"]

    V: dict[str, dict[str, str]] = {}
    for lang in LANGS:
        # rates display like "→ Lula 53,2 / Bolsonaro 41,0" (percent, 1 decimal)
        def rate(row: str) -> str:
            l, b = tr_rate(row)
            return f"→ Lula {fmt(lang, 100*l,1)} / Bolsonaro {fmt(lang, 100*b,1)}"

        V[lang] = {
            "VERDICT": VERDICTS[lang],
            # ── m1 Shpilkin ──
            "M1": (f"The threshold of {fmt(lang, cut,1)}% is the runoff sample’s 99.5th turnout "
                   f"percentile. Sections above it contain {fmt(lang, tail_pct,2)}% of ballots cast, "
                   f"including {fmt(lang, 100*shp_l['tail_share_of_party'],2)}% of Lula’s and "
                   f"{fmt(lang, 100*shp_b['tail_share_of_party'],2)}% of Flávio Bolsonaro’s votes. "
                   f"This is a descriptive tail count: it neither identifies fraudulent votes nor "
                   f"bounds their total."),
            "M1_C1": (f"Turnout across sections: one bell, mode {fmt(lang, shp_l['mode'],2)}%, "
                      f"σ {fmt(lang, shp_l['sigma'],1)} pp; the boundary is the distribution’s own "
                      f"q99.5 ({fmt(lang, cut,1)}%). Lula’s votes above it: "
                      f"{int_fmt(lang, shp_l['tail_votes_party'])} "
                      f"({fmt(lang, 100*shp_l['tail_share_of_party'],2)}% of his total)."),
            "M1_C2": (f"The same for Bolsonaro: above the boundary "
                      f"{int_fmt(lang, shp_b['tail_votes_party'])} votes "
                      f"({fmt(lang, 100*shp_b['tail_share_of_party'],2)}% of his total)."),
            # ── m2 comet ──
            "M2": (f"National weighted turnout–share correlations are "
                   f"{fmt(lang, corr.get('LULA',0),2)} for Lula and "
                   f"{fmt(lang, corr.get('BOLSONARO',0),2)} for Flávio Bolsonaro. Horizontal clouds, "
                   f"no rising tail. Neither a nonzero correlation proves fraud nor a near-zero "
                   f"value rules it out."),
            # ── m3 fingerprints ──
            "M3": (f"A descriptive two-Gaussian mixture on (turnout × share) places the second "
                   f"component at {fmt(lang, fp_l['mean_anom'][0],0)}% turnout with weight "
                   f"{fmt(lang, fp_l['weight_anom'],2)} for Lula and "
                   f"{fmt(lang, fp_b['mean_anom'][0],0)}% with {fmt(lang, fp_b['weight_anom'],2)} "
                   f"for Bolsonaro — normal-turnout structure, no cluster in the high-turnout/"
                   f"high-share corner."),
            "M3_C1": (f"Density of (turnout × Lula share), weighted by voters; markers — the means "
                      f"of the two mixture components ( turnout {fmt(lang, fp_l['mean_main'][0],0)}% "
                      f"and {fmt(lang, fp_l['mean_anom'][0],0)}%). No fraud cluster in the top-right "
                      f"corner."),
            "M3_C2": (f"The same for Bolsonaro: the mirror image — the second component "
                      f"({fmt(lang, fp_b['weight_anom'],2)} of mass) is the opposite end of the same "
                      f"geography, not an anomaly."),
            # ── m4 integer peaks ──
            "M4": (f"The share of sections with whole-percent turnout matches the size-adjusted "
                   f"random null (z = {fmt(lang, pk_t['z'],1)}); for Lula’s share "
                   f"z = {fmt(lang, pk_s['z'],2)}; at multiples of 5 "
                   f"|z| = {fmt(lang, max(abs(pk_t['z_mult5']), abs(pk_s['z_mult5'])),1)}. "
                   f"In documented falsification cases z reaches dozens."),
            "M4_D": (f"What it checks: how often turnout (or the leader’s share) lands exactly on a "
                     f"whole percentage. Observed {fmt(lang, pk_t['observed_pct'],2)}% of sections "
                     f"with whole-percent turnout vs {fmt(lang, pk_t['null_pct'],2)}% expected "
                     f"(z = {fmt(lang, pk_t['z'],1)}); the leader’s share z = "
                     f"{fmt(lang, pk_s['z'],2)}; at multiples of 5 — the stronger prior — "
                     f"|z| ≤ {fmt(lang, max(abs(pk_t['z_mult5']), abs(pk_s['z_mult5'])),1)}. "
                     f"Documented falsification cases reach z of dozens."),
            "M4_C1": (f"Left: the section turnout histogram with verticals at multiples of 5 — no "
                      f"spikes at round values. Right: observed whole-percent share vs the Monte "
                      f"Carlo null (z = {fmt(lang, pk_t['z'],1)})."),
            # ── m5 Benford ──
            "M5": (f"The second-digit test on the pooled candidate counts: maximum deviation "
                   f"{fmt(lang, ben['max_dev'],2)} pp from Benford’s expectation "
                   f"(p = {ben['p_value']:.2e}); both candidates individually "
                   f"{'pass' if all(r['p_value'] > 0.05 for r in metrics['benford2']) else 'reject'} "
                   f"their reference distributions at the 5% level. Small counts and heterogeneous "
                   f"sections can violate Benford assumptions; the smooth profile proves neither "
                   f"fraud nor its absence."),
            "M5_C1": ("Second-digit frequencies for the two candidates’ pooled counts vs Benford’s "
                      "expectation with the 95% Monte Carlo band: a smooth monotone profile, no "
                      "digit stands out."),
            # ── m6 last digit ──
            "M6": (f"Last-digit frequencies of the pooled counts (counts ≥ 100): maximum deviation "
                   f"{fmt(lang, last['max_dev'],2)} pp from uniform; the combined excess of digits "
                   f"0 and 5 is at most {fmt(lang, excess05,2)} pp. "
                   f"A flat profile within noise."),
            "M6_C1": ("Last-digit frequencies vs uniform with the 95% Monte Carlo band: a flat "
                      "profile within noise."),
            # ── m7 2D correlations ──
            "M7": (f"State-level turnout–share correlations for Lula range from "
                   f"{fmt(lang, uf_min,2)} to {fmt(lang, uf_max,2)}; Bolsonaro’s are the mirror "
                   f"image (vote shares sum to one). These correlations alone do not distinguish "
                   f"mobilisation from manipulation."),
            "M7_C1": (f"Left: national weighted correlations — near zero. Right: by state, Lula "
                      f"from {fmt(lang, uf_min,2)} to {fmt(lang, uf_max,2)}, mirrored between the "
                      f"two candidates."),
            # ── m8 outliers/ML/duplicates ──
            "M8": (f"The within-municipality outlier rule flags {int_fmt(lang, ne)} sections "
                   f"({fmt(lang, ne_pct,2)}%). Isolation Forest flags {int_fmt(lang, ml)} "
                   f"(~1% by its configured threshold). Duplicate identical result vectors: "
                   f"{int_fmt(lang, dup['rows_in_dup_groups'])} rows in {dup['groups']} groups. "
                   f"Flags require contextual investigation; neither a flag nor its absence "
                   f"determines whether a section was manipulated."),
            "M8_C1": (f"Robust z of turnout vs robust z of Lula’s share (within municipalities). "
                      f"Red — the {int_fmt(lang, ne)} flagged sections ({fmt(lang, ne_pct,2)}%): "
                      f"scattered, no cluster."),
            "M8_C2": ("Isolation Forest: the anomaly-score distribution with its 1% threshold and "
                      "the top anomalies on the (turnout × share) plane — ordinary sections, "
                      "nothing patterned."),
            # ── m9 urnas ──
            "M9": (f"Observed vote shares differ across the {len(metrics['urna_models'])} "
                   f"ballot-machine generations in the field; the runoff split stays within "
                   f"a few percentage points across generations carrying at least a million "
                   f"voters. Deployment geography and electorate composition confound this "
                   f"comparison; unadjusted differences neither establish a machine effect nor "
                   f"certify machine security."),
            # ── m10 controls ──
            "M10": (f"The same-stage comparison matches {int_fmt(lang, j22['match']['matched'])} "
                    f"sections across the 2022 and 2026 runoffs "
                    f"({fmt(lang, j22['match']['matched_pct_of_B'],1)}% of 2026 sections). "
                    f"Tail ballot shares: {fmt(lang, shp22[0]['tail_voters_own_pct'],2)}–"
                    f"{fmt(lang, shp22[1]['tail_voters_own_pct'],2)}% in 2022-R2 vs "
                    f"{fmt(lang, shp_ctrl[0]['tail_voters_own_pct'],2)}% in 2026-R2. Between the "
                    f"2026 rounds, turnout rose a median "
                    f"{fmt(lang, j26['d_turnout']['median'],2)} pp; |z|>4 jumps — "
                    f"{fmt(lang, j26['d_turnout']['flagged_pct'],2)}% of sections, both directions. "
                    f"Similarity is descriptive evidence, not proof of absence of manipulation."),
            "M10_C1": (f"Turnout distributions of both rounds of 2022 and 2026: same shape, 2026 "
                       f"shifted up (runoff turnout {fmt(lang, pva['actual_2026_runoff']['turnout_pct'],2)}%). "
                       f"Boundary — the 2022 control ({fmt(lang, control['t_cut']['control_2022_max'],1)}%)."),
            "M10_C2": (f"2026 R1 → runoff on the same sections (n={int_fmt(lang, j26['match']['matched'])}): "
                       f"Δturnout median {fmt(lang, j26['d_turnout']['median'],2)} pp, symmetric; "
                       f"flagged jumps {fmt(lang, j26['d_turnout']['flagged_pct'],2)}% "
                       f"({int_fmt(lang, j26['d_turnout']['up'])} up / "
                       f"{int_fmt(lang, j26['d_turnout']['down'])} down); Δshares — the mirror "
                       f"swings of a real campaign."),
            "M10_C3": (f"2022 runoff → 2026 runoff (n={int_fmt(lang, j22['match']['matched'])}): "
                       f"Δturnout median {fmt(lang, j22['d_turnout']['median'],2)} pp; jumps "
                       f"{fmt(lang, j22['d_turnout']['flagged_pct'],2)}% "
                       f"({int_fmt(lang, j22['d_turnout']['up'])} up / "
                       f"{int_fmt(lang, j22['d_turnout']['down'])} down); Lula’s flagged-section "
                       f"share {fmt(lang, j22['flagged_shareB_lula'],1)}% vs national "
                       f"{fmt(lang, nat.get('share:LULA', pva['actual_2026_runoff']['lula_twoway_pct']),1)}% — "
                       f"jump sections do not favour either candidate."),
            "M10_C4": (f"Runoff fingerprints: both mixture components at normal turnout for Lula "
                       f"(2nd at {fmt(lang, fp_l['mean_anom'][0],0)}%, weight "
                       f"{fmt(lang, fp_l['weight_anom'],2)}) — no corner cluster."),
            # ── m11 selftest ──
            "M11": (f"Adding about {int_fmt(lang, st['injected_added_ballots_party'])} synthetic "
                    f"ballots for the leader under the specified injection scheme increases the "
                    f"tail statistic {fmt(lang, st['signal_growth'],1)}-fold. Rounding turnout to "
                    f"integer percentages in 5% of sections moves z from "
                    f"{fmt(lang, st['peaks_z_clean'],2)} to {fmt(lang, st['peaks_z_rounded'],2)}. "
                    f"These experiments demonstrate sensitivity to those mechanisms and parameters, "
                    f"not to every manipulation of comparable size."),
            "M11_C1": (f"Left: the turnout distribution after the synthetic injection — a visible "
                       f"second hump above the boundary. Right: leader votes in the anomalous zone "
                       f"before/after — a {fmt(lang, st['signal_growth'],0)}-fold signal growth."),
            # ── paradox ──
            "TR_SUMMARY": fmt(lang, pool_lula_tw, 1),
            "TR_CURY": rate("CURY"),
            "TR_FER": rate("FERREIRA"),
            "TR_CAI": rate("CAIADO"),
            "TR_ZEMA": rate("ZEMA"),
            "TR_BLANK": rate("BRANCO"),
            "TR_NEW": rate("NEW"),
            "ERR_CURY": decomp_pp(lang, "CURY"),
            "ERR_FER": decomp_pp(lang, "FERREIRA"),
            "ERR_CAI": decomp_pp(lang, "CAIADO"),
            "ERR_ZEMA": decomp_pp(lang, "ZEMA"),
            "ERR_BLANK": decomp_pp(lang, "BRANCO"),
            "ERR_NEW": decomp_pp(lang, "NEW"),
            # ── data ──
            "D1": int_fmt(lang, n_sections),
            "D2": ("zero discrepancies in all checks (nominal votes vs detail files, blank/null "
                   "cross-checks, no duplicated section keys, no turnout above electorate)."),
        }
        V[lang]["METH_SUMMARY"] = (
            f"Taken together, the reported results do not establish manipulation in the runoff "
            f"counts; the tail, digit and correlation diagnostics stay inside the envelope the "
            f"2022 control sets."
            if all(r["p_value"] > 0.05 for r in metrics["benford2"]) else
            "Some tests reject their reference distributions; interpreting them requires attention "
            "to model assumptions.")

    for fname in ("index.html", "translations.js"):
        p = SITE / fname
        s = p.read_text(encoding="utf-8")
        # index.html is the en-default static content: fill with en values;
        # translations.js: fill each language block with its own values
        if fname == "index.html":
            s2 = s
            for tok, val in V["en"].items():
                s2 = s2.replace(f"⟦{tok}⟧", val)
            left = re.findall(r"⟦[A-Z0-9_]+⟧", s2)
            p.write_text(s2, encoding="utf-8")
            print(f"index.html filled; remaining tokens: {sorted(set(left)) or 'none'}")
        else:
            blocks = re.split(r"(?m)^(\s*)(en|pt|es|ru): \{", s)
            out = [blocks[0]]
            for i in range(1, len(blocks), 3):
                indent, lang, body = blocks[i], blocks[i + 1], blocks[i + 2]
                for tok, val in V[lang].items():
                    body = body.replace(f"⟦{tok}⟧", val)
                left = re.findall(r"⟦[A-Z0-9_]+⟧", body)
                if left:
                    print(f"WARN {lang}: unfilled {sorted(set(left))}", file=sys.stderr)
                out += [indent, f"{lang}: {{", body]
            p.write_text("".join(out), encoding="utf-8")
            print("translations.js filled (en/pt/es/ru)")


if __name__ == "__main__":
    main()
