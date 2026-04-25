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

# (list) List of inclusions using pattern matching
source.include_patterns = assets/*,images/*.png

# (str) Application version
version = 1.0.0

# (list) Application requirements
# Добавлена jnius для работы со StrictMode и расширенные либы для Google Cloud
requirements = python3, hostpython3, kivy==2.3.0, kivymd==1.2.0, pillow, plyer, jnius, sdl2_ttf, sdl2_image, sdl2_mixer, google-cloud-vision, google-auth, requests, certifi, charset-normalizer, idna, urllib3

# (str) Supported orientation
orientation = portrait

# (list) Permissions
# Добавлена критическая группа разрешений для Android 13+ (READ_MEDIA_IMAGES)
android.permissions = CAMERA, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, INTERNET, READ_MEDIA_IMAGES, READ_MEDIA_VIDEO

# (int) Target Android API
# API 33 соответствует Android 13, что правильно для современных устройств
android.api = 33

# (int) Minimum API
android.minapi = 21

# (str) Android NDK version
android.ndk = 25b

# (str) Android Build Tools version
android.build_tools_version = 33.0.0

# (bool) Use --private data storage
android.private_storage = True

# (str) Android logcat filters
android.logcat_filters = *:S python:D

# (str) Android architecture to build for
android.archs = arm64-v8a

# (list) The Android archs to build for
# Фиксируем arm64-v8a для стабильности на твоем Xiaomi

[buildozer]
# (int) Log level (0 = error only, 1 = info, 2 = debug)
log_level = 2

# (int) Display warning if buildozer is run as root
warn_on_root = 1
