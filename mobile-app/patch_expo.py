#!/usr/bin/env python3
"""
Patch expo-modules-core for Xcode 16.4 Swift 6 concurrency compatibility
"""

import os
import re
import shutil

EXPO_CORE = "node_modules/expo-modules-core/ios"

def backup_and_restore():
    backup = f"{EXPO_CORE}.backup"
    if os.path.exists(backup):
        print("Restoring from backup...")
        if os.path.exists(EXPO_CORE):
            shutil.rmtree(EXPO_CORE)
        shutil.copytree(backup, EXPO_CORE)
    else:
        print("Creating backup...")
        shutil.copytree(EXPO_CORE, backup)

def patch_file(filepath, patches):
    """Apply patches to a file"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    original = content
    for pattern, replacement in patches:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
    
    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"✓ Patched {os.path.basename(filepath)}")
        return True
    return False

# Patch definitions
patches = {
    f"{EXPO_CORE}/ReactDelegates/ExpoReactDelegate.swift": [
        (r'\.first\(where: \{ _ in true \}\) \?\? UIViewController\(\)',
         '.first(where: { _ in true }) ?? MainActor.assumeIsolated { UIViewController() }'),
    ],
    
    f"{EXPO_CORE}/Core/Logging/PersistentFileLog.swift": [
        (r'typealias PersistentFileLogFilter = \(PersistentFileLog\.Entry\) -> Bool',
         'typealias PersistentFileLogFilter = @Sendable (PersistentFileLog.Entry) -> Bool'),
    ],
    
    f"{EXPO_CORE}/Core/Views/SwiftUI/SwiftUIHostingView.swift": [
        (r'@MainActor AnyExpoSwiftUIHostingView', 'AnyExpoSwiftUIHostingView'),
        (r'public override func updateProps\(_ rawProps: \[String: Any\]\) \{',
         'nonisolated public override func updateProps(_ rawProps: [String: Any]) {'),
        (r'(nonisolated public override func updateProps.*?\{)\s*(guard let appContext)',
         r'\1\n      MainActor.assumeIsolated {\n      \2'),
        (r'(hasSafeAreaBeenConfigured = true)\s*(\})\s*(\})',
         r'\1\n      }\n    \3'),
        (r'public func getContentView\(\) -> any ExpoSwiftUI\.View \{',
         'nonisolated public func getContentView() -> any ExpoSwiftUI.View {'),
        (r'(nonisolated public func getContentView.*?\{)\s*return contentView',
         r'\1\n      return MainActor.assumeIsolated { contentView }'),
        (r'public func getProps\(\) -> ExpoSwiftUI\.ViewProps \{',
         'nonisolated public func getProps() -> ExpoSwiftUI.ViewProps {'),
        (r'(nonisolated public func getProps.*?\{)\s*return props',
         r'\1\n      return MainActor.assumeIsolated { props }'),
    ],
    
    f"{EXPO_CORE}/Core/Views/SwiftUI/SwiftUIViewFrameObserver.swift": [
        (r'callback\(CGRect\(origin: view\.frame\.origin, size: newValue\.size\)\)',
         'MainActor.assumeIsolated { callback(CGRect(origin: view.frame.origin, size: newValue.size)) }'),
    ],
    
    f"{EXPO_CORE}/Core/Views/SwiftUI/SwiftUIVirtualView.swift": [
        (r'override func updateProps\(_ rawProps: \[String: Any\]\) \{',
         'nonisolated override func updateProps(_ rawProps: [String: Any]) {'),
        (r'(nonisolated override func updateProps.*?\{)\s*(guard let appContext)',
         r'\1\n      MainActor.assumeIsolated {\n      \2'),
        (r'(try props\.updateRawProps.*?\n.*?log\.error.*?\n.*?\})\s*(\})',
         r'\1\n      }\n    \2'),
        (r'override func mountChildComponentView\(_ childComponentView: UIView, index: Int\) \{',
         'nonisolated override func mountChildComponentView(_ childComponentView: UIView, index: Int) {'),
        (r'(nonisolated override func mountChildComponentView.*?\{)\s*(var children)',
         r'\1\n      MainActor.assumeIsolated {\n      \2'),
        (r'(props\.objectWillChange\.send\(\))\s*(\}\s*\/\/\/)',
         r'\1\n      }\n    \2'),
        (r'override func unmountChildComponentView\(_ childComponentView: UIView, index: Int\) \{',
         'nonisolated override func unmountChildComponentView(_ childComponentView: UIView, index: Int) {'),
        (r'(nonisolated override func unmountChildComponentView.*?\{)\s*(\/\/ Make sure)',
         r'\1\n      MainActor.assumeIsolated {\n      \2'),
        (r'(props\.objectWillChange\.send\(\)\s*\}\s*\})\s*(\})',
         r'\1\n      }\n    \2'),
    ],
    
    f"{EXPO_CORE}/DevTools/URLAuthenticationChallengeForwardSender.swift": [
        (r'^  let completionHandler: \(URLSession\.AuthChallengeDisposition, URLCredential\?\) -> Void$',
         '  nonisolated(unsafe) let completionHandler: (URLSession.AuthChallengeDisposition, URLCredential?) -> Void'),
    ],
    
    f"{EXPO_CORE}/DevTools/URLSessionSessionDelegateProxy.swift": [
        (r'^  private var delegateMap: \[AnyHashable: URLSessionDataDelegate\] = \[:\]$',
         '  nonisolated(unsafe) private var delegateMap: [AnyHashable: URLSessionDataDelegate] = [:]'),
    ],
    
    f"{EXPO_CORE}/Core/Views/ViewDefinition.swift": [
        (r'@MainActor AnyArgument', 'AnyArgument'),
    ],
}

if __name__ == "__main__":
    if not os.path.exists(EXPO_CORE):
        print(f"Error: {EXPO_CORE} not found")
        exit(1)
    
    backup_and_restore()
    
    print("\nApplying patches...")
    for filepath, file_patches in patches.items():
        if os.path.exists(filepath):
            patch_file(filepath, file_patches)
        else:
            print(f"⚠ File not found: {filepath}")
    
    print("\n✓ All patches applied!")
    print("\nNext steps:")
    print("  cd ios && rm -rf Pods Podfile.lock && pod install && cd ..")
    print("  npx expo run:ios")
