# -*- coding: utf-8 -*-
"""一次性激活授权核心：生成/校验/激活，MAC 绑定 + 签名 + 有效期 + 规格。"""
import hashlib
import hmac
import re
from datetime import datetime, timedelta

import auth

TIER_MAP = {"full": "FULL", "cultivate": "CULTURE"}
DUR_MAP = {"1": "1D", "7": "7D", "365": "365D", "per": "PER"}
DUR_DAYS = {"1": 1, "7": 7, "365": 365}
CARD_TYPES = {
    "CULTURE-1D", "CULTURE-7D", "CULTURE-365D", "CULTURE-PER",
    "FULL-1D", "FULL-7D", "FULL-365D", "FULL-PER",
}
_CARD_RE = re.compile(r"^KABU-([A-Z]+-\d+D|FULL-PER|CULTURE-PER)-(\d{8})-([0-9A-F]{16})$")
# 同步 auth 档位表，令 check_license / write_license 认新档位
auth.CARD_TYPES = CARD_TYPES


def get_machine_code(mac=None):
    """由 MAC（AA:BB:..或AA-BB-..）派生绑定码；缺省用本机。"""
    if mac:
        mac_hex = mac.replace(":", "").replace("-", "").upper()
        return hashlib.md5(mac_hex.encode("ascii")).hexdigest().upper()
    return auth.get_machine_code()


def gen_card(mac, tier, duration):
    """CLI 生成卡密。tier=full/cultivate，duration=1/7/365/per。返回 (card, card_type, expire)。"""
    tier = str(tier).strip().lower()
    dur = str(duration).strip().lower()
    if tier not in TIER_MAP:
        raise ValueError("规格必须为 full 或 cultivate")
    if dur not in DUR_MAP:
        raise ValueError("有效期必须为 1 / 7 / 365 / per")
    card_type = "%s-%s" % (TIER_MAP[tier], DUR_MAP[dur])
    expire = datetime(2099, 12, 31) if dur == "per" else datetime.now() + timedelta(days=DUR_DAYS[dur])
    mc = get_machine_code(mac)
    raw = "%s|%s|%s|%s" % (mc, card_type, expire.strftime("%Y%m%d"), auth.CARD_SECRET)
    h = hashlib.md5(raw.encode("ascii")).hexdigest().upper()[:16]
    return "KABU-%s-%s-%s" % (card_type, expire.strftime("%Y%m%d"), h), card_type, expire


def parse_card(card):
    m = _CARD_RE.fullmatch(str(card).strip().upper())
    if not m:
        return None
    card_type, expiry, h = m.group(1), m.group(2), m.group(3)
    try:
        expire = datetime.strptime(expiry, "%Y%m%d")
    except ValueError:
        return None
    return card_type, expire, h


def verify_card(card, mac=None):
    """校验多个信息：格式、规格合法、有效期、MAC 绑定签名。返回 (ok, card_type, expire)。"""
    p = parse_card(card)
    if not p:
        return False, "", None
    card_type, expire, h = p
    if expire.date() < datetime.now().date():
        return False, card_type, expire
    mc = get_machine_code(mac)
    raw = "%s|%s|%s|%s" % (mc, card_type, expire.strftime("%Y%m%d"), auth.CARD_SECRET)
    expected = hashlib.md5(raw.encode("ascii")).hexdigest().upper()[:16]
    if hmac.compare_digest(expected, h):
        return True, card_type, expire
    return False, card_type, expire


def activate(card, mac=None):
    """激活：校验通过写注册表。返回 (ok, msg)。"""
    mac = mac or auth.get_mac()
    ok, card_type, expire = verify_card(card, mac)
    if not ok:
        return False, "卡密无效、已过期或与当前机器不匹配"
    auth.write_license(card_type, expire)
    return True, "激活成功"
