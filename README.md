# tools_for_4399 工具库

4399 / 卡布西游 登录与网关客户端工具库。
> 注：Python 导入名不能以数字开头，故 `import 4399` 语法非法；导入包名为 `tools_for_4399`。

## 模块
- `tools_for_4399.base` —— 基础方法：AES 密码加密、账号本地存储、平台常量
- `tools_for_4399.kbxy` —— 卡布西游网关客户端（KabuClient）与协议 opcode
- `tools_for_4399.kbxy_standalone` —— 成品函数：一键登录、取 auth_string、选服进服

## 安装
```bash
pip install tools-for-4399
# 或本地开发安装
pip install -e .
```

## 快速使用
```python
from tools_for_4399 import kabu_login

# 默认进服（上次/自动）
pid, sid = kabu_login("账号", "密码")

# 随机进服
pid, sid = kabu_login("账号", "密码", server_mode="random")

# 指定进服
pid, sid = kabu_login("账号", "密码", server_id=527)
```

## 分步调用
```python
from tools_for_4399 import login_4399, get_auth_string, enter_server
cookies = login_4399("账号", "密码")     # 登录4399拿Cookie
auth = get_auth_string(cookies)          # 取auth_string
client = enter_server(auth)              # 连网关进服
```

## 账号管理
```python
from tools_for_4399.base import load_accounts, save_accounts, upsert_account, get_accounts
data = load_accounts()
upsert_account(data, "账号", "密码", remember=True)
save_accounts(data)
```

> 注意：记住密码会把明文密码写入本地 accounts.json，仅供个人离线工具使用。
