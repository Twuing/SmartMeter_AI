# VERSION 2.0: почти все работает но криво
import os
import re
import sqlite3
import csv
import tempfile
import webbrowser
from datetime import datetime
from urllib.parse import quote

try:
    import cv2
except ImportError:
    cv2 = None
try:
    import numpy as np
except ImportError:
    np = None
try:
    from google.cloud import vision
    from google.oauth2 import service_account
except ImportError:
    vision = None
    service_account = None
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.storage.jsonstore import JsonStore
from kivy.utils import platform
from kivy.uix.screenmanager import Screen
from kivy.uix.stencilview import StencilView
from kivy.uix.widget import Widget
from kivymd.app import MDApp
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.label import MDLabel
from kivymd.uix.list import IconRightWidget, MDList, TwoLineAvatarIconListItem
from kivymd.uix.screen import MDScreen
from kivymd.uix.snackbar import Snackbar
from plyer import notification
try:
    from plyer import camera
except Exception:
    camera = None


KV = """
MDScreen:
    MDBottomNavigation:
        id: bottom_nav
        panel_color: app.theme_cls.bg_normal
        text_color_active: app.theme_cls.primary_color

        MDBottomNavigationItem:
            name: "dashboard"
            text: "Сканер"
            icon: "camera-iris"

            FloatLayout:
                id: image_viewport
                size_hint: 1, 1

                # Layer 0: photo background (movable/scalable).
                StencilView:
                    id: scatter_host
                    size_hint: 1, 1
                    pos: 0, 0

                    Scatter:
                        id: image_scatter
                        size_hint: 1, 1
                        pos: 0, 0
                        do_rotation: False
                        do_translation: True
                        do_scale: True
                        auto_bring_to_front: False
                        scale_min: 0.1
                        scale_max: 20

                        Image:
                            id: selected_image
                            source: ""
                            allow_stretch: True
                            keep_ratio: True
                            size_hint: 1, 1
                            pos: 0, 0

                # Layer 1: editable results at the top.
                MDBoxLayout:
                    orientation: "vertical"
                    size_hint_x: 1
                    size_hint_y: None
                    adaptive_height: True
                    spacing: dp(6)
                    padding: dp(20), dp(40), dp(20), 0
                    pos_hint: {"top": 1}

                    MDCard:
                        orientation: "vertical"
                        adaptive_height: True
                        md_bg_color: 0.95, 0.95, 0.95, 0.95
                        padding: dp(10), dp(10), dp(10), dp(10)
                        radius: [12, 12, 12, 12]
                        elevation: 1

                        MDBoxLayout:
                            orientation: "vertical"
                            adaptive_height: True
                            spacing: dp(15)
                            padding: dp(10), dp(10), dp(10), dp(10)

                            MDTextField:
                                id: reading_input
                                text: ""
                                hint_text: "Показания"
                                helper_text: "Проверьте и исправьте данные"
                                helper_text_mode: "on_focus"
                                helper_text_color_normal: app.theme_cls.accent_color
                                helper_text_color_focus: app.theme_cls.accent_color
                                mode: "rectangle"
                                focus: False
                                opacity: 1
                                size_hint_y: None
                                height: dp(44)
                                font_size: "20sp"
                                input_filter: "float"
                                text_color_normal: 0, 0, 0, 1
                                text_color_focus: 0, 0, 0, 1
                                on_text: app.on_reading_input_change(self.text)

                            MDIconButton:
                                id: confirm_button
                                icon: "check"
                                theme_text_color: "Custom"
                                text_color: 1, 1, 1, 1
                                md_bg_color: 0.0, 0.6, 0.35, 1
                                on_release: app.save_current_reading()

                            MDLabel:
                                id: cost_label
                                text: "0.00 кВт·ч | 0.00 тг."
                                bold: True
                                font_size: "14sp"
                                theme_text_color: "Custom"
                                text_color: 0, 0.6, 0, 1
                                halign: "left"
                                size_hint_y: None
                                height: self.texture_size[1]

                            MDLabel:
                                id: total_label
                                text: ""
                                font_size: "13sp"
                                theme_text_color: "Custom"
                                text_color: 0.8, 0.2, 0.2, 1
                                halign: "left"
                                size_hint_y: None
                                height: self.texture_size[1]

                # Layer 2: frame overlay (touch transparent).
                OverlayWidget:
                    id: overlay_layer
                    input_transparent: True
                    size_hint: 1, 1
                    pos: 0, 0
                    canvas.before:
                        Color:
                            rgba: 0, 0, 0, 0
                        Color:
                            rgba: 1, 0.3, 0.3, 0.28 if app.show_frame else 0
                        Rectangle:
                            pos: app.excluded_x, app.frame_y
                            size: app.excluded_w, app.frame_h
                        Color:
                            rgba: 0, 0, 0, 0.9 if app.show_frame else 0
                        Line:
                            rectangle: (app.frame_x + 1, app.frame_y - 1, app.frame_w, app.frame_h)
                            width: 3
                        Line:
                            points: [app.excluded_x + 1, app.frame_y - 1, app.excluded_x + 1, app.frame_y + app.frame_h - 1]
                            width: 3
                        Color:
                            rgba: 0, 1, 0, 1 if app.show_frame else 0
                        Line:
                            rectangle: (app.frame_x, app.frame_y, app.frame_w, app.frame_h)
                            width: 3
                        Line:
                            points: [app.excluded_x, app.frame_y, app.excluded_x, app.frame_y + app.frame_h]
                            width: 3
                        # Viewfinder corners (L-shape) for stronger framing.
                        Line:
                            points: [app.frame_x, app.frame_y + app.frame_h, app.frame_x + dp(22), app.frame_y + app.frame_h]
                            width: 3
                        Line:
                            points: [app.frame_x, app.frame_y + app.frame_h, app.frame_x, app.frame_y + app.frame_h - dp(22)]
                            width: 3
                        Line:
                            points: [app.frame_x + app.frame_w, app.frame_y + app.frame_h, app.frame_x + app.frame_w - dp(22), app.frame_y + app.frame_h]
                            width: 3
                        Line:
                            points: [app.frame_x + app.frame_w, app.frame_y + app.frame_h, app.frame_x + app.frame_w, app.frame_y + app.frame_h - dp(22)]
                            width: 3
                        Line:
                            points: [app.frame_x, app.frame_y, app.frame_x + dp(22), app.frame_y]
                            width: 3
                        Line:
                            points: [app.frame_x, app.frame_y, app.frame_x, app.frame_y + dp(22)]
                            width: 3
                        Line:
                            points: [app.frame_x + app.frame_w, app.frame_y, app.frame_x + app.frame_w - dp(22), app.frame_y]
                            width: 3
                        Line:
                            points: [app.frame_x + app.frame_w, app.frame_y, app.frame_x + app.frame_w, app.frame_y + dp(22)]
                            width: 3

                # Layer 3: action buttons near the bottom.
                MDBoxLayout:
                    orientation: "horizontal"
                    size_hint_x: 1
                    size_hint_y: None
                    height: dp(52)
                    spacing: dp(10)
                    padding: dp(10)
                    pos_hint: {"x": 0, "y": 0.08}

                    MDRaisedButton:
                        text: "Загрузить фото"
                        icon: "image-plus"
                        md_bg_color: 0.1, 0.45, 0.9, 1
                        text_color: 1, 1, 1, 1
                        on_release: app.open_file_manager()

                    MDRaisedButton:
                        text: "Фото"
                        icon: "camera"
                        md_bg_color: 0.35, 0.35, 0.35, 1
                        text_color: 1, 1, 1, 1
                        on_release: app.take_photo()

                    MDRaisedButton:
                        text: "Распознать"
                        icon: "file-find"
                        md_bg_color: 0.0, 0.6, 0.35, 1
                        text_color: 1, 1, 1, 1
                        on_release: app.recognize_reading()

        MDBottomNavigationItem:
            name: "history"
            text: "История"
            icon: "history"
            on_tab_press: app.load_history_from_db()

            MDBoxLayout:
                orientation: "vertical"
                padding: "20dp"
                spacing: "12dp"

                MDCard:
                    id: monthly_total_card
                    orientation: "vertical"
                    padding: "12dp"
                    radius: [12, 12, 12, 12]
                    elevation: 1
                    md_bg_color: 0.95, 0.95, 0.95, 1
                    size_hint_y: None
                    height: self.minimum_height

                    MDLabel:
                        text: "Итого за месяц"
                        theme_text_color: "Primary"
                        size_hint_y: None
                        height: self.texture_size[1]

                    MDLabel:
                        id: total_kwh_label
                        text: "Всего потрачено: 0 кВт·ч"
                        font_style: "H6"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: 0, 0.6, 0, 1
                        size_hint_y: None
                        height: self.texture_size[1]

                    Widget:
                        size_hint_y: None
                        height: dp(4)

                    MDLabel:
                        id: total_money_label
                        text: "Итого к оплате: 0.00 тг."
                        theme_text_color: "Primary"
                        size_hint_y: None
                        height: self.texture_size[1]

                    MDBoxLayout:
                        size_hint_y: None
                        height: self.minimum_height
                        spacing: "6dp"

                        MDIcon:
                            id: monthly_warning_icon
                            icon: "alert-outline"
                            theme_text_color: "Custom"
                            text_color: 1, 0.45, 0, 1
                            opacity: 0
                            size_hint: None, None
                            size: dp(20), dp(20)

                        MDLabel:
                            id: monthly_warning_text
                            text: "Превышение лимита"
                            theme_text_color: "Custom"
                            text_color: 1, 0.45, 0, 1
                            opacity: 0
                            size_hint_y: None
                            height: self.texture_size[1]

                MDBoxLayout:
                    size_hint_y: None
                    height: dp(40)
                    spacing: "10dp"

                    MDRaisedButton:
                        text: "Экспорт"
                        icon: "file-export"
                        on_release: app.export_to_csv()

                    MDRaisedButton:
                        text: "Очистить всё"
                        icon: "delete-alert"
                        md_bg_color: 0.8, 0.2, 0.2, 1
                        on_release: app.confirm_clear_history()

                ScrollView:
                    MDList:
                        id: history_md_list

        MDBottomNavigationItem:
            name: "settings"
            text: "Настройки"
            icon: "cog"

            MDBoxLayout:
                orientation: "vertical"
                spacing: "16dp"
                padding: "20dp"

                MDTextField:
                    id: price_input
                    hint_text: "Цена за 1 кВт/ч"
                    helper_text: "Введите число, например: 5.80"
                    helper_text_mode: "on_focus"
                    mode: "rectangle"
                    input_filter: "float"
                    input_type: "number"

                MDTextField:
                    id: consumption_limit_input
                    hint_text: "Норма: 200 кВт·ч"
                    helper_text: "Лимит потребления за месяц"
                    helper_text_mode: "on_focus"
                    mode: "rectangle"
                    input_filter: "float"

                MDTextField:
                    id: reminder_day_input
                    hint_text: "День напоминания (1-31)"
                    helper_text: "Например: 25"
                    helper_text_mode: "on_focus"
                    mode: "rectangle"
                    input_filter: "int"

                MDBoxLayout:
                    size_hint_y: None
                    height: dp(40)
                    spacing: "10dp"

                    MDCheckbox:
                        id: reminder_checkbox
                        active: app.reminder_enabled
                        size_hint: None, None
                        size: dp(36), dp(36)
                        selected_color: 0.1, 0.45, 0.9, 1
                        unselected_color: 0.5, 0.5, 0.5, 1
                        pos_hint: {"center_y": 0.5}

                    MDLabel:
                        id: reminder_checkbox_label
                        text: "Включить напоминания"
                        valign: "middle"
                        on_touch_down: app.toggle_reminder_checkbox(*args)

                MDTextField:
                    id: google_key_path_input
                    hint_text: "Путь к Google Key"
                    helper_text: "Укажите путь к JSON-ключу Google Cloud"
                    helper_text_mode: "on_focus"
                    mode: "rectangle"

                MDRaisedButton:
                    text: "Выбрать файл"
                    icon: "file-search"
                    size_hint_x: 1
                    on_release: app.open_key_file_manager()

                MDRaisedButton:
                    text: "Сохранить"
                    icon: "content-save"
                    size_hint_x: 1
                    on_release: app.save_settings()

                MDLabel:
                    id: save_status
                    text: ""
                    theme_text_color: "Hint"

        MDBottomNavigationItem:
            name: "analytics"
            text: "Графики"
            icon: "chart-line"
            on_tab_press: app.update_chart()

            AnalyticsScreen:
                id: analytics_screen
                MDBoxLayout:
                    orientation: "vertical"
                    padding: "16dp"
                    spacing: "12dp"

                    MDLabel:
                        text: "График расхода"
                        font_style: "H6"
                        theme_text_color: "Primary"
                        size_hint_y: None
                        height: self.texture_size[1]

                    MDBoxLayout:
                        id: analytics_chart_box
                        md_bg_color: 0.96, 0.96, 0.96, 1

                    MDCard:
                        orientation: "vertical"
                        adaptive_height: True
                        padding: "12dp"
                        spacing: "8dp"
                        radius: [12, 12, 12, 12]
                        elevation: 1
                        md_bg_color: 0.97, 0.97, 0.97, 1

                        MDLabel:
                            id: analytics_title
                            text: "Аналитика за текущий месяц"
                            bold: True
                            theme_text_color: "Primary"
                            size_hint_y: None
                            height: self.texture_size[1]

                        MDLabel:
                            id: monthly_usage_text
                            text: "Всего потрачено: 0.00 кВт·ч"
                            theme_text_color: "Custom"
                            text_color: 0, 0.4, 0.8, 1
                            size_hint_y: None
                            height: self.texture_size[1]

                        MDLabel:
                            id: daily_avg_text
                            text: "В среднем за сутки: 0.00 кВт·ч"
                            theme_text_color: "Custom"
                            text_color: 0.2, 0.5, 0.2, 1
                            size_hint_y: None
                            height: self.texture_size[1]

                        MDLabel:
                            id: status_text
                            text: "Статус: В норме"
                            theme_text_color: "Custom"
                            text_color: 0, 0.6, 0, 1
                            size_hint_y: None
                            height: self.texture_size[1]

                        MDRaisedButton:
                            text: "Отправить отчет"
                            icon: "share-variant"
                            on_release: app.share_monthly_report()
"""


class RootScreen(Screen):
    pass


class AnalyticsScreen(MDScreen):
    pass


class OverlayWidget(Widget):
    input_transparent = BooleanProperty(True)

    def on_touch_down(self, touch):
        if self.input_transparent:
            return False
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.input_transparent:
            return False
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if self.input_transparent:
            return False
        return super().on_touch_up(touch)


class SmartMeterApp(MDApp):
    show_frame = BooleanProperty(True)
    reminder_enabled = BooleanProperty(False)
    status_text = StringProperty("0.00 тг.")
    overlay_y = NumericProperty(0)
    overlay_h = NumericProperty(0)
    frame_view_x = NumericProperty(0)
    frame_view_y = NumericProperty(0)
    frame_view_w = NumericProperty(0)
    frame_view_h = NumericProperty(0)
    frame_x = NumericProperty(0)
    frame_y = NumericProperty(0)
    frame_w = NumericProperty(0)
    frame_h = NumericProperty(0)
    excluded_x = NumericProperty(0)
    excluded_w = NumericProperty(0)

    STORE_FILE = "app_settings.json"
    VISION_KEY_FILE = "google_vision_key.json"
    PROCESSED_IMAGE_FILE = "processed_temp.png"
    OCR_READY_FILE = "ocr_ready.png"
    FRAME_WIDTH_RATIO = 0.75
    FRAME_HEIGHT_RATIO = 0.32
    MAIN_DIGITS_RATIO = 0.8

    def app_storage_path(self, filename):
        base_dir = os.path.abspath(os.getcwd())
        os.makedirs(base_dir, exist_ok=True)
        return os.path.join(base_dir, filename)

    def build(self):
        self.title = "SmartMeter AI"
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Blue"
        self.price_per_kwh = 0.0
        self.monthly_limit_kwh = 200.0
        self.reminder_day = 1
        self.reminder_enabled = False
        self.google_key_path = ""
        self.store = JsonStore(self.app_storage_path(self.STORE_FILE))
        self.vision_client = self.create_vision_client()
        self.file_manager = MDFileManager(
            exit_manager=self.exit_file_manager,
            select_path=self.select_image_path,
            ext=[".jpg", ".jpeg", ".png"],
        )
        self.key_file_manager = MDFileManager(
            exit_manager=self.exit_key_file_manager,
            select_path=self.select_key_path,
            ext=[".json"],
        )
        self.file_manager_opened = False
        self.key_file_manager_opened = False
        self.current_image_path = ""
        self.db_conn = None
        self.clear_dialog = None
        self.share_dialog = None
        self.report_dialog = None
        Window.bind(on_keyboard=self.on_keyboard)
        root = Builder.load_string(KV)
        self.load_settings(root)
        root.ids.image_viewport.bind(size=self.update_frame_geometry, pos=self.update_frame_geometry)
        Window.bind(on_resize=self.on_window_resize)
        Clock.schedule_once(self.update_frame_geometry, 0)
        return root

    def on_start(self):
        db_path = self.app_storage_path("meter_readings.db")
        self.db_conn = sqlite3.connect(db_path)
        cursor = self.db_conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                value REAL NOT NULL,
                cost REAL NOT NULL
            )
            """
        )
        # One-time reset to discard legacy incorrect totals.
        if not self.store.exists("db_reset_done"):
            cursor.execute("DELETE FROM readings")
            self.store.put("db_reset_done", value=True)
        self.db_conn.commit()
        self.check_reminders()

    def on_stop(self):
        if self.db_conn:
            self.db_conn.close()
            self.db_conn = None

    def create_vision_client(self):
        if vision is None or service_account is None:
            print("Google Vision SDK недоступен: импорт не выполнен")
            return None
        # Primary source: settings.json -> google_api.key_path
        key_path = ""
        legacy_store = JsonStore(self.app_storage_path("settings.json"))
        if legacy_store.exists("google_api"):
            key_path = legacy_store.get("google_api").get("key_path", "").strip()
        if not key_path:
            print("Путь к ключу не задан в настройках")

        # Fallback to current app settings.
        if not key_path:
            key_path = (self.google_key_path or "").strip()

        # Optional environment fallback.
        if not key_path:
            key_path = (os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or "").strip()

        # Final fallback to local default file.
        if not key_path:
            key_path = self.app_storage_path(self.VISION_KEY_FILE)

        if os.path.exists(key_path):
            try:
                credentials = service_account.Credentials.from_service_account_file(key_path)
                return vision.ImageAnnotatorClient(credentials=credentials)
            except Exception as error:
                print(f"Ошибка инициализации клиента: {error}")
                return None
        else:
            print(f"Файл ключа не найден по пути: {key_path}")
            return None

    def load_settings(self, root):
        data = self.store.get("settings") if self.store.exists("settings") else {}

        value = data.get("price_per_kwh", 0.0)
        try:
            self.price_per_kwh = float(value)
        except (TypeError, ValueError):
            self.price_per_kwh = 0.0

        self.google_key_path = data.get("google_key_path", "")
        limit_value = data.get("monthly_limit_kwh", 200.0)
        reminder_day_value = data.get("reminder_day", 1)
        reminders_enabled_value = data.get("reminders_enabled", False)
        try:
            self.monthly_limit_kwh = float(limit_value)
        except (TypeError, ValueError):
            self.monthly_limit_kwh = 200.0
        try:
            self.reminder_day = max(1, min(31, int(reminder_day_value)))
        except (TypeError, ValueError):
            self.reminder_day = 1
        self.reminder_enabled = bool(reminders_enabled_value)
        root.ids.google_key_path_input.text = self.google_key_path
        root.ids.reminder_day_input.text = str(self.reminder_day)
        root.ids.reminder_checkbox.active = self.reminder_enabled
        root.ids.consumption_limit_input.text = f"{self.monthly_limit_kwh:.2f}"
        if self.price_per_kwh > 0:
            root.ids.price_input.text = f"{self.price_per_kwh:.2f}"
        self.vision_client = self.create_vision_client()
        self.update_cost_from_input()

    def toggle_reminder_checkbox(self, widget, touch):
        if not self.root:
            return False
        if not widget.collide_point(*touch.pos):
            return False
        checkbox = self.root.ids.reminder_checkbox
        checkbox.active = not checkbox.active
        self.reminder_enabled = checkbox.active
        return True

    def open_file_manager(self):
        start_path = os.path.expanduser("~")
        self.file_manager.show(start_path)
        self.file_manager_opened = True
        self.root.ids.total_label.text = "Выберите изображение..."

    def open_key_file_manager(self):
        start_path = os.path.expanduser("~")
        self.key_file_manager.show(start_path)
        self.key_file_manager_opened = True

    def select_key_path(self, path):
        if path.lower().endswith(".json"):
            self.root.ids.google_key_path_input.text = path
            self.google_key_path = path
        self.exit_key_file_manager()

    def exit_key_file_manager(self, *args):
        self.key_file_manager_opened = False
        self.key_file_manager.close()

    def take_photo(self):
        if platform == "win":
            print("Камера доступна только на Android")
            return
        if camera is None:
            print("Камера недоступна: plyer.camera не инициализирован")
            return

        fd, temp_path = tempfile.mkstemp(prefix="smartmeter_", suffix=".jpg")
        os.close(fd)

        try:
            camera.take_picture(filename=temp_path, on_complete=self.on_photo_complete)
        except Exception as error:
            print(f"Ошибка запуска камеры: {error}")

    def on_photo_complete(self, path):
        Clock.schedule_once(lambda dt: self._apply_captured_photo(path), 0)

    def _apply_captured_photo(self, path):
        if not path:
            return
        if not os.path.exists(path):
            return

        self.current_image_path = path
        self.root.ids.selected_image.source = path
        self.root.ids.selected_image.reload()
        Clock.schedule_once(self.reset_image_transform, 0)
        self.status_text = "Изображение готово к распознаванию"
        self.root.ids.total_label.text = self.status_text
        self.update_cost_from_input()

        placeholder = self.root.ids.get("camera_placeholder")
        if placeholder is not None:
            placeholder.opacity = 0
            placeholder.disabled = True

    def select_image_path(self, path):
        self.exit_file_manager()
        self.current_image_path = path
        self.root.ids.selected_image.source = path
        self.root.ids.selected_image.reload()
        Clock.schedule_once(self.reset_image_transform, 0)
        self.status_text = "Изображение готово к распознаванию"
        self.root.ids.total_label.text = self.status_text
        self.update_cost_from_input()

    def on_reading_text(self, value):
        # Backward-compatible alias for old KV bindings.
        self.on_reading_input_change(value)

    def on_reading_input_change(self, value):
        if not self.root:
            return
        raw_value = (value or "").strip().replace(",", ".")
        confirm_button = self.root.ids.confirm_button

        if not raw_value:
            confirm_button.disabled = True
            self.root.ids.total_label.text = ""
            self.root.ids.cost_label.text = "0.00 кВт·ч | 0.00 тг."
            self.root.ids.cost_label.text_color = (0, 0.6, 0, 1)
            return

        try:
            reading = float(raw_value)
        except ValueError:
            confirm_button.disabled = True
            self.root.ids.total_label.text = "Проверьте корректность распознавания."
            self.root.ids.cost_label.text = "Ошибка формата показаний."
            self.root.ids.cost_label.text_color = (1, 0.2, 0.2, 1)
            return

        last_reading = self.get_last_reading()
        consumption = 0.0 if last_reading is None else reading - last_reading
        if consumption < 0:
            confirm_button.disabled = True
            self.root.ids.total_label.text = "Проверьте корректность распознавания."
            self.root.ids.cost_label.text = "Ошибка: Показания меньше предыдущих!"
            self.root.ids.cost_label.text_color = (1, 0.2, 0.2, 1)
            return

        confirm_button.disabled = False
        cost = consumption * self.price_per_kwh
        self.root.ids.cost_label.text = (
            f"Расход: {consumption:.2f} кВт·ч | К оплате: {cost:.2f} тг."
        )
        self.root.ids.cost_label.text_color = (0, 0.6, 0, 1)
        self.root.ids.total_label.text = "Готово к сохранению"

    def update_cost_from_input(self):
        if not self.root:
            return
        self.on_reading_input_change(self.root.ids.reading_input.text)

    def get_last_reading(self):
        if self.db_conn is None:
            return None
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT value FROM readings ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        return float(row[0]) if row else None

    def reset_image_transform(self, *args):
        scatter_host = self.root.ids.scatter_host
        scatter = self.root.ids.image_scatter
        scatter.scale = 1
        scatter.center = scatter_host.center
        self.update_frame_geometry()

    def update_frame_geometry(self, *args):
        if not self.root:
            return
        viewport = self.root.ids.image_viewport
        vx, vy = viewport.pos
        vw, vh = viewport.size
        if vw <= 0 or vh <= 0:
            return

        self.frame_view_x = vx
        self.frame_view_y = vy
        self.frame_view_w = vw
        self.frame_view_h = vh
        self.overlay_y = vy
        self.overlay_h = vh
        self.frame_w = min(dp(260), vw)
        self.frame_h = min(dp(60), vh)
        self.frame_x = vx + (vw - self.frame_w) / 2
        self.frame_y = vy + (vh - self.frame_h) / 2 - dp(40)
        self.excluded_x = self.frame_x + self.frame_w * self.MAIN_DIGITS_RATIO
        self.excluded_w = self.frame_w * (1 - self.MAIN_DIGITS_RATIO)

    def on_window_resize(self, window, width, height):
        self.update_frame_geometry()

    def recognize_reading(self):
        if cv2 is None or np is None:
            print("Распознавание временно недоступно (нет OpenCV)")
            return
        if vision is None:
            print("Распознавание временно недоступно (нет Google Vision SDK)")
            return
        try:
            if self.vision_client is None:
                self.vision_client = self.create_vision_client()
                if self.vision_client is None:
                    self.status_text = "Google Vision не настроен: добавьте JSON-ключ."
                    self.root.ids.total_label.text = self.status_text
                    return
            if not self.current_image_path:
                self.status_text = "Сначала загрузите фото."
                self.root.ids.total_label.text = self.status_text
                return

            image = cv2.imdecode(
                np.fromfile(self.current_image_path, dtype=np.uint8),
                cv2.IMREAD_COLOR,
            )
            if image is None:
                self.status_text = "Ошибка чтения изображения."
                self.root.ids.total_label.text = self.status_text
                return

            scatter = self.root.ids.image_scatter
            image_widget = self.root.ids.selected_image
            current_scale = max(scatter.scale, 1e-6)
            if scatter.width <= 0 or scatter.height <= 0 or image_widget.width <= 0 or image_widget.height <= 0:
                self.status_text = "Невозможно определить область распознавания."
                self.root.ids.total_label.text = self.status_text
                return

            # Bottom-left corner of frame in scatter/image local space.
            local_x0, local_y0 = scatter.to_local(self.frame_x, self.frame_y, relative=True)
            # Crop size in local space with explicit scale compensation.
            local_w = (self.frame_w * self.MAIN_DIGITS_RATIO) / current_scale
            local_h = self.frame_h / current_scale
            local_cx = local_x0 + local_w / 2
            local_cy = local_y0 + local_h / 2

            img_h, img_w = image.shape[:2]
            u_center = max(0.0, min(1.0, local_cx / image_widget.width))
            v_center = max(0.0, min(1.0, local_cy / image_widget.height))
            crop_cx = int(u_center * img_w)
            crop_cy = int((1.0 - v_center) * img_h)  # invert Y: Kivy -> OpenCV

            crop_w = int((local_w / image_widget.width) * img_w * 1.1)
            crop_h = int((local_h / image_widget.height) * img_h * 1.1)
            crop_h = max(10, crop_h)
            crop_w = max(10, crop_w)
            crop_cy += 65

            x0 = max(0, crop_cx - crop_w // 2)
            x1 = min(img_w, crop_cx + crop_w // 2)
            y0 = max(0, crop_cy - crop_h // 2)
            y1 = min(img_h, crop_cy + crop_h // 2)

            if x1 <= x0 or y1 <= y0:
                self.status_text = "Область рамки вне изображения."
                self.root.ids.total_label.text = self.status_text
                return

            # Keep only precise crop from selection frame for Vision OCR.
            ocr_crop = image[y0:y1, x0:x1]
            ocr_ready_path = self.app_storage_path(self.OCR_READY_FILE)
            cv2.imwrite(ocr_ready_path, ocr_crop)
            debug_crop_path = self.app_storage_path("debug_crop.png")
            cv2.imwrite(debug_crop_path, ocr_crop)

            ok, encoded = cv2.imencode(".png", ocr_crop)
            if not ok:
                self.status_text = "Не удалось подготовить изображение для Vision OCR."
                self.root.ids.total_label.text = self.status_text
                return

            vision_image = vision.Image(content=encoded.tobytes())
            try:
                response = self.vision_client.text_detection(image=vision_image)
            except Exception as e:
                print(f"ПОДРОБНАЯ ОШИБКА GOOGLE: {e}")
                self.status_text = "Ошибка запроса к Google Vision."
                self.root.ids.total_label.text = self.status_text
                return

            if response.error.message:
                self.status_text = f"Google Vision error: {response.error.message}"
                self.root.ids.total_label.text = self.status_text
                return

            annotations = response.text_annotations or []
            first_line = annotations[0].description.splitlines()[0] if annotations else ""
            raw_value = re.sub(r"[^0-9.]", "", first_line)
            digits = raw_value.replace(".", "")
            print(f"Vision raw='{first_line.strip()}' normalized='{raw_value}'")
            if not digits:
                self.status_text = "Цифры не распознаны."
                self.root.ids.total_label.text = self.status_text
                print(f"Debug crop saved: {debug_crop_path}")
                print(self.status_text)
                return

            reading = float(raw_value) if raw_value else int(digits)
            self.root.ids.reading_input.text = str(reading)
            last_reading = self.get_last_reading()
            if last_reading is None:
                consumption = 0.0
            else:
                consumption = reading - last_reading
            if consumption < 0:
                self.root.ids.cost_label.text_color = (1, 0.2, 0.2, 1)
                self.root.ids.cost_label.text = "Ошибка: Показания меньше предыдущих!"
                self.root.ids.confirm_button.disabled = True
                self.status_text = "Проверьте корректность распознавания."
                self.root.ids.total_label.text = self.status_text
                return

            self.root.ids.confirm_button.disabled = False
            self.root.ids.cost_label.text_color = (0, 0.6, 0, 1)
            cost = consumption * self.price_per_kwh
            self.status_text = f"{reading} кВт·ч | {cost:.2f} тг."
            self.root.ids.cost_label.text = (
                f"Расход: {consumption:.2f} кВт·ч | К оплате: {cost:.2f} тг."
            )
            self.root.ids.total_label.text = "Распознавание выполнено."
            print(f"Debug crop saved: {debug_crop_path}")
            print(self.status_text)
        except Exception as error:
            print(f"Распознавание временно недоступно (ошибка OpenCV): {error}")
            return

    def add_to_history(self):
        self.save_current_reading()

    def save_current_reading(self):
        if self.db_conn is None:
            self.status_text = "База данных недоступна."
            self.root.ids.total_label.text = self.status_text
            return

        value = self.root.ids.reading_input.text.strip().replace(",", ".")
        if not value:
            self.status_text = "Введите или распознайте показания перед сохранением."
            self.root.ids.total_label.text = self.status_text
            return
        try:
            reading = float(value)
        except ValueError:
            self.status_text = "Некорректный формат показаний."
            self.root.ids.total_label.text = self.status_text
            return

        last_reading = self.get_last_reading()
        consumption = 0.0 if last_reading is None else reading - last_reading
        if consumption < 0:
            self.status_text = "Ошибка: Показания меньше предыдущих!"
            self.root.ids.total_label.text = self.status_text
            self.root.ids.cost_label.text_color = (1, 0.2, 0.2, 1)
            self.root.ids.confirm_button.disabled = True
            return

        cost = consumption * self.price_per_kwh
        date_value = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = self.db_conn.cursor()
        cursor.execute(
            "INSERT INTO readings (date, value, cost) VALUES (?, ?, ?)",
            (date_value, reading, cost),
        )
        self.db_conn.commit()

        self.status_text = "Запись добавлена в историю."
        self.root.ids.cost_label.text = f"Расход: {consumption:.2f} кВт·ч | К оплате: {cost:.2f} тг."
        self.root.ids.cost_label.text_color = (0, 0.6, 0, 1)
        self.root.ids.total_label.text = self.status_text
        self.root.ids.reading_input.text = ""
        self.root.ids.confirm_button.disabled = False
        try:
            snack = Snackbar(text="Данные успешно сохранены")
            snack.open()
        except Exception as error:
            print(f"Snackbar error: {error}")
            print("Данные успешно сохранены")
        self.load_history_from_db()

    def load_history_from_db(self):
        history_list = self.root.ids.history_md_list
        history_list.clear_widgets()
        if self.db_conn is None:
            return

        cursor = self.db_conn.cursor()
        cursor.execute(
            "SELECT id, date, value, cost FROM readings ORDER BY id DESC"
        )
        rows = cursor.fetchall()
        for row_id, date_value, value, cost in rows:
            item = TwoLineAvatarIconListItem(
                text=f"{value:.3f} кВт·ч",
                secondary_text=f"{date_value} | {cost:.2f} тг.",
            )
            share_button = IconRightWidget(icon="share-variant")
            share_button.bind(
                on_release=lambda _btn, d=date_value, r=float(value): self.show_share_dialog(d, r)
            )
            item.add_widget(share_button)
            delete_button = IconRightWidget(icon="delete")
            delete_button.bind(on_release=lambda _btn, rid=row_id: self.delete_reading(rid))
            item.add_widget(delete_button)
            history_list.add_widget(item)
        self.calculate_monthly_total()

    def update_chart(self):
        if not self.root:
            return
        chart_box = self.root.ids.analytics_chart_box
        chart_box.clear_widgets()
        if self.db_conn is None:
            chart_box.add_widget(MDLabel(text="База данных недоступна.", halign="center"))
            return

        cursor = self.db_conn.cursor()
        cursor.execute(
            "SELECT date, value FROM readings ORDER BY id DESC LIMIT 15"
        )
        rows = cursor.fetchall()
        if not rows:
            chart_box.add_widget(MDLabel(text="Нет данных для графика.", halign="center"))
            return

        rows = list(reversed(rows))
        dates = []
        values = []
        for date_value, reading in rows:
            try:
                dt_obj = datetime.strptime(date_value, "%Y-%m-%d %H:%M:%S")
                dates.append(dt_obj.strftime("%d.%m"))
            except ValueError:
                dates.append(date_value[:5])
            values.append(float(reading))

        consumptions = [0.0]
        for index in range(1, len(values)):
            consumptions.append(max(0.0, values[index] - values[index - 1]))

        print("График временно недоступен")
        chart_box.add_widget(
            MDLabel(
                text="График временно недоступен",
                halign="center",
                theme_text_color="Hint",
            )
        )

        current_dt = datetime.now()
        current_month = current_dt.strftime("%Y-%m")
        cursor.execute(
            "SELECT date, value FROM readings WHERE substr(date, 1, 7) = ? ORDER BY date ASC",
            (current_month,),
        )
        month_rows = cursor.fetchall()

        monthly_sum = 0.0
        if len(month_rows) > 1:
            prev_value = float(month_rows[0][1])
            for _, raw_value in month_rows[1:]:
                cur_value = float(raw_value)
                monthly_sum += max(0.0, cur_value - prev_value)
                prev_value = cur_value

        day_number = max(1, current_dt.day)
        daily_avg = monthly_sum / day_number

        self.root.ids.analytics_title.text = (
            f"Аналитика за {current_dt.strftime('%m.%Y')}"
        )
        self.root.ids.monthly_usage_text.text = (
            f"Всего потрачено: {monthly_sum:.2f} кВт·ч"
        )
        self.root.ids.daily_avg_text.text = (
            f"В среднем за сутки: {daily_avg:.2f} кВт·ч"
        )

        if monthly_sum > self.monthly_limit_kwh:
            self.root.ids.status_text.text = "Статус: Превышение!"
            self.root.ids.status_text.text_color = (0.9, 0.2, 0.2, 1)
        else:
            self.root.ids.status_text.text = "Статус: В норме"
            self.root.ids.status_text.text_color = (0, 0.6, 0, 1)

    def get_graph_widget(self, figure):
        print("График временно недоступен")
        return Widget()

    def calculate_monthly_total(self):
        if not self.root or self.db_conn is None:
            return
        current_month = datetime.now().strftime("%Y-%m")
        cursor = self.db_conn.cursor()
        cursor.execute(
            "SELECT value, cost FROM readings WHERE substr(date, 1, 7) = ? ORDER BY date ASC, id ASC",
            (current_month,),
        )
        rows = cursor.fetchall()

        total_consumption = 0.0
        total_price = 0.0
        prev_value = None
        for value, cost in rows:
            reading_value = float(value)
            if prev_value is not None:
                total_consumption += max(0.0, reading_value - prev_value)
            prev_value = reading_value
            total_price += float(cost or 0.0)

        self.root.ids.total_kwh_label.text = f"Всего потрачено: {total_consumption:.2f} кВт·ч"
        self.root.ids.total_money_label.text = f"Итого к оплате: {total_price:.2f} тг."

        if total_consumption > self.monthly_limit_kwh:
            self.root.ids.monthly_total_card.md_bg_color = (1.0, 0.75, 0.4, 1)
            self.root.ids.monthly_warning_icon.opacity = 1
            self.root.ids.monthly_warning_text.opacity = 1
        else:
            self.root.ids.monthly_total_card.md_bg_color = (0.95, 0.95, 0.95, 1)
            self.root.ids.monthly_warning_icon.opacity = 0
            self.root.ids.monthly_warning_text.opacity = 0

    def delete_reading(self, reading_id):
        if self.db_conn is None:
            return
        cursor = self.db_conn.cursor()
        cursor.execute("DELETE FROM readings WHERE id = ?", (reading_id,))
        self.db_conn.commit()
        self.load_history_from_db()

    def export_to_csv(self):
        if self.db_conn is None:
            self.root.ids.total_label.text = "База данных недоступна."
            return
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT id, date, value, cost FROM readings ORDER BY id ASC")
        rows = cursor.fetchall()
        export_path = self.app_storage_path("readings_export.csv")
        with open(export_path, "w", newline="", encoding="utf-8-sig") as csv_file:
            writer = csv.writer(csv_file, delimiter=";")
            writer.writerow(["Дата", "Показания", "Расход (кВт·ч)", "Тариф (тг)", "Итого (тг)"])
            if not rows:
                writer.writerow(["Нет данных", "", "", "", ""])
            else:
                previous_value = None
                for _row_id, date_value, value, cost in rows:
                    reading_value = float(value)
                    total_cost = float(cost)
                    try:
                        dt_obj = datetime.strptime(date_value, "%Y-%m-%d %H:%M:%S")
                        export_date = dt_obj.strftime("%d.%m.%Y %H:%M")
                    except ValueError:
                        export_date = date_value
                    if previous_value is None:
                        consumption = 0.0
                    else:
                        consumption = max(0.0, reading_value - previous_value)
                    tariff = (
                        (total_cost / consumption) if consumption > 0 else float(self.price_per_kwh)
                    )
                    writer.writerow(
                        [
                            export_date,
                            f"{reading_value:.2f}".replace(".", ","),
                            f"{consumption:.2f}".replace(".", ","),
                            f"{tariff:.2f}".replace(".", ","),
                            f"{total_cost:.2f}".replace(".", ","),
                        ]
                    )
                    previous_value = reading_value
        self.root.ids.total_label.text = f"Экспортировано: {export_path}"

    def confirm_clear_history(self):
        if self.clear_dialog:
            self.clear_dialog.dismiss()
        self.clear_dialog = MDDialog(
            title="Очистить историю",
            text="Удалить все записи из базы данных?",
            buttons=[
                MDFlatButton(text="Отмена", on_release=lambda *_: self.clear_dialog.dismiss()),
                MDFlatButton(text="Очистить", on_release=lambda *_: self.clear_all_readings()),
            ],
        )
        self.clear_dialog.open()

    def clear_all_readings(self):
        if self.db_conn is None:
            return
        cursor = self.db_conn.cursor()
        cursor.execute("DELETE FROM readings")
        self.db_conn.commit()
        if self.clear_dialog:
            self.clear_dialog.dismiss()
            self.clear_dialog = None
        self.load_history_from_db()
        self.root.ids.total_label.text = "История очищена."

    def show_share_dialog(self, date, reading):
        if self.share_dialog:
            self.share_dialog.dismiss()
        self.share_dialog = MDDialog(
            title="Поделиться показаниями",
            text=f"Дата: {date}\nПоказания: {reading:.3f} кВт·ч",
            buttons=[
                MDFlatButton(
                    text="Telegram",
                    on_release=lambda *_: self.share_to_messenger("telegram", date, reading),
                ),
                MDFlatButton(
                    text="WhatsApp",
                    on_release=lambda *_: self.share_to_messenger("whatsapp", date, reading),
                ),
                MDFlatButton(text="Отмена", on_release=lambda *_: self.dismiss_share_dialog()),
            ],
        )
        self.share_dialog.open()

    def dismiss_share_dialog(self):
        if self.share_dialog:
            self.share_dialog.dismiss()
            self.share_dialog = None

    def share_to_messenger(self, messenger, date, reading):
        text = (
            "Здравствуйте! Показания счетчика электроэнергии.\n"
            f"Дата: {date}\n"
            f"Текущие показания: {reading:.3f} кВт·ч."
        )
        if messenger == "telegram":
            url = f"https://t.me/share/url?url={quote(text)}"
        elif messenger == "whatsapp":
            url = f"https://wa.me/?text={quote(text)}"
        else:
            return
        webbrowser.open(url)
        self.dismiss_share_dialog()

    def share_monthly_report(self):
        if not self.root:
            return
        current_dt = datetime.now()
        month_title = current_dt.strftime("%m.%Y")

        usage_text = self.root.ids.monthly_usage_text.text
        avg_text = self.root.ids.daily_avg_text.text
        status_text_value = self.root.ids.status_text.text.replace("Статус: ", "")

        usage_value = re.sub(r"[^\d.,]", "", usage_text.split(":")[-1]).replace(",", ".")
        avg_value = re.sub(r"[^\d.,]", "", avg_text.split(":")[-1]).replace(",", ".")
        usage_value = usage_value if usage_value else "0.00"
        avg_value = avg_value if avg_value else "0.00"

        report_text = (
            f"Отчет по электроэнергии за {month_title}.\n"
            f"Итоговый расход: {usage_value} кВт·ч.\n"
            f"Среднее в сутки: {avg_value} кВт·ч.\n"
            f"Статус: {status_text_value}."
        )

        if self.report_dialog:
            self.report_dialog.dismiss()

        self.report_dialog = MDDialog(
            title="Отправить отчет",
            text=report_text,
            buttons=[
                MDFlatButton(
                    text="Telegram",
                    on_release=lambda *_: self._open_report_link("telegram", report_text),
                ),
                MDFlatButton(
                    text="WhatsApp",
                    on_release=lambda *_: self._open_report_link("whatsapp", report_text),
                ),
                MDFlatButton(text="Отмена", on_release=lambda *_: self._dismiss_report_dialog()),
            ],
        )
        self.report_dialog.open()

    def _dismiss_report_dialog(self):
        if self.report_dialog:
            self.report_dialog.dismiss()
            self.report_dialog = None

    def _open_report_link(self, messenger, text):
        if messenger == "telegram":
            url = f"https://t.me/share/url?url={quote(text)}"
        elif messenger == "whatsapp":
            url = f"https://wa.me/?text={quote(text)}"
        else:
            return
        webbrowser.open(url)
        self._dismiss_report_dialog()

    def exit_file_manager(self, *args):
        self.file_manager_opened = False
        self.file_manager.close()

    def on_keyboard(self, window, key, scancode, codepoint, modifiers):
        if key in (27, 1001) and self.file_manager_opened:
            self.exit_file_manager()
            return True
        if key in (27, 1001) and self.key_file_manager_opened:
            self.exit_key_file_manager()
            return True
        return False

    def save_settings(self):
        value = self.root.ids.price_input.text.strip().replace(",", ".")
        key_path = self.root.ids.google_key_path_input.text.strip()
        limit_text = self.root.ids.consumption_limit_input.text.strip().replace(",", ".")
        reminder_day_text = self.root.ids.reminder_day_input.text.strip()
        reminders_enabled = self.root.ids.reminder_checkbox.active
        if not value:
            self.root.ids.save_status.text = "Введите цену перед сохранением."
            return
        try:
            self.price_per_kwh = float(value)
            self.monthly_limit_kwh = float(limit_text) if limit_text else 200.0
            self.reminder_day = max(1, min(31, int(reminder_day_text))) if reminder_day_text else 1
            self.reminder_enabled = bool(reminders_enabled)
            self.google_key_path = key_path
            self.store.put(
                "settings",
                price_per_kwh=self.price_per_kwh,
                google_key_path=self.google_key_path,
                monthly_limit_kwh=self.monthly_limit_kwh,
                reminder_day=self.reminder_day,
                reminders_enabled=self.reminder_enabled,
            )
            self.vision_client = self.create_vision_client()
            if self.vision_client is not None and self.google_key_path:
                self.root.ids.save_status.text = "Ключ успешно подключен"
            elif self.vision_client is not None:
                self.root.ids.save_status.text = (
                    f"Сохранено: {self.price_per_kwh:.2f} тг. за 1 кВт·ч"
                )
            else:
                self.root.ids.save_status.text = "Сохранено, но ключ Google не подключен."
            self.update_cost_from_input()
            self.calculate_monthly_total()
        except ValueError:
            self.root.ids.save_status.text = "Некорректное значение цены или лимита."
        except OSError:
            self.root.ids.save_status.text = "Ошибка сохранения настроек."

    def check_reminders(self):
        if not self.reminder_enabled:
            return
        today = datetime.now()
        if today.day != self.reminder_day:
            return

        current_month = today.strftime("%Y-%m")
        state = self.store.get("reminder_state") if self.store.exists("reminder_state") else {}
        last_notified_month = state.get("last_notified_month", "")
        if last_notified_month == current_month:
            return

        try:
            notification.notify(
                title="SmartMeter AI",
                message="Пора передать показания счетчика!",
                app_name="SmartMeter AI",
                timeout=10,
            )
            self.store.put("reminder_state", last_notified_month=current_month)
        except Exception as error:
            print(f"Reminder notification error: {error}")


if __name__ == "__main__":
    SmartMeterApp().run()
