"""Election forensics: statistical methods for detecting election fraud.

Methods (following the survey "The Shpilkin method and other statistical
methods for detecting election fraud"):
- shpilkin: the Shpilkin method (turnout histogram, "honest core", estimate of anomalous votes)
- fingerprints: electoral fingerprints (Klimek et al., PNAS 2012)
- integer_peaks: integer peaks of turnout/result (Kobak et al., 2016)
- correlations: 2D turnout-result correlation analysis (Kobak et al., 2012)
- digit_tests: Benford's law (second digit) and the last-digit test (Beber-Scacco)
- neighbors: comparison of units against neighbours/surroundings (Myagkov-Ordeshook-Shakin)
- anomaly_ml: finding anomalous units with ML algorithms (Zhang et al., 2019)
"""

__version__ = "0.1.0"
