#!/usr/bin/env python3
"""
Cell Cover Generator HTTP Server 客户端测试脚本
用于测试通过 Tailscale 访问的服务器
"""
import requests
import sys
import json
from typing import Optional


class CellCoverClient:
    """Cell Cover Generator API 客户端"""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        """
        初始化客户端

        Args:
            base_url: 服务器地址（如 http://192.168.1.100:8888 或 http://tailscale-ip:8888）
            api_key: 可选的 API 密钥
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()

        if api_key:
            self.session.headers.update({"X-API-Key": api_key})

    def health_check(self) -> dict:
        """健康检查"""
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    def list_concepts(self) -> dict:
        """列出所有可用的创意概念"""
        response = self.session.get(f"{self.base_url}/api/v1/concepts")
        response.raise_for_status()
        return response.json()

    def create_image(
        self,
        prompt: str,
        concept: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
        style: Optional[str] = None,
        version: Optional[str] = None,
        mode: str = "relax",
        chaos: Optional[int] = None,
        stylize: Optional[int] = None
    ) -> dict:
        """
        创建新的图像生成任务

        Args:
            prompt: 提示词
            concept: 概念键（可选）
            aspect_ratio: 纵横比（如 16:9）
            style: 风格（如 raw）
            version: Midjourney 版本（如 v6, v7）
            mode: 生成模式（relax, fast, turbo）
            chaos: 混乱度（0-100）
            stylize: 风格化（0-1000）

        Returns:
            包含任务信息的字典
        """
        data = {
            "prompt": prompt,
            "mode": mode
        }

        if concept:
            data["concept"] = concept
        if aspect_ratio:
            data["aspect_ratio"] = aspect_ratio
        if style:
            data["style"] = style
        if version:
            data["version"] = version
        if chaos is not None:
            data["chaos"] = chaos
        if stylize is not None:
            data["stylize"] = stylize

        response = self.session.post(
            f"{self.base_url}/api/v1/create",
            data=data
        )
        response.raise_for_status()
        return response.json()

    def list_tasks(
        self,
        limit: int = 20,
        status: Optional[str] = None,
        concept: Optional[str] = None
    ) -> dict:
        """
        列出任务列表

        Args:
            limit: 返回任务数量限制
            status: 按状态过滤
            concept: 按概念过滤

        Returns:
            任务列表
        """
        params = {"limit": limit}
        if status:
            params["status"] = status
        if concept:
            params["concept"] = concept

        response = self.session.get(f"{self.base_url}/api/v1/tasks", params=params)
        response.raise_for_status()
        return response.json()

    def view_task(
        self,
        task_id: str,
        remote: bool = False,
        save: bool = False
    ) -> dict:
        """
        查看任务详情

        Args:
            task_id: 任务 ID
            remote: 从远程 API 获取信息
            save: 保存远程信息到本地

        Returns:
            任务详情
        """
        params = {}
        if remote:
            params["remote"] = "true"
        if save:
            params["save"] = "true"

        response = self.session.get(
            f"{self.base_url}/api/v1/tasks/{task_id}",
            params=params
        )
        response.raise_for_status()
        return response.json()

    def perform_action(
        self,
        task_id: str,
        action_code: str,
        mode: str = "fast",
        wait: bool = False
    ) -> dict:
        """
        对任务执行操作

        Args:
            task_id: 任务 ID
            action_code: 操作代码（如 variation1, upsample1）
            mode: 生成模式
            wait: 等待任务完成

        Returns:
            操作结果
        """
        data = {
            "action_code": action_code,
            "mode": mode,
            "wait": str(wait).lower()
        }

        response = self.session.post(
            f"{self.base_url}/api/v1/tasks/{task_id}/action",
            data=data
        )
        response.raise_for_status()
        return response.json()

    def describe_image(self, image_path: str) -> dict:
        """
        描述上传的图像

        Args:
            image_path: 图像文件路径

        Returns:
            描述结果
        """
        with open(image_path, "rb") as f:
            files = {"image": f}
            response = self.session.post(
                f"{self.base_url}/api/v1/describe",
                files=files
            )

        response.raise_for_status()
        return response.json()


def main():
    """测试客户端"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Cell Cover Generator HTTP Server 客户端"
    )
    parser.add_argument(
        "server_url",
        help="服务器地址（如 http://192.168.1.100:8888 或 http://tailscale-ip:8888）"
    )
    parser.add_argument(
        "--api-key",
        help="API 密钥（如果服务器配置了）"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="运行快速测试"
    )

    args = parser.parse_args()

    # 创建客户端
    client = CellCoverClient(args.server_url, args.api_key)

    # 测试模式
    if args.test:
        print("=" * 60)
        print("Cell Cover Generator 客户端测试")
        print("=" * 60)
        print(f"服务器地址: {args.server_url}")
        print("")

        try:
            # 1. 健康检查
            print("1️⃣  健康检查...")
            health = client.health_check()
            print(f"   ✓ 状态: {health['status']}")
            print("")

            # 2. 列出概念
            print("2️⃣  列出创意概念...")
            concepts = client.list_concepts()
            print(f"   ✓ 成功获取概念列表")
            print("")

            # 3. 列出任务
            print("3️⃣  列出任务...")
            tasks = client.list_tasks(limit=5)
            print(f"   ✓ 成功获取任务列表")
            print("")

            print("=" * 60)
            print("✅ 所有测试通过！服务器运行正常。")
            print("=" * 60)
            print("")
            print("📚 可用 API 端点:")
            print("   - POST /api/v1/create      创建图像生成任务")
            print("   - GET  /api/v1/concepts    列出创意概念")
            print("   - GET  /api/v1/tasks       列出任务")
            print("   - GET  /api/v1/tasks/{id}  查看任务详情")
            print("   - POST /api/v1/tasks/{id}/action  执行操作")
            print("   - POST /api/v1/describe   描述图像")

        except requests.exceptions.ConnectionError:
            print(f"❌ 无法连接到服务器: {args.server_url}")
            print("   请确认:")
            print("   1. 服务器是否正在运行")
            print("   2. 网络连接是否正常")
            print("   3. 防火墙是否允许连接")
            sys.exit(1)
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            sys.exit(1)
    else:
        # 交互模式
        print(f"Cell Cover Generator 客户端")
        print(f"连接到: {args.server_url}")
        print(f"输入 'help' 查看可用命令")
        print("")

        while True:
            try:
                cmd = input("> ").strip()

                if not cmd:
                    continue

                if cmd.lower() in ("exit", "quit"):
                    break

                if cmd.lower() == "help":
                    print("""
可用命令:
  health          - 健康检查
  concepts        - 列出创意概念
  tasks           - 列出任务
  create <prompt> - 创建图像任务
  view <id>       - 查看任务详情
  action <id> <code> - 对任务执行操作
  describe <path> - 描述图像
  exit/quit       - 退出
                    """)
                    continue

                # 处理命令（简化版）
                if cmd.lower() == "health":
                    result = client.health_check()
                    print(json.dumps(result, indent=2))

                elif cmd.lower() == "concepts":
                    result = client.list_concepts()
                    print(json.dumps(result, indent=2))

                elif cmd.lower() == "tasks":
                    result = client.list_tasks()
                    print(result.get("data", "无任务"))

                elif cmd.lower().startswith("create "):
                    prompt = cmd[7:].strip()
                    result = client.create_image(prompt)
                    print(json.dumps(result, indent=2))

                elif cmd.lower().startswith("view "):
                    task_id = cmd[5:].strip()
                    result = client.view_task(task_id)
                    print(result.get("data", "无数据"))

                else:
                    print(f"未知命令: {cmd} (输入 'help' 查看帮助)")

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"错误: {e}")


if __name__ == "__main__":
    main()
