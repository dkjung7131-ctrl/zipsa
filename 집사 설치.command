#!/bin/bash
# 더블클릭 설치 — 터미널 명령어를 몰라도 됩니다.
# GitHub에서 Code → Download ZIP → 압축 풀기 → 이 파일을 더블클릭
cd "$(dirname "$0")" || exit 1
clear
echo "🐱 집사를 설치합니다..."
echo
if bash install.sh; then
  echo
  echo "🐾 설치가 끝났어요. 이 창은 닫아도 됩니다."
  echo "   (받아 온 이 폴더는 지워도 됩니다)"
else
  echo
  echo "설치를 마치지 못했어요. 위 메시지를 확인해 주세요."
  echo "개발 도구 설치 창이 떴다면, 설치를 마친 뒤 이 파일을 다시 더블클릭하세요."
fi
