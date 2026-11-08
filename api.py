"""数据层：只负责调 GitHub API，不关心数据怎么展示。

这一层出错就抛异常，不打印任何东西。
"""

import re
import time
from typing import Any, Iterator

import requests
from requests.exceptions import ConnectionError, HTTPError, Timeout

API = "https://api.github.com"
TIMEOUT = 10
ATTEMPTS = 3
BACKOFF = 0.5
PER_PAGE = 100
MAX_PAGES = 100

# Link 头里的 <url>; rel="next" 片段
LINK_RE = re.compile(r'<([^>]+)>;\s*rel="([^"]+)"')


def _next_url(link_header: str | None) -> str | None:
    """从 Link 头里取 rel="next" 的 URL。"""
    if not link_header:
        return None
    for url, rel in LINK_RE.findall(link_header):
        if rel == "next":
            return url
    return None


def _get_json(url: str, params: dict | None = None) -> tuple[dict | list, str | None]:
    """带重试的 GET，返回 (json, Link 头)。所有请求都从这里走。"""
    for attempt in range(ATTEMPTS):
        try:
            resp = requests.get(url, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.json(), resp.headers.get("Link")
        except (Timeout, ConnectionError):
            if attempt == ATTEMPTS - 1:
                raise
            time.sleep(BACKOFF * (2 ** attempt))
        except HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            if status is not None and 400 <= status < 500 and status != 429:
                raise  # 除了 429 限流，其他 4xx 都不值得重试
            if attempt == ATTEMPTS - 1:
                raise
            time.sleep(BACKOFF * (2 ** attempt))
    # 循环走完还没返回/抛出（例如 ATTEMPTS 被配成 0），兜底报错而不是返回 None
    raise RuntimeError(f"GET {url} 重试 {ATTEMPTS} 次后仍未成功")


def get_user(username: str) -> dict[str, Any]:
    """取用户信息，只保留需要的字段。"""
    data, _ = _get_json(f"{API}/users/{username}")
    if not isinstance(data, dict):
        raise TypeError(f"{API}/users/{username} 应返回 JSON 对象，实际是 {type(data).__name__}")
    return {
        "login": data["login"],
        "name": data["name"],
        "followers": data["followers"],
        "public_repos": data["public_repos"],
        "created_at": data["created_at"],
    }


def get_repos(username: str) -> Iterator[dict[str, Any]]:
    """取用户全部仓库（自动翻页），只保留需要的字段。

    每条：{"name", "stars", "language", "fork", "description"}
    """
    # 第一页要显式带 per_page（GitHub 默认 30/页）；后面的 URL 由 Link 头给出，已自带参数
    url: str | None = f"{API}/users/{username}/repos"
    params: dict | None = {"per_page": PER_PAGE, "page": 1}
    pages = 0
    # max_pages 是保险丝，防止任何解析失误导致无限翻页
    while url and pages < MAX_PAGES:
        data, link_header = _get_json(url, params=params)
        if not isinstance(data, list):
            raise TypeError(f"{url} 应返回 JSON 数组，实际是 {type(data).__name__}")
        for repo in data:
            yield {
                "name": repo["name"],
                "stars": repo["stargazers_count"],
                "language": repo["language"],
                "fork": repo["fork"],
                "description": repo["description"],
            }
        url = _next_url(link_header)
        params = None
        pages += 1
