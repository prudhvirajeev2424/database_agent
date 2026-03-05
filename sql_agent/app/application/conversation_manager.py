from typing import List, Dict
from app.infrastructure.logger import AppLogger

class ConversationManager:
    """
    Token-aware rolling memory manager.

    - No fixed message limit.
    - Compresses only when estimated token usage exceeds threshold.
    - Keeps recent context intact.
    """

    def __init__(
        self,
        llm,
        token_limit: int = 6000,      
        compression_ratio: float = 0.5
    ):
        self.llm = llm
        self.history: List[Dict[str, str]] = []
        self.token_limit = token_limit
        self.compression_ratio = compression_ratio

    # =====================================================
    # Add Messages
    # =====================================================

    async def add_user(self, message: str):
        self.history.append({"role": "user", "content": message})
        await self._manage_memory()

    async def add_assistant(self, message: str):
        self.history.append({"role": "assistant", "content": message})
        await self._manage_memory()

    def get_history(self):
        return self.history

    # =====================================================
    # Token Estimation
    # =====================================================

    def _estimate_tokens(self) -> int:
        """
        Rough token estimate:
        ~4 characters ≈ 1 token (approximation)
        """
        total_chars = sum(len(m["content"]) for m in self.history)
        return total_chars // 4

    # =====================================================
    # Memory Control
    # =====================================================

    async def _manage_memory(self):

        current_tokens = self._estimate_tokens()

        if current_tokens < self.token_limit:
            return

        AppLogger.info("Token limit exceeded. Compressing memory.")

        await self._compress_memory()

    # =====================================================
    # Compression Logic
    # =====================================================

    async def _compress_memory(self):

        try:
            # Split old vs recent messages
            split_index = int(len(self.history) * self.compression_ratio)

            old_messages = self.history[:split_index]
            recent_messages = self.history[split_index:]

            conversation_text = "\n".join(
                f"{m['role'].upper()}: {m['content']}"
                for m in old_messages
            )

            prompt = f"""
You are a conversation compression engine.

Summarize the following conversation while preserving:

- Tables discussed
- Filters applied
- Aggregations used
- User preferences (format type, JSON, table, summary)
- Important constraints

Keep it compact but context-complete.

Conversation:
{conversation_text}

Return ONLY the summary text.
"""

            response = await self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )

            summary_text = response.choices[0].message.content.strip()

            # Rebuild history
            self.history = [
                {
                    "role": "system",
                    "content": f"Summary of earlier conversation:\n{summary_text}"
                }
            ] + recent_messages

            AppLogger.info("Memory compression successful.")

        except Exception as e:
            AppLogger.error(f"Memory compression failed: {e}")
            # Emergency fallback: keep recent only
            self.history = self.history[-10:]