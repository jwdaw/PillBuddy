#!/usr/bin/env ruby

# Script to disable Swift concurrency checking in Xcode project

pbxproj_path = 'ios/Pods/Pods.xcodeproj/project.pbxproj'

unless File.exist?(pbxproj_path)
  puts "Error: #{pbxproj_path} not found"
  exit 1
end

content = File.read(pbxproj_path)
modified = false

# Add SWIFT_STRICT_CONCURRENCY = minimal to all build configurations
if content.gsub!(/(\s+buildSettings = \{[^}]*?)(SWIFT_VERSION = [^;]+;)/, '\1\2' + "\n\t\t\t\tSWIFT_STRICT_CONCURRENCY = minimal;")
  modified = true
  puts "Added SWIFT_STRICT_CONCURRENCY = minimal"
end

# Also disable upcoming concurrency features
if content.gsub!(/(\s+buildSettings = \{[^}]*?)(SWIFT_VERSION = [^;]+;)/, '\1\2' + "\n\t\t\t\tSWIFT_UPCOMING_FEATURE_CONCURRENCY_CHECKING = NO;")
  modified = true
  puts "Added SWIFT_UPCOMING_FEATURE_CONCURRENCY_CHECKING = NO"
end

if modified
  File.write(pbxproj_path, content)
  puts "Successfully modified #{pbxproj_path}"
else
  puts "No modifications needed or pattern not found"
end
