#!/bin/bash

set -e

echo "Patching expo-modules-core for Xcode 16.4 Swift concurrency (v2)..."

EXPO_CORE="node_modules/expo-modules-core/ios"

if [ ! -d "$EXPO_CORE" ]; then
    echo "Error: expo-modules-core not found"
    exit 1
fi

# Restore from backup if it exists
if [ -d "${EXPO_CORE}.backup" ]; then
    echo "Restoring from backup..."
    rm -rf "$EXPO_CORE"
    cp -r "${EXPO_CORE}.backup" "$EXPO_CORE"
fi

# Fix 1: ExpoReactDelegate.swift - wrap UIViewController init in MainActor
echo "Patching ExpoReactDelegate.swift..."
cat > /tmp/expo_patch_1.swift << 'EOF'
  public func createRootViewController() -> UIViewController? {
    return self.handlers.lazy
      .compactMap { $0.createRootViewController() }
      .first(where: { _ in true }) ?? MainActor.assumeIsolated { UIViewController() }
  }
EOF
perl -i -p0e 's/public func createRootViewController\(\) -> UIViewController\? \{.*?\n.*?\n.*?\n.*?\}/`cat \/tmp\/expo_patch_1.swift`/se' \
    "$EXPO_CORE/ReactDelegates/ExpoReactDelegate.swift"

# Fix 2: PersistentFileLog.swift - add @Sendable
echo "Patching PersistentFileLog.swift..."
sed -i '' 's/typealias PersistentFileLogFilter = (PersistentFileLog.Entry) -> Bool/typealias PersistentFileLogFilter = @Sendable (PersistentFileLog.Entry) -> Bool/g' \
    "$EXPO_CORE/Core/Logging/PersistentFileLog.swift"

# Fix 3: SwiftUIHostingView.swift - remove @MainActor from protocol conformance
echo "Patching SwiftUIHostingView.swift..."
sed -i '' 's/@MainActor AnyExpoSwiftUIHostingView/AnyExpoSwiftUIHostingView/g' \
    "$EXPO_CORE/Core/Views/SwiftUI/SwiftUIHostingView.swift"

# Fix 4: Wrap updateProps body in MainActor.assumeIsolated
sed -i '' '/public override func updateProps(_ rawProps: \[String: Any\]) {/,/^    }$/ {
    s/public override func updateProps/nonisolated public override func updateProps/
    s/guard let appContext else {/MainActor.assumeIsolated {\
      guard let appContext else {/
    /^    }$/i\
      }\
    
}' "$EXPO_CORE/Core/Views/SwiftUI/SwiftUIHostingView.swift"

# Fix 5: getContentView - wrap in MainActor.assumeIsolated
sed -i '' 's/public func getContentView() -> any ExpoSwiftUI.View {$/nonisolated public func getContentView() -> any ExpoSwiftUI.View {/g' \
    "$EXPO_CORE/Core/Views/SwiftUI/SwiftUIHostingView.swift"
sed -i '' '/nonisolated public func getContentView/,/^    }$/ {
    s/return contentView/return MainActor.assumeIsolated { contentView }/
}' "$EXPO_CORE/Core/Views/SwiftUI/SwiftUIHostingView.swift"

# Fix 6: getProps - wrap in MainActor.assumeIsolated
sed -i '' 's/public func getProps() -> ExpoSwiftUI.ViewProps {$/nonisolated public func getProps() -> ExpoSwiftUI.ViewProps {/g' \
    "$EXPO_CORE/Core/Views/SwiftUI/SwiftUIHostingView.swift"
sed -i '' '/nonisolated public func getProps/,/^    }$/ {
    s/return props/return MainActor.assumeIsolated { props }/
}' "$EXPO_CORE/Core/Views/SwiftUI/SwiftUIHostingView.swift"

# Fix 7: SwiftUIViewFrameObserver.swift - add @MainActor to closure
echo "Patching SwiftUIViewFrameObserver.swift..."
sed -i '' 's/callback(CGRect(origin: view.frame.origin, size: newValue.size))/MainActor.assumeIsolated { callback(CGRect(origin: view.frame.origin, size: newValue.size)) }/g' \
    "$EXPO_CORE/Core/Views/SwiftUI/SwiftUIViewFrameObserver.swift"

# Fix 8: SwiftUIVirtualView.swift - wrap all methods in MainActor.assumeIsolated
echo "Patching SwiftUIVirtualView.swift..."

# updateProps
sed -i '' '/override func updateProps(_ rawProps: \[String: Any\]) {/,/^    }$/ {
    s/override func updateProps/nonisolated override func updateProps/
    s/guard let appContext else {/MainActor.assumeIsolated {\
      guard let appContext else {/
    /^    }$/i\
      }\
    
}' "$EXPO_CORE/Core/Views/SwiftUI/SwiftUIVirtualView.swift"

# mountChildComponentView
sed -i '' '/override func mountChildComponentView(_ childComponentView: UIView, index: Int) {/,/^    }$/ {
    s/override func mountChildComponentView/nonisolated override func mountChildComponentView/
    s/var children = props.children/MainActor.assumeIsolated {\
      var children = props.children/
    /props.objectWillChange.send()/a\
      }\
    
}' "$EXPO_CORE/Core/Views/SwiftUI/SwiftUIVirtualView.swift"

# unmountChildComponentView
sed -i '' '/override func unmountChildComponentView(_ childComponentView: UIView, index: Int) {/,/^    }$/ {
    s/override func unmountChildComponentView/nonisolated override func unmountChildComponentView/
    s/childComponentView.removeFromSuperview()/MainActor.assumeIsolated {\
      childComponentView.removeFromSuperview()/
    /^    }$/i\
      }\
    
}' "$EXPO_CORE/Core/Views/SwiftUI/SwiftUIVirtualView.swift"

# Fix 9: URLAuthenticationChallengeForwardSender.swift
echo "Patching URLAuthenticationChallengeForwardSender.swift..."
sed -i '' 's/^  let completionHandler: (URLSession.AuthChallengeDisposition, URLCredential?) -> Void$/  nonisolated(unsafe) let completionHandler: (URLSession.AuthChallengeDisposition, URLCredential?) -> Void/g' \
    "$EXPO_CORE/DevTools/URLAuthenticationChallengeForwardSender.swift"

# Fix 10: URLSessionSessionDelegateProxy.swift
echo "Patching URLSessionSessionDelegateProxy.swift..."
sed -i '' 's/^  private var delegateMap: \[AnyHashable: URLSessionDataDelegate\] = \[:\]$/  nonisolated(unsafe) private var delegateMap: [AnyHashable: URLSessionDataDelegate] = [:]/g' \
    "$EXPO_CORE/DevTools/URLSessionSessionDelegateProxy.swift"

# Fix 11: ViewDefinition.swift - remove @MainActor
echo "Patching ViewDefinition.swift..."
sed -i '' 's/@MainActor AnyArgument/AnyArgument/g' \
    "$EXPO_CORE/Core/Views/ViewDefinition.swift"

echo ""
echo "✓ Patching complete!"
echo ""
echo "Now run:"
echo "  cd ios && rm -rf Pods Podfile.lock && pod install && cd .."
echo "  npx expo run:ios"
