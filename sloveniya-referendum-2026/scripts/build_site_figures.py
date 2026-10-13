# Фигуры для публичной страницы сайта репозитория — по комплекту на каждый
# язык (en, sl, hr, it, hu), данные — data/derived/volisca_all.csv. Запуск из
# каталога проекта:
#   uv run python scripts/build_site_figures.py
# Выход: <репо>/site/sloveniya-referendum-2026/img/<lang>/{turnout,comet,cross}.png
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
GREY = "#8a97a5"
CUT = 70.0  # граница честного спада (q99.5 контролов), см. отчёт, раздел 1

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
df = df[df["upr"] > 0]  # обычные участки, без досрочных точек


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


for lang, tr in T.items():
    (OUT / lang).mkdir(parents=True, exist_ok=True)
    fig_turnout(lang, tr)
    fig_comet(lang, tr)
    fig_cross(lang, tr)
    print(f"{lang}: turnout, comet, cross -> site/sloveniya-referendum-2026/img/{lang}/")

# прежние английские картинки в корне img/ больше не нужны
for stale in ["turnout.png", "comet.png", "cross.png"]:
    p = OUT / stale
    if p.exists():
        p.unlink()
        print("removed stale", p.name)
