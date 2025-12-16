"""Query engine for the Vista."""

from typing import List
import logging
from enum import Enum
from pathlib import Path

from vista.models import QueryResponse, RetrievedChunk
from vista.vector_store import VectorStoreManager
from vista.embedding_generator import EmbeddingGenerator
from vista.llm_base import BaseLLMClient

logger = logging.getLogger(__name__)


class QueryIntent(Enum):
    GREETING = "GREETING"
    IDENTITY = "IDENTITY"
    META = "META"
    KNOWLEDGE = "KNOWLEDGE"


class QueryEngine:
    """Processes user queries and orchestrates retrieval and generation."""

    def __init__(
        self,
        vector_store: VectorStoreManager,
        embedding_gen: EmbeddingGenerator,
        llm_client: BaseLLMClient,
        max_context_tokens: int = 3000,
    ):
        self.vector_store = vector_store
        self.embedding_gen = embedding_gen
        self.llm_client = llm_client
        self.max_context_tokens = max_context_tokens

        # Load static prompts (NOT part of RAG)
        self.system_prompt = self._load_prompt("prompts/system.txt")
        self.identity_prompt = self._load_prompt("prompts/identity.txt")
        self.meta_prompt = self._load_prompt("prompts/meta.txt")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def query(self, question: str, n_results: int = 5) -> QueryResponse:
        logger.info(f"Processing query: {question[:100]}...")

        try:
            intent = self._detect_intent(question)
            logger.debug(f"Detected intent: {intent.value}")

            # -------------------------------
            # Non-RAG paths
            # -------------------------------
            if intent in {
                QueryIntent.GREETING,
                QueryIntent.IDENTITY,
                QueryIntent.META,
            }:
                prompt = self._construct_direct_prompt(question, intent)
                answer = self.llm_client.generate_response(prompt)

                return QueryResponse(
                    answer=answer,
                    sources=[],
                    query=question,
                )

            # -------------------------------
            # RAG path (KNOWLEDGE)
            # -------------------------------
            query_embedding = self.embedding_gen.generate_embedding(question)
            retrieved_chunks = self.vector_store.query(query_embedding, n_results)

            if not retrieved_chunks:
                logger.warning("No relevant chunks found for query")
                prompt = self._construct_no_context_prompt(question)
                answer = self.llm_client.generate_response(prompt)

                return QueryResponse(
                    answer=answer,
                    sources=[],
                    query=question,
                )

            limited_chunks = self._limit_context_size(retrieved_chunks)
            prompt = self._construct_rag_prompt(question, limited_chunks)
            answer = self.llm_client.generate_response(prompt)

            return QueryResponse(
                answer=answer,
                sources=limited_chunks,
                query=question,
            )

        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            return QueryResponse(
                answer="I ran into an internal error while answering this question.",
                sources=[],
                query=question,
            )

    # ------------------------------------------------------------------
    # Intent detection
    # ------------------------------------------------------------------

    def _detect_intent(self, question: str) -> QueryIntent:
        q = question.lower().strip()

        if q in {"hi", "hello", "hey", "hey there"}:
            print("I was here")
            return QueryIntent.GREETING

        if "who are you" in q or "what are you" in q:
            return QueryIntent.IDENTITY

        if "how does vista work" in q or "how do you work" in q:
            return QueryIntent.META

        return QueryIntent.KNOWLEDGE

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    def _construct_direct_prompt(self, question: str, intent: QueryIntent) -> str:
        parts = [
            self.system_prompt,
            self.identity_prompt,
        ]

        if intent == QueryIntent.META:
            parts.append(self.meta_prompt)

        parts.append(f"User question:\n{question}\n\nAnswer:")

        return "\n\n".join(parts)

    def _construct_no_context_prompt(self, question: str) -> str:
        return f"""
{self.system_prompt}

{self.identity_prompt}

The user asked a question, but no relevant information was found.
Respond honestly and say that you do not have enough information.
Do not speculate or fabricate details.

Question:
{question}

Answer:
""".strip()

    def _construct_rag_prompt(
        self, question: str, context_chunks: List[RetrievedChunk]
    ) -> str:
        context_parts = []

        for i, chunk in enumerate(context_chunks, 1):
            source_info = ""
            if chunk.metadata:
                category = chunk.metadata.get("category", "unknown")
                filename = chunk.metadata.get("filename", "unknown")
                source_info = f" (Source: {category}/{filename})"

            context_parts.append(
                f"Context {i}{source_info}:\n{chunk.text}"
            )

        context_text = "\n\n".join(context_parts)

        return f"""
{self.system_prompt}

{self.identity_prompt}

Answer the question using ONLY the context below.
If the context is insufficient, say so clearly.

Question:
{question}

{context_text}

Answer:
""".strip()

    # ------------------------------------------------------------------
    # Context size control
    # ------------------------------------------------------------------

    def _limit_context_size(
        self, chunks: List[RetrievedChunk]
    ) -> List[RetrievedChunk]:
        if not chunks:
            return chunks

        available_tokens = self.max_context_tokens - 500
        available_chars = available_tokens * 4

        limited_chunks = []
        current_chars = 0

        for chunk in chunks:
            chunk_chars = len(chunk.text) + 100

            if current_chars + chunk_chars <= available_chars:
                limited_chunks.append(chunk)
                current_chars += chunk_chars
            else:
                break

        if not limited_chunks and chunks:
            first_chunk = chunks[0]
            max_chunk_chars = available_chars - 100

            truncated_text = (
                first_chunk.text[:max_chunk_chars] + "..."
                if len(first_chunk.text) > max_chunk_chars
                else first_chunk.text
            )

            limited_chunks = [
                RetrievedChunk(
                    text=truncated_text,
                    metadata=first_chunk.metadata,
                    similarity_score=first_chunk.similarity_score,
                )
            ]

        return limited_chunks

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _load_prompt(self, relative_path: str) -> str:
        base_dir = Path(__file__).resolve().parent.parent
        prompt_path = base_dir / relative_path

        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read().strip()