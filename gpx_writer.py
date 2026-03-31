"""
gpx_writer.py – GPX export library for wardrive2map

Public API:
    build_gpx(entries, title_suffix="") -> str

Output is GPX 1.1, compatible with Garmin eTrex and other GPS devices.
"""

from datetime import datetime, UTC
from xml.sax.saxutils import escape

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GPX_SYM: dict[str, str] = {"WIFI": "Waypoint", "BLE": "Dot"}


def _wpt(entry: dict) -> list[str]:
    ssid    = entry["SSID"].strip() or "(hidden)"
    mac     = entry["MAC"].strip()
    auth    = entry["AuthMode"].strip()
    channel = entry["Channel"].strip()
    etype   = entry["Type"].strip()
    lat     = entry["CurrentLatitude"].strip()
    lon     = entry["CurrentLongitude"].strip()
    alt     = entry["AltitudeMeters"].strip()
    seen    = entry["FirstSeen"].strip()

    try:
        rssi = int(entry["RSSI"].strip())
    except ValueError:
        rssi = -999

    # Garmin name max 30 chars — keep it readable
    raw_name = (ssid if ssid != "(hidden)" else mac) if etype == "WIFI" else mac
    name = escape(raw_name[:30])
    desc = escape(f"{auth} | Ch:{channel} | {rssi}dBm | {mac} | {seen}")
    sym  = _GPX_SYM.get(etype, "Waypoint")

    lines = [f'  <wpt lat="{lat}" lon="{lon}">']
    if alt:
        lines.append(f'    <ele>{escape(alt)}</ele>')
    lines += [
        f'    <time>{seen.replace(" ", "T")}Z</time>',
        f'    <name>{name}</name>',
        f'    <desc>{desc}</desc>',
        f'    <sym>{sym}</sym>',
        f'  </wpt>',
    ]
    return lines


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_gpx(entries: list[dict], title_suffix: str = "") -> str:
    """
    Convert a list of wardrive log entries to a GPX 1.1 string.

    Entries without valid GPS coordinates are silently skipped.
    Each device becomes a <wpt> element with name, description and symbol.
    Compatible with Garmin eTrex 30HCx and other GPS devices.
    """
    valid = [
        e for e in entries
        if e.get("CurrentLatitude", "").strip() not in ("", "0", "0.0")
        and e.get("CurrentLongitude", "").strip() not in ("", "0", "0.0")
    ]
    skipped = len(entries) - len(valid)
    if skipped:
        print(f"  Skipped {skipped} entries without valid GPS coordinates.")

    doc_name = f"Wardrive {datetime.now():%Y-%m-%d}"
    if title_suffix:
        doc_name += f" [{title_suffix}]"

    wifi_count = sum(1 for e in valid if e.get("Type", "").strip() == "WIFI")
    ble_count  = sum(1 for e in valid if e.get("Type", "").strip() == "BLE")

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gpx version="1.1" creator="wardrive2map.py"',
        '    xmlns="http://www.topografix.com/GPX/1/1"',
        '    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
        '    xsi:schemaLocation="http://www.topografix.com/GPX/1/1',
        '    http://www.topografix.com/GPX/1/1/gpx.xsd">',
        f'  <metadata>',
        f'    <name>{escape(doc_name)}</name>',
        f'    <desc>{escape(f"WiFi: {wifi_count} | BLE: {ble_count}")}</desc>',
        f'    <time>{datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}</time>',
        f'  </metadata>',
    ]
    for e in valid:
        lines += _wpt(e)
    lines.append('</gpx>')
    return "\n".join(lines)
