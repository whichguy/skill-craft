import AppKit
import WebKit

// A line-oriented driver for a real WebKit view. The protocol carries no app routes or selectors.
final class Browser: NSObject, WKNavigationDelegate {
    let view: WKWebView
    let window: NSWindow
    var navigation: ((Any?, Error?) -> Void)?

    init(_ script: String, store: WKWebsiteDataStore) {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = store
        configuration.userContentController.addUserScript(
            WKUserScript(source: script, injectionTime: .atDocumentStart, forMainFrameOnly: true)
        )
        view = WKWebView(frame: NSRect(x: 0, y: 0, width: 1440, height: 900), configuration: configuration)
        window = NSWindow(contentRect: view.frame, styleMask: [.titled, .resizable], backing: .buffered, defer: false)
        super.init()
        view.navigationDelegate = self
        window.isReleasedWhenClosed = false
        window.contentView = view
        window.orderFrontRegardless()
        window.makeKey()
        window.makeFirstResponder(view)
    }

    func webView(_ view: WKWebView, didFinish navigation: WKNavigation!) {
        let completion = self.navigation
        self.navigation = nil
        completion?(true, nil)
    }

    func webView(_ view: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        let completion = self.navigation
        self.navigation = nil
        completion?(nil, error)
    }

    func webView(_ view: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        webView(view, didFailProvisionalNavigation: navigation, withError: error)
    }

    func key(_ key: String) {
        let tab = key.hasSuffix("Tab")
        let space = key == "Space"
        let characters = tab ? "\t" : (space ? " " : "\r")
        let code: UInt16 = tab ? 48 : (space ? 49 : 36)
        var modifiers: NSEvent.ModifierFlags = []
        if key.contains("Shift+") { modifiers.insert(.shift) }
        if key.contains("Option+") { modifiers.insert(.option) }
        window.makeKey()
        for type in [NSEvent.EventType.keyDown, .keyUp] {
            if let event = NSEvent.keyEvent(
                with: type, location: .zero, modifierFlags: modifiers,
                timestamp: ProcessInfo.processInfo.systemUptime, windowNumber: window.windowNumber,
                context: nil, characters: characters, charactersIgnoringModifiers: characters,
                isARepeat: false, keyCode: code
            ) {
                window.sendEvent(event)
            }
        }
    }
}

let app = NSApplication.shared
app.setActivationPolicy(.accessory)
let store = WKWebsiteDataStore.nonPersistent()
var browser: Browser?
var initialization: String = ""

func output(_ id: Int, _ value: Any?, _ error: Error? = nil) {
    let result: [String: Any] = ["id": id, "value": value ?? NSNull(), "error": error?.localizedDescription as Any? ?? NSNull()]
    if let data = try? JSONSerialization.data(withJSONObject: result),
       let line = String(data: data, encoding: .utf8) {
        print(line)
        fflush(stdout)
    }
}

DispatchQueue.global().async {
    while let line = readLine() {
        guard let data = line.data(using: .utf8),
              let command = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any],
              let request = command["id"] as? Int,
              let op = command["op"] as? String else { continue }
        DispatchQueue.main.async {
            if op == "open" {
                initialization = command["script"] as? String ?? ""
                browser = Browser(initialization, store: store)
            } else if op == "return" {
                browser = Browser(initialization, store: store)
            }
            guard let current = browser else { output(request, false); return }
            switch op {
            case "open", "navigate", "return":
                guard let url = URL(string: command["url"] as? String ?? "") else { output(request, false); return }
                current.navigation = { value, error in output(request, value, error) }
                current.view.load(URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData))
            case "reload":
                current.navigation = { value, error in output(request, value, error) }
                current.view.reloadFromOrigin()
            case "eval":
                let source = command["source"] as? String ?? ""
                current.view.callAsyncJavaScript(source, arguments: [:], in: nil, in: .page) { result in
                    switch result {
                    case .success(let value): output(request, value)
                    case .failure(let error): output(request, nil, error)
                    }
                }
            case "size":
                let width = command["width"] as? Double ?? 1440
                let height = command["height"] as? Double ?? 900
                current.window.setContentSize(NSSize(width: width, height: height))
                output(request, true)
            case "key":
                current.key(command["key"] as? String ?? "")
                output(request, true)
            case "close":
                current.window.close()
                browser = nil
                output(request, true)
            default: output(request, false)
            }
        }
    }
    DispatchQueue.main.async { app.stop(nil); exit(0) }
}
app.run()
