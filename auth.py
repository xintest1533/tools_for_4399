import hashlib
import hmac
import re
import uuid
import winreg
from datetime import date, datetime, timedelta

REG_PATH = r"Software\KabuHelper"
CARD_SECRET = "KABU2026"
CARD_TYPES = {"CULTURE-1D", "CULTURE-7D", "CULTURE-365D", "CULTURE-PER",
              "FULL-1D", "FULL-7D", "FULL-365D", "FULL-PER"}
CARD_HASH_RE = re.compile(r"^[0-9A-F]{16}$")
MACHINE_CODE_RE = re.compile(r"^[0-9A-F]{32}$")


def get_mac() -> str:
    """Return a stable hardware identifier used for local license binding."""
    return ":".join(("%012X" % uuid.getnode())[i:i + 2] for i in range(0, 12, 2))


def get_machine_code() -> str:
    mac = hex(uuid.getnode())[2:]
    return hashlib.md5(mac.encode("ascii")).hexdigest().upper()


def _card_hash(machine_code: str, card_type: str, expires_on: date) -> str:
    raw = f"{machine_code}|{card_type}|{expires_on.strftime('%Y%m%d')}|{CARD_SECRET}"
    return hashlib.md5(raw.encode("ascii")).hexdigest().upper()[:16]


def write_license(card_type: str, expire: datetime):
    if card_type not in CARD_TYPES:
        raise ValueError("不支持的授权档位")
    if not isinstance(expire, datetime):
        raise TypeError("授权到期时间必须是 datetime")

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
        winreg.SetValueEx(key, "Activated", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "CardType", 0, winreg.REG_SZ, card_type)
        winreg.SetValueEx(key, "MacBind", 0, winreg.REG_SZ, get_mac())
        winreg.SetValueEx(key, "ExpireTime", 0, winreg.REG_SZ, expire.strftime("%Y-%m-%d"))


def check_license() -> str:
    """Return the valid permission tier, or 'none' if the registry license is invalid."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ) as key:
            activated = winreg.QueryValueEx(key, "Activated")[0]
            card_type = winreg.QueryValueEx(key, "CardType")[0]
            mac_bind = winreg.QueryValueEx(key, "MacBind")[0]
            expire_str = winreg.QueryValueEx(key, "ExpireTime")[0]

        if (activated != 1 or mac_bind != get_mac() or card_type not in CARD_TYPES):
            return "none"
        expire_date = datetime.strptime(expire_str, "%Y-%m-%d").date()
        if expire_date < datetime.now().date():
            return "none"
        return "full" if card_type.startswith("FULL-") else "culture"
    except (OSError, TypeError, ValueError):
        return "none"


def verify_card(card: str):
    """Verify a machine-bound card and return its tier and expiration date."""
    normalized = card.strip().upper()
    if not normalized.startswith("KABU-"):
        return False, "", None

    rest = normalized[5:]
    parts = rest.rsplit("-", 2)
    if len(parts) == 3 and re.fullmatch(r"\d{8}", parts[1]):
        card_type, expiry_text, card_hash = parts
        if card_type not in CARD_TYPES or not CARD_HASH_RE.fullmatch(card_hash):
            return False, "", None
        try:
            expire = datetime.strptime(expiry_text, "%Y%m%d")
        except ValueError:
            return False, "", None
        if expire.date() < datetime.now().date():
            return False, "", None
        expected = _card_hash(get_machine_code(), card_type, expire.date())
        if hmac.compare_digest(expected, card_hash):
            return True, card_type, expire
        return False, "", None

    # Accept cards issued before the expiry date was embedded in the card string.
    card_type, card_hash = rest.rsplit("-", 1) if "-" in rest else ("", "")
    if card_type not in CARD_TYPES or not CARD_HASH_RE.fullmatch(card_hash):
        return False, "", None
    possible_expirations = (
        datetime.now() + timedelta(days=7),
        datetime(2099, 12, 31),
    )
    machine_code = get_machine_code()
    for expire in possible_expirations:
        expected = _card_hash(machine_code, card_type, expire.date())
        if hmac.compare_digest(expected, card_hash):
            return True, card_type, expire
    return False, "", None
