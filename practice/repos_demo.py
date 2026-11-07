# Day 2 练习：仓库列表、分页、排序。
import re

import requests

API = "https://api.github.com"

# 匹配 Link 头里的 <url>; rel="xxx" 片段
LINK_RE = re.compile(r'<([^>]+)>;\s*rel="([^"]+)"')


def _next_url_from(link_header: str | None) -> str | None:
    """从 Link 头里取 rel="next" 的 URL，没有则返回 None。"""
    if not link_header:
        return None
    for url, rel in LINK_RE.findall(link_header):
        if rel == "next":
            return url
    return None


def _get_json(url: str, params: dict | None = None) -> tuple[list[dict] | dict, str | None]:
    """GET 一个 URL，返回 (解析后的 JSON, Link 响应头)。所有请求都从这里走。"""
    resp = requests.get(url, params=params, timeout=10)   # 超时是必须的
    resp.raise_for_status()
    return resp.json(), resp.headers.get("Link")


def fetch_repos(username: str, per_page: int = 100, page: int = 1) -> tuple[list[dict], str | None]:
    """取一页仓库。返回 (仓库列表, 下一页的 URL 或 None)。"""
    data, link_header = _get_json(
        f"{API}/users/{username}/repos",
        params={"per_page": per_page, "page": page},
    )
    return data, _next_url_from(link_header)


def get_all_repos(username: str, per_page: int = 100, max_pages: int = 100) -> list[dict]:
    """顺着分页把所有仓库拉完。"""
    repos, next_url = fetch_repos(username, per_page=per_page, page=1)
    pages = 1
    # max_pages 是保险丝，防止任何解析失误导致无限循环
    while next_url and pages < max_pages:
        page_repos, link_header = _get_json(next_url)
        repos.extend(page_repos)
        next_url = _next_url_from(link_header)
        pages += 1
    return repos


def top_repos(repos: list[dict], n: int = 5) -> list[dict]:
    """按 stars 降序取前 n 个，跳过 fork 的仓库。"""
    ranked = sorted(
        (repo for repo in repos if not repo["fork"]),
        key=lambda repo: repo["stargazers_count"],
        reverse=True,
    )
    return ranked[:n]


if __name__ == "__main__":
    repos = get_all_repos("torvalds", per_page=5)   # 故意调小，方便看到分页
    print(f"共 {len(repos)} 个仓库")
    for repo in top_repos(repos, 5):
        print(f"{repo['name']:20} ★{repo['stargazers_count']:>7}  {repo['language']}")
