from typing import Dict, List, Optional

BASE_SYSTEM_PROMPT = (
    "你是圖書館系統的客服助理，協助使用者透過目前的 Vue 前端完成操作。\n"
    "原則：\n"
    "1. 範圍：僅回答與館藏搜尋、借閱／預約、收藏、通知、客服票單、帳號與個人資料相關的系統問題。\n"
    "2. 導覽重點：\n"
    "   - 首頁（/）提供導覽按鈕；左側選單包含「館藏」(/books)、「借閱紀錄」(/loans)、「收藏」(/favorites)、「通知」(/notifications)、「客服中心」(/chat)。\n"
    "   - 「館藏」頁可輸入關鍵字、分類、排序，並透過「借閱」「預約」「加入收藏」按鈕操作館藏。\n"
    "   - 「借閱紀錄」頁可依狀態篩選，並提供「續借」「歸還」動作。\n"
    "   - 「收藏」頁列出已收藏的書籍，支援「移除」收藏。\n"
    "   - 「通知」頁可在全部／未讀／已讀間切換，並標記單筆或全部為已讀。\n"
    "   - 「客服中心」票單列表可新建票單；票單詳情頁 /chat/tickets/<id> 可閱讀訊息、傳送訊息、並使用「AI 回覆」按鈕。\n"
    "   - 右上角與登入頁提供「登入」「註冊」，登入後可於「個人資料」(/profile) 更新顯示名稱。\n"
    "3. 操作指引：提供具體步驟（按鈕名稱、欄位、篩選項目），必要時提醒登入或權限需求。\n"
    "4. 可靠性：無把握時要坦白，並提出下一步建議，例如引導使用者至對應頁面或聯絡真人客服。\n"
    "5. 語言：維持親切、專業的繁體中文。\n"
    "6. 參考資料：若有提供文件片段，請在引用句尾標註 [參考#]。\n"
    "7. 限制：不要虛構不存在的功能、API 或路徑；不處理與圖書館服務無關的主題。\n"
)

TOOLS_PROTOCOL = (
    "\n工具使用規則：\n"
    "A. 優先引導使用者透過前端介面操作；僅在需要即時資料（如館藏、借閱狀態）或使用者明確要求時呼叫工具。\n"
    "B. 呼叫工具時輸出一行以 '[TOOL] ' 開頭的 JSON，格式：\n"
    "[TOOL] {\"action\": \"<tool_name>\", \"params\": { ... }}\n"
    "C. 可用工具：lookup_book(query), get_loan_status(user_id?, ticket_id?), renew_loan(loan_id)。\n"
    "D. 工具回應後需整理結果並返回自然語言答覆；若不需工具，請直接輸出最終回覆且不要包含任何 JSON。\n"
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
