# -*- coding: utf-8 -*-
"""一次性激活器：校验多信息(MAC绑定/签名/有效期/规格) -> 覆盖写授权 -> 自删。
支持同机二次激活：即使本机已有授权（含已过期），只要新卡校验通过即覆盖换档。
用法: python activate_self.py KABU-...   或双击打包后的 EXE。
"""
import os
import subprocess
import sys

import license as L


def self_destruct():
    if getattr(sys, "frozen", False):
        subprocess.Popen(
            ["cmd", "/c", 'timeout /t 2 >nul & del /f /q "%s"' % sys.executable],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    else:
        try:
            os.remove(os.path.abspath(__file__))
        except OSError:
            pass


def main():
    card = ""
    if len(sys.argv) > 1:
        card = sys.argv[1]
    else:
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "license.txt"), encoding="utf-8") as f:
                card = f.read().strip()
        except OSError:
            pass
    if not card:
        print("用法: activate_self.py KABU-卡密，或双击 EXE")
        sys.exit(1)

    ok, msg = L.activate(card)  # 校验多信息并以本机 MAC 绑定，通过则覆盖写授权
    print(msg)
    if not ok:
        sys.exit(1)
    self_destruct()


if __name__ == "__main__":
    main()
