#!/usr/bin/env python3
"""连续自动连打：登录后循环推进龙腾盛会，直到通关(今日已胜)或打满 17 场至终局战。
驱动 dragon_auto_start() 进副本/推进 + dragon_check_stuck() watchdog 心跳兜底发起战斗。
输出最终 stage / today_pass / battle_type 状态到 stdout。"""
import os
import sys
import time
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools_for_4399.kbxy import KabuClient, HOST  # noqa: E402
import login_4399  # noqa: E402


def main() -> int:
    creds = login_4399.load_credentials()

DEADLINE_SEC = 1700  # 约 28 分钟上限


def main() -> int:
    creds = login_4399.load_credentials()
    token = (creds or {}).get("token") or ""
    if not token:
        print("[ERR] credentials.json 无 token", flush=True)
        return 2
    c = KabuClient(HOST)
    if not c.connect():
        print("[ERR] 连接游戏服务器失败", flush=True)
        return 2
    try:
        if not c.login(token):
            print("[ERR] 登录失败：token 可能过期", flush=True)
            return 2
        print("[OK] 登录成功，开始连续自动连打", flush=True)
    except Exception as e:
        print(f"[ERR] 登录异常：{e}", flush=True)
        return 2

    deadline = time.time() + DEADLINE_SEC
    last_stage = -1
    while time.time() < deadline:
        try:
            if c.dragon_state.get("dragon_battle_active"):
                c.dragon_check_stuck()
                time.sleep(3)
                continue
            if c.dragon_state.get("today_pass", 0) != 0:
                print("[通关] 今日已通关，停止连打", flush=True)
                break
            ok = c.dragon_auto_start()
            for _ in range(6):
                c.dragon_check_stuck()
                time.sleep(2)
                if c.dragon_state.get("dragon_battle_active"):
                    break
            stage = c.dragon_state.get("current_stage")
            if stage != last_stage:
                last_stage = stage
                bt = "终局战" if (stage or 0) >= 17 else "普通战"
                print(f"[进度] 第{(stage or 0) + 1}/17 场({bt}) "
                      f"battle_active={c.dragon_state.get('dragon_battle_active')} "
                      f"today_pass={c.dragon_state.get('today_pass')}", flush=True)
        except Exception as e:
            print(f"[WRAN] 循环异常：{e}", flush=True)
            time.sleep(3)

    stage = c.dragon_state.get("current_stage", 0)
    tp = c.dragon_state.get("today_pass", 0)
    summary = {
        "stage": stage,
        "stage_label": f"第{stage + 1}/17场",
        "today_pass": tp,
        "reached_final": stage >= 17,
        "won": tp != 0,
        "battle_active": c.dragon_state.get("dragon_battle_active"),
    }
    print("[RESULT] " + json.dumps(summary, ensure_ascii=False), flush=True)
    try:
        c.close()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
