#!/bin/bash

set -e

echo "Patching expo-modules-core for Xcode 16.4 Swift concurrency..."

EXPO_CORE="node_modules/expo-modules-core/ios"

if [ ! -d "$EXPO_CORE" ]; then
    echo "Error: expo-modules-core not found"
    exit 1
fi

# Backup
echo "Creating backups..."
cp -r "$EXPO_CORE" "${EXPO_CORE}.backup" 2>/dev/null || true

# Fix 1: ExpoReactDelegate.swift - wrap UIViewController init in MainActor
echo "Patching ExpoReactDelegate.swift..."
sed -i '' 's/.first(where: { _ in true }) ?? UIViewController()/.first(where: { _ in true }) ?? MainActor.assumeIsolated { UIViewController() }/g' \
    "$EXPO_CORE/ReactDelegates/ExpoReactDelegate.swift"

# Fix 2: PersistentFileLog.swift - add @Sendable
echo "Patching PersistentFileLog.swift..."
sed -i '' 's/typealias PersistentFileLogFilter = (PersistentFileLog.Entry) -> Bool/typealias PersistentFileLogFilter = @Sendable (PersistentFileLog.Entry) -> Bool/g' \
    "$EXPO_CORE/Core/Logging/PersistentFileLog.swift"

# Fix 3: SwiftUIHostingView.swift - remove @MainActor from protocol conformance
echo "Patching SwiftUIHostingView.swift..."
sed -i '' 's/@MainActor AnyExpoSwiftUIHostingView/AnyExpoSwiftUIHostingView/g' \
    "$EXPO_CORE/Core/Views/SwiftUI/SwiftUIHostingView.swift"

# Fix 4: Add nonisolated to methods that need it
sed -i '' 's/public override func updateProps/nonisolated public override func updateProps/g' \
    "$EXPO_CORE/Core/Views/SwiftUI/SwiftUIHostingView.swift"

sed -i '' 's/public func getContentView/nonisolated public func getContentView/g' \
    "$EXPO_CORE/Core/Views/SwiftUI/SwiftUIHostingView.swift"

sed -i '' 's/public func getProps/nonisolated public func getProps/g' \
    "$EXPO_CORE/Core/Views/SwiftUI/SwiftUIHostingView.swift"

# Fix 5: SwiftUIViewFrameObserver.swift - add @MainActor to closure
echo "Patching SwiftUIViewFrameObserver.swift..."
sed -i '' 's/callback(CGRect(origin: view.frame.origin, size: newValue.size))/MainActor.assumeIsolated { callback(CGRect(origin: view.frame.origin, size: newValue.size)) }/g' \
    "$EXPO_CORE/Core/Views/SwiftUI/SwiftUIViewFrameObserver.swift"

# Fix 6: SwiftUIVirtualView.swift - add nonisolated
echo "Patching SwiftUIVirtualView.swift..."
sed -i '' 's/override func updateProps/nonisolated override func updateProps/g' \
    "$EXPO_CORE/Core/Views/SwiftUI/SwiftUIVirtualView.swift"

sed -i '' 's/override func mountChildComponentView/nonisolated override func mountChildComponentView/g' \
    "$EXPO_CORE/Core/Views/SwiftUI/SwiftUIVirtualView.swift"

sed -i '' 's/override func unmountChildComponentView/nonisolated override func unmountChildComponentView/g' \
    "$EXPO_CORE/Core/Views/SwiftUI/SwiftUIVirtualView.swift"

# Fix 7: URLAuthenticationChallengeForwardSender.swift
echo "Patching URLAuthenticationChallengeForwardSender.swift..."
sed -i '' 's/let completionHandler: (URLSession.AuthChallengeDisposition, URLCredential?) -> Void/nonisolated(unsafe) let completionHandler: (URLSession.AuthChallengeDisposition, URLCredential?) -> Void/g' \
    "$EXPO_CORE/DevTools/URLAuthenticationChallengeForwardSender.swift"

# Fix 8: URLSessionSessionDelegateProxy.swift
echo "Patching URLSessionSessionDelegateProxy.swift..."
sed -i '' 's/private var delegateMap: \[AnyHashable: URLSessionDataDelegate\] = \[:\]/nonisolated(unsafe) private var delegateMap: [AnyHashable: URLSessionDataDelegate] = [:]/g' \
    "$EXPO_CORE/DevTools/URLSessionSessionDelegateProxy.swift"

# Fix 9: ViewDefinition.swift - remove @MainActor
echo "Patching ViewDefinition.swift..."
sed -i '' 's/@MainActor AnyArgument/AnyArgument/g' \
    "$EXPO_CORE/Core/Views/ViewDefinition.swift"

echo ""
echo "✓ Patching complete!"
echo ""
echo "Now run:"
echo "  cd ios && rm -rf Pods Podfile.lock && pod install && cd .."
echo "  npx expo run:ios"
