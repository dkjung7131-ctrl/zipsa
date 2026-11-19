#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
집사 Finder 확장 설치 도우미 (install.sh가 호출)

  setup.py appex-plist <Info.plist 경로> <번들 ID> <버전>   확장의 Info.plist 작성
  setup.py token <파일 경로>                                 링크 확인값(무작위) 작성
  setup.py prompt <번들 ID>                                  꺼져 있으면 켜는 방법 안내

macOS는 새 Finder 확장을 꺼진 채로 등록한다. 켜는 건 사용자가 직접 해야 한다
(시스템 설정 → 일반 → 로그인 항목 및 확장 프로그램 → 파일 제공자 → 집사).
"""
import os
import plistlib
import secrets
import subprocess
import sys

HOW_TO_ENABLE = ("시스템 설정 → 일반 → 로그인 항목 및 확장 프로그램 → (카테고리별) "
                 "파일 제공자 ⓘ → '집사'를 켜 주세요.")
SETTINGS_URL = "x-apple.systempreferences:com.apple.ExtensionsPreferences"
PROMPTED_MARK = "~/Library/Caches/zipsa/finder-extension-prompted"


def write_appex_plist(path, bundle_id, version):
    with open(path, "wb") as f:
        plistlib.dump({
            "CFBundleDevelopmentRegion": "ko",
            "CFBundleDisplayName": "집사",
            "CFBundleExecutable": "ZipsaFinder",
            "CFBundleIdentifier": bundle_id,
            "CFBundleInfoDictionaryVersion": "6.0",
            "CFBundleName": "ZipsaFinder",
            "CFBundlePackageType": "XPC!",
            "CFBundleShortVersionString": version,
            "CFBundleVersion": version,
            "CFBundleSupportedPlatforms": ["MacOSX"],
            "LSMinimumSystemVersion": "13.0",
            "NSExtension": {
                "NSExtensionAttributes": {},
                "NSExtensionPointIdentifier": "com.apple.FinderSync",
                "NSExtensionPrincipalClass": "ZipsaFinder.FinderSync",
            },
        }, f)


def write_token(path):
    with open(path, "w") as f:
        f.write(secrets.token_urlsafe(24))


def is_enabled(bundle_id):
    """pluginkit 목록에서 '+'로 시작하면 켜진 것 (읽기만 한다)"""
    try:
        out = subprocess.run(["/usr/bin/pluginkit", "-m", "-i", bundle_id], stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, universal_newlines=True, timeout=20).stdout
    except Exception:
        return False
    return any(line.startswith("+") and bundle_id in line for line in out.splitlines())


def dialog(message):
    """누른 버튼 이름 (실패하면 None)"""
    script = ["on run argv", "activate",
              'display dialog (item 1 of argv) with title "Zipsa" buttons {"나중에", "설정 열기"} '
              "default button 2 giving up after 300",
              "return button returned of result", "end run"]
    cmd = ["/usr/bin/osascript"]
    for line in script:
        cmd += ["-e", line]
    try:
        r = subprocess.run(cmd + [message], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           universal_newlines=True)
    except Exception:
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def prompt(bundle_id):
    """꺼져 있으면 켜는 방법을 출력하고, 처음 한 번은 대화상자로도 알린다"""
    if is_enabled(bundle_id):
        return
    print("\nFinder 우클릭 메뉴로 쓰려면 한 번만 켜 주세요:\n  " + HOW_TO_ENABLE)
    mark = os.path.expanduser(PROMPTED_MARK)
    if os.path.exists(mark):
        return
    try:
        os.makedirs(os.path.dirname(mark), exist_ok=True)
        open(mark, "w").close()
    except OSError:
        pass
    choice = dialog("🐾 이제 Finder에서 우클릭하면 '집사에게 압축 맡기기'가 바로 보여요.\n\n"
                    "처음 한 번만 켜 주세요:\n" + HOW_TO_ENABLE)
    if choice == "설정 열기":
        subprocess.run(["/usr/bin/open", SETTINGS_URL])


def main():
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "appex-plist":
        write_appex_plist(*args)
    elif cmd == "token":
        write_token(*args)
    elif cmd == "prompt":
        prompt(*args)
    else:
        sys.exit("unknown command: " + cmd)


if __name__ == "__main__":
    main()
