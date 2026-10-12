# Research foundation and implementation boundaries

Research access date: 11 October 2026. The supplied attachment is the application brief; it contains no paper PDFs. Publicly accessible primary material was therefore consulted. This document records research guidance, not evidence of field validation or a claim that this prototype reproduces the papers.

## 1. Mixed filtering and sensor placement

J. S. Lee, S. Choi, S.-S. Kim, C. Park, and Y. G. Kim, “A Mixed Filtering Approach for Track Condition Monitoring Using Accelerometers on the Axle Box and Bogie,” *IEEE Transactions on Instrumentation and Measurement*, 61(3), 749–758, 2012. [DOI](https://doi.org/10.1109/TIM.2011.2170377).

**Access limit:** The author-upload publication page and abstract were accessible; the publisher DOI and author PDF fetch failed. The complete paper was not read. [Author-upload record](https://www.researchgate.net/publication/220408930_A_Mixed_Filtering_Approach_for_Track_Condition_Monitoring_Using_Accelerometers_on_the_Axle_Box_and_Bogie).

The abstract describes stable displacement estimation and wavelength-band classification from lateral and vertical acceleration at axle boxes and bogies, with comparison against commercial geometry measurements. This supports treating mounting location as relevant to interpretation. The requested state-estimation, bandpass, and compensation direction comes from the supplied brief; the inaccessible equations were not independently verified here.

**Adaptation boundary:** Use separate acceleration channels and causal filtering. Avoid presenting double-integrated acceleration as measured track geometry. A generic high-pass or bandpass filter is not Lee's compensated mixed-filter estimator. Unless a model-based estimator and its compensation are explicitly implemented and validated, displacement reconstruction is omitted.

## 2. Wavelet localization

M. Molodova, Z. Li, A. Núñez, and R. Dollevoet, “Automatic Detection of Squats in Railway Infrastructure,” *IEEE Transactions on Intelligent Transportation Systems*, 15(5), 1980–1990, 2014. [DOI](https://doi.org/10.1109/TITS.2014.2307955). [TU Delft full paper](https://ocw.tudelft.nl/wp-content/uploads/Molodova_et_al_TITS.pdf).

**Access:** Public full-paper text was consulted, particularly Sections III–V.

The method uses Morlet continuous wavelets and scale-averaged wavelet power to localize responses. The studied system uses 200–400 Hz and 1000–2000 Hz bands for light defects; these are track-specific choices. Processing also addresses wheel-periodic interference and spatial alignment of repeated signals. Welds and insulated joints can exceed a detection threshold. The paper's reported field performance is not a result for RAILFORM.

**Adaptation boundary:** Compute a genuine CWT from acquired windows and expose its frequency scale. Use independently documented project bands and healthy synthetic reference thresholds. A simple mean of coefficient power must be named wavelet energy, not asserted to reproduce the paper's normalized scale-averaged wavelet power. Distinguish signal localization from verified defect classification.

## 3. Longitudinal sensing and confounders

Z. Li, M. Molodova, A. Núñez, and R. Dollevoet, “Improvements in Axle Box Acceleration Measurements for the Detection of Light Squats in Railway Infrastructure,” *IEEE Transactions on Industrial Electronics*, 62(7), 4385–4397, 2015. [DOI](https://doi.org/10.1109/TIE.2015.2389761). [TU Delft bibliographic record](https://research.tudelft.nl/en/publications/improvements-in-axle-box-acceleration-measurements-for-the-detect/). [Full author-upload text](https://www.researchgate.net/publication/272590516_Improvements_in_Axle_Box_Acceleration_Measurements_for_the_Detection_of_Light_Squats_in_Railway_Infrastructure).

**Access:** Author-upload full-paper text was consulted, including instrumentation, coherent averaging, and wheel-defect sections.

The study explains enhanced light-defect sensitivity from longitudinal ABA, uses multiple sensors and aligned repeated measurements to reduce noise and missed contacts, and addresses wheel-periodic disturbances. Longitudinal sensing is not immunity to interference. Its repeated-pass averaging uses alignment; simply averaging unaligned time windows does not provide the same evidence. Severe wheel defects are outside the paper's considered cases.

**Adaptation boundary:** Maintain vertical and longitudinal evidence separately, report agreement, and group repeat observations by measured chainage. Simulate wheel impacts according to wheel phase and test periodicity from measurements. Spatial recurrence and periodicity remain supporting clues, not definitive root-cause proof. Do not claim reproduction of the paper's instrumentation, hammer tests, finite-element analyses, or field measurements.

## Prototype design constraints

The following are project engineering choices proposed from the brief and research context, not reported paper results. Final implemented values belong in the detector configuration and methodology documentation.

1. Keep ground truth in an evaluation-only structure. Detector arguments may include samples, sample times, speed, measured position and quality flags; they must not include injected labels, defect positions or preset identifiers.
2. Use acceleration units of m/s² throughout. PSD units are (m/s²)²/Hz. Label wavelet power according to the actual library normalization; do not imply a calibrated physical spectral density unless established.
3. Require every configured frequency to lie below Nyquist. For 12.8 kHz acquisition, 6.4 kHz is Nyquist; leave transition-band margin. UI delivery frequency is independent of sample rate.
4. Stateful live filters retain their state across chunks. Centered CWT can be computed on an already acquired trailing window; alerts become available only at that window's end. Do not assign zero detection delay to an earlier within-window event. CWT boundaries have edge effects.
5. Derive thresholds only from healthy training runs. Split seeds/runs before constructing overlapping windows. Use disjoint held-out seeds, including difficult confounders and degraded sensors, for evaluation.
6. Define anomaly score as deviation from baseline, severity as a documented heuristic, and evidence strength as sensor agreement plus quality and recurrence. None is automatically a calibrated probability.
7. Missing samples are missing evidence. Preserve a quality mask even if a bounded fill is needed for a filter. Gate unreliable condition inference and report quality alerts separately. Unobserved corridor sections remain unknown.
8. Detect periodic wheel-like disturbances from spacing or autocorrelation of measured impacts, with speed conversion and finite observation limits. Never choose the label from the simulator preset. A spatially periodic rail condition can still be a confounder.
9. Merge overlapping-window detections with explicit hysteresis, grouping tolerance and cooldown. Repeated-pass evidence counts distinct passes, not duplicate windows.
10. Evaluate events using one-to-one matching within a disclosed distance tolerance. Report unmatched detections as false positives and unmatched truth events as misses. False alarms/km needs actual observed distance; event detection has no natural true-negative count unless an independent segmentation rule is specified.
11. Report classification separately on a defined population (for example matched detected events). Missing detections must not silently disappear from any end-to-end classification claim. Processing latency is wall-clock execution time; detection delay is simulation time from event onset until evidence is available.

## Claims deliberately excluded

This prototype does not establish rail cracks, remaining useful life, operational speed limits, maintenance deadlines, certified safety decisions, or validated failure prediction. A physics-inspired signal generator is not a validated vehicle–track solver. Synthetic held-out results characterize that generator and detector configuration only. Real deployment would require calibrated sensors, synchronization and localization analysis, independent inspection labels, multiple vehicles and routes, domain-shift testing, and a separate operational safety process.

The paper access limitation in Section 1 remains unresolved. Obtaining the full Lee paper is required before claiming an equation-level reproduction or complete review of all three full papers.
