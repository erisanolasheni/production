"""
Digital Twin API — Week 2 Day 2–3
- Memory: local JSON files or S3 (USE_S3=true)
- LLM: OpenAI-compatible (OpenRouter) when LLM_PROVIDER=openai (default), or AWS Bedrock when LLM_PROVIDER=bedrock
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel

from context import prompt

_BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(_BACKEND_DIR / ".env", override=True)

app = FastAPI()

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# --- LLM provider ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").strip().lower()
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "global.amazon.nova-2-lite-v1:0").strip()
DEFAULT_AWS_REGION = os.getenv("DEFAULT_AWS_REGION", "us-east-1").strip()

bedrock_client: Optional[object] = None
if LLM_PROVIDER == "bedrock":
    bedrock_client = boto3.client("bedrock-runtime", region_name=DEFAULT_AWS_REGION)

_openai_singleton: OpenAI | None = None


def _openai_client() -> OpenAI:
    global _openai_singleton
    if _openai_singleton is not None:
        return _openai_singleton
    raw = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY") or ""
    api_key = raw.strip()
    if not api_key:
        raise RuntimeError("Set OPENAI_API_KEY (or OPENROUTER_API_KEY) when LLM_PROVIDER=openai")
    base = os.getenv("LLM_BASE_URL", "").strip()
    kwargs: dict = {"api_key": api_key}
    if base:
        kwargs["base_url"] = base
        if "openrouter.ai" in base:
            referer = os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost:3000").strip()
            title = os.getenv("OPENROUTER_APP_TITLE", "Digital Twin").strip()
            if referer:
                kwargs["default_headers"] = {"HTTP-Referer": referer, "X-Title": title}
    _openai_singleton = OpenAI(**kwargs)
    return _openai_singleton


def _chat_model_openai() -> str:
    return os.getenv("LLM_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"


# --- Memory ---
USE_S3 = os.getenv("USE_S3", "false").lower() == "true"
S3_BUCKET = os.getenv("S3_BUCKET", "").strip()


def _memory_dir_local() -> Path:
    raw = os.getenv("MEMORY_DIR", "").strip()
    if raw:
        return Path(raw).resolve()
    return _BACKEND_DIR.parent / "memory"


MEMORY_DIR_PATH = _memory_dir_local()
s3_client = boto3.client("s3") if USE_S3 else None


def get_memory_path(session_id: str) -> str:
    return f"{session_id}.json"


def load_conversation(session_id: str) -> List[Dict]:
    if USE_S3:
        assert s3_client is not None
        try:
            response = s3_client.get_object(Bucket=S3_BUCKET, Key=get_memory_path(session_id))
            return json.loads(response["Body"].read().decode("utf-8"))
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return []
            raise
    MEMORY_DIR_PATH.mkdir(parents=True, exist_ok=True)
    file_path = MEMORY_DIR_PATH / get_memory_path(session_id)
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_conversation(session_id: str, messages: List[Dict]) -> None:
    if USE_S3:
        assert s3_client is not None
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=get_memory_path(session_id),
            Body=json.dumps(messages, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
        return
    MEMORY_DIR_PATH.mkdir(parents=True, exist_ok=True)
    file_path = MEMORY_DIR_PATH / get_memory_path(session_id)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=2, ensure_ascii=False)


def _messages_for_openai(conversation: List[Dict], user_message: str) -> List[Dict]:
    msgs: List[Dict] = [{"role": "system", "content": prompt()}]
    for msg in conversation[-20:]:
        role = msg.get("role")
        content = msg.get("content")
        if role in ("user", "assistant") and isinstance(content, str):
            msgs.append({"role": role, "content": content})
    msgs.append({"role": "user", "content": user_message})
    return msgs


def _call_openai_chat(messages: List[Dict]) -> str:
    resp = _openai_client().chat.completions.create(
        model=_chat_model_openai(),
        messages=messages,
    )
    text = resp.choices[0].message.content
    return text if text is not None else ""


def _call_bedrock(conversation: List[Dict], user_message: str) -> str:
    assert bedrock_client is not None
    sys_blocks = [{"text": prompt()}]
    br_messages: List[Dict] = []
    for msg in conversation[-50:]:
        role = msg.get("role")
        content = msg.get("content")
        if role not in ("user", "assistant") or not isinstance(content, str):
            continue
        br_messages.append({"role": role, "content": [{"text": content}]})
    br_messages.append({"role": "user", "content": [{"text": user_message}]})

    try:
        response = bedrock_client.converse(
            modelId=BEDROCK_MODEL_ID,
            messages=br_messages,
            system=sys_blocks,
            inferenceConfig={"maxTokens": 2000, "temperature": 0.7, "topP": 0.9},
        )
        parts = response["output"]["message"]["content"]
        return parts[0]["text"] if parts else ""
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code == "AccessDeniedException":
            raise HTTPException(status_code=403, detail="Access denied to Bedrock model") from e
        raise HTTPException(status_code=500, detail=f"Bedrock error: {e}") from e


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


@app.get("/")
async def root():
    return {
        "message": "AI Digital Twin API",
        "memory_enabled": True,
        "storage": "S3" if USE_S3 else "local",
        "llm_provider": LLM_PROVIDER,
        "bedrock_model": BEDROCK_MODEL_ID if LLM_PROVIDER == "bedrock" else None,
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "use_s3": USE_S3,
        "llm_provider": LLM_PROVIDER,
        "bedrock_model": BEDROCK_MODEL_ID if LLM_PROVIDER == "bedrock" else None,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        session_id = request.session_id or str(uuid.uuid4())
        conversation = load_conversation(session_id)

        if LLM_PROVIDER == "bedrock":
            assistant_response = _call_bedrock(conversation, request.message)
        else:
            assistant_response = _call_openai_chat(_messages_for_openai(conversation, request.message))

        conversation.append(
            {"role": "user", "content": request.message, "timestamp": datetime.now().isoformat()},
        )
        conversation.append(
            {
                "role": "assistant",
                "content": assistant_response,
                "timestamp": datetime.now().isoformat(),
            },
        )
        save_conversation(session_id, conversation)

        return ChatResponse(response=assistant_response, session_id=session_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/conversation/{session_id}")
async def get_conversation(session_id: str):
    try:
        conversation = load_conversation(session_id)
        return {"session_id": session_id, "messages": conversation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/sessions")
async def list_sessions():
    """Local storage only: list session files (S3 listing not implemented)."""
    if USE_S3:
        return {"sessions": [], "note": "Use S3 console or add listing; sessions stored in S3 bucket."}
    sessions = []
    MEMORY_DIR_PATH.mkdir(parents=True, exist_ok=True)
    for file_path in MEMORY_DIR_PATH.glob("*.json"):
        session_id = file_path.stem
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        sessions.append(
            {
                "session_id": session_id,
                "message_count": len(data),
                "last_message": data[-1]["content"] if data else None,
            },
        )
    return {"sessions": sessions}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
