#!/bin/bash

# Patch Expo modules for Swift 6 concurrency compatibility

echo "Patching Expo modules for Xcode 16.4 Swift concurrency..."

# Add @preconcurrency to problematic imports
find node_modules/expo-modules-core/ios -name "*.swift" -type f -exec sed -i '' 's/^import UIKit$/@preconcurrency import UIKit/g' {} \;
find node_modules/expo-modules-core/ios -name "*.swift" -type f -exec sed -i '' 's/^import SwiftUI$/@preconcurrency import SwiftUI/g' {} \;

# Add nonisolated(unsafe) to problematic stored properties
sed -i '' 's/let completionHandler: (URLSession.AuthChallengeDisposition, URLCredential?) -> Void/nonisolated(unsafe) let completionHandler: (URLSession.AuthChallengeDisposition, URLCredential?) -> Void/g' node_modules/expo-modules-core/ios/DevTools/URLAuthenticationChallengeForwardSender.swift

sed -i '' 's/private var delegateMap: \[AnyHashable: URLSessionDataDelegate\] = \[:\]/nonisolated(unsafe) private var delegateMap: [AnyHashable: URLSessionDataDelegate] = [:]/g' node_modules/expo-modules-core/ios/DevTools/URLSessionSessionDelegateProxy.swift

echo "Patching complete!"
