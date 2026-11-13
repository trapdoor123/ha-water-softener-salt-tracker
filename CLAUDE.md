# Project Context: Water Softener Salt Tracker (Home Assistant Custom Integration)

You are taking over development on **`ha-water-softener-salt-tracker`**, a custom Home Assistant integration designed for distribution via **HACS** (Home Assistant Community Store).

## 1. Repository & Release Status
- **GitHub Repository:** `[https://github.com/trapdoor123/ha-water-softener-salt-tracker](https://github.com/trapdoor123/ha-water-softener-salt-tracker)`
- **Current Release:** `v1.0.2` (published on `main` and tagged as a GitHub Release for HACS)
- **Integration Domain:** `water_softener_salt_tracker`
- **Integration Type:** `helper` (`iot_class: calculated`)
- **Workflow Expectations:** When making code changes, always keep `custom_components/water_softener_salt_tracker/manifest.json` (`"version"`) in sync with semantic Git tags (`vX.Y.Z`) and GitHub Releases (`gh release create`), as HACS relies on matching manifest versions and GitHub release tags to notify users of updates.

## 2. Core Problem & Architecture
Instead of placing ultrasonic or optical distance sensors inside a corrosive brine tank, this integration estimates water softener salt consumption purely from whole-house cumulative water meter readings (`total` or `total_increasing` sensors).

### Directory Structure

    ha-water-softener-salt-tracker/
    ├── custom_components/
    │   └── water_softener_salt_tracker/
    │       ├── __init__.py       # SoftenerDataCoordinator + HA Store persistence
    │       ├── button.py         # WaterSoftenerResetButton ("Reset Salt Level")
    │       ├── config_flow.py    # ConfigFlow + OptionsFlowHandler
    │       ├── const.py          # Domain constants & default calibration values
    │       ├── manifest.json     # Integration metadata & version
    │       ├── sensor.py         # 4 diagnostic/tracking sensor entities
    │       └── translations/
    │           └── en.json       # UI labels for config & options flows, repair issues
    ├── .gitignore
    ├── CLAUDE.md                 # Project context for Claude Code
    ├── hacs.json                 # HACS repository metadata
    └── README.md                 # User documentation & softener calibration reference

### Data Model & Calculation Logic
- **Persistence:** Uses `homeassistant.helpers.storage.Store` (key: `water_softener_salt_tracker.storage_<entry_id>`) to persist:
  - `baseline_reading` (`float`, in Litres): Snapshot of the upstream water meter at the last salt refill.
  - `last_refill_date` (`str`, `YYYY-MM-DD`): Date of the last refill.
- **Formulas (evaluated dynamically on upstream water meter state changes):**
  - `water_used = max(current_meter_reading - baseline_reading, 0.0)`
  - `salt_remaining_kg = max(salt_capacity - (water_used * (consumption_rate / 1000.0)), 0.0)`
  - `salt_level_pct = max(round((salt_remaining_kg / salt_capacity) * 100, 1), 0.0)`
- **Entities Exposed (grouped under a single HA Device):**
  - `sensor.<name>_water_processed_since_refill` (`SensorDeviceClass.WATER`, `SensorStateClass.TOTAL_INCREASING`, unit: `L`)
  - `sensor.<name>_salt_remaining` (unit: `kg`)
  - `sensor.<name>_salt_level` (unit: `%`)
  - `sensor.<name>_last_refill_date` (`YYYY-MM-DD` string)
  - `button.<name>_reset_salt_level` (snapshots current water meter reading as `baseline_reading` and sets `last_refill_date` to today)

## 3. Real-World Testing & Empirical Calibration Context
- **Primary Test Environment:**
  - **Water Data Source:** Thames Water HACS integration (updates daily with a ~2–3 day reporting lag; whole-house supply runs through the softener).
  - **Softener Hardware:** 2019 **Harvey Dual Flo H20/25** (HV3 / TwinTec S3 twin-tank non-electric chassis), factory `SERVICE: 750` L gear (`0.400 g/L` theoretical rate at 300 g/regen), `REGEN: 17` L.
  - **Empirical Calibration Finding:** A full 8.0 kg load (two 4.0 kg salt blocks) ran from `25,052 L` (15 Aug 2026) to empty at `36,737 L` (13 Nov 2026) = `11,685 L` recorded (`~12,088 L` lag-adjusted). Because ~0.8–1.0 kg dissolves immediately to saturate standing brine water when starting empty—and older brine valves (`B/V 1`) can draw slightly more refill water per cycle—the calibrated real-world rate for this unit is **`0.685 g/L`** (recorded) / **`0.665 g/L`** (lag-adjusted) rather than the `0.400 g/L` brochure figure.

## 4. Home Assistant Technical Constraints & Lessons Learned
- **`OptionsFlow` Compatibility (Fixed in `v1.0.2`):** In modern Home Assistant Core, `self.config_entry` on `config_entries.OptionsFlow` is a built-in read-only property. Never assign `self.config_entry = config_entry` inside `OptionsFlowHandler.__init__`, as doing so raises an `AttributeError` (`500 Internal Server Error`) when users click the integration's gear/configure button.
- **Sensor Filtering:** `config_flow.py` uses `EntitySelectorConfig(domain="sensor", device_class=[SensorDeviceClass.WATER])`. Keep in mind some custom/scraper water integrations omit `device_class: water`—consider whether future versions should broaden or provide a fallback selector if users report missing sensors.
- **README Attribution:** Preserve the footer line (`*100% vibe-coded with love by Gemini.*`) at the bottom of `README.md`.

## 5. Planned Roadmap & Feature Backlog
Please inspect the current codebase first, summarize its state, and be ready to help implement and release features from this backlog:
1. **Custom Service Call (`water_softener_salt_tracker.set_refill`):** Register a native HA service/action accepting optional `baseline_reading` (`float`) and `last_refill_date` (`date`/`str`) so users can backdate refills or correct baselines from Developer Tools / automations without editing `.storage` files.
2. **Automatic Unit Conversion (`m³` and `gal`):** Detect `native_unit_of_measurement` on the upstream water meter sensor (`L`, `m³`, `gal`, `ft³`) and normalize automatically to Litres so users don't need intermediate template sensors.
3. **Partial Top-Up Support:** Allow adding a configurable mass of salt (e.g. one 4.0 kg block added when at 30%) rather than assuming every reset starts from 100% of `salt_capacity`.
4. **Consumption Rate & Days-Remaining Forecasting:** Track rolling daily water usage to expose an `Estimated Days Remaining` (and/or predicted empty date) sensor.
5. **CI & Automated Testing:** Add `pytest-homeassistant-custom-component` unit tests and GitHub Actions workflows for `hassfest` and `hacs/action` validation.

Start by inspecting the repository files (`git status`, `git log -n 5`, and the contents of `custom_components/water_softener_salt_tracker/`) to confirm everything matches this baseline, then ask what feature I want to tackle first.
