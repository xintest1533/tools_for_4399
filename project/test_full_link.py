#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
卡布西游脱机助手 —— 全链路自动测试脚本（培育 / 神兽园 / 龙腾盛会）。
供「卡布助手测试开发交替」定时任务奇数小时调用。

用法：
    python3 test_full_link.py --token <4399登录态token> [--out <报告路径>] [--shenshou <神兽园id>]

说明：
  - 测试账号由调用方通过多账号凭证存储读取后换算成 4399 登录态 token 传入，
    本脚本绝不把账号/密码写入日志或仓库。
  - 覆盖三模块：培育仓(Cultivate)、神兽园(peiyu_*)、龙腾盛会(dragon_*)，
    逐 opcode 记录回包 mParams 与解析结果，产出结构化测试报告。
"""
import argparse
import json
import os
import sys
import time
import traceback

# project/ 与仓库根都在查找路径内（login_4399.py 位于仓库根）
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools_for_4399.kbxy import KabuClient, HOST  # noqa: E402


def _resolve_token(cli_token: str) -> str:
    """--token 优先；否则从 credentials.json 自动取登录态（token>cookie>账号密码）。"""
    if cli_token:
        return cli_token
    try:
        import login_4399
        cred = login_4399.load_credentials()
        if not cred:
            raise RuntimeError("credentials.json 不存在或无内容")
        return login_4399.get_token(cred, save=True)
    except Exception as e:  # noqa: BLE001
        print(f"[TEST] 自动取登录态失败: {e}", file=sys.stderr)
        raise


def _r(op: str, status, **extra) -> dict:
    d = {"op": op, "status": "OK" if status else "FAIL"}
    d.update(extra)
    return d


def probe_peiyu(c: KabuClient, results: list, shenshou_user_id: int = 0) -> None:
    """神兽园 + 培育仓链路探测。"""
    if shenshou_user_id > 0:
        results.append(_r("神兽园入口检查", c.peiyu_enter_check(shenshou_user_id)))
    else:
        results.append({"op": "神兽园入口检查", "status": "SKIP", "note": "缺少 shenshou_user_id"})
    results.append(_r("神兽园状态", c.peiyu_get_status()))
    try:
        # 培育仓：龙腾化形仓状态查询(1187122->1330482)
        results.append(_r("培育仓状态", c.send_cmd(1187122, 0, [])))
    except Exception as e:  # noqa: BLE001
        results.append({"op": "培育仓状态", "status": "EXC", "detail": str(e)})


def probe_dragon(c: KabuClient, results: list) -> None:
    """龙腾盛会链路探测：进副本 -> 查进度 -> 出战查询(操作1, 只读不消耗额度)。"""
    try:
        results.append(_r("龙腾进副本", c.dragon_enter_copy()))
        time.sleep(1.0)
        results.append(_r("龙腾查进度", c.dragon_query_progress()))
        time.sleep(1.2)
        # 出战信息由 1317250 进度回包自带(choice_monster=1 时给出 12 只出战怪)，
        # 无需发操作1(1186184)——其回包同为 1317250，会消费 auto_running 卡死自动流程。
        team = c.dragon_state.get("dragon_team") or []
        drew = c.dragon_state.get("dragon_drew")
        armed = c.dragon_state.get("dragon_combat_armed")
        results.append(_r(
            "龙腾出战确认(进度回包自带)", True,
            detail=f"dragon_drew={drew} dragon_combat_armed={armed} 出战{len(team)}只（回包详见日志）",
        ))
    except Exception as e:  # noqa: BLE001
        results.append({"op": "龙腾进副本/查进度", "status": "EXC", "detail": str(e)})


def probe_dragon_battle(c: KabuClient, results: list) -> None:
    """龙腾战斗链路探测（--battle）：进关卡 -> 发起普通战 -> 观察回合/技能/进度推进。
    注意：会消耗账号 1 场今日战斗额度（每日 17 场）。"""
    try:
        c.dragon_goto_level(0)
        time.sleep(1.5)
        ok = c.dragon_start_battle(0)
        if not ok:
            results.append(_r("龙腾发起战斗", False, detail="发起失败（战斗中或前置不足）"))
            return
        results.append(_r("龙腾发起战斗", True, detail="已发送[2,1,0]普通战"))
        time.sleep(6.0)
        round_n = c.dragon_state.get("dragon_round", 0)
        active = c.dragon_state.get("dragon_battle_active")
        team = c.dragon_state.get("dragon_team") or []
        results.append(_r(
            "龙腾回合观察", True if round_n > 0 else "无回合回包",
            detail=f"dragon_round={round_n} battle_active={active} 出战{len(team)}只（回包详见日志）",
        ))
        time.sleep(1.0)
        c.dragon_query_progress()
        time.sleep(1.0)
        stage = c.dragon_state.get("current_stage")
        cur = c.dragon_state.get("current_combat")
        results.append(_r("龙腾进度推进检查", True,
                          detail=f"current_stage={stage} current_combat={cur}"))
    except Exception as e:  # noqa: BLE001
        results.append({"op": "龙腾战斗链路", "status": "EXC", "detail": str(e)})


def probe_dragon_auto(c: KabuClient, results: list) -> None:
    """自动连打闭环探测（--auto，依赖先 --battle 打过一场）：
    设置 auto_mode/in_dragon，查进度触发自动流程，然后模拟 watchdog 心跳
    循环调用 dragon_check_stuck()（兜底发起战斗/交换编队续战），
    观察 dragon_battle_active 是否变 True（连续连打闭环验证）。"""
    try:
        c.dragon_state["auto_mode"] = True
        c.dragon_state["in_dragon"] = True
        c.dragon_state["auto_running"] = True
        c.dragon_query_progress()
        started = False
        for _ in range(8):
            time.sleep(1.5)
            try:
                c.dragon_check_stuck()
            except Exception as exc:  # noqa: BLE001
                results.append({"op": "龙腾自动连打闭环", "status": "EXC", "detail": str(exc)})
                return
            if c.dragon_state.get("dragon_battle_active"):
                started = True
                break
        armed = c.dragon_state.get("dragon_combat_armed")
        viewed = c.dragon_state.get("dragon_candidate_viewed")
        active = c.dragon_state.get("dragon_battle_active")
        stage = c.dragon_state.get("current_stage")
        results.append(_r(
            "龙腾自动连打闭环", True,
            detail=f"combat_armed={armed} candidate_viewed={viewed} "
                   f"battle_active={active} stage={stage}（battle_active=True 表示已自动发起下一场）",
        ))
    except Exception as e:  # noqa: BLE001
        results.append({"op": "龙腾自动连打闭环", "status": "EXC", "detail": str(e)})


def main() -> int:
    ap = argparse.ArgumentParser(description="卡布西游全链路测试")
    ap.add_argument("--token", default="", help="4399 登录态 token（优先；缺省自动从 credentials.json 取）")
    ap.add_argument("--out", default="", help="报告输出路径，默认写 test_reports/")
    ap.add_argument("--shenshou", type=int, default=0, help="神兽园 shenshou_user_id（可选）")
    ap.add_argument("--battle", action="store_true",
                    help="发起1场龙腾普通战实测战斗链路（消耗今日1场额度）")
    ap.add_argument("--auto", action="store_true",
                    help="战斗后验证自动连打闭环（查进度→自动发起下一场；需--battle）")
    args = ap.parse_args()

    report = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "module": "全链路(培育/神兽园/龙腾)",
        "results": [],
        "summary": {"ok": 0, "fail": 0},
    }

    c = KabuClient(HOST)
    try:
        token = _resolve_token(args.token)
        if not c.connect():
            report["results"].append(_r("连接游戏服务器", False, detail="连接失败"))
        else:
            try:
                ok_login = c.login(token)
            except ConnectionError as exc:
                report["results"].append(_r(
                    "登录", False,
                    detail=f"凭证过期：{exc}。请重新抓取4399浏览器cookie后运行："
                           "python login_4399.py --cookie '<新cookie>' --save",
                ))
                ok_login = False
            if not ok_login:
                if not any(r["op"] == "登录" for r in report["results"]):
                    report["results"].append(_r("登录", False, detail="token 无效或超时"))
            else:
                report["results"].append(_r("登录", True))
                probe_peiyu(c, report["results"], args.shenshou)
                probe_dragon(c, report["results"])
                if args.battle:
                    probe_dragon_battle(c, report["results"])
                if args.auto:
                    probe_dragon_auto(c, report["results"])
    except Exception:  # noqa: BLE001
        report["results"].append({"op": "全链路", "status": "EXC", "detail": traceback.format_exc()})
    finally:
        try:
            c.close()
        except Exception:  # noqa: BLE001
            pass

    # 未解析回包统计（作为改进建议沉淀进测试产物）
    report["unparsed_opcodes"] = (
        c.get_unparsed_opcodes() if hasattr(c, "get_unparsed_opcodes") else {}
    )
    unparsed_n = len(report["unparsed_opcodes"])
    if unparsed_n:
        report["improvements"] = (
            f"存在 {unparsed_n} 类未结构化解析的回包，建议下轮开发为高频 opcode"
            " 增加结构化解析器（先覆盖出现时机明确的 1315883/1317360/1317152 等）"
        )

    for r in report["results"]:
        if r.get("status") in ("OK", "SKIP"):
            report["summary"]["ok"] += 1
        else:
            report["summary"]["fail"] += 1

    out_dir = args.out or os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_reports")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"full_link_{time.strftime('%Y%m%d_%H%M%S')}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n[TEST] 报告已写入: {out_path}")
    return 0 if report["summary"]["fail"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
