import asyncio
import json
import re
import os
from pathlib import Path
from tabulate import tabulate

from app.infrastructure.db_adapters.adapter_factory import AdapterFactory
from app.infrastructure.llm_client import LLMClient
from app.application.schema_registry import SchemaRegistry
from app.application.execution_engine import ExecutionEngine
from app.application.conversation_manager import ConversationManager
from .query_generator_agent import QueryGeneratorAgent
from .response_agent import ResponseAgent
from app.infrastructure.logger import AppLogger


class RightShoringAgent:
    """Decision-policy layer that estimates prompt complexity and maps to
    execution choices using a structured policy (JSON).
 
    It exposes `decide(prompt, intent)` which returns a dict with keys like
    `requires_llm`, `execution_mode`, `model_tier`, `cost_level`,
    `complexity_score`, and `classification`.
    """
 
    def __init__(self, policy_path: str = None, config: dict = None):
        policy = None
        if policy_path and os.path.exists(policy_path):
            try:
                with open(policy_path, "r", encoding="utf-8") as f:
                    policy = json.load(f)
            except Exception as e:
                raise RuntimeError(f"Failed to load policy file: {e}")
        if config:
            if policy:
                policy.update(config)
            else:
                policy = config
        if not policy:
            raise RuntimeError("No policy provided for RightShoringAgent.")
 
        self.policy = policy
        self.weights = self.policy.get("WEIGHTS")
        self.thresholds = self.policy.get("PROMPT_COMPLEXITY_THRESHOLDS")
        self.model_map = self.policy.get("MODEL_MAPPING")
        self.intent_policies = self.policy.get("INTENT_POLICIES")
        self.risk = self.policy.get("RISK")
        self.entities = set(e.lower() for e in self.policy.get("ENTITIES", []))
        self.agg_keywords = [k.lower() for k in self.policy.get("AGG_KEYWORDS", [])]
        self.analytical_keywords = [k.lower() for k in self.policy.get("ANALYTICAL_KEYWORDS", [])]
        self.sorting_keywords = [k.lower() for k in self.policy.get("SORTING_KEYWORDS", [])]
        self.time_keywords = [k.lower() for k in self.policy.get("TIME_KEYWORDS", [])]
        # Similarity threshold for detecting "similar" prompts in history
        # If a previous user prompt is similar enough and is followed by an assistant
        # response, reuse that assistant response instead of calling the LLM again.
        self.similarity_threshold = float(self.policy.get("SIMILARITY_THRESHOLD", 0.8))
        # Lightweight knowledge base: store recent (canonicalized) prompt -> assistant response
        self.kb_max_entries = int(self.policy.get("KB_MAX_ENTRIES", 200))
        self.kb = []  # entries: dict with keys: prompt, canonical, response, intent
        # Whether to canonicalize numeric tokens (replace numbers with <NUM>) when matching
        self.kb_canonicalize_numbers = bool(self.policy.get("KB_CANONICALIZE_NUMBERS", True))
        self.similarity_threshold_query = float(self.policy.get("SIMILARITY_THRESHOLD_QUERY", 0.5))
 
    def calculate_prompt_complexity(self, prompt: str) -> int:
        p = (prompt or "").lower()
        score = 0
 
        # Entities
        entity_count = sum(1 for e in self.entities if e in p)
        if entity_count == 1:
            score += int(self.weights.get("entity_1", 1))
        elif entity_count == 2:
            score += int(self.weights.get("entity_2", 3))
        elif entity_count >= 3:
            score += int(self.weights.get("entity_3_plus", 6))
 
        # Aggregation
        if any(k in p for k in self.agg_keywords):
            score += int(self.weights.get("aggregation", 3))
 
        # Analytical
        if any(k in p for k in self.analytical_keywords):
            score += int(self.weights.get("analytical", 5))
 
        # Sorting
        if any(k in p for k in self.sorting_keywords):
            score += int(self.weights.get("sorting", 2))
 
        # Time
        if any(k in p for k in self.time_keywords):
            score += int(self.weights.get("time_filter", 2))
 
        # Risk
        risk_kw = self.risk.get("risk_keywords", [])
        if any(k in p for k in (kw.lower() for kw in risk_kw)):
            score += int(self.weights.get("risk", 7))
 
        return score
 
    def _tokenize(self, text: str):
        # split into lowercased word tokens, keep numbers as tokens
        if not text or not isinstance(text, str):
            return []
        tokens = re.findall(r"\w+", text.lower())
        return tokens
 
    def _canonicalize_prompt(self, text: str) -> str:
        if not text or not isinstance(text, str):
            return ""
        t = text.lower().strip()
        if self.kb_canonicalize_numbers:
            # replace long numeric tokens (ids, account numbers) with a placeholder
            t = re.sub(r"\b\d{2,}\b", "<NUM>", t)
        # collapse whitespace
        t = re.sub(r"\s+", " ", t)
        return t
 
    def _extract_number_tokens(self, tokens: list):
        return [t for t in tokens if re.fullmatch(r"\d+", t)]
 
    def _jaccard_similarity(self, a: set, b: set) -> float:
        if not a and not b:
            return 1.0
        inter = a.intersection(b)
        union = a.union(b)
        if not union:
            return 0.0
        return len(inter) / len(union)
 
    def _is_similar_prompt(self, a: str, b: str) -> bool:
        # Heuristic similarity: compare token overlap (Jaccard) after optional
        # canonicalization; ensure numeric tokens match when present unless
        # canonicalization is enabled.
        a_tokens = self._tokenize(a)
        b_tokens = self._tokenize(b)
 
        if self.kb_canonicalize_numbers:
            a_can = self._canonicalize_prompt(a)
            b_can = self._canonicalize_prompt(b)
            a_non = set(self._tokenize(a_can))
            b_non = set(self._tokenize(b_can))
        else:
            a_nums = set(self._extract_number_tokens(a_tokens))
            b_nums = set(self._extract_number_tokens(b_tokens))
            # If both contain numbers and they differ, treat as different prompts.
            if a_nums or b_nums:
                if a_nums != b_nums:
                    return False
            a_non = set(t for t in a_tokens if not re.fullmatch(r"\d+", t))
            b_non = set(t for t in b_tokens if not re.fullmatch(r"\d+", t))
 
        score = self._jaccard_similarity(a_non, b_non)
        return score >= self.similarity_threshold
 
    def _kb_search(self, prompt: str, intent: dict = None):
        """Search KB for a canonical match. Returns response or None."""
        if not prompt:
            return None
        can = self._canonicalize_prompt(prompt)
        for entry in reversed(self.kb):
            try:
                entry_can = entry.get("canonical")
                if not entry_can:
                    continue
                # quick exact match
                if entry_can == can:
                    return entry.get("response")
                # fuzzy match
                if self._is_similar_prompt(entry.get("prompt", ""), prompt):
                    # optionally match intent types to avoid reusing different operations
                    if intent and entry.get("intent"):
                        if entry.get("intent").get("operation_type") != intent.get("operation_type"):
                            continue
                    return entry.get("response")
            except Exception:
                continue
        return None
 
    def store_kb_entry(self, prompt: str, response: str, intent: dict = None):
        try:
            can = self._canonicalize_prompt(prompt)
            entry = {"prompt": prompt, "canonical": can, "response": response, "intent": intent}
            self.kb.append(entry)
            # trim
            if len(self.kb) > self.kb_max_entries:
                self.kb = self.kb[-self.kb_max_entries:]
        except Exception:
            pass
 
    def _kb_search_query(self, prompt: str, intent: dict = None):
        """Search KB for a stored SQL query for a similar prompt. Returns query or None."""
        if not prompt:
            return None
        can = self._canonicalize_prompt(prompt)
        for entry in reversed(self.kb):
            try:
                # entry may have 'query' key
                if entry.get("canonical") == can and entry.get("query"):
                    return entry.get("query")
                # fuzzy match
                # compute jaccard similarity score for query-matching
                a = entry.get("prompt", "")
                b = prompt
                # quick domain-keyword match: if both contain customer + high + risk, consider it equivalent
                a_set = set(self._tokenize(a))
                b_set = set(self._tokenize(b))
                domain_keys = {"customer", "customers", "risk", "high", "profile"}
                if ("risk" in a_set and "high" in a_set and ("customer" in a_set or "customers" in a_set)):
                    if ("risk" in b_set and "high" in b_set and ("customer" in b_set or "customers" in b_set)):
                        if entry.get("query"):
                            if intent and entry.get("intent"):
                                if entry.get("intent").get("operation_type") != intent.get("operation_type"):
                                    continue
                            return entry.get("query")
                a_tokens = self._tokenize(a)
                b_tokens = self._tokenize(b)
                if self.kb_canonicalize_numbers:
                    a_can = self._canonicalize_prompt(a)
                    b_can = self._canonicalize_prompt(b)
                    a_non = set(self._tokenize(a_can))
                    b_non = set(self._tokenize(b_can))
                else:
                    a_non = set(t for t in a_tokens if not re.fullmatch(r"\d+", t))
                    b_non = set(t for t in b_tokens if not re.fullmatch(r"\d+", t))
 
                score = self._jaccard_similarity(a_non, b_non)
                if score >= self.similarity_threshold_query and entry.get("query"):
                    if intent and entry.get("intent"):
                        if entry.get("intent").get("operation_type") != intent.get("operation_type"):
                            continue
                    return entry.get("query")
            except Exception:
                continue
        return None
 
    def store_query_entry(self, prompt: str, query: str, intent: dict = None):
        """Store a prompt -> query mapping in the KB."""
        try:
            can = self._canonicalize_prompt(prompt)
            entry = {"prompt": prompt, "canonical": can, "query": query, "intent": intent}
            self.kb.append(entry)
            if len(self.kb) > self.kb_max_entries:
                self.kb = self.kb[-self.kb_max_entries:]
        except Exception:
            pass
 
    def classify(self, score: int) -> str:
        if score <= int(self.thresholds.get("low", 4)):
            return "low"
        if score <= int(self.thresholds.get("medium", 9)):
            return "medium"
        return "high"
 
    def decide(self, prompt: str, intent: str, history: list = None) -> dict:
        """Return decision dict based on policy and prompt features.
 
        If `history` is provided (list of message dicts), detect repeated user
        prompts and return a cached assistant response when available to avoid
        unnecessary LLM calls.
        """
        score = self.calculate_prompt_complexity(prompt)
        classification = self.classify(score)
 
        # Base decision from intent policy
        base = self.intent_policies.get(intent, {}) if intent else {}
 
        decision = {
            "intent": intent,
            "complexity_score": score,
            "classification": classification,
            "requires_llm": base.get("requires_llm", True),
            "execution_mode": base.get("execution_mode", "sql_generation"),
            "model_type": base.get("model_type", self.model_map.get(classification)),
            "cost_level": base.get("cost_level", "medium")
        }
 
        # Risk override
        p = (prompt or "").lower()
        risk_kw = self.risk.get("risk_keywords", [])
        if any(k in p for k in (kw.lower() for kw in risk_kw)):
            decision["model_type"] = self.risk.get("force_model") or decision["model_type"]
            decision["risk_detected"] = True
        else:
            decision["risk_detected"] = False
 
        # Repetition detection: if the same user prompt exists in history and
        # is followed by an assistant reply, treat as cached and avoid LLM.
        if history and isinstance(history, list):
            for i in range(len(history) - 1):
                try:
                    if history[i].get("role") == "user" and history[i].get("content", "").strip() == (prompt or "").strip():
                        if history[i + 1].get("role") == "assistant":
                            cached = history[i + 1].get("content")
                            decision["requires_llm"] = False
                            decision["execution_mode"] = "static_response"
                            decision["cached_response"] = cached
                            decision["reason"] = "repeat_from_history"
                            break
                except Exception:
                    continue
 
            # If no exact repeat found, try similarity-based reuse (smarter caching)
            try:
                for i in range(len(history) - 1):
                    if history[i].get("role") != "user":
                        continue
                    prev = history[i].get("content", "")
                    if not prev:
                        continue
                    if self._is_similar_prompt(prev, prompt):
                        # only reuse when the next message is an assistant response
                        if i + 1 < len(history) and history[i + 1].get("role") == "assistant":
                            cached = history[i + 1].get("content")
                            decision["requires_llm"] = False
                            decision["execution_mode"] = "static_response"
                            decision["cached_response"] = cached
                            decision["reason"] = "similar_from_history"
                            break
            except Exception:
                pass
 
        return decision

class Orchestrator:
 
    MAX_RETRIES = int(os.getenv("ORCHESTRATOR_MAX_RETRIES", 2))
 
    def __init__(self, config: dict = None):
        config = config or {}
 
        try:
            self.adapter = AdapterFactory.create_adapter()
        except Exception as e:
            AppLogger.error(f"Adapter creation failed: {e}")
            raise
 
        # Async connection will happen in async initialization
        self.schema_registry = SchemaRegistry(self.adapter)
        self.execution_engine = ExecutionEngine(self.adapter)
        self._initialized = False
 
        # Remove model_name argument
        self.llm = LLMClient()
        self.query_agent = QueryGeneratorAgent(self.llm, self.schema_registry)
        self.response_agent = ResponseAgent(self.llm)
 
        # Rightshoring decision layer
        policy_path = config.get("policy_path") or (Path(__file__).parent / "rightshoring_policy.json")
        try:
            self.rightshoring = RightShoringAgent(policy_path=str(policy_path), config=config.get("rightshoring"))
        except Exception:
            self.rightshoring = RightShoringAgent(config=config.get("rightshoring"))
        self.memory = ConversationManager(self.llm)
 
        self.last_query = None
        self.last_result = None
 
    async def initialize(self):
        """Initialize async components (connect to database, load schema)."""
        if self._initialized:
            return
       
        try:
            await self.adapter.connect()
            await self.schema_registry.initialize()
            self._initialized = True
        except Exception as e:
            AppLogger.error(f"Failed to initialize Orchestrator: {e}")
            raise
 
    def _safe_json_loads(self, text: str):
        """Try to parse JSON robustly from LLM outputs that may include extra text.
 
        Returns parsed object or raises JSONDecodeError if unable to parse.
        """
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to decode first JSON object from the string
            try:
                from json import JSONDecoder
                decoder = JSONDecoder()
                obj, idx = decoder.raw_decode(text)
                return obj
            except Exception:
                pass
 
            # Fallback: regex to extract first {...}
            m = re.search(r"(\{[\s\S]*\})", text)
            if m:
                try:
                    return json.loads(m.group(1))
                except Exception:
                    pass
 
            # Give up
            raise
 
    # ----------------------------
    # LLM INTENT ROUTER
    # ----------------------------
    async def _route_intent(self, question: str):
        schema_tables = list(self.schema_registry.schema.keys())
        router_prompt = os.getenv("ROUTER_PROMPT")
        if router_prompt:
            ROUTER_PROMPT = router_prompt.format(schema_tables=schema_tables)
        else:
            ROUTER_PROMPT = f"""
You are an AI Orchestrator.
 
Classify the user request into one of the following intents:
 
- GREETING
- GENERAL_CONVERSATION
- SIMPLE_INTEREST
- COMPOUND_INTEREST
- DATABASE_QUERY
- SESSION_SUMMARY
- OUT_OF_SCOPE
- SQL_QUERY
 
Available Database Tables:
{schema_tables}
 
Return STRICT JSON:
 
{{
  "intent": "...",
  "reason": "short explanation"
}}
 
JSON only.
"""
 
        messages = [
            {"role": "system", "content": ROUTER_PROMPT},
            {"role": "user", "content": question}
        ]
 
        resp = await self.llm.chat_completion(messages=messages, temperature=0)
        try:
            return self._safe_json_loads(resp.choices[0].message.content)
        except Exception:
            # propagate JSON parse failure to caller
            raise
 
    # ----------------------------
    # Deterministic Interest Logic
    # ----------------------------
    def _compute_simple_interest(self, principal, rate, time):
        si = principal * rate * time / 100
        return {
            "interest": si,
            "total": principal + si
        }
 
    def _compute_compound_interest(self, principal, rate, time, n):
        amount = principal * ((1 + (rate / 100) / n) ** (n * time))
        return {
            "interest": amount - principal,
            "total": amount
        }