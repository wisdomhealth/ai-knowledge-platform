import uuid

from app.repositories.conversation_repository import ConversationRepository


class ConversationMemory:
    """Load conversation history and convert it into the model message format.

    Constructor arguments:
        repository: Data access object used to query conversation messages.
    """

    def __init__(self, *, repository: ConversationRepository):
        self.repository = repository

    async def load_messages(
        self,
        *,
        conversation_id: uuid.UUID,
        limit: int = 12,
    ) -> list[dict[str, str]]:
        messages = await self.repository.list_recent_messages(conversation_id, limit=limit)
        return [{"role": message.role, "content": message.content} for message in messages]
