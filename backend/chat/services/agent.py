# chat/services/agent.py
from __future__ import annotations
import os, json, re
from typing import Dict, Tuple, List
from django.utils import timezone
from ..models import Message, Ticket
from .prompting import build_messages
from .ollama_client import chat_once

# 可選：RAG/工具（若沒放檔案，註解掉這兩行與相關用法）
from .rag_store import search_topk
from .tools import TOOLS_REGISTRY

_TOOL_RE = re.compile(r"^\[TOOL\]\s*(\{.*\})\s*$", re.DOTALL)

def _maybe_parse_tool_call(text: str) -> Dict | None:
    m = _TOOL_RE.match(text.strip())
    if not m:
        return None
    try:
        obj = json.loads(m.group(1))
        if isinstance(obj, dict) and obj.get("action"):
            return obj
    except Exception:
        return None
    return None

def assistant_reply(*, ticket: Ticket, user_text: str,
                    use_rag: bool = True, enable_tools: bool = True, user=None) -> Tuple[str, Dict]:
    # 1) 讀歷史
    history_qs = list(Message.objects.filter(ticket=ticket).order_by("-created_at")[:16])
    history = [{"role": ("assistant" if m.is_ai else "user"), "content": m.content}
               for m in reversed(history_qs)]

    # 2) RAG 片段（可關閉）
    ctx_snippets: List[Dict] = []
    if use_rag:
        try:
            ctx_snippets = search_topk(user_text, k=int(os.getenv("RAG_TOP_K", "4")))
        except Exception:
            ctx_snippets = []

    # 3) 編排訊息（含工具協定）
    msgs = build_messages(
        history, user_text,
        ticket_settings=getattr(ticket, "config", {}) or {},
        context_snippets=ctx_snippets,
        enable_tools=enable_tools,
    )

    # 4) 第一次回覆（可能要求工具）
    first = chat_once(msgs)
    call = _maybe_parse_tool_call(first) if enable_tools else None
    meta = {
        "model": os.getenv("OLLAMA_MODEL", "qwen3:8b"),
        "used_rag": bool(ctx_snippets),
        "tool_called": bool(call),
        "timestamp": timezone.now().isoformat(),
    }
    if not call:
        return first, meta

    # 5) 執行工具（若有）
    action = call.get("action")
    params = call.get("params") or {}
    tool_fn = (TOOLS_REGISTRY or {}).get(action)
    if not tool_fn:
        return (f"無法執行工具：{action}。", {**meta, "tool_error": "unknown_tool"})

    try:
        tool_result = tool_fn(params)
    except Exception as e:
        return (f"工具執行失敗：{action} ({e})。", {**meta, "tool_error": str(e)})

    # 6) 回餵工具結果，產生最終答案
    tool_summary = json.dumps(tool_result, ensure_ascii=False)[:2000]
    msgs.append({"role": "system", "content": f"[TOOL_RESULT] {tool_summary}"})
    final = chat_once(msgs)
    meta["tool_action"] = action
    return final, meta
