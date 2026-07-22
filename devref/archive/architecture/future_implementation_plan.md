# BQuant: Architecture and Implementation Plan for Missing Features

## 1. Introduction

This document outlines the proposed architecture for implementing the missing features in the `bquant` package, as identified in the gap analysis (`devref/gaps/methodology_vs_implementation_gap_analysis.md`). The goal is to create a robust, modular, and complete toolkit for quantitative analysis that fully realizes the vision of the original research methodology.

The core of this plan is to resolve the existing architectural debt—namely, the duplicated logic between `MACDZoneAnalyzer` and the `bquant.analysis` package—and then to build upon a consolidated foundation.

## 2. Target Architecture

The guiding principle is that the `bquant/analysis` package should be the **single source of truth** for all analysis logic. The proposed architecture involves modifying existing modules and adding new ones to create a comprehensive and cohesive system.

### 2.1. Consolidated and Enhanced Modules

*   **`bquant.analysis.zones.zone_features.py` -> `ZoneFeaturesAnalyzer`**
    *   **Responsibility:** The sole component responsible for calculating all features for a given list of zones.
    *   **Enhancements:** This class will be expanded to calculate all features from the methodology, including:
        *   `hist_slope`
        *   Advanced swing metrics (avg/max rally/drop size, ratios)
        *   Shape metrics (`skewness`, `kurtosis`)
        *   Divergence metrics
        *   Volume-based metrics

*   **`bquant.analysis.statistical.hypothesis_testing.py` -> `HypothesisTestSuite`**
    *   **Responsibility:** The sole component for running statistical hypothesis tests.
    *   **Enhancements:**
        *   Fix the broken `test_histogram_slope_hypothesis` by using the `hist_slope` feature from the enhanced `ZoneFeaturesAnalyzer`.
        *   Add new tests for H4 (Correlation vs. Drawdown) and H5 (S/R Levels).

*   **`bquant.analysis.zones.sequence_analysis.py` -> `ZoneSequenceAnalyzer`**
    *   **Responsibility:** Analysis of zone sequences, transitions, and clustering.
    *   **Enhancements:**
        *   The `_markov_chain_analysis` method will be updated to accept complex, user-defined states (e.g., "long_bull", "short_bear") instead of being hardcoded to simple "bull"/"bear".

### 2.2. New Modules and Packages

*   **`bquant.analysis.statistical.stationarity.py`**
    *   **Responsibility:** Perform stationarity tests.
    *   **Components:** Will contain a function `run_adf_test()` that takes a time series (e.g., a series of zone durations) and returns the Augmented Dickey-Fuller test results.

*   **`bquant.analysis.modeling.py`**
    *   **Responsibility:** House various modeling techniques.
    *   **Components:** Will initially contain a function `run_ols_regression()` to model the relationship between different zone features, as described in the methodology.

*   **`bquant.validation.py` (New Top-Level Package)**
    *   **Responsibility:** Provide tools for robust strategy validation, a cross-cutting concern.
    *   **Components:**
        *   `walk_forward.py`: A utility for performing walk-forward validation.
        *   `sensitivity.py`: A utility for analyzing strategy sensitivity to parameter changes.

### 2.3. The New Orchestrator: `AnalysisPipeline`

To tie all the modular components together, a new primary orchestrator will be introduced.

*   **Location:** `bquant.analysis.pipeline.py`
*   **Class:** `AnalysisPipeline`
*   **Responsibility:**
    1.  Accept raw data (e.g., OHLCV DataFrame) and a configuration object.
    2.  The configuration will specify which analysis steps to perform (e.g., feature engineering, hypothesis testing, clustering).
    3.  Call the appropriate analysis modules from `bquant.analysis` in a logical sequence.
    4.  Aggregate the results from each step into a single, comprehensive, and structured result object.
    5.  This will serve as the main, high-level entry point for users and will replace the logic currently in `MACDZoneAnalyzer.analyze_complete`.

## 3. Detailed Implementation Plan

This plan is broken down into phases to ensure a structured and manageable development process.

### Phase 1: Refactoring and Consolidation

*   **Objective:** Eliminate duplicated code and establish `bquant.analysis` as the single source of truth.
*   **Steps:**
    1.  **Consolidate Features:** Move all unique feature calculation logic from `MACDZoneAnalyzer.calculate_zone_features` into `ZoneFeaturesAnalyzer`.
    2.  **Consolidate Hypotheses:** Move the hypothesis testing logic from `MACDZoneAnalyzer.test_hypotheses` into `HypothesisTestSuite`.
    3.  **Refactor `MACDZoneAnalyzer`:** Modify `MACDZoneAnalyzer` to delegate all analysis tasks to the `bquant.analysis` modules. Its primary role will be to identify zones and pass them to the analysis pipeline.
    4.  **Update Tests:** Ensure all unit and integration tests are updated to use the consolidated components from `bquant.analysis`.

### Phase 2: Implementing Missing Features

*   **Objective:** Enhance `ZoneFeaturesAnalyzer` to compute all features from the research methodology.
*   **Steps (in order of increasing complexity):**
    1.  Add `hist_slope` calculation to `ZoneFeaturesAnalyzer`.
    2.  Fix the `test_histogram_slope_hypothesis` in `HypothesisTestSuite` to use the new feature.
    3.  Add advanced swing analysis features (e.g., avg/max rally/drop size, ratios).
    4.  Add shape metrics (`skewness`, `kurtosis`).
    5.  Add divergence detection logic and associated features.
    6.  Integrate volume data into the data processing pipeline and add volume-based features.

### Phase 3: Implementing Missing Analysis Modules

*   **Objective:** Create new, self-contained modules for advanced statistical analysis.
*   **Steps:**
    1.  Create `bquant.analysis.statistical.stationarity.py` and implement a function for the Augmented Dickey-Fuller (ADF) test. Add corresponding unit tests.
    2.  Create `bquant.analysis.modeling.py` and implement a function for OLS regression. Add corresponding unit tests.
    3.  Update `ZoneSequenceAnalyzer` to allow for complex, user-defined state definitions in its Markov chain analysis.

### Phase 4: Creating the New Orchestrator

*   **Objective:** Build a new, high-level entry point for running a complete analysis.
*   **Steps:**
    1.  Design and implement the `bquant.analysis.pipeline.AnalysisPipeline` class.
    2.  The pipeline should accept a configuration object to allow for flexible and partial analyses.
    3.  It will call the modular components in sequence and aggregate their results.
    4.  Create integration tests for the full pipeline.

### Phase 5: Implementing Validation Tools

*   **Objective:** Provide tools for robustly validating trading strategies.
*   **Steps:**
    1.  Create the new `bquant.validation` package.
    2.  Design and implement a walk-forward validation utility.
    3.  Design and implement a parameter sensitivity analysis utility.
    4.  Add comprehensive documentation and examples for the validation tools.
