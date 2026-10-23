#!/usr/bin/env python3
"""Build the KiCad PCM ZIP with tag-derived status and version metadata."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "kicad_part_marking"
PCM_ICON = ROOT / "assets" / "icon-64.png"
PACKAGE_NAME = "kicad-part-marking"
VERSION_PATTERN = re.compile(r"^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def run_git(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def project_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"(\d+\.\d+\.\d+)"\s*$', text, re.MULTILINE)
    if not match:
        raise RuntimeError("pyproject.toml must define a numeric X.Y.Z fallback version.")
    return match.group(1)


def resolve_build_version() -> tuple[str, str, str, bool]:
    """Return (version, status, short hash, clean exact version tag)."""
    fallback = project_version()
    commit = run_git("rev-parse", "--short=8", "HEAD") or "unknown"
    exact_tags = run_git("tag", "--points-at", "HEAD") or ""
    matching = sorted(
        (match.group(1), tag)
        for tag in exact_tags.splitlines()
        if (match := VERSION_PATTERN.fullmatch(tag)) is not None
    )
    status_output = run_git("status", "--porcelain", "--untracked-files=normal")
    clean = status_output == ""

    if len(matching) == 1:
        version, _tag = matching[0]
        return version, ("stable" if clean else "testing"), commit, clean
    if len(matching) > 1:
        # Multiple release versions on the same commit are ambiguous; still
        # produce a testing archive using a deterministic version choice.
        return matching[-1][0], "testing", commit, False

    nearest = run_git(
        "describe",
        "--tags",
        "--abbrev=0",
        "--match",
        "v[0-9]*.[0-9]*.[0-9]*",
    )
    nearest_match = VERSION_PATTERN.fullmatch(nearest or "")
    version = nearest_match.group(1) if nearest_match else fallback
    return version, "testing", commit, False


def package_metadata(version: str, status: str) -> dict[str, object]:
    return {
        "$schema": "https://go.kicad.org/pcm/schemas/v2",
        "name": "KiCad Part Marking",
        "description": "Create a native Micro QR part marking on copper and solder mask.",
        "description_full": (
            "Generates a Micro QR code on the selected solder-mask layer with a rounded, "
            "solid copper backing. The code and backing are grouped for interactive placement."
        ),
        "identifier": "org.edward.kicad.part-marking",
        "type": "plugin",
        "author": {"name": "Edward Chamberlain", "contact": {}},
        "license": "GPL-3.0",
        "resources": {},
        "versions": [
            {
                "version": version,
                "status": status,
                "kicad_version": "10.0",
                "runtime": "ipc",
            }
        ],
    }


def plugin_files() -> list[Path]:
    files: list[Path] = []
    for path in PLUGIN_ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(PLUGIN_ROOT)
        if "__pycache__" in relative.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        files.append(path)
    return sorted(files, key=lambda path: path.relative_to(PLUGIN_ROOT).as_posix())


def archive_name(version: str) -> str:
    return f"{PACKAGE_NAME}-{version}-PCM.zip"


def build(output_dir: Path) -> Path:
    if not PCM_ICON.is_file():
        raise RuntimeError(f"Missing PCM icon: {PCM_ICON}")
    files = plugin_files()
    if not files:
        raise RuntimeError(f"No plugin files found under {PLUGIN_ROOT}")

    version, status, commit, _clean_tag = resolve_build_version()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / archive_name(version)

    metadata_bytes = (
        json.dumps(package_metadata(version, status), indent=2, ensure_ascii=False)
        + "\n"
    ).encode("utf-8")

    # Use fixed ZIP timestamps so the same source produces a reproducible archive.
    zip_timestamp = (1980, 1, 1, 0, 0, 0)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{output_path.stem}-",
            suffix=".zip",
            dir=output_dir,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)

        with zipfile.ZipFile(temporary_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for source in files:
                relative = PurePosixPath("plugins") / source.relative_to(PLUGIN_ROOT).as_posix()
                info = zipfile.ZipInfo(relative.as_posix(), zip_timestamp)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (0o100644 & 0xFFFF) << 16
                archive.writestr(info, source.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

            icon_info = zipfile.ZipInfo("resources/icon.png", zip_timestamp)
            icon_info.compress_type = zipfile.ZIP_DEFLATED
            icon_info.external_attr = (0o100644 & 0xFFFF) << 16
            archive.writestr(icon_info, PCM_ICON.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

            metadata_info = zipfile.ZipInfo("metadata.json", zip_timestamp)
            metadata_info.compress_type = zipfile.ZIP_DEFLATED
            metadata_info.external_attr = (0o100644 & 0xFFFF) << 16
            archive.writestr(metadata_info, metadata_bytes, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

        with zipfile.ZipFile(temporary_path, "r") as archive:
            names = set(archive.namelist())
            required = {"plugins/plugin.json", "plugins/main.py", "resources/icon.png", "metadata.json"}
            if not required.issubset(names):
                raise RuntimeError(f"Archive is missing required PCM files: {sorted(required - names)}")
            parsed_metadata = json.loads(archive.read("metadata.json"))
            version_metadata = parsed_metadata["versions"][0]
            if version_metadata["status"] != status or version_metadata["runtime"] != "ipc":
                raise RuntimeError("Archived PCM status or runtime did not match the selected build.")
            if "download_url" in version_metadata or "download_sha256" in version_metadata:
                raise RuntimeError("Package archive metadata must not contain download location fields.")

        os.replace(temporary_path, output_path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    print(f"Built {output_path}")
    print(f"Version: {version} | status: {status} | commit: {commit}")
    if status == "testing":
        print("Testing build: the short commit hash is reported here, not in PCM version metadata or the ZIP filename.")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "dist",
        help="directory for the PCM ZIP (default: dist)",
    )
    args = parser.parse_args()
    try:
        build(args.output_dir.resolve())
    except Exception as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
