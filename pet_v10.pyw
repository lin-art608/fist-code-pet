"""桌宠 v10：完整主程序、64 帧舞蹈与逐像素透明。"""
from __future__ import annotations

import ctypes
import json
import os
import random
import sys
import time
from pathlib import Path

from PySide6.QtCore import QPoint, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QAction,
    QColor,
    QCloseEvent,
    QFont,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QApplication, QMenu, QWidget


ROOT = Path(__file__).resolve().parent
ASSET_DIR = ROOT / "assets"
ACTION_DIR = ASSET_DIR / "actions"
SAVE_FILE = ROOT / "pet_save.json"
WINDOW_SIZE = (400, 500)
ACTION_COUNTS = {"idle": 8, "wave": 8, "jump": 8, "dance": 64, "feed": 8}
ACTION_INTERVALS = {"idle": 180, "wave": 160, "jump": 180, "dance": 42, "feed": 200}
LOOP_ACTIONS = {"idle"}


class State:
    def __init__(self) -> None:
        self.data = {"mood": 80, "hunger": 30, "energy": 90, "intimacy": 50}
        self.load()

    def load(self) -> None:
        try:
            if SAVE_FILE.exists():
                saved = json.loads(SAVE_FILE.read_text(encoding="utf-8"))
                self.data.update({key: value for key, value in saved.items() if key in self.data})
        except (OSError, ValueError, TypeError):
            pass

    def save(self) -> None:
        try:
            SAVE_FILE.write_text(
                json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError:
            pass

    def feed(self) -> None:
        self.data["hunger"] = max(0, self.data["hunger"] - 30)
        self.data["mood"] = min(100, self.data["mood"] + 5)
        self.data["intimacy"] = min(100, self.data["intimacy"] + 2)


class DesktopPet(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.state = State()
        self._shutting_down = False
        self._drag_offset: QPoint | None = None
        self._action = "idle"
        self._frame_index = 0
        self._bubble_text = ""
        self._last_save = time.time()
        self._next_auto_talk = time.time() + random.uniform(25, 45)

        self.setWindowTitle("桌宠 v10")
        self.setFixedSize(*WINDOW_SIZE)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.frames = self._load_frames()

        self.action_timer = QTimer(self)
        self.action_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.action_timer.timeout.connect(self._next_frame)
        self.action_timer.start(ACTION_INTERVALS[self._action])

        self.bubble_timer = QTimer(self)
        self.bubble_timer.setSingleShot(True)
        self.bubble_timer.timeout.connect(self._clear_bubble)

        self.background_timer = QTimer(self)
        self.background_timer.timeout.connect(self._background_tick)
        self.background_timer.start(5000)

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - self.width() - 24, screen.bottom() - self.height() - 24)
        self.say("你好～", 1800)

    @staticmethod
    def _load_frames() -> dict[str, list[QPixmap]]:
        result: dict[str, list[QPixmap]] = {}
        for action, count in ACTION_COUNTS.items():
            paths = sorted(ACTION_DIR.glob(f"{action}_*.png"))
            if len(paths) != count:
                raise RuntimeError(f"动作 {action} 应有 {count} 帧，实际找到 {len(paths)} 帧")
            pixmaps = [QPixmap(str(path)) for path in paths]
            if any(pixmap.isNull() for pixmap in pixmaps):
                raise RuntimeError(f"动作 {action} 存在无法读取的图片")
            result[action] = pixmaps
        return result

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.drawPixmap(0, 0, self.frames[self._action][self._frame_index])
        if self._bubble_text:
            bubble = QRectF(10, 6, self.width() - 20, 42)
            painter.setPen(QPen(QColor("#C7B487"), 1))
            painter.setBrush(QColor(255, 253, 247, 242))
            painter.drawRoundedRect(bubble, 10, 10)
            painter.setPen(QColor("#3C3A36"))
            painter.setFont(QFont("Microsoft YaHei", 10))
            painter.drawText(
                bubble.adjusted(10, 2, -10, -2),
                Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                self._bubble_text,
            )

    def play_action(self, action: str) -> None:
        if action not in self.frames:
            action = "idle"
        self._action = action
        self._frame_index = 0
        self.action_timer.setInterval(ACTION_INTERVALS[action])
        if not self.action_timer.isActive():
            self.action_timer.start()
        self.update()

    def _next_frame(self) -> None:
        frames = self.frames[self._action]
        next_index = self._frame_index + 1
        if next_index >= len(frames):
            if self._action in LOOP_ACTIONS:
                self._frame_index = 0
            else:
                self.play_action("idle")
                return
        else:
            self._frame_index = next_index
        self.update()

    def say(self, text: str, duration_ms: int = 2000) -> None:
        self._bubble_text = text
        self.bubble_timer.start(duration_ms)
        self.update()

    def _clear_bubble(self) -> None:
        self._bubble_text = ""
        self.update()

    def feed(self) -> None:
        self.state.feed()
        self.play_action("feed")
        self.say("好好吃～", 1500)

    def show_stats(self) -> None:
        data = self.state.data
        self.say(
            f'心情:{int(data["mood"])}  饥饿:{int(data["hunger"])}  '
            f'体力:{int(data["energy"])}  亲密:{int(data["intimacy"])}',
            3500,
        )

    def open_menu(self, position: QPoint) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background:#FFFDF7; color:#3C3A36; border:1px solid #BCA97F; "
            "padding:4px; } QMenu::item { padding:6px 28px 6px 16px; } "
            "QMenu::item:selected { background:#E8D9B8; }"
        )
        actions = [
            ("喂食", self.feed),
            ("挥手", lambda: self.play_action("wave")),
            ("跳一跳", lambda: self.play_action("jump")),
            ("跳个舞（64帧）", lambda: self.play_action("dance")),
            ("说句话", lambda: self.say(random.choice([
                "你好呀", "今天也辛苦了", "一直陪着你好吗", "要记得休息哦～"
            ]), 2200)),
            ("查看属性", self.show_stats),
        ]
        for label, callback in actions:
            action = QAction(label, menu)
            action.triggered.connect(callback)
            menu.addAction(action)
        menu.addSeparator()
        quit_action = QAction("退出", menu)
        quit_action.triggered.connect(self.close)
        menu.addAction(quit_action)
        menu.exec(position)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self.open_menu(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = None
            event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.feed()
            event.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def _background_tick(self) -> None:
        now = time.time()
        if now - self._last_save >= 10:
            self.state.save()
            self._last_save = now
        if now >= self._next_auto_talk:
            self._next_auto_talk = now + random.uniform(25, 45)
            if self.state.data["hunger"] > 70:
                self.say("有点饿了…", 2000)
            else:
                self.say(random.choice(["嗯～", "好安静", "陪你待着", "…"]), 1800)

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._shutting_down:
            self._shutting_down = True
            self.action_timer.stop()
            self.bubble_timer.stop()
            self.background_timer.stop()
            self.state.save()
        event.accept()
        app = QApplication.instance()
        if app is not None:
            QTimer.singleShot(0, app.quit)


def main() -> int:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    pet = DesktopPet()
    pet.show()
    if os.environ.get("DESKTOP_PET_SMOKE_TEST") == "1":
        QTimer.singleShot(100, lambda: pet.play_action("dance"))
        QTimer.singleShot(1000, pet.close)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
