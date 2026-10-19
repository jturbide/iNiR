# Qt palette comparison

A Qt 6 Widgets application using Breeze and the qt6ct platform theme.
The before image points qtct at iNiR's KDE-format Darkly.colors file.
The after image uses the generated iNiR-qtct.conf palette.
Both use the same source colors and style; the fixture is rendered offscreen.

These are PR review assets, kept outside the code contribution branch.

The preview.cpp source accepts a title and PNG output path. Set
QT_QPA_PLATFORM=offscreen and QT_QPA_PLATFORMTHEME=qt6ct with an isolated
XDG_CONFIG_HOME containing qt6ct/qt6ct.conf for each palette.
