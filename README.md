# gh-stats

查询 GitHub 用户与仓库信息的命令行工具，数据来自 GitHub 公开 API，不需要 API Key。

## 功能

- 查看用户信息：关注者数、公开仓库数、注册时间
- 查看用户仓库：按 stars 排序，支持只看前 N 个
- `--json` 输出机器可读结果，方便接管道
- 请求带超时和重试，网络抖动不会直接失败
- 错误有中文提示和明确退出码，不吐 traceback

## 环境要求

- Python 3.10 及以上
- 依赖：`requests`；跑测试需要 `pytest`

## 安装

```bash
git clone https://github.com/stinginvi/gh-stats.git
cd gh-stats

python -m venv .venv
source .venv/Scripts/activate      # Windows Git Bash
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS / Linux:     source .venv/bin/activate

pip install -r requirements.txt
python main.py -h
```

## 用法

```bash
# 查看用户信息
python main.py user torvalds

# 查看仓库，按 stars 排序取前 3
python main.py repos torvalds --top 3

# 输出 JSON（和上面的 --top 一致，同样是排好序的前 3 个）
python main.py repos torvalds --top 3 --json
```

### 示例输出

```text
$ python main.py user torvalds
Linus Torvalds (torvalds)
  关注者:   331,081
  公开仓库: 12
  注册时间: 2011-09-03

$ python main.py repos torvalds --top 3
linux        ★ 254781  C
             Linux kernel source tree
AudioNoise   ★   4531  C
             Random digital audio effects
GuitarPedal  ★   2490  C
             Linus learns analog circuits
```

```text
$ python main.py repos torvalds --top 1 --json
[
  {
    "name": "linux",
    "stars": 254781,
    "language": "C",
    "fork": false,
    "description": "Linux kernel source tree"
  }
]
```

## 退出码

| 退出码 | 含义 | 例子 |
|---|---|---|
| 0 | 成功 | 正常查询 |
| 1 | 业务错误 | 用户不存在、限流、超时、连不上网 |
| 2 | 参数用法错误 | `--top abc` |

错误信息输出到 stderr，正常结果输出到 stdout，所以可以安全地重定向：

```bash
python main.py repos torvalds --json > repos.json
```

## 错误处理

| 情况 | 提示 |
|---|---|
| 用户不存在（404） | `找不到用户 xxx（GitHub 返回 404）` |
| 限流（403） | `GitHub 限流了（约 N 分钟后可恢复），请稍后再试` |
| 超时 | `请求超时（超过 10 秒），网络可能不稳定，稍后再试` |
| 连不上 | `连不上 GitHub，请检查网络或代理设置` |

内部策略：

- 每个请求 **10 秒超时**
- 超时 / 连接错误 / 5xx / 429 **自动重试 3 次**，间隔 0.5s → 1s 指数退避
- 其余 4xx **不重试**（参数或身份问题，重试没有意义）
- 403 会区分「没权限」和「限流」，后者给出配额恢复时间

## 项目结构

```
gh-stats/
├── main.py          # 入口，只负责启动
├── cli.py           # 界面层：参数解析、输出格式、错误翻译
├── api.py           # 数据层：请求、重试、分页、字段裁剪
├── tests/
│   └── test_api.py  # api 层单元测试，全部使用假响应，不打真实网络
├── practice/        # 学习过程的分步练习，不参与主流程
├── requirements.txt
└── README.md
```

依赖方向固定为 `main → cli → api`：数据层不打印、不读参数；界面层不发请求。

## 测试

```bash
python -m pytest -q
```

覆盖：字段裁剪、404 不重试、500 重试后成功、分页合并。测试用 `unittest.mock` 替换网络层，不消耗 API 配额。

## 已知限制

- 未认证请求每小时 60 次，频繁使用会被限流
- 只查询公开数据，不支持私有仓库（需要 Token）
- 仓库按 API 返回顺序收集后再本地排序，超大账号会翻多页
- 没有缓存，同一用户连续查询会重复请求

## 许可

MIT
