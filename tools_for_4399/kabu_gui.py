#!/usr/bin/env python3
"""卡布西游脱机助手 GUI（浅色清新主题，tkinter 原生，无外部依赖）。
功能：龙腾盛会自动连打 / 培育仓状态 / 抽奖回显 / 日志实时显示与导出。
布局：左侧功能区、右侧日志区（靠右），机械式按钮（点击下沉2px、阴影内翻、1s 复原）。
"""
import json
import os
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools_for_4399.kbxy import KabuClient, HOST  # noqa: E402
import login_4399  # noqa: E402

# ---- 浅色清新配色 ----
BG = "#f3f6fa"
CARD = "#ffffff"
TEXT = "#2b3440"
SUB = "#8a94a6"
ACCENT = "#4c8bf5"
ACCENT_DOWN = "#3b76d9"
BORDER = "#e3e8ef"
OK = "#2f9e63"
WARN = "#d99a2b"
ERR = "#e05c5c"
INFO = "#3a6ea5"
LOGG_BG = "#fbfcfe"
LOGG_FG = "#3a4553"
R = 10  # 圆角半径


def _hex_shade(hexc: str, factor: float) -> str:
    r = max(0, min(255, int(int(hexc[1:3], 16) * factor)))
    g = max(0, min(255, int(int(hexc[3:5], 16) * factor)))
    b = max(0, min(255, int(int(hexc[5:7], 16) * factor)))
    return f"#{r:02x}{g:02x}{b:02x}"


class MechButton(tk.Canvas):
    """机械式按钮：圆角、按下时下沉2px + 阴影内翻，1s 后复原。"""

    def __init__(self, parent, text, command, bg=ACCENT, fg="#ffffff",
                 width=150, height=38, font=("Microsoft YaHei UI", 11, "bold")):
        self._bg = bg
        self._fg = fg
        self._text = text
        self._cmd = command
        self._pressed = False
        super().__init__(parent, width=width, height=height, bg=parent["bg"],
                         highlightthickness=0, bd=0)
        self._font = font
        self._w = width
        self._h = height
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Enter>", lambda e: self._draw(shade=1.06))
        self.bind("<Leave>", lambda e: self._draw(shade=1.0))
        self._draw()

    def _draw(self, shade: float = 1.0, down: bool = False):
        self.delete("all")
        if down:
            y_off = 2  # 下沉2px
            body = _hex_shade(self._bg, 0.9)
            sh = _hex_shade(self._bg, 0.75)
        else:
            y_off = 0
            body = _hex_shade(self._bg, shade)
            sh = _hex_shade(self._bg, 0.55)
        # 阴影（内翻：先画深色底再盖高亮）
        self.create_round_rectangle(2, 3 + y_off, self._w, self._h + 1 + y_off, r=R,
                                    fill=sh, outline="")
        self.create_round_rectangle(2, y_off, self._w - 2, self._h - 2 + y_off, r=R,
                                    fill=body, outline="")
        self.create_text(self._w / 2, self._h / 2 + y_off, text=self._text,
                         fill=self._fg, font=self._font)

    def create_round_rectangle(self, x1, y1, x2, y2, r, **kw):
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
               x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return self.create_polygon(pts, smooth=True, **kw)

    def _on_press(self, _e):
        self._pressed = True
        self._draw(down=True)
        if self._cmd:
            self._cmd()

    def _on_release(self, _e):
        self._pressed = False
        self._draw(down=True)
        # 1s 后复原
        self.after(1000, lambda: self._draw())

    def set(self, text=None, bg=None, fg=None):
        if text:
            self._text = text
        if bg:
            self._bg = bg
        if fg:
            self._fg = fg
        self._draw()


class KabuGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.log_q: "queue.Queue[str]" = queue.Queue()
        self.stop_flag = threading.Event()
        self.thread: "threading.Thread | None" = None
        self.c: "KabuClient | None" = None
        root.title("卡布西游脱机助手")
        root.geometry("960x620")
        root.minsize(880, 560)
        root.configure(bg=BG)
        try:
            ico = os.path.join(ROOT, "kbxy.ico")
            if os.path.exists(ico):
                root.iconbitmap(ico)
        except Exception:
            pass
        self._build()
        self.root.after(180, self._drain_logs)

    # ---------- 布局 ----------
    def _build(self):
        pad = 16
        # 顶栏
        top = tk.Frame(self.root, bg=CARD)
        top.pack(fill="x", padx=pad, pady=(pad, 8))
        self.title_lbl = tk.Label(top, text="卡布西游脱机助手", bg=CARD, fg=TEXT,
                                  font=("Microsoft YaHei UI", 16, "bold"))
        self.title_lbl.pack(side="left", padx=12, pady=10)
        self.acct_lbl = tk.Label(top, text="账号：未登录", bg=CARD, fg=SUB,
                                 font=("Microsoft YaHei UI", 10))
        self.acct_lbl.pack(side="left", padx=8)
        self.export_btn = MechButton(top, "导出日志", self._export_log, bg=ACCENT,
                                     width=104, height=34)
        self.export_btn.pack(side="right", padx=12, pady=8)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=pad, pady=(0, pad))

        # 左侧功能区
        self.left = tk.Frame(body, bg=CARD)
        self.left.pack(side="left", fill="y", padx=(0, 8))

        self._build_login()
        self._build_dragon()
        self._build_peiyu()

        # 右侧日志区（靠右）
        self.right = tk.Frame(body, bg=CARD)
        self.right.pack(side="right", fill="both", expand=True)
        tk.Label(self.right, text="运行日志", bg=CARD, fg=SUB,
                 font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w", padx=12, pady=(10, 4))
        logframe = tk.Frame(self.right, bg=LOGG_BG)
        logframe.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.log_txt = tk.Text(logframe, bg=LOGG_BG, fg=LOGG_FG, wrap="none",
                               state="disabled", font=("Consolas", 10),
                               relief="flat", bd=0, padx=10, pady=10)
        sb = tk.Scrollbar(logframe, command=self.log_txt.yview)
        self.log_txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log_txt.pack(side="left", fill="both", expand=True)
        self.log_txt.tag_configure("INFO", foreground=INFO)
        self.log_txt.tag_configure("WRAN", foreground=WARN)
        self.log_txt.tag_configure("ERROR", foreground=ERR)
        self.log_txt.tag_configure("USER", foreground=OK, font=("Consolas", 10, "bold"))
        self.log_txt.tag_configure("BATTLE", foreground=TEXT)
        self.log_txt.tag_configure("OK", foreground=OK)
        self.log_txt.tag_configure("DEBUG", foreground=SUB)

        # 状态栏
        status = tk.Frame(self.root, bg=CARD)
        status.pack(fill="x", padx=pad, pady=(0, pad))
        self.status_lbl = tk.Label(status, text="就绪", bg=CARD, fg=SUB,
                                   font=("Microsoft YaHei UI", 10))
        self.status_lbl.pack(side="left", padx=12, pady=8)
        self.state_lbl = tk.Label(status, text="", bg=CARD, fg=OK,
                                  font=("Microsoft YaHei UI", 10, "bold"))
        self.state_lbl.pack(side="right", padx=12)

    def _card_title(self, text):
        return tk.Label(self.left, text=text, bg=CARD, fg=SUB,
                        font=("Microsoft YaHei UI", 10, "bold"))

    def _build_login(self):
        self._card_title("登录").pack(anchor="w", padx=16, pady=(12, 4))
        row = tk.Frame(self.left, bg=CARD)
        row.pack(fill="x", padx=16, pady=4)
        self.login_btn = MechButton(row, "一键登录", self._do_login, width=120, height=36)
        self.login_btn.pack(side="left")
        self.reload_btn = MechButton(row, "刷新凭证", self._refresh_cred, bg=SUB,
                                     width=120, height=36)
        self.reload_btn.pack(side="left", padx=(10, 0))

    def _build_dragon(self):
        self._card_title("龙腾盛会自动连打").pack(anchor="w", padx=16, pady=(16, 4))
        row1 = tk.Frame(self.left, bg=CARD)
        row1.pack(fill="x", padx=16, pady=4)
        self.start_btn = MechButton(row1, "开始自动连打", self._start_dragon, width=150, height=38)
        self.start_btn.pack(side="left")
        self.stop_btn = MechButton(row1, "停止", self._stop_dragon, bg=ERR,
                                   width=88, height=38)
        self.stop_btn.pack(side="left", padx=(10, 0))
        row2 = tk.Frame(self.left, bg=CARD)
        row2.pack(fill="x", padx=16, pady=4)
        self.enter_btn = MechButton(row2, "进副本", self._enter_copy, bg=SUB,
                                    width=104, height=34)
        self.enter_btn.pack(side="left")
        self.progress_btn = MechButton(row2, "查询进度", self._query_progress, bg=SUB,
                                       width=104, height=34)
        self.progress_btn.pack(side="left", padx=(10, 0))
        row2b = tk.Frame(self.left, bg=CARD)
        row2b.pack(fill="x", padx=16, pady=4)
        self.revive_on = False
        self.revive_btn = MechButton(row2b, "卡布币复活：关", self._toggle_revive, bg=SUB,
                                     width=160, height=34)
        self.revive_btn.pack(side="left")
        self.dragon_status = tk.Label(self.left, text="进度：还没进副本", bg=CARD, fg=TEXT,
                                      font=("Microsoft YaHei UI", 10))
        self.dragon_status.pack(anchor="w", padx=16, pady=6)
        self.reward_lbl = tk.Label(self.left, text="抽奖：暂无", bg=CARD, fg=SUB,
                                   font=("Microsoft YaHei UI", 10))
        self.reward_lbl.pack(anchor="w", padx=16, pady=(0, 12))

    def _build_peiyu(self):
        self._card_title("培育仓").pack(anchor="w", padx=16, pady=(16, 4))
        row = tk.Frame(self.left, bg=CARD)
        row.pack(fill="x", padx=16, pady=4)
        self.peiyu_btn = MechButton(row, "查询培育状态", self._query_peiyu, bg=SUB,
                                    width=140, height=36)
        self.peiyu_btn.pack(side="left")
        self.peiyu_status = tk.Label(self.left, text="培育：未查询", bg=CARD, fg=TEXT,
                                     font=("Microsoft YaHei UI", 10))
        self.peiyu_status.pack(anchor="w", padx=16, pady=6)

    # ---------- 日志 ----------
    def push_log(self, msg: str, level: str = "INFO"):
        self.log_q.put(f"[{level}] {msg}")

    def _drain_logs(self):
        try:
            while True:
                line = self.log_q.get_nowait()
                self._append_log(line)
        except queue.Empty:
            pass
        self.root.after(180, self._drain_logs)

    def _append_log(self, line: str):
        self.log_txt.configure(state="normal")
        tag = "INFO"
        if "[ERROR]" in line:
            tag = "ERROR"
        elif "[WRAN]" in line:
            tag = "WRAN"
        elif "[USER]" in line:
            tag = "USER"
        elif "[BATTLE]" in line:
            tag = "BATTLE"
        elif "[OK]" in line:
            tag = "OK"
        self.log_txt.insert("end", time.strftime("%H:%M:%S ") + line + "\n", tag)
        self.log_txt.see("end")
        self.log_txt.configure(state="disabled")

    def _export_log(self):
        path = filedialog.asksaveasfilename(
            title="导出日志", defaultextension=".txt", initialfile="kabu_log.txt")
        if not path:
            return
        content = self.log_txt.get("1.0", "end-1c")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        messagebox.showinfo("导出完成", f"日志已导出到：\n{path}")

    def set_status(self, text: str, color=SUB):
        self.status_lbl.configure(text=text, fg=color)

    # ---------- 凭证 / 登录 ----------
    def _resolve_token(self) -> str:
        cred = login_4399.load_credentials()
        if not cred:
            self.push_log("credentials.json 不存在或无内容", "ERROR")
            return ""
        return cred.get("token") or cred.get("auth_string") or ""

    def _get_client(self) -> "KabuClient":
        if self.c and self.c.connected:
            return self.c
        self.c = KabuClient(HOST, log_callback=self.push_log)
        if not self.c.connect():
            self.push_log("连接游戏服务器失败", "ERROR")
            return None
        return self.c

    def _do_login(self):
        if self.thread and self.thread.is_alive():
            self.push_log("已有任务运行中", "WRAN")
            return
        def work():
            token = self._resolve_token()
            if not token:
                self.push_log("未找到登录凭证，请点「刷新凭证」抓取 4399 cookie 后重试", "ERROR")
                return
            c = self._get_client()
            if not c:
                return
            try:
                ok = c.login(token)
            except Exception as e:
                self.push_log(f"登录异常（凭证可能过期）：{e}。请点「刷新凭证」重新抓取", "ERROR")
                return
            if ok:
                self.push_log("登录成功", "OK")
                self.root.after(0, lambda: self.acct_lbl.configure(
                    text=f"账号：{getattr(c, 'nickname', '') or '已登录'}"))
            else:
                self.push_log("登录失败：token 无效或超时，请点「刷新凭证」", "ERROR")
        threading.Thread(target=work, daemon=True).start()

    def _refresh_cred(self):
        msg = ("请用浏览器登录 4399（卡布西游），复制 cookie 后运行：\n"
               "python login_4399.py --cookie \"<你的cookie>\" --save\n"
               "或提供 --token。保存后点「一键登录」。")
        messagebox.showinfo("刷新凭证", msg)

    # ---------- 龙腾 ----------
    def _start_dragon(self):
        if self.thread and self.thread.is_alive():
            self.push_log("自动连打已在运行", "WRAN")
            return
        self.stop_flag.clear()
        self.start_btn.set(text="连打中...", bg=OK)
        self.push_log("启动龙腾自动连打", "USER")
        self.thread = threading.Thread(target=self._dragon_loop, daemon=True)
        self.thread.start()

    def _stop_dragon(self):
        self.stop_flag.set()
        self.push_log("请求停止自动连打", "WRAN")

    def _toggle_revive(self):
        self.revive_on = not self.revive_on
        if self.revive_on:
            self.revive_btn.set(text="卡布币复活：开", bg=OK)
            self.push_log("已开启卡布币自动复活：出战妖怪阵亡时会自动消耗卡布币复活（需要足够的卡布币）", "USER")
        else:
            self.revive_btn.set(text="卡布币复活：关", bg=SUB)
            self.push_log("已关闭卡布币自动复活：出战妖怪阵亡后自动连打会停止，需手动补血/复活", "USER")

    def _dragon_loop(self):
        try:
            token = self._resolve_token()
            if not token:
                self.push_log("未找到登录凭证", "ERROR")
                return
            c = self._get_client()
            if not c:
                return
            if not c.logged_in:
                try:
                    c.login(token)
                except Exception as e:
                    self.push_log(f"登录失败：{e}", "ERROR")
                    return
            self.push_log("登录成功，开始自动连打", "OK")
            c.dragon_state["dragon_auto_revive"] = self.revive_on
            if self.revive_on:
                self.push_log("已按开关开启卡布币自动复活：阵亡时会自动消耗卡布币复活", "USER")
            deadline = time.time() + 1800
            last = -1
            while not self.stop_flag.is_set() and time.time() < deadline:
                try:
                    if c.dragon_state.get("dragon_battle_active"):
                        c.dragon_check_stuck()
                        time.sleep(2)
                        continue
                    if c.dragon_state.get("today_pass", 0) != 0:
                        self.push_log("已经通关啦，自动连打结束", "USER")
                        break
                    c.dragon_auto_start()
                    for _ in range(6):
                        c.dragon_check_stuck()
                        time.sleep(1.5)
                        if c.dragon_state.get("dragon_battle_active"):
                            break
                    stage = c.dragon_state.get("current_stage", 0)
                    if stage != last:
                        last = stage
                        tp = c.dragon_state.get("today_pass", 0)
                        label = "最后的总Boss战" if stage >= 17 else f"第{stage + 1}/17场"
                        done = "已通关" if tp else "还没通关"
                        self.root.after(0, lambda s=label, d=done: self.dragon_status.configure(
                            text=f"进度：{s}，{d}"))
                        self.push_log(f"进度：{s}，{done}", "USER")
                    rw = c.dragon_state.get("dragon_lottery_rewards") or []
                    if rw:
                        names = [c._spirit_name(v) for v in rw if v > 0]
                        shown = "、".join(names) if names else "、".join(map(str, rw))
                        self.root.after(0, lambda s=shown: self.reward_lbl.configure(
                            text=f"抽奖：{s}"))
                except Exception as e:
                    self.push_log(f"连打循环异常：{e}", "ERROR")
                    time.sleep(3)
            self.push_log("自动连打已停止", "WRAN")
        finally:
            self.root.after(0, lambda: self.start_btn.set(text="开始自动连打", bg=ACCENT))

    def _enter_copy(self):
        def work():
            c = self._get_client()
            if not c or not c.logged_in:
                self.push_log("请先一键登录", "WRAN")
                return
            c.dragon_enter_copy()
            self.push_log("已请求进入龙腾副本", "INFO")
        threading.Thread(target=work, daemon=True).start()

    def _query_progress(self):
        def work():
            c = self._get_client()
            if not c or not c.logged_in:
                self.push_log("请先一键登录", "WRAN")
                return
            c.dragon_query_progress()
        threading.Thread(target=work, daemon=True).start()

    # ---------- 培育 ----------
    def _query_peiyu(self):
        def work():
            c = self._get_client()
            if not c or not c.logged_in:
                self.push_log("请先一键登录", "WRAN")
                return
            try:
                c.peiyu_enter_check(0)
                time.sleep(0.8)
                c.peiyu_get_status()
                self.push_log("已查询培育状态", "INFO")
            except Exception as e:
                self.push_log(f"培育查询异常：{e}", "ERROR")
        threading.Thread(target=work, daemon=True).start()


def main():
    root = tk.Tk()
    try:
        KabuGUI(root)
        root.mainloop()
    except Exception as e:
        try:
            messagebox.showerror("启动失败", str(e))
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
