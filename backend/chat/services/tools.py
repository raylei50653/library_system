# chat/services/tools.py
from __future__ import annotations
from typing import Dict, Any

def lookup_book(params: Dict[str, Any]) -> Dict[str, Any]:
    query = (params.get("query") or "").strip()
    if query:
        return {
            "type": "book",
            "items": [
                {"title": f"（DEMO）關鍵字：{query}", "available": 2}
            ],
        }
    return {"error": "missing query"}

def get_loan_status(params: Dict[str, Any]) -> Dict[str, Any]:
    return {"loans": [{"book": "Python入門", "status": "active", "due_at": "2025-11-01"}]}

def renew_loan(params: Dict[str, Any]) -> Dict[str, Any]:
    loan_id = params.get("loan_id")
    if not loan_id: return {"error": "missing loan_id"}
    return {"ok": True, "loan_id": loan_id, "new_due_at": "2025-11-15"}

TOOLS_REGISTRY = {
    "lookup_book": lookup_book,
    "get_loan_status": get_loan_status,
    "renew_loan": renew_loan,
}
