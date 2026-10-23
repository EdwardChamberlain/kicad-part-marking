#!/usr/bin/env python3
"""Build the KiCad PCM ZIP: plugin files, icon and metadata.

Version and status (testing/stable) come from pcm/metadata.json.
"""

import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / "kicad_part_marking"
PCM_DIR = ROOT / "pcm"


def main() -> None:
    metadata = json.loads((PCM_DIR / "metadata.json").read_text(encoding="utf-8"))
    version = metadata["versions"][0]["version"]
    output = ROOT / "dist" / f"kicad-part-marking-{version}-PCM.zip"
    output.parent.mkdir(exist_ok=True)

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(PLUGIN_DIR.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                archive.write(path, f"plugins/{path.relative_to(PLUGIN_DIR).as_posix()}")
        archive.write(PCM_DIR / "icon.png", "resources/icon.png")
        archive.write(PCM_DIR / "metadata.json", "metadata.json")

    print(f"Built {output.relative_to(ROOT)} ({metadata['versions'][0]['status']})")


if __name__ == "__main__":
    main()
