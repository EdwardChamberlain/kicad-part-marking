# KiCad Part Marking

A KiCad PCB Editor IPC plugin that adds a Micro QR part marking. The code is
drawn on the solder-mask layer over a solid copper square, so each module is
exposed copper. The barcode and copper are grouped and placed with the mouse.

## Requirements

- KiCad 10.0.1 or newer (the barcode API arrived in 10.0.1).
- The IPC API server enabled in **Preferences → Plugins**.

## Using it

Click **Generate Part Marking** in the PCB Editor toolbar and enter:

- **Marking size**: the overall square in mm, including a 0.1 mm copper
  border on each edge.
- **Side**: Front or Back.
- **Code text**: up to 35 digits, 21 upper-case characters
  (A–Z, 0–9, space, `$%*+-./:`), or 15 bytes of other text.

The marking appears at the centre of the board outline and follows the cursor;
click to place it. Escape leaves it where it started; undo twice removes it (once for the group, once for the items).

## Running from a terminal

No install is needed. With the board open in KiCad's PCB Editor:

```sh
python -m venv .venv
.venv/bin/pip install -r kicad_part_marking/requirements.txt
.venv/bin/python kicad_part_marking/main.py
```

That opens the settings dialog. To skip it, pass the settings instead:

```sh
.venv/bin/python kicad_part_marking/main.py --text "PN-1234 R2" --size 3 --side front
```

## Files

```
kicad_part_marking/   the plugin folder KiCad loads
  plugin.json         action definition
  main.py             entrypoint
  dialog.py           settings dialog (PySide6 / Qt)
  marking.py          builds and places the marking
pcm/                  PCM package metadata and icon
scripts/build_plugin.py
scripts/generate_icons.py
tests/
```

## Development

Install by symlinking `kicad_part_marking/` into KiCad's plugins folder
(macOS and Windows: `~/Documents/KiCad/10.0/plugins/`, Linux:
`~/.local/share/KiCad/10.0/plugins/`). KiCad installs `requirements.txt` into
the plugin's own Python environment the first time it loads. That includes
PySide6 for the dialog, roughly a 100 MB download, so the first run is slow.

Run the tests (no KiCad needed):

```sh
python -m venv .venv
.venv/bin/pip install -r kicad_part_marking/requirements.txt
.venv/bin/python -m unittest discover -s tests
```

Errors are shown in a dialog and printed with a traceback to the console.

## PCM package

Set the version and status (`testing` or `stable`) in `pcm/metadata.json`, then:

```sh
pip install -r requirements-build.txt
python scripts/build_plugin.py
```

The ZIP is written to `dist/`.

The build first regenerates the icons with `scripts/generate_icons.py`: a gold
(ENIG) Micro QR code encoding "Hello PCB!" on green solder mask, at 24, 48 and
64 px for the toolbar and 64 px for the package manager. Those sizes keep every
module a whole number of pixels. The generated PNGs are committed so the plugin
folder works without a build.
