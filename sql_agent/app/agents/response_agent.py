import json
import re
from datetime import datetime
from tabulate import tabulate
from app.infrastructure.logger import AppLogger


class ResponseAgent:
    RESPONSE_PROMPT = """
    You are a senior-level database reporting and analytics engine operating in a strict production environment.

    You MUST generate output strictly based on:
    1. SQL result set
    2. Structured intent
    3. User question

    You MUST NOT:
    - Invent data
    - Infer missing information
    - Add assumptions
    - Add external knowledge
    - Modify numeric precision
    - Reformat timestamps
    - Compute new metrics
    - Drop records
    - Reorder fields unless explicitly requested

    ============================================================
    SUMMARY MODE INSTRUCTIONS
    ============================================================

    If output_format = SUMMARY or AUTO (and summary appropriate):

    Provide:
    - Record count
    - Key metrics (if present)
    - Aggregations (if present)
    - Structured professional formatting

    DO NOT:
    - Include raw JSON
    - Include SQL
    - Add headings outside summary mode

    ============================================================
    CRITICAL RULES
    ============================================================

    Return ONLY the requested output.
    No markdown.
    No explanations unless summary mode.
    """
    OUT_OF_SCOPE_MESSAGE = "This question is outside the scope of the connected database."
    NO_RECORDS_MESSAGE = "No records found for this query."
    NO_MATCHING_RECORDS_MESSAGE = "No records found matching the criteria for this query."
    ERROR_MESSAGE = "Response generation failed: {e}"
    ANALYSIS_REPORT_HEADER = """
====================================================
AI DATABASE ANALYSIS REPORT
Generated: {timestamp}
====================================================
"""
    ANALYSIS_REPORT_FOOTER = """
====================================================
"""
    PRIMARY_ORDER = [
        "account_number", "account_type", "branch_name", "balance",
        "status", "opened_date", "customer_id", "account_id"
    ]

    def __init__(self, llm):
        self.llm = llm

    async def generate_response(
        self,
        question,
        result,
        query=None,
        intent=None,
        history=None,
        detailed: bool = False,
        **kwargs
    ):

        if result == "OUT_OF_SCOPE":
            return self.OUT_OF_SCOPE_MESSAGE

        if not result:
            return self.NO_RECORDS_MESSAGE
        
        # Handle aggregation queries that return NULL values (e.g., SUM with no matching rows)
        if isinstance(result, list) and len(result) > 0:
            # Check if all values in all rows are None
            all_none = True
            for row in result:
                if isinstance(row, dict):
                    for value in row.values():
                        if value is not None:
                            all_none = False
                            break
                else:
                    all_none = False
                    break
            
            if all_none:
                return self.NO_MATCHING_RECORDS_MESSAGE

        operation_type = intent.get("operation_type") if intent else "DATASET"
        output_format = intent.get("output_format") if intent else "AUTO"

        # ==========================================================
        # DETERMINISTIC ROUTING FIRST (NO LLM)
        # ==========================================================

        # 1️⃣ SQL FORMAT
        if output_format == "SQL":
            return query

        # 2️⃣ JSON FORMAT
        if output_format == "JSON":
            return json.dumps(result, indent=2, default=str)

        # 3️⃣ TABLE FORMAT
        # If caller or intent explicitly requested TABLE, render a table here.
        if output_format == "TABLE":
            if isinstance(result, list) and result:
                headers = result[0].keys()
                rows = [row.values() for row in result]
                return "\n" + tabulate(rows, headers=headers, tablefmt="grid")
            else:
                return str(result)

        # 4️⃣ AUTO MODE — infer user's preference from the question and result
        if output_format == "AUTO":
            inferred = self._infer_output_format(question, result, intent)

            if inferred == "TABLE" and isinstance(result, list) and result:
                headers = result[0].keys()
                rows = [row.values() for row in result]
                return "\n" + tabulate(rows, headers=headers, tablefmt="grid")

            # SUMMARY preferred: give a concise plain-English summary by default
            if inferred == "SUMMARY":
                if isinstance(result, list):
                    count = len(result)
                    if count == 0:
                        return self.NO_RECORDS_MESSAGE
                    if count == 1 and isinstance(result[0], dict):
                        # Check if it's aggregated (has keys starting with total_, sum_, count_, avg_, etc.)
                        keys = list(result[0].keys())
                        agg_indicators = ['total_', 'sum_', 'count_', 'avg_', 'average_', 'min_', 'max_']
                        if any(any(k.lower().startswith(ind) for ind in agg_indicators) for k in keys):
                            # It's aggregated, present directly as key-value pairs
                            items = [f"{k}: {v}" for k, v in result[0].items() if v is not None]
                            return ", ".join(items)
                    
                    # Check if this is an overview request (indicated in intent)
                    is_overview = intent and intent.get("is_overview_request", False)
                    if is_overview:
                        # For overview requests, provide statistical summary
                        summary = self._generate_table_statistics(result)
                        return summary
                    
                    # Otherwise, default summary
                    first = result[0] if count > 0 else None
                    summary = f"Found {count} record{'s' if count != 1 else ''}."
                    if first and isinstance(first, dict):
                        sample = self._summarize_single_record(first, intent=intent, detailed=False)
                        summary += " Example record: " + sample
                    return summary

                if isinstance(result, dict):
                    return self._summarize_single_record(result, intent=intent, detailed=detailed)

                # Fallback to JSON for other types
                return json.dumps(result, indent=2, default=str)

        # If result is a single dict (not wrapped in a list), summarize it for readability
        if isinstance(result, dict) and output_format in ("AUTO", "SUMMARY"):
            # Check if it's aggregated data
            keys = list(result.keys())
            agg_indicators = ['total_', 'sum_', 'count_', 'avg_', 'average_', 'min_', 'max_']
            if any(any(k.lower().startswith(ind) for ind in agg_indicators) for k in keys):
                # It's aggregated, present directly as key-value pairs with clean formatting
                items = []
                for k, v in result.items():
                    if v is not None:
                        # Format the key nicely
                        display_key = k.replace('_', ' ').title()
                        # Format the value
                        if isinstance(v, (int, float)) and '.' in str(v):
                            display_val = self._format_currency(v)
                        else:
                            display_val = str(v)
                        items.append(f"{display_key}: {display_val}")
                return ", ".join(items)
            return self._summarize_single_record(result, intent=intent, detailed=detailed)

        # ==========================================================
        # SUMMARY / ANALYTICS MODE (LLM REQUIRED)
        # ==========================================================

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        intent_text = json.dumps(intent, indent=2) if intent else "None"

        user_content = f"""
User Question:
{question}

Structured Intent:
{intent_text}

SQL Query:
{query}

Result (JSON):
{json.dumps(result, indent=2, default=str)}
"""

        # If detailed requested, nudge the assistant to provide deeper analysis
        system_prompt = self.RESPONSE_PROMPT
        if detailed:
            system_prompt = self.RESPONSE_PROMPT + "\n\nProvide a detailed analysis, explaining key drivers, notable anomalies, and suggested next steps. Use professional, concise language."

        try:
            resp = await self.llm.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.0
            )

            content = resp.choices[0].message.content.strip()

            return (
                self.ANALYSIS_REPORT_HEADER.format(timestamp=timestamp)
                + f"\n{content}\n"
                + self.ANALYSIS_REPORT_FOOTER
            )

        except Exception as e:
            AppLogger.error(f"ResponseAgent failed: {e}")
            return self.ERROR_MESSAGE.format(e=e)

    def _generate_table_statistics(self, result: list) -> str:
        """Generate statistical summary for overview requests."""
        if not result:
            return "No records found."
        
        count = len(result)
        stats = []
        stats.append(f"Total Records: {count}")
        
        # Analyze columns for basic statistics
        if isinstance(result[0], dict):
            keys = list(result[0].keys())
            stats.append(f"Columns: {', '.join(keys)}")
            
            # Try to find numeric columns for basic stats
            numeric_cols = {}
            for key in keys:
                values = []
                for row in result:
                    val = row.get(key)
                    if isinstance(val, (int, float)):
                        values.append(val)
                
                if values and len(values) > 0:
                    try:
                        numeric_cols[key] = {
                            'min': min(values),
                            'max': max(values),
                            'avg': sum(values) / len(values)
                        }
                    except Exception:
                        pass
            
            # Add numeric statistics if found
            if numeric_cols:
                stats.append("\nNumeric Summaries:")
                for col, nums in numeric_cols.items():
                    stats.append(f"  {col}: min={self._format_currency(nums['min'])}, avg={self._format_currency(nums['avg'])}, max={self._format_currency(nums['max'])}")
        
        return "\n".join(stats)

    def _format_currency(self, value):
        try:
            v = float(value)
            return f"{v:,.2f}"
        except Exception:
            return str(value)

    def _summarize_single_record(self, record: dict, intent=None, detailed: bool = False) -> str:
        # Prefer common banking fields in a readable sentence
        primary_order = self.PRIMARY_ORDER

        parts = []
        # account identity
        acct_num = record.get("account_number") or record.get("account_id")
        acct_type = record.get("account_type")
        if acct_num and acct_type:
            parts.append(f"Account {acct_num} ({acct_type})")
        elif acct_num:
            parts.append(f"Account {acct_num}")

        # branch
        branch = record.get("branch_name")
        if branch:
            parts.append(f"at branch {branch}")

        # balance
        balance = record.get("balance")
        if balance is not None:
            parts.append(f"has a balance of {self._format_currency(balance)}")

        # status/opened
        status = record.get("status")
        opened = record.get("opened_date")
        extras = []
        if status:
            extras.append(str(status))
        if opened:
            extras.append(f"opened on {opened}")
        if extras:
            parts.append("(" + ", ".join(extras) + ")")

        # Fallback: include a few other informative fields
        fallback_fields = []
        for k in primary_order:
            if k in record and record.get(k) is not None:
                # already included above
                continue
        # If we built parts, join into a sentence
        if parts:
            summary = " ".join(parts) + "."
        else:
            # Generic summary: list key: value pairs
            items = [f"{k}: {v}" for k, v in record.items() if v is not None]
            summary = ", ".join(items)

        if detailed:
            # Add a compact JSON block for detail when requested
            try:
                json_block = json.dumps(record, indent=2, default=str)
                return summary + "\n\n" + json_block
            except Exception:
                return summary

        return summary

    def _infer_output_format(self, question: str, result, intent=None) -> str:
        """Heuristic to infer desired output format from the user's question and result.

        Returns one of: 'TABLE', 'SUMMARY', 'JSON'. Defaults to 'SUMMARY' unless
        the user explicitly requests a tabular presentation.
        """
        if not question or not isinstance(question, str):
            return "SUMMARY"

        q = question.lower()

        # Explicit requests for tables / CSV / spreadsheet
        if re.search(r"\b(table|tabular|as a table|in a table|grid|csv|spreadsheet|tabulate|show as table|tabularly|list|in list)\b", q):
            return "TABLE"

        # Explicit quantifiers implying every/ALL records → prefer TABLE
        if re.search(r"\b(all|every|each|for each|for every|all customers|every customer|all accounts|every account)\b", q):
            return "TABLE"

        # Explicit requests for summaries, explanations, or plain English
        if re.search(r"\b(summary|summarize|in plain english|explain|describe|interpret|what does|trend|trends|history)\b", q):
            return "SUMMARY"

        # (Removed loose heuristics like 'show' or 'list' → TABLE.)

        # Default: prefer a concise plain-English summary
        return "SUMMARY"