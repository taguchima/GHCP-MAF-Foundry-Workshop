# Copyright (c) Microsoft. All rights reserved.

"""Hosted Agent: Microsoft 365 と Azure の最新リリース情報を日本語で回答するエージェント

このファイルは ``azd ai agent init --deploy-mode code`` で生成される
テンプレートを MSUpdatesAgent のロジックで置き換えたものです。
Foundry にデプロイされ、MRC MCP と連携して最新情報を取得します。
"""

import os
from collections.abc import AsyncGenerator

from agent_framework import Agent, AgentSession
from agent_framework.foundry import FoundryChatClient
from azure.ai.agentserver.invocations import InvocationAgentServerHost
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse

# Load environment variables from .env file
load_dotenv()


INSTRUCTIONS = """あなたは Microsoft 365 と Azure の最新リリース情報を回答する日本語アシスタントです。

【重要な指示】
- 必ず MRC (Microsoft Release Communications) MCP ツールを使用して一次情報を取得してください。
- 回答には必ず出典 URL を添えてください。
- 日本語のみで応答してください。
- ユーザーの質問に対して、MRC ツールから取得した最新の情報を使用して回答します。
- 不確実な情報は「確認できませんでした」と明記してください。"""

MRC_URL = "https://www.microsoft.com/releasecommunications/mcp"

# In-memory session store — keyed by session ID.
# WARNING: This is lost on restart. Use durable storage in production.
_sessions: dict[str, AgentSession] = {}

# Create the agent
client = FoundryChatClient(
    project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
    model=os.environ.get("FOUNDRY_MODEL") or os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"],
    credential=DefaultAzureCredential(),
)

agent = Agent(
    client=client,
    name="MSUpdatesAgent",
    instructions=INSTRUCTIONS,
    tools=[
        client.get_mcp_tool(
            name="MRC",
            url=MRC_URL,
            approval_mode="never_require",
        ),
    ],
    # History will be managed by the hosting infrastructure, thus there
    # is no need to store history by the service. Learn more at:
    # https://developers.openai.com/api/reference/resources/responses/methods/create
    default_options={"store": False},
)

app = InvocationAgentServerHost()


@app.invoke_handler
async def handle_invoke(request: Request):
    """Handle streaming multi-turn chat with Azure OpenAI via SSE."""
    data = await request.json()
    session_id = request.state.session_id

    stream = data.get("stream", False)
    user_message = data.get("message", None)
    if user_message is None:
        error = "Missing 'message' in request"
        if stream:
            return StreamingResponse(content=error, status_code=400)
        return Response(content=error, status_code=400)

    session = _sessions.setdefault(session_id, AgentSession(session_id=session_id))

    if stream:

        async def stream_response() -> AsyncGenerator[str]:
            async for update in agent.run(user_message, session=session, stream=True):
                yield update.text

        return StreamingResponse(
            stream_response(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    response = await agent.run([user_message], session=session, stream=stream)
    return JSONResponse({"response": response.text})


if __name__ == "__main__":
    app.run()
