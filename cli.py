"""界面层：解析参数、调 api、打印结果、把异常翻译成人话。"""

import argparse
import json
import sys
import time

import requests

import api


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gh-stats", description="查询 GitHub 用户与仓库")
    sub = parser.add_subparsers(dest="command", required=True)

    p_user = sub.add_parser("user", help="查看用户信息")
    p_user.add_argument("username")

    p_repos = sub.add_parser("repos", help="查看用户的仓库")
    p_repos.add_argument("username")
    p_repos.add_argument("--top", type=int, default=10, help="只看前 N 个（按 stars 排序）")
    p_repos.add_argument("--json", action="store_true", help="输出 JSON")

    return parser


def print_user(data: dict) -> None:
    """打印用户信息。"""
    print(f"{data['name'] or data['login']} ({data['login']})")
    print(f"  关注者:   {data['followers']:,}")
    print(f"  公开仓库: {data['public_repos']:,}")
    print(f"  注册时间: {data['created_at'][:10]}")


def print_repos(ranked: list[dict]) -> None:
    """打印已经排序好的仓库列表。"""
    if not ranked:
        print("没有找到仓库")
        return
    name_width = max(len(repo["name"]) for repo in ranked)
    for repo in ranked:
        language = repo["language"] or "-"
        fork = " (fork)" if repo["fork"] else ""
        description = repo["description"] or ""
        if len(description) > 50:
            description = description[:49] + "…"
        print(f"{repo['name']:<{name_width}}  ★{repo['stars']:>7}  {language:<10}{fork}")
        if description:
            print(f"{'':<{name_width}}  {description}")


def _is_rate_limited(response: requests.Response) -> bool:
    """403 到底是限流还是没权限：看限流响应头或响应体。"""
    return response.headers.get("X-RateLimit-Remaining") == "0" or "rate limit" in response.text.lower()


def _reset_hint(response: requests.Response) -> str:
    """估算配额恢复还需要多久，给个偏保守的估计。"""
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        return f"{retry_after} 秒"
    reset = response.headers.get("X-RateLimit-Reset")
    if reset:
        try:
            seconds = max(int(reset) - int(time.time()), 0)
        except ValueError:
            return "约 1 分钟"
        if seconds >= 3600:
            return "1 小时以上"
        return f"约 {seconds // 60 + 1} 分钟"
    return "约 1 分钟"


def _report_error(exc: Exception, username: str) -> int:
    """把 api 层抛出的异常翻译成用户看得懂的话，返回退出码 1。

    要处理的：404、限流 403、超时、连不上、其他 HTTP 错误。
    """
    if isinstance(exc, requests.Timeout):
        print(f"请求超时（超过 {api.TIMEOUT} 秒），网络可能不稳定，稍后再试", file=sys.stderr)
    elif isinstance(exc, requests.ConnectionError):
        print("连不上 GitHub，请检查网络或代理设置", file=sys.stderr)
    elif isinstance(exc, requests.HTTPError) and exc.response is not None:
        status = exc.response.status_code
        if status == 404:
            print(f"找不到用户 {username}（GitHub 返回 404）", file=sys.stderr)
        elif status == 403 and _is_rate_limited(exc.response):
            print(f"GitHub 限流了（{_reset_hint(exc.response)}后可恢复），请稍后再试", file=sys.stderr)
        elif status == 403:
            print("没有权限访问这个资源（GitHub 返回 403）", file=sys.stderr)
        else:
            print(f"GitHub 返回了 HTTP {status}，稍后再试", file=sys.stderr)
    else:
        print(f"出错了：{exc}", file=sys.stderr)
    return 1


def cmd_user(args) -> int:
    try:
        data = api.get_user(args.username)
    except (requests.RequestException, RuntimeError) as exc:
        return _report_error(exc, args.username)
    print_user(data)
    return 0


def cmd_repos(args) -> int:
    try:
        # get_repos 是生成器，异常要等到迭代时才抛，所以 list() 必须包在 try 里
        repos = list(api.get_repos(args.username))
    except (requests.RequestException, RuntimeError) as exc:
        return _report_error(exc, args.username)
    # 排序和取前 N 只做一次，表格和 JSON 看到的是同一批数据
    ranked = sorted(repos, key=lambda repo: repo["stars"], reverse=True)[: args.top]
    if args.json:
        print(json.dumps(ranked, ensure_ascii=False, indent=2))
    else:
        print_repos(ranked)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handlers = {"user": cmd_user, "repos": cmd_repos}
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
