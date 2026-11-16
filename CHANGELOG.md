# Changelog

Each `## vX.Y.Z` section below becomes the GitHub Release notes for that
version when it is published.

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
