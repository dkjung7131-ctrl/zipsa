#!/bin/bash
# 집사(Zipsa) 설치 스크립트 (macOS)
#   - 터미널 명령어: ~/.local/bin/zipsa
#   - 드래그&드롭 앱: ~/Applications/집사.app
#   - Finder 우클릭 메뉴: 집사.app 안의 Finder 확장 (Swift로 빌드)
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
APP_ID="io.github.dkjung7131-ctrl.zipsa"
EXT_ID="$APP_ID.finder"
EXT="$APP/Contents/PlugIns/ZipsaFinder.appex"
VERSION=$(sed -n 's/^VERSION = "\([0-9.]*\)"$/\1/p' zipsa.py)
LSREGISTER=/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister
mkdir -p "$BIN_DIR" "$HOME/Applications"

# 이전 이름(CleanZip)으로 설치한 적이 있으면 정리
rm -rf "$HOME/Applications/CleanZip.app" "$BIN_DIR/cleanzip"

# 1) 터미널 명령어 (cat으로 복사 → 다운로드 격리 속성이 따라오지 않음)
cat zipsa.py > "$BIN_DIR/zipsa"
chmod 755 "$BIN_DIR/zipsa"
echo "✓ 명령어 설치: $BIN_DIR/zipsa"

# 2) 드래그&드롭 앱 (+ Finder 확장이 보내는 zipsa-finder:// 링크를 받는 역할)
pkill -x ZipsaFinder 2>/dev/null || true   # 예전 확장 프로세스 정리 (새로 빌드한 걸 다시 띄우기 위해)
rm -rf "$APP"
osacompile -o "$APP" droplet.applescript
cat zipsa.py > "$RES/zipsa.py"

# 아이콘 교체: 에셋 카탈로그 아이콘을 지우고 applet.icns를 쓰도록
cat zipsa.icns > "$RES/applet.icns"
rm -f "$RES/Assets.car"
/usr/libexec/PlistBuddy -c "Delete :CFBundleIconName" "$PLIST" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Set :CFBundleIconFile applet" "$PLIST" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Add :CFBundleIconFile string applet" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :CFBundleIdentifier string $APP_ID" "$PLIST" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier $APP_ID" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :CFBundleURLTypes array" -c "Add :CFBundleURLTypes:0 dict" \
  -c "Add :CFBundleURLTypes:0:CFBundleURLName string Zipsa Finder" \
  -c "Add :CFBundleURLTypes:0:CFBundleURLSchemes array" \
  -c "Add :CFBundleURLTypes:0:CFBundleURLSchemes:0 string zipsa-finder" "$PLIST"

# 3) Finder 우클릭 메뉴: 앱 안에 Finder 확장 빌드 (실패해도 명령어·앱은 그대로 씀)
FINDER_OK=""
mkdir -p "$EXT/Contents/MacOS" "$EXT/Contents/Resources"
if swiftc -O -module-name ZipsaFinder -parse-as-library -application-extension \
     -target "$(uname -m)-apple-macos13.0" -framework Cocoa -framework FinderSync \
     -Xlinker -e -Xlinker _NSExtensionMain \
     finder/FinderSync.swift -o "$EXT/Contents/MacOS/ZipsaFinder" >/dev/null 2>&1; then
  /usr/bin/python3 -I finder/setup.py appex-plist "$EXT/Contents/Info.plist" "$EXT_ID" "$VERSION"
  /usr/bin/python3 -I finder/setup.py token "$EXT/Contents/Resources/token"
  FINDER_OK=1
else
  rm -rf "$APP/Contents/PlugIns"
  echo "⚠ Finder 우클릭 메뉴를 빌드하지 못했습니다 (swiftc). 앱과 명령어는 그대로 쓸 수 있습니다." >&2
fi

# 서명: 확장은 샌드박스 권한과 함께 먼저, 그다음 앱 (--deep을 쓰면 확장 권한이 지워짐)
xattr -cr "$APP" 2>/dev/null || true
if [[ -n "$FINDER_OK" ]]; then
  codesign --force --sign - --entitlements finder/ZipsaFinder.entitlements "$EXT" >/dev/null 2>&1 || true
fi
codesign --force --sign - "$APP" >/dev/null 2>&1 || true
touch "$APP"   # Finder 아이콘 캐시 갱신
"$LSREGISTER" -f -R "$APP" >/dev/null 2>&1 || true   # 링크·확장 등록
echo "✓ 앱 설치: $APP"

# 예전 버전(1.2.x)의 빠른 동작은 확장과 메뉴가 겹치므로 정리
rm -rf "$HOME/Library/Services/집사에게 압축 맡기기.workflow"
/System/Library/CoreServices/pbs -update >/dev/null 2>&1 || true

if [[ -n "$FINDER_OK" ]]; then
  pluginkit -a "$EXT" >/dev/null 2>&1 || true   # 등록 + (켜져 있으면) 새 확장 실행
  echo "✓ Finder 우클릭 메뉴 설치"
  # macOS는 새 확장을 꺼 둔다 → 꺼져 있으면 켜는 방법 안내 (대화상자는 처음 한 번만)
  /usr/bin/python3 -I finder/setup.py prompt "$EXT_ID" || true
fi

# 'zipsa --update'가 부른 경우: 안내 문구와 Finder 열기는 생략
[[ -n "${ZIPSA_UPDATING:-}" ]] && exit 0

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *) echo
     echo "터미널에서 'zipsa'로 바로 쓰려면:"
     echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc && source ~/.zshrc" ;;
esac

echo
echo "Finder에서 우클릭 → '집사에게 압축 맡기기'로도 쓸 수 있습니다."
open -R "$APP" 2>/dev/null || true
