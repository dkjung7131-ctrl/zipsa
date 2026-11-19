#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Finder 빠른 동작 "집사에게 압축 맡기기"를 만든다 (install.sh가 호출).
Automator에서 손으로 만드는 것과 같은 결과:
  받는 항목 = 파일 또는 폴더, 위치 = Finder, 셸 스크립트 실행(/bin/zsh, 입력은 인수로)

사용: python3 quick_action.py <Services 폴더> <zipsa 명령어 경로>   → 만든 .workflow 경로 출력
"""
import os
import plistlib
import shutil
import sys
import uuid

NAME = "집사에게 압축 맡기기"
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


def main():
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
