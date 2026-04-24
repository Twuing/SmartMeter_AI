[app]
# (str) Title of your application
title = SmartMeter AI

# (str) Package name
package.name = smartmeterai

# (str) Package domain (needed for android packaging)
package.domain = org.test

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,jpeg,kv,json,db,csv

# (str) Application version
version = 1.0.0

# (list) Application requirements
# ВАЖНО: Убрали matplotlib и numpy, чтобы сборка не падала.
requirements = python3, hostpython3, kivy==2.3.0, kivymd==1.2.0, pillow, plyer, sdl2_ttf, sdl2_image, sdl2_mixer

# (str) Supported orientation
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Permissions
android.permissions = CAMERA, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, INTERNET

# (int) Target Android API, should be as high as possible.
android.api = 33

# (int) Minimum API your APK will support.
android.minapi = 21

# (str) Android NDK version to use
android.ndk = 25b

# (str) Android Build Tools version to use
# Это решение нашей проблемы с лицензиями!
android.build_tools_version = 33.0.0

# (bool) Use --private data storage
android.private_storage = True

# (str) Android logcat filters to use
android.logcat_filters = *:S python:D

# (str) Android architecture to build for
android.archs = arm64-v8a

# (bool) Allow backup
android.allow_backup = True

[buildozer]
# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = off, 1 = on)
warn_on_root = 1
