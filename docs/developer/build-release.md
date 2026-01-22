# Build & Release

## Tag-based releases
- GitHub Actions: `.github/workflows/release.yml`
- GitLab CI: `.gitlab-ci.yml`

## Source archives
- `tools/make_release.py` generates archives from a git ref using `git archive`.

## Binary bundles
- `tools/make_binary_release.py` builds PyInstaller bundles for the current OS and packages them.

![Release pipeline](../assets/diagrams/release-pipeline.svg)
