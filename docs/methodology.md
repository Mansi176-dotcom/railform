# Architecture and methodology

## Data flow and separation

`Simulator → quality mask → stateful causal bandpass → 0.4 s trailing window / 0.1 s hop → features → hysteresis + cooldown → deterministic explanation → SQLAlchemy/SQLite → bounded WebSocket queues → React`.

The simulator has a seeded NumPy generator. Track impacts are anchored in chainage; wheel impacts repeat every 2.8 m of wheel phase. Speed is km/h at the API and m/s internally. Baseline excitation includes speed dependence. Axle-box vertical/longitudinal and attenuated bogie vertical/lateral channels are distinct. This is a lightweight physics-inspired generator, not a validated dynamics solver. Bogie attenuation is a simplification, not a transfer function calibrated to a vehicle.

## Processing

Default 12,800 samples/s; selectable 10,000–25,600 samples/s. A third-order 3–4,000 Hz Butterworth bandpass uses retained SOS state. Invalid samples are forward-filled only for filter continuity; their original mask remains and suppresses condition inference above 5% missingness. Saturation above 1% also generates a quality alert. No future samples are used. Live filtering is causal. Wavelets use the completed trailing window; window edge artifacts remain possible.

Features: RMS, peak-to-peak, crest factor, Pearson kurtosis, Welch PSD, integrated 600–2,200 Hz energy, 3–20 Hz energy, and mean squared Morlet CWT coefficients at project frequencies 650, 900, 1,250, 1,800, 2,200 Hz. CWT extraction low-pass resamples by two; the UI scalogram low-pass resamples by four and displays 30–1,500 Hz. These are project parameters, not universally valid bands or an exact SAWP reproduction. CWT power is library-normalized coefficient power, not calibrated PSD. The UI PSD has units (m/s²)²/Hz.

Healthy seeds 11–13 establish each reference as four times the 99.5th percentile across their windows. Score is the larger longitudinal wavelet-energy/reference or low-frequency-energy/reference ratio. Trigger >1, rearm <0.65, cooldown 0.45 s. A 0.2 s acquired-evidence settling period allows periodicity discrimination before creating an event. There is no Isolation Forest or calibrated probability. The raw baseline uses absolute acceleration >1 m/s² with 0.65 rearm and the same cooldown.

Severity: score <2 low, 2–8 moderate, >=8 high. It is a research heuristic. Evidence: supporting vertical wavelet deviation plus acceptable quality; repeated spatial support requires distinct pass IDs in a 30 m chainage bin. This is coarse alignment, not coherent averaging. Label is based on measured low-frequency dominance or measured periodic peaks; it does not consume simulator truth. Periodic peaks use at least two spacings and coefficient of variation <0.2. Wheel/track discrimination remains ambiguous at onset and in short windows. Quality alarms are a separate event class.

## Timing, storage and integrity

Analysis timestamp is window end; event chainage is the largest longitudinal filtered peak. There is no zero-delay assumption. Processing latency times feature extraction and detection with a monotonic wall clock, excluding UI rendering and SQLite/file writes. WebSocket refresh is nominally 10 Hz; workload can reduce it. Acquisition sample rate is separate. Min/max chronological decimation retains extrema, but does not replace raw data for analysis.

One lifespan-managed worker prevents duplicate starts. Each client has a 3-packet queue; dropped packets increment an exposed buffer-gap counter. Feature history is 600 points, memory alerts 500, UI feed packets 100; disk raw ring is 32 compressed 0.1 s chunks. SQL feature records cycle across 300 summaries; persisted runs retain 20. Reset pauses, creates a new run and removes prior raw ring files, while archived SQL records survive until retention pruning. Quality gaps do not count toward coverage. Automatic reconnect uses a three-second retry and sequence numbers; stale indication follows four seconds without a packet.

## Evaluation

Held-out seeds 101–108, one per preset, each 11 simulated seconds, defect chainage 150 m. Split by seed occurs before overlapping windows. Evaluation uses a 25 m, one-to-one nearest-pair event match. Known periodic-wheel and quality *diagnostic labels* are excluded from track predictions; no truth is used by the detector. Unmatched predictions are false positives; unmatched injected track events are false negatives. Track event localization and detection delay are measured only for matches. Classification counts correct labels among matched events separately. This small synthetic suite cannot establish field performance. Event matching has no natural true-negative count; no fabricated TN matrix is shown.

## Explicit omissions and limitations

No displacement reconstruction, compensated mixed-filter state estimator, finite-element vehicle model, field calibration, operational recommendation, or exact reproduction of the three papers. No ML black-box model is needed for the interpretable core. UI stores the latest streaming window rather than an arbitrary historical raw-window archive. Sensor placement is schematic. Spatial bins and wheel-periodicity rules are heuristic; welds and joints can confound both. A completed demo summarizes detected events; held-out performance is computed separately in Evaluation to prevent labeling demo observations as independent test results.
