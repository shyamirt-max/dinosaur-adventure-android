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

# No dangerous Android runtime permissions are required.
android.permissions =

android.api = 35
android.minapi = 24
android.ndk = 29
android.ndk_api = 24

# First test build for modern 64-bit Android phones.
android.archs = arm64-v8a

android.accept_sdk_license = True
android.logcat_filters = *:S python:D SDL:D

# Use SDL2 and the uploaded local pygame-ce recipe.
p4a.bootstrap = sdl2
p4a.branch = develop
p4a.local_recipes = recipes

[buildozer]
log_level = 2
warn_on_root = 1
