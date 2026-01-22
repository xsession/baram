#!/usr/bin/env python
"""Create local release archives matching CI naming.

Outputs into dist/ by default:
- baram-<version>-windows.zip
- baram-<version>-linux.tar.gz
- baram-<version>-macos.tar.gz
- SHA256SUMS

Requires: git available on PATH.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import pathlib
import subprocess
import sys
import tempfile
from typing import Iterable


def run(cmd: list[str], *, cwd: pathlib.Path) -> None:
    subprocess.run(cmd, cwd=str(cwd), check=True)


def sha256sum(path: pathlib.Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def write_sha256sums(files: Iterable[pathlib.Path], out_file: pathlib.Path) -> None:
    lines = []
    for p in sorted(files, key=lambda x: x.name):
        lines.append(f"{sha256sum(p)}  {p.name}")
    out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version",
        required=True,
        help="Version/tag name to archive (e.g. v1.2.3). Must exist as a git ref.",
    )
    parser.add_argument(
        "--out",
        default="dist",
        help="Output directory (default: dist)",
    )

    args = parser.parse_args()

    repo_root = pathlib.Path(__file__).resolve().parents[1]
    out_dir = (repo_root / args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    version = args.version
    prefix = f"baram-{version}/"

    win_zip = out_dir / f"baram-{version}-windows.zip"
    linux_tgz = out_dir / f"baram-{version}-linux.tar.gz"
    mac_tgz = out_dir / f"baram-{version}-macos.tar.gz"

    # Validate the ref exists
    try:
        run(["git", "rev-parse", "--verify", "--quiet", version], cwd=repo_root)
    except subprocess.CalledProcessError:
        print(f"error: git ref not found: {version}", file=sys.stderr)
        return 2

    # Windows zip
    run(
        [
            "git",
            "archive",
            "--format=zip",
            f"--prefix={prefix}",
            "-o",
            str(win_zip),
            version,
        ],
        cwd=repo_root,
    )

    # Linux/macOS tar.gz (gzip in Python so Windows doesn't need external gzip)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = pathlib.Path(tmp)
        tmp_tar = tmp_dir / "baram.tar"
        run(
            [
                "git",
                "archive",
                "--format=tar",
                f"--prefix={prefix}",
                "-o",
                str(tmp_tar),
                version,
            ],
            cwd=repo_root,
        )

        tar_bytes = tmp_tar.read_bytes()
        for target in (linux_tgz, mac_tgz):
            with target.open("wb") as out_f:
                with gzip.GzipFile(filename=target.name, mode="wb", compresslevel=9, fileobj=out_f) as gz:
                    gz.write(tar_bytes)

    sums = out_dir / "SHA256SUMS"
    write_sha256sums([win_zip, linux_tgz, mac_tgz], sums)

    print(f"Wrote: {win_zip.name}")
    print(f"Wrote: {linux_tgz.name}")
    print(f"Wrote: {mac_tgz.name}")
    print(f"Wrote: {sums.name}")
    print(f"Output dir: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
