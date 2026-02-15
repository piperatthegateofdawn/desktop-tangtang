import os
import sys
import time
import random
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QPixmap, QAction
from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QMenu


# ============== 可调参数 ==============
FPS_IDLE_MS = 300          # idle 每帧间隔（毫秒）
FPS_CLICK_MS = 200         # click 动画每帧间隔（毫秒）
FPS_DRAG_MS = 120          # drag 动画每帧间隔（毫秒）

CLICK2_HOLD_MS = 2000      # 点击2 停留时长（毫秒）
CLICK3_HOLD_MS = 3000      # 点击3 停留时长（毫秒）

BLINK_AFTER_CYCLES_MIN = 2
BLINK_AFTER_CYCLES_MAX = 5

RAPID_CLICK_WINDOW_SEC = 1.6
RAPID_CLICK_THRESHOLD = 5

TOP_MARGIN = 90            # 给气泡留空间（像素）
PET_SCALE = 0.25           # 桌宠缩放比例

BUBBLE_OFFSET_X = 70       # 气泡向右
BUBBLE_OFFSET_Y = 50       # 气泡向下

TIRED_RATIO = 0.2        # <20% 就疲惫
FPS_IDLE_TIRED_MS = 520    # 疲惫 idle 更慢（你可调）

# idle 闲聊
IDLE_CHAT_MIN_MS = 1 * 60 * 1000
IDLE_CHAT_MAX_MS = 5 * 60 * 1000
IDLE_CHAT_DURATION_MS = 6000

# 资源目录
ASSETS_DIR = "assets"
IDLE_DIR = os.path.join(ASSETS_DIR, "idle")
CLICK_DIR = os.path.join(ASSETS_DIR, "click")
DRAG_DIR = os.path.join(ASSETS_DIR, "drag")
FEED_DIR = os.path.join(ASSETS_DIR, "feed")
PAT_DIR = os.path.join(ASSETS_DIR, "pat")
PRAISE_DIR = os.path.join(ASSETS_DIR, "praise")


def resource_path(relative_path: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(__file__))
    return os.path.join(base, relative_path)


def load_pixmap(*path_parts: str) -> QPixmap:
    p = resource_path(os.path.join(*path_parts))
    if not os.path.exists(p):
        raise FileNotFoundError(f"找不到图片文件：{p}")
    pm = QPixmap(p)
    if pm.isNull():
        raise RuntimeError(f"图片加载失败（可能文件损坏或格式问题）：{p}")
    return pm


def pick_existing_idle_name(candidates: list[str]) -> str:
    for name in candidates:
        p = resource_path(os.path.join(IDLE_DIR, name))
        if os.path.exists(p):
            return name
    return candidates[0]


class DesktopPet(QWidget):
    def __init__(self):
        super().__init__()

        # 窗口：无边框、透明、置顶、Tool（不占任务栏）
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # 显示宠物图片
        self.label = QLabel(self)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        # ============== 加载资源 ==============
        # idle normal
        self.pm_normal = load_pixmap(IDLE_DIR, "正常.png")
        self.pm_sway1 = load_pixmap(IDLE_DIR, "摆动1.png")
        self.pm_sway2 = load_pixmap(IDLE_DIR, "摆动2.png")

        blink_up_name = pick_existing_idle_name(["眨眼(向上).png", "眨眼（向上）.png"])
        blink_close_name = pick_existing_idle_name(["眨眼(闭眼).png", "眨眼（闭眼）.png"])
        self.pm_blink_up = load_pixmap(IDLE_DIR, blink_up_name)
        self.pm_blink_close = load_pixmap(IDLE_DIR, blink_close_name)

        # idle tired
        self.pm_tired1 = load_pixmap(IDLE_DIR, "疲惫1.png")
        self.pm_tired2 = load_pixmap(IDLE_DIR, "疲惫2.png")
        self.pm_tired3 = load_pixmap(IDLE_DIR, "疲惫3.png")
        tired_blink_name = pick_existing_idle_name(["眨眼(疲惫).png", "眨眼（疲惫）.png"])
        self.pm_blink_tired = load_pixmap(IDLE_DIR, tired_blink_name)
        self.tired_step = 0

        # click
        self.pm_click1 = load_pixmap(CLICK_DIR, "点击1.png")
        self.pm_click2 = load_pixmap(CLICK_DIR, "点击2.png")
        self.pm_click3 = load_pixmap(CLICK_DIR, "点击3.png")

        # drag
        self.pm_drag1 = load_pixmap(DRAG_DIR, "拖动1.png")
        self.pm_drag2 = load_pixmap(DRAG_DIR, "拖动2.png")

        # feed
        self.pm_feed1 = load_pixmap(FEED_DIR, "投喂1.png")
        self.pm_feed2 = load_pixmap(FEED_DIR, "投喂2.png")
        self.pm_feed3 = load_pixmap(FEED_DIR, "投喂3.png")
        self.pm_feed4 = load_pixmap(FEED_DIR, "投喂4.png")
        self.pm_feed5 = load_pixmap(FEED_DIR, "投喂5.png")

        # pat
        self.pm_pat1 = load_pixmap(PAT_DIR, "摸摸1.png")
        self.pm_pat2 = load_pixmap(PAT_DIR, "摸摸2.png")
        self.pm_pat3 = load_pixmap(PAT_DIR, "摸摸3.png")
        self.pm_pat4 = load_pixmap(PAT_DIR, "摸摸4.png")
        self.pat_queue: list[QPixmap] = []
        self._pat_hold_frames = 0
        self._pat_final_pm = None

        # praise
        self.pm_praise1 = load_pixmap(PRAISE_DIR, "夸夸1.png")
        self.pm_praise2 = load_pixmap(PRAISE_DIR, "夸夸2.png")
        self.pm_praise3 = load_pixmap(PRAISE_DIR, "夸夸3.png")
        self.pm_praise4 = load_pixmap(PRAISE_DIR, "夸夸4.png")
        self.praise_queue: list[QPixmap] = []

        # ============== 气泡 ==============
        self.bubble = QLabel(self)
        self.bubble.setStyleSheet("""
            QLabel {
                background: rgba(255, 255, 255, 220);
                color: #111;
                border-radius: 10px;
                padding: 6px 10px;
                font-size: 14px;
            }
        """)
        self.bubble.hide()
        self.bubble.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        # ============== 初始显示 + 窗口尺寸（按缩放后） ==============
        scaled_w = int(self.pm_normal.width() * PET_SCALE)
        scaled_h = int(self.pm_normal.height() * PET_SCALE)
        self.resize(scaled_w, scaled_h + TOP_MARGIN)
        self.label.move(0, TOP_MARGIN)
        self._show(self.pm_normal)

        # ============== 状态机变量 ==============
        self.mode = "idle"  # idle / click / drag / feed / pat / praise
        self.idle_step = 0
        self.cycle_count = 0
        self.next_blink_cycle = self._pick_next_blink_cycle()
        self.blink_phase = self._BLINK_NONE

        self.click_queue: list[QPixmap] = []
        self.feed_queue: list[QPixmap] = []
        self.drag_step = 0

        # 连点统计
        self.rapid_click_count = 0
        self.last_click_ts = 0.0

        # 拖拽
        self._dragging = False
        self._drag_offset = QPoint()
        self._press_global = None

        # 精力
        self.energy = 100
        self.ENERGY_MAX = 100
        self._energy_awarded_in_action = False

        # ============== 精力条 UI（淡粉气泡版） ==============
        self.energy_bg = QLabel(self)
        self.energy_bg.setStyleSheet("""
        QLabel {
            background: rgba(255, 235, 242, 140);
            border: 1px solid rgba(255, 205, 220, 160);
            border-radius: 10px;
        }
        """)
        self.energy_bg.resize(128, 14)

        self.energy_fill = QLabel(self)
        self.energy_fill.setStyleSheet("""
        QLabel {
            background: rgba(255, 190, 210, 180);
            border-radius: 10px;
        }
        """)
        self.energy_fill.resize(128, 14)

        self.energy_icon = QLabel(self)
        self.energy_icon.setText("♥")
        self.energy_icon.setStyleSheet("""
        QLabel {
            color: rgba(255, 165, 190, 200);
            font-size: 13px;
        }
        """)

        for w in (self.energy_bg, self.energy_fill, self.energy_icon):
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            w.show()

        self._update_energy_bar()

        # ============== 定时器：动画 tick ==============
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_tick)
        self.timer.start(FPS_IDLE_MS)

        # ============== 定时器：精力衰减 ==============
        self.energy_timer = QTimer(self)
        self.energy_timer.timeout.connect(self._decay_energy)
        self.energy_timer.start(60 * 1000)  # 1 分钟

       # ===== idle 闲聊：正常/疲惫 两套 =====
        self.idle_lines_normal = [
            "要记得喝水！",
            "陪我玩嘛~",
            "在干嘛呢？",
            "想你了！",
            "今天吃了什么好吃的？",
            "工作累吗？休息一下吧！",
            "别忘了伸展身体哦！",
            "加油喵！",
            "天气不错，一起散步吧！",
            "喜欢你！",
        ]

        # 疲惫时：求关注 / 委屈 / 难受（你可以随时继续加）
        self.idle_lines_tired = [
            "…可以陪我一下吗",
            "好像被冷落了…",
            "呜…想贴贴",
            "好累…",
            "可以摸摸我吗…",
            "我不想一个人待着",
            "抱抱我…就一下",
            "我是不是做错什么了…",
            "理我理我！",
        ]

        self.bubble_hide_timer = QTimer(self)
        self.bubble_hide_timer.setSingleShot(True)
        self.bubble_hide_timer.timeout.connect(self._hide_bubble)

        self.idle_chat_timer = QTimer(self)
        self.idle_chat_timer.setSingleShot(True)
        self.idle_chat_timer.timeout.connect(self._idle_chat_once)
        self._schedule_next_idle_chat()

        # 初始位置：屏幕右下
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - self.width() - 40, screen.bottom() - self.height() - 80)

        # 初始同步一次 idle 速度（疲惫/正常）
        self._enter_idle()

    # ---------- blink phase constants ----------
    _BLINK_NONE = 0
    _BLINK_UP = 1
    _BLINK_CLOSE = 2
    _BLINK_TIRED = 3

    # ---------- 工具 ----------
    def _is_tired(self) -> bool:
        return self.energy < int(self.ENERGY_MAX * TIRED_RATIO)

    def _apply_idle_speed(self):
        if self.mode != "idle":
            return
        self.timer.setInterval(FPS_IDLE_TIRED_MS if self._is_tired() else FPS_IDLE_MS)

    def _enter_idle(self):
        self.mode = "idle"
        # 清一下疲惫步进，避免回切“卡中间帧”
        if not self._is_tired():
            self.tired_step = 0
        self._apply_idle_speed()

    def _open_context_menu(self, global_pos):
        menu = QMenu(self)

        act_feed = QAction("投喂", self)
        act_feed.triggered.connect(self._on_feed)
        menu.addAction(act_feed)

        act_pat = QAction("摸摸", self)
        act_pat.triggered.connect(self._on_pat)
        menu.addAction(act_pat)

        act_praise = QAction("夸夸", self)
        act_praise.triggered.connect(self._on_praise)
        menu.addAction(act_praise)

        menu.addSeparator()

        act_quit = QAction("残忍离开", self)
        act_quit.triggered.connect(QApplication.quit)
        menu.addAction(act_quit)

        menu.exec(global_pos)

    def _decay_energy(self):
        self.energy = max(0, self.energy - 2)
        self._update_energy_bar()
        self._apply_idle_speed()

        if self.energy <= 15 and self.mode == "idle":
            if not self.bubble.isVisible():
                self._show_bubble("有点累了…")
                self.bubble_hide_timer.start(2000)

    def _update_energy_bar(self):
        bar_w = 128
        bar_h = 14

        pet_x = self.label.x()
        pet_y = self.label.y()
        pet_w = self.label.width()

        x = pet_x + (pet_w - bar_w) // 2
        y = pet_y - bar_h - 8
        if y < 0:
            y = 0

        self.energy_bg.move(x, y)
        self.energy_bg.resize(bar_w, bar_h)

        ratio = self.energy / self.ENERGY_MAX
        fill_w = max(0, int(bar_w * ratio))
        self.energy_fill.move(x, y)
        self.energy_fill.resize(fill_w, bar_h)

        self.energy_icon.move(x - 16, y - 2)

    def _gain_energy(self, amount: int):
        self.energy = min(self.ENERGY_MAX, self.energy + amount)
        self._update_energy_bar()
        self._apply_idle_speed()

        # 条短暂更亮（可选）
        self.energy_bg.setStyleSheet("""
        QLabel {
            background: rgba(255, 235, 242, 200);
            border: 1px solid rgba(255, 205, 220, 200);
            border-radius: 10px;
        }
        """)
        QTimer.singleShot(1200, self._reset_energy_bar_style)

    def _reset_energy_bar_style(self):
        self.energy_bg.setStyleSheet("""
        QLabel {
            background: rgba(255, 235, 242, 140);
            border: 1px solid rgba(255, 205, 220, 160);
            border-radius: 10px;
        }
        """)

    def _show(self, pm: QPixmap):
        scaled = pm.scaled(
            int(pm.width() * PET_SCALE),
            int(pm.height() * PET_SCALE),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.label.setPixmap(scaled)
        self.label.resize(scaled.size())

    def _show_bubble(self, text: str):
        self.bubble.setText(text)
        self.bubble.adjustSize()

        pet_x = self.label.x()
        pet_y = self.label.y()
        pet_w = self.label.width()

        x = pet_x + (pet_w - self.bubble.width()) // 2
        y = pet_y - self.bubble.height() - 6

        x += BUBBLE_OFFSET_X
        y += BUBBLE_OFFSET_Y

        if x < 0:
            x = 0
        if y < 0:
            y = 0

        self.bubble.move(x, y)
        self.bubble.show()

    def _hide_bubble(self):
        self.bubble.hide()

    def _pick_next_blink_cycle(self) -> int:
        return random.randint(BLINK_AFTER_CYCLES_MIN, BLINK_AFTER_CYCLES_MAX)

    # ---------- idle ----------
    def _tick_idle(self):
        # ===== 疲惫模式：疲惫1-2-3循环，穿插“眨眼（疲惫）”单帧 =====
        if self._is_tired():
            if self.blink_phase == self._BLINK_TIRED:
                self._show(self.pm_blink_tired)
                self.blink_phase = self._BLINK_NONE
                return

            if self.tired_step == 0:
                self._show(self.pm_tired1)
                self.tired_step = 1
            elif self.tired_step == 1:
                self._show(self.pm_tired2)
                self.tired_step = 2
            else:
                self._show(self.pm_tired3)
                self.tired_step = 0

                self.cycle_count += 1
                if self.cycle_count >= self.next_blink_cycle:
                    self.blink_phase = self._BLINK_TIRED
                    self.cycle_count = 0
                    self.next_blink_cycle = self._pick_next_blink_cycle()
            return

        # ===== 正常模式：眨眼两帧 + 摆动循环 =====
        if self.blink_phase == self._BLINK_UP:
            self._show(self.pm_blink_up)
            self.blink_phase = self._BLINK_CLOSE
            return
        if self.blink_phase == self._BLINK_CLOSE:
            self._show(self.pm_blink_close)
            self.blink_phase = self._BLINK_NONE
            return

        if self.idle_step == 0:
            self._show(self.pm_normal)
            self.idle_step = 1
        elif self.idle_step == 1:
            self._show(self.pm_sway1)
            self.idle_step = 2
        elif self.idle_step == 2:
            self._show(self.pm_normal)
            self.idle_step = 3
        else:
            self._show(self.pm_sway2)
            self.idle_step = 0

            self.cycle_count += 1
            if self.cycle_count >= self.next_blink_cycle:
                self.blink_phase = self._BLINK_UP
                self.cycle_count = 0
                self.next_blink_cycle = self._pick_next_blink_cycle()

    # ---------- click ----------
    def _start_click_animation(self, is_special: bool):
        self.mode = "click"
        self.bubble_hide_timer.stop()
        self._hide_bubble()

        self.click_queue.clear()
        self.timer.setInterval(FPS_CLICK_MS)

        if is_special:
            hold3_frames = max(1, CLICK3_HOLD_MS // FPS_CLICK_MS)
            self.click_queue.append(self.pm_click1)
            self.click_queue.extend([self.pm_click3] * hold3_frames)
            self.click_queue.append(self.pm_normal)
        else:
            hold2_frames = max(1, CLICK2_HOLD_MS // FPS_CLICK_MS)
            self.click_queue.append(self.pm_click1)
            self.click_queue.extend([self.pm_click2] * hold2_frames)

        self._tick_click()

    def _tick_click(self):
        if not self.click_queue:
            self._hide_bubble()
            self._enter_idle()
            return

        pm = self.click_queue.pop(0)
        self._show(pm)

        if pm.cacheKey() == self.pm_click2.cacheKey():
            self._show_bubble("还要！")
        elif pm.cacheKey() == self.pm_click3.cacheKey():
            self._show_bubble("不许一直玩我！")
        else:
            self._hide_bubble()

    # ---------- drag ----------
    def _tick_drag(self):
        if self.drag_step == 0:
            self._show(self.pm_drag1)
            self.drag_step = 1
        else:
            self._show(self.pm_drag2)
            self.drag_step = 0

    # ---------- tick ----------
    def on_tick(self):
        if self.mode == "idle":
            self._tick_idle()
        elif self.mode == "click":
            self._tick_click()
        elif self.mode == "feed":
            self._tick_feed()
        elif self.mode == "pat":
            self._tick_pat()
        elif self.mode == "praise":
            self._tick_praise()
        else:
            self._tick_drag()

    # ---------- feed ----------
    def _on_feed(self):
        self._start_feed_animation()

    def _start_feed_animation(self):
        self._energy_awarded_in_action = False
        self.mode = "feed"
        self.feed_queue.clear()

        self.bubble_hide_timer.stop()
        self._hide_bubble()

        self.timer.setInterval(400)

        self.feed_queue.append(self.pm_normal)
        self.feed_queue.append(self.pm_feed1)

        for _ in range(4):
            self.feed_queue.append(self.pm_feed2)
            self.feed_queue.append(self.pm_feed3)

        self.feed_queue.append(self.pm_feed4)

        hold_frames = max(1, 3000 // 400)
        self.feed_queue.extend([self.pm_feed5] * hold_frames)

        self._tick_feed()

    def _tick_feed(self):
        if not self.feed_queue:
            self._hide_bubble()
            self._enter_idle()
            return

        pm = self.feed_queue.pop(0)
        self._show(pm)

        if pm.cacheKey() == self.pm_feed5.cacheKey():
            self._show_bubble("呀咪呀咪！")
            if not self._energy_awarded_in_action:
                self._gain_energy(12)
                self._energy_awarded_in_action = True

    # ---------- pat ----------
    def _on_pat(self):
        self._start_pat_animation()

    def _start_pat_animation(self):
        self._energy_awarded_in_action = False
        self.mode = "pat"
        self.pat_queue.clear()

        self.bubble_hide_timer.stop()
        self._hide_bubble()

        PAT_FPS_MS = 160
        self.timer.setInterval(PAT_FPS_MS)

        loops = random.randint(4, 8)
        for _ in range(loops):
            self.pat_queue.append(self.pm_pat1)
            self.pat_queue.append(self.pm_pat2)

        self._pat_final_pm = random.choice([self.pm_pat3, self.pm_pat4])

        hold_ms = 3500
        hold_frames = max(1, hold_ms // PAT_FPS_MS)
        self._pat_hold_frames = hold_frames
        self.pat_queue.extend([self._pat_final_pm] * hold_frames)

        self._tick_pat()

    def _tick_pat(self):
        if not self.pat_queue:
            self._hide_bubble()
            self._enter_idle()
            return

        pm = self.pat_queue.pop(0)
        self._show(pm)

        in_final_hold = (len(self.pat_queue) <= self._pat_hold_frames)
        if in_final_hold and self._pat_final_pm is not None and pm.cacheKey() == self._pat_final_pm.cacheKey():
            if self._pat_final_pm.cacheKey() == self.pm_pat3.cacheKey():
                self._show_bubble("好酥糊~")
            else:
                self._show_bubble("再陪陪我…")

            if not self._energy_awarded_in_action:
                self._gain_energy(12)
                self._energy_awarded_in_action = True
        else:
            self._hide_bubble()

    # ---------- praise ----------
    def _on_praise(self):
        self._start_praise_animation()

    def _start_praise_animation(self):
        self._energy_awarded_in_action = False
        self.mode = "praise"
        self.praise_queue.clear()

        self.bubble_hide_timer.stop()
        self._hide_bubble()

        PRAISE_FPS_MS = 250
        self.timer.setInterval(PRAISE_FPS_MS)

        self.praise_queue.append(self.pm_praise1)
        self.praise_queue.append(self.pm_praise2)
        self.praise_queue.append(self.pm_praise1)
        self.praise_queue.append(self.pm_praise3)

        hold_ms = 3200
        hold_frames = max(1, hold_ms // PRAISE_FPS_MS)
        self.praise_queue.extend([self.pm_praise4] * hold_frames)

        self._tick_praise()

    def _tick_praise(self):
        if not self.praise_queue:
            self._hide_bubble()
            self._enter_idle()
            return

        pm = self.praise_queue.pop(0)
        self._show(pm)

        if pm.cacheKey() == self.pm_praise4.cacheKey():
            self._show_bubble("真、真的吗…")
            if not self._energy_awarded_in_action:
                self._gain_energy(10)
                self._energy_awarded_in_action = True
        else:
            self._hide_bubble()

    # ---------- idle 闲聊 ----------
    def _schedule_next_idle_chat(self):
        delay = random.randint(IDLE_CHAT_MIN_MS, IDLE_CHAT_MAX_MS)
        self.idle_chat_timer.start(delay)

  
    def _idle_chat_once(self):
        if self.mode == "idle" and (not self._dragging):
            lines = self.idle_lines_tired if self._is_tired() else self.idle_lines_normal
            if lines:
                self._show_bubble(random.choice(lines))
                self.bubble_hide_timer.start(IDLE_CHAT_DURATION_MS)

        self._schedule_next_idle_chat()

    

    # ---------- 鼠标 ----------
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            now = time.time()
            if now - self.last_click_ts <= RAPID_CLICK_WINDOW_SEC:
                self.rapid_click_count += 1
            else:
                self.rapid_click_count = 1
            self.last_click_ts = now

            is_special = (self.rapid_click_count >= RAPID_CLICK_THRESHOLD)
            if is_special:
                self.rapid_click_count = 0

            self._start_click_animation(is_special=is_special)


            self._dragging = True
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._press_global = event.globalPosition().toPoint()

        elif event.button() == Qt.MouseButton.RightButton:
            self._open_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if self._dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            self.move(event.globalPosition().toPoint() - self._drag_offset)

            if self._press_global is not None:
                cur = event.globalPosition().toPoint()
                dist = (cur - self._press_global).manhattanLength()
                if dist >= 4:
                    if self.mode != "drag":
                        self.mode = "drag"
                        self.drag_step = 0
                        self._show_bubble(random.choice(["放开我！", "呜——", "救命！"]))
                        self.timer.setInterval(FPS_DRAG_MS)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self._press_global = None

            if self.mode == "drag":
                self._hide_bubble()
                self._enter_idle()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    pet = DesktopPet()
    pet.show()
    sys.exit(app.exec())
