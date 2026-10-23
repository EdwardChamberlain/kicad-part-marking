# KiCad Part Marking

A KiCad PCB Editor IPC plugin that creates a grouped Micro QR part marking. The
QR pattern is placed on the solder-mask layer, over a rounded, solid copper
backing, so the code is exposed copper rather than silkscreen artwork.

## Requirements

- KiCad 10.0.1 or newer for the native Micro QR barcode API.
- Python 3.9 or newer for local development.
- KiCad's IPC API server enabled in **Preferences → Plugins**.

KiCad 9 supports the initial IPC API, but the barcode APIs used for this
project are only available in later KiCad and `kicad-python` releases.

## Plugin layout

`kicad_part_marking/` is the self-contained plugin directory. Copy it or
symlink it into KiCad's version-specific `plugins` directory. Typical locations
are:

- macOS: `~/Documents/KiCad/10.0/plugins/`
- Windows: `~/Documents/KiCad/10.0/plugins/`
- Linux: `~/.local/share/KiCad/10.0/plugins/`

KiCad reads `plugin.json`, creates the plugin's Python environment, and adds
the action to the PCB Editor toolbar. The first load can take a little while
while dependencies are installed.

## Local development

Create a virtual environment and install the plugin requirements:

```sh
python -m venv .venv
. .venv/bin/activate  # On Windows: .venv\\Scripts\\activate
python -m pip install -r kicad_part_marking/requirements.txt
```

Run the entrypoint from a terminal while KiCad is open and its IPC API is
enabled:

```sh
python kicad_part_marking/main.py
```

When launched by KiCad, the plugin receives `KICAD_API_SOCKET` and
`KICAD_API_TOKEN` automatically. The action asks for an overall marking side
in millimetres (including the copper border), top/bottom side, and code text.
The Micro QR itself is inset by 0.1 mm on every edge and uses error correction
level L. Escape during cursor placement discards the unplaced group.

## PCM package

Build a KiCad Plugin and Content Manager (PCM) archive with:

```sh
python scripts/build_plugin.py
```

The ZIP is written to `dist/kicad-part-marking-X.Y.Z-PCM.zip`. A clean build
from an exact `vX.Y.Z` Git tag is marked `stable`; other builds are marked
`testing` in the archive's `metadata.json`. Testing builds keep the tagged
`X.Y.Z` version and print the short commit hash in build output. The PCM ZIP
contains only package files; repository download URL and hash fields are
intentionally omitted until the package is published.
