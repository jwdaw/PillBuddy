const { getDefaultConfig } = require("expo/metro-config");

const config = getDefaultConfig(__dirname);

// Add polyfills for Node.js modules required by AWS SDK
config.resolver.extraNodeModules = {
  ...config.resolver.extraNodeModules,
  crypto: require.resolve("expo-crypto"),
  stream: require.resolve("readable-stream"),
  buffer: require.resolve("buffer/"),
};

module.exports = config;
