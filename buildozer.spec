[app]
title = SmartMeter AI
package.name = smartmeterai
package.domain = org.test
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,json,db,csv
version = 1.0.0

# Добавлена связка для стабильной сборки KivyMD
requirements = python3, kivy==2.3.0, kivymd==1.2.0, pillow, matplotlib, numpy, pandas, pyparsing, cycler, python-dateutil, kiwisolver

orientation = portrait
fullscreen = 0
android.permissions = CAMERA, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, INTERNET
android.api = 33
android.minapi = 21
android.ndk = 25b
android.build_tools_version = 33.0.0
android.archs = arm64-v8a
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
