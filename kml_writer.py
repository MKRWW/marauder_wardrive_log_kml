"""
kml_writer.py – KML export library for wardrive2map

Public API:
    build_kml(entries, title_suffix="") -> str
"""

from datetime import datetime
from xml.sax.saxutils import escape

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

# KML icon color format: AABBGGRR  (alpha, blue, green, red)
_STYLES: dict[str, tuple[str, float]] = {
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cdata(text: str) -> str:
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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_kml(entries: list[dict], title_suffix: str = "") -> str:
    """
    Convert a list of wardrive log entries to a KML string.

    Entries without valid GPS coordinates are silently skipped.
    WiFi and BLE devices are placed in separate KML folders.
    Placemarks are color-coded by RSSI signal strength.
    """
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

    doc_name = f"Wardrive {datetime.now():%Y-%m-%d}"
    if title_suffix:
        doc_name += f" [{title_suffix}]"

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        '<Document>',
        f'  <name>{escape(doc_name)}</name>',
        f'  <description>{_cdata(f"Exported {datetime.now():%Y-%m-%d %H:%M} | WiFi: {len(wifi)} | BLE: {len(ble)}")}</description>',
    ]

    lines += _style_xml()

    folders = [(f"WiFi Networks ({len(wifi)})", wifi)]
    if ble:
        folders.append((f"BLE Devices ({len(ble)})", ble))

    for folder_label, folder_entries in folders:
        lines += [f'  <Folder>', f'    <name>{folder_label}</name>']
        for e in folder_entries:
            lines += _placemark(e)
        lines.append('  </Folder>')

    lines += ['</Document>', '</kml>']
    return "\n".join(lines)
