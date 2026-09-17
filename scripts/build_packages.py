#!/usr/bin/env python3
"""Validate uploaded Pinyin audio, build ZIP packages, and generate the Mini App manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

AUDIO_EXTS = {".mp3", ".m4a", ".aac", ".wav", ".ogg", ".opus"}
MAX_FILES_PER_PART = 900


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_pinyin(stem: str):
    match = re.fullmatch(r"(.+?)([1-5])", stem, flags=re.IGNORECASE)
    if not match:
        return stem, None
    return match.group(1), int(match.group(2))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--parts", type=int, choices=[2, 3], default=3)
    parser.add_argument("--expected", type=int, default=1338)
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--staging", default=".pinyin-staging")
    args = parser.parse_args()

    if not args.repo or "/" not in args.repo:
        raise SystemExit("Repository is required via --repo or GITHUB_REPOSITORY")
    if args.expected < 1:
        raise SystemExit("--expected must be >= 1")

    staging = Path(args.staging)
    dist = Path("dist")
    manifest_dir = Path("manifest")
    dist.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    for old in dist.iterdir():
        if old.is_file():
            old.unlink()

    final_tag = f"pinyin-v{args.version}"
    seen_names: set[str] = set()
    items = []
    packages = []
    total_source_bytes = 0
    total_package_bytes = 0

    for part_no in range(1, args.parts + 1):
        source_tag = f"pinyin-audio-v{args.version}-part{part_no}"
        source_dir = staging / f"part{part_no}"
        if not source_dir.is_dir():
            raise SystemExit(f"Missing staging directory: {source_dir}")

        files = sorted(
            [p for p in source_dir.iterdir() if p.is_file()],
            key=lambda p: p.name.casefold(),
        )
        if not files:
            raise SystemExit(f"{source_tag} contains no downloaded files")
        if len(files) > MAX_FILES_PER_PART:
            raise SystemExit(
                f"{source_tag} has {len(files)} files; keep each part <= {MAX_FILES_PER_PART}"
            )

        bad = [p.name for p in files if p.suffix.lower() not in AUDIO_EXTS]
        if bad:
            sample = ", ".join(bad[:10])
            raise SystemExit(f"{source_tag} contains unsupported files: {sample}")

        package_name = f"pinyin-v{args.version}-part{part_no}.zip"
        package_path = dist / package_name
        part_source_bytes = 0
        part_items = []

        with zipfile.ZipFile(
            package_path,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
            allowZip64=True,
        ) as archive:
            for audio in files:
                folded = audio.name.casefold()
                if folded in seen_names:
                    raise SystemExit(f"Duplicate audio filename across parts: {audio.name}")
                seen_names.add(folded)

                size = audio.stat().st_size
                if size <= 0:
                    raise SystemExit(f"Empty audio file: {audio}")

                stem = audio.stem
                syllable, tone = parse_pinyin(stem)
                digest = sha256_file(audio)
                archive.write(audio, arcname=audio.name)

                item = {
                    "id": stem,
                    "name": audio.name,
                    "stem": stem,
                    "syllable": syllable,
                    "tone": tone,
                    "part": part_no,
                    "package": package_name,
                    "path": audio.name,
                    "size": size,
                    "digest": f"sha256:{digest}",
                    "stream_url": (
                        f"https://github.com/{args.repo}/releases/download/"
                        f"{source_tag}/{quote(audio.name, safe='')}"
                    ),
                }
                part_items.append(item)
                items.append(item)
                part_source_bytes += size
                total_source_bytes += size

        package_size = package_path.stat().st_size
        package_digest = sha256_file(package_path)
        total_package_bytes += package_size
        packages.append(
            {
                "part": part_no,
                "id": f"part{part_no}",
                "source_release_tag": source_tag,
                "file": package_name,
                "count": len(part_items),
                "uncompressed_bytes": part_source_bytes,
                "size": package_size,
                "digest": f"sha256:{package_digest}",
                "download_url": (
                    f"https://github.com/{args.repo}/releases/download/"
                    f"{final_tag}/{package_name}"
                ),
            }
        )

    if len(items) != args.expected:
        counts = ", ".join(f"part{p['part']}={p['count']}" for p in packages)
        raise SystemExit(
            f"Expected {args.expected} audio files, found {len(items)} ({counts})"
        )

    items.sort(key=lambda item: item["name"].casefold())
    manifest = {
        "schema_version": 2,
        "ready": True,
        "content_version": str(args.version),
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "repository": args.repo,
        "final_release_tag": final_tag,
        "delivery": "github-release-zip-packages",
        "recommended_client_storage": "indexeddb",
        "offline_download": {
            "enabled": True,
            "download_packages_sequentially": True,
            "resume_unit": "package",
            "extract_one_package_at_a_time": True,
        },
        "total_items": len(items),
        "total_source_bytes": total_source_bytes,
        "total_package_bytes": total_package_bytes,
        "packages": packages,
        "items": items,
    }

    payload = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    versioned_manifest = manifest_dir / f"pinyin-v{args.version}.json"
    latest_manifest = manifest_dir / "latest.json"
    release_manifest = dist / f"pinyin-manifest-v{args.version}.json"
    versioned_manifest.write_text(payload, encoding="utf-8")
    latest_manifest.write_text(payload, encoding="utf-8")
    release_manifest.write_text(payload, encoding="utf-8")

    print(f"Validated {len(items)} audio files")
    print(f"Source: {total_source_bytes / 1024 / 1024:.2f} MiB")
    print(f"Packages: {total_package_bytes / 1024 / 1024:.2f} MiB")
    for package in packages:
        print(
            f"part{package['part']}: {package['count']} files -> "
            f"{package['file']} ({package['size'] / 1024 / 1024:.2f} MiB)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
