# -*- coding: utf-8 -*-
"""一次性激活器（GUI，买家用）：输入卡密 -> 校验多信息 -> 激活 -> 删除自己。"""
import os
import subprocess
import sys
from datetime import datetime

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QMessageBox)

import license as L


class ActWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("卡布西游脱机助手 激活器")
        self.setFixedSize(520, 220)
        w = QWidget()
        lay = QVBoxLayout(w)

        lay.addWidget(QLabel("请输入激活卡密："))
        self.card_input = QLineEdit()
        self.card_input.setPlaceholderText("KABU-FULL-365D-2027xxxx-xxxx")
        lay.addWidget(self.card_input)

        self.act = QPushButton("立即激活")
        self.act.clicked.connect(self.do_activate)
        lay.addWidget(self.act)

        self.tip = QLabel("激活完成后本程序将自动删除。")
        lay.addWidget(self.tip)

        self.setCentralWidget(w)

    def self_destruct(self):
        if getattr(sys, "frozen", False):
            subprocess.Popen(
                ["cmd", "/c", 'timeout /t 2 >nul & del /f /q "%s"' % sys.executable],
                creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            try:
                os.remove(os.path.abspath(__file__))
            except OSError:
                pass

    def do_activate(self):
        card = self.card_input.text().strip()
        if not card:
            QMessageBox.warning(self, "错误", "请输入激活卡密")
            return
        # 严格校验：格式/规格/有效期/签名/MAC绑定，防用户乱改卡密
        p = L.parse_card(card)
        if not p:
            QMessageBox.warning(self, "激活失败", "卡密格式错误，请核对卡密，勿自行修改")
            return
        card_type, expire, _ = p
        if expire.date() < datetime.now().date():
            QMessageBox.warning(self, "激活失败", "卡密已过期")
            return
        ok, msg = L.activate(card)
        if ok:
            QMessageBox.information(self, "激活成功", "授权已写入，程序即将退出并自动删除。")
            self.self_destruct()
            QApplication.quit()
        else:
            QMessageBox.warning(self, "激活失败", "卡密与当前机器不匹配或签名无效，请勿修改卡密")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ActWindow()
    win.show()
    sys.exit(app.exec_())
