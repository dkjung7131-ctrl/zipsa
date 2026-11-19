#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zipsa (집사) — 윈도우에서 깨지지 않는 ZIP을 만드는 macOS용 압축 도구

  1. macOS 전용 파일 제외: .DS_Store, ._* (AppleDouble), __MACOSX, .Spotlight-V100 등
     (확장 속성 / 리소스 포크도 저장하지 않음)
  2. 파일명을 NFC로 정규화 + UTF-8 플래그 기록 → 윈도우에서 한글 자소 분리·깨짐 없음

표준 라이브러리만 사용 (macOS 기본 python3 3.9 이상에서 동작)
"""
import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import unicodedata
import urllib.request
import zipfile
from collections import Counter

VERSION = "1.2.2"

# 새 버전은 GitHub 릴리스(태그 vX.Y.Z)로 배포한다. main에 push만 한 변경은 사용자에게 가지 않는다.
REPO_URL = "https://github.com/dkjung7131-ctrl/zipsa"
CHECK_INTERVAL = 24 * 60 * 60   # 새 버전 자동 확인은 하루 한 번
CACHE_FILE = "~/Library/Caches/zipsa/update.json"

# 압축에서 빼는 macOS 전용 파일/폴더 (이름이 '._'로 시작하는 AppleDouble 파일도 제외)
JUNK_NAMES = {
    ".DS_Store", "__MACOSX", ".Spotlight-V100", ".Trashes", ".fseventsd",
    ".TemporaryItems", ".DocumentRevisions-V100", ".VolumeIcon.icns",
    ".apdisk", ".localized", "Icon\r",
}

ABOUT = """🐱 집사 (Zipsa) — 윈도우 호환 ZIP 만들기

압축할 파일이나 폴더를 집사 아이콘 위로 끌어다 놓으세요.

• macOS 전용 파일(.DS_Store, ._*, __MACOSX 등) 제외
• 한글 파일명을 NFC로 정규화 (윈도우에서 자소 분리 없음)
• 결과는 원본과 같은 폴더에 '이름.zip'으로 저장"""


class ZipsaError(Exception):
    pass


def nfc(s):
    return unicodedata.normalize("NFC", s)


def is_junk(name):
    return name.startswith("._") or name in JUNK_NAMES


class Plan:
    """압축할 항목 목록과 통계"""

    def __init__(self, exclude=None):
        self.items = []            # (파일시스템 경로, ZIP 내부 이름, 폴더 여부)
        self.names = set()
        self.junk = Counter()
        self.skipped = []          # 심볼릭 링크, 소켓 등
        self.duplicates = []
        self.normalized = 0
        self.files = 0
        self.dirs = 0
        self.exclude = exclude     # 출력 파일 (dev, ino) — 자기 자신을 압축하지 않도록

    def claim(self, arcname):
        if arcname in self.names:
            self.duplicates.append(arcname)
            return False
        self.names.add(arcname)
        return True

    def collect(self, path, name, parent=""):
        if is_junk(name):
            self.junk["._*" if name.startswith("._") else name.replace("\r", "")] += 1
            return
        try:
            st = os.lstat(path)
        except OSError as e:
            raise ZipsaError("읽을 수 없습니다: %s (%s)" % (path, e.strerror))
        if self.exclude and (st.st_dev, st.st_ino) == self.exclude:
            return

        fixed = nfc(name)
        if fixed != name:
            self.normalized += 1
        arcname = parent + fixed

        if stat.S_ISDIR(st.st_mode):
            arcname += "/"
            if not self.claim(arcname):
                return
            self.items.append((path, arcname, True))
            self.dirs += 1
            try:
                children = os.listdir(path)
            except OSError as e:
                raise ZipsaError("폴더를 열 수 없습니다: %s (%s)" % (path, e.strerror))
            for child in sorted(children, key=nfc):
                self.collect(os.path.join(path, child), child, arcname)
        elif stat.S_ISREG(st.st_mode):
            if self.claim(arcname):
                self.items.append((path, arcname, False))
                self.files += 1
        else:
            self.skipped.append(arcname)


def unique_path(path):
    """Finder처럼 이미 있으면 '이름 2.zip', '이름 3.zip' ..."""
    if not os.path.lexists(path):
        return path
    root, ext = os.path.splitext(path)
    n = 2
    while os.path.lexists("%s %d%s" % (root, n, ext)):
        n += 1
    return "%s %d%s" % (root, n, ext)


def decide_output(inputs, output):
    if output:
        out = os.path.abspath(output)
        folder, base = os.path.split(out)
        out = os.path.join(folder, nfc(base))
        if os.path.isdir(out):
            raise ZipsaError("출력 경로가 폴더입니다: " + out)
        if not os.path.isdir(folder):
            raise ZipsaError("출력 폴더가 없습니다: " + folder)
        return out
    first = inputs[0]
    base = nfc(os.path.basename(first)) if len(inputs) == 1 else "Archive"
    return unique_path(os.path.join(os.path.dirname(first), base + ".zip"))


def write_zip(plan, output, level):
    folder, base = os.path.split(output)
    tmp = os.path.join(folder, ".%s.zipsa-%d.tmp" % (base, os.getpid()))
    if level == 0:
        method, kw = zipfile.ZIP_STORED, {}
    else:
        method, kw = zipfile.ZIP_DEFLATED, {"compresslevel": level}
    try:
        # strict_timestamps=False: 1980년 이전 날짜도 오류 없이 1980-01-01로 저장
        # ZIP64는 4GB 넘는 파일/아카이브에서 자동 적용
        with zipfile.ZipFile(tmp, "w", compression=method, allowZip64=True,
                             strict_timestamps=False, **kw) as zf:
            for path, arcname, _ in plan.items:
                # 비 ASCII 이름에는 zipfile이 UTF-8 플래그(bit 11)를 자동으로 설정
                zf.write(path, arcname)
        os.replace(tmp, output)   # 완성된 뒤에만 최종 이름으로 (중간 실패 시 찌꺼기 없음)
    except OSError as e:
        _remove(tmp)
        raise ZipsaError("압축 실패: %s (%s)" % (e.filename or output, e.strerror or e))
    except BaseException:
        _remove(tmp)
        raise


def _remove(path):
    try:
        os.unlink(path)
    except OSError:
        pass


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return "%d %s" % (n, unit) if unit == "B" else "%.1f %s" % (n, unit)
        n /= 1024.0
    return "%.1f TB" % n


def run(args):
    inputs = []
    for p in args.paths:
        if not p:
            raise ZipsaError("빈 경로가 전달되었습니다")
        ap = os.path.abspath(p)
        if not os.path.lexists(ap):
            raise ZipsaError("없는 경로입니다: " + p)
        if os.path.basename(ap) == "":
            raise ZipsaError("루트(/)는 압축할 수 없습니다")
        inputs.append(ap)

    output = decide_output(inputs, args.output)
    exclude = None
    if os.path.exists(output):
        st = os.stat(output)
        exclude = (st.st_dev, st.st_ino)

    plan = Plan(exclude)
    for ap in inputs:
        # 최상위 항목이 심볼릭 링크면 원본을 따라가되, 이름은 사용자가 고른 이름 유지
        plan.collect(os.path.realpath(ap), os.path.basename(ap))
    if not plan.items:
        raise ZipsaError("압축할 항목이 없습니다 (모두 macOS 전용 파일이었습니다)")

    write_zip(plan, output, args.level)
    return output, plan


def summary(output, plan):
    lines = ["🐾 집사가 정리했어요: %s (%s)" % (os.path.basename(output), human_size(os.path.getsize(output))),
             "   파일 %d개 · 폴더 %d개" % (plan.files, plan.dirs)]
    if plan.junk:
        lines.append("   제외한 macOS 파일: " +
                     ", ".join("%s %d개" % (k, v) for k, v in sorted(plan.junk.items())))
    if plan.normalized:
        lines.append("   NFC로 바꾼 이름: %d개" % plan.normalized)
    if plan.skipped:
        lines.append("   ⚠ 건너뜀(심볼릭 링크 등): " + ", ".join(plan.skipped[:5]) +
                     (" 외 %d개" % (len(plan.skipped) - 5) if len(plan.skipped) > 5 else ""))
    if plan.duplicates:
        lines.append("   ⚠ 정규화 후 이름이 겹쳐 제외: " + ", ".join(plan.duplicates[:5]))
    return "\n".join(lines)


def mac_notify(title, message, error=False):
    """macOS 알림(성공) 또는 경고창(실패). 빠른 동작/앱에서 실행할 때 사용"""
    if sys.platform != "darwin":
        return
    show = ("display alert (item 1 of argv) message (item 2 of argv) as critical" if error
            else "display notification (item 2 of argv) with title (item 1 of argv)")
    try:
        subprocess.run(["/usr/bin/osascript", "-e", "on run argv", "-e", show, "-e", "end run",
                        title, message],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    except Exception:
        pass


def mac_dialog(message, buttons):
    """버튼이 있는 대화상자. 누른 버튼 이름을 돌려준다 (실패하면 None)"""
    icon = os.path.join(os.path.dirname(os.path.abspath(__file__)), "applet.icns")
    show = "display dialog (item 1 of argv) with title (item 2 of argv) buttons btns default button (count of btns)"
    script = ["on run argv", "activate", "set btns to items 4 thru -1 of argv",
              'if item 3 of argv is "" then', "set r to " + show,
              "else", "set r to " + show + " with icon (POSIX file (item 3 of argv))", "end if",
              "return button returned of r", "end run"]
    cmd = ["/usr/bin/osascript"]
    for line in script:
        cmd += ["-e", line]
    cmd += [message, "집사", icon if os.path.isfile(icon) else ""] + list(buttons)
    try:
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           universal_newlines=True, timeout=600)
    except Exception:
        return None
    return r.stdout.strip() if r.returncode == 0 else None


# ── 업데이트 ────────────────────────────────────────────────────────────────

def parse_version(v):
    try:
        return tuple(int(p) for p in str(v).lstrip("vV").split("."))
    except ValueError:
        return None


def is_newer(latest):
    a, b = parse_version(latest), parse_version(VERSION)
    return a is not None and b is not None and a > b


def _open_url(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": "zipsa/" + VERSION})
    return urllib.request.urlopen(req, timeout=timeout)


def latest_version(timeout):
    """GitHub 최신 릴리스 버전('1.2.0'). 릴리스가 없으면 None, 네트워크 오류는 예외"""
    with _open_url(REPO_URL + "/releases/latest", timeout) as r:
        final = r.geturl()   # 릴리스가 있으면 .../releases/tag/v1.2.0 으로 리다이렉트된다
    m = re.search(r"/releases/tag/v(\d+(?:\.\d+)*)$", final)
    return m.group(1) if m else None


def update_hint():
    """하루 한 번 새 버전을 확인해서, 있으면 그 버전 문자열을 돌려준다 (실패는 조용히 무시)"""
    if os.environ.get("ZIPSA_NO_UPDATE_CHECK"):
        return None
    path = os.path.expanduser(CACHE_FILE)
    try:
        with open(path, encoding="utf-8") as f:
            cache = json.load(f)
    except (OSError, ValueError):
        cache = None
    if not isinstance(cache, dict):
        cache = {}
    checked = cache.get("checked")
    if not isinstance(checked, (int, float)) or not 0 <= time.time() - checked < CHECK_INTERVAL:
        try:
            cache["latest"] = latest_version(timeout=3)
        except Exception:
            pass   # 오프라인 등: 이전 결과를 쓰고 내일 다시 확인
        cache["checked"] = time.time()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cache, f)
        except OSError:
            pass
    latest = cache.get("latest")
    return latest if is_newer(latest) else None


def install_update():
    """최신 릴리스를 내려받아 그 안의 install.sh로 다시 설치한다. 결과 메시지를 돌려준다"""
    try:
        latest = latest_version(timeout=10)
    except Exception as e:
        raise ZipsaError("새 버전을 확인하지 못했습니다. 인터넷 연결을 확인하세요. (%s)" % e)
    if latest is None:
        raise ZipsaError("배포된 버전이 없습니다")
    if not is_newer(latest):
        return "이미 최신 버전입니다 (%s)" % VERSION

    tmp = tempfile.mkdtemp(prefix="zipsa-update-")
    try:
        archive = os.path.join(tmp, "src.tar.gz")
        with _open_url("%s/archive/refs/tags/v%s.tar.gz" % (REPO_URL, latest), 60) as r, \
                open(archive, "wb") as f:
            shutil.copyfileobj(r, f)
        src = os.path.join(tmp, "src")
        with tarfile.open(archive) as tf:
            for m in tf.getmembers():
                if m.name.startswith("/") or ".." in m.name.split("/") or not (m.isfile() or m.isdir()):
                    raise ZipsaError("내려받은 파일이 이상해서 설치하지 않았습니다: " + m.name)
            tf.extractall(src)
        tops = os.listdir(src)
        installer = os.path.join(src, tops[0], "install.sh") if len(tops) == 1 else ""
        if not os.path.isfile(installer):
            raise ZipsaError("내려받은 파일에 install.sh가 없습니다")
        r = subprocess.run(["/bin/bash", installer], env=dict(os.environ, ZIPSA_UPDATING="1"),
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        if r.returncode != 0:
            raise ZipsaError("설치하지 못했습니다:\n" + r.stdout.strip()[-800:])
    except (OSError, tarfile.TarError) as e:
        raise ZipsaError("업데이트하지 못했습니다: %s" % e)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return "%s → %s 업데이트를 마쳤어요" % (VERSION, latest)


def app_about():
    """집사.app을 더블클릭했을 때: 소개·버전을 보여 주고, 새 버전이 있으면 업데이트를 권한다"""
    try:
        latest = latest_version(timeout=5)
    except Exception:
        latest = None
    text = ABOUT + "\n\n버전 " + VERSION
    if not is_newer(latest):
        mac_dialog(text + (" (최신)" if latest else ""), ["확인"])
        return 0
    text += "\n\n새 버전(%s)이 나왔어요. 지금 업데이트할까요?" % latest
    if mac_dialog(text, ["나중에", "업데이트"]) != "업데이트":
        return 0
    try:
        msg = install_update()
    except ZipsaError as e:
        mac_notify("집사가 업데이트하지 못했어요", str(e), error=True)
        return 1
    mac_dialog("🐾 " + msg, ["확인"])
    return 0


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    ap = argparse.ArgumentParser(
        prog="zipsa",
        description="macOS 전용 파일을 빼고 한글 파일명을 NFC로 정규화해서 윈도우 호환 ZIP을 만듭니다.")
    ap.add_argument("paths", nargs="*", metavar="파일|폴더")
    ap.add_argument("-o", "--output", metavar="ZIP",
                    help="출력 파일 (기본: 항목 1개면 '이름.zip', 여러 개면 'Archive.zip', 같은 이름이 있으면 '이름 2.zip')")
    ap.add_argument("-l", "--level", type=int, default=6, choices=range(10), metavar="0-9",
                    help="압축 레벨 (기본 6, 0 = 무압축)")
    ap.add_argument("-q", "--quiet", action="store_true", help="결과 요약을 출력하지 않음")
    ap.add_argument("--notify", action="store_true", help="결과를 macOS 알림/경고창으로 표시")
    ap.add_argument("--update", action="store_true", help="최신 버전으로 업데이트")
    ap.add_argument("--app", action="store_true", help=argparse.SUPPRESS)   # 집사.app 더블클릭
    ap.add_argument("--version", action="version", version="zipsa " + VERSION)
    args = ap.parse_args(argv)

    if args.app:
        return app_about()
    if args.update:
        try:
            print(install_update())
        except ZipsaError as e:
            print("zipsa: " + str(e), file=sys.stderr)
            return 1
        return 0
    if not args.paths:
        ap.print_help()
        return 2

    try:
        output, plan = run(args)
    except KeyboardInterrupt:
        return 130
    except Exception as e:
        msg = str(e) if isinstance(e, ZipsaError) else "%s: %s" % (type(e).__name__, e)
        print("zipsa: " + msg, file=sys.stderr)
        if args.notify:
            mac_notify("집사가 압축하지 못했어요", msg, error=True)
        return 1

    text = summary(output, plan)
    if not args.quiet:
        try:
            print(text)
        except BrokenPipeError:
            pass
    newer = update_hint() if (args.notify or not args.quiet) else None
    if newer and not args.quiet:
        print("zipsa: 새 버전(%s)이 나왔어요. 'zipsa --update'로 업데이트하세요." % newer, file=sys.stderr)
    if args.notify:
        lines = [l.strip() for l in text.splitlines()]
        if newer:
            lines.append("새 버전(%s) — 집사.app을 열어 업데이트하세요" % newer)
        mac_notify("집사 🐾", "\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
