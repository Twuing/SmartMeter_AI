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
# ВНИМАНИЕ: Добавлены opencv и jnius. OpenCV нужен для обработки, jnius для камеры.
requirements = python3, hostpython3, kivy==2.3.0, kivymd==1.2.0, pillow, plyer, jnius, opencv, google-cloud-vision, google-auth, requests, certifi, charset-normalizer, idna, urllib3

# (str) Supported orientation
orientation = portrait

# (list) Permissions
# Полный набор прав: камера, интернет и доступ к фото для Android 13+ (MIUI)
android.permissions = CAMERA, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, INTERNET, READ_MEDIA_IMAGES, READ_MEDIA_VIDEO

# (int) Target Android API
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

# (bool) Copy library to python-install directory (needed for some binary libs)
android.copy_libs = 1

[buildozer]
# (int) Log level (0 = error only, 1 = info, 2 = debug)
log_level = 2

# (int) Display warning if buildozer is run as root
warn_on_root = 1
