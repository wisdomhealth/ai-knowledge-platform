from app.agents.memory import ConversationMemory
from app.integrations.exceptions import IntegrationNotConfigured
from app.integrations.openai_client import OpenAIClient
from app.rag.service import RagService
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.agents import ConversationRequest, ConversationResponse, RagSourceSchema


class ConversationAgent:
    """Handle user queries with conversation memory and RAG context."""

    system_prompt = (
        "You are a production AI backend assistant. Answer clearly, cite available context, "
        "and say when the indexed knowledge base does not contain enough evidence."
    )

    # Constructor arguments:
    #     repository: Data access object for conversations, messages, and agent runs.
    #     memory: Memory component that loads recent conversation messages.
    #     openai_client: Client used to call the OpenAI chat model.
    #     rag_service: RAG service used to retrieve knowledge-base context.
    def __init__(
        self,
        *,
        repository: ConversationRepository,
        memory: ConversationMemory,
        openai_client: OpenAIClient,
        rag_service: RagService,
    ):
        self.repository = repository
        self.memory = memory
        self.openai_client = openai_client
        self.rag_service = rag_service

    async def respond(self, payload: ConversationRequest) -> ConversationResponse:
        conversation = None
        if payload.conversation_id:
            conversation = await self.repository.get_conversation(payload.conversation_id)
        if conversation is None:
            conversation = await self.repository.create_conversation(
                user_id=payload.user_id,
                title=payload.message[:80],
                metadata=payload.metadata,
            )

        run = await self.repository.create_agent_run(
            agent_type="conversation",
            conversation_id=conversation.id,
            goal=payload.message,
            input_json=payload.model_dump(mode="json"),
        )
        user_message = await self.repository.add_message(
            conversation_id=conversation.id,
            role="user",
            content=payload.message,
        )

        sources = []
        context_block = ""
        if payload.use_rag:
            sources = await self.rag_service.search(query=payload.message, limit=payload.rag_limit)
            context_block = "\n\n".join(source.content for source in sources)

        history = await self.memory.load_messages(conversation_id=conversation.id)
        messages = [{"role": "system", "content": self.system_prompt}]
        if context_block:
            messages.append({"role": "system", "content": f"Indexed context:\n{context_block}"})
        messages.extend(history)

        try:
            answer = await self.openai_client.chat(messages=messages)
        except IntegrationNotConfigured:
            if context_block:
                answer = (
                    "OpenAI is not configured, but I found relevant indexed context:\n\n"
                    f"{context_block[:1500]}"
                )
            else:
                answer = "OpenAI is not configured and no matching indexed context was found."

        assistant_message = await self.repository.add_message(
            conversation_id=conversation.id,
            role="assistant",
            content=answer,
        )
        await self.repository.complete_agent_run(
            run,
            status="completed",
            output_json={"answer": answer, "message_id": str(assistant_message.id)},
            trace=[{"event": "rag.search", "sources": len(sources)}],
        )

        return ConversationResponse(
            conversation_id=conversation.id,
            run_id=run.id,
            user_message_id=user_message.id,
            assistant_message_id=assistant_message.id,
            answer=answer,
            sources=[
                RagSourceSchema(
                    document_id=source.document_id,
                    chunk_id=source.chunk_id,
                    title=source.title,
                    content=source.content,
                    score=source.score,
                )
                for source in sources
            ],
        )
