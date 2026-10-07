import socket
import struct
import time
import threading
import random
import zlib
import re
import os
import sys
from typing import Optional, List, Dict, Any, Callable, Tuple

HOST: str = "109.244.56.70"
HEARTBEAT_OP: int = 327686
SPLIT_MAGIC: int = 21316
COMPRESSED_MAGIC: int = 21315

ELEMENT_TO_NATURE = {0: "金", 1: "木", 2: "水", 3: "火", 4: "土", 5: "妖", 6: "魔", 7: "毒", 8: "圣", 9: "翼", 10: "雷", 11: "幻", 12: "怪", 13: "风", 14: "灵", 15: "特殊", 16: "无", 17: "冰", 18: "机械", 19: "火风", 20: "木灵", 21: "土幻", 22: "水妖", 23: "音", 24: "金怪", 25: "鬼", 26: "水雷"}
ELEMENT_NODE = {
    0: {0: 0.5, 1: 2.0, 2: 1.0, 3: 0.5, 4: 1.0, 5: 0.5, 6: 1.0, 7: 1.0, 8: 0.5, 9: 1.0, 10: 1.0, 11: 1.0, 12: 2.0, 13: 2.0, 14: 1.0, 15: 1.0, 16: 1.0, 17: 1.0, 18: 1.0, 19: 1.25, 20: 1.5, 21: 1.0, 22: 0.75, 23: 2.0, 24: 1.25, 25: 1.0, 26: 1.0},
    1: {0: 0.5, 1: 0.5, 2: 1.0, 3: 1.0, 4: 2.0, 5: 1.0, 6: 2.0, 7: 1.0, 8: 0.5, 9: 0.5, 10: 2.0, 11: 0.5, 12: 1.0, 13: 0.5, 14: 2.0, 15: 1.0, 16: 1.0, 17: 0.5, 18: 0.5, 19: 0.75, 20: 1.25, 21: 1.25, 22: 1.0, 23: 1.0, 24: 0.75, 25: 1.0, 26: 1.5},
    2: {0: 1.0, 1: 1.0, 2: 0.5, 3: 2.0, 4: 0.5, 5: 1.0, 6: 1.0, 7: 2.0, 8: 0.5, 9: 2.0, 10: 1.0, 11: 1.0, 12: 0.5, 13: 1.0, 14: 0.5, 15: 1.0, 16: 1.0, 17: 2.0, 18: 1.0, 19: 1.5, 20: 0.75, 21: 0.75, 22: 0.75, 23: 0.5, 24: 0.75, 25: 1.0, 26: 0.75},
    3: {0: 2.0, 1: 1.0, 2: 0.5, 3: 0.5, 4: 1.0, 5: 0.5, 6: 1.0, 7: 2.0, 8: 0.5, 9: 2.0, 10: 1.0, 11: 2.0, 12: 1.0, 13: 1.0, 14: 0.5, 15: 1.0, 16: 1.0, 17: 1.0, 18: 2.0, 19: 0.75, 20: 0.75, 21: 1.5, 22: 0.5, 23: 1.0, 24: 1.5, 25: 2.0, 26: 0.75},
    4: {0: 1.0, 1: 0.5, 2: 2.0, 3: 1.0, 4: 0.5, 5: 1.0, 6: 1.0, 7: 2.0, 8: 0.5, 9: 0.5, 10: 2.0, 11: 2.0, 12: 2.0, 13: 1.0, 14: 1.0, 15: 1.0, 16: 1.0, 17: 0.5, 18: 0.5, 19: 1.0, 20: 0.75, 21: 1.25, 22: 1.5, 23: 1.0, 24: 1.5, 25: 1.0, 26: 4.0},
    5: {0: 1.0, 1: 2.0, 2: 2.0, 3: 1.0, 4: 1.0, 5: 0.5, 6: 0.5, 7: 0.5, 8: 2.0, 9: 1.0, 10: 0.5, 11: 0.5, 12: 2.0, 13: 1.0, 14: 1.0, 15: 1.0, 16: 1.0, 17: 1.0, 18: 2.0, 19: 1.0, 20: 1.5, 21: 0.75, 22: 1.25, 23: 0.5, 24: 1.5, 25: 1.0, 26: 1.25},
    6: {0: 1.0, 1: 0.5, 2: 1.0, 3: 2.0, 4: 0.5, 5: 2.0, 6: 0.5, 7: 1.0, 8: 2.0, 9: 1.0, 10: 0.5, 11: 0.5, 12: 1.0, 13: 1.0, 14: 1.0, 15: 1.0, 16: 1.0, 17: 2.0, 18: 1.0, 19: 1.5, 20: 0.75, 21: 0.5, 22: 1.5, 23: 2.0, 24: 1.0, 25: 0.5, 26: 0.75},
    7: {0: 1.0, 1: 2.0, 2: 0.5, 3: 0.5, 4: 0.5, 5: 2.0, 6: 1.0, 7: 0.5, 8: 1.0, 9: 1.0, 10: 1.0, 11: 0.5, 12: 1.0, 13: 2.0, 14: 1.0, 15: 1.0, 16: 1.0, 17: 1.0, 18: 1.0, 19: 1.25, 20: 1.5, 21: 0.5, 22: 1.25, 23: 2.0, 24: 1.0, 25: 2.0, 26: 0.75},
    8: {0: 2.0, 1: 2.0, 2: 2.0, 3: 2.0, 4: 2.0, 5: 0.5, 6: 0.5, 7: 1.0, 8: 0.5, 9: 1.0, 10: 1.0, 11: 0.5, 12: 1.0, 13: 1.0, 14: 1.0, 15: 1.0, 16: 1.0, 17: 1.0, 18: 1.0, 19: 1.5, 20: 1.5, 21: 1.25, 22: 1.25, 23: 1.0, 24: 1.5, 25: 1.0, 26: 1.5},
    9: {0: 2.0, 1: 1.0, 2: 0.5, 3: 1.0, 4: 2.0, 5: 1.0, 6: 1.0, 7: 1.0, 8: 1.0, 9: 0.5, 10: 0.5, 11: 1.0, 12: 1.0, 13: 2.0, 14: 2.0, 15: 1.0, 16: 1.0, 17: 0.5, 18: 0.5, 19: 1.5, 20: 1.5, 21: 1.5, 22: 0.75, 23: 0.5, 24: 1.5, 25: 2.0, 26: 0.5},
    10: {0: 1.0, 1: 0.5, 2: 1.0, 3: 1.0, 4: 0.5, 5: 2.0, 6: 2.0, 7: 1.0, 8: 1.0, 9: 2.0, 10: 0.5, 11: 2.0, 12: 0.5, 13: 1.0, 14: 1.0, 15: 1.0, 16: 1.0, 17: 0.5, 18: 1.0, 19: 1.0, 20: 0.75, 21: 1.25, 22: 1.5, 23: 1.0, 24: 0.75, 25: 1.0, 26: 0.75},
    11: {0: 0.5, 1: 1.0, 2: 0.5, 3: 0.5, 4: 1.0, 5: 2.0, 6: 1.0, 7: 2.0, 8: 2.0, 9: 1.0, 10: 0.5, 11: 0.5, 12: 1.0, 13: 1.0, 14: 2.0, 15: 1.0, 16: 1.0, 17: 0.5, 18: 1.0, 19: 0.75, 20: 1.5, 21: 0.75, 22: 1.25, 23: 0.5, 24: 0.75, 25: 1.0, 26: 0.5},
    12: {0: 1.0, 1: 2.0, 2: 1.0, 3: 1.0, 4: 0.5, 5: 0.5, 6: 2.0, 7: 1.0, 8: 1.0, 9: 1.0, 10: 2.0, 11: 0.5, 12: 0.5, 13: 1.0, 14: 1.0, 15: 1.0, 16: 1.0, 17: 1.0, 18: 1.0, 19: 1.0, 20: 1.5, 21: 0.5, 22: 0.75, 23: 1.0, 24: 0.75, 25: 2.0, 26: 1.5},
    13: {0: 0.5, 1: 2.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.0, 6: 1.0, 7: 1.0, 8: 0.5, 9: 2.0, 10: 1.0, 11: 0.5, 12: 1.0, 13: 0.5, 14: 1.0, 15: 1.0, 16: 1.0, 17: 2.0, 18: 0.5, 19: 0.75, 20: 1.5, 21: 0.75, 22: 1.0, 23: 1.0, 24: 0.75, 25: 1.0, 26: 1.0},
    14: {0: 1.0, 1: 1.0, 2: 2.0, 3: 2.0, 4: 1.0, 5: 1.0, 6: 2.0, 7: 0.5, 8: 1.0, 9: 0.5, 10: 2.0, 11: 1.0, 12: 1.0, 13: 1.0, 14: 0.5, 15: 1.0, 16: 1.0, 17: 0.5, 18: 2.0, 19: 1.5, 20: 0.75, 21: 1.0, 22: 1.5, 23: 0.5, 24: 1.0, 25: 1.0, 26: 4.0},
    15: {0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.0, 6: 1.0, 7: 1.0, 8: 1.0, 9: 1.0, 10: 1.0, 11: 1.0, 12: 1.0, 13: 1.0, 14: 1.0, 15: 1.0, 16: 1.0, 17: 1.0, 18: 1.0, 19: 1.0, 20: 1.0, 21: 1.0, 22: 1.0, 23: 1.0, 24: 1.0, 25: 1.0, 26: 1.0},
    16: {0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.0, 6: 1.0, 7: 1.0, 8: 1.0, 9: 1.0, 10: 1.0, 11: 1.0, 12: 1.0, 13: 1.0, 14: 1.0, 15: 1.0, 16: 1.0, 17: 1.0, 18: 1.0, 19: 1.0, 20: 1.0, 21: 1.0, 22: 1.0, 23: 1.0, 24: 1.0, 25: 1.0, 26: 1.0},
    17: {0: 1.0, 1: 1.0, 2: 0.5, 3: 1.0, 4: 2.0, 5: 0.5, 6: 1.0, 7: 1.0, 8: 1.0, 9: 1.0, 10: 1.0, 11: 2.0, 12: 1.0, 13: 0.5, 14: 1.0, 15: 1.0, 16: 1.0, 17: 0.5, 18: 0.5, 19: 0.75, 20: 1.0, 21: 4.0, 22: 0.5, 23: 0.5, 24: 1.0, 25: 1.0, 26: 0.75},
    18: {0: 1.0, 1: 1.0, 2: 0.5, 3: 0.5, 4: 2.0, 5: 1.0, 6: 1.0, 7: 1.0, 8: 0.5, 9: 1.0, 10: 0.5, 11: 2.0, 12: 1.0, 13: 1.0, 14: 1.0, 15: 1.0, 16: 1.0, 17: 2.0, 18: 0.5, 19: 0.75, 20: 1.0, 21: 4.0, 22: 0.75, 23: 1.0, 24: 1.0, 25: 0.0, 26: 0.5},
    19: {0: 1.25, 1: 1.5, 2: 0.75, 3: 0.75, 4: 1.0, 5: 0.75, 6: 1.0, 7: 1.5, 8: 0.5, 9: 4.0, 10: 1.0, 11: 1.25, 12: 1.0, 13: 0.75, 14: 0.75, 15: 1.0, 16: 1.0, 17: 1.5, 18: 1.25, 19: 0.75, 20: 1.12, 21: 1.12, 22: 0.75, 23: 1.0, 24: 1.12, 25: 1.5, 26: 0.88},
    20: {0: 0.75, 1: 0.75, 2: 1.5, 3: 1.5, 4: 1.5, 5: 1.0, 6: 4.0, 7: 0.75, 8: 0.75, 9: 0.5, 10: 4.0, 11: 0.75, 12: 1.0, 13: 0.75, 14: 1.25, 15: 1.0, 16: 1.0, 17: 0.5, 18: 1.25, 19: 1.12, 20: 1.0, 21: 1.12, 22: 1.25, 23: 0.75, 24: 0.88, 25: 1.0, 26: 2.75},
    21: {0: 0.75, 1: 0.75, 2: 1.25, 3: 0.75, 4: 0.75, 5: 1.5, 6: 1.0, 7: 4.0, 8: 1.25, 9: 0.75, 10: 1.25, 11: 1.25, 12: 1.5, 13: 1.0, 14: 1.5, 15: 1.0, 16: 1.0, 17: 0.5, 18: 0.75, 19: 0.88, 20: 1.12, 21: 1.0, 22: 1.38, 23: 0.75, 24: 1.12, 25: 1.0, 26: 1.25},
    22: {0: 1.0, 1: 1.5, 2: 1.25, 3: 1.5, 4: 0.75, 5: 0.75, 6: 0.75, 7: 1.25, 8: 1.25, 9: 1.5, 10: 0.75, 11: 0.75, 12: 1.25, 13: 1.0, 14: 0.75, 15: 1.0, 16: 1.0, 17: 1.5, 18: 1.5, 19: 1.25, 20: 1.12, 21: 0.75, 22: 1.0, 23: 0.5, 24: 1.12, 25: 1.0, 26: 1.0},
    23: {0: 0.5, 1: 1.0, 2: 1.0, 3: 1.0, 4: 0.5, 5: 2.0, 6: 0.5, 7: 0.5, 8: 1.0, 9: 2.0, 10: 1.0, 11: 2.0, 12: 2.0, 13: 1.0, 14: 1.0, 15: 1.0, 16: 1.0, 17: 2.0, 18: 1.0, 19: 1.0, 20: 1.0, 21: 1.25, 22: 1.5, 23: 0.5, 24: 1.25, 25: 0.5, 26: 1.0},
    24: {0: 0.75, 1: 4.0, 2: 1.0, 3: 0.75, 4: 0.75, 5: 0.5, 6: 1.5, 7: 1.0, 8: 0.75, 9: 1.0, 10: 1.5, 11: 0.75, 12: 1.25, 13: 1.5, 14: 1.0, 15: 1.0, 16: 1.0, 17: 1.0, 18: 1.0, 19: 1.12, 20: 1.5, 21: 0.75, 22: 0.75, 23: 1.5, 24: 1.0, 25: 1.5, 26: 1.25},
    25: {0: 1.0, 1: 1.0, 2: 2.0, 3: 0.5, 4: 1.0, 5: 2.0, 6: 2.0, 7: 1.0, 8: 1.0, 9: 0.5, 10: 1.0, 11: 0.5, 12: 0.5, 13: 1.0, 14: 1.0, 15: 1.0, 16: 1.0, 17: 1.0, 18: 1.0, 19: 0.75, 20: 1.0, 21: 0.75, 22: 4.0, 23: 2.0, 24: 0.75, 25: 0.5, 26: 1.5},
    26: {0: 1.0, 1: 0.75, 2: 0.75, 3: 1.5, 4: 0.5, 5: 1.5, 6: 1.5, 7: 1.5, 8: 0.75, 9: 4.0, 10: 0.75, 11: 1.5, 12: 0.5, 13: 1.0, 14: 0.75, 15: 1.0, 16: 1.0, 17: 1.25, 18: 1.0, 19: 1.25, 20: 0.75, 21: 1.0, 22: 1.12, 23: 0.75, 24: 0.75, 25: 1.0, 26: 0.75}
}

OP_FIRST_HANDSHAKE = 1185433
OP_CHECK_ACCOUNT = 1183744
OP_GET_WORLD_NUM = 1183751
OP_GET_WORLD_LIST = 1183749
OP_ENTER_WORLD = 1183750
OP_ENTER_SCENE = 1184313
OP_CHECK_ACCOUNT_BACK = 1314816
OP_GET_WORLD_NUM_BACK = 1314823
OP_GET_WORLD_LIST_BACK = 1314821
OP_ENTER_WORLD_BACK = 1314822
OP_ENTER_SCENE_BACK = 1315395

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
OP_DRAGON_ENTER = 1186180
OP_DRAGON_ENTER_BACK = 1317252
OP_DRAGON_BATTLE_ENTER = 1186049
OP_DRAGON_ROUND_ADVANCE = 1186056
OP_DRAGON_ROUND_RESULT_BACK = 1317122
OP_DRAGON_MONSTER_DOWN_BACK = 1317126
OP_DRAGON_EXIT = 1186323
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

OP_CULTIVATE_LIST = 1187329
OP_CULTIVATE_PREVIEW = 1187120
OP_CULTIVATE_PREVIEW_BACK = 1330480
OP_CULTIVATE_START = 1187121
OP_CULTIVATE_START_BACK = 1330481
OP_CULTIVATE_STATE = 1187122
OP_CULTIVATE_STATE_BACK = 1330482
OP_CULTIVATE_END = 1187123
OP_CULTIVATE_END_BACK = 1330483
OP_CULTIVATE_SPEEDUP = 1187128
OP_CULTIVATE_SPEEDUP_BACK = 1330488
OP_CULTIVATE_REFRESH = 1184833
OP_CULTIVATE_REFRESH_BACK = 1324097
OP_ENTER_COPY = 1184771
OP_GATEWAY_INDULGE_BACK = 1315586
OP_REMOVE_PLAYER_BACK = 1315328

class KabuClient:
    def __init__(self, host: str, log_callback=None, *, port: Optional[int] = None):
        self.host = host
        self.port = port
        self.log_callback = log_callback or print
        self.sock: Optional[socket.socket] = None
        self.connected = False
        self.logged_in = False
        self.in_scene = False
        self.current_scene_id: Optional[int] = None
        self.recv_buffer = b""
        self.msg_handlers: Dict[int, Callable[[int, bytes], None]] = {
            OP_CHECK_ACCOUNT_BACK: self._handle_account_response,
            OP_GET_WORLD_NUM_BACK: self._handle_world_num_response,
            OP_GET_WORLD_LIST_BACK: self._handle_world_list_response,
            OP_ENTER_WORLD_BACK: self._handle_enter_world_response,
            OP_ENTER_SCENE_BACK: self._handle_enter_scene_response,
            OP_BATTLE_START_BACK: self._handle_battle_start,
            OP_BATTLE_ROUND_START_BACK: self._handle_battle_round_start,
            OP_BATTLE_ROUND_RESULT_BACK: self._handle_battle_round_result,
            OP_BATTLE_END_BACK: self._handle_battle_end,
            OP_DRAGON_QUERY_BACK: self._handle_dragon_progress_response,
            OP_DRAGON_ACTION_BACK: self._handle_dragon_action_response,
            OP_DRAGON_ENTER_BACK: self._handle_dragon_enter_response,
            OP_DRAGON_ROUND_RESULT_BACK: self._handle_dragon_round_result,
            OP_DRAGON_MONSTER_DOWN_BACK: self._handle_dragon_monster_down,
            OP_GET_SPIRIT_LIST_BACK: self._handle_spirit_list_response,
            OP_GET_PACKAGE_BACK: self._handle_package_response,
            OP_PEIYU_CAN_ENTER_BACK: self._handle_peiyu_enter_response,
            OP_PEIYU_STATUS_BACK: self._handle_peiyu_status_response,
            OP_PEIYU_GROW_BACK: self._handle_peiyu_grow_response,
            OP_PEIYU_FOOD_BACK: self._handle_peiyu_food_response,
            OP_PEIYU_HARVEST_BACK: self._handle_peiyu_harvest_response,
            OP_CULTIVATE_PREVIEW_BACK: self._handle_cultivate_preview_response,
            OP_CULTIVATE_START_BACK: self._handle_cultivate_start_response,
            OP_CULTIVATE_STATE_BACK: self._handle_cultivate_state_response,
            OP_CULTIVATE_END_BACK: self._handle_cultivate_end_response,
            OP_CULTIVATE_SPEEDUP_BACK: self._handle_cultivate_speedup_response,
            OP_GATEWAY_INDULGE_BACK: self._handle_indulge_response,
            OP_REMOVE_PLAYER_BACK: self._handle_remove_player_response,
        }
        self._spirit_names: Optional[Dict[int, str]] = None
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
            "auto_mode": False,
            "auto_lottery_queue": [],
            "current_stage": 1,
            "auto_request_at": None,
            "in_dragon": False,
            "dragon_battle_active": False,
            "dragon_targets": [],
        }
        self.spirit_list: List[Dict[str, Any]] = []
        self.inventory: List[Dict[str, Any]] = []
        self.peiyu_state: Dict[str, Any] = {}
        self.element_advantage: Dict[int, Dict[int, float]] = ELEMENT_NODE
        self.enemy_element = 0

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
            self.current_scene_id = struct.unpack_from("<I", body, offset)[0]
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
        if self.current_scene_id is not None and self.current_scene_id > 0:
            self.log(f"发送进场景请求，场景ID={self.current_scene_id}")
            self.send_cmd(OP_ENTER_SCENE, self.current_scene_id)
        else:
            self.log("未能从进世界回包解析到场景ID，跳过进场景请求", "WRAN")

    def _handle_enter_scene_response(self, m_params: int, _body: bytes):
        self.in_scene = True
        self.log(f"已进入场景（回包 mParams={m_params}），功能请求可用")

    def set_auto_battle(self, enabled: bool):
        self.auto_battle_enabled = bool(enabled)
        if not enabled:
            self.log("自动战斗AI已关闭")
        else:
            self.log("自动战斗AI已启用；策略为可用技能、必要时换宠，禁用未分类道具")

    def _handle_battle_start(self, m_params: int, body: bytes):
        if m_params < 0:
            return
        if self.dragon_state.get("in_dragon"):
            self._handle_dragon_battle_start(m_params, body)
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

    def _handle_dragon_battle_start(self, m_params: int, body: bytes):
        self.dragon_state["dragon_battle_active"] = True
        self.dragon_state["dragon_targets"] = []
        skillsets = []
        switch_ids = []
        pets = []
        enemies = []
        try:
            offset = 0
            while offset + 4 <= len(body):
                state, offset = self._read_int(body, offset)
                if state == -1:
                    break
                if state not in (1, 2):
                    continue
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
                    break
                skills = []
                ok = True
                for _ in range(skill_count):
                    if offset + 12 > len(body):
                        ok = False
                        break
                    sid2, pp, mpp = struct.unpack("<III", body[offset:offset + 12])
                    offset += 12
                    skills.append((sid2, pp, mpp))
                if not ok:
                    break
                is_mine = (self.user_id is not None and user_id == self.user_id)
                actor = {
                    "sid": sid, "group_type": group_type, "hp": hp,
                    "max_hp": max(max_hp, hp, 1), "level": level,
                    "element": element, "spirit_id": spirit_id,
                    "unique_id": unique_id, "user_id": user_id, "skills": skills,
                }
                if is_mine:
                    skillsets.append(skills)
                    switch_ids.append(unique_id)
                    pets.append({"hp": hp, "maxhp": max(max_hp, hp, 1),
                                 "element": element, "spirit_id": spirit_id,
                                 "unique_id": unique_id, "sid": sid})
                else:
                    enemies.append(actor)
                if state == 2 and not is_mine:
                    if offset + 4 > len(body):
                        break
                    _, offset = self._read_int(body, offset)
        except (ValueError, struct.error) as exc:
            self.log(f"[龙腾] 战斗初始化通用解析失败：{exc}，回退 uid 扫描", "WRAN")
            skillsets, switch_ids, pets = self._dragon_parse_by_uid(body)
        self.dragon_state["dragon_skills"] = skillsets
        self.dragon_state["dragon_switch_ids"] = switch_ids
        self.dragon_state["dragon_pets"] = pets
        self.dragon_state["dragon_enemies"] = enemies
        self.dragon_state["dragon_skill_idx"] = 0
        self.dragon_state["dragon_sub_idx"] = 0
        self.dragon_state["dragon_waiting"] = "idle"
        self.dragon_state["dragon_down_count"] = 0
        self.dragon_state["dragon_enemy_alive"] = len(enemies)
        self.dragon_state["dragon_refresh_needed"] = False
        enemy_desc = "、".join(
            f"[{e['element']}#{e['spirit_id']} hp{e['hp']}]" for e in enemies
        ) or "无"
        self.log(f"[龙腾] 战斗初始化回包 (mP={m_params}，{len(body)}字节)："
                 f"我方候选宠 {len(skillsets)} 组，敌方/Boss {len(enemies)} 只（{enemy_desc}）", "INFO")
        self.send_cmd(OP_DRAGON_BATTLE_ENTER, 0)

    def _dragon_parse_by_uid(self, body: bytes):
        skillsets = []
        switch_ids = []
        pets = []
        if self.user_id is not None:
            uid_bytes = struct.pack("<I", self.user_id)
            pos = 0
            while True:
                idx = body.find(uid_bytes, pos)
                if idx < 0:
                    break
                off = idx + 4
                if off + 4 > len(body):
                    break
                cnt = struct.unpack("<I", body[off:off + 4])[0]
                if 1 <= cnt <= 8:
                    off += 4
                    sk = []
                    ok = True
                    for _ in range(cnt):
                        if off + 12 > len(body):
                            ok = False
                            break
                        sid, pp, mpp = struct.unpack("<III", body[off:off + 12])
                        sk.append((sid, pp, mpp))
                        off += 12
                    if ok:
                        skillsets.append(sk)
                        if idx >= 8:
                            switch_ids.append(struct.unpack("<I", body[idx - 8:idx - 4])[0])
                            pets.append({"hp": 1, "maxhp": 1, "element": 0, "spirit_id": 0})
                        else:
                            switch_ids.append(0)
                            pets.append({"hp": 1, "maxhp": 1, "element": 0, "spirit_id": 0})
                pos = idx + 1
        return skillsets, switch_ids, pets

    def _handle_dragon_monster_down(self, m_params: int, _body: bytes):
        if not self.dragon_state.get("dragon_battle_active"):
            return
        switch_ids = self.dragon_state.get("dragon_switch_ids") or []
        pi = self.dragon_state.get("dragon_skill_idx", 0)
        nxt = pi + 1
        self.dragon_state["dragon_down_count"] = (
            self.dragon_state.get("dragon_down_count", 0) + 1
        )
        down = self.dragon_state["dragon_down_count"]
        self.log(f"[龙腾] 我方宠倒下（累计 {down} 只）", "WRAN")
        if nxt >= len(switch_ids):
            self.log("[龙腾] 我方出战宠全部倒下，退出副本", "ERROR")
            self.dragon_state["dragon_refresh_needed"] = True
            self.dragon_exit_copy()
            return
        target = switch_ids[nxt]
        self.dragon_state["dragon_skill_idx"] = nxt
        self.dragon_state["dragon_sub_idx"] = 0
        self.log(f"[龙腾] 宠倒下，切换到候选宠 #{nxt} (ID={target})", "WRAN")
        self.send_cmd(OP_BATTLE_USER_OP, 1, [target])
        self.send_cmd(OP_DRAGON_ROUND_ADVANCE, 0)
        self.dragon_state["dragon_waiting"] = "await_advance"

    def _element_adv(self, att, dfd):
        if att not in ELEMENT_NODE or dfd not in ELEMENT_NODE:
            return 0.0
        a = ELEMENT_NODE[att].get(dfd, 1.0)
        b = ELEMENT_NODE[dfd].get(att, 1.0)
        return a if a > b else 0.0

    def _dragon_decide_action(self):

        sets = self.dragon_state.get("dragon_skills") or []
        if not sets:
            self.log("[决策] 无候选技能，无法决策", "ERROR")
            return ("idle", None, 0.0)
        pi = min(self.dragon_state.get("dragon_skill_idx", 0), len(sets) - 1)
        sk = sets[pi]
        pets = self.dragon_state.get("dragon_pets") or []
        cur_hp = pets[pi]["hp"] if pi < len(pets) else 1
        cur_max = pets[pi]["maxhp"] if pi < len(pets) else 1
        cur_ratio = cur_hp / max(cur_max, 1)

        enemies = self.dragon_state.get("dragon_enemies") or []
        enemy_ele = enemies[0]["element"] if enemies else 0
        self.enemy_element = enemy_ele
        enemy_nature = ELEMENT_TO_NATURE.get(enemy_ele, "")
        if enemy_ele:
            self.log(f"[决策] 敌方/Boss 属性 element={enemy_ele} 系别={enemy_nature or '未知'}", "INFO")
        cur_ele = pets[pi]["element"] if pi < len(pets) else 0
        cur_bonus = self._element_adv(cur_ele, enemy_ele)

        candidates = []
        for si, (sid, pp, mpp) in enumerate(sk):
            if pp <= 0:
                continue
            s = 50.0 - si * 5.0 + min(pp, mpp) * 1.0
            if cur_ratio < 0.3:
                s -= 12.0
            if cur_bonus:
                s += cur_bonus * 30.0
            candidates.append((f"技能{sid}", s, ("skill", sid)))
        switch_ids = self.dragon_state.get("dragon_switch_ids") or []
        for idx in range(pi + 1, len(sets)):
            if idx >= len(pets):
                break
            ratio = pets[idx]["hp"] / max(pets[idx]["maxhp"], 1)
            s = 10.0 + ratio * 60.0
            ele = pets[idx].get("element", 0)
            if self._element_adv(ele, enemy_ele) > 0:
                s += 120.0
                self.log(f"[决策] 候选宠#{idx}(elem={ele}) 克制敌方(elem={enemy_ele})，优先上阵", "INFO")
            if cur_ratio < 0.25:
                s += 30.0
            candidates.append((f"换宠#{idx}", s, ("switch", idx)))

        if not candidates:
            self.log("[决策] 无可执行候选（当前宠技能全耗），切换候选宠兜底", "WRAN")
            nxt = pi + 1
            if nxt < len(sets):
                return ("switch", nxt, 0.6)
            return ("idle", None, 0.0)

        total = sum(c[1] for c in candidates)
        best = max(candidates, key=lambda c: c[1])
        conf = best[1] / total if total > 0 else 1.0
        detail = " ".join(
            f"{n}={s:.0f}({s / total * 100:.0f}%)" for n, s, _ in candidates
        )
        self.log(f"[决策] 候选[{detail}] → 选 {best[0]} 置信{conf:.2f}", "INFO")
        return best[2] + (conf,)

    def _dragon_round_action(self):
        pets = self.dragon_state.get("dragon_pets") or []
        switch_ids = self.dragon_state.get("dragon_switch_ids") or []
        pi = min(self.dragon_state.get("dragon_skill_idx", 0), len(pets) - 1)
        if pets and pi < len(pets) and pets[pi].get("hp", 1) <= 0:
            nxt = pi + 1
            if nxt < len(switch_ids) and switch_ids[nxt]:
                self.dragon_state["dragon_skill_idx"] = nxt
                self.dragon_state["dragon_sub_idx"] = 0
                self.log(f"[龙腾] 当前宠血量归零，兜底切换到候选宠 #{nxt} "
                         f"(UID={switch_ids[nxt]})", "WRAN")
                self.send_cmd(OP_BATTLE_USER_OP, 1, [switch_ids[nxt]])
                self.send_cmd(OP_DRAGON_ROUND_ADVANCE, 0)
                self.dragon_state["dragon_waiting"] = "await_advance"
                return
            self.log("[龙腾] 当前宠倒下且无候选可切，触发退出副本", "ERROR")
            self.dragon_state["dragon_refresh_needed"] = True
            self.dragon_exit_copy()
            return
        action, payload, conf = self._dragon_decide_action()
        if action == "skill":
            sid = payload
            self.dragon_state["dragon_waiting"] = "await_attack"
            self.send_cmd(OP_BATTLE_USER_OP, 0, [2, sid])
        elif action == "switch":
            idx = payload
            self.dragon_state["dragon_skill_idx"] = idx
            self.dragon_state["dragon_sub_idx"] = 0
            switch_ids = self.dragon_state.get("dragon_switch_ids") or []
            target = switch_ids[idx] if idx < len(switch_ids) else 0
            self.log(f"[决策] 切换到候选宠 #{idx} (ID={target})", "USER")
            self.send_cmd(OP_BATTLE_USER_OP, 1, [target])
            self.send_cmd(OP_DRAGON_ROUND_ADVANCE, 0)
            self.dragon_state["dragon_waiting"] = "await_advance"
        elif action == "refresh":
            self.log("[决策] 触发刷新（重新登录继续打，无损）", "USER")
            self.dragon_state["dragon_refresh_needed"] = True
            self.dragon_exit_copy()

    def _load_spirit_names(self):
        """从 sprite.xml 加载妖怪ID->名称映射（懒加载）。"""
        self._spirit_names = {}
        candidates = []
        if getattr(sys, "_MEIPASS", None):
            candidates.append(os.path.join(sys._MEIPASS, "sprite.xml"))
        candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sprite.xml"))
        candidates.append(os.path.join(os.getcwd(), "sprite.xml"))
        candidates.append("sprite.xml")
        for path in candidates:
            try:
                if not os.path.exists(path):
                    continue
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    txt = f.read()
                for m in re.finditer(r'<sprite id="(\d+)">\s*<name>([^<]*)</name>', txt):
                    self._spirit_names[int(m.group(1))] = m.group(2).strip()
                if self._spirit_names:
                    self.log(f"已加载妖怪名称表 {len(self._spirit_names)} 条（{path}）", "INFO")
                return
            except Exception as exc:
                self.log(f"加载妖怪名称表失败：{exc}", "WRAN")

    def _spirit_name(self, sid: int) -> str:
        if self._spirit_names is None:
            self._load_spirit_names()
        nm = (self._spirit_names or {}).get(sid)
        return nm if nm else ""

    def _sid_label(self, sid: int) -> str:
        nm = self._spirit_name(sid)
        return f"{nm}(#{sid})" if nm else f"#{sid}"

    def _log_battle_round(self, body: bytes, tag: str = "战斗"):
        """解析战斗回合回包 body 并打日志，用于战斗过程可视化回显。"""
        if not body:
            return
        try:
            has_battle, offset = self._read_int(body, 0)
            if has_battle != 1:
                self.log(f"[{tag}] 回合回包：无行动数据", "INFO")
                return
            attacker_sid, offset = self._read_int(body, offset)
            skill_id, offset = self._read_int(body, offset)
            defender_sid, offset = self._read_int(body, offset)
            miss, offset = self._read_int(body, offset)
            if miss == 0:
                _, offset = self._read_int(body, offset)
                attacker_hp, offset = self._read_int(body, offset)
                defender_hp, offset = self._read_int(body, offset)
                self.log(f"[{tag}] {self._sid_label(attacker_sid)} 用技能{skill_id} 攻击 "
                         f"{self._sid_label(defender_sid)} 命中，"
                         f"当前血量 {attacker_hp}/{defender_hp}", "BATTLE")
            else:
                self.log(f"[{tag}] {self._sid_label(attacker_sid)} 用技能{skill_id} 攻击 "
                         f"{self._sid_label(defender_sid)} 未命中(MISS)", "BATTLE")
        except (ValueError, struct.error) as exc:
            self.log(f"解析战斗回合回显失败：{exc}", "ERROR")

    def _handle_dragon_round_result(self, m_params: int, body: bytes):
        if not self.dragon_state.get("dragon_battle_active"):
            return
        if m_params == 0:
            self._log_battle_round(body, "龙腾")
            self._update_dragon_hp_from_round(body)
        waiting = self.dragon_state.get("dragon_waiting", "idle")
        if waiting == "await_attack":
            self.dragon_state["dragon_waiting"] = "await_advance"
            self.send_cmd(OP_DRAGON_ROUND_ADVANCE, 0)
        elif waiting == "await_advance" and m_params == 1:
            self.dragon_state["dragon_waiting"] = "idle"

    def _update_dragon_hp_from_round(self, body: bytes):
        """从战斗回合回包同步我方宠血量，用于宠死即切兜底。"""
        if not body:
            return
        try:
            has_battle, offset = self._read_int(body, 0)
            if has_battle != 1:
                return
            attacker_sid, offset = self._read_int(body, offset)
            _, offset = self._read_int(body, offset)  # skill_id
            defender_sid, offset = self._read_int(body, offset)
            miss, offset = self._read_int(body, offset)
            if miss != 0:
                return
            _, offset = self._read_int(body, offset)  # 伤害
            attacker_hp, offset = self._read_int(body, offset)
            defender_hp, offset = self._read_int(body, offset)
        except (ValueError, struct.error):
            return
        pets = self.dragon_state.get("dragon_pets") or []
        for p in pets:
            if p.get("sid") == attacker_sid:
                p["hp"] = attacker_hp
            if p.get("sid") == defender_sid:
                p["hp"] = defender_hp
        pi = min(self.dragon_state.get("dragon_skill_idx", 0), len(pets) - 1)
        if pets and pi < len(pets) and pets[pi].get("hp", 1) <= 0:
            self.dragon_state["dragon_down_count"] = (
                self.dragon_state.get("dragon_down_count", 0) + 1
            )
            self.log(f"[龙腾] 回合血量跟踪：当前宠血量归零，等待/触发切换", "WRAN")

    def _handle_indulge_response(self, m_params: int, body: bytes):
        """1315586 防沉迷/健康系统回包：状态、剩余时长、在线时长。"""
        if not body:
            self.log(f"[防沉迷] 回包 mP={m_params}（空body）", "INFO")
            return
        try:
            if m_params == 0:
                self.log("[防沉迷] 收到健康系统提示", "INFO")
                return
            offset = 0
            status, offset = self._read_int(body, offset)
            surplus, offset = self._read_int(body, offset)
            ptype, offset = self._read_int(body, offset)
            statetime = system_times = online_time = 0
            if status != 8 and status != 4 and offset + 4 <= len(body):
                statetime, offset = self._read_int(body, offset)
            if status != 8 and offset + 4 <= len(body):
                system_times, offset = self._read_int(body, offset)
            if status != 8 and offset + 4 <= len(body):
                online_time, offset = self._read_int(body, offset)
            status_names = {1: "正常", 2: "临近限时", 3: "限时", 4: "无法进入", 8: "关停"}
            self.log(f"[防沉迷] 状态={status}({status_names.get(status, '?')}) "
                     f"剩余={surplus} 限时={statetime} 系统时间={system_times} "
                     f"在线={online_time} 类型={ptype}", "INFO")
        except (ValueError, struct.error) as exc:
            self.log(f"[防沉迷] 回包解析失败：{exc}", "ERROR")

    def _handle_remove_player_response(self, m_params: int, _body: bytes):
        """1315328 场景玩家离开回包：仅回显，不参与任何决策。"""
        self.log(f"[场景] 有玩家离开当前场景，成员变动 (mP={m_params})", "INFO")

    def _handle_battle_round_start(self, m_params: int, _body: bytes):
        if self.dragon_state.get("dragon_battle_active"):
            self.dragon_state["dragon_round"] = self.dragon_state.get("dragon_round", 0) + 1
            self.log(f"[龙腾] 第 {self.dragon_state['dragon_round']} 回合开始，操作时限={m_params}",
                     "BATTLE")
            self._dragon_round_action()
            return
        if not self.battle_state["active"]:
            return
        self.battle_round += 1
        self.log(f"第 {self.battle_round} 回合开始，操作时限参数={m_params}")
        if self.auto_battle_enabled:
            self._choose_battle_action()

    def _handle_battle_round_result(self, m_params: int, body: bytes):
        if m_params == 0:
            self._log_battle_round(body, "战斗")
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
        target_ele = target.get("element", 0)
        active_ele = active.get("element", 0)
        if self._element_adv(active_ele, target_ele) <= 0:
            better = next(
                (actor for actor in player_team
                 if actor["hp"] > 0 and actor["unique_id"] != active["unique_id"]
                 and self._element_adv(actor.get("element", 0), target_ele) > 0),
                None,
            )
            if better is not None:
                self.log(f"克制决策：当前妖怪(元素{active_ele})不克制敌方(元素{target_ele})，"
                         f"切换至克制妖怪 {better['unique_id']}", "INFO")
                if self.send_cmd(OP_BATTLE_USER_OP, 1, [better["unique_id"]]):
                    self.auto_action_round = self.battle_round
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
             if actor["hp"] > 0 and actor["unique_id"] != active["unique_id"]
             and self._element_adv(actor.get("element", 0), target_ele) > 0),
            None,
        )
        if reserve is None:
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
        if self.dragon_state.get("dragon_battle_active"):
            self.dragon_state["dragon_battle_active"] = False
            self.log("[龙腾] 龙腾战斗结束（结算回包）", "INFO")
            if self.dragon_state.get("auto_mode") and self.dragon_state.get("in_dragon"):
                if self.dragon_state.get("life_chance", 0) > 0:
                    self.log("[龙腾] 一键连打：免费补血后进入下一关", "USER")
                    self.dragon_medal_heal(False)
                else:
                    self.log("[龙腾] 一键连打：免费补血次数已用完，直接查询下一关", "USER")
                    self.dragon_query_progress()
            return
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
            f"进度：第 {progress['next_combat_index'] + 1}/17 场"
            f"({'终局战(Boss)' if progress['next_combat_index'] >= 17 else '普通战'})，"
            f"当前场次={progress['current_combat']}，"
            f"候选妖怪={len(candidates)}只"
        )
        self.log("[龙腾] 候选列表：" + "、".join(candidates))
        if wins:
            self.log("[龙腾] 已胜场：" + "、".join(wins))

        if self.dragon_state["auto_running"]:
            self.dragon_state["auto_running"] = False
            self.dragon_state["auto_request_at"] = None
            if progress["today_pass"] != 0:
                if self.dragon_state.get("auto_mode"):
                    self.log("[龙腾] 今日已通关，一键连打自动抽取奖励", "USER")
                    self.dragon_state["auto_lottery_queue"] = [1, 2]
                    nxt = self.dragon_state["auto_lottery_queue"].pop(0)
                    self.dragon_lottery(nxt)
                else:
                    self.log("今日龙腾已通关，不再发起战斗")
                return
            if not self.dragon_state.get("in_dragon"):
                self.log("尚未进入龙腾副本，先补发进副本请求", "WRAN")
                self.dragon_enter_copy()
                return

            if progress["choice_monster"] == 0:
                self.dragon_state["auto_draw_wait"] = True
                self.log("[龙腾] 尚未抽取出战妖怪，发送抽取请求（每天首次进副本有效）", "USER")
                self.send_cmd(OP_DRAGON_ACTION, DRAGON_COPY_MPARAMS, [])
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
        if self.dragon_state.get("auto_draw_wait"):
            self.dragon_state["auto_draw_wait"] = False
            if result == 0:
                self.log("[龙腾] 抽取出战回包成功，重新查询进度以确认出战", "USER")
                self.dragon_state["auto_running"] = True
                self.dragon_query_progress()
                return
            self.log("[龙腾] 抽取出战回包异常，稍后重试", "WRAN")
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
        elif operation == 3 and result == 0:
            details.append("抽奖成功")
            try:
                if offset + 4 <= len(body):
                    idx, offset = self._read_int(body, offset)
                    details.append(f"奖励序号={idx}")
                while offset + 4 <= len(body):
                    val, offset = self._read_int(body, offset)
                    details.append(f"奖励字段={val}")
            except (ValueError, struct.error):
                pass
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

        if operation == 5 and self.dragon_state.get("auto_mode") and self.dragon_state.get("in_dragon"):
            self.log("[龙腾] 一键连打：补血阶段完成，查询下一关", "USER")
            self.dragon_query_progress()
        elif operation == 3 and self.dragon_state.get("auto_mode"):
            q = self.dragon_state.get("auto_lottery_queue") or []
            if q:
                nxt = q.pop(0)
                self.log(f"[龙腾] 一键连打：继续抽取奖励类型 {nxt}", "USER")
                self.dragon_lottery(nxt)
            else:
                self.dragon_state["auto_running"] = False
                self.dragon_state["auto_request_at"] = None
                self.dragon_state["auto_mode"] = False
                self.dragon_state["auto_lottery_queue"] = []
                self.log("[龙腾] 奖励抽取完毕，一键连打结束", "USER")

    def _handle_dragon_enter_response(self, m_params: int, body: bytes):
        self.dragon_state["in_dragon"] = True
        if m_params == DRAGON_COPY_MPARAMS and len(body) >= 4:
            result, _ = self._read_int(body, 0)
            self.log(f"[龙腾] 已进入副本，入口回包 result={result}")
        else:
            self.log(f"[龙腾] 已进入副本 (mP={m_params})")

    def dragon_query_progress(self):
        return self.send_cmd(OP_DRAGON_QUERY, DRAGON_COPY_MPARAMS)

    def dragon_enter_copy(self) -> bool:
        self.log("请求进入龙腾副本", "USER")
        return self.send_cmd(OP_DRAGON_ENTER, DRAGON_COPY_MPARAMS, [0])

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

    def dragon_exit_copy(self) -> bool:
        self.log("请求离开龙腾副本", "USER")
        self.dragon_state["in_dragon"] = False
        self.dragon_state["dragon_battle_active"] = False
        return self.send_cmd(OP_DRAGON_EXIT, 0)

    def dragon_auto_start(self) -> bool:
        if self.dragon_state["auto_running"]:
            started_at = self.dragon_state.get("auto_request_at")
            if started_at is not None and time.monotonic() - started_at < 15:
                self.dragon_state["auto_running"] = False
                self.dragon_state["auto_request_at"] = None
                self.dragon_state["auto_mode"] = False
                self.dragon_state["auto_lottery_queue"] = []
                self.log("已取消等待中的自动推进", "USER")
                return False
            self.log("等待进度回包超时，重新查询", "WRAN")
        self.dragon_state["auto_running"] = True
        self.dragon_state["auto_request_at"] = time.monotonic()
        self.dragon_state["auto_mode"] = True
        self.dragon_state["auto_draw_wait"] = False
        if not self.dragon_state.get("in_dragon"):
            self.dragon_enter_copy()
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

    def _handle_cultivate_preview_response(self, m_params: int, body: bytes):
        if m_params == 1:
            try:
                offset = 0
                iid, offset = self._read_int(body, offset)
                is_own, offset = self._read_int(body, offset)
                skills = []
                sid, offset = self._read_int(body, offset)
                while sid != 0 and offset + 4 <= len(body):
                    skills.append(sid)
                    sid, offset = self._read_int(body, offset)
                self.log(f"[培育仓] 预览妖怪 iid={iid} 自有技能={is_own} 技能={skills}", "INFO")
            except (ValueError, struct.error) as exc:
                self.log(f"[培育仓] 预览回包解析失败：{exc}", "ERROR")
        else:
            self.log(f"[培育仓] 预览失败 mP={m_params}", "WRAN")

    def _handle_cultivate_start_response(self, m_params: int, body: bytes):
        msgs = {-1: "没有可培育的空间", -4: "妖怪不是最高形态，无法培育",
                -5: "含有未知组，无法培育", -6: "妖怪组别不同，无法培育"}
        if m_params == 1:
            try:
                offset = 0
                fid, offset = self._read_int(body, offset)
                mid, offset = self._read_int(body, offset)
                self.log(f"[培育仓] 开始培育已确认（父={fid} 母={mid}）", "INFO")
            except (ValueError, struct.error):
                self.log("[培育仓] 开始培育成功", "INFO")
        else:
            self.log(f"[培育仓] 开始培育失败：{msgs.get(m_params, m_params)}", "WRAN")

    def _handle_cultivate_state_response(self, m_params: int, body: bytes):
        if m_params == 1:
            try:
                offset = 0
                cid, offset = self._read_int(body, offset)
                end_time, offset = self._read_int(body, offset)
                need_time, offset = self._read_int(body, offset)
                fiid, offset = self._read_int(body, offset)
                ftype, offset = self._read_int(body, offset)
                flevel, offset = self._read_int(body, offset)
                miid, offset = self._read_int(body, offset)
                mtype, offset = self._read_int(body, offset)
                mlevel, offset = self._read_int(body, offset)
                egg_iid, offset = self._read_int(body, offset)
                skills = []
                sid, offset = self._read_int(body, offset)
                while sid != 0 and offset + 4 <= len(body):
                    skills.append(sid)
                    sid, offset = self._read_int(body, offset)
                self.peiyu_state.update({
                    "cid": cid, "end_time": end_time, "need_time": need_time,
                    "father": (fiid, ftype, flevel), "mother": (miid, mtype, mlevel),
                    "egg_iid": egg_iid, "skills": skills,
                })
                self.log(f"[培育仓] 状态 CID={cid} 剩余={end_time} 需时={need_time} "
                         f"父={fiid} 母={miid} 蛋={egg_iid} 技能={skills}", "INFO")
            except (ValueError, struct.error) as exc:
                self.log(f"[培育仓] 状态回包解析失败：{exc}", "ERROR")
        else:
            self.log(f"[培育仓] 当前无培育中的蛋（mP={m_params}）", "INFO")

    def _handle_cultivate_end_response(self, m_params: int, body: bytes):
        if m_params in (1, 3):
            try:
                offset = 0
                mid, offset = self._read_int(body, offset)
                fid, offset = self._read_int(body, offset)
                self.log(f"[培育仓] 取回成功：母={mid} 父={fid}（精魄已入包）", "INFO")
            except (ValueError, struct.error):
                self.log("[培育仓] 取回成功（精魄已入包）", "INFO")
        elif m_params == -1:
            self.log("[培育仓] 取回失败：宠物/妖怪仓库没位置了", "WRAN")
        elif m_params == 2:
            self.log("[培育仓] 精魄收藏箱已满，取回将无法获得精魄", "WRAN")
        elif m_params == 0:
            self.log("[培育仓] 取回结果 mP=0", "INFO")
        else:
            self.log(f"[培育仓] 取回失败 mP={m_params}", "WRAN")

    def _handle_cultivate_speedup_response(self, m_params: int, body: bytes):
        try:
            offset = 0
            flag, offset = self._read_int(body, offset)
        except (ValueError, struct.error):
            flag = m_params
        msgs = {1: "成功加速培育进度", -1: "今天已加速过，明天再试", -2: "需选择加速方式",
                -11: "卡布币不足", -12: "道具数量不足"}
        self.log(f"[培育仓] 加速回包 flag={flag}：{msgs.get(flag, '')}", "INFO" if flag == 1 else "WRAN")

    def cultivate_get_monster_list(self):
        return self.send_cmd(OP_CULTIVATE_LIST)

    def cultivate_preview(self, fid: int, mid: int):
        return self.send_cmd(OP_CULTIVATE_PREVIEW, 0, [fid, mid])

    def cultivate_start(self, fid: int, mid: int):
        self.log(f"[培育仓] 开始培育：父={fid} 母={mid}", "USER")
        return self.send_cmd(OP_CULTIVATE_START, 0, [fid, mid])

    def cultivate_get_status(self):
        return self.send_cmd(OP_CULTIVATE_STATE)

    def cultivate_get_egg(self, cid: int, flag: int = 0):
        self.log(f"[培育仓] 取回蛋 CID={cid} flag={flag}", "USER")
        return self.send_cmd(OP_CULTIVATE_END, cid, [flag])

    def cultivate_speed_up(self, mode: int, id_: int, day: int = 0):
        if mode not in (1, 4, 5):
            raise ValueError("mode 必须为 1(日常)/4(卡布币)/5(道具)")
        return self.send_cmd(OP_CULTIVATE_SPEEDUP, mode, [id_, day])

    def cultivate_refresh(self):
        return self.send_cmd(OP_CULTIVATE_REFRESH, 10000, [4])

    def cultivate_enter(self) -> bool:
        """进入培育仓（妖怪孵蛋繁殖）场景 19030。"""
        self.log("[培育仓] 进入培育仓场景（19030）", "USER")
        return self.send_cmd(OP_ENTER_COPY, 19030)

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
