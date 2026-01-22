#!/usr/bin/env python
"""Create a binary release archive for the current platform.

This builds PyInstaller bundles (baramFlow + baramMesh) and packages them into:
- dist/baram-<version>-<platform>-binaries.zip

Also writes/updates:
- dist/SHA256SUMS-binaries-<platform>

Notes:
- Requires PyInstaller (`requirements-build.txt`).
- Requires Qt build tools to generate `resource_rc.py` and `*_ui.py` via convertUi.py.
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import platform
import sys
import zipfile

repo_root = pathlib.Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from tools.build_binaries import platform_id


def sha256sum(path: pathlib.Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def zip_dir(zip_path: pathlib.Path, root_dir: pathlib.Path, *, prefix: str) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in root_dir.rglob("*"):
            if p.is_dir():
                continue
            rel = p.relative_to(root_dir)
            z.write(p, arcname=str(pathlib.PurePosixPath(prefix) / rel.as_posix()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True, help="Version/tag label to embed in artifact names")
    parser.add_argument("--out", default="dist", help="Output directory (default: dist)")
    parser.add_argument("--clean", action="store_true", help="Clean build caches")
    args = parser.parse_args()

    out_dir = (repo_root / args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build into dist-binaries/<platform>/...
    cmd = [sys.executable, str(repo_root / "tools" / "build_binaries.py")]
    if args.clean:
        cmd.append("--clean")
    # keep output stable for CI
    cmd += ["--out", "dist-binaries"]

    import subprocess

    subprocess.run(cmd, cwd=str(repo_root), check=True)

    plat = platform_id()
    built_root = repo_root / "dist-binaries" / plat
    if not built_root.exists():
        raise FileNotFoundError(built_root)

    version = args.version
    zip_path = out_dir / f"baram-{version}-{plat}-binaries.zip"

    # Put both app bundles under a single top folder
    top = f"baram-{version}-{plat}-binaries"

    # Create a temporary staging dir structure in-memory by writing files with prefixed names
    # (zip_dir handles prefixing all entries)
    zip_dir(zip_path, built_root, prefix=top)

    sums_path = out_dir / f"SHA256SUMS-binaries-{plat}"
    sums_path.write_text(f"{sha256sum(zip_path)}  {zip_path.name}\n", encoding="utf-8")

    print(f"Wrote: {zip_path}")
    print(f"Wrote: {sums_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
