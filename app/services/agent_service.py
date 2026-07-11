from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.conversation_agent import ConversationAgent
from app.agents.memory import ConversationMemory
from app.agents.tool_registry import RuntimeContext
from app.agents.tools import build_default_tool_registry
from app.agents.workflow_agent import WorkflowAgent
from app.integrations.openai_client import OpenAIClient
from app.rag.service import RagService
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.agents import (
    ConversationRequest,
    ConversationResponse,
    WorkflowRequest,
    WorkflowResponse,
)
from app.services.google_sheets_service import GoogleSheetsService
from app.services.web_scraper_service import WebScraperService


class AgentService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        openai_client: OpenAIClient,
        rag_service: RagService,
        google_sheets_service: GoogleSheetsService,
        web_scraper_service: WebScraperService,
    ):
        self.session = session
        self.repository = ConversationRepository(session)
        self.rag_service = rag_service
        self.openai_client = openai_client
        self.google_sheets_service = google_sheets_service
        self.web_scraper_service = web_scraper_service

    async def conversation(self, payload: ConversationRequest) -> ConversationResponse:
        agent = ConversationAgent(
            repository=self.repository,
            memory=ConversationMemory(repository=self.repository),
            openai_client=self.openai_client,
            rag_service=self.rag_service,
        )
        response = await agent.respond(payload)
        await self.session.commit()
        return response

    async def workflow(self, payload: WorkflowRequest) -> WorkflowResponse:
        runtime_context = RuntimeContext(
            rag_service=self.rag_service,
            web_scraper_service=self.web_scraper_service,
            google_sheets_service=self.google_sheets_service,
        )
        agent = WorkflowAgent(
            repository=self.repository,
            registry=build_default_tool_registry(),
            runtime_context=runtime_context,
        )
        response = await agent.run(payload)
        await self.session.commit()
        return response
