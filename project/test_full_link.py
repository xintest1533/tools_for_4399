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
    """龙腾盛会链路探测：进副本 -> 查进度。"""
    try:
        results.append(_r("龙腾进副本", c.dragon_enter_copy()))
        time.sleep(1.0)
        results.append(_r("龙腾查进度", c.dragon_query_progress()))
    except Exception as e:  # noqa: BLE001
        results.append({"op": "龙腾进副本/查进度", "status": "EXC", "detail": str(e)})


def main() -> int:
    ap = argparse.ArgumentParser(description="卡布西游全链路测试")
    ap.add_argument("--token", default="", help="4399 登录态 token（优先；缺省自动从 credentials.json 取）")
    ap.add_argument("--out", default="", help="报告输出路径，默认写 test_reports/")
    ap.add_argument("--shenshou", type=int, default=0, help="神兽园 shenshou_user_id（可选）")
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
        elif not c.login(token):
            report["results"].append(_r("登录", False, detail="token 无效或超时"))
        else:
            report["results"].append(_r("登录", True))
            probe_peiyu(c, report["results"], args.shenshou)
            probe_dragon(c, report["results"])
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
