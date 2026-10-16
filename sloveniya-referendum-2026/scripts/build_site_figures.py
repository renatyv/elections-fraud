# Figures for the public site page of this repository — one set per language
# (en, sl, hr, it, hu), data — data/derived/volisca_all.csv. Run from the
# project directory:
#   uv run python scripts/build_site_figures.py
# Output: <repo>/site/sloveniya-referendum-2026/img/<lang>/{turnout,comet,cross}.png
#         and the paradox figures (territory, decomposition, quorum) for
#         paradoxes.html — analysis: scripts/analyze_paradoxes.py
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas", "matplotlib"]
# ///
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "site" / "sloveniya-referendum-2026" / "img"
OUT.mkdir(parents=True, exist_ok=True)

BLUE = "#3b82c4"
DARK = "#16324f"
RED = "#c0392b"
GREEN = "#1e8e5a"
GREY = "#8a97a5"
CUT = 70.0  # honest-decline boundary (q99.5 of the controls), see the report, section 1

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
    "bell_title": "One smooth bell curve — and it fades out by 70%",
    "bell_xlabel": "Turnout, % of registered voters",
    "bell_ylabel": "Number of precincts",
    "bell_cut": "honest-decline boundary (70%)",
    "bell_box": "only 10 precincts above 80%\n(808 ballots = 0.1%)",
    "comet_title": "Turnout vs YES share — parliamentary-investigation referendum",
    "comet_xlabel": "Turnout, %",
    "comet_ylabel": 'YES ("ZA") share, % of valid votes',
    "comet_legend": "average by turnout group",
    "comet_box": ("YES share grows smoothly with turnout\n"
                  "(+4 pp per +10 pp turnout) — the city/countryside split.\n"
                  "No separate 'tail' at high turnout."),
    "cross_suptitle": "Same precincts, four ballots: the geography of YES agrees everywhere",
    "yes": "YES",
    "names": {
        "preiskava": "Parliamentary investigation",
        "socialna_pomoc": "Social assistance",
        "volilna_pravica": "Local voting rights",
        "rtv_prispevek": "RTV fee",
    },
},
"sl": {
    "bell_title": "En sam gladek zvon — izzveni pri 70 %",
    "bell_xlabel": "Udeležba, % volivcev",
    "bell_ylabel": "Število volišč",
    "bell_cut": "meja poštenega upada (70 %)",
    "bell_box": "nad 80 % le 10 volišč\n(808 glasovnic = 0,1 %)",
    "comet_title": "Udeležba in delež ZA — zakonodajni referendum",
    "comet_xlabel": "Udeležba, %",
    "comet_ylabel": "Delež ZA, % veljavnih glasov",
    "comet_legend": "povprečje po skupinah udeležbe",
    "comet_box": ("Delež ZA gladko narašča z udeležbo\n"
                  "(+4 točke na +10 točk udeležbe) — ločnica mesto/vas.\n"
                  "Ločenega »repa« pri visoki udeležbi ni."),
    "cross_suptitle": "Ista volišča, štiri glasovnice: geografija ZA se ujema povsod",
    "yes": "ZA",
    "names": {
        "preiskava": "Parlamentarna preiskava",
        "socialna_pomoc": "Socialna pomoč",
        "volilna_pravica": "Volilna pravica",
        "rtv_prispevek": "Prispevek RTV",
    },
},
"hr": {
    "bell_title": "Jedno glatko zvono — gasi se kod 70 %",
    "bell_xlabel": "Izlaznost, % birača",
    "bell_ylabel": "Broj biračkih mjesta",
    "bell_cut": "granica poštenog pada (70 %)",
    "bell_box": "iznad 80 % tek 10 mjesta\n(808 listića = 0,1 %)",
    "comet_title": "Izlaznost i udio ZA — referendum o zakonu",
    "comet_xlabel": "Izlaznost, %",
    "comet_ylabel": "Udio ZA, % važećih glasova",
    "comet_legend": "prosjek po skupinama izlaznosti",
    "comet_box": ("Udio ZA glatko raste s izlaznošću\n"
                  "(+4 boda na +10 bodova izlaznosti) — podjela grad/selo.\n"
                  "Odvojenog »repa« pri visokoj izlaznosti nema."),
    "cross_suptitle": "Ista mjesta, četiri listića: geografija ZA slaže se svugdje",
    "yes": "ZA",
    "names": {
        "preiskava": "Parlamentarna istraga",
        "socialna_pomoc": "Socijalna pomoć",
        "volilna_pravica": "Biračko pravo",
        "rtv_prispevek": "Prihod za RTV",
    },
},
"it": {
    "bell_title": "Un'unica campana regolare — si esaurisce al 70%",
    "bell_xlabel": "Affluenza, % degli elettori",
    "bell_ylabel": "Numero di sezioni",
    "bell_cut": "limite del calo onesto (70%)",
    "bell_box": "oltre l'80% solo 10 sezioni\n(808 schede = 0,1%)",
    "comet_title": "Affluenza e quota SÌ — referendum legislativo",
    "comet_xlabel": "Affluenza, %",
    "comet_ylabel": "Quota SÌ, % dei voti validi",
    "comet_legend": "media per gruppo di affluenza",
    "comet_box": ("La quota di SÌ cresce dolcemente con l'affluenza\n"
                  "(+4 punti per +10 punti di affluenza) — divisione città/campagna.\n"
                  "Nessuna «coda» separata ad alta affluenza."),
    "cross_suptitle": "Stesse sezioni, quattro schede: la geografia del SÌ concorde ovunque",
    "yes": "SÌ",
    "names": {
        "preiskava": "Inchiesta parlamentare",
        "socialna_pomoc": "Sussidio sociale",
        "volilna_pravica": "Diritto di voto locale",
        "rtv_prispevek": "Canone RTV",
    },
},
"hu": {
    "bell_title": "Egyetlen sima haranggörbe — 70% körül elhal",
    "bell_xlabel": "Részvétel, % a választásra jogosultakból",
    "bell_ylabel": "Szavazókörök száma",
    "bell_cut": "a korrekt csökkenés határa (70%)",
    "bell_box": "80% felett mindössze 10 kör\n(808 szavazólap = 0,1%)",
    "comet_title": "Részvétel és IGEN-arány — törvényi népszavazás",
    "comet_xlabel": "Részvétel, %",
    "comet_ylabel": "IGEN-arány, % az érvényes szavazatokból",
    "comet_legend": "átlag részvételi csoportonként",
    "comet_box": ("Az IGEN-arány a részvétellel simán nő\n"
                  "(+4 pont / +10 pont részvétel) — város–vidék megosztás.\n"
                  "Külön „farok” magas részvételnél nincs."),
    "cross_suptitle": "Ugyanazok a körök, négy szavazólap: az IGEN földrajza mindenhol egyezik",
    "yes": "IGEN",
    "names": {
        "preiskava": "Parlamenti vizsgálat",
        "socialna_pomoc": "Szociális segély",
        "volilna_pravica": "Helyi választójog",
        "rtv_prispevek": "RTV-díj",
    },
},
}

df = pd.read_csv(ROOT / "data" / "derived" / "volisca_all.csv")
df = df[df["upr"] > 0]  # regular precincts, no early-voting points


def fig_turnout(lang: str, tr: dict) -> None:
    t = df[df["referendum"] == "preiskava"]["udelezba_prc"] * 100
    fig, ax = plt.subplots(figsize=(9.6, 4.0), dpi=150)
    ax.hist(t, bins=80, range=(0, 100), color=BLUE, alpha=0.85, edgecolor="white", linewidth=0.3)
    ax.axvline(CUT, color=RED, linestyle="--", linewidth=1.6)
    ax.text(CUT + 1.2, ax.get_ylim()[1] * 0.92, tr["bell_cut"], color=RED, fontsize=10)
    ax.text(
        84,
        ax.get_ylim()[1] * 0.60,
        tr["bell_box"],
        color=DARK,
        fontsize=10,
        ha="center",
        bbox=dict(boxstyle="round,pad=0.4", fc="#f4f7fa", ec=GREY, lw=0.8),
    )
    ax.set_xlim(0, 100)
    ax.set_xlabel(tr["bell_xlabel"])
    ax.set_ylabel(tr["bell_ylabel"])
    ax.set_title(tr["bell_title"])
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / lang / "turnout.png")
    plt.close(fig)


def fig_comet(lang: str, tr: dict) -> None:
    c = df[df["referendum"] == "preiskava"].copy()
    c["turnout"] = c["udelezba_prc"] * 100
    c["za"] = c["za_prc"] * 100
    fig, ax = plt.subplots(figsize=(9.6, 4.8), dpi=150)
    ax.scatter(c["turnout"], c["za"], s=c["upr"] / 55, color=BLUE, alpha=0.18, linewidths=0)
    bins = list(range(25, 100, 5))
    c["bin"] = pd.cut(c["turnout"], bins)
    m = c.groupby("bin", observed=True).apply(
        lambda g: pd.Series(
            {"x": (g["turnout"] * g["upr"]).sum() / g["upr"].sum(), "y": (g["za"] * g["velj"]).sum() / g["velj"].sum()}
        ),
        include_groups=False,
    )
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
    ax.legend(loc="lower right", fontsize=10, framealpha=0.9)
    ax.set_xlim(15, 100)
    ax.set_ylim(15, 95)
    ax.set_xlabel(tr["comet_xlabel"])
    ax.set_ylabel(tr["comet_ylabel"])
    ax.set_title(tr["comet_title"])
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / lang / "comet.png")
    plt.close(fig)


def fig_cross(lang: str, tr: dict) -> None:
    key = ["enota_st", "okraj_rpeid", "volisce_st"]
    piv = df.pivot_table(index=key, columns="referendum", values="za_prc") * 100
    wts = df.groupby(key)["velj"].sum()
    pairs = [
        ("preiskava", "socialna_pomoc"),
        ("preiskava", "volilna_pravica"),
        ("socialna_pomoc", "rtv_prispevek"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.3), dpi=150, sharex=True, sharey=True)
    for ax, (a, b) in zip(axes, pairs):
        sub = piv[[a, b]].dropna().join(wts.rename("w"), how="left")
        ax.scatter(sub[a], sub[b], s=6, color=BLUE, alpha=0.25, linewidths=0)
        wa, wb, ww = sub[a], sub[b], sub["w"]
        mwa = (wa * ww).sum() / ww.sum()
        mwb = (wb * ww).sum() / ww.sum()
        cov = (ww * (wa - mwa) * (wb - mwb)).sum()
        r = cov / ((ww * (wa - mwa) ** 2).sum() ** 0.5 * (ww * (wb - mwb) ** 2).sum() ** 0.5)
        ax.text(0.05, 0.93, f"r = {r:+.2f}", transform=ax.transAxes, fontsize=12,
                fontweight="bold", color=DARK)
        ax.set_xlabel(f"{tr['yes']}, % — {tr['names'][a]}", fontsize=9.5)
        ax.set_xlim(15, 95)
        ax.set_ylim(15, 95)
    axes[0].set_ylabel(f"{tr['yes']}, % — {tr['names']['socialna_pomoc']}", fontsize=9.5)
    axes[1].set_ylabel(f"{tr['yes']}, % — {tr['names']['volilna_pravica']}", fontsize=9.5)
    axes[2].set_ylabel(f"{tr['yes']}, % — {tr['names']['rtv_prispevek']}", fontsize=9.5)
    fig.suptitle(tr["cross_suptitle"], fontsize=12.5, fontweight="bold", y=1.0)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(OUT / lang / "cross.png")
    plt.close(fig)


# ── paradox figures (paradoxes.html): data, translations, functions ──────────

REFS = ["preiskava", "socialna_pomoc", "volilna_pravica", "rtv_prispevek"]

nat = pd.read_csv(ROOT / "data" / "derived" / "nacionalni_pregled.csv")

PX: dict[str, dict] = {}
for ref in REFS:
    d = df[df["referendum"] == ref]
    reg = d[d["upr"] > 0]
    early = d[d["volisce_st"] >= 900]
    nrow = nat[(nat.referendum == ref) & (nat.nivo == "slovenija")].iloc[0]
    okr = nat[(nat.referendum == ref) & (nat.nivo == "okraj")]
    reg_net = reg["za"].sum() - reg["proti"].sum()
    early_net = early["za"].sum() - early["proti"].sum()
    PX[ref] = {
        "winner": "za" if nrow.za > nrow.proti else "proti",
        "dist_za": int((okr.za > okr.proti).sum()),
        "dist_n": len(okr),
        "reversed": (okr.za > okr.proti).sum() > (okr.proti > okr.za).sum(),
        "precinct_net": int(reg_net),
        "early_net": int(early_net),
        "special_net": int((nrow.za - nrow.proti) - reg_net - early_net),
        "national_net": int(nrow.za - nrow.proti),
        "proti": int(nrow.proti),
        "quorum": float(nrow.upr / 5),
        "half": float(nrow.velj / 2),
        "margin_quorum": int(nrow.proti - nrow.upr / 5),
        "margin_majority": int(abs(nrow.za - nrow.proti)),
    }


def fmt_num(v: int, lang: str) -> str:
    s = f"{v:,}"
    if lang == "en":
        return s
    if lang == "hu":
        return s.replace(",", " ")
    return s.replace(",", ".")


PXT = {
"en": {
    "yes": "YES", "no": "NO",
    "ter_title": "Same votes, another rule: winner by majority of the 88 districts",
    "ter_xlabel": "Districts won by YES, % of 88",
    "ter_majority": "majority: 45+ districts",
    "ter_reversal": "← reversal",
    "ter_natl": "nationally:",
    "dec_title": "Who decided it: on election day YES won all four questions",
    "dec_ylabel": "Net margin, YES − NO",
    "dec_l1": "election-day precincts", "dec_l2": "early voting", "dec_l3": "postal / abroad",
    "dec_natl": "national result",
    "quo_title": "Rejection needs BOTH thresholds — NO cleared them only where it won",
    "quo_ylabel": "Votes",
    "quo_l1": "NO votes", "quo_l2": "Art. 90 quorum (1/5 of electorate)",
    "quo_l3": "half of valid votes (majority threshold)",
    "w_quorum": "quorum", "w_majority": "majority",
    "w_rejected": "rejected", "w_approved": "approved",
},
"sl": {
    "yes": "ZA", "no": "PROTI",
    "ter_title": "Enaki glasovi, drugo pravilo: zmagovalec po večini 88 okrajev",
    "ter_xlabel": "Okraji, kjer je zmagal ZA, % od 88",
    "ter_majority": "večina: 45+ okrajev",
    "ter_reversal": "← obrat",
    "ter_natl": "državno:",
    "dec_title": "Kdo je odločal: na dan glasovanja je ZA zmagal pri vseh štirih vprašanjih",
    "dec_ylabel": "Neto razlika, ZA − PROTI",
    "dec_l1": "volišča na dan glasovanja", "dec_l2": "predčasno glasovanje",
    "dec_l3": "pošta / tujina",
    "dec_natl": "državni izid",
    "quo_title": "Zavrnitev zahteva OBE meji — PROTI ju je presegel le tam, kjer je zmagal",
    "quo_ylabel": "Glasovi",
    "quo_l1": "glasovi PROTI", "quo_l2": "kvorum po 90. členu (1/5 volivcev)",
    "quo_l3": "polovica veljavnih glasov (meja večine)",
    "w_quorum": "kvorum", "w_majority": "večina",
    "w_rejected": "zavrnjen", "w_approved": "sprejet",
},
"hr": {
    "yes": "ZA", "no": "PROTIV",
    "ter_title": "Isti glasovi, drugo pravilo: pobjednik po većini 88 kotara",
    "ter_xlabel": "Kotari gdje je pobijedio ZA, % od 88",
    "ter_majority": "većina: 45+ kotara",
    "ter_reversal": "← obrat",
    "ter_natl": "državno:",
    "dec_title": "Tko je odlučivao: na dan glasovanja ZA je pobijedio na sva četiri pitanja",
    "dec_ylabel": "Neto razlika, ZA − PROTIV",
    "dec_l1": "birališta na dan glasovanja", "dec_l2": "rano glasovanje",
    "dec_l3": "pošta / inozemstvo",
    "dec_natl": "državni ishod",
    "quo_title": "Odbačaj zahtijeva OBA praga — PROTIV ih je prešao samo gdje je pobijedio",
    "quo_ylabel": "Glasovi",
    "quo_l1": "glasovi PROTIV", "quo_l2": "kvorum po čl. 90 (1/5 birača)",
    "quo_l3": "polovica važećih glasova (prag većine)",
    "w_quorum": "kvorum", "w_majority": "većina",
    "w_rejected": "odbačen", "w_approved": "prihvaćen",
},
"it": {
    "yes": "SÌ", "no": "CONTRO",
    "ter_title": "Stessi voti, altra regola: il vincitore per maggioranza degli 88 collegi",
    "ter_xlabel": "Collegi vinti dal SÌ, % su 88",
    "ter_majority": "maggioranza: 45+ collegi",
    "ter_reversal": "← inversione",
    "ter_natl": "nazionalmente:",
    "dec_title": "Chi ha deciso: il giorno del voto il SÌ ha vinto su tutti e quattro i quesiti",
    "dec_ylabel": "Scarto netto, SÌ − CONTRO",
    "dec_l1": "sezioni del giorno del voto", "dec_l2": "voto anticipato",
    "dec_l3": "posta / estero",
    "dec_natl": "esito nazionale",
    "quo_title": ("Il rigetto richiede ENTRAMBE le soglie — "
                  "il CONTRO le ha superate solo dove ha vinto"),
    "quo_ylabel": "Voti",
    "quo_l1": "voti CONTRO", "quo_l2": "quorum dell'art. 90 (1/5 degli elettori)",
    "quo_l3": "metà dei voti validi (soglia di maggioranza)",
    "w_quorum": "quorum", "w_majority": "maggioranza",
    "w_rejected": "respinto", "w_approved": "approvato",
},
"hu": {
    "yes": "IGEN", "no": "ELLEN",
    "ter_title": "Ugyanazok a szavazatok, más szabály: győztes a 88 körzet többsége szerint",
    "ter_xlabel": "Az IGEN által nyert körzetek, % a 88-ból",
    "ter_majority": "többség: 45+ körzet",
    "ter_reversal": "← megfordulás",
    "ter_natl": "országosan:",
    "dec_title": "Ki döntött: a szavazás napján az IGEN nyert mind a négy kérdésen",
    "dec_ylabel": "Nettókülönbség, IGEN − ELLEN",
    "dec_l1": "szavazókörök a szavazás napján", "dec_l2": "előre szavazás",
    "dec_l3": "postai / külföldi",
    "dec_natl": "országos eredmény",
    "quo_title": "Az elutasításhoz MINDKÉT küszöb kell — az ELLEN csak ott lépte túl, ahol nyert",
    "quo_ylabel": "Szavazatok",
    "quo_l1": "ELLEN-szavazatok", "quo_l2": "a 90. cikk szerinti kvórum (a választók 1/5-e)",
    "quo_l3": "az érvényes szavazatok fele (többségi küszöb)",
    "w_quorum": "kvórum", "w_majority": "többség",
    "w_rejected": "elutasítva", "w_approved": "elfogadva",
},
}


def fig_px_territory(lang: str, tr: dict, t: dict) -> None:
    fig, ax = plt.subplots(figsize=(9.6, 4.4), dpi=150)
    y = list(range(len(REFS)))
    za = [100 * PX[r]["dist_za"] / PX[r]["dist_n"] for r in REFS]
    colors = [GREEN if PX[r]["winner"] == "za" else RED for r in REFS]
    labels = [f"{tr['names'][r]}\n{t['ter_natl']} {PX[r]['winner'].upper()}" for r in REFS]
    ax.barh(y, za, color=colors, alpha=0.85, height=0.62, zorder=3)
    ax.axvline(50, color=DARK, linestyle="--", linewidth=1.6, zorder=4)
    ax.text(50.7, -0.6, t["ter_majority"], color=DARK, fontsize=10)
    for i, r in enumerate(REFS):
        ax.text(za[i] - 2, i,
                f"{t['yes']} {PX[r]['dist_za']} : {PX[r]['dist_n'] - PX[r]['dist_za']} {t['no']}"
                + (f"  {t['ter_reversal']}" if PX[r]["reversed"] else ""),
                va="center", ha="right", fontsize=10.5, color="white",
                fontweight="bold", zorder=5)
    ax.set_yticks(y, labels, fontsize=10)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel(t["ter_xlabel"])
    ax.set_title(t["ter_title"])
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / lang / "territory.png")
    plt.close(fig)


def fig_px_decomposition(lang: str, tr: dict, t: dict) -> None:
    fig, ax = plt.subplots(figsize=(9.6, 4.6), dpi=150)
    x = list(range(len(REFS)))
    width = 0.27
    series = [("precinct_net", t["dec_l1"], BLUE),
              ("early_net", t["dec_l2"], "#8a6116"),
              ("special_net", t["dec_l3"], GREY)]
    for k, (key, label, color) in enumerate(series):
        vals = [PX[r][key] for r in REFS]
        ax.bar([i + (k - 1) * width for i in x], vals, width=width, label=label,
               color=color, alpha=0.85, zorder=3)
    top = max(max(PX[r]["precinct_net"], PX[r]["early_net"], PX[r]["special_net"])
              for r in REFS)
    for i, r in enumerate(REFS):
        ax.text(i, top + 16000,
                f"{PX[r]['winner'].upper()} +{fmt_num(abs(PX[r]['national_net']), lang)}",
                ha="center", fontsize=10, color=DARK, fontweight="bold")
    ax.axhline(0, color=DARK, linewidth=1.2)
    ax.set_xticks(x, [tr["names"][r] for r in REFS], fontsize=10)
    ax.set_yticks(list(range(-40000, 240001, 40000)))
    ax.yaxis.set_major_formatter(lambda v, _: f"{v / 1000:+.0f}k" if v else "0")
    ax.set_ylim(-48000, top + 38000)
    ax.set_ylabel(t["dec_ylabel"])
    ax.set_title(t["dec_title"])
    ax.legend(fontsize=10, framealpha=0.9, loc="upper center", ncol=3,
              bbox_to_anchor=(0.5, -0.16))
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(OUT / lang / "decomposition.png", bbox_inches="tight")
    plt.close(fig)


def fig_px_quorum(lang: str, tr: dict, t: dict) -> None:
    fig, ax = plt.subplots(figsize=(9.6, 4.6), dpi=150)
    x = list(range(len(REFS)))
    protis = [PX[r]["proti"] for r in REFS]
    quorums = [PX[r]["quorum"] for r in REFS]
    halves = [PX[r]["half"] for r in REFS]
    ax.bar(x, protis, color=RED, alpha=0.8, width=0.55, zorder=3, label=t["quo_l1"])
    ax.scatter(x, quorums, marker="_", s=1400, color=DARK, linewidths=2.6,
               zorder=4, label=t["quo_l2"])
    ax.scatter(x, halves, marker="_", s=1400, color=GREY, linewidths=2.6,
               zorder=4, label=t["quo_l3"])
    for i, r in enumerate(REFS):
        rej = PX[r]["winner"] == "proti"
        maj = (f"+{fmt_num(PX[r]['margin_majority'], lang)}" if rej
               else f"−{fmt_num(PX[r]['margin_majority'], lang)}")
        ax.text(i, max(protis[i], halves[i]) + 14000,
                f"{t['w_quorum']} +{fmt_num(PX[r]['margin_quorum'], lang)}\n"
                f"{t['w_majority']} {maj}\n"
                f"{t['w_rejected'] if rej else t['w_approved']}",
                ha="center", fontsize=9, color=DARK, linespacing=1.35)
    ax.set_xticks(x, [tr["names"][r] for r in REFS], fontsize=10)
    ax.set_ylim(0, max(protis) * 1.42)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v / 1000:.0f}k")
    ax.set_ylabel(t["quo_ylabel"])
    ax.set_title(t["quo_title"])
    ax.legend(fontsize=9.5, framealpha=0.9, loc="upper center", ncol=3,
              bbox_to_anchor=(0.5, -0.18))
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(OUT / lang / "quorum.png", bbox_inches="tight")
    plt.close(fig)


for lang, tr in T.items():
    (OUT / lang).mkdir(parents=True, exist_ok=True)
    fig_turnout(lang, tr)
    fig_comet(lang, tr)
    fig_cross(lang, tr)
    fig_px_territory(lang, tr, PXT[lang])
    fig_px_decomposition(lang, tr, PXT[lang])
    fig_px_quorum(lang, tr, PXT[lang])
    print(f"{lang}: turnout, comet, cross, territory, decomposition, quorum "
          f"-> site/sloveniya-referendum-2026/img/{lang}/")

# the old English images at the img/ root are no longer needed
for stale in ["turnout.png", "comet.png", "cross.png"]:
    p = OUT / stale
    if p.exists():
        p.unlink()
        print("removed stale", p.name)
