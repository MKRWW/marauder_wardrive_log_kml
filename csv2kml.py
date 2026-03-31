#!/usr/bin/env python3
"""
csv2kml.py – Convert Marauder wardrive.log to KML

Usage:
    python csv2kml.py -i wardrive_0.log
    python csv2kml.py -i wardrive_0.log -o mymap.kml

If -i is omitted, the script looks for a wardrive*.log in its own directory.
If -o is omitted, the KML is written next to the input file.

Color coding (WiFi):
    Green  : RSSI >= -60 dBm  (strong)
    Yellow : RSSI >= -70 dBm  (good)
    Orange : RSSI >= -80 dBm  (weak)
    Red    : RSSI  < -80 dBm  (very weak)

BLE devices are shown in blue.
"""

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape


# ---------------------------------------------------------------------------
# Style helpers
# ---------------------------------------------------------------------------

# KML icon color format: AABBGGRR  (alpha, blue, green, red)
_STYLES = {
    "wifi_strong":    ("ff00cc00", 1.2),   # green
    "wifi_good":      ("ff00ddff", 1.0),   # yellow-ish
    "wifi_weak":      ("ff0080ff", 1.0),   # orange
    "wifi_very_weak": ("ff0000ff", 1.0),   # red
    "ble":            ("ffff6600", 0.9),   # blue
}

_ICON_URL = "http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png"


def _style_id(rssi: int, entry_type: str) -> str:
    if entry_type == "BLE":
        return "ble"
    if rssi >= -60:
        return "wifi_strong"
    if rssi >= -70:
        return "wifi_good"
    if rssi >= -80:
        return "wifi_weak"
    return "wifi_very_weak"


# ---------------------------------------------------------------------------
# KML builder
# ---------------------------------------------------------------------------

def _style_xml() -> list[str]:
    lines = []
    for sid, (color, scale) in _STYLES.items():
        lines += [
            f'  <Style id="{sid}">',
            f'    <IconStyle>',
            f'      <color>{color}</color>',
            f'      <scale>{scale}</scale>',
            f'      <Icon><href>{_ICON_URL}</href></Icon>',
            f'    </IconStyle>',
            f'    <LabelStyle><scale>0</scale></LabelStyle>',
            f'  </Style>',
        ]
    return lines


def _cdata(text: str) -> str:
    """Wrap text in CDATA, escaping any embedded ]]> sequences."""
    return "<![CDATA[" + text.replace("]]>", "]]&gt;") + "]]>"


def _placemark(entry: dict) -> list[str]:
    ssid    = entry["SSID"].strip() or "(hidden)"
    mac     = entry["MAC"].strip()
    auth    = entry["AuthMode"].strip()
    channel = entry["Channel"].strip()
    seen    = entry["FirstSeen"].strip()
    acc     = entry["AccuracyMeters"].strip()
    etype   = entry["Type"].strip()
    lat     = entry["CurrentLatitude"].strip()
    lon     = entry["CurrentLongitude"].strip()
    alt     = entry["AltitudeMeters"].strip()

    try:
        rssi = int(entry["RSSI"].strip())
    except ValueError:
        rssi = -999

    style = _style_id(rssi, etype)
    display_name = f"{ssid} ({mac})" if etype == "WIFI" else mac

    desc_html = (
        f"<b>SSID:</b> {ssid}<br/>"
        f"<b>MAC:</b> {mac}<br/>"
        f"<b>Auth:</b> {auth}<br/>"
        f"<b>Channel:</b> {channel}<br/>"
        f"<b>RSSI:</b> {rssi} dBm<br/>"
        f"<b>Type:</b> {etype}<br/>"
        f"<b>Seen:</b> {seen}<br/>"
        f"<b>GPS accuracy:</b> {acc} m"
    )

    return [
        f'    <Placemark>',
        f'      <name>{escape(display_name)}</name>',
        f'      <description>{_cdata(desc_html)}</description>',
        f'      <styleUrl>#{style}</styleUrl>',
        f'      <Point>',
        f'        <coordinates>{lon},{lat},{alt}</coordinates>',
        f'      </Point>',
        f'    </Placemark>',
    ]


def build_kml(entries: list[dict]) -> str:
    valid = [
        e for e in entries
        if e.get("CurrentLatitude", "").strip() not in ("", "0", "0.0")
        and e.get("CurrentLongitude", "").strip() not in ("", "0", "0.0")
    ]
    skipped = len(entries) - len(valid)
    if skipped:
        print(f"  Skipped {skipped} entries without valid GPS coordinates.")

    wifi = [e for e in valid if e.get("Type", "").strip() == "WIFI"]
    ble  = [e for e in valid if e.get("Type", "").strip() == "BLE"]

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        '<Document>',
        f'  <name>Wardrive {datetime.now():%Y-%m-%d}</name>',
        f'  <description>{_cdata(f"Exported {datetime.now():%Y-%m-%d %H:%M} | WiFi: {len(wifi)} | BLE: {len(ble)}")}</description>',
    ]

    lines += _style_xml()

    for folder_label, folder_entries in [
        (f"WiFi Networks ({len(wifi)})", wifi),
        (f"BLE Devices ({len(ble)})", ble),
    ]:
        lines += [f'  <Folder>', f'    <name>{folder_label}</name>']
        for e in folder_entries:
            lines += _placemark(e)
        lines.append('  </Folder>')

    lines += ['</Document>', '</kml>']
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="csv2kml.py",
        description="Convert a Marauder wardrive.log (CSV) to a KML file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Color coding (WiFi):\n"
            "  Green  : RSSI >= -60 dBm  (strong)\n"
            "  Yellow : RSSI >= -70 dBm  (good)\n"
            "  Orange : RSSI >= -80 dBm  (weak)\n"
            "  Red    : RSSI  < -80 dBm  (very weak)\n"
            "  Blue   : BLE devices\n"
        ),
    )
    parser.add_argument(
        "-i", "--input",
        metavar="INPUT",
        help="Wardrive log file (CSV). Defaults to the first wardrive*.log found next to this script.",
    )
    parser.add_argument(
        "-o", "--output",
        metavar="OUTPUT",
        help="Output KML file. Defaults to <input>.kml next to the input file.",
    )
    args = parser.parse_args()

    # Resolve input path
    if args.input:
        log_path = Path(args.input)
    else:
        script_dir = Path(__file__).parent
        candidates = sorted(script_dir.glob("wardrive*.log"))
        if not candidates:
            parser.error("No wardrive*.log found. Specify one with -i / --input.")
        log_path = candidates[0]
        print(f"Auto-detected input: {log_path.name}")

    if not log_path.exists():
        parser.error(f"File not found: {log_path}")

    # Resolve output path
    out_path = Path(args.output) if args.output else log_path.with_suffix(".kml")

    # Parse
    with open(log_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        entries = list(reader)

    print(f"Read {len(entries)} entries from '{log_path.name}'")

    # Build and write KML
    kml = build_kml(entries)
    out_path.write_text(kml, encoding="utf-8")

    wifi_count = sum(1 for e in entries if e.get("Type", "").strip() == "WIFI")
    ble_count  = sum(1 for e in entries if e.get("Type", "").strip() == "BLE")
    print(f"KML written to '{out_path}'")
    print(f"  WiFi: {wifi_count}  |  BLE: {ble_count}")


if __name__ == "__main__":
    main()
