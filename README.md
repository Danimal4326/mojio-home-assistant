# Mojio Home Assistant Integration

Custom component integrating [Mojio](https://www.moj.io/)-connected vehicles with
Home Assistant, including **Audi** vehicles.

Requires Home Assistant **2026.7.0** or newer.

## Features

Configured entirely from the UI - no YAML. Each vehicle becomes a device with:

- **Device tracker** - GPS position with accuracy, so the vehicle shows on the map
  and triggers zone automations.
- **Sensors** - fuel level, battery voltage, speed, engine RPM, odometer, distance
  since install, engine oil temperature, diagnostic code count, vehicle status,
  last contact, and last-trip distance / duration / start time.
- **Binary sensors** - ignition, parked, idling, tow detected, disturbance,
  accident detected, check engine, battery connected, tire pressure warning.

## Installation

### HACS

Add this repository as a custom repository in HACS (category: Integration),
install it, then restart Home Assistant.

### Manual

Copy `custom_components/mojio` into your Home Assistant `config/custom_components`
directory and restart.

## Configuration

Go to **Settings → Devices & Services → Add Integration** and search for
**Mojio**. You'll be asked for:

| Field | Notes |
| --- | --- |
| Tenant | Your vehicle brand's Mojio tenant. Use `audi` for Audi vehicles. |
| Email / Password | Your vehicle brand's connected-services account login. |
| Client ID / secret | The OAuth credentials used by your brand's mobile app. |

The polling interval (default 300 seconds) can be changed afterwards via the
integration's **Configure** button.

If the stored credentials stop working, Home Assistant raises a re-authentication
prompt rather than silently failing.

## Notes on Audi vehicles

The Audi tenant doesn't report everything the Mojio API defines:

- **Trip distance** is returned as a flat `0`, and the odometer readings attached
  to trips are stale. The bundled SDK recovers the real distance from the trip's
  GPS path instead; the `last_trip_distance` sensor sets a
  `derived_from_gps_path` attribute when it does. Derived values are GPS-sampled
  and read slightly short of a true odometer.
- **Fuel efficiency**, harsh-acceleration and idling counts are not reported at
  all, so no entities are created for them.
- **Tire pressure** is absent from the payload, so that binary sensor stays
  `unknown` unless your vehicle reports it.

## Troubleshooting

### An odometer shows feet instead of miles

Only affects installs made from `master` before the first release, which briefly
exposed the odometers in meters - Home Assistant maps a metres-based distance
sensor onto feet for US customary users, and only a kilometres-based one onto
miles.

Home Assistant pins a sensor's display unit in the entity registry the first
time it is registered, so updating alone will not change an existing entity.
For each affected entity (`Odometer` and `Distance since install`) either:

- open the entity → gear icon → set **Unit of Measurement** to miles, or
- delete the entity and reload the integration so it re-registers, or
- remove and re-add the integration.

## Brand images

Home Assistant 2026.3+ serves brand images for custom integrations from the
integration's own `brand/` directory, falling back to the brands CDN only if
that directory is absent. `custom_components/mojio/brand/icon.png` is therefore
what stops the UI showing "logo not found" - no submission to the
[home-assistant/brands](https://github.com/home-assistant/brands) repository is
required.

Home Assistant falls back from `logo.png`, `icon@2x.png` and the `dark_*`
variants to `icon.png`, so the single icon covers every image the frontend asks
for.

## Development

The Mojio SDK is vendored under `custom_components/mojio/mojio_sdk/` rather than
installed from PyPI - see that directory's README for why, and use
`scripts/sync_sdk.sh` to re-sync it.

```bash
python -m venv .venv-ha
.venv-ha/bin/pip install homeassistant pytest-homeassistant-custom-component
.venv-ha/bin/pytest
```
