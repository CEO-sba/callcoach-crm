#!/bin/bash
# CallCoach iOS Setup Script
# Run this from: ~/Desktop/callcoach-crm/mobile/ios/
set -e

echo "=== CallCoach iOS Setup ==="
echo ""

# Step 1: Check prerequisites
echo "Checking prerequisites..."

if ! command -v xcodebuild &> /dev/null; then
    echo "ERROR: Xcode is not installed. Install from App Store first."
    exit 1
fi

if ! command -v pod &> /dev/null; then
    echo "Installing CocoaPods..."
    sudo gem install cocoapods
fi

if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is not installed."
    exit 1
fi

echo "All prerequisites met."
echo ""

# Step 2: Generate Xcode project using react-native init template
# We create a temp project and copy the .xcodeproj from it
echo "Generating Xcode project..."

TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

# Create a minimal Xcode project using xcodegen or manual approach
# Since we need a proper .xcodeproj, we use a ruby script with xcodeproj gem

# First check if xcodeproj gem is available
if ! gem list xcodeproj -i &> /dev/null; then
    echo "Installing xcodeproj gem..."
    sudo gem install xcodeproj
fi

# Go back to ios directory
cd "$(dirname "$0")"
IOS_DIR="$(pwd)"

ruby << 'RUBY_SCRIPT'
require 'xcodeproj'

ios_dir = ENV['IOS_DIR'] || Dir.pwd
project_path = File.join(ios_dir, 'CallCoach.xcodeproj')

# Create project
project = Xcodeproj::Project.new(project_path)

# Add main target
target = project.new_target(:application, 'CallCoach', :ios, '13.4')

# Set build settings
target.build_configurations.each do |config|
  config.build_settings['PRODUCT_BUNDLE_IDENTIFIER'] = 'com.callcoachmobile'
  config.build_settings['INFOPLIST_FILE'] = 'CallCoach/Info.plist'
  config.build_settings['ASSETCATALOG_COMPILER_APPICON_NAME'] = 'AppIcon'
  config.build_settings['CODE_SIGN_STYLE'] = 'Automatic'
  config.build_settings['CURRENT_PROJECT_VERSION'] = '1'
  config.build_settings['MARKETING_VERSION'] = '1.0.0'
  config.build_settings['SWIFT_VERSION'] = '5.0'
  config.build_settings['CLANG_ENABLE_MODULES'] = 'YES'
  config.build_settings['OTHER_LDFLAGS'] ||= ['$(inherited)']
  config.build_settings['HEADER_SEARCH_PATHS'] ||= ['$(inherited)']
  config.build_settings['FRAMEWORK_SEARCH_PATHS'] ||= ['$(inherited)']
  config.build_settings['LIBRARY_SEARCH_PATHS'] ||= ['$(inherited)']
  config.build_settings['GENERATE_INFOPLIST_FILE'] = 'NO'
  config.build_settings['IPHONEOS_DEPLOYMENT_TARGET'] = '13.4'

  if config.name == 'Debug'
    config.build_settings['GCC_PREPROCESSOR_DEFINITIONS'] = ['DEBUG=1', '$(inherited)']
    config.build_settings['ONLY_ACTIVE_ARCH'] = 'YES'
  end

  if config.name == 'Release'
    config.build_settings['ONLY_ACTIVE_ARCH'] = 'NO'
  end
end

# Add source files to target
source_group = project.main_group.new_group('CallCoach', 'CallCoach')

# Add source files
['AppDelegate.h', 'AppDelegate.mm', 'main.m', 'CallStateModule.m'].each do |filename|
  filepath = File.join(ios_dir, 'CallCoach', filename)
  if File.exist?(filepath)
    ref = source_group.new_file(filepath)
    target.add_file_references([ref]) if filename.end_with?('.m', '.mm')
  end
end

# Add Info.plist
info_plist_path = File.join(ios_dir, 'CallCoach', 'Info.plist')
source_group.new_file(info_plist_path) if File.exist?(info_plist_path)

# Add LaunchScreen.storyboard
storyboard_path = File.join(ios_dir, 'CallCoach', 'LaunchScreen.storyboard')
if File.exist?(storyboard_path)
  ref = source_group.new_file(storyboard_path)
  target.add_file_references([ref])
end

# Add entitlements
entitlements_path = File.join(ios_dir, 'CallCoach', 'CallCoach.entitlements')
source_group.new_file(entitlements_path) if File.exist?(entitlements_path)

# Add PrivacyInfo
privacy_path = File.join(ios_dir, 'CallCoach', 'PrivacyInfo.xcprivacy')
if File.exist?(privacy_path)
  ref = source_group.new_file(privacy_path)
  target.add_file_references([ref])
end

# Add Images.xcassets
assets_path = File.join(ios_dir, 'CallCoach', 'Images.xcassets')
if File.exist?(assets_path)
  ref = source_group.new_file(assets_path)
  target.add_file_references([ref])
end

# Add test target
test_target = project.new_target(:unit_test_bundle, 'CallCoachTests', :ios, '13.4')
test_target.add_dependency(target)

# Save
project.save

puts "Xcode project created at: #{project_path}"
RUBY_SCRIPT

echo ""
echo "Xcode project generated."
echo ""

# Step 3: Install pods
echo "Installing CocoaPods dependencies..."
export IOS_DIR="$IOS_DIR"
pod install

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Open the workspace in Xcode:"
echo "  open CallCoach.xcworkspace"
echo ""
echo "Then:"
echo "  1. Select your Apple Developer team in Signing & Capabilities"
echo "  2. Select a simulator or connected device"
echo "  3. Press Cmd+R to build and run"
echo ""
echo "Or build from terminal:"
echo "  xcodebuild -workspace CallCoach.xcworkspace -scheme CallCoach -configuration Debug -sdk iphonesimulator build"
