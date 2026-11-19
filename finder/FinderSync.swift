// 집사 Finder 확장: 우클릭 메뉴에 "집사에게 압축 맡기기"를 바로 보여 준다.
//
// Finder 확장은 샌드박스 안에서 돌아서, 고른 파일을 다른 앱에 직접 넘길 수 없다
// (LaunchServices가 permErr -54로 막음). 그래서 경로를 담은 링크
//   zipsa-finder://compress?p=<경로>&p=<경로>...&t=<확인값>
// 를 열고, 샌드박스 밖의 집사.app이 받아서 압축한다.
// 확인값(t)은 설치할 때 만들어 확장 안에 넣어 둔 것이라, 다른 앱이나 웹페이지는 모른다.
import Cocoa
import FinderSync

class FinderSync: FIFinderSync {
    override init() {
        super.init()
        // 메뉴를 보여 줄 위치: 디스크 전체
        FIFinderSyncController.default().directoryURLs = [URL(fileURLWithPath: "/")]
    }

    override func menu(for menuKind: FIMenuKind) -> NSMenu? {
        guard menuKind == .contextualMenuForItems else { return nil }
        let menu = NSMenu(title: "")
        let item = NSMenuItem(title: "집사에게 압축 맡기기", action: #selector(compress(_:)), keyEquivalent: "")
        // 집사 고양이 얼굴 (finder/menu_icon.png). 없으면 시스템 상자 아이콘
        if let url = Bundle.main.url(forResource: "menu_icon", withExtension: "png"),
           let icon = NSImage(contentsOf: url) {
            icon.size = NSSize(width: 16, height: 16)
            item.image = icon
        } else {
            item.image = NSImage(systemSymbolName: "archivebox", accessibilityDescription: nil)
        }
        menu.addItem(item)
        return menu
    }

    @objc func compress(_ sender: AnyObject?) {
        guard let urls = FIFinderSyncController.default().selectedItemURLs(), !urls.isEmpty else { return }
        var items = urls.map { URLQueryItem(name: "p", value: $0.path) }
        if let tokenURL = Bundle.main.url(forResource: "token", withExtension: nil),
           let token = try? String(contentsOf: tokenURL, encoding: .utf8) {
            items.append(URLQueryItem(name: "t", value: token.trimmingCharacters(in: .whitespacesAndNewlines)))
        }
        var c = URLComponents()
        c.scheme = "zipsa-finder"
        c.host = "compress"
        c.queryItems = items
        // URLComponents는 '+'를 그대로 두는데, 받는 쪽은 '+'를 공백으로 읽으므로 직접 인코딩
        c.percentEncodedQuery = c.percentEncodedQuery?.replacingOccurrences(of: "+", with: "%2B")
        if let link = c.url {
            NSWorkspace.shared.open(link)
        }
    }
}
