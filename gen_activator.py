# -*- coding: utf-8 -*-
"""一次性激活器生成器（CLI，仅作者使用）。
用法:
  python gen_activator.py --mac AA:BB:CC:DD:EE:FF --tier full --duration 365
  python gen_activator.py --mac AA:BB:CC:DD:EE:FF --tier cultivate --duration per --exe
参数:
  --mac      客户网卡 MAC（绑定到该机器）
  --tier     full=全功能 / cultivate=仅培育
  --duration 1=体验1天 / 7=7天 / 365=365天 / per=永久
  --exe      同时打包一个一次性激活器 EXE（内含卡密，激活后自删）
"""
import argparse
import os
import subprocess
import sys

import license as L


def build_activator_exe(card, mac, out_name):
    """生成一个内含卡密的一次性激活器 bundle 并打包为 EXE。"""
    bundle = r"""# -*- coding: utf-8 -*-
import os, sys, subprocess
CARD = %(card)r
import license as L
import auth

def self_destruct():
    if getattr(sys, "frozen", False):
        subprocess.Popen(
            ["cmd", "/c", "timeout /t 2 >nul & del /f /q \\"" + sys.executable + "\\""],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    else:
        try:
            os.remove(os.path.abspath(__file__))
        except OSError:
            pass

def main():
    if auth.check_license() != "none":
        print("本机已激活，无需重复激活")
        self_destruct()
        return
    ok, msg = L.activate(CARD)
    print(msg)
    if ok:
        print("卡密:", CARD)
        self_destruct()
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
""" % {"card": card}
    src = os.path.join(os.getcwd(), "_act_bundle.py")
    with open(src, "w", encoding="utf-8") as f:
        f.write(bundle)
    py = sys.executable
    cmd = [
        py, "-m", "PyInstaller", "--noconfirm", "--onefile", "--windowed",
        "--name", out_name, "--paths", os.getcwd(), src,
    ]
    print("打包中...")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if os.path.exists(os.path.join("dist", out_name + ".exe")):
        print("激活器已生成:", os.path.join("dist", out_name + ".exe"))
    else:
        print("打包失败:")
        print(r.stdout[-2000:] if r.stdout else "")
        print(r.stderr[-2000:] if r.stderr else "")
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(prog="gen_activator", description="生成一次性激活卡密")
    ap.add_argument("--mac", required=True, help="客户MAC，如 AA:BB:CC:DD:EE:FF")
    ap.add_argument("--tier", required=True, choices=["full", "cultivate"], help="规格：全功能/仅培育")
    ap.add_argument("--duration", required=True, choices=["1", "7", "365", "per"], help="有效期：1=1天/7=7天/365=365天/per=永久")
    ap.add_argument("--exe", action="store_true", help="同时打包一次性激活器EXE")
    a = ap.parse_args()

    card, ctype, expire = L.gen_card(a.mac, a.tier, a.duration)
    print("=== 卡密 ===")
    print(card)
    print("绑定MAC:", a.mac)
    print("规格:", ctype)
    print("到期:", expire.strftime("%Y-%m-%d"))

    if a.exe:
        short = a.mac.replace(":", "").replace("-", "")[-6:]
        build_activator_exe(card, a.mac, "激活器_%s" % short)


if __name__ == "__main__":
    main()
