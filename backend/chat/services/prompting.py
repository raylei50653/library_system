from typing import Dict, List, Optional

BASE_SYSTEM_PROMPT = (
    "你是圖書館客服助理。原則："
    "- 僅回答與本系統功能、借閱規則、分類、帳號與通知相關的問題"
    "- 無把握時要坦白，並提供下一步行動（例如引導使用者到 /books 搜尋）"
    "- 回覆語言：繁體中文"
)

TOOLS_PROTOCOL = (
    "若你需要呼叫工具，請輸出一行以 '[TOOL] ' 開頭的 JSON，格式："
    "[TOOL] {\"action\": \"<tool_name>\", \"params\": { ... }}"
    "工具清單：lookup_book(query), get_loan_status(user_id?, ticket_id?), renew_loan(loan_id)"
    "若不需要工具，請直接輸出最終回覆，不要包含任何 JSON。"
)


def render_context_snippet(snippets: Optional[List[Dict]] = None, max_chars: int = 1200) -> str:
    if not snippets:
        return ""
    acc = []
    budget = max_chars
    for i, sn in enumerate(snippets, 1):
        chunk = sn.get("text") or ""
        meta = sn.get("meta") or {}
        head = f"[參考{i}] {meta.get('title','KB')}"
        take = (head + chunk)[: min(len(head + chunk), budget)]
        acc.append(take)
        budget -= len(take)
        if budget <= 0:
            break
    return "".join(acc)


def build_messages(history: List[Dict], user_text: str, *, ticket_settings: Dict | None = None,
                   context_snippets: Optional[List[Dict]] = None, enable_tools: bool = False) -> List[Dict]:
    """Assemble messages for the LLM with optional RAG context & tools protocol."""
    system = BASE_SYSTEM_PROMPT
    if enable_tools:
        system += "" + TOOLS_PROTOCOL
    ctx = render_context_snippet(context_snippets)
    if ctx:
        system += "以下為可引用的館內資料擷取：" + ctx

    msgs: List[Dict] = [{"role": "system", "content": system}]
    msgs.extend(history[-8:])
    msgs.append({"role": "user", "content": user_text})
    return msgs
