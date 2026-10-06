# -*- coding: utf-8 -*-
"""激活器生成器（GUI，作者用）：输入 MAC/规格/有效期 -> 生成卡密，可一键打包一次性激活器 EXE。"""
import os
import subprocess
import sys

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QComboBox, QPushButton, QMessageBox, QTextEdit)

import license as L


class GenWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("激活器生成器（作者）")
        self.setFixedSize(600, 400)
        w = QWidget()
        lay = QVBoxLayout(w)

        mh = QHBoxLayout()
        mh.addWidget(QLabel("客户机器码:"))
        self.mac = QLineEdit()
        self.mac.setPlaceholderText("如 MZJJ6HPRMDCQ（主程序未激活时显示）")
        mh.addWidget(self.mac)
        lay.addLayout(mh)

        sh = QHBoxLayout()
        sh.addWidget(QLabel("规格:"))
        self.tier = QComboBox()
        self.tier.addItems(["全功能 (full)", "仅培育 (cultivate)"])
        sh.addWidget(self.tier)
        lay.addLayout(sh)

        dh = QHBoxLayout()
        dh.addWidget(QLabel("有效期:"))
        self.dur = QComboBox()
        self.dur.addItems(["体验1天 (1)", "7天 (7)", "365天 (365)", "永久 (per)"])
        dh.addWidget(self.dur)
        lay.addLayout(dh)

        self.gen = QPushButton("生成卡密")
        self.gen.clicked.connect(self.do_gen)
        lay.addWidget(self.gen)

        self.out = QTextEdit()
        self.out.setReadOnly(True)
        lay.addWidget(self.out)

        hb = QHBoxLayout()
        self.copy = QPushButton("复制卡密")
        self.copy.clicked.connect(self.do_copy)
        hb.addWidget(self.copy)
        self.pack = QPushButton("打包一次性激活器 EXE")
        self.pack.clicked.connect(self.do_pack)
        hb.addWidget(self.pack)
        lay.addLayout(hb)

        self.card = ""
        self.setCentralWidget(w)

    def _tier(self):
        return "full" if self.tier.currentIndex() == 0 else "cultivate"

    def _dur(self):
        return ["1", "7", "365", "per"][self.dur.currentIndex()]

    def do_gen(self):
        code = self.mac.text().strip()
        if not code:
            QMessageBox.warning(self, "错误", "请输入客户机器码")
            return
        try:
            mac = L.code_to_mac(code)
            card, ct, ex = L.gen_card(mac, self._tier(), self._dur())
        except ValueError as e:
            QMessageBox.warning(self, "错误", str(e))
            return
        self.card = card
        self.out.setText("机器码: %s\n还原MAC: %s\n\n卡密: %s\n规格: %s\n到期: %s" %
                         (code, mac, card, ct, ex.strftime("%Y-%m-%d")))

    def do_copy(self):
        if not self.card:
            QMessageBox.warning(self, "错误", "请先生成卡密")
            return
        QApplication.clipboard().setText(self.card)
        QMessageBox.information(self, "成功", "卡密已复制到剪贴板")

    def do_pack(self):
        if not self.card:
            QMessageBox.warning(self, "错误", "请先生成卡密")
            return
        py = sys.executable
        r = subprocess.run(
            [py, "-m", "PyInstaller", "--noconfirm", "--onefile", "--windowed",
             "--name", "激活器", "--paths", os.getcwd(), "activate_gui.py"],
            capture_output=True, text=True)
        exe = os.path.join("dist", "激活器.exe")
        if os.path.exists(exe):
            QMessageBox.information(self, "成功", "已生成 %s" % exe)
        else:
            QMessageBox.warning(self, "失败", r.stderr[-600:] or r.stdout[-600:])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = GenWindow()
    win.show()
    sys.exit(app.exec_())
