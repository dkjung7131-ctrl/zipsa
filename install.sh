#!/bin/bash
# 집사(Zipsa) 설치 스크립트 (macOS)
#   - 터미널 명령어: ~/.local/bin/zipsa
#   - 드래그&드롭 앱: ~/Applications/집사.app
#   - Finder 빠른 동작: ~/Library/Services/집사에게 압축 맡기기.workflow
set -euo pipefail
cd "$(dirname "$0")"

if [[ "$(uname)" != "Darwin" ]]; then
  echo "macOS에서만 설치할 수 있습니다." >&2; exit 1
fi

# macOS 기본 python3 (Xcode Command Line Tools에 포함) 확인
if ! /usr/bin/python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' >/dev/null 2>&1; then
  echo "python3가 필요합니다 (Xcode Command Line Tools)."
  echo "설치 창이 뜨면 설치를 마친 뒤 이 스크립트를 다시 실행하세요."
  xcode-select --install 2>/dev/null || true
  exit 1
fi

BIN_DIR="$HOME/.local/bin"
APP="$HOME/Applications/집사.app"
RES="$APP/Contents/Resources"
PLIST="$APP/Contents/Info.plist"
mkdir -p "$BIN_DIR" "$HOME/Applications"

# 이전 이름(CleanZip)으로 설치한 적이 있으면 정리
rm -rf "$HOME/Applications/CleanZip.app" "$BIN_DIR/cleanzip"

# 1) 터미널 명령어 (cat으로 복사 → 다운로드 격리 속성이 따라오지 않음)
cat zipsa.py > "$BIN_DIR/zipsa"
chmod 755 "$BIN_DIR/zipsa"
echo "✓ 명령어 설치: $BIN_DIR/zipsa"

# 2) 드래그&드롭 앱
rm -rf "$APP"
osacompile -o "$APP" droplet.applescript
cat zipsa.py > "$RES/zipsa.py"

# 아이콘 교체: 에셋 카탈로그 아이콘을 지우고 applet.icns를 쓰도록
cat zipsa.icns > "$RES/applet.icns"
rm -f "$RES/Assets.car"
/usr/libexec/PlistBuddy -c "Delete :CFBundleIconName" "$PLIST" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Set :CFBundleIconFile applet" "$PLIST" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Add :CFBundleIconFile string applet" "$PLIST"

xattr -cr "$APP" 2>/dev/null || true
codesign --force --deep --sign - "$APP" >/dev/null 2>&1 || true
touch "$APP"   # Finder 아이콘 캐시 갱신
echo "✓ 앱 설치: $APP"

# 3) Finder 우클릭 → 빠른 동작 → 집사에게 압축 맡기기
mkdir -p "$HOME/Library/Services"
WF=$(/usr/bin/python3 -I quick_action.py "$HOME/Library/Services" "$BIN_DIR/zipsa")
/System/Library/CoreServices/pbs -update >/dev/null 2>&1 || true   # 서비스 메뉴 목록 갱신
echo "✓ 빠른 동작 설치: $WF"
# macOS는 이렇게 설치한 빠른 동작을 꺼 둔다 → 꺼져 있으면 켜는 방법 안내 (대화상자는 처음 한 번만)
/usr/bin/python3 -I quick_action.py --prompt-enable || true

# 'zipsa --update'가 부른 경우: 안내 문구와 Finder 열기는 생략
[[ -n "${ZIPSA_UPDATING:-}" ]] && exit 0

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *) echo
     echo "터미널에서 'zipsa'로 바로 쓰려면:"
     echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc && source ~/.zshrc" ;;
esac

echo
echo "Finder에서 우클릭 → 빠른 동작 → '집사에게 압축 맡기기'로도 쓸 수 있습니다."
open -R "$APP" 2>/dev/null || true
