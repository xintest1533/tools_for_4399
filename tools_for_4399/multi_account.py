
import json
import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from .kbxy import KabuClient

class AccountTask:

    def __init__(
        self,
        username: str,
        password: str = "",
        token: str = "",
        server_mode: str = "auto",
        task_name: str = "idle",
        task_kwargs: Optional[Dict[str, Any]] = None,
    ):
        self.username = username
        self.password = password
        self.token = token
        self.server_mode = server_mode
        self.task_name = task_name
        self.task_kwargs = task_kwargs or {}

class MultiAccountRunner:
    def __init__(
        self,
        accounts: List[AccountTask],
        cred_file: str = "credentials.json",
        log: Optional[Callable[[str], None]] = None,
        token_fetcher: Optional[Callable[[str, str], str]] = None,
        task_runner: Optional[Callable[[KabuClient, Dict[str, Any]], None]] = None,
    ):

        self.accounts = accounts
        self.cred_file = cred_file
        self._log = log or (lambda s: print(f"[{threading.current_thread().name}] {s}"))
        self.token_fetcher = token_fetcher
        self.task_runner = task_runner
        self.threads: List[threading.Thread] = []
        self.clients: Dict[str, KabuClient] = {}
        self.status: Dict[str, str] = {}
        self._creds: Dict[str, Any] = self._load_creds()
        self._login_lock = threading.Lock()
        self._last_login_ts = 0.0

    def _throttle_login(self) -> None:
        with self._login_lock:
            now = time.time()
            wait = 60.0 - (now - self._last_login_ts)
            if wait > 0:
                self._log(f"距上次登录不足1分钟，等待 {wait:.0f}s（节流防风控）")
                time.sleep(wait)
            self._last_login_ts = time.time()

    def _load_creds(self) -> Dict[str, Any]:
        if not os.path.exists(self.cred_file):
            return {}
        try:
            with open(self.cred_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_creds(self) -> None:
        try:
            with open(self.cred_file, "w", encoding="utf-8") as f:
                json.dump(self._creds, f, ensure_ascii=False, indent=2)
        except OSError as exc:
            self._log(f"凭证存档失败: {exc}")

    def get_saved_token(self, username: str) -> str:
        return (self._creds.get(username) or {}).get("token", "")

    def save_token(self, username: str, token: str, uid: int = 0, server_id: int = 0) -> None:
        entry = self._creds.setdefault(username, {})
        entry["token"] = token
        if uid:
            entry["uid"] = uid
        if server_id:
            entry["server_id"] = server_id
        entry["saved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self._save_creds()

    def _login_and_enter(self, acc: AccountTask) -> Optional[KabuClient]:
        token = acc.token or self.get_saved_token(acc.username)
        if not token and self.token_fetcher:
            try:
                self._throttle_login()
                token = self.token_fetcher(acc.username, acc.password)
                self.save_token(acc.username, token)
            except Exception as exc:
                self.status[acc.username] = f"登录失败: {exc}"
                self._log(f"[{acc.username}] 拉取 token 失败: {exc}")
                return None
        if not token:
            self.status[acc.username] = "无 token 且未提供 fetcher"
            return None
        client = KabuClient("109.244.56.70", log_callback=lambda m, l="INFO": self._log(
            f"[{acc.username}][{l}] {m}"))
        if not client.connect():
            self.status[acc.username] = "连接网关失败"
            return None
        try:
            ok = client.login(token, server_mode=acc.server_mode)
        except Exception as exc:
            self.status[acc.username] = f"进服失败: {exc}"
            client.close()
            if self.token_fetcher:
                try:
                    self._throttle_login()
                    token = self.token_fetcher(acc.username, acc.password)
                    self.save_token(acc.username, token)
                    client.connect()
                    ok = client.login(token, server_mode=acc.server_mode)
                except Exception as exc2:
                    self._log(f"[{acc.username}] 重拉 token 仍失败: {exc2}")
                    ok = False
            else:
                ok = False
        if not ok:
            self.status[acc.username] = f"认证失败({client.login_error})"
            client.close()
            return None
        self.save_token(acc.username, token,
                        uid=client.user_id or 0,
                        server_id=client.selected_server_id or 0)
        self.status[acc.username] = "已进服"
        return client

    def _run_one(self, acc: AccountTask) -> None:
        self.status[acc.username] = "启动"
        client = self._login_and_enter(acc)
        if client is None:
            self.status[acc.username] = "未进服"
            return
        self.clients[acc.username] = client
        try:
            if self.task_runner:
                self.task_runner(client, acc.task_kwargs)
            else:
                self.status[acc.username] = "已进服，等待任务（idle）"
        finally:
            client.close()
            self.status[acc.username] = "已结束"

    def start_all(self) -> None:
        for acc in self.accounts:
            t = threading.Thread(
                target=self._run_one, args=(acc,),
                name=f"acc-{acc.username}", daemon=True,
            )
            self.threads.append(t)
            t.start()

    def stop_all(self) -> None:
        for client in self.clients.values():
            try:
                client.close()
            except Exception:
                pass

    def wait(self, timeout: Optional[float] = None) -> None:
        for t in self.threads:
            t.join(timeout)

    def status_report(self) -> Dict[str, str]:
        return dict(self.status)
