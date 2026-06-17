"""MSUpdatesAgent: Microsoft 365 と Azure の最新リリース情報を日本語で回答するエージェント

ローカル CLI として python src/agent.py で実行。
Microsoft Release Communications MCP と連携し、最新情報を取得します。
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator

from agent_framework import MCPStreamableHTTPTool
from agent_framework.foundry import FoundryChatClient
from azure.identity.aio import AzureCliCredential
from dotenv import dotenv_values


# --- 1. Load .env (fill-only, don't override) ---
_DOTENV_PATH = Path(__file__).resolve().parents[1] / ".env"
for _k, _v in dotenv_values(_DOTENV_PATH).items():
    if _v is None:
        continue
    if not (os.getenv(_k) or "").strip():
        os.environ[_k] = _v


def _require_env(name: str) -> str:
    """環境変数が設定されているかチェック。未設定または空文字列の場合はエラー."""
    value = (os.getenv(name) or "").strip()
    if not value:
        raise RuntimeError(
            f"Required environment variable is missing or empty: {name}. "
            "Set it via .env / export / Codespaces secrets and try again."
        )
    return value


# --- 2. Define system instructions ---
INSTRUCTIONS = """あなたは Microsoft 365 と Azure の最新リリース情報を日本語で回答するアシスタントです。

【重要な指示】
- 必ず MRC (Microsoft Release Communications) MCP ツールを使用して一次情報を取得してください。
- 回答には必ず出典 URL を添えてください。
- 日本語のみで応答してください。
- ユーザーの質問に対して、MRC ツールから取得した最新の情報を使用して回答します。
- 不確実な情報は「確認できませんでした」と明記してください。"""

MRC_MCP_URL = "https://www.microsoft.com/releasecommunications/mcp"


async def main() -> None:
    """Main entry point for the CLI agent."""
    project_endpoint = _require_env("FOUNDRY_PROJECT_ENDPOINT")
    model = _require_env("FOUNDRY_MODEL")

    async with AzureCliCredential() as cred:
        client = FoundryChatClient(
            project_endpoint=project_endpoint,
            model=model,
            credential=cred,
        )

        # --- 3. Wire the agent with MRC MCP tool ---
        async with client.as_agent(
            name="MSUpdatesAgent",
            instructions=INSTRUCTIONS,
            tools=[
                MCPStreamableHTTPTool(
                    name="mrc",
                    url=MRC_MCP_URL,
                    description="Microsoft Release Communications API for latest release information",
                    timeout=10.0,
                    approval_mode="never_require",
                ),
            ],
        ) as agent:
            # --- 4. Interactive CLI loop ---
            print("=" * 70)
            print("MSUpdatesAgent - Microsoft 365 & Azure の最新リリース情報")
            print("=" * 70)
            print("終了するには 'exit' または 'quit' を入力してください。\n")

            while True:
                try:
                    user_input = input("質問> ").strip()
                except EOFError:
                    # stdin が閉じられた場合（非対話的実行）
                    break

                if not user_input:
                    continue

                if user_input.lower() in ("exit", "quit"):
                    print("エージェントを終了します。")
                    break

                try:
                    print("\n処理中...\n")
                    response = await agent.run(user_input)
                    print(f"回答:\n{response.text}\n")
                except Exception as e:
                    print(f"エラー: {e}\n", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
