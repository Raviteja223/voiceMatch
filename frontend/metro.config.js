const { getDefaultConfig } = require("expo/metro-config");

const config = getDefaultConfig(__dirname);

// Keep Metro config minimal and cross-platform to avoid Windows ESM loader issues.
config.maxWorkers = 2;

module.exports = config;
