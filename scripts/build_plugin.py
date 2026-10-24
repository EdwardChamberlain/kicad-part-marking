#!/usr/bin/env python3
"""Build the KiCad PCM ZIP: regenerate the icons, then zip plugin files, icon and metadata.

Version and status (testing/stable) come from pcm/metadata.json.
Needs the build requirements: pip install -r requirements-build.txt
"""

import json
from pathlib import Path
import zipfile

import generate_icons

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / "kicad_part_marking"
PCM_DIR = ROOT / "pcm"
# Only the plugin's own files: skips caches, egg-info and other local leftovers.
PLUGIN_SUFFIXES = {".py", ".json", ".txt", ".png"}


def main() -> None:
    generate_icons.main()
    metadata = json.loads((PCM_DIR / "metadata.json").read_text(encoding="utf-8"))
    version = metadata["versions"][0]["version"]
    output = ROOT / "dist" / f"kicad-part-marking-{version}-PCM.zip"
    output.parent.mkdir(exist_ok=True)
    if output.exists():
        print(f"Note: replacing an existing {version} build. KiCad treats a same-version"
              " reinstall unreliably; bump the version in pcm/metadata.json for a new release.")

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(PLUGIN_DIR.iterdir()):
            if path.is_file() and path.suffix in PLUGIN_SUFFIXES:
                archive.write(path, f"plugins/{path.relative_to(PLUGIN_DIR).as_posix()}")
        archive.write(PCM_DIR / "icon.png", "resources/icon.png")
        archive.write(PCM_DIR / "metadata.json", "metadata.json")

    print(f"Built {output.relative_to(ROOT)} ({metadata['versions'][0]['status']})")


if __name__ == "__main__":
    main()
