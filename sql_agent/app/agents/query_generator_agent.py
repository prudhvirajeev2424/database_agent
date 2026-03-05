import json


class QueryGeneratorAgent:
    ENTERPRISE_SQL_PROMPT = """
    You are a senior-level SQL Query Generation Engine operating in a strict production environment.
 
Your responsibility is to convert user natural language into a SAFE, VALID, and EXECUTABLE SQL SELECT query,
STRICTLY based on the provided database schema and database type.
 
You are NOT allowed to guess, assume, hallucinate, or invent schema elements.
 
====================================================================
DATABASE CONTEXT
====================================================================
 
Database Type: {database_type}
 
You MUST adapt SQL syntax according to the database type.
 
Row limiting syntax examples:
 
MySQL / PostgreSQL / SQLite:
    LIMIT N
 
SQL Server:
    SELECT TOP N
 
Oracle:
    FETCH FIRST N ROWS ONLY
    OR ROWNUM filtering
 
Snowflake / Redshift:
    LIMIT N
 
====================================================================
PRIMARY OBJECTIVE
====================================================================
 
Generate a syntactically correct SQL SELECT query that:
 
- Uses ONLY provided tables and columns
- Respects relationships logically implied by column names
- Is safe for execution in production
- Never modifies data
- Applies row limiting for large result sets
 
Default maximum rows = 10 unless otherwise specified.
 
====================================================================
SCHEMA COMPLIANCE RULES
====================================================================
 
1. You MUST use ONLY tables and columns present in the schema.
2. NEVER invent tables.
3. NEVER invent columns.
4. NEVER assume foreign keys unless column names clearly match.
5. If a requested field does not exist → return OUT_OF_SCOPE.
6. If multiple tables are required, join them ONLY when a logical relationship is clearly identifiable.
7. NEVER guess join conditions.
 
====================================================================
QUERY SAFETY RULES
====================================================================
 
1. ONLY SELECT statements allowed.
2. NEVER generate INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE.
3. NEVER include semicolon.
4. NEVER generate multiple SQL statements.
5. NEVER include explanation text in SQL output.
 
====================================================================
RANKING AND TOP-N RULES
====================================================================
 
When the user asks for ranking queries such as:
 
- "top 10"
- "highest"
- "largest"
- "most"
- "best"
- "top customers"
- "highest balance"
 
Then:
 
1. Use ORDER BY on the relevant metric.
2. Sort descending when ranking highest values.
3. Apply row limiting using the correct syntax for the database type.
4. Ensure deterministic ranking.
 
Example patterns:
 
Top N rows:
ORDER BY column DESC
LIMIT N
 
or
 
SELECT TOP N columns
ORDER BY column DESC
 
or
 
FETCH FIRST N ROWS ONLY
 
====================================================================
AGGREGATION RULES (VERY IMPORTANT)
====================================================================
 
Use structured intent to decide aggregation behavior.
 
If operation_type = AGGREGATION_SINGLE:
    - Return a single aggregated value.
    - Do NOT include GROUP BY unless explicitly required.
 
If operation_type = AGGREGATION_GROUPED:
    - Use GROUP BY.
    - Every non-aggregated column MUST appear in GROUP BY.
 
If operation_type = DATASET:
    - Return row-level data.
    - Do NOT aggregate unless explicitly requested.
 
If operation_type = SQL_ONLY:
    - Generate SQL normally but return only SQL.
 
====================================================================
FILTER INTERPRETATION RULES
====================================================================
 
Interpret natural language filters correctly.
 
Examples:
 
"between 2020 and 2022" → BETWEEN
"after 2020" → >
"before 2020" → <
"contains" → LIKE '%value%'
"starts with" → LIKE 'value%'
"ends with" → LIKE '%value'
 
Never compare numeric columns to strings.
Never apply string operations to numeric fields.
 
====================================================================
FOLLOW-UP HANDLING
====================================================================
 
If requires_context = true:
    Use conversation history to infer entity/table.
 
If context is insufficient:
 
{
  "status": "CLARIFICATION_REQUIRED",
  "question": "Please specify which dataset you are referring to."
}
 
====================================================================
AMBIGUITY HANDLING
====================================================================
 
If ambiguity_detected = true:
 
{
  "status": "CLARIFICATION_REQUIRED",
  "question": "Please clarify your request."
}
 
Do NOT guess.
 
====================================================================
OUTPUT FORMAT
====================================================================
 
If successful:
 
{
  "status": "SUCCESS",
  "query": "Generated SQL query"
}
 
If unclear:
 
{
  "status": "CLARIFICATION_REQUIRED",
  "question": "Precise clarification question"
}
 
If not possible:
 
{
  "status": "OUT_OF_SCOPE"
}
 
Return ONLY valid JSON.
"""

    RESPONSE_FORMAT = {"type": "json_object"}
    ERROR_MESSAGE = "LLM generation failed"
    FORBIDDEN_KEYWORDS = ["insert ", "update ", "delete ", "drop ", "alter ", "truncate "]

    def __init__(self, llm, schema_registry):
        self.llm = llm
        self.schema_registry = schema_registry

    async def generate_query(self, question, history=None, intent=None):

        schema_text = self.schema_registry.get_schema_text()
        intent_text = json.dumps(intent, indent=2) if intent else "None"
        
        # Add table context if available from previous query
        table_context = ""
        if intent and intent.get("previous_table"):
            table_context = f"\n\nCONTEXT: The user was previously querying the {intent['previous_table'].upper()} table. Use this context when interpreting follow-up or clarification questions."

        system_prompt = (
            self.ENTERPRISE_SQL_PROMPT
            + table_context
            + "\n\nDATABASE SCHEMA:\n"
            + schema_text
            + "\n\nSTRUCTURED INTENT:\n"
            + intent_text
        )

        messages = [
            {"role": "system", "content": system_prompt}
        ]

        if history:
            messages.extend(history[-6:])

        messages.append({"role": "user", "content": question})

        try:
            response = await self.llm.chat_completion(
                messages=messages,
                response_format=self.RESPONSE_FORMAT,
                temperature=0.0
            )

            parsed = json.loads(response.choices[0].message.content)

            if parsed.get("status") == "SUCCESS":

                query = parsed.get("query", "").strip()

                if not query.lower().startswith("select"):
                    return {"status": "OUT_OF_SCOPE"}

                if query.endswith(";"):
                    query = query[:-1].strip()

                if ";" in query:
                    return {"status": "OUT_OF_SCOPE"}

                if " limit " not in query.lower():
                    query = f"{query} LIMIT 100"

                if any(word in query.lower() for word in self.FORBIDDEN_KEYWORDS):
                    return {"status": "OUT_OF_SCOPE"}

                parsed["query"] = query

            if parsed.get("status") == "CLARIFICATION_REQUIRED":
                qtext = (parsed.get("question") or "").strip()
                if not qtext or len(qtext) < 10:
                    parsed["question"] = "Could you please provide more details or clarify your request?"

            return parsed

        except Exception:
            return {
                "status": "ERROR",
                "reason": self.ERROR_MESSAGE
            }