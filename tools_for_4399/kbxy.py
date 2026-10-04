import socket
import struct
import time
import threading
import random
import zlib
from typing import Optional, List, Dict, Any, Callable, Tuple

HOST: str = "109.244.56.70"
HEARTBEAT_OP: int = 327686
SPLIT_MAGIC: int = 21316
COMPRESSED_MAGIC: int = 21315

OP_FIRST_HANDSHAKE = 1185433
OP_CHECK_ACCOUNT = 1183744
OP_GET_WORLD_NUM = 1183751
OP_GET_WORLD_LIST = 1183749
OP_ENTER_WORLD = 1183750
OP_CHECK_ACCOUNT_BACK = 1314816
OP_GET_WORLD_NUM_BACK = 1314823
OP_GET_WORLD_LIST_BACK = 1314821
OP_ENTER_WORLD_BACK = 1314822

DRAGON_COPY_MPARAMS = 20
OP_DRAGON_QUERY = 1186178
OP_DRAGON_QUERY_BACK = 1317250
OP_DRAGON_ACTION = 1186184
OP_DRAGON_ACTION_BACK = 1317251
OP_BATTLE_USER_OP = 1186050
OP_BATTLE_START_BACK = 1317120
OP_BATTLE_ROUND_START_BACK = 1317121
OP_BATTLE_ROUND_RESULT_BACK = 1317122
OP_BATTLE_END_BACK = 1317125
OP_PEIYU_CAN_ENTER = 1187090
OP_PEIYU_CAN_ENTER_BACK = 1330435
OP_PEIYU_GET_STATUS = 1187099
OP_PEIYU_STATUS_BACK = 1330443
OP_PEIYU_ERGAO = 1187095
OP_PEIYU_GROW = 1187096
OP_PEIYU_GROW_BACK = 1330440
OP_PEIYU_FOOD = 1187097
OP_PEIYU_FOOD_BACK = 1330441
OP_PEIYU_HARVEST = 1187098
OP_PEIYU_HARVEST_BACK = 1330442
OP_PEIYU_FANGSHENG = 1187101
OP_PEIYU_BUY_TOOLS = 1187113

OP_GET_SPIRIT_LIST = 1187329
OP_GET_SPIRIT_LIST_BACK = 1318401
OP_GET_PACKAGE = 1183761
OP_GET_PACKAGE_BACK = 1314833
PACKAGE_ALL_CATEGORIES = 0xFFFFFFFF
PEIYU_FOOD_CATEGORY = 300030


class KabuClient:
    def __init__(self, host: str, log_callback=None, *, port: Optional[int] = None):
        self.host = host
        self.port = port
        self.log_callback = log_callback or print
        self.sock: Optional[socket.socket] = None
        self.connected = False
        self.logged_in = False
        self.recv_buffer = b""
        self.msg_handlers: Dict[int, Callable[[int, bytes], None]] = {
            OP_CHECK_ACCOUNT_BACK: self._handle_account_response,
            OP_GET_WORLD_NUM_BACK: self._handle_world_num_response,
            OP_GET_WORLD_LIST_BACK: self._handle_world_list_response,
            OP_ENTER_WORLD_BACK: self._handle_enter_world_response,
            OP_BATTLE_START_BACK: self._handle_battle_start,
            OP_BATTLE_ROUND_START_BACK: self._handle_battle_round_start,
            OP_BATTLE_ROUND_RESULT_BACK: self._handle_battle_round_result,
            OP_BATTLE_END_BACK: self._handle_battle_end,
            OP_DRAGON_QUERY_BACK: self._handle_dragon_progress_response,
            OP_DRAGON_ACTION_BACK: self._handle_dragon_action_response,
            OP_GET_SPIRIT_LIST_BACK: self._handle_spirit_list_response,
            OP_GET_PACKAGE_BACK: self._handle_package_response,
            OP_PEIYU_CAN_ENTER_BACK: self._handle_peiyu_enter_response,
            OP_PEIYU_STATUS_BACK: self._handle_peiyu_status_response,
            OP_PEIYU_GROW_BACK: self._handle_peiyu_grow_response,
            OP_PEIYU_FOOD_BACK: self._handle_peiyu_food_response,
            OP_PEIYU_HARVEST_BACK: self._handle_peiyu_harvest_response,
        }
        self.lock = threading.Lock()
        self.login_condition = threading.Condition()
        self.login_error: Optional[str] = None
        self.user_id: Optional[int] = None
        self.selected_server_id: Optional[int] = None
        self.selected_server_name = ""
        self.auto_battle_enabled = False
        self.battle_round = 0
        self.auto_action_round = -1
        self.battle_state: Dict[str, Any] = {
            "active": False,
            "battle_type": 0,
            "escape_allowed": False,
            "player_team": [],
            "enemy_team": [],
        }
        self.send_lock = threading.Lock()
        self.heartbeat_stop = threading.Event()
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.login_token = ""
        self._login_server_id: Optional[int] = None
        self._login_server_mode = "auto"
        self.dragon_state = {
            "today_pass": 0,
            "life_chance": 0,
            "auto_running": False,
            "current_stage": 1,
            "auto_request_at": None,
        }
        self.spirit_list: List[Dict[str, Any]] = []
        self.inventory: List[Dict[str, Any]] = []
        self.peiyu_state: Dict[str, Any] = {}

    def log(self, msg: str, level: str = "INFO"):
        self.log_callback(f"[{level}] {msg}")

    def connect(self) -> bool:
        if self.connected:
            return True

        old_sock = self.sock
        self.sock = None
        if old_sock is not None:
            try:
                old_sock.close()
            except OSError as e:
                self.log(f"关闭旧连接失败: {e}", "ERROR")

        sock = None
        try:
            if self.port is None:
                self.port = random.randint(12001, 12020)
            self.log(f"正在连接游戏服务器 {self.host}:{self.port}...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((self.host, self.port))
            sock.settimeout(None)
            self.sock = sock
            self.connected = True
            self.recv_buffer = b""
            self.log("连接游戏服务器成功")
            threading.Thread(target=self._recv_loop, daemon=True).start()
            self.heartbeat_stop.clear()
            if self.heartbeat_thread is None or not self.heartbeat_thread.is_alive():
                self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
                self.heartbeat_thread.start()
            return True
        except OSError as e:
            if sock is not None:
                sock.close()
            self.log(f"连接失败: {e}", "ERROR")
            return False

    def login(self, token: str, timeout: float = 30,
              server_id: int = None, server_mode: str = "auto"):
        """登录进服。

        server_id    : 指定进服——传入具体服务器ID即进入该服（优先）。
        server_mode  : "auto"(默认/上次服务器) | "random"(随机) | "specified"(指定)。
                       当 server_id 非空时强制按 specified 处理。
        """
        if server_mode not in ("auto", "random", "specified"):
            raise ValueError("server_mode 必须为 auto/random/specified")
        if not self.connected:
            raise ConnectionError("请先连接游戏服务器")
        if not token:
            raise ValueError("登录 token 不能为空")
        self.login_token = token
        self._login_server_id = server_id
        self._login_server_mode = "specified" if server_id is not None else server_mode
        self.logged_in = False
        self.login_error = None
        self.user_id = None
        self.selected_server_id = None
        with self.login_condition:
            self.login_condition.notify_all()
        self.log("正在进行认证登录")
        if not self.send_cmd(OP_FIRST_HANDSHAKE, 0):
            raise ConnectionError("发送登录握手失败")
        if not self.send_cmd(OP_CHECK_ACCOUNT, 3, [token]):
            raise ConnectionError("发送账号认证失败")
        deadline = time.monotonic() + timeout
        with self.login_condition:
            while not self.logged_in and self.login_error is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self.login_error = "等待服务端完成登录超时"
                    break
                self.login_condition.wait(remaining)
        if self.login_error is not None:
            raise ConnectionError(self.login_error)
        self.log(f"服务端已确认进入服务器 {self.selected_server_name} ({self.selected_server_id})")

    def _heartbeat_loop(self):
        while not self.heartbeat_stop.wait(30):
            if self.connected:
                self.send_cmd(HEARTBEAT_OP, 0)

    def _build_body(self, body_list: List[Any] = None) -> bytes:
        ba = b""
        if not body_list:
            return ba
        for v in body_list:
            if isinstance(v, bool):
                ba += struct.pack("<?", v)
            elif isinstance(v, int):
                ba += struct.pack("<I", v & 0xFFFFFFFF)
            elif isinstance(v, str):
                utf_data = v.encode("utf-8")
                if len(utf_data) > 0xFFFF:
                    raise ValueError("字符串超过协议长度限制")
                ba += struct.pack("<H", len(utf_data))
                ba += utf_data
            elif isinstance(v, bytes):
                ba += v
            else:
                raise TypeError(f"不支持的协议字段类型: {type(v).__name__}")
        return ba

    def send_cmd(self, opcode: int, m_params: int = 0, body_list: List[Any] = None) -> bool:
        if not self.connected:
            self.log("连接断开，正在尝试自动重连", "WRAN")
            if not self.connect():
                return False
            if self.login_token:
                self.login(self.login_token)
        return self._send_packet(opcode, m_params, body_list)

    def _send_packet(self, opcode: int, m_params: int, body_list: List[Any] = None) -> bool:
        body_bin = self._build_body(body_list)
        body_len = len(body_bin)
        if body_len > 0xFFFF:
            raise ValueError("数据包超过协议长度限制")
        header = struct.pack("<HHII", SPLIT_MAGIC, body_len, opcode, m_params)
        full_pkt = header + body_bin
        try:
            with self.send_lock:
                if not self.connected or self.sock is None:
                    return False
                self.sock.sendall(full_pkt)
            self.log(f"发送命令 opcode={opcode}, mParams={m_params}")
            return True
        except OSError as e:
            self.log(f"发送失败: {e}", "ERROR")
            self.connected = False
            return False

    def _recv_loop(self):
        sock = self.sock
        try:
            while self.connected and sock is self.sock:
                if sock is None:
                    self.connected = False
                    break
                data = sock.recv(4096)
                if not data:
                    self.connected = False
                    break
                with self.lock:
                    self.recv_buffer += data
                self._parse_buffer()
        except OSError as e:
            if self.connected:
                self.log(f"接收连接断开: {e}", "ERROR")
            self.connected = False
        finally:
            if self.sock is sock:
                self.sock = None
                self.connected = False
            self.logged_in = False
            if self.login_error is None:
                self.login_error = "连接在登录完成前断开"
            with self.login_condition:
                self.login_condition.notify_all()
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass

    def _parse_buffer(self):
        while True:
            if len(self.recv_buffer) < 12:
                break
            magic, body_len, opcode, m_params = struct.unpack("<HHIi", self.recv_buffer[:12])
            if magic not in (SPLIT_MAGIC, COMPRESSED_MAGIC):
                self.recv_buffer = self.recv_buffer[1:]
                continue
            total_len = 12 + body_len
            if len(self.recv_buffer) < total_len:
                break
            body = self.recv_buffer[12:total_len]
            self.recv_buffer = self.recv_buffer[total_len:]
            if magic == COMPRESSED_MAGIC:
                try:
                    body = zlib.decompress(body)
                except zlib.error as e:
                    self.log(f"压缩回包 opcode={opcode} 解压失败: {e}", "ERROR")
                    continue
            self.log(f"收到回包 opcode={opcode}, mParams={m_params}")
            handler = self.msg_handlers.get(opcode)
            if handler is None:
                preview = body[:96].hex(" ")
                truncated = "（已截断）" if len(body) > 96 else ""
                self.log(
                    f"尚无结构化解析器，回包原始数据 {len(body)} 字节：{preview}{truncated}",
                    "WRAN",
                )
                continue
            try:
                handler(m_params, body)
            except Exception as e:
                if opcode == OP_DRAGON_QUERY_BACK:
                    self.dragon_state["auto_running"] = False
                    self.dragon_state["auto_request_at"] = None
                self.log(f"处理回包 opcode={opcode} 失败: {e}", "ERROR")

    def register_msg_handler(self, opcode: int, handler: Callable[[int, bytes], None]):
        self.msg_handlers[opcode] = handler

    def _fail_login(self, reason: str):
        self.logged_in = False
        self.login_error = reason
        self.log(reason, "ERROR")
        with self.login_condition:
            self.login_condition.notify_all()

    def _handle_account_response(self, m_params: int, _body: bytes):
        if m_params == 2:
            self.log("账号认证通过，正在查询服务器列表")
            if not self.send_cmd(OP_GET_WORLD_NUM, 0):
                self._fail_login("查询服务器数量请求发送失败")
            return
        if m_params == 1:
            self._fail_login("账号认证通过，但账号尚未创建游戏角色")
            return
        messages = {
            0: "账号认证失败：服务端拒绝登录",
            -1: "账号认证失败：服务端返回 -1（凭据未通过或请求参数无效）",
            -2: "账号或密码错误",
            -3: "账号或密码错误",
            -4: "账号认证失败：服务端错误",
            -5: "账号认证失败：服务端错误",
        }
        if m_params == 3:
            reason = "账号已被封停"
            if len(_body) >= 4:
                blocked_until, _ = self._read_int(_body, 0)
                reason += f"，限制时间戳={blocked_until}"
        else:
            reason = messages.get(m_params, f"账号认证失败：服务端状态码 {m_params}")
        self._fail_login(reason)

    def _handle_world_num_response(self, m_params: int, body: bytes):
        if body:
            self._fail_login("服务器数量回包格式异常")
            return
        if m_params <= 0:
            self._fail_login(f"服务端没有可用服务器：状态码 {m_params}")
            return
        self.log(f"服务端报告可用服务器数量：{m_params}")
        if not self.send_cmd(OP_GET_WORLD_LIST, 1000):
            self._fail_login("服务器列表请求发送失败")

    def _handle_world_list_response(self, _m_params: int, body: bytes):
        try:
            if len(body) < 2:
                raise ValueError("缺少服务器数量")
            count = struct.unpack_from("<h", body, 0)[0]
            if count <= 0 or count > 2000:
                raise ValueError(f"服务器数量无效：{count}")
            offset = 2
            servers = []
            for _ in range(count):
                server_id, offset = self._read_int(body, offset)
                name, offset = self._read_utf(body, offset)
                online_count, offset = self._read_int(body, offset)
                if server_id <= 0:
                    raise ValueError(f"服务器编号无效：{server_id}")
                servers.append({
                    "id": server_id,
                    "name": name,
                    "online": online_count,
                })
            last_server_id, offset = self._read_int(body, offset)
            if offset != len(body):
                raise ValueError(f"服务器列表回包剩余未解析数据：{len(body) - offset} 字节")
        except (ValueError, UnicodeDecodeError, struct.error) as exc:
            self._fail_login(f"解析服务器列表失败：{exc}")
            return

        server = self._choose_server(servers, last_server_id)
        self.selected_server_id = server["id"]
        self.selected_server_name = server["name"]
        self.log(
            f"选择服务器 {server['name']} ({server['id']})，"
            f"在线人数={server['online']}，列表数量={len(servers)}"
        )
        if not self.send_cmd(OP_ENTER_WORLD, server["id"]):
            self._fail_login("进入服务器请求发送失败")

    def _choose_server(self, servers: List[Dict[str, Any]], last_server_id: int) -> Dict[str, Any]:
        """按登录模式挑选服务器：specified(指定) / random(随机) / auto(默认上次或首个)。"""
        mode = getattr(self, "_login_server_mode", "auto")
        req = getattr(self, "_login_server_id", None)
        if mode == "specified" and req is not None:
            target = next((item for item in servers if item["id"] == req), None)
            if target is not None:
                return target
            self.log(f"指定服务器 {req} 不在当前列表，退回自动选择", "WRAN")
        if mode == "random":
            return random.choice(servers)
        return next((item for item in servers if item["id"] == last_server_id), servers[0])

    def _handle_enter_world_response(self, m_params: int, body: bytes):
        if m_params not in (0, 1):
            self._fail_login(f"进入服务器失败：服务端状态码 {m_params}")
            return
        try:
            offset = 16
            _, offset = self._read_utf(body, offset)
            offset += 16
            if offset + 8 > len(body):
                raise ValueError("进入服务器回包缺少玩家身份字段")
            self.user_id = struct.unpack_from("<I", body, offset + 4)[0]
            if self.user_id == 0:
                raise ValueError("进入服务器回包中的玩家ID无效")
        except (ValueError, UnicodeDecodeError, struct.error) as exc:
            self.user_id = None
            self._fail_login(f"解析进入服务器回包失败：{exc}")
            return
        self.logged_in = True
        self.login_error = None
        with self.login_condition:
            self.login_condition.notify_all()
        self.log(
            f"进入服务器确认成功，玩家ID="
            f"{self.user_id if self.user_id is not None else '未解析'}"
        )

    def set_auto_battle(self, enabled: bool):
        self.auto_battle_enabled = bool(enabled)
        if not enabled:
            self.log("自动战斗AI已关闭")
        else:
            self.log("自动战斗AI已启用；策略为可用技能、必要时换宠，禁用未分类道具")

    def _handle_battle_start(self, m_params: int, body: bytes):
        if m_params < 0:
            return
        try:
            offset = 0
            state, offset = self._read_int(body, offset)
            player_team = []
            enemy_team = []
            while state != -1:
                if len(player_team) + len(enemy_team) >= 100:
                    raise ValueError("战斗妖怪数量超过协议限制")
                actor_state = state
                sid, offset = self._read_int(body, offset)
                group_type, offset = self._read_int(body, offset)
                hp, offset = self._read_int(body, offset)
                max_hp, offset = self._read_int(body, offset)
                level, offset = self._read_int(body, offset)
                element, offset = self._read_int(body, offset)
                spirit_id, offset = self._read_int(body, offset)
                unique_id, offset = self._read_int(body, offset)
                user_id, offset = self._read_int(body, offset)
                skill_count, offset = self._read_int(body, offset)
                if skill_count < 0 or skill_count > 64:
                    raise ValueError(f"技能数量无效：{skill_count}")
                skills = []
                for _ in range(skill_count):
                    skill_id, offset = self._read_int(body, offset)
                    pp, offset = self._read_int(body, offset)
                    max_pp, offset = self._read_int(body, offset)
                    skills.append({"id": skill_id, "pp": pp, "max_pp": max_pp})
                actor = {
                    "state": 1 if actor_state == 2 else actor_state,
                    "sid": sid,
                    "group_type": group_type,
                    "hp": hp,
                    "max_hp": max_hp,
                    "level": level,
                    "element": element,
                    "spirit_id": spirit_id,
                    "unique_id": unique_id,
                    "user_id": user_id,
                    "skills": skills,
                }
                if self.user_id is not None and user_id == self.user_id:
                    player_team.append(actor)
                else:
                    enemy_team.append(actor)
                if actor_state == 2 and (self.user_id is None or user_id != self.user_id):
                    _, offset = self._read_int(body, offset)
                state, offset = self._read_int(body, offset)
            escape_allowed, offset = self._read_int(body, offset)
            if offset != len(body):
                raise ValueError(f"战斗开始回包剩余未解析数据：{len(body) - offset} 字节")
        except (ValueError, struct.error) as exc:
            self.battle_state["active"] = False
            self.log(f"解析战斗开始回包失败：{exc}", "ERROR")
            return

        self.battle_state = {
            "active": True,
            "battle_type": m_params,
            "escape_allowed": escape_allowed == 1,
            "player_team": player_team,
            "enemy_team": enemy_team,
        }
        self.battle_round = 0
        self.auto_action_round = -1
        self.log(
            f"战斗开始：类型={m_params}，我方妖怪={len(player_team)}，"
            f"对方妖怪={len(enemy_team)}，允许逃跑={escape_allowed == 1}"
        )
        if not player_team:
            self.log("未能从战斗数据中识别我方队伍；自动战斗不会发送操作", "WRAN")

    def _handle_battle_round_start(self, m_params: int, _body: bytes):
        if not self.battle_state["active"]:
            return
        self.battle_round += 1
        self.log(f"第 {self.battle_round} 回合开始，操作时限参数={m_params}")
        if self.auto_battle_enabled:
            self._choose_battle_action()

    def _handle_battle_round_result(self, m_params: int, body: bytes):
        if m_params == 0:
            try:
                has_battle, offset = self._read_int(body, 0)
                if has_battle == 1:
                    attacker_sid, offset = self._read_int(body, offset)
                    skill_id, offset = self._read_int(body, offset)
                    defender_sid, offset = self._read_int(body, offset)
                    miss, offset = self._read_int(body, offset)
                    if miss == 0:
                        _, offset = self._read_int(body, offset)
                        attacker_hp, offset = self._read_int(body, offset)
                        defender_hp, offset = self._read_int(body, offset)
                        _, offset = self._read_int(body, offset)
                        attacker = self._find_battle_actor(attacker_sid)
                        defender = self._find_battle_actor(defender_sid)
                        if attacker is not None:
                            attacker["hp"] = attacker_hp
                        if defender is not None:
                            defender["hp"] = defender_hp
                    attacker = self._find_battle_actor(attacker_sid)
                    if attacker in self.battle_state["player_team"]:
                        for skill in attacker["skills"]:
                            if skill["id"] == skill_id:
                                skill["pp"] = max(0, skill["pp"] - 1)
                                break
            except (ValueError, struct.error) as exc:
                self.log(f"解析战斗回合结果失败：{exc}", "ERROR")
        elif m_params == 1:
            self._handle_battle_actor_update(body)
        elif m_params == 2:
            self.log("收到战斗道具结果；自动道具保持禁用", "INFO")

    def _handle_battle_actor_update(self, body: bytes):
        try:
            offset = 0
            sid, offset = self._read_int(body, offset)
            unique_id, offset = self._read_int(body, offset)
            update_type, offset = self._read_int(body, offset)
            if update_type not in (1, 2):
                return
            state, offset = self._read_int(body, offset)
            sid, offset = self._read_int(body, offset)
            group_type, offset = self._read_int(body, offset)
            hp, offset = self._read_int(body, offset)
            max_hp, offset = self._read_int(body, offset)
            level, offset = self._read_int(body, offset)
            element, offset = self._read_int(body, offset)
            spirit_id, offset = self._read_int(body, offset)
            unique_id, offset = self._read_int(body, offset)
            user_id, offset = self._read_int(body, offset)
            skill_count, offset = self._read_int(body, offset)
            if skill_count < 0 or skill_count > 64:
                raise ValueError(f"技能数量无效：{skill_count}")
            skills = []
            for _ in range(skill_count):
                skill_id, offset = self._read_int(body, offset)
                pp, offset = self._read_int(body, offset)
                max_pp, offset = self._read_int(body, offset)
                skills.append({"id": skill_id, "pp": pp, "max_pp": max_pp})
            actor = {
                "state": 1 if state == 2 else state,
                "sid": sid,
                "group_type": group_type,
                "hp": hp,
                "max_hp": max_hp,
                "level": level,
                "element": element,
                "spirit_id": spirit_id,
                "unique_id": unique_id,
                "user_id": user_id,
                "skills": skills,
            }
            team = (
                self.battle_state["player_team"]
                if self.user_id is not None and user_id == self.user_id
                else self.battle_state["enemy_team"]
            )
            existing = next(
                (item for item in team if item["unique_id"] == unique_id),
                None,
            )
            if existing is None:
                team.append(actor)
            else:
                existing.update(actor)
        except (ValueError, struct.error) as exc:
            self.log(f"解析战斗妖怪状态更新失败：{exc}", "ERROR")

    def _find_battle_actor(self, sid: int):
        for team in (self.battle_state["player_team"], self.battle_state["enemy_team"]):
            for actor in team:
                if actor["sid"] == sid:
                    return actor
        return None

    def _choose_battle_action(self):
        if not self.auto_battle_enabled or not self.battle_state["active"]:
            return
        if self.battle_round == self.auto_action_round:
            return
        player_team = self.battle_state["player_team"]
        if self.user_id is None or not player_team:
            self.log("自动战斗暂停：无法确认我方身份或队伍", "WRAN")
            return
        active = next(
            (actor for actor in player_team if actor["state"] == 1 and actor["hp"] > 0),
            None,
        )
        if active is None:
            active = next((actor for actor in player_team if actor["hp"] > 0), None)
            if active is not None:
                self.log(f"当前妖怪无法继续战斗，切换至妖怪 uniqueid={active['unique_id']}")
                if self.send_cmd(OP_BATTLE_USER_OP, 1, [active["unique_id"]]):
                    self.auto_action_round = self.battle_round
                return
            if self.battle_state["escape_allowed"]:
                self.log("我方已无存活妖怪且服务端允许逃跑，尝试撤退", "WRAN")
                if self.send_cmd(OP_BATTLE_USER_OP, 3):
                    self.auto_action_round = self.battle_round
                return
            self.log("自动战斗暂停：没有可用妖怪且服务端未允许逃跑", "ERROR")
            return
        if not self.battle_state["enemy_team"]:
            self.log("自动战斗暂停：无法识别对方目标", "WRAN")
            return
        target = next(
            (actor for actor in self.battle_state["enemy_team"]
             if actor["state"] == 1 and actor["hp"] > 0),
            None,
        )
        if target is None:
            target = next((actor for actor in self.battle_state["enemy_team"] if actor["hp"] > 0), None)
        if target is None:
            self.log("自动战斗暂停：没有存活的对方目标", "WRAN")
            return
        skill = next(
            (item for item in active["skills"] if item["id"] > 0 and item["pp"] > 0),
            None,
        )
        if skill is not None:
            self.log(
                f"自动决策：妖怪 {active['unique_id']} 使用技能 {skill['id']} "
                f"(PP={skill['pp']})，目标 SID={target['sid']}"
            )
            if self.send_cmd(OP_BATTLE_USER_OP, 0, [target["sid"], skill["id"]]):
                self.auto_action_round = self.battle_round
            return
        reserve = next(
            (actor for actor in player_team
             if actor["hp"] > 0 and actor["unique_id"] != active["unique_id"]),
            None,
        )
        if reserve is not None:
            self.log(f"自动决策：当前技能 PP 耗尽，切换至妖怪 {reserve['unique_id']}", "WRAN")
            if self.send_cmd(OP_BATTLE_USER_OP, 1, [reserve["unique_id"]]):
                self.auto_action_round = self.battle_round
            return
        if self.battle_state["escape_allowed"]:
            self.log("自动决策：没有可用技能或替补且服务端允许逃跑，尝试撤退", "WRAN")
            if self.send_cmd(OP_BATTLE_USER_OP, 3):
                self.auto_action_round = self.battle_round
            return
        self.log("自动战斗暂停：技能 PP 已耗尽、无可用替补且服务端不允许逃跑", "ERROR")

    def _handle_battle_end(self, _m_params: int, _body: bytes):
        if self.battle_state["active"]:
            self.log("战斗结束")
        self.battle_state["active"] = False
        self.auto_action_round = -1

    @staticmethod
    def _read_int(body: bytes, offset: int) -> Tuple[int, int]:
        if offset + 4 > len(body):
            raise ValueError("回包缺少4字节整数")
        return struct.unpack_from("<i", body, offset)[0], offset + 4

    @staticmethod
    def _read_utf(body: bytes, offset: int) -> Tuple[str, int]:
        if offset + 2 > len(body):
            raise ValueError("回包缺少字符串长度")
        text_len = struct.unpack_from("<H", body, offset)[0]
        offset += 2
        if offset + text_len > len(body):
            raise ValueError("回包字符串内容不完整")
        return body[offset:offset + text_len].decode("utf-8"), offset + text_len

    @staticmethod
    def _read_count(body: bytes, offset: int, label: str, minimum_item_size: int = 4):
        count, offset = KabuClient._read_int(body, offset)
        if count < 0 or count > (len(body) - offset) // minimum_item_size:
            raise ValueError(f"{label}数量无效或超过回包长度")
        return count, offset

    def _handle_peiyu_enter_response(self, m_params: int, body: bytes):
        if body:
            raise ValueError("神兽园进入检查回包不应包含 body")
        if m_params == 1:
            self.log("神兽园入口检查通过")
        else:
            self.log(f"神兽园入口检查未通过：服务端状态码={m_params}", "WRAN")

    def _handle_peiyu_status_response(self, m_params: int, body: bytes):
        offset = 0
        garden_level = None
        feed_level = None
        if m_params == 2:
            garden_level, offset = self._read_int(body, offset)
            feed_level, offset = self._read_int(body, offset)
        elif m_params != 1:
            self.log(f"忽略神兽园状态回包：未知 mParams={m_params}", "WRAN")
            return

        if offset + 4 > len(body):
            raise ValueError("神兽园状态回包缺少用户ID")
        user_id = struct.unpack_from("<I", body, offset)[0]
        offset += 4
        grow_level, offset = self._read_int(body, offset)
        grow_exp, offset = self._read_int(body, offset)
        current_garden_level, offset = self._read_int(body, offset)
        foods, offset = self._read_int(body, offset)
        food_x, offset = self._read_int(body, offset)
        food_y, offset = self._read_int(body, offset)
        monster_count, offset = self._read_count(body, offset, "园中妖怪", 8)
        monsters = []
        for _ in range(monster_count):
            index, offset = self._read_int(body, offset)
            monster_type, offset = self._read_int(body, offset)
            monsters.append({"index": index, "type": monster_type})
        egg_count, offset = self._read_count(body, offset, "妖蛋", 24)
        eggs = []
        for _ in range(egg_count):
            index, offset = self._read_int(body, offset)
            egg_id, offset = self._read_int(body, offset)
            step, offset = self._read_int(body, offset)
            remaining_time, offset = self._read_int(body, offset)
            hatch_rate, offset = self._read_int(body, offset)
            mood, offset = self._read_int(body, offset)
            eggs.append({
                "index": index,
                "egg_id": egg_id,
                "step": step,
                "remaining_time": remaining_time,
                "hatch_rate": hatch_rate,
                "mood": mood,
            })
        if offset != len(body):
            raise ValueError(f"神兽园状态回包剩余未解析数据：{len(body) - offset} 字节")

        self.peiyu_state = {
            "user_id": user_id,
            "grow_level": grow_level,
            "grow_exp": grow_exp,
            "garden_level": current_garden_level,
            "foods": foods,
            "food_position": (food_x, food_y),
            "monsters": monsters,
            "eggs": eggs,
        }
        if garden_level is not None:
            self.peiyu_state["visited_garden_level"] = garden_level
            self.peiyu_state["visited_feed_level"] = feed_level
        self.log(
            f"[神兽园] 用户={user_id}，培育等级={grow_level}，经验={grow_exp}，"
            f"园区等级={current_garden_level}，神明果={foods}，"
            f"妖兽={len(monsters)}，妖蛋={len(eggs)}"
        )
        for egg in eggs:
            self.log(
                f"[神兽园] 妖蛋索引={egg['index']}，ID={egg['egg_id']}，"
                f"阶段={egg['step']}，剩余时间={egg['remaining_time']}，"
                f"孵化率={egg['hatch_rate']}，心情={egg['mood']}"
            )

    def _handle_peiyu_grow_response(self, m_params: int, body: bytes):
        if m_params != 1:
            self.log(f"神兽园养殖请求失败：服务端状态码={m_params}", "WRAN")
            return
        egg_id, offset = self._read_int(body, 0)
        index, offset = self._read_int(body, offset)
        step, offset = self._read_int(body, offset)
        remaining_time, offset = self._read_int(body, offset)
        if offset != len(body):
            raise ValueError("神兽园养殖回包包含多余数据")
        self.log(
            f"[神兽园] 养殖已受理：蛋ID={egg_id}，索引={index}，"
            f"阶段={step}，剩余时间={remaining_time}"
        )

    def _handle_peiyu_food_response(self, _m_params: int, body: bytes):
        foods, offset = self._read_int(body, 0)
        divine_fruit, offset = self._read_int(body, offset)
        if offset != len(body):
            raise ValueError("神明果回包包含多余数据")
        self.log(f"[神兽园] 神明果操作完成：剩余神明果={divine_fruit}，食物数={foods}")

    def _handle_peiyu_harvest_response(self, m_params: int, body: bytes):
        exp, offset = self._read_int(body, 0)
        if offset != len(body):
            raise ValueError("收获妖蛋回包包含多余数据")
        self.log(f"[神兽园] 收获完成：妖蛋索引={m_params}，培育经验增加={exp}")

    def _handle_package_response(self, m_params: int, body: bytes):
        if m_params in (9, 1048576):
            self.log(f"背包回包 mParams={m_params} 是局部用途数据，按游戏客户端逻辑跳过", "WRAN")
            return

        offset = 0
        iso_code, offset = self._read_int(body, offset)
        group_count, offset = self._read_count(body, offset, "背包分组")
        groups = []
        for _ in range(group_count):
            pack_code, offset = self._read_int(body, offset)
            pack_id, offset = self._read_int(body, offset)
            item_count, offset = self._read_count(body, offset, "背包物品")
            items = []
            for _ in range(item_count):
                position, offset = self._read_int(body, offset)
                item_id, offset = self._read_int(body, offset)
                item = {
                    "pack_code": pack_code,
                    "pack_id": pack_id,
                    "position": position,
                    "id": item_id,
                }
                if item_id > 0:
                    item["count"], offset = self._read_int(body, offset)
                    items.append(item)
            groups.append({
                "pack_code": pack_code,
                "pack_id": pack_id,
                "count": item_count,
                "items": items,
            })

        expiry_count, offset = self._read_count(body, offset, "物品有效期")
        expiries = []
        for _ in range(expiry_count):
            item_id, offset = self._read_int(body, offset)
            if item_id != 0:
                count, offset = self._read_int(body, offset)
                expires_at, offset = self._read_int(body, offset)
                expiries.append({
                    "id": item_id,
                    "count": count,
                    "expires_at": expires_at,
                })
        if offset != len(body):
            raise ValueError(f"背包回包剩余未解析数据：{len(body) - offset} 字节")

        self.inventory = groups
        item_total = sum(len(group["items"]) for group in groups)
        self.log(
            f"[背包] 查询结果：分组={len(groups)}，物品={item_total}，"
            f"有效期记录={len(expiries)}，状态码={iso_code}"
        )
        for group in groups:
            self.log(
                f"[背包] 分组 packCode={group['pack_code']} packId={group['pack_id']}："
                + (", ".join(
                    f"ID {item['id']} x{item['count']} (位置 {item['position']})"
                    for item in group["items"]
                ) or "无物品")
            )
        for item in expiries:
            self.log(
                f"[背包] 物品 ID {item['id']} x{item['count']} 有效期时间戳={item['expires_at']}"
            )

    def _handle_spirit_list_response(self, m_params: int, body: bytes):
        offset = 0
        serial, offset = self._read_int(body, offset)
        monster_count, offset = self._read_count(body, offset, "妖怪")
        stat_fields = (
            "is_first", "level", "exp", "type", "forbid_item",
            "attack", "defence", "magic", "resistance", "strength",
            "hp", "speed", "mold", "state", "need_exp", "time",
            "sex", "attack_learn_value", "defence_learn_value",
            "magic_learn_value", "resistance_learn_value", "hp_learn_value",
            "speed_learn_value", "attack_genius_value",
            "defence_genius_value", "magic_genius_value",
            "resistance_genius_value", "hp_genius_value",
            "speed_genius_value", "peerless_id", "peerless_status",
            "temporary_peerless_count",
        )
        monsters = []
        for _ in range(monster_count):
            monster_id, offset = self._read_int(body, offset)
            if monster_id == 0:
                break
            monster_type, offset = self._read_int(body, offset)
            index, offset = self._read_int(body, offset)
            monster = {
                "id": monster_id,
                "type_id": monster_type,
                "index": index,
            }
            for field in stat_fields:
                monster[field], offset = self._read_int(body, offset)

            skill_count, offset = self._read_count(body, offset, "妖怪技能", 12)
            skills = []
            active_skill_ids = []
            for _ in range(skill_count):
                skill_id, offset = self._read_int(body, offset)
                skill_pp, offset = self._read_int(body, offset)
                max_pp, offset = self._read_int(body, offset)
                active_skill_ids.append(skill_id)
                skills.append({"id": skill_id, "pp": skill_pp, "max_pp": max_pp})

            learnable_skills = []
            while True:
                skill_id, offset = self._read_int(body, offset)
                if skill_id == 0:
                    break
                if skill_id not in active_skill_ids:
                    learnable_skills.append(skill_id)

            unavailable_count, offset = self._read_int(body, offset)
            if unavailable_count < 0:
                raise ValueError("不可用技能数量无效")
            symm_count, offset = self._read_count(body, offset, "装备")
            equipment = []
            for _ in range(symm_count):
                place, offset = self._read_int(body, offset)
                equipment_id, offset = self._read_int(body, offset)
                equipment_index, offset = self._read_int(body, offset)
                equipment.append({
                    "place": place,
                    "id": equipment_id,
                    "index": equipment_index,
                })

            for _ in range(2):
                while True:
                    skill_id, offset = self._read_int(body, offset)
                    if skill_id in (-1, 0):
                        break
                    if skill_id > 0 and skill_id not in active_skill_ids:
                        learnable_skills.append(skill_id)
            monster["skills"] = skills
            monster["learnable_skill_ids"] = learnable_skills
            monster["unavailable_skill_slots"] = unavailable_count
            monster["equipment"] = equipment
            monsters.append(monster)

        current_count, offset = self._read_int(body, offset)
        total_count, offset = self._read_int(body, offset)
        if offset != len(body):
            raise ValueError(f"妖怪列表回包剩余未解析数据：{len(body) - offset} 字节")
        if m_params != 0:
            self.log(f"妖怪列表回包 mParams={m_params} 非主列表结果", "WRAN")
            return

        self.spirit_list = monsters
        self.log(
            f"[妖怪列表] 序列号={serial}，当前数量={current_count}，"
            f"总数量={total_count}，本次解析={len(monsters)}"
        )
        for monster in monsters:
            skill_ids = ", ".join(str(skill["id"]) for skill in monster["skills"]) or "无"
            self.log(
                f"[妖怪列表] 妖怪ID={monster['id']}，索引={monster['index']}，"
                f"等级={monster['level']}，HP={monster['hp']}，技能={skill_ids}"
            )

    def _handle_dragon_progress_response(self, m_params: int, body: bytes):
        if m_params != DRAGON_COPY_MPARAMS:
            self.dragon_state["auto_running"] = False
            self.dragon_state["auto_request_at"] = None
            self.log(f"忽略龙腾进度回包：副本参数不匹配 ({m_params})", "WRAN")
            return

        names = (
            "medals", "life_chance", "today_pass", "player_index",
            "low_award_flag", "high_award_flag", "low_award_index",
            "high_award_index",
        )
        progress = {}
        offset = 0
        for name in names:
            progress[name], offset = self._read_int(body, offset)

        candidates = []
        for _ in range(15):
            candidate, offset = self._read_utf(body, offset)
            candidates.append(candidate)

        progress["choice_monster"], offset = self._read_int(body, offset)
        progress["next_combat_index"], offset = self._read_int(body, offset)
        progress["current_combat"], offset = self._read_int(body, offset)
        if progress["current_combat"] < 0:
            raise ValueError("回包中的当前战斗场数无效")

        wins = []
        for _ in range(progress["current_combat"]):
            win, offset = self._read_utf(body, offset)
            wins.append(win)
        if progress["choice_monster"] == 1:
            progress["player_monster_info"], offset = self._read_utf(body, offset)

        self.dragon_state.pop("player_monster_info", None)
        self.dragon_state.update(progress)
        self.dragon_state["current_stage"] = progress["next_combat_index"]
        self.dragon_state["candidates"] = candidates
        self.dragon_state["wins"] = wins
        self.log(
            f"[龙腾] 勋章={progress['medals']}，副本间免费补血次数="
            f"{progress['life_chance']}，今日通关={progress['today_pass']}，"
            f"下一关={progress['next_combat_index']}，当前场次={progress['current_combat']}，"
            f"候选妖怪={len(candidates)}只"
        )
        self.log("[龙腾] 候选列表：" + "、".join(candidates))
        if wins:
            self.log("[龙腾] 已胜场：" + "、".join(wins))

        if self.dragon_state["auto_running"]:
            self.dragon_state["auto_running"] = False
            self.dragon_state["auto_request_at"] = None
            if progress["today_pass"] != 0:
                self.log("今日龙腾已通关，不再发起战斗")
                return
            if progress["choice_monster"] != 1:
                self.log("尚未选择出战妖怪；请先在游戏中完成选宠", "WRAN")
                return

            battle_type = int(progress["next_combat_index"] >= 17)
            battle_name = "终局战" if battle_type else "普通战"
            self.log(f"根据服务端关卡进度，自动选择：{battle_name}")
            if not self.dragon_start_battle(battle_type):
                self.log("发起战斗失败；请检查连接后重试", "ERROR")

    def _handle_dragon_action_response(self, m_params: int, body: bytes):
        if m_params != DRAGON_COPY_MPARAMS:
            self.log(f"忽略龙腾操作回包：副本参数不匹配 ({m_params})", "WRAN")
            return

        operation, offset = self._read_int(body, 0)
        result, offset = self._read_int(body, offset)
        action_names = {
            1: "出战妖怪查询",
            2: "战斗",
            3: "抽奖",
            4: "查看候选妖怪",
            5: "补血",
            6: "复活妖怪",
            7: "交换候选妖怪",
        }
        action = action_names.get(operation, f"未知操作({operation})")
        result_messages = {
            (2, 0): "战斗已发起",
            (2, 1): "今日已战胜首领",
            (2, 2): "没有可战斗的妖怪",
            (3, 0): "抽奖成功",
            (3, 1): "当前不可抽奖",
            (3, 2): "已经抽过奖励",
            (4, 0): "查看成功",
            (4, 1): "卡布币不足",
            (5, 0): "补血成功",
            (5, 1): "免费补血次数已用完",
            (5, 2): "龙腾勋章不足",
            (5, 3): "无需补血",
            (5, 4): "无需补血；阵亡妖怪需要复活",
            (5, 5): "出战妖怪均已阵亡",
            (6, 0): "复活成功",
            (6, 1): "卡布币不足",
            (6, 2): "该妖怪无需复活",
            (7, 0): "交换成功",
            (7, 1): "交换失败",
        }
        details = []
        if operation == 2 and result == 0:
            combat_result, offset = self._read_int(body, offset)
            medals, offset = self._read_int(body, offset)
            boss_index, offset = self._read_int(body, offset)
            details.extend((f"战斗结果={combat_result}", f"获得勋章={medals}",
                            f"Boss序号={boss_index}"))
        elif operation == 5:
            heal_type, offset = self._read_int(body, offset)
            details.append(f"补血类型={heal_type}")
        elif result == 0 and operation in (1, 6, 7):
            monster_info, offset = self._read_utf(body, offset)
            details.append(f"妖怪信息={monster_info}")

        suffix = f"，{'，'.join(details)}" if details else ""
        result_text = result_messages.get((operation, result), f"result={result}")
        level = "INFO" if result == 0 else "WRAN"
        self.log(f"[龙腾] {action}回包：{result_text}{suffix}", level)

    def dragon_query_progress(self):
        return self.send_cmd(OP_DRAGON_QUERY, DRAGON_COPY_MPARAMS)

    def dragon_get_selected_monsters(self):
        self.send_cmd(OP_DRAGON_ACTION, DRAGON_COPY_MPARAMS, [1, 0, 0])

    def dragon_start_battle(self, battle_type: int = 0) -> bool:
        if battle_type not in (0, 1):
            raise ValueError("battle_type 必须为 0（普通战）或 1（终局战）")
        if self.battle_state["active"]:
            self.log("当前战斗尚未结束，不能发起新的龙腾战斗", "WRAN")
            return False
        return self.send_cmd(OP_DRAGON_ACTION, DRAGON_COPY_MPARAMS, [2, 1, battle_type])

    def _ensure_dragon_preparation(self, action: str) -> bool:
        if self.battle_state["active"]:
            self.log(f"龙腾{action}仅能在两场战斗之间的编队准备阶段使用，战斗中不可使用", "WRAN")
            return False
        return True

    def dragon_medal_heal(self, use_medal: bool = True) -> bool:
        if not self._ensure_dragon_preparation("补血"):
            return False
        if use_medal:
            self.log("请求消耗1枚龙腾勋章，为出战编队全队补血")
        else:
            self.log("请求使用1次副本间免费补血次数，不消耗龙腾勋章")
        return self.send_cmd(OP_DRAGON_ACTION, DRAGON_COPY_MPARAMS, [5, 1, int(use_medal)])

    def dragon_lottery(self, reward_type: int):
        if reward_type not in (1, 2):
            raise ValueError("reward_type 必须为 1（初级奖励）或 2（高级奖励）")
        self.send_cmd(OP_DRAGON_ACTION, DRAGON_COPY_MPARAMS, [3, 1, reward_type])

    def dragon_lookup_monster(self, index: int, monster_id: int) -> bool:
        if not self._ensure_dragon_preparation("查看敌方阵容"):
            return False
        self.log("请求查看龙腾副本敌方阵容；该操作可能消耗1000铜钱", "USER")
        return self.send_cmd(OP_DRAGON_ACTION, DRAGON_COPY_MPARAMS, [4, 2, index, monster_id])

    def dragon_revive_monster(self, index: int) -> bool:
        if not self._ensure_dragon_preparation("复活"):
            return False
        self.log("请求复活龙腾副本中的阵亡妖怪；该操作可能消耗5卡布币", "USER")
        return self.send_cmd(OP_DRAGON_ACTION, DRAGON_COPY_MPARAMS, [6, 1, index])

    def dragon_swap_monsters(self, index1: int, index2: int) -> bool:
        if not self._ensure_dragon_preparation("交换编队"):
            return False
        return self.send_cmd(OP_DRAGON_ACTION, DRAGON_COPY_MPARAMS, [7, 2, index1, index2])

    def dragon_auto_start(self) -> bool:
        """Check server state, then start at most one correctly typed battle."""
        if self.dragon_state["auto_running"]:
            started_at = self.dragon_state.get("auto_request_at")
            if started_at is not None and time.monotonic() - started_at < 15:
                self.dragon_state["auto_running"] = False
                self.dragon_state["auto_request_at"] = None
                self.log("已取消等待中的自动推进", "USER")
                return False
            self.log("等待进度回包超时，重新查询", "WRAN")
        self.dragon_state["auto_running"] = True
        self.dragon_state["auto_request_at"] = time.monotonic()
        self.log("自动推进：先读取服务端进度，再判断是否发起下一战", "USER")
        if not self.dragon_query_progress():
            self.dragon_state["auto_running"] = False
            self.dragon_state["auto_request_at"] = None
            return False
        return True


    def peiyu_enter_check(self, shenshou_user_id: int):
        if shenshou_user_id <= 0:
            raise ValueError("shenshou_user_id 必须为正整数")
        return self.send_cmd(OP_PEIYU_CAN_ENTER, shenshou_user_id)

    def peiyu_get_status(self):
        return self.send_cmd(OP_PEIYU_GET_STATUS, 1)

    def peiyu_feed(self, value: int):
        """Send the integer supplied by the original 神明果 UI event."""
        return self.send_cmd(OP_PEIYU_FOOD, PEIYU_FOOD_CATEGORY, [value])

    def peiyu_grow(self, index: int):
        if index <= 0:
            raise ValueError("index 必须为正整数")
        return self.send_cmd(OP_PEIYU_GROW, index)

    def peiyu_harvest(self, index: int):
        if index <= 0:
            raise ValueError("index 必须为正整数")
        return self.send_cmd(OP_PEIYU_HARVEST, index)

    def peiyu_fangsheng(self, index: int):
        if index <= 0:
            raise ValueError("index 必须为正整数")
        return self.send_cmd(OP_PEIYU_FANGSHENG, index)

    def peiyu_buy_tools(self, tool_id: int, count: int):
        return self.send_cmd(OP_PEIYU_BUY_TOOLS, 0, [tool_id, count])

    def get_spirit_list(self):
        return self.send_cmd(OP_GET_SPIRIT_LIST)

    def get_package(self):
        return self.send_cmd(OP_GET_PACKAGE, PACKAGE_ALL_CATEGORIES)

    def close(self):
        self.heartbeat_stop.set()
        self.connected = False
        sock = self.sock
        self.sock = None
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()
