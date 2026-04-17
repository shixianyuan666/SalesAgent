from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from api.models import AgentConfig
from api.repos.memory_repo import MemoryRepo
from api.repos.product_repo import ProductRepo
from api.repos.settings_repo import SettingsRepo
from api.services.openai_compat import OpenAICompatClient, OpenAICompatConfig
from api.services.retrieval import HybridRetriever


class AgentState(TypedDict, total=False):
    user_id: str
    text: str
    effective_text: str
    memory_preferences: dict[str, object]
    memory_summary: str
    rewritten_query: str
    slots: dict[str, object]
    asked_key: str | None
    pending_need: str | None
    retrieved: list[dict[str, Any]]
    selected_ids: list[str]
    reply_text: str
    need_human: bool


@dataclass(frozen=True)
class AgentResult:
    reply_text: str
    product_ids: list[str]
    need_human: bool


def _load_llm() -> OpenAICompatClient:
    raw = SettingsRepo().get_json("llm", {})
    if not isinstance(raw, dict):
        raw = {}
    return OpenAICompatClient(
        OpenAICompatConfig(
            base_url=str(raw.get("base_url")) if raw.get("base_url") else None,
            api_key=str(raw.get("api_key")) if raw.get("api_key") else None,
            chat_model=str(raw.get("chat_model")) if raw.get("chat_model") else None,
            embedding_model=str(raw.get("embedding_model")) if raw.get("embedding_model") else None,
        )
    )


def _load_agent_cfg() -> AgentConfig:
    raw = SettingsRepo().get_json("agent", {})
    if not isinstance(raw, dict):
        raw = {}
    return AgentConfig(**raw)


async def _node_read_memory(state: AgentState) -> AgentState:
    user_id = state["user_id"]
    mem = MemoryRepo().get(user_id)
    if not mem:
        return {"memory_preferences": {}, "memory_summary": ""}
    return {"memory_preferences": mem.preferences, "memory_summary": mem.summary_text}


def _extract_budget(text: str) -> str | None:
    m = re.search(r"(预算|价格|价位)\s*([0-9]{1,6})\s*(元|块|rmb|¥)?", text)
    if m:
        return m.group(2) + "元"
    m2 = re.search(r"([0-9]{1,6})\s*(元|块|rmb|¥)", text)
    if m2:
        return m2.group(1) + "元"
    return None


def _extract_use_case(text: str) -> str | None:
    for k in ["办公", "游戏", "家用", "出差", "学生", "直播", "礼物", "送人"]:
        if k in text:
            return k
    return None


def _human_trigger(text: str) -> bool:
    for k in ["转人工", "人工", "真人", "投诉", "退款", "差评", "客服"]:
        if k in text:
            return True
    return False


async def _node_extract_slots(state: AgentState) -> AgentState:
    llm = _load_llm()
    prefs = state.get("memory_preferences") or {}
    if not isinstance(prefs, dict):
        prefs = {}
    text = (state.get("text") or "").strip()

    effective_text = text
    pending_need = prefs.get("pending_need")
    if isinstance(pending_need, str) and pending_need.strip() and prefs.get("last_question"):
        effective_text = (pending_need.strip() + " " + text).strip()

    slots: dict[str, object] = {}
    budget = _extract_budget(effective_text)
    use_case = _extract_use_case(effective_text)

    last_q = str(prefs.get("last_question") or "")
    if last_q == "budget" and not budget:
        budget = _extract_budget("预算 " + effective_text)
    if last_q == "use_case" and not use_case:
        use_case = text[:20]

    if budget:
        slots["budget"] = budget
    if use_case:
        slots["use_case"] = use_case

    if llm.cfg.base_url and llm.cfg.api_key and llm.cfg.chat_model:
        schema = '{"budget":null,"use_case":null,"must_ask":null}'
        sys = "你是售卖智能体的信息抽取模块，专注抽取预算和用途；无法确定就返回null。"
        res = await llm.chat_json(sys, effective_text, schema)
        if isinstance(res, dict):
            if res.get("budget") and not slots.get("budget"):
                slots["budget"] = str(res["budget"])
            if res.get("use_case") and not slots.get("use_case"):
                slots["use_case"] = str(res["use_case"])

    merged_prefs = dict(prefs)
    if "budget" in slots:
        merged_prefs["budget_range"] = slots["budget"]
        merged_prefs.pop("last_question", None)
        merged_prefs.pop("pending_need", None)
    if "use_case" in slots:
        merged_prefs["use_case"] = slots["use_case"]
        merged_prefs.pop("last_question", None)
        merged_prefs.pop("pending_need", None)

    need_human = _human_trigger(text)
    return {
        "memory_preferences": merged_prefs,
        "slots": slots,
        "need_human": need_human,
        "effective_text": effective_text,
    }



async def _node_rewrite_query(state: AgentState) -> AgentState:
    prefs = state.get("memory_preferences") or {}
    base = (state.get("effective_text") or state.get("text") or "").strip()
    hint = ""
    if isinstance(prefs, dict) and prefs:
        use_case = prefs.get("use_case")
        budget = prefs.get("budget_range")
        if use_case or budget:
            hint = f" 用途:{use_case or ''} 预算:{budget or ''}".strip()
    rewritten = (base + (" " + hint if hint else "")).strip()
    return {"rewritten_query": rewritten}


async def _node_retrieve(state: AgentState) -> AgentState:
    llm = _load_llm()
    cfg = _load_agent_cfg()
    repo = ProductRepo()
    retriever = HybridRetriever(llm=llm, repo=repo)
    results = await retriever.retrieve(state.get("rewritten_query") or "", cfg.top_n)
    packed: list[dict[str, Any]] = []
    for r in results:
        packed.append(
            {
                "id": r.product.id,
                "title": r.product.title,
                "description": r.product.description,
                "tags": r.product.tags,
                "external_url": r.product.external_url,
                "score": r.score,
                "score_keyword": r.score_keyword,
                "score_vector": r.score_vector,
            }
        )
    return {"retrieved": packed}


async def _node_judge(state: AgentState) -> AgentState:
    llm = _load_llm()
    cfg = _load_agent_cfg()
    items = state.get("retrieved") or []
    query = state.get("rewritten_query") or state.get("text") or ""

    max_score = max([float(i.get("score") or 0.0) for i in items], default=0.0)
    if not items or (cfg.force_clarify_when_low_confidence and max_score < cfg.min_relevance_score):
        return {"selected_ids": []}

    if llm.cfg.base_url and llm.cfg.api_key and llm.cfg.chat_model:
        schema = '{"accepted_ids":["prod_xxx"],"need_human":false}'
        sys = "你是严谨的售卖智能体审核器，必须避免把相似但不满足需求的商品发给用户。"
        json_payload = {
            "user_need": query,
            "candidates": [
                {
                    "id": i.get("id"),
                    "title": i.get("title"),
                    "description": i.get("description"),
                    "tags": i.get("tags"),
                    "url": i.get("external_url"),
                }
                for i in items
            ],
        }
        res = await llm.chat_json(sys, json.dumps(json_payload, ensure_ascii=False), schema)
        accepted = res.get("accepted_ids") if isinstance(res, dict) else None
        if isinstance(accepted, list) and accepted:
            ids = []
            seen = set()
            for x in accepted:
                sx = str(x)
                if sx and sx not in seen:
                    ids.append(sx)
                    seen.add(sx)
            need_human = bool(res.get("need_human")) if isinstance(res, dict) else False
            return {"selected_ids": ids, "need_human": need_human}

    ids: list[str] = []
    for i in items:
        if float(i.get("score") or 0.0) >= cfg.min_relevance_score:
            ids.append(str(i["id"]))
    uniq: list[str] = []
    seen = set()
    for x in ids:
        if x not in seen:
            uniq.append(x)
            seen.add(x)
    return {"selected_ids": uniq[: cfg.top_n]}


async def _node_compose_reply(state: AgentState) -> AgentState:
    cfg = _load_agent_cfg()
    selected = state.get("selected_ids") or []
    items = state.get("retrieved") or []
    id_to_item = {str(i.get("id")): i for i in items}

    if not selected:
        prefs = state.get("memory_preferences") or {}
        if not isinstance(prefs, dict):
            prefs = {}
        need_budget = not prefs.get("budget_range")
        need_use_case = not prefs.get("use_case")
        base_need = str(prefs.get("pending_need") or (state.get("effective_text") or state.get("text") or "")).strip()
        if need_use_case:
            return {
                "reply_text": "为了更精准推荐，你主要是用来做什么场景（办公/游戏/家用/出差）？",
                "asked_key": "use_case",
                "pending_need": base_need,
            }
        if need_budget:
            return {
                "reply_text": "你的预算大概在多少（例如 100-200 元）？",
                "asked_key": "budget",
                "pending_need": base_need,
            }
        return {"reply_text": cfg.fallback_text, "asked_key": None}

    lines = ["我帮你找到了这些更匹配的："]
    for idx, pid in enumerate(selected, start=1):
        i = id_to_item.get(pid)
        if not i:
            continue
        title = str(i.get("title") or "")
        url = str(i.get("external_url") or "")
        lines.append(f"{idx}. {title} {url}".strip())

    lines.append("如果你告诉我用途/预算/规格，我可以再更精准筛选。")
    return {"reply_text": "\n".join(lines)}


async def _node_update_memory(state: AgentState) -> AgentState:
    user_id = state["user_id"]
    selected = state.get("selected_ids") or []
    prefs = state.get("memory_preferences") or {}
    if not isinstance(prefs, dict):
        prefs = {}

    asked_key = state.get("asked_key")
    if asked_key:
        prefs = {**prefs, "last_question": asked_key}

    pending_need = state.get("pending_need")
    if pending_need:
        prefs = {**prefs, "pending_need": pending_need}

    if selected:
        prefs = {**prefs, "last_recommended_product_ids": selected}

    summary = state.get("memory_summary") or ""
    q = (state.get("text") or "").strip()
    if q:
        summary = (summary + "\n" + q).strip()[-2000:]

    MemoryRepo().upsert(user_id=user_id, preferences=prefs, summary_text=summary)
    MemoryRepo().append_event(user_id=user_id, event_type="message", payload={"text": q, "selected": selected})
    return {}


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("read_memory", _node_read_memory)
    g.add_node("extract_slots", _node_extract_slots)
    g.add_node("rewrite_query", _node_rewrite_query)
    g.add_node("retrieve", _node_retrieve)
    g.add_node("judge", _node_judge)
    g.add_node("compose", _node_compose_reply)
    g.add_node("update_memory", _node_update_memory)

    g.set_entry_point("read_memory")
    g.add_edge("read_memory", "extract_slots")
    g.add_edge("extract_slots", "rewrite_query")
    g.add_edge("rewrite_query", "retrieve")
    g.add_edge("retrieve", "judge")
    g.add_edge("judge", "compose")
    g.add_edge("compose", "update_memory")
    g.add_edge("update_memory", END)

    return g.compile()


GRAPH = build_graph()


async def run_agent(user_id: str, text: str) -> AgentResult:
    out = await GRAPH.ainvoke({"user_id": user_id, "text": text})
    reply_text = str(out.get("reply_text") or "")
    product_ids = [str(x) for x in (out.get("selected_ids") or [])]
    need_human = bool(out.get("need_human") or False)
    return AgentResult(reply_text=reply_text, product_ids=product_ids, need_human=need_human)
