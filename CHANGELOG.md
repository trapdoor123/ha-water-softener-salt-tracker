# Changelog

Each `## vX.Y.Z` section below becomes the GitHub Release notes for that
version when it is published.

## v1.1.1

### Bug fixes

- **No more "Unknown" while the water meter is blank.** The tracker now remembers the last valid water meter reading and uses it whenever the meter has no reading. Daily-updating utility meters, such as Thames Water, often stay blank for hours after a Home Assistant restart; previously the salt sensors showed Unknown until the meter reported again.
- **Reset salt level** now works while the meter is blank, using its last valid reading. It is only refused if the meter has never reported a reading.
- **Switching water meters** via Reconfigure now carries your usage over even if the old meter is blank, using its last valid reading.
- Fixed a rare case where reloading the integration (for example after changing its settings) could later overwrite a newer refill baseline.

### Upgrade notes

- Restart Home Assistant after updating.
- The tracker needs one reading from your water meter after this update before it can remember it. Until your meter next reports, the salt sensors may still show Unknown; after that, restarts no longer affect them.

## v1.1.0

### Changes

- **Now a proper device.** The integration is listed under **Settings > Devices & services > Integrations** with one device per softener, holding all the sensors and the Reset button. Previously it appeared as a helper with no obvious device.
- **Softener make and model.** You can enter these (optional) when adding the integration or later via Reconfigure. They appear on the device page. Earlier versions labelled every device "Harvey / Generic"; that label is removed.
- **Reconfigure.** Change the water meter, make or model from the integration's menu without deleting it. If you switch water meters, the water used since your last refill is carried over, so your salt level stays the same.
- **Better sensors.**
  - *Last refill date* is now a real date sensor.
  - *Salt remaining* is now a weight sensor, so you can display it in other units.
  - *Salt remaining* and *Salt level* now record long-term statistics for history graphs.
- **Easier number entry.** Salt capacity and consumption rate are typed into boxes instead of sliders, and the rate accepts three decimal places (e.g. `0.685`).
- **Clean removal.** Deleting the integration now also deletes its stored refill baseline.

### Upgrade notes

- Restart Home Assistant after updating.
- Entity IDs are unchanged, so dashboards and automations keep working.
- To add your softener's make and model, open the integration, click the three-dot menu on the entry and choose **Reconfigure**.

## v1.0.4

### Bug fixes

- **Minimum Home Assistant version corrected to 2024.12.0.** v1.0.3 declared 2024.11.0, but the options form fails on 2024.11. HACS will now only offer the integration on 2024.12.0 or later.

### Internal

- Added an automated test suite, run against both the minimum supported and the latest Home Assistant.
- Added CI: lint, tests, hassfest and HACS validation on every pull request, weekly, and before each release.

## v1.0.3

### Bug fixes

- **Fresh installs start at 100%.** The first valid water meter reading is now stored as the baseline. Previously a new install showed 0% until the reset button was pressed.
- **Unavailable water meter.** The sensors now show `unknown` while the upstream meter has no usable value, instead of a full salt level and a false reset of the water sensor's statistics.
- **Reset Salt Level button.** Pressing it while the water meter is unavailable now gives an error instead of storing a baseline of 0.
- **Meter reset or replacement.** If the meter reads below the stored baseline, a warning is logged and a repair issue appears until you press Reset Salt Level.
- **Form labels.** Labels in the setup and options forms now load correctly (`translations/en.json`).
- The refill date now uses Home Assistant's configured timezone.

### Requirements

- Home Assistant 2024.11.0 or later.

### Upgrade notes

- Restart Home Assistant after updating.
- If you have never pressed Reset Salt Level, the integration will take the current meter reading as its baseline on first start and show 100%. An existing baseline and refill date are kept.
