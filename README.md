# Water Softener Salt Tracker for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/default)
[![GitHub Release](https://img.shields.io/github/v/release/trapdoor123/ha-water-softener-salt-tracker)](https://github.com/trapdoor123/ha-water-softener-salt-tracker/releases)

A lightweight Home Assistant integration that estimates water softener salt consumption based on whole-house water consumption data. 

Eliminates the need for ultrasonic tank sensors, optical rangefinders, or ESP32 hardware modifications inside corrosive salt brine tanks.

---

## How It Works

Non-electric and metered softeners (e.g., Harvey, TwinTec, MiniMax, Kinetico, BWT) regenerate based on mechanical water displacement:
1. Every litre of water entering the property is softened.
2. After processing a fixed volume (determined by water hardness and internal gearing), the unit initiates a regeneration cycle consuming a fixed mass of salt (typically ~300g per cycle).
3. This integration continuously tracks water consumed from any cumulative water meter sensor, calculates the salt consumed, and maintains an accurate inventory in kilograms and percentage.

---

## Compatible Water Data Sources

This integration works with any Home Assistant entity reporting cumulative water consumption (`state_class: total_increasing` or `total` in Litres).

### 1. Water Utility Scrapers & APIs
| Provider / Integration | Type | Typical Update Frequency |
| :--- | :--- | :--- |
| **Thames Water** (UK) | HACS Scraper | Daily (with ~2–3 day reporting delay) |
| **Severn Trent / Anglian / Southern Water** | Scraper / REST | Daily |
| **Sydney Water / Yarra Valley Water** (Australia) | Custom / API | Daily |
| **Veolia / Saur** (Europe) | Custom / API | Daily |

*Note: Because an 8 kg salt fill typically lasts 60–90 days, a 2–3 day utility reporting delay represents only ~3% of the total tracking cycle and does not impact real-world alerting.*

### 2. Local Hardware & Smart Meters (Real-Time)
* **Smart Flow Meters:** Flo by Moen (`flo`), Flume 1 & 2 (`flume`), Phyn Plus, or StreamLabs.
* **ESPHome Pulse Meters:** Optical sensors (TCRT5000), Hall-effect flow meters, or inductive proximity sensors reading the metal disc on utility meters.
* **Radio Transceivers (wmbusmeters / RTL-SDR):** Decoding Wireless M-Bus (OMS) transmissions from Itron, Kamstrup, Diehl, or Sensus automated meter reading (AMR) units.
* **Smart Energy Displays:** Hildebrand Glow CAD (Glowmarkt) reading combined utility smart meters.

---

## Setting Up a Custom Water Sensor

If your water meter reports in cubic metres (m³), gallons, or daily deltas, convert it to a cumulative Litres sensor before linking it to this integration.

### Example A: Converting m³ to Litres (Template Sensor)
Add this to your `configuration.yaml`:

```yaml
template:
  - sensor:
      - name: "Water Meter Total Litres"
        unique_id: water_meter_total_litres
        unit_of_measurement: "L"
        device_class: water
        state_class: total_increasing
        icon: mdi:water
        state: >
          {% set m3 = states('sensor.water_meter_cubic_meters') | float(0) %}
          {{ (m3 * 1000) | round(1) }}
```

### Example B: Converting Delta/Daily Pulses into a Running Total
If your meter sensor resets daily (e.g. `sensor.daily_water_litres`), wrap it in a **Utility Meter** helper:

1. In Home Assistant, go to **Settings > Devices & Services > Helpers**.
2. Click **Create Helper** > **Utility Meter**.
3. Select your daily sensor as the input.
4. Set **Meter reset cycle** to **No cycle** (continuous accumulation).
5. Use this new helper as the input entity for the Salt Tracker.

---

## Softener Calibration Reference

Find your softener model and local water hardness to determine your `Consumption Rate (g/L)`:

| Softener Model | Water Hardness (ppm / CaCO₃) | Gearing / Volume per Cycle | Salt Consumed per Litre |
| :--- | :--- | :--- | :--- |
| **Harvey HV3 / TwinTec S3 / MiniMax M2** | < 320 ppm | 1000 L | `0.300 g/L` |
| **Harvey HV3 / TwinTec S3 / MiniMax M2** | 321–375 ppm | 870 L | `0.345 g/L` (Standard) |
| **Harvey HV3 / TwinTec S3 / MiniMax M2** | 376–430 ppm | 750 L | `0.400 g/L` |
| **Harvey HV4 / TwinTec S4 / MiniMax Major** | ~300 ppm | ~900 L | `0.333 g/L` |
| **Kinetico Premier Compact** | High Hardness | ~450 L | `0.450 g/L` |
| **Generic Electric Softener (Single Tank)** | 300 ppm | ~1800 L (1.5 kg regen) | `0.833 g/L` |

---

## Installation via HACS

1. Open **HACS** in your Home Assistant instance.
2. Click the three dots in the top right corner and select **Custom repositories**.
3. Paste the repository URL: `https://github.com/trapdoor123/ha-water-softener-salt-tracker`
4. Set Category to **Integration** and click **Add**.
5. Find **Water Softener Salt Tracker**, click **Download**, and restart Home Assistant.

---

## Configuration

1. Go to **Settings > Devices & Services > Add Integration**.
2. Search for **Water Softener Salt Tracker**.
3. Configure the following:
   * **Water Meter Sensor:** Pick your cumulative water sensor from the drop-down.
   * **Salt Capacity:** Total weight loaded at full refill (default: `8.0` kg for 2 block packs).
   * **Consumption Rate:** Salt consumption in grams per litre (default: `0.345` g/L).

---

## Entities Provided

| Entity | Domain | Description |
| :--- | :--- | :--- |
| `sensor.water_softener_salt_level` | Sensor (%) | Current estimated salt capacity remaining |
| `sensor.water_softener_salt_remaining` | Sensor (kg) | Estimated kilograms of salt remaining |
| `sensor.water_softener_water_processed` | Sensor (L) | Litres of water softened since last refill |
| `sensor.water_softener_last_refill_date` | Sensor | Date of last recorded salt replenishment |
| `button.water_softener_reset_salt_level` | Button | Snapshot current meter reading to 100% capacity |

---

*100% vibe-coded with love by Gemini.*
