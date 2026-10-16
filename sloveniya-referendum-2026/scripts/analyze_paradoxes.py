"""Voting-paradox analysis: which paradoxes from paradoxes.md the data can test.

The repo-level catalogue (paradoxes.md) lists social-choice pathologies; most
need multi-candidate preference data, which a binary ZA/PROTI referendum cannot
produce. Three items are testable on the precinct data — this script computes
them all:

1. Multiple-district paradox + frustrated majority (territorial analog):
   the national winner vs winners of territorial majorities (8 units /
   88 districts / 3,083 stations), plus the decomposition of the national
   totals into election-day precincts / early-voting points / special votes
   (on election-day precincts alone all four questions went ZA — both
   rejections were decided by early and postal voters).
2. Gerrymander bound: with precinct-level districting, can the national
   loser win a majority of 88 winner-take-all districts of (roughly) equal
   electorate? Deterministic size-constrained greedy packing; the arithmetic
   floor for 45/88 is just above 25% of the vote.
3. Art. 90 quorum margins (binding referendum preiskava): rejection requires
   PROTI > ZA among valid votes AND PROTI >= 1/5 of registered voters —
   exact margins and counterfactuals for both conditions (no-show /
   perverse-response family). The rule is individually monotone: no strict
   no-show exists, but the outcome is tied to the size of the registered
   electorate — people who never voted.

Run (from the project directory):
    uv run python scripts/analyze_paradoxes.py

Output: analysis/paradoxes/{tables,figures,metrics.json} + PARADOXES.md.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

BASE = Path(__file__).resolve().parents[1]
SRC_PREC = BASE / "data" / "derived" / "volisca_all.csv"
SRC_NAT = BASE / "data" / "derived" / "nacionalni_pregled.csv"
OUT = BASE / "analysis" / "paradoxes"

REFS = ["preiskava", "socialna_pomoc", "volilna_pravica", "rtv_prispevek"]
REF_TITLE = {
    "preiskava": "ZPPre-B (binding)",
    "socialna_pomoc": "social assistance",
    "volilna_pravica": "voting rights",
    "rtv_prispevek": "RTV fee",
}
BINDING = "preiskava"  # Art. 90 quorum applies to the legislative referendum only

N_DISTRICTS = 88
NEED = N_DISTRICTS // 2 + 1  # majority of winner-take-all districts
SIZE_LO = 0.85  # a built district must hold at least this share of the target electorate
SIZE_HI = 1.15  # ... and at most this share

GREEN = "#1e8e5a"
RED = "#c0392b"
DARK = "#16324f"
GREY = "#8a97a5"
BLUE = "#3b82c4"
AMBER = "#8a6116"


# ────────────────────────────── data ──────────────────────────────


@dataclass(frozen=True)
class NationalTotals:
    referendum: str
    upr: int
    gl: int
    velj: int
    nev: int
    za: int
    proti: int

    @property
    def winner(self) -> str:
        return "ZA" if self.za > self.proti else "PROTI"

    @property
    def margin(self) -> int:
        return abs(self.za - self.proti)


@dataclass(frozen=True)
class TerritorialSplit:
    referendum: str
    level: str  # units / districts / stations
    n: int
    za: int
    proti: int
    ties: int
    national_winner: str

    @property
    def territorial_winner(self) -> str:
        return "ZA" if self.za > self.proti else "PROTI"

    @property
    def reversed(self) -> bool:
        return self.territorial_winner != self.national_winner


@dataclass(frozen=True)
class VoteDecomposition:
    referendum: str
    national_net: int  # za - proti
    precinct_net: int  # election-day regular precincts (station no. < 900)
    early_net: int  # early-voting points (no. >= 900)
    special_net: int  # national minus both = postal / abroad / residual


@dataclass(frozen=True)
class GerrymanderResult:
    referendum: str
    loser: str  # side that lost the national vote
    loser_share: float  # of national valid votes
    built_wins: int  # winning districts built by packing
    filler_wins: int  # filler districts that win anyway
    ok: bool  # built_wins + filler_wins >= NEED
    district_electorate_min: int
    district_electorate_median: float
    district_electorate_max: int
    arithmetic_floor: float  # min national vote share to win NEED of N (equal districts)

    @property
    def total_wins(self) -> int:
        return self.built_wins + self.filler_wins


@dataclass(frozen=True)
class QuorumMargins:
    referendum: str
    binding: bool
    upr: int
    quorum: float  # upr / 5
    proti: int
    half_valid: float  # velj / 2 — the majority threshold
    margin_quorum: int  # proti - quorum
    margin_majority: int  # |za - proti|
    winner: str
    flip_votes: int  # extra votes the losing side needs to flip the national majority
    abstainers: int  # upr - gl
    flip_pct_of_abstainers: float
    invalid: int
    electorate_growth_to_swallow: int  # extra registrations for proti < upr/5 (0 if proti lost)


def load() -> tuple[pd.DataFrame, dict[str, NationalTotals]]:
    prec = pd.read_csv(SRC_PREC)
    nat_df = pd.read_csv(SRC_NAT)
    nat = {}
    for _, r in nat_df[nat_df.nivo == "slovenija"].iterrows():
        nat[r.referendum] = NationalTotals(
            referendum=r.referendum,
            upr=int(r.upr), gl=int(r.gl), velj=int(r.velj), nev=int(r.nev),
            za=int(r.za), proti=int(r.proti),
        )
    assert set(nat) == set(REFS), f"national totals: {sorted(nat)}"
    for ref in REFS:
        assert len(prec[prec.referendum == ref]) == 3083, ref
    return prec, nat


# ───────────────────── 1. territorial paradoxes ─────────────────────


def territorial_splits(
    prec: pd.DataFrame, nat: dict[str, NationalTotals]
) -> list[TerritorialSplit]:
    nat_df = pd.read_csv(SRC_NAT)
    rows: list[TerritorialSplit] = []
    for ref in REFS:
        d = prec[prec.referendum == ref]
        u = nat_df[(nat_df.referendum == ref) & (nat_df.nivo == "enota")]
        o = nat_df[(nat_df.referendum == ref) & (nat_df.nivo == "okraj")]
        for level, g in (("units", u), ("districts", o), ("stations", d)):
            rows.append(TerritorialSplit(
                referendum=ref, level=level, n=len(g),
                za=int((g.za > g.proti).sum()),
                proti=int((g.proti > g.za).sum()),
                ties=int((g.za == g.proti).sum()),
                national_winner=nat[ref].winner,
            ))
    return rows


def decompositions(prec: pd.DataFrame, nat: dict[str, NationalTotals]) -> list[VoteDecomposition]:
    rows: list[VoteDecomposition] = []
    for ref in REFS:
        d = prec[prec.referendum == ref]
        reg, early = d[d.volisce_st < 900], d[d.volisce_st >= 900]
        n = nat[ref]
        special_za = n.za - reg.za.sum() - early.za.sum()
        special_p = n.proti - reg.proti.sum() - early.proti.sum()
        rows.append(VoteDecomposition(
            referendum=ref,
            national_net=n.za - n.proti,
            precinct_net=int(reg.za.sum() - reg.proti.sum()),
            early_net=int(early.za.sum() - early.proti.sum()),
            special_net=int(special_za - special_p),
        ))
    return rows


# ───────────────────── 2. gerrymander bound ─────────────────────


def pack_districts(reg: pd.DataFrame, loser: str, n: int, need: int) -> GerrymanderResult:
    """Deterministic size-constrained greedy packing.

    Precincts are taken in descending order of the loser's share of valid
    votes; districts are filled one by one until the loser has a majority of
    the district's valid votes and >= SIZE_LO of the target electorate
    (never more than SIZE_HI). The remaining precincts are spread over the
    leftover districts by least-loaded fill.
    """
    l_col, o_col = (("za", "proti") if loser == "ZA" else ("proti", "za"))
    items = reg[["enota_st", "okraj_rpeid", "volisce_st", "upr", "za", "proti"]].copy()
    items["l"] = items[l_col]
    items["o"] = items[o_col]
    items["share"] = items["l"] / (items["za"] + items["proti"]).clip(lower=1)
    # strongest loser precincts first; deterministic tie-break
    items = items.sort_values(["share", "upr", "volisce_st"], ascending=[False, False, True])
    target = items["upr"].sum() / n

    remaining = items.to_dict("records")
    winners: list[list[dict]] = []
    idx = 0
    while len(winners) < need and idx < len(remaining):
        cur, upr_sum, l_sum, o_sum = [], 0, 0, 0
        while idx < len(remaining):
            p = remaining[idx]
            if upr_sum > 0 and upr_sum + p["upr"] > SIZE_HI * target:
                break
            cur.append(p)
            upr_sum += p["upr"]
            l_sum += p["l"]
            o_sum += p["o"]
            idx += 1
            if upr_sum >= SIZE_LO * target and l_sum > o_sum:
                break
        if upr_sum >= SIZE_LO * target and l_sum > o_sum:
            winners.append(cur)

    # leftovers into filler districts, least-loaded first
    fillers: list[tuple[int, list[dict]]] = [(0, []) for _ in range(n - len(winners))]
    for p in remaining[idx:]:
        fillers.sort(key=lambda t: t[0])
        size, cur = fillers[0]
        fillers[0] = (size + p["upr"], cur + [p])

    def district_l(d: list[dict]) -> tuple[int, int]:
        return sum(p["l"] for p in d), sum(p["o"] for p in d)

    filler_wins = sum(1 for _, d in fillers if district_l(d)[0] > district_l(d)[1])
    all_sizes = sorted([sum(p["upr"] for p in d) for d in winners]
                       + [s for s, d in fillers if d])
    med = all_sizes[len(all_sizes) // 2] if all_sizes else 0.0

    return GerrymanderResult(
        referendum=str(reg.referendum.iloc[0]),
        loser=loser,
        loser_share=float(reg[l_col].sum() / (reg["za"].sum() + reg["proti"].sum())),
        built_wins=len(winners),
        filler_wins=filler_wins,
        ok=len(winners) + filler_wins >= need,
        district_electorate_min=int(all_sizes[0]) if all_sizes else 0,
        district_electorate_median=float(med),
        district_electorate_max=int(all_sizes[-1]) if all_sizes else 0,
        arithmetic_floor=(need * 0.5) / n,
    )


def gerrymanders(prec: pd.DataFrame, nat: dict[str, NationalTotals]) -> list[GerrymanderResult]:
    out: list[GerrymanderResult] = []
    for ref in REFS:
        reg = prec[(prec.referendum == ref) & (prec.upr > 0)]
        loser = "PROTI" if nat[ref].winner == "ZA" else "ZA"
        out.append(pack_districts(reg, loser, N_DISTRICTS, NEED))
    return out


# ───────────────────── 3. Art. 90 quorum margins ─────────────────────


def quorum_margins(nat: dict[str, NationalTotals]) -> list[QuorumMargins]:
    rows: list[QuorumMargins] = []
    for ref in REFS:
        n = nat[ref]
        quorum = n.upr / 5
        rows.append(QuorumMargins(
            referendum=ref, binding=ref == BINDING,
            upr=n.upr, quorum=quorum, proti=n.proti,
            half_valid=n.velj / 2,
            margin_quorum=int(round(n.proti - quorum)),
            margin_majority=n.margin,
            winner=n.winner,
            flip_votes=n.margin + 1,
            abstainers=n.upr - n.gl,
            flip_pct_of_abstainers=(n.margin + 1) / (n.upr - n.gl) * 100,
            invalid=n.nev,
            electorate_growth_to_swallow=(5 * n.proti - n.upr) if n.proti > n.za else 0,
        ))
    return rows


# ────────────────────────────── figures ──────────────────────────────


def fig_territory(splits: list[TerritorialSplit], path: Path) -> None:
    d = [s for s in splits if s.level == "districts"]
    fig, ax = plt.subplots(figsize=(9.6, 4.4), dpi=150)
    y = range(len(REFS))
    za = [100 * s.za / s.n for s in d]
    labels = [f"{REF_TITLE[s.referendum]} — {s.national_winner} won nationally"
              for s in d]
    colors = [GREEN if s.national_winner == "ZA" else RED for s in d]
    ax.barh(list(y), za, color=colors, alpha=0.85, height=0.62, zorder=3)
    ax.axvline(50, color=DARK, linestyle="--", linewidth=1.6, zorder=4)
    ax.text(50.7, -0.6, "majority: 45+ districts", color=DARK, fontsize=10)
    for i, s in enumerate(d):
        ax.text(za[i] - 2, i, f"ZA {s.za} : {s.proti} PROTI"
                + ("  ← reversal" if s.reversed else ""),
                va="center", ha="right", fontsize=10.5, color="white",
                fontweight="bold", zorder=5)
    ax.set_yticks(list(y), labels, fontsize=10)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Districts won by ZA, % of 88")
    ax.set_title("Same votes, another rule: winner by majority of the 88 real districts")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def fig_quorum(q: list[QuorumMargins], path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9.6, 4.6), dpi=150)
    refs = [q[i].referendum for i in range(len(REFS))]
    quorums = [q[i].quorum for i in range(len(REFS))]
    protis = [q[i].proti for i in range(len(REFS))]
    halves = [q[i].half_valid for i in range(len(REFS))]
    x = range(len(REFS))
    ax.bar(x, protis, color=RED, alpha=0.8, width=0.55, zorder=3, label="PROTI votes")
    ax.scatter(list(x), quorums, marker="_", s=1400, color=DARK, linewidths=2.6,
               zorder=4, label="Art. 90 quorum (1/5 of electorate)")
    ax.scatter(list(x), halves, marker="_", s=1400, color=GREY, linewidths=2.6,
               zorder=4, label="half of valid votes (majority threshold)")
    for i in range(len(REFS)):
        rej = q[i].winner == "PROTI"
        maj = f"+{q[i].margin_majority:,}" if rej else f"−{q[i].margin_majority:,}"
        y0 = max(protis[i], halves[i]) + 14000
        ax.text(i, y0,
                f"quorum +{q[i].margin_quorum:,}\nmajority {maj}\n"
                f"{'rejected' if rej else 'approved'}",
                ha="center", fontsize=9, color=DARK, linespacing=1.35)
    ax.set_xticks(list(x), [REF_TITLE[r] for r in refs], fontsize=10)
    ax.set_ylim(0, max(protis) * 1.42)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v / 1000:.0f}k")
    ax.set_ylabel("Votes")
    ax.set_title("Rejection needs BOTH thresholds — PROTI cleared them only where it won")
    ax.legend(fontsize=9.5, framealpha=0.9, loc="upper center", ncol=3,
              bbox_to_anchor=(0.5, -0.18))
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def fig_decomposition(dec: list[VoteDecomposition], path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9.6, 4.6), dpi=150)
    x = range(len(REFS))
    width = 0.27
    series = [("precinct_net", "election-day precincts", BLUE),
              ("early_net", "early voting", AMBER),
              ("special_net", "postal / abroad", GREY)]
    for k, (key, label, color) in enumerate(series):
        vals = [getattr(d, key) for d in dec]
        ax.bar([i + (k - 1) * width for i in x], vals, width=width, label=label,
               color=color, alpha=0.85, zorder=3)
    top = max(max(d.precinct_net, d.early_net, d.special_net) for d in dec)
    for i, d in enumerate(dec):
        ax.text(i, top + 16000,
                f"{'ZA' if d.national_net > 0 else 'PROTI'} +{abs(d.national_net):,}",
                ha="center", fontsize=10, color=DARK, fontweight="bold")
    ax.axhline(0, color=DARK, linewidth=1.2)
    ax.set_xticks(list(x), [REF_TITLE[d.referendum] for d in dec], fontsize=10)
    ax.set_yticks(list(range(-40000, 240001, 40000)))
    ax.yaxis.set_major_formatter(lambda v, _: f"{v / 1000:+.0f}k" if v else "0")
    ax.set_ylim(-48000, top + 38000)
    ax.set_ylabel("Net margin, ZA − PROTI")
    ax.set_title("Who decided it: election-day precincts went ZA on all four questions")
    ax.legend(fontsize=10, framealpha=0.9, loc="upper center", ncol=3,
              bbox_to_anchor=(0.5, -0.16))
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


# ──────────────────────────── report ────────────────────────────


def _cell_split(s: TerritorialSplit) -> str:
    tag = " **← reversal**" if s.reversed else ""
    ties = f" (+{s.ties} ties)" if s.ties else ""
    return f"ZA {s.za:,} : {s.proti:,} PROTI{ties}{tag}"


def write_report(splits: list[TerritorialSplit], dec: list[VoteDecomposition],
                 gerr: list[GerrymanderResult], quo: list[QuorumMargins],
                 nat: dict[str, NationalTotals]) -> None:
    s = {(x.referendum, x.level): x for x in splits}
    dd = {x.referendum: x for x in dec}
    g = {x.referendum: x for x in gerr}
    q = {x.referendum: x for x in quo}
    n = nat
    pre, rtv = q["preiskava"], q["rtv_prispevek"]

    share = {
        ref: f"{n[ref].winner} {max(n[ref].za, n[ref].proti) / n[ref].velj * 100:.2f}%"
        for ref in REFS
    }
    terr_rows = "\n".join(
        f"| {REF_TITLE[ref]} | **{share[ref]}** | {_cell_split(s[ref, 'units'])} "
        f"| {_cell_split(s[ref, 'districts'])} | {_cell_split(s[ref, 'stations'])} |"
        for ref in REFS)
    dec_rows = "\n".join(
        f"| {REF_TITLE[ref]} | ZA +{dd[ref].precinct_net:,} | PROTI {dd[ref].early_net:,} "
        f"| PROTI {dd[ref].special_net:,} | "
        f"{'ZA' if dd[ref].national_net > 0 else 'PROTI'} {abs(dd[ref].national_net):,} |"
        for ref in REFS)
    gerr_rows = "\n".join(
        f"| {REF_TITLE[ref]} | {g[ref].loser} ({g[ref].loser_share * 100:.2f}%) "
        f"| {g[ref].total_wins} | {'**yes**' if g[ref].ok else 'no'} |"
        for ref in REFS)
    def _growth(x: QuorumMargins) -> str:
        return f"+{x.electorate_growth_to_swallow:,}" if x.electorate_growth_to_swallow else "—"

    quo_rows = "\n".join(
        f"| {REF_TITLE[ref]}{'*' if q[ref].binding else ''} "
        f"| {q[ref].proti:,} | {q[ref].quorum:,.0f} | +{q[ref].margin_quorum:,} "
        f"| {q[ref].margin_majority:,} "
        f"| {q[ref].flip_votes:,} ({q[ref].flip_pct_of_abstainers:.2f}% of abstainers) "
        f"| {_growth(q[ref])} |"
        for ref in REFS)

    quo_header = ("| Referendum | PROTI votes | Quorum | Margin over quorum "
                  "| Majority margin | Loser's flip votes "
                  "| Extra registrations to void the quorum |")

    md = f"""# Voting paradoxes in the Slovenian referendums of 11.10.2026

*Which items of the catalogue [`paradoxes.md`](../paradoxes.md) are testable on this
data — and what they show. A binary ZA/PROTI ballot cannot produce vote-splitting,
so most of the catalogue (Condorcet winner/loser, center squeeze, spoiler, cloning,
best-is-worst, lesser-evil, later-no-harm/help) is structurally out of scope: it needs
preferences over 3+ alternatives. Three items are testable — all three turn out
to be live on this election. Data: official DVK aggregates
(`data/derived/nacionalni_pregled.csv`) and precinct results
(`data/derived/volisca_all.csv`); outputs in `analysis/paradoxes/`.*

## 1. Multiple-district paradox — it occurred, on the real territories

Slovenian referendums are decided by the national vote total. Had they instead been
decided by winning a **majority of territories** (electoral-college style), the
outcomes would change: on `rtv_prispevek` the national PROTI win (by 546 votes)
turns into a ZA win at every territorial level, and on `preiskava` (PROTI by
23,147 votes) into a ZA win at the level of the 8 electoral units and of polling
stations — only the 88 districts keep PROTI (48:40):

| Referendum | National winner | 8 units | 88 districts | 3,083 stations |
|---|---|---|---|---|
{terr_rows}

This is the multiple-district paradox on real, non-designed territories, and the
territorial form of the *frustrated majority*: on both rejected questions the
nationally winning side is the minority among territories. Figure: `figures/territory.png`.

### 1a. Aggregation over time: the counting-night reversals

The same sensitivity plays out over time (media-reconstructed partial results,
[`data/wikipedia/counting_night_dynamics.md`](data/wikipedia/counting_night_dynamics.md)):
on all four questions **ZA led after the first fifth of ballots counted**; both final
PROTI wins are counting-order reversals — cities (ZA-leaning) are counted faster.

### 1b. Aggregation over ballot mode: who actually decided it

Decomposing the national totals (the 9% of ballots without a regular-precinct
breakdown flipped both rejections):

| Referendum | Election-day precincts | Early voting | Postal/abroad (residual) | National |
|---|---|---|---|---|
{dec_rows}

**On election-day ballots alone, all four questions went ZA.** Both rejections were
decided by early voters (>75,000 people, the second-largest early turnout in Slovenian
referendum history) plus postal/abroad votes. Figure: `figures/decomposition.png`.

## 2. Gerrymander bound — a quarter of the vote is enough in principle

With precinct-level districting and winner-take-all districts, can the national
loser win a majority of 88 (roughly equal) districts? Deterministic greedy packing
(loser's strongest precincts first, districts 0.85–1.15 of the target electorate,
no geography constraint — one construction, hence a lower bound on what a motivated
mapmaker could do):

| Referendum | National loser | Districts won by packing | Enough for 45? |
|---|---|---|---|
{gerr_rows}

The packing succeeds exactly where the loser is near parity on election-day
precincts ({g['preiskava'].loser_share * 100:.1f}% and {g['rtv_prispevek'].loser_share * 100:.1f}%):
Slovenia's precinct geography is not segregated enough to
stretch a 38–43% minority over 45 districts of ~equal size. The arithmetic floor
is unchanged, though: winning 45 of 88 equal winner-take-all districts requires
just above **{g['preiskava'].arithmetic_floor * 100:.1f}%** of the national vote.
Slovenia does not decide referendums this way — the numbers quantify how much the
aggregation rule, not the voters, would decide the outcome.

## 3. Art. 90 quorum and the no-show family — exact margins

The binding referendum (`preiskava`) is rejected only if **PROTI wins a majority of
valid votes AND PROTI ≥ 1/5 of all registered voters**. Margins on both conditions
(the other three were consultative; their rows are the same arithmetic applied
counterfactually):

{quo_header}
|---|---|---|---|---|---|---|
{quo_rows}

\\* binding; Art. 90 applies formally only here. Figure: `figures/quorum.png`.

Reading the table through the paradoxes.md families:

- **No-show / perverse response: absent, provably.** The rule is individually
  monotone — an extra ZA vote can never cause rejection, an extra PROTI vote can
  never prevent it — exactly matching the catalogue's "Plurality: −" for these rows.
- **The quorum imports non-voters into the outcome.** Rejection of ZPPre-B needed
  {pre.quorum:,.0f} PROTI votes *because {pre.upr:,} people were registered*. Had the
  register been {pre.upr + pre.electorate_growth_to_swallow:,}
  ({pre.electorate_growth_to_swallow / pre.upr * 100:.0f}% larger), the same
  {pre.proti:,} PROTI votes would no longer have cleared 1/5 — the law would have
  stood without a single vote changing. The flip side: {pre.flip_votes:,} additional
  ZA voters ({pre.flip_pct_of_abstainers:.1f}% of the {pre.abstainers:,} abstainers)
  would have kept the law.
- **Fragility is real but bounded.** The RTV margin — {rtv.margin_majority} votes
  out of {n['rtv_prispevek'].velj:,} valid — is smaller than its {rtv.invalid:,}
  invalid ballots; {rtv.flip_votes} extra ZA votes flip it. Yet even under the
  Art. 90 rule applied counterfactually to all four questions, no outcome changes:
  on both PROTI-won questions PROTI also cleared the quorum
  (+{pre.margin_quorum:,} and +{rtv.margin_quorum:,}), and on the ZA-won ones the
  quorum does not stand in the way of approval.

## 4. What this data cannot test

Condorcet winner/loser and cyclical majorities, center squeeze, spoiler, cloning,
best-is-worst, lesser-evil, later-no-harm/help, truncation, twin — all require
ranked ballots or ≥3 options; a ZA/PROTI vote has two strategies and no
vote-splitting. Strategic voting (the catalogue's one "+" for every procedure)
is unmeasurable without preference polls, which the project does not collect.

## Reproducibility

`uv run python scripts/analyze_paradoxes.py` → `analysis/paradoxes/`
(tables: `territorial_winners.csv`, `decomposition.csv`, `gerrymander.csv`,
`quorum_margins.csv`; figures: `territory.png`, `decomposition.png`, `quorum.png`;
`metrics.json`). Precinct sums vs national totals differ by construction
(early-voting points and the postal/abroad residual) — the national rows of
`nacionalni_pregled.csv` are authoritative, as everywhere in this project.
"""
    (BASE / "PARADOXES.md").write_text(md, encoding="utf-8")


# ──────────────────────────── main ────────────────────────────


def main() -> None:
    tab = OUT / "tables"
    fig = OUT / "figures"
    tab.mkdir(parents=True, exist_ok=True)
    fig.mkdir(parents=True, exist_ok=True)

    prec, nat = load()
    splits = territorial_splits(prec, nat)
    dec = decompositions(prec, nat)
    gerr = gerrymanders(prec, nat)
    quo = quorum_margins(nat)

    pd.DataFrame([asdict(x) for x in splits]).to_csv(tab / "territorial_winners.csv", index=False)
    pd.DataFrame([asdict(x) for x in dec]).to_csv(tab / "decomposition.csv", index=False)
    pd.DataFrame([asdict(x) for x in gerr]).to_csv(tab / "gerrymander.csv", index=False)
    pd.DataFrame([asdict(x) for x in quo]).to_csv(tab / "quorum_margins.csv", index=False)

    fig_territory(splits, fig / "territory.png")
    fig_decomposition(dec, fig / "decomposition.png")
    fig_quorum(quo, fig / "quorum.png")

    metrics = {
        "title": "Slovenia 11.10.2026: voting paradoxes testable on referendum data",
        "n_referendums": len(REFS),
        "district_level_reversals": [s.referendum for s in splits
                                     if s.level == "districts" and s.reversed],
        "unit_level_reversals": [s.referendum for s in splits
                                 if s.level == "units" and s.reversed],
        "za_won_election_day_all": all(d.precinct_net > 0 for d in dec),
        "gerrymander": {g.referendum: {"loser": g.loser, "wins": g.total_wins,
                                       "ok": g.ok} for g in gerr},
        "quorum": {q.referendum: {"margin_quorum": q.margin_quorum,
                                  "margin_majority": q.margin_majority,
                                  "flip_votes": q.flip_votes} for q in quo},
        "min_majority_margin_votes": min(q.margin_majority for q in quo),
    }
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

    write_report(splits, dec, gerr, quo, nat)
    print("tables/figures/metrics ->", OUT)
    print("report ->", BASE / "PARADOXES.md")


if __name__ == "__main__":
    main()
