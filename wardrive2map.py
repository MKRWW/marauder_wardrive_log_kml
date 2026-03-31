#!/usr/bin/env python3
"""
wardrive2map.py – Convert Marauder wardrive.log to KML or GPX

Usage:
    python wardrive2map.py -i wardrive_0.log
    python wardrive2map.py -i wardrive_0.log -o mymap.kml
    python wardrive2map.py -i wardrive_0.log --format gpx
    python wardrive2map.py -i wardrive_0.log --format gpx -o waypoints.gpx
    python wardrive2map.py -i wardrive_0.log --wifi-only --auth WEP --format gpx

If -i is omitted, the script looks for a wardrive*.log in its own directory.
If -o is omitted, the output file is written next to the input with the
appropriate extension (.kml or .gpx).

--format     : kml (default) or gpx
--wifi-only  : exclude BLE devices from output
--auth       : comma-separated list of AuthMode substrings to keep,
               e.g. WEP  or  WPA2_PSK,WPA3  (case-insensitive)

Color coding (WiFi, KML only):
    Green  : RSSI >= -60 dBm  (strong)
    Yellow : RSSI >= -70 dBm  (good)
    Orange : RSSI >= -80 dBm  (weak)
    Red    : RSSI  < -80 dBm  (very weak)

BLE devices are shown in blue (KML only).
GPX output is compatible with Garmin devices (tested: eTrex 30HCx).
"""

import argparse
import csv
from pathlib import Path

from gpx_writer import build_gpx
from kml_writer import build_kml

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="wardrive2map.py",
        description="Convert a Marauder wardrive.log (CSV) to KML or GPX.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Output formats:\n"
            "  kml  (default) Google Earth / Maps, color-coded by RSSI\n"
            "  gpx            Garmin eTrex and other GPS devices\n"
            "\n"
            "Color coding (WiFi, KML only):\n"
            "  Green  : RSSI >= -60 dBm  (strong)\n"
            "  Yellow : RSSI >= -70 dBm  (good)\n"
            "  Orange : RSSI >= -80 dBm  (weak)\n"
            "  Red    : RSSI  < -80 dBm  (very weak)\n"
            "  Blue   : BLE devices\n"
            "\n"
            "Filter examples:\n"
            "  --wifi-only                     only WiFi, no BLE\n"
            "  --auth WEP                      only WEP networks\n"
            "  --auth WPA2_PSK,WPA_WPA2_PSK   WPA2 variants\n"
            "  --auth WPA3                     anything containing WPA3\n"
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
        help="Output file. Defaults to <input>.<ext> next to the input file.",
    )
    parser.add_argument(
        "--format",
        metavar="FORMAT",
        choices=["kml", "gpx"],
        default="kml",
        help="Output format: kml (default) or gpx (for Garmin and other GPS devices).",
    )
    parser.add_argument(
        "--wifi-only",
        action="store_true",
        help="Only include WiFi networks, exclude BLE devices.",
    )
    parser.add_argument(
        "--auth",
        metavar="MODE[,MODE,...]",
        help=(
            "Comma-separated AuthMode substrings to keep (case-insensitive). "
            "Examples: WEP  or  WPA2_PSK,WPA3  or  WPA2_WPA3_PSK. "
            "Only entries whose AuthMode contains at least one of the given "
            "substrings are included. Implies --wifi-only."
        ),
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
    default_ext = f".{args.format}"
    out_path = Path(args.output) if args.output else log_path.with_suffix(default_ext)

    # Parse
    with open(log_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        entries = list(reader)

    print(f"Read {len(entries)} entries from '{log_path.name}'")

    # --- Apply filters ---
    auth_filters: list[str] = []
    if args.auth:
        auth_filters = [a.strip().upper() for a in args.auth.split(",") if a.strip()]

    # --auth implies --wifi-only
    wifi_only = args.wifi_only or bool(auth_filters)

    title_parts: list[str] = []
    if wifi_only:
        entries = [e for e in entries if e.get("Type", "").strip() == "WIFI"]
        title_parts.append("WiFi only")

    if auth_filters:
        def _auth_match(e: dict) -> bool:
            auth = e.get("AuthMode", "").upper()
            return any(f in auth for f in auth_filters)
        entries = [e for e in entries if _auth_match(e)]
        title_parts.append("Auth: " + ", ".join(auth_filters))

    if title_parts:
        print(f"  Filter: {' | '.join(title_parts)}  → {len(entries)} entries remaining")

    title_suffix = " | ".join(title_parts)

    # Build and write output
    if args.format == "gpx":
        output = build_gpx(entries, title_suffix=title_suffix)
        fmt_label = "GPX"
    else:
        output = build_kml(entries, title_suffix=title_suffix)
        fmt_label = "KML"

    out_path.write_text(output, encoding="utf-8")

    wifi_count = sum(1 for e in entries if e.get("Type", "").strip() == "WIFI")
    ble_count  = sum(1 for e in entries if e.get("Type", "").strip() == "BLE")
    print(f"{fmt_label} written to '{out_path}'")
    print(f"  WiFi: {wifi_count}  |  BLE: {ble_count}")


if __name__ == "__main__":
    main()
