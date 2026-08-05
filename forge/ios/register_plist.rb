# register_plist.rb — registers GoogleService-Info.plist into the Xcode
# project + target Resources build phase, since there's no local Mac to
# do this by hand in Xcode. Runs during the Codemagic pre-build stage,
# from within forge/ios/App/ (see codemagic.yaml).
#
# Idempotent: safe to run on every build — skips if already registered.

require 'xcodeproj'

project_path = 'App.xcodeproj'
plist_filename = 'GoogleService-Info.plist'
target_name = 'App'
group_name = 'App'

project = Xcodeproj::Project.open(project_path)

target = project.targets.find { |t| t.name == target_name }
raise "Target '#{target_name}' not found in #{project_path}" unless target

group = project.main_group.find_subpath(group_name, true)
raise "Group '#{group_name}' not found in project" unless group

already_referenced = group.files.any? { |f| f.path == plist_filename }

if already_referenced
  puts "[register_plist] #{plist_filename} already in project — skipping"
else
  file_ref = group.new_reference(plist_filename)
  target.add_resources([file_ref])
  project.save
  puts "[register_plist] Added #{plist_filename} to project + Resources build phase"
end