[app]
title = Dinosaur Adventure
package.name = dinosauradventure
package.domain = com.tarun.games
source.dir = .
source.include_exts = py,png,jpg,jpeg,webp,wav,ogg,mp3,json,ttf
source.exclude_dirs = .git,.github,.buildozer,bin,__pycache__,venv,.venv
version = 1.0.0
requirements = python3,pygame-ce
orientation = landscape
fullscreen = 1

# The game uses app-private storage and procedural audio only.
# No dangerous Android permissions are requested.
android.permissions =
android.api = 35
android.minapi = 24
android.ndk_api = 24
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.logcat_filters = *:S python:D SDL:D
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 1
