# -*- coding: utf-8 -*-
"""龙腾诊断：进副本→查进度→依次发操作1/4，dump回包判断服务端出战状态。"""
import sys, os, time
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
base = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, base)
from tools_for_4399.kbxy import KabuClient, HOST
import kabu_login

def cb(m):
    print(m, flush=True)

acc = (sys.argv[1], sys.argv[2]) if len(sys.argv) >= 3 else ("zvuk5985", "ispwu45612")
print(f"=== 登录 {acc[0]} ===", flush=True)
cookies = kabu_login.login_4399(acc[0], acc[1], log=cb)
if not cookies:
    print("!!! 登录失败", flush=True)
    sys.exit(1)
auth = kabu_login.get_auth_string(cookies, log=cb)
client = KabuClient(HOST, log_callback=cb)
client.connect()
client.login(auth, timeout=30, server_id=None, server_mode="auto")
time.sleep(2)

print("=== 进龙腾副本 ===", flush=True)
client.dragon_enter_copy()
print("--- 进副本后等待10秒观察抽取 ---", flush=True)
time.sleep(10)
for i in range(3):
    print(f"--- 查进度 #{i+1} ---", flush=True)
    client.dragon_query_progress()
    time.sleep(3)
    print("choice_monster=", client.dragon_state.get("choice_monster"),
          "next_combat_index=", client.dragon_state.get("next_combat_index"),
          "current_combat=", client.dragon_state.get("current_combat"),
          "in_dragon=", client.dragon_state.get("in_dragon"), flush=True)

print("=== 发操作1 出战查询 [1,0,0] ===", flush=True)
client.send_cmd(1186184, 20, [1, 0, 0])
time.sleep(3)

print("=== 发操作4 查看候选 [4,0,0] ===", flush=True)
client.send_cmd(1186184, 20, [4, 0, 0])
time.sleep(3)

print("=== 再查进度 ===", flush=True)
client.dragon_query_progress()
time.sleep(3)

print("=== 发战斗 [2,1,0] ===", flush=True)
client.send_cmd(1186184, 20, [2, 1, 0])
time.sleep(4)

print("=== DIAG 结束 ===", flush=True)
try:
    client.close()
except Exception:
    pass
print("DONE", flush=True)
