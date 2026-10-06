# -*- coding: utf-8 -*-
"""一次性激活器（GUI，买家用）：输入卡密 -> 校验多信息 -> 激活 -> 删除自己。"""
import os
import subprocess
import sys

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
        ok, msg = L.activate(card)
        if ok:
            QMessageBox.information(self, "激活成功", "授权已写入，程序即将退出并自动删除。")
            self.self_destruct()
            QApplication.quit()
        else:
            QMessageBox.warning(self, "激活失败", msg)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ActWindow()
    win.show()
    sys.exit(app.exec_())
