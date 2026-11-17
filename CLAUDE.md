# Project Context: Water Softener Salt Tracker (Home Assistant Custom Integration)

You are taking over development on **`ha-water-softener-salt-tracker`**, a custom Home Assistant integration designed for distribution via **HACS** (Home Assistant Community Store).

## 1. Repository & Release Status
- **GitHub Repository:** `[https://github.com/trapdoor123/ha-water-softener-salt-tracker](https://github.com/trapdoor123/ha-water-softener-salt-tracker)`
- **Current Release:** `v1.1.0` (published on `main` and tagged as a GitHub Release for HACS)
- **Integration Domain:** `water_softener_salt_tracker`
- **Integration Type:** `device` (`iot_class: calculated`) since `v1.1.0` — one device per config entry (per softener). It was `helper` before, which hid the device in the UI.
- **Release Process:** Releases are automated by `.github/workflows/release.yml`. To release, bump `"version"` in `custom_components/water_softener_salt_tracker/manifest.json`, add a matching `## vX.Y.Z` section to `CHANGELOG.md` (it becomes the release notes), and merge to `main`. The workflow first runs the CI checks (`ci.yml`) and, if they pass, creates the `vX.Y.Z` tag and GitHub Release if that tag does not exist yet. HACS relies on matching manifest versions and release tags to notify users of updates. Do not create tags or releases by hand (cloud Claude Code sessions cannot push tags or create releases anyway).

## 2. Core Problem & Architecture
Instead of placing ultrasonic or optical distance sensors inside a corrosive brine tank, this integration estimates water softener salt consumption purely from whole-house cumulative water meter readings (`total` or `total_increasing` sensors).

### Directory Structure

    ha-water-softener-salt-tracker/
    ├── custom_components/
    │   └── water_softener_salt_tracker/
    │       ├── __init__.py       # Entry setup/unload/removal; coordinator stored on entry.runtime_data
    │       ├── button.py         # WaterSoftenerResetButton ("Reset salt level")
    │       ├── config_flow.py    # ConfigFlow (user + reconfigure steps) + OptionsFlowHandler
    │       ├── const.py          # Domain constants & default calibration values
    │       ├── coordinator.py    # SoftenerDataCoordinator, meter reading, HA Store persistence
    │       ├── entity.py         # SoftenerEntity base: shared DeviceInfo + listener registration
    │       ├── manifest.json     # Integration metadata & version
    │       ├── sensor.py         # 4 diagnostic/tracking sensor entities
    │       └── translations/
    │           └── en.json       # UI labels for flows, entity names, repair issues
    ├── .github/
    │   └── workflows/
    │       ├── ci.yml            # Lint, tests, hassfest and HACS validation
    │       └── release.yml       # Runs CI, then tags + publishes a release when the manifest version is new
    ├── tests/                    # pytest-homeassistant-custom-component test suite
    ├── .gitignore
    ├── CHANGELOG.md              # Per-version notes, used as GitHub Release notes
    ├── CLAUDE.md                 # Project context for Claude Code
    ├── hacs.json                 # HACS repository metadata
    ├── pyproject.toml            # pytest and ruff configuration
    ├── README.md                 # User documentation & softener calibration reference
    ├── requirements_test.txt     # Test requirements (latest Home Assistant)
    └── requirements_test_min.txt # Test requirements (minimum supported Home Assistant)

### Data Model & Calculation Logic
- **Persistence:** Uses `homeassistant.helpers.storage.Store` (key: `water_softener_salt_tracker.storage_<entry_id>`) to persist:
  - `baseline_reading` (`float`, in Litres): Snapshot of the upstream water meter at the last salt refill.
  - `last_refill_date` (`str`, `YYYY-MM-DD`): Date of the last refill.
- **Formulas (evaluated dynamically on upstream water meter state changes):**
  - `water_used = max(current_meter_reading - baseline_reading, 0.0)`
  - `salt_remaining_kg = max(salt_capacity - (water_used * (consumption_rate / 1000.0)), 0.0)`
  - `salt_level_pct = max(round((salt_remaining_kg / salt_capacity) * 100, 1), 0.0)`
- **Config entry data:** `name`, `water_meter_sensor`, `salt_capacity`, `consumption_rate`, and optional `manufacturer` / `model` (shown on the device). Options (`salt_capacity`, `consumption_rate`) override data. The Reconfigure step changes `water_meter_sensor`, `manufacturer` and `model`; switching meters re-bases the stored baseline so the water used since refill carries over.
- **Entities Exposed (grouped under a single HA Device; names come from `translation_key`s in `translations/en.json`):**
  - `sensor.<name>_water_processed_since_refill` (`SensorDeviceClass.WATER`, `SensorStateClass.TOTAL_INCREASING`, unit: `L`)
  - `sensor.<name>_salt_remaining` (`SensorDeviceClass.WEIGHT`, `MEASUREMENT`, unit: `kg`)
  - `sensor.<name>_salt_level` (`MEASUREMENT`, unit: `%`)
  - `sensor.<name>_last_refill_date` (`SensorDeviceClass.DATE`)
  - `button.<name>_reset_salt_level` (snapshots current water meter reading as `baseline_reading` and sets `last_refill_date` to today)

## 3. Real-World Testing & Empirical Calibration Context
- **Primary Test Environment:**
  - **Water Data Source:** Thames Water HACS integration (updates daily with a ~2–3 day reporting lag; whole-house supply runs through the softener).
  - **Softener Hardware:** 2019 **Harvey Dual Flo H20/25** (HV3 / TwinTec S3 twin-tank non-electric chassis), factory `SERVICE: 750` L gear (`0.400 g/L` theoretical rate at 300 g/regen), `REGEN: 17` L.
  - **Empirical Calibration Finding:** A full 8.0 kg load (two 4.0 kg salt blocks) ran from `25,052 L` (15 Aug 2026) to empty at `36,737 L` (13 Nov 2026) = `11,685 L` recorded (`~12,088 L` lag-adjusted). Because ~0.8–1.0 kg dissolves immediately to saturate standing brine water when starting empty—and older brine valves (`B/V 1`) can draw slightly more refill water per cycle—the calibrated real-world rate for this unit is **`0.685 g/L`** (recorded) / **`0.665 g/L`** (lag-adjusted) rather than the `0.400 g/L` brochure figure.

## 4. Home Assistant Technical Constraints & Lessons Learned
- **`OptionsFlow` Compatibility (Fixed in `v1.0.2`):** In Home Assistant Core 2024.12 and later, `self.config_entry` on `config_entries.OptionsFlow` is a built-in read-only property. Never assign `self.config_entry = config_entry` inside `OptionsFlowHandler.__init__`, as doing so raises an `AttributeError` (`500 Internal Server Error`) when users click the integration's gear/configure button.
- **Minimum Home Assistant Version:** `2024.12.0`, declared in `hacs.json`. The options flow relies on the built-in `OptionsFlow.config_entry` property, which does not exist in 2024.11 (verified by the test suite). If the minimum changes, update `hacs.json` and `requirements_test_min.txt` together; a test enforces that they match.
- **Testing & Linting:** Run `pip install -r requirements_test.txt` then `pytest`, and `ruff check .`. CI runs the tests against both the latest and the minimum Home Assistant, plus `hassfest` and HACS validation, on every pull request, weekly, and before each release. Add or update tests with every behaviour change.
- **Entity IDs Must Stay Stable:** Unique IDs (`<entry_id>_water_processed`, `_salt_remaining`, `_salt_level`, `_last_refill`, `_reset_button`) and the translated entity names determine entity IDs. Changing either renames users' entities on new installs or breaks history, so don't.
- **Restarts:** Any code update needs a full Home Assistant restart (Python modules load once at startup); this is unavoidable for custom integrations. Settings changes (options, reconfigure) only reload the entry.
- **Sensor Filtering:** `config_flow.py` uses `EntitySelectorConfig(domain="sensor", device_class=[SensorDeviceClass.WATER])`. Keep in mind some custom/scraper water integrations omit `device_class: water`—consider whether future versions should broaden or provide a fallback selector if users report missing sensors.

## 5. Planned Roadmap & Feature Backlog
Please inspect the current codebase first, summarize its state, and be ready to help implement and release features from this backlog:
1. **Custom Service Call (`water_softener_salt_tracker.set_refill`):** Register a native HA service/action accepting optional `baseline_reading` (`float`) and `last_refill_date` (`date`/`str`) so users can backdate refills or correct baselines from Developer Tools / automations without editing `.storage` files.
2. **Automatic Unit Conversion (`m³` and `gal`):** Detect `native_unit_of_measurement` on the upstream water meter sensor (`L`, `m³`, `gal`, `ft³`) and normalize automatically to Litres so users don't need intermediate template sensors.
3. **Partial Top-Up Support:** Allow adding a configurable mass of salt (e.g. one 4.0 kg block added when at 30%) rather than assuming every reset starts from 100% of `salt_capacity`.
4. **Consumption Rate & Days-Remaining Forecasting:** Track rolling daily water usage to expose an `Estimated Days Remaining` (and/or predicted empty date) sensor.
5. ~~**CI & Automated Testing**~~ — done in `v1.0.4` (see Testing & Linting above).

Start by inspecting the repository files (`git status`, `git log -n 5`, and the contents of `custom_components/water_softener_salt_tracker/`) to confirm everything matches this baseline, then ask what feature I want to tackle first.
