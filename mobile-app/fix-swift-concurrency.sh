#!/bin/bash

echo "Fixing Swift concurrency issues for Xcode 16.4..."

# Find the Pods.xcodeproj file
PBXPROJ="ios/Pods/Pods.xcodeproj/project.pbxproj"

if [ ! -f "$PBXPROJ" ]; then
    echo "Error: $PBXPROJ not found. Run 'pod install' first."
    exit 1
fi

# Backup the original file
cp "$PBXPROJ" "$PBXPROJ.backup"

# Use perl to add Swift concurrency settings to all build configurations
perl -i -pe 's/(SWIFT_VERSION = [^;]+;)/$1\n\t\t\t\tSWIFT_STRICT_CONCURRENCY = minimal;\n\t\t\t\tSWIFT_UPCOMING_FEATURE_CONCURRENCY_CHECKING = NO;/g unless /SWIFT_STRICT_CONCURRENCY/' "$PBXPROJ"

echo "✓ Modified Xcode project to disable strict Swift concurrency checking"

# Also modify the main app project
APP_PBXPROJ="ios/mobileapp.xcodeproj/project.pbxproj"

if [ -f "$APP_PBXPROJ" ]; then
    cp "$APP_PBXPROJ" "$APP_PBXPROJ.backup"
    perl -i -pe 's/(SWIFT_VERSION = [^;]+;)/$1\n\t\t\t\tSWIFT_STRICT_CONCURRENCY = minimal;\n\t\t\t\tSWIFT_UPCOMING_FEATURE_CONCURRENCY_CHECKING = NO;/g unless /SWIFT_STRICT_CONCURRENCY/' "$APP_PBXPROJ"
    echo "✓ Modified app project to disable strict Swift concurrency checking"
fi

echo ""
echo "Done! Now try building again with: npx expo run:ios"
