#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Finder 빠른 동작 "집사에게 압축 맡기기"를 만든다 (install.sh가 호출).
Automator에서 손으로 만드는 것과 같은 결과:
  받는 항목 = 파일 또는 폴더, 위치 = Finder, 셸 스크립트 실행(/bin/zsh, 입력은 인수로)

사용: python3 quick_action.py <Services 폴더> <zipsa 명령어 경로>   → 만든 .workflow 경로 출력
      python3 quick_action.py --prompt-enable   → 꺼져 있으면 켜는 방법 안내 (대화상자는 처음 한 번만)

macOS는 파일로 설치한 빠른 동작을 꺼진 채로 등록한다. 켜는 건 사용자가 직접 해야 한다
(Finder 우클릭 → 빠른 동작 → 사용자화…). 켜면 pbs 설정의 NSServicesStatus에 기록된다.
"""
import os
import plistlib
import shutil
import subprocess
import sys
import unicodedata
import uuid

NAME = "집사에게 압축 맡기기"
HOW_TO_ENABLE = ("Finder에서 아무 파일이나 우클릭 → 빠른 동작 → 사용자화… 를 누르고 "
                 "'%s'를 켜 주세요." % NAME)
PROMPTED_MARK = "~/Library/Caches/zipsa/quick-action-prompted"
FINDER = "/System/Library/CoreServices/Finder.app"
ACTION = "/System/Library/Automator/Run Shell Script.action"


def _arg(i, name, default):
    return {"default value": default, "name": name, "required": "0", "type": "0", "uuid": str(i)}


def build(zipsa):
    command = '"%s" --notify "$@"' % zipsa.replace("\\", "\\\\").replace('"', '\\"')
    strings = {"Container": "List", "Types": ["com.apple.cocoa.string"]}
    action = {
        "AMAccepts": dict(strings, Optional=True),
        "AMActionVersion": "2.0.3",
        "AMApplication": ["Automator"],
        "AMParameterProperties": {k: {} for k in
                                  ("COMMAND_STRING", "CheckedForUserDefaultShell", "inputMethod", "shell", "source")},
        "AMProvides": strings,
        "ActionBundlePath": ACTION,
        "ActionName": "Run Shell Script",
        "ActionParameters": {
            "COMMAND_STRING": command,
            "CheckedForUserDefaultShell": True,
            "inputMethod": 1,          # 입력 전달: 인수로
            "shell": "/bin/zsh",
            "source": "",
        },
        "BundleIdentifier": "com.apple.RunShellScript",
        "CFBundleVersion": "2.0.3",
        "CanShowSelectedItemsWhenRun": False,
        "CanShowWhenRun": True,
        "Category": ["AMCategoryUtilities"],
        "Class Name": "RunShellScriptAction",
        "InputUUID": str(uuid.uuid4()).upper(),
        "Keywords": ["Shell", "Script", "Command", "Run", "Unix"],
        "OutputUUID": str(uuid.uuid4()).upper(),
        "UUID": str(uuid.uuid4()).upper(),
        "UnlocalizedApplications": ["Automator"],
        "arguments": {
            "0": _arg(0, "inputMethod", 0),
            "1": _arg(1, "CheckedForUserDefaultShell", False),
            "2": _arg(2, "source", ""),
            "3": _arg(3, "COMMAND_STRING", ""),
            "4": _arg(4, "shell", "/bin/sh"),
        },
        "conversionLabel": 0,
        "isViewVisible": 1,
        "location": "309.000000:305.000000",
        "nibPath": ACTION + "/Contents/Resources/Base.lproj/main.nib",
    }
    document = {
        "AMApplicationBuild": "534",
        "AMApplicationVersion": "2.10",
        "AMDocumentVersion": "2",
        "actions": [{"action": action, "isViewVisible": 1}],
        "connectors": {},
        "workflowMetaData": {
            "applicationBundleID": "com.apple.finder",
            "applicationBundleIDsByPath": {FINDER: "com.apple.finder"},
            "applicationPath": FINDER,
            "applicationPaths": [FINDER],
            "inputTypeIdentifier": "com.apple.Automator.fileSystemObject",
            "outputTypeIdentifier": "com.apple.Automator.nothing",
            "presentationMode": 15,
            "processesInput": False,
            "serviceApplicationBundleID": "com.apple.finder",
            "serviceApplicationPath": FINDER,
            "serviceInputTypeIdentifier": "com.apple.Automator.fileSystemObject",
            "serviceOutputTypeIdentifier": "com.apple.Automator.nothing",
            "serviceProcessesInput": False,
            "systemImageName": "NSActionTemplate",
            "useAutomaticInputType": False,
            "workflowTypeIdentifier": "com.apple.Automator.servicesMenu",
        },
    }
    info = {
        "NSServices": [{
            "NSBackgroundColorName": "background",
            "NSIconName": "NSActionTemplate",
            "NSMenuItem": {"default": NAME},
            "NSMessage": "runWorkflowAsService",
            "NSRequiredContext": {"NSApplicationIdentifier": "com.apple.finder"},
            "NSSendFileTypes": ["public.item"],
        }]
    }
    return info, document


def services_status():
    """pbs 설정의 NSServicesStatus (읽기만 한다)"""
    try:
        out = subprocess.run(["/usr/bin/defaults", "export", "pbs", "-"], stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, timeout=10).stdout
        status = plistlib.loads(out).get("NSServicesStatus", {})
    except Exception:
        return {}
    return status if isinstance(status, dict) else {}


def is_enabled(status=None):
    """Finder 우클릭 메뉴에 켜져 있는지. 키 형식: '(null) - <메뉴 이름> - runWorkflowAsService'"""
    status = services_status() if status is None else status
    suffix = unicodedata.normalize("NFC", " - %s - runWorkflowAsService" % NAME)
    for key, value in status.items():
        if unicodedata.normalize("NFC", str(key)).endswith(suffix) and isinstance(value, dict):
            modes = value.get("presentation_modes")
            return isinstance(modes, dict) and bool(modes.get("ContextMenu"))
    return False


def show_dialog(message):
    script = ["on run argv", "activate",
              'display dialog (item 1 of argv) with title (item 2 of argv) buttons {"확인"} '
              "default button 1 giving up after 300",
              "end run"]
    cmd = ["/usr/bin/osascript"]
    for line in script:
        cmd += ["-e", line]
    subprocess.run(cmd + [message, "집사"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def prompt_enable():
    """꺼져 있으면 켜는 방법을 출력하고, 처음 한 번은 대화상자로도 알린다"""
    if is_enabled():
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
    show_dialog("🐾 집사를 Finder 우클릭 메뉴에서도 쓸 수 있어요.\n\n" + HOW_TO_ENABLE)


def main():
    if sys.argv[1:] == ["--prompt-enable"]:
        prompt_enable()
        return
    services, zipsa = sys.argv[1], sys.argv[2]
    out = os.path.join(services, NAME + ".workflow")
    shutil.rmtree(out, ignore_errors=True)   # 예전에 만든 것(손으로 만든 것 포함)은 새로 교체
    contents = os.path.join(out, "Contents")
    os.makedirs(contents)
    info, document = build(zipsa)
    for name, data in (("Info.plist", info), ("document.wflow", document)):
        with open(os.path.join(contents, name), "wb") as f:
            plistlib.dump(data, f)
    print(out)


if __name__ == "__main__":
    main()
