#!/bin/bash

echo "🧹 Clearing Metro bundler cache..."
npx expo start -c

echo ""
echo "✅ Metro bundler started with cleared cache"
echo "📱 Scan the QR code with Expo Go app"
echo ""
echo "🔍 Check the console for these messages:"
echo "   - DynamoDB Service initializing..."
echo "   - AWS_REGION: us-east-1"
echo "   - AWS_ACCESS_KEY_ID: ✅ Loaded"
echo "   - AWS_SECRET_ACCESS_KEY: ✅ Loaded"
