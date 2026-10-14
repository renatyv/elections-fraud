# The Shpilkin Method and Other Statistical Methods for Detecting Election Fraud

*Brief analytical report. Compiled: 2026-10-10.*

---

## 1. Context: election forensics

**Election forensics** is a field at the intersection of statistics, physics, and political science that looks for traces of manipulation in official election results: anomalous distributions of turnout and outcomes, "adjustment" toward round numbers, unnatural distributions of digits in protocol records. The key idea: honest elections leave a "noisy" statistical picture, while interference (ballot stuffing, extra ballots, rewritten protocols) leaves reproducible statistical traces.

The historical Russian precursor is the work of **A. Sobyanin and V. Sukhovolsky (mid-1990s)**, who were the first to systematically search for turnout anomalies in precinct-level (UIK) data. The methods took their modern form after the 2011 State Duma elections, when independent researchers gained convenient access to protocol data from all precinct election commissions.

---

## 2. The Shpilkin method

**Author:** Sergei Shpilkin, physicist; since the late 2000s he has been analyzing Russian federal elections (published in particular in «Troitsky Variant — Nauka», trv-science.ru; co-author of several peer-reviewed papers).

### 2.1. Empirical regularities of "honest" elections

The method relies on three robust properties of elections without mass manipulation:

1. **The turnout distribution** (across precincts or across the number of voters) is a smooth unimodal curve, close to normal/lognormal, without a heavy right tail.
2. **Independence of outcome from turnout**: the share of votes for a candidate/party is roughly the same at any turnout level (mobilization of supporters and opponents proceeds symmetrically). On a "turnout × outcome" diagram this yields a compact horizontal cloud.
3. **Absence of prominent "round" values**: turnout of 60/70/75/80 % and outcomes of 89/90 % occur no more often than neighboring values.

### 2.2. What looks like a fingerprint of fraud

- **The "comet tail"**: on a "turnout × outcome" scatterplot, the cloud stretches up and to the right — in precincts with anomalously high turnout (80–100 %), the share for the "party of power" rises sharply. At the same time, opponents' results often **fall** as turnout grows (vote transfer).
- **A heavy right tail and peaks at whole percentages** in the turnout distribution (anomalously many precincts at exactly 60, 70, 75, 80, 85, 90, 95 % turnout and with round outcomes).
- Growth in the correlation between turnout and the "party of power" outcome.

### 2.3. Mathematical core of the anomalous-votes estimate

1. A histogram is built of **the number of votes for a candidate as a function of turnout** (0.1–1 % bins in turnout; weighted by the number of registered voters, not by the number of precincts).
2. The "honest core" is isolated — the bulk of the distribution described by a smooth model; an assumption is made that manipulation only **adds** turnout and votes (shifting precincts up and to the right), i.e. there are no "negative" falsifications.
3. The anomalous component = observed distribution minus the "honest core" model; the integral of the difference yields **an estimate of the number of stuffed/shifted votes** and makes it possible to recompute the outcome without the anomalous precincts.

### 2.4. Known estimates (from Shpilkin's publications and independent media)

- State Duma elections **2011**: ~14 million anomalous votes for "United Russia".
- Presidential election **2012**: ~10–12 million anomalous votes for Putin.
- Presidential election **2018**: ~10 million.
- Presidential election **2024**: by independent estimates, on the order of 20+ million (widely cited in the media; exact figures depend on model assumptions).

These figures are model estimates under the method's assumptions (see section 4), not facts established in court.

---

## 3. Other methods

| # | Method | Idea | Key papers |
|---|--------|------|------------|
| 1 | **Electoral "fingerprints" + mixture models** | A 2D histogram (turnout × share for a party); honest data is described by a mixture of Gaussian clusters, falsified precincts form a separate "fraudulent" cluster; the mixture share = the scale of the anomaly | Klimek, Yegorov, Hanel, Thurner, *PNAS* 109(41), 2012 (Russia, Uganda vs Switzerland as control) |
| 2 | **Integer peaks** | Precincts with an exactly integer percentage of turnout/outcome occur many times more often than expected — a trace of protocols "drawn" by humans | Kobak, Shpilkin, Pshenichnikov, *Annals of Applied Statistics* 10(1), 2016 (arXiv:1410.6059); *Significance* 15(3), 2018 "Putin's peaks" |
| 3 | **2D correlation analysis** | Joint analysis of turnout↔outcome correlations across all candidates and regions | Kobak, Shpilkin, Pshenichnikov, arXiv:1205.0741 (2012) |
| 4 | **Benford's law (second-digit test)** | In naturally occurring counts, second digits follow Benford's law; hand-made numbers deviate | Mebane (2006); Deckert, Myagkov, Ordeshook (2011) |
| 5 | **Last-digit test** | The last digits of honest counts are uniform (0–9); fabricated ones are not | Beber, Scacco, *Political Analysis* 20(2), 2012 |
| 6 | **Ballot-serial-number statistics + forensics** | Analysis of the sequence of ballot submissions during multi-day voting reveals "batch" injections; verification of serial numbers of ballot batches (duplicates = a trace of interference) | Podlazov, Makarov, arXiv:2412.04535; *Electoral Politics*, 2025 |
| 7 | **Machine learning** | Classifiers trained on synthetic ("fake") and honest data to find anomalous precincts | Zhang, Alvarez, Levin, *PLOS ONE*, 2019 |
| 8 | **Comparison of "similar" precincts and neighbors** | Neighboring/socio-economically similar precincts should produce similar results; outliers are candidates for verification; comparison of precincts with and without observers | Myagkov, Ordeshook, Shakin, *The Forensics of Election Fraud*, Cambridge UP, 2009 |
| 9 | **Turnout dynamics during the day** | The "evening influx" — an anomalous increase in turnout and in the "party of power" outcome toward the end of the day / on later days of multi-day voting | observer practice + Podlazov & Makarov (2025) |
| 10 | **Non-statistical "anchors"** | Exit polls, parallel vote counts from protocol copies, webcams, discrepancies between UIK/TIK/CIK data | observer networks («Golos» and others) |

Methods 1–3 are genetically related to the Shpilkin method (he is a co-author of papers 2–3); methods 4–5 are "digit" tests from classical election forensics; method 6 was the first to combine statistics with physical evidence.

---

## 4. Limitations and criticism

- **The "turnout ↔ outcome" correlation is non-specific**: a similar relationship occurs in elections not suspected of fraud (for example, in the United Kingdom — due to heterogeneity of constituencies and mobilization).
- **Benford tests are contentious**: Mebane himself warned that they may mistake tactical voting for fraud; the expert community considers them a weak instrument.
- **Electorate heterogeneity** (urban/rural, regions) by itself generates multidimensionality of the distributions and can imitate "tails" — hence the need for control countries/elections.
- **Estimates of anomalous votes depend on model assumptions** (the shape of the "honest core", the ban on "negative" falsifications) — this is an estimate of magnitude, not an exact number.
- **Statistics show abnormality, but not mechanism**: it does not prove *who* interfered or *how*. The gold standard is a combination of statistical anomalies with documentary/forensic evidence (as in the Podlazov–Makarov paper, where 8 of 9 statistical conclusions matched the physical evidence).

---

## 5. Sources

- Kobak D., Shpilkin S., Pshenichnikov M. S. **Integer percentages as electoral falsification fingerprints** // Annals of Applied Statistics, 10(1), 2016 — [arXiv:1410.6059](https://arxiv.org/abs/1410.6059)
- Kobak D., Shpilkin S., Pshenichnikov M. S. **Putin's peaks: Russian election data revisited** // Significance, 15(3), 2018 — [arXiv:1804.09495](https://arxiv.org/abs/1804.09495)
- Kobak D., Shpilkin S., Pshenichnikov M. S. **Statistical anomalies in 2011–2012 Russian elections revealed by 2D correlation analysis** — [arXiv:1205.0741](https://arxiv.org/abs/1205.0741)
- Klimek P., Yegorov Y., Hanel R., Thurner S. **Statistical detection of systematic election irregularities** // PNAS, 109(41), 2012 — [DOI: 10.1073/pnas.1206343109](https://www.pnas.org/doi/10.1073/pnas.1206343109)
- Podlazov A., Makarov V. **A dual approach to proving electoral fraud using statistics and forensic evidence** — [arXiv:2412.04535](https://arxiv.org/abs/2412.04535); Electoral Politics, 2025
- Beber B., Scacco A. **What the Numbers Say: A Digit-Based Test for Election Fraud** // Political Analysis, 20(2), 2012
- Myagkov M., Ordeshook P., Shakin D. **The Forensics of Election Fraud: Russia and Ukraine**. Cambridge University Press, 2009
- Zhang, Alvarez, Levin. Machine learning for detecting election anomalies // PLOS ONE, 2019
- Wikipedia: [Election forensics](https://en.wikipedia.org/wiki/Election_forensics) (overview and references to Mebane 2006, Deckert et al. 2011); [Нарушения на выборах — признаки фальсификаций](https://ru.wikipedia.org/wiki/%D0%A4%D0%B0%D0%BB%D1%8C%D1%81%D0%B8%D1%84%D0%B8%D0%BA%D0%B0%D1%86%D0%B8%D1%8F_%D0%B8%D1%82%D0%BE%D0%B3%D0%BE%D0%B2_%D0%B3%D0%BE%D0%BB%D0%BE%D1%81%D0%BE%D0%B2%D0%B0%D0%BD%D0%B8%D1%8F) (ru)
- Sergei Shpilkin's publications in «Troitsky Variant — Nauka»: [trv-science.ru](https://trv-science.ru/)
