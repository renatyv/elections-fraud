"""Электоральные «отпечатки пальцев» (Klimek, Yegorov, Hanel, Thurner, PNAS 2012).

2D-распределение (явка × доля за партию), взвешенное по числу избирателей.
Честные данные — компактные кластеры около гауссовых; фальсификации дают
«хвост» к высокой явке и высокому результату. Смесь двух 2D-гауссиан:
вторая компонента с высокой явкой и высоким результатом трактуется
как аномальный кластер, её вес — оценка масштаба.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
from sklearn.mixture import GaussianMixture

from .data import ElectionData


@dataclass
class FingerprintResult:
    party: str
    # параметры компонент смеси (0 — основная, 1 — аномальная, если разделена)
    weight_anom: float
    mean_anom: tuple[float, float]
    mean_main: tuple[float, float]
    anom_cluster_voters: int
    anom_cluster_votes_party: int
    total_voters: int
    separated: bool  # разделилась ли смесь на два кластера

    def to_dict(self) -> dict:
        return asdict(self)


def fingerprint_mixture(
    data: ElectionData,
    party: str,
    seed: int = 42,
) -> FingerprintResult:
    """Смесь 2D-гауссиан на (явка, доля партии), взвешенная по избирателям.

    Аномальной считается отдельная компонента с заметно большей явкой
    (разница средних > 2 п.п.) и весом > 1 %.
    """
    rng = np.random.default_rng(seed)
    x = data.turnout.to_numpy(dtype=float)
    y = data.share(party).to_numpy(dtype=float)
    w = data.registered.to_numpy(dtype=float)
    ok = np.isfinite(y) & (data.df["voted"].to_numpy() > 0)
    x, y, w = x[ok], y[ok], w[ok]

    # sklearn 1.9 не принимает sample_weight в GaussianMixture.fit —
    # взвешивание по избирателям делаем ресэмплингом территорий
    p = w / w.sum()
    sample_size = min(50_000, max(20_000, 10 * len(x)))
    idx = rng.choice(len(x), size=sample_size, replace=True, p=p)
    gm = GaussianMixture(n_components=2, covariance_type="full", random_state=seed,
                         n_init=3, max_iter=300, reg_covar=1e-3)
    gm.fit(np.column_stack([x[idx], y[idx]]))
    means = gm.means_
    # аномальная компонента — с большей явкой
    anom_idx = int(np.argmax(means[:, 0]))
    main_idx = 1 - anom_idx
    weight_anom = float(gm.weights_[anom_idx])

    # кластеры по апостериорным вероятностям
    labels = gm.predict(np.column_stack([x, y]))
    anom_mask = labels == anom_idx
    anom_voters = int(w[anom_mask].sum())
    anom_votes_party = int(data.df[party].to_numpy()[ok][anom_mask].sum())

    # кластер фальсификаций по Klimek et al. — «вправо-вверх»: выше явка
    # И выше результат; раскол только по явке или только по результату —
    # территориальная неоднородность, не сигнал фальсификаций
    separated = bool(
        weight_anom > 0.01
        and means[anom_idx, 0] - means[main_idx, 0] > 2.0
        and means[anom_idx, 1] > means[main_idx, 1]
    )
    return FingerprintResult(
        party=party.removeprefix("votes:"),
        weight_anom=weight_anom,
        mean_anom=(float(means[anom_idx, 0]), float(means[anom_idx, 1])),
        mean_main=(float(means[main_idx, 0]), float(means[main_idx, 1])),
        anom_cluster_voters=anom_voters,
        anom_cluster_votes_party=anom_votes_party,
        total_voters=int(w.sum()),
        separated=bool(separated),
    )


def to_dict(res: FingerprintResult) -> dict:
    return res.to_dict()
