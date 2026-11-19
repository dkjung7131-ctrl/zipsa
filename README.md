<img src="zipsa_icon.png" width="160" alt="집사 아이콘">

# 집사 (Zipsa) 🐱

윈도우에서 깨지지 않는 ZIP을 만드는 macOS용 압축 도구입니다.
맥이 흘리고 다니는 털(`.DS_Store`, `._*`)을 치우고, 흐트러진 한글 자모를 단정하게 정리해 드립니다.

- **macOS 전용 파일 제외**: `.DS_Store`, `._*`, `__MACOSX`, `.Spotlight-V100`, `.Trashes`, `Icon\r` 등. 확장 속성·리소스 포크도 넣지 않습니다.
- **한글 파일명 NFC 정규화**: ZIP 안의 모든 경로를 NFC로 바꾸고 UTF-8 플래그를 기록해서, 윈도우 탐색기·반디집·7-Zip 어디서 풀어도 자소 분리나 깨짐이 없습니다. 만들어지는 ZIP 파일 이름 자체도 NFC입니다.
- 원본 파일은 건드리지 않습니다. 4GB 넘는 파일도 됩니다(ZIP64).

## 설치

```bash
git clone https://github.com/dkjung7131-ctrl/zipsa.git
cd zipsa
bash install.sh
```

git이 없으면 이 페이지의 **Code → Download ZIP**으로 받아서 푼 뒤 `bash install.sh`를 실행하세요.

- 터미널 명령어 `~/.local/bin/zipsa`와 앱 `~/Applications/집사.app`이 설치됩니다.
- macOS 기본 `python3`(Xcode Command Line Tools)를 씁니다. 없으면 설치 창이 뜹니다.

## 사용법

**앱**: 파일이나 폴더를 `집사.app` 아이콘 위로 끌어다 놓으면 같은 폴더에 `이름.zip`이 생깁니다. Dock에 올려두면 편합니다.

**터미널**:

```bash
zipsa 폴더                  # → 폴더.zip
zipsa a.pdf b.xlsx 폴더     # 여러 개 → Archive.zip
zipsa -o ~/Desktop/전달.zip 폴더
zipsa -l 9 폴더             # 압축 레벨 0~9 (기본 6)
```

같은 이름의 ZIP이 이미 있으면 Finder처럼 `이름 2.zip`으로 만듭니다(`-o`로 지정하면 덮어씀).

## Finder 우클릭 메뉴에 넣기 (빠른 동작)

1. **Automator** 실행 → 새로운 문서 → **빠른 동작**
2. 상단에서 받는 항목을 **파일 또는 폴더**, 위치를 **Finder**로 설정
3. 왼쪽 목록에서 **셸 스크립트 실행**을 오른쪽으로 끌어다 놓기
4. 셸은 `/bin/zsh`, 입력 전달은 **인수로** 선택하고 내용을 아래로 교체

   ```bash
   "$HOME/.local/bin/zipsa" --notify "$@"
   ```

5. `⌘S`로 저장, 이름은 `집사에게 압축 맡기기`

이제 Finder에서 항목을 선택하고 우클릭 → **빠른 동작 → 집사에게 압축 맡기기**. 완료되면 알림이 뜹니다.

## 참고

- 심볼릭 링크는 윈도우에서 제대로 풀리지 않아 건너뛰고, 결과 요약에 표시합니다.
- 1980년 이전 수정 날짜는 ZIP 형식 한계로 1980-01-01로 저장됩니다.
- 처음 실행할 때 데스크탑·문서 폴더 접근 권한을 물어보면 허용하세요.
- 아이콘 원본은 `icon.svg`입니다. 수정한 뒤 `install.sh`를 다시 실행하려면 `zipsa.icns`도 새로 만들어야 합니다.

## 라이선스

MIT
