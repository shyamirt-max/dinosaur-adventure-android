#!/usr/bin/env bash
set -e
python3 -m pip install --user --upgrade buildozer cython virtualenv
buildozer android debug
printf '\nAPK output:\n'
find bin -maxdepth 1 -type f -name '*.apk' -print
