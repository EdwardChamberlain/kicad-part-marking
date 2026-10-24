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
- **Side**: Top or Bottom.
- **Code text**: up to 35 digits, 21 upper-case characters
  (A–Z, 0–9, space, `$%*+-./:`), or 15 bytes of other text.

The marking appears at the centre of the board outline and follows the cursor;
click to place it. Escape leaves it where it started; undo twice removes it (once for the group, once for the items).

## Running from a terminal

No install is needed. With the board open in KiCad's PCB Editor:

```sh
python -m venv .venv
.venv/bin/pip install -r kicad_part_marking/requirements.txt
.venv/bin/python kicad_part_marking/main.py --text "PN-1234 R2" --size 5 --side top
```

Passing `--text` skips the dialog. Without it, the Tk dialog opens, which
needs a Python with Tk (Homebrew Python needs `brew install python-tk`).

## Files

```
kicad_part_marking/   the plugin folder KiCad loads
  plugin.json         action definition
  main.py             entrypoint
  dialog.py           settings dialog (Tk)
  marking.py          builds and places the marking
pcm/                  PCM package metadata and icon
scripts/build_plugin.py
tests/
```

## Development

Install by symlinking `kicad_part_marking/` into KiCad's plugins folder
(macOS and Windows: `~/Documents/KiCad/10.0/plugins/`, Linux:
`~/.local/share/KiCad/10.0/plugins/`). KiCad installs `requirements.txt` into
the plugin's own Python environment the first time it loads.

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
python scripts/build_plugin.py
```

The ZIP is written to `dist/`.
