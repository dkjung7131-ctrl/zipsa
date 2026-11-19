#!/bin/bash
# 새 버전 배포 (개발자용)
#   1. zipsa.py의 VERSION을 올린다 (예: 1.2.0 → 1.2.1)
#   2. 커밋하고 git push
#   3. bash release.sh  → GitHub 릴리스 v1.2.1 생성. 사용자는 하루 안에 업데이트 알림을 받는다.
set -euo pipefail
cd "$(dirname "$0")"

ver=$(sed -n 's/^VERSION = "\([0-9.]*\)"$/\1/p' zipsa.py)
[[ -n "$ver" ]] || { echo "zipsa.py에서 VERSION을 찾지 못했습니다" >&2; exit 1; }
tag="v$ver"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "커밋하지 않은 변경이 있습니다. 먼저 커밋하세요." >&2; exit 1
fi
git fetch -q origin main
if [[ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]]; then
  echo "로컬과 origin/main이 다릅니다. 먼저 git push 하세요." >&2; exit 1
fi
if git ls-remote --exit-code --tags origin "refs/tags/$tag" >/dev/null 2>&1; then
  echo "$tag 는 이미 배포됐습니다. zipsa.py의 VERSION을 올리세요." >&2; exit 1
fi

gh release create "$tag" --target main --title "$tag" --generate-notes
echo "✓ $tag 배포 완료 — 사용자는 하루 안에 업데이트 알림을 받습니다."
