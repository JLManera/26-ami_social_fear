---
editor_options: 
  markdown: 
    wrap: 72
---

# **Social transmission of fear is disrupted by pharmaceutical pollution**

Jack L. Manera ^1,^\*, Eleanor R. Moore ^1^, Mirjam Amcoff ^2^, Bob B.M.
Wong ^1,†^, Jake M. Martin ^1,3,4,5,†^, Niclas Kolm ^6,†^, Michael G.
Bertram ^1,4,6,†^

^1^ *School of Biological Sciences, Monash University, Melbourne 3800,
Australia*

^2^ *Department of Aquatic Resources, Swedish University of Agricultural
Sciences, Uppsala 750 07, Sweden*

^3^ *School of Life and Environmental Sciences, Deakin University, Waurn
Ponds, Victoria 3216, Australia*

^4^ *Department of Wildlife, Fish, and Environmental Studies, Swedish
University of Agricultural Sciences, Umeå 901 83, Sweden*

^5^ *School of Agriculture, Biomedicine and Environment, La Trobe
University, Melbourne, Victoria 3086, Australia*

^6^ *Department of Zoology, Stockholm University, Stockholm 106 91,
Sweden*

This repository contains data wrangling and analysis scripts, and
supporting code for a study investigating how environmentally realistic
concentrations of amitriptyline affect the social transmission of fear
in guppies (*Poecilia reticulata*).

## Abstract

Social information transfer enables rapid responses to threats and
underpins collective predator avoidance across taxa. Yet whether the
growing threat of environmental pollutants, such as pharmaceuticals,
disrupt this process remains unknown. Here, we show that the widespread
antidepressant pollutant amitriptyline disrupts fear contagion—the
automatic matching of an individual’s behavioural state to that of a
frightened conspecific—in the guppy (*Poecilia reticulata*).
Amitriptyline exposure impaired the translation of socially acquired
threat information into behavioural responses and weakened behavioural
coupling with distressed conspecifics, while responses to directly
detected threats remained unaffected. These findings provide the first
evidence that pollution can degrade the dynamics of fear contagion—a
fundamental mechanism underpinning rapid, socially mediated responses to
predation risk. By eroding the integrity of social information networks,
psychoactive contaminants may compromise coordinated antipredator
behaviour and reshape predator–prey dynamics in polluted ecosystems,
revealing a previously unrecognised dimension of ecotoxicological risk.

## Study design bullet-points

-   **Species**: Female guppies (*Poecilia reticulata*)
-   **Sample size**: 324 individuals (162 observer fish + 162
    demonstrator fish)
-   **Treatments**:
    -   Control (0 ng/L amitriptyline, 54 observer fish)
    -   Low-dose (31 ng/L amitriptyline, 54 observer fish)
    -   High-dose (175 ng/L amitriptyline, 54 observer fish)
-   **Exposure duration**: 11 days
-   **Information conditions**:
    -   *Social information*: Dermal alarm cue delivered to
        demonstrators only (n = 27 per treatment group)
    -   *Combined information*: Dermal alarm cue delivered to both
        observer and demonstrators (n = 27 per treatment)
-   **Demonstrators**: Shoals of 3 unexposed fish; each shoal tested
    with one observer from each treatment group
-   **Trial structure**: 20-minute baseline recording, dermal alarm cue
    delivery, then 90-minute threat response recording

## Repository Structure

```         
├── 26-analysis-ami_social_fear.qmd            # Main analysis script
├── 26-data_wrangling-ami_social_fear.qmd      # Data processing pipeline
├── 26-water_analysis-ami_social_fear.qmd      # Water sample analysis
├── 26-ami_social_fear.Rproj                   # RStudio project file
├── r_package_versions.md                      # R package versions used
│
├── 1-media/                                   # Media files (not tracked in git)
│   ├── 1-videos/                              # Raw experimental videos
│   ├── 2-photos/                              # Photos (e.g. fish morphometric images)
│   └── 3-overlays/                            # Tracking overlay videos
│
├── 2-data/                                    # Data files
│   ├── BLINDING_KEY.csv                       # Treatment blinding key for blinded analysis
│   ├── morphs.csv                             # Fish morphometric data
│   ├── pixel_distances.csv                    # Video calibration data
│   ├── summary_data.csv                       # Trial-level summary metrics
│   ├── temporal_data.csv                      # Time-series data (not in git)
│   ├── water_analysis_results.csv             # Water sample chemical analysis
│   ├── 1-raw_tracks/                          # Raw tracking output (not in git)
│   ├── 2-smoothed_tracks/                     # Intermediate processed tracks (not in git)
│   ├── 3-behaviour_tracks/                    # Final processed tracks (not in git)
│   └── 4-models/                              # Fitted Bayesian models (not in git)
│
├── 3-figs/                                    # Figures
│   ├── Fig.1.png                              # Main text Figure 1
│   ├── Fig.2.png                              # Main text Figure 2
│   ├── figure1.png                            # Working version of Figure 1
│   ├── figure2.png                            # Working version of Figure 2
│   ├── supplementary_water_concs.png          # Supplementary water concentration figure
│   ├── Supplementary_Tables.docx              # Supplementary tables document
│   └── spatial_checks/                        # Tracking quality and tank edge visualisations (not in git)
│
└── 4-assisting_code/                          # Helper scripts
    ├── batch_tracker.py                       # Batch video tracking automation
    ├── calibrator.py                          # Pixel-to-cm calibration tool
    ├── glitch_detection_app.py                # Track error detection GUI
    ├── overlay_smoothed_tracks.py             # Create tracking overlay videos
    ├── stationary_fish_tracker.py             # Track static fish positions
    └── requirements.txt                       # Python dependencies

```

## Data Files

### 1. `summary_data.csv`

Trial-level summary statistics computed from the trajectory data. Each
row represents one fish-trial combination.

| Column | Description |
|------------------------------------|------------------------------------|
| `session_name` | Unique trial identifier (e.g., `d1-t1-c1-t-1l2-d`) |
| `day`, `trial`, `camera` | Experimental day, trial number, and camera ID |
| `phase` | Recording phase (`baseline` or `trial`) relative to cue |
| `ID` | Fish identifier |
| `treatment` | Blinded amitriptyline treatment code (control, low, or high) |
| `information` | Blinded information condition (social, or combined) |
| `duration_s` | Total recording duration in seconds |
| `duration_m` | Total recording duration in minutes |
| `total_time_moving` | Time spent moving (min) |
| `prop_time_moving` | Proportion of time spent moving |
| `prop_time_moving_ind2`, `prop_time_moving_ind3`, `prop_time_moving_ind4` | Proportion of time spent moving for demonstrator individuals 2–4 |
| `prop_time_moving_demonstrators` | Aggregated proportion of time spent moving across all demonstrators |
| `latency_to_moving` | Time to first movement after stimulus (min) |
| `latency_to_moving_ind2`, `latency_to_moving_ind3`, `latency_to_moving_ind4` | Latency to first movement for demonstrator individuals 2–4 (min) |
| `latency_to_moving_demonstrators` | Aggregated latency to first movement across all demonstrators (min) |
| `reaction_time_ind1` | Focal fish reaction time after stimulus delivery (seconds) |
| `reaction_time_ind2`, `reaction_time_ind3`, `reaction_time_ind4` | Reaction time for demonstrator individuals 2–4 (seconds) |
| `reaction_time_demonstrators` | Aggregated demonstrator reaction time (seconds) |
| `reaction_distance_from_dems` | Focal fish distance from demonstrators at the moment of reaction (cm) |
| `mean_velocity_cm` | Mean swimming velocity (cm/s) |
| `mean_dist_to_edge_cm` | Mean distance from tank edge (cm) |
| `mean_dist_to_top_cm` | Mean distance from demonstrator area (cm) |
| `total_time_near_edge` | Total time spent near tank edge (min) |
| `prop_time_near_edge` | Proportion of time spent near tank edge |
| `total_time_near_demonstrator` | Total time spent near demonstrator area (min) |
| `prop_time_near_demonstrator` | Proportion of time spent near demonstrator area |
| `recovery_time` | Time to return to baseline activity levels (min) |
| `returned_to_baseline` | Whether focal fish returned to baseline activity levels (TRUE/FALSE) |
| `recovery_time_ind2`, `recovery_time_ind3`, `recovery_time_ind4` | Recovery time for demonstrator individuals 2–4 (min) |
| `returned_to_baseline_ind2`, `returned_to_baseline_ind3`, `returned_to_baseline_ind4` | Whether demonstrators 2–4 returned to baseline activity (TRUE/FALSE) |
| `recovery_time_demonstrators` | Aggregated demonstrator recovery time (min) |
| `recovery_similarity_before`, `recovery_similarity_after` | Similarity of focal behaviour to baseline before and after recovery |
| `baseline_velocity_mean`, `baseline_velocity_sd` | Mean and standard deviation of velocity during baseline (cm/s) |
| `baseline_prop_moving_mean`, `baseline_prop_moving_sd` | Mean and standard deviation of proportion moving during baseline |
| `baseline_prop_moving_sd_ind2`, `baseline_prop_moving_sd_ind3`, `baseline_prop_moving_sd_ind4` | Standard deviation of baseline proportion moving for demonstrators 2–4 |
| `time_near_edge_pre_recovery` | Time spent near tank edge prior to recovery (min) |
| `time_near_demonstrator_pre_recovery` | Time spent near demonstrator area prior to recovery (min) |
| `time_moving_pre_recovery` | Time spent moving prior to recovery (min) |
| `mean_dist_to_edge_pre_recovery` | Mean distance from tank edge prior to recovery (cm) |
| `mean_dist_to_demonstrator_pre_recovery` | Mean distance from demonstrator area prior to recovery (cm) |
| `weight` | Fish body weight (g) |
| `demonstrator_id` | Demonstrator shoal identifier |

### 2. `temporal_data.csv`

Time-series behavioural data at 1-second resolution. Contains
frame-by-frame positions, velocities, and behavioural classifications
for all individuals.

| Column | Description |
|------------------------------------|------------------------------------|
| `session_name` | Unique trial identifier |
| `time` | Time within recording (seconds) |
| `trial_time` | Time within trial, aligned to stimulus delivery (seconds) |
| `x_cm`, `y_cm` | Focal fish position in cm |
| `velocity_cm_s` | Instantaneous focal swimming velocity (cm/s) |
| `n_frames` | Number of frames contributing to the time bin |
| `n_moving`, `prop_moving_instant` | Count and proportion of focal frames classified as moving in the bin |
| `n_moving_ind2`, `n_moving_ind3`, `n_moving_ind4` | Frame count classified as moving for demonstrator individuals 2–4 |
| `prop_moving_instant_ind2`, `prop_moving_instant_ind3`, `prop_moving_instant_ind4` | Instantaneous proportion moving for demonstrator individuals 2–4 |
| `prop_moving_sliding` | Sliding-window proportion moving for the focal fish |
| `prop_moving_sliding_ind2`, `prop_moving_sliding_ind3`, `prop_moving_sliding_ind4` | Sliding-window proportion moving for demonstrator individuals 2–4 |
| `prop_moving_sliding_demonstrators` | Aggregated sliding-window proportion moving across all demonstrators |
| `dist_to_edge_cm` | Distance from tank edge (cm) |
| `dist_to_top_cm` | Distance from demonstrator area (cm) |
| `prop_near_edge` | Proportion of frames near tank edge in the bin |
| `prop_near_demonstrator` | Proportion of frames near demonstrator area in the bin |
| `behaviour_ind1_numeric` | Numeric behavioural state classification for the focal fish |
| `behaviour_ind2_numeric`, `behaviour_ind3_numeric`, `behaviour_ind4_numeric` | Numeric behavioural state classification for demonstrator individuals 2–4 |
| `day`, `trial`, `camera` | Experimental day, trial number, and camera ID |
| `phase` | Recording phase (`baseline` or `trial`) |
| `ID` | Fish identifier |
| `treatment` | Blinded treatment code (TX = control, TY = high, TZ = low amitriptyline) |
| `information` | Information condition (IA = direct + social, IB = social only) |
| `weight` | Fish body weight (g) |
| `demonstrator_id` | Paired demonstrator fish ID |

**Note**: This file is \~215 MB and is not tracked in the git
repository.

### 3. `BLINDING_KEY.csv`

Mapping between blinded codes and original experimental conditions. The
analysis was conducted blind to treatment identity.

| Column | Description |
|------------------------------------|------------------------------------|
| `variable` | Variable name (`treatment` or `information`) |
| `original` | Original condition code (c = control, l = low, h = high; direct/indirect) |
| `blinded` | Blinded code used during analysis (TX, TY, TZ; IA, IB) |

### 4. `pixel_distances.csv`

Video calibration data used to convert pixel coordinates to centimetres.

| Column                 | Description                                |
|------------------------|--------------------------------------------|
| `timestamp`            | Time the calibration was recorded          |
| `id`                   | Session identifier                         |
| `distance_px`          | Calibration distance in pixels             |
| `x1`, `y1`, `x2`, `y2` | Calibration line endpoints                 |
| `background_path`      | Path to background image used to calibrate |
| `session_root`         | Path to tracking session folder            |

### 5. `morphs.csv`

Morphometric and metadata for each fish.

| Column         | Description             |
|----------------|-------------------------|
| `id`           | Fish identifier         |
| `d`, `t`, `c`  | Day, trial, camera      |
| `session_name` | Full session identifier |
| `weight`       | Body weight (g)         |
| `demonstrator` | Demonstrator identifier |

### 6. `water_analysis_results.csv`

Chemical analysis results for water samples taken from exposure tanks,
used to confirm amitriptyline concentrations.

| Column                 | Description                                 |
|------------------------|---------------------------------------------|
| `Reference`            | Laboratory sample reference code            |
| `Sample Description`   | Experimental sample identifier              |
| `Sample No.`           | Sample number                               |
| `Replicate`            | Replicate identifier                        |
| `Date Sampled`         | Date the water sample was collected         |
| `Amitriptyline (ng/L)` | Measured amitriptyline concentration (ng/L) |

## R package versions

See `r_package_versions.md` for a complete table.

## Python Requirements

The helper scripts in `4-assisting_code/` require Python 3.10+.
Dependencies are listed in `requirements.txt`:

``` bash
pip install -r 4-assisting_code/requirements.txt
```

## Files Not Tracked

The following are excluded from version control due to size: - Video
files (`1-media/`) - Raw tracking output (`2-data/1-raw_tracks/`) -
Smoothed trajectories (`2-data/2-smoothed_tracks/`) - Behaviour tracks
(`2-data/3-behaviour_tracks/`) - Fitted model objects
(`2-data/4-models/`) - Temporal data (`2-data/temporal_data.csv`) -
Tracking-quality visualisations (`3-figs/spatial_checks/`). But please
do not hesitate to reach out if you require access to any of these
materials.

## Licensing, Citation and Contact

These materials are released under a Creative Commons
Attribution–NonCommercial–ShareAlike 4.0 International licence (CC
BY-NC-SA 4.0).

When using or adapting this code and data, please cite the associated
manuscript.

For correspondence, please contact Jack L. Manera
([Jack.Manera\@monash.edu](mailto:Jack.Manera@monash.edu){.email}).
