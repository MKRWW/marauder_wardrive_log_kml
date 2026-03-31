# Marauder Log to KML Exporter

Convert [ESP32 Marauder](https://github.com/justcallmekoko/ESP32Marauder) wardrive logs to KML files for visualization in Google Earth, Google Maps, or any GIS tool.

## What is Wardriving?

Wardriving is the practice of moving through an area while scanning for Wi-Fi networks and Bluetooth devices, logging their signal strength and GPS coordinates. The resulting data gives you a spatial picture of the wireless landscape around you — useful for network research, coverage analysis, or just curiosity.

## What is ESP32 Marauder?

[ESP32 Marauder](https://github.com/justcallmekoko/ESP32Marauder) is an open-source firmware for ESP32-based devices (e.g. Flipper Zero Wi-Fi dev board, M5Stack) that turns them into portable wireless scanners. Among many features, it can perform wardrive sessions — scanning for nearby Wi-Fi access points and BLE devices while recording GPS coordinates — and saves the results as a CSV log file (`wardrive_X.log`).

## What does this script do?

`csv2kml.py` reads a Marauder wardrive log and produces a `.kml` file with one placemark per detected device, color-coded by signal strength. Open the KML in Google Earth or import it into Google Maps to see exactly where every network was detected.

### Color coding

| Color  | Signal strength (RSSI) | Meaning       |
|--------|------------------------|---------------|
| Green  | ≥ −60 dBm              | Strong        |
| Yellow | ≥ −70 dBm              | Good          |
| Orange | ≥ −80 dBm              | Weak          |
| Red    | < −80 dBm              | Very weak     |
| Blue   | —                      | BLE device    |

Each placemark shows: SSID, MAC address, encryption type, channel, RSSI, first-seen timestamp, and GPS accuracy.

The output KML contains two folders:
- **WiFi Networks** — all detected access points
- **BLE Devices** — all detected Bluetooth Low Energy devices

## Requirements

- Python 3.10 or newer
- No third-party packages — uses the standard library only

## Usage

```bash
# Auto-detect the first wardrive*.log in the script directory
python csv2kml.py

# Explicit input file
python csv2kml.py -i wardrive_0.log

# Explicit input and output
python csv2kml.py -i wardrive_0.log -o mymap.kml

# Only WiFi networks, no BLE
python csv2kml.py -i wardrive_0.log --wifi-only

# Only networks with a specific auth mode (implies --wifi-only)
python csv2kml.py -i wardrive_0.log --auth WEP
python csv2kml.py -i wardrive_0.log --auth WPA2_PSK,WPA_WPA2_PSK
python csv2kml.py -i wardrive_0.log --auth WPA3

# Help
python csv2kml.py -h
```

### Filter options

| Option | Description |
|--------|-------------|
| `--wifi-only` | Exclude BLE devices, only export WiFi networks |
| `--auth MODE[,MODE,...]` | Keep only entries whose `AuthMode` contains one of the given substrings (case-insensitive). Implies `--wifi-only`. |

The `--auth` filter matches substrings, so `WPA3` will match both `[WPA3_PSK]` and `[WPA2_WPA3_PSK]`.

## Input format

Standard Marauder wardrive CSV:

```
MAC,SSID,AuthMode,FirstSeen,Channel,RSSI,CurrentLatitude,CurrentLongitude,AltitudeMeters,AccuracyMeters,Type
B4:C2:6A:98:63:DC,MyNetwork,[WPA2_PSK],2026-03-31 10:06:40,1,-72,53.4921532,7.4391389,14.60,2.50,WIFI
```

## License

MIT
