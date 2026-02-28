// Test file to verify environment variables are loading
import { AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY } from "@env";

export function testEnvVars() {
  console.log("=== Testing Environment Variables ===");
  console.log("AWS_REGION:", AWS_REGION);
  console.log(
    "AWS_ACCESS_KEY_ID:",
    AWS_ACCESS_KEY_ID ? "✅ Loaded" : "❌ Missing",
  );
  console.log(
    "AWS_SECRET_ACCESS_KEY:",
    AWS_SECRET_ACCESS_KEY ? "✅ Loaded" : "❌ Missing",
  );
  console.log("=====================================");

  if (!AWS_REGION || !AWS_ACCESS_KEY_ID || !AWS_SECRET_ACCESS_KEY) {
    throw new Error(
      "Environment variables not loaded! Make sure to restart Metro bundler with: npx expo start -c",
    );
  }
}
