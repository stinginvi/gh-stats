# Day 1 练习：用 requests 调 GitHub 公开 API。

import requests

API = "https://api.github.com"


def fetch_user(username: str) -> dict:
    url = f"{API}/users/{username}"
    resp = requests.get(url, timeout=5)
    resp.raise_for_status()      # 4xx/5xx 抛 HTTPError，200 继续
    return resp.json()



def print_summary(data: dict) -> None:
    """打印 login、name、followers、public_repos、created_at 五个字段。"""
    print(data["login"], data["name"], data["followers"], data["public_repos"], data["created_at"])


if __name__ == "__main__":
    print_summary(fetch_user("torvalds"))
