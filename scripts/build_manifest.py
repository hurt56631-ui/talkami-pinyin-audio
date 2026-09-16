#!/usr/bin/env python3
"""Build Talkami Pinyin manifest from GitHub Release assets."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

AUDIO_EXTS = {".mp3", ".m4a", ".aac", ".wav", ".ogg", ".opus"}
MAX_ASSETS_PER_PART = 900


def gh_json(endpoint: str):
    proc = subprocess.run(
        ["gh", "api", endpoint],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or f"gh api failed: {endpoint}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON from GitHub API for {endpoint}: {exc}") from exc


def list_release_assets(repo: str, release_id: int):
    assets = []
    page = 1
    while True:
        batch = gh_json(
            f"repos/{repo}/releases/{release_id}/assets?per_page=100&page={page}"
        )
        if not isinstance(batch, list):
            raise SystemExit(f"Unexpected asset response for release {release_id}")
        assets.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return assets


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--parts", type=int, choices=[2, 3], default=3)
    parser.add_argument("--expected", type=int, default=1338)
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    args = parser.parse_args()

    if not args.repo or "/" not in args.repo:
        raise SystemExit("Repository is required via --repo or GITHUB_REPOSITORY")
    if args.expected < 1:
        raise SystemExit("--expected must be >= 1")

    all_items = []
    parts = []
    seen_names = set()
    total_bytes = 0

    for part_no in range(1, args.parts + 1):
        tag = f"pinyin-audio-v{args.version}-part{part_no}"
        release = gh_json(f"repos/{args.repo}/releases/tags/{tag}")
        release_id = int(release["id"])
        assets = list_release_assets(args.repo, release_id)

        if not assets:
            raise SystemExit(f"{tag} has no assets")
        if len(assets) > MAX_ASSETS_PER_PART:
            raise SystemExit(
                f"{tag} has {len(assets)} assets; keep each part <= {MAX_ASSETS_PER_PART}"
            )

        unsupported = []
        part_items = []
        part_bytes = 0

        for asset in assets:
            if asset.get("state") != "uploaded":
                raise SystemExit(
                    f"{tag}: asset {asset.get('name')} is not fully uploaded "
                    f"(state={asset.get('state')})"
                )

            name = str(asset.get("name", "")).strip()
            ext = Path(name).suffix.lower()
            if ext not in AUDIO_EXTS:
                unsupported.append(name or "<unnamed>")
                continue

            folded = name.casefold()
            if folded in seen_names:
                raise SystemExit(f"Duplicate audio filename across releases: {name}")
            seen_names.add(folded)

            size = int(asset.get("size") or 0)
            if size <= 0:
                raise SystemExit(f"{tag}: invalid size for {name}")

            browser_url = str(asset.get("browser_download_url", "")).strip()
            api_url = str(asset.get("url", "")).strip()
            if not browser_url:
                raise SystemExit(f"{tag}: missing browser_download_url for {name}")

            digest = asset.get("digest") or None
            item = {
                "id": f"part{part_no}:{name}",
                "name": name,
                "stem": Path(name).stem,
                "part": part_no,
                "release_tag": tag,
                "asset_id": int(asset["id"]),
                "size": size,
                "content_type": asset.get("content_type") or "application/octet-stream",
                "digest": digest,
                "download_url": browser_url,
                "api_url": api_url,
            }
            part_items.append(item)
            part_bytes += size
            total_bytes += size

        if unsupported:
            sample = ", ".join(unsupported[:10])
            extra = "" if len(unsupported) <= 10 else f" (+{len(unsupported) - 10} more)"
            raise SystemExit(f"{tag} contains unsupported files: {sample}{extra}")

        if not part_items:
            raise SystemExit(f"{tag} has no supported audio files")

        part_items.sort(key=lambda x: x["name"].casefold())
        all_items.extend(part_items)
        parts.append(
            {
                "part": part_no,
                "release_tag": tag,
                "release_id": release_id,
                "count": len(part_items),
                "bytes": part_bytes,
            }
        )

    if len(all_items) != args.expected:
        counts = ", ".join(f"part{p['part']}={p['count']}" for p in parts)
        raise SystemExit(
            f"Expected {args.expected} audio files, found {len(all_items)} ({counts})"
        )

    manifest = {
        "schema_version": 1,
        "ready": True,
        "content_version": str(args.version),
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "repository": args.repo,
        "storage": "github-release-assets",
        "recommended_client_storage": "indexeddb",
        "download_concurrency": 4,
        "total_items": len(all_items),
        "total_bytes": total_bytes,
        "parts": parts,
        "items": all_items,
    }

    out_dir = Path("manifest")
    out_dir.mkdir(parents=True, exist_ok=True)
    versioned = out_dir / f"pinyin-v{args.version}.json"
    latest = out_dir / "latest.json"
    payload = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    versioned.write_text(payload, encoding="utf-8")
    latest.write_text(payload, encoding="utf-8")

    mib = total_bytes / 1024 / 1024
    print(f"Built {versioned}: {len(all_items)} files, {mib:.2f} MiB")
    for part in parts:
        print(
            f"  part{part['part']}: {part['count']} files, "
            f"{part['bytes'] / 1024 / 1024:.2f} MiB"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
