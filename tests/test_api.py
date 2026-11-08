"""api 层测试：全部用假响应，不打真实网络。

跑法（在 gh-stats 目录下）：python -m pytest -q
"""

import json
from unittest.mock import patch

import pytest
import requests

import api


def make_response(payload, status=200, headers=None):
    """造一个和 requests.Response 行为一致的假响应。

    用真的 requests.Response 对象，raise_for_status() 和 json() 都是真逻辑，
    只有网络那一层被 patch 掉，所以测试很接近真实行为。
    """
    resp = requests.Response()
    resp.status_code = status
    resp._content = json.dumps(payload).encode("utf-8")
    resp.headers.update(headers or {})
    return resp


# ---------------- 示范：已经写好，照着这个写后面三个 ----------------
def test_get_user_keeps_only_needed_fields():
    payload = {
        "login": "octocat",
        "name": "The Octocat",
        "followers": 100,
        "public_repos": 8,
        "created_at": "2011-01-25T18:44:36Z",
        "id": 1,
        "node_id": "MDQ6VXNlcjE=",
        "avatar_url": "https://example.com/a.png",
    }
    with patch("api.requests.get", return_value=make_response(payload)) as fake:
        data = api.get_user("octocat")

    # 只保留 5 个字段，其他全丢掉
    assert data == {
        "login": "octocat",
        "name": "The Octocat",
        "followers": 100,
        "public_repos": 8,
        "created_at": "2011-01-25T18:44:36Z",
    }
    fake.assert_called_once()
    assert fake.call_args.kwargs["timeout"] == api.TIMEOUT   # 超时必须传


# ---------------- TODO 1：404 不该重试 ----------------
def test_404_raises_without_retry():
    """期望：抛 requests.HTTPError，且 requests.get 只被调用 1 次。"""
    # 提示：
    #   with patch("api.requests.get", return_value=make_response({"message": "Not Found"}, status=404)) as fake:
    #       with pytest.raises(requests.HTTPError):
    #           api.get_user("nobody")
    #   assert fake.call_count == 1



    with patch("api.requests.get", return_value=make_response({"message": "Not Found"}, status=404)) as fake:
        with pytest.raises(requests.HTTPError):
            api.get_user("nobody")
    assert fake.call_count == 1


# ---------------- TODO 2：500 重试后成功 ----------------
def test_retries_on_500_then_succeeds():
    """期望：第一次 500，第二次 200，最终返回数据，get 被调用 2 次。"""
    # 提示：
    #   1. 用 side_effect=[make_response({}, status=500), make_response(payload)]
    #   2. 同时 patch("api.time.sleep")，否则测试真的要等 0.5 秒
    #   3. 断言 fake.call_count == 2
    # get_user 会取 5 个字段，假数据必须给全，否则先死在 KeyError 上，测不到重试
    payload = {
        "login": "x",
        "name": "X",
        "followers": 1,
        "public_repos": 2,
        "created_at": "2020-01-01T00:00:00Z",
    }
    with (
        patch("api.time.sleep") as sleeper,          # 别真的等 0.5 秒
        patch(
            "api.requests.get",
            side_effect=[make_response({}, status=500), make_response(payload)],
        ) as fake,
    ):
        data = api.get_user("x")

    assert data["login"] == "x"
    assert fake.call_count == 2                     # 500 之后重试了一次
    sleeper.assert_called_once()                    # 而且确实退避等待过


# ---------------- TODO 3：翻页 ----------------
def test_get_repos_paginates():
    """期望：两页数据合并，第二页的 Link 头没有 next 就停。"""
    page1 = [{"name": "a", "stargazers_count": 1, "language": "C", "fork": False, "description": None}]
    page2 = [{"name": "b", "stargazers_count": 2, "language": "Go", "fork": False, "description": "x"}]
    link = '<https://api.github.com/users/x/repos?page=2>; rel="next"'
    # 提示：
    #   side_effect=[make_response(page1, headers={"Link": link}), make_response(page2)]
    #   repos = list(api.get_repos("x"))
    #   断言 [r["name"] for r in repos] == ["a", "b"]，且 call_count == 2
    with patch("api.requests.get", side_effect=[make_response(page1, headers={"Link": link}), make_response(page2)]) as fake:
        repos = list(api.get_repos("x"))
    assert [r["name"] for r in repos] == ["a", "b"]
    assert fake.call_count == 2


