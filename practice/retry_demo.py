# Day 3 练习：超时、重试、异常分类。

import time

from requests.exceptions import Timeout, ConnectionError
import requests
from requests import HTTPError

API = "https://api.github.com"


def fetch_with_retry(
    url: str,
    params: dict | None = None,
    attempts: int = 3,
    backoff: float = 0.5,
) -> dict:
    """带重试的 GET。

    成功：返回解析后的 json。
    失败：重试用尽后，抛出最后一个异常（不要吞掉）。
    """
    # TODO: for attempt in range(attempts):
    for attempt in range(attempts):
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except (Timeout, ConnectionError):
            if attempt == attempts - 1:
                raise
            time.sleep(backoff * (2 ** attempt))
        except HTTPError as e:
            if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                raise  # 除了 429 限流，其他 4xx 都不值得重试
            if attempt == attempts - 1:
                raise
            time.sleep(backoff * (2 ** attempt))
    #   1. try: requests.get(url, params=params, timeout=10) → raise_for_status() → return json
    #   2. except (Timeout, ConnectionError): 还次数就 sleep 后继续
    #   3. except HTTPError: 看 e.response.status_code
    #        4xx（429 除外）→ 直接 raise，不浪费时间
    #        5xx / 429        → 还次数就 sleep 后继续
    # 提示：sleep 时长用 backoff * (2 ** attempt)
    pass


if __name__ == "__main__":
    # 1. 正常请求：应该一次成功（/zen 返回纯文本，不能 .json()，所以用 users）
    data = fetch_with_retry(f"{API}/users/torvalds")
    print(f"[正常] 拿到响应: {data['login']}，followers={data['followers']}")

    # 2. 404：不该重试，应该立刻抛错
    start = time.perf_counter()
    try:
        fetch_with_retry(f"{API}/users/this-user-does-not-exist-xyz123")
    except requests.HTTPError as e:
        print(f"[404] 立刻失败 {time.perf_counter() - start:.2f}s -> {e.response.status_code}")
    else:
        print("[404] 没有抛异常，逻辑有问题")

    # 3. 连不上：应该重试 3 次后放弃（耗时应接近 0.5 + 1 = 1.5s）
    start = time.perf_counter()
    try:
        fetch_with_retry("https://no-such-host-xyz.invalid/")
    except requests.RequestException as e:
        print(f"[断网] 重试后失败 {time.perf_counter() - start:.2f}s -> {type(e).__name__}")
    else:
        print("[断网] 没有抛异常，逻辑有问题")
