#!/usr/bin/env python3
"""Apply iNiR's KDE colors in the palette format understood by qt5ct/qt6ct.

Called under apply-gtk-theme.sh's app-theme.lock. A standalone invocation must
hold that same lock. Qt5 ignores the final Qt6 Accent role in the shared palette.
"""

import argparse
import configparser
import os
from pathlib import Path
import stat
import tempfile


def read_ini(path):
    config = configparser.ConfigParser(interpolation=None, strict=False)
    config.optionxform = str
    with path.open() as stream:
        config.read_file(stream)
    return config


def palette(config, disabled=False, inactive=False):
    def color(group, key):
        section = f"Colors:{group}"
        if inactive and config.has_option(f"{section}][Inactive", key):
            section += "][Inactive"
        channels = tuple(int(value.strip()) for value in config[section][key].split(","))
        if len(channels) != 3 or any(value < 0 or value > 255 for value in channels):
            raise ValueError(f"Invalid RGB color: [{section}] {key}")
        return channels

    def foreground(group, key="ForegroundNormal"):
        return color(group, "ForegroundInactive" if disabled else key)

    def shade(rgb, factor):
        return tuple(max(0, min(255, round(value * factor))) for value in rgb)

    button = color("Button", "BackgroundNormal")
    # QPalette::ColorRole order, including NoRole at 17 and Qt6 Accent at 21.
    colors = [
        foreground("Window"),                       # WindowText
        button,                                      # Button
        shade(button, 1.5),                           # Light
        shade(button, 1.25),                          # Midlight
        shade(button, 1 / 1.5),                       # Dark
        shade(button, 1 / 1.25),                      # Mid
        foreground("View"),                         # Text
        foreground("Selection"),                    # BrightText
        foreground("Button"),                       # ButtonText
        color("View", "BackgroundNormal"),          # Base
        color("Window", "BackgroundNormal"),        # Window
        (0, 0, 0),                                   # Shadow
        color("View", "BackgroundAlternate") if disabled else color("Selection", "BackgroundNormal"),
        foreground("View" if disabled else "Selection"),  # HighlightedText
        foreground("View", "ForegroundLink"),       # Link
        foreground("View", "ForegroundVisited"),    # LinkVisited
        color("View", "BackgroundAlternate"),       # AlternateBase
        color("Window", "BackgroundNormal"),        # NoRole
        color("Tooltip", "BackgroundNormal"),       # ToolTipBase
        foreground("Tooltip"),                      # ToolTipText
        color("View", "ForegroundInactive"),        # PlaceholderText
        foreground("Window", "ForegroundActive"),   # Accent
    ]
    return ", ".join("#ff" + "".join(f"{channel:02x}" for channel in rgb) for rgb in colors)


def qsettings_string(value):
    if value.startswith("@"):
        value = "@" + value
    encoded = value.encode("utf-16-be", errors="surrogatepass")
    escaped = []
    after_hex = False
    # Qt5's default INI codec is not UTF-8; both versions read UTF-16 escapes.
    for index in range(0, len(encoded), 2):
        code = int.from_bytes(encoded[index:index + 2], "big")
        character = chr(code)
        if code < 32 or code > 126 or (after_hex and character in "0123456789abcdefABCDEF"):
            escaped.append(f"\\x{code:04x}")
            after_hex = True
        else:
            escaped.append("\\" + character if character in '\\"' else character)
            after_hex = False
    return ('"' + "".join(escaped) + '"').encode("ascii")


def appearance_entries(contents):
    # Qt's typed values and escapes are not ConfigParser's INI dialect.
    # Only the owned Appearance assignments may be rewritten.
    lines = contents.splitlines(keepends=True)
    appearance = False
    insertion = None
    assignments = {}
    for index, line in enumerate(lines):
        stripped = line.strip()
        if index == 0:
            stripped = stripped.removeprefix(b"\xef\xbb\xbf")
        if stripped.startswith(b"[") and b"]" in stripped:
            if appearance:
                insertion = index
            appearance = stripped[1:].partition(b"]")[0] == b"Appearance"
            if appearance:
                insertion = index + 1
        elif appearance and b"=" in line:
            key = line.partition(b"=")[0].strip()
            assignments.setdefault(key, []).append(index)
    if appearance:
        insertion = len(lines)
    return lines, assignments, insertion


def appearance_value(contents, key):
    lines, assignments, _ = appearance_entries(contents)
    indices = assignments.get(key, [])
    return lines[indices[-1]].partition(b"=")[2].strip() if indices else b""


def is_empty(value):
    return value in (b"", b'""')


def update_appearance(contents, values):
    lines, assignments, insertion = appearance_entries(contents)
    newline = b"\r\n" if any(line.endswith(b"\r\n") for line in lines) else b"\n"

    values = dict(values)
    styles = assignments.get(b"style", [])
    style = lines[styles[-1]].partition(b"=")[2].strip() if styles else b""
    if is_empty(style):
        values[b"style"] = b"Darkly"

    missing = []
    for key, value in values.items():
        if key not in assignments:
            missing.append(key + b"=" + value + newline)
        for index in assignments.get(key, []):
            line = lines[index]
            ending = b"\r\n" if line.endswith(b"\r\n") else b"\n" if line.endswith(b"\n") else b""
            lines[index] = line.partition(b"=")[0] + b"=" + value + ending

    if missing:
        if insertion is None:
            insertion = len(lines)
            missing.insert(0, b"[Appearance]" + newline)
        if insertion and not lines[insertion - 1].endswith((b"\n", b"\r")):
            missing.insert(0, newline)
        lines[insertion:insertion] = missing
    return b"".join(lines)


def write_if_changed(path, contents):
    # Preserve an existing configuration-file symlink and its target's mode.
    path = path.resolve()
    if path.is_file() and path.read_bytes() == contents:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(contents)
            stream.flush()
            os.fchmod(stream.fileno(), mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="iNiR-generated KDE .colors file")
    parser.add_argument("--icon-theme", default="", help="Resolved icon family; preserve current choice when empty")
    parser.add_argument("--fallback-icon-theme", default="Adwaita", help="Icon theme for configurations without a selection")
    args = parser.parse_args()
    config_home = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    data_home = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    output = data_home / "color-schemes/iNiR-qtct.conf"
    source = read_ini(args.source)
    contents = "; Generated by iNiR; shared Qt5/Qt6 QPalette roles.\n[ColorScheme]\n"
    contents += f"active_colors={palette(source)}\n"
    contents += f"inactive_colors={palette(source, inactive=True)}\n"
    contents += f"disabled_colors={palette(source, disabled=True)}\n"

    configs = {}
    for toolkit in ("qt5ct", "qt6ct"):
        target = config_home / toolkit / f"{toolkit}.conf"
        configs[toolkit] = (target, target.read_bytes() if target.exists() else b"")
    qt6_icon = appearance_value(configs["qt6ct"][1], b"icon_theme")
    updates = []
    for toolkit, (target, config) in configs.items():
        appearance = {
            b"color_scheme_path": qsettings_string(str(output)),
            b"custom_palette": b"true",
        }
        if args.icon_theme:
            appearance[b"icon_theme"] = qsettings_string(args.icon_theme)
        elif is_empty(appearance_value(config, b"icon_theme")):
            appearance[b"icon_theme"] = qt6_icon if not is_empty(qt6_icon) else qsettings_string(args.fallback_icon_theme)
        updates.append((target, update_appearance(config, appearance)))

    write_if_changed(output, contents.encode("utf-8"))
    for target, contents in updates:
        write_if_changed(target, contents)


if __name__ == "__main__":
    main()
