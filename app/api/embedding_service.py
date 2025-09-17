from openai import OpenAI
from typing import List, Optional
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        self.settings = get_settings()
        if self.settings.open_ai_key:
            self.client = OpenAI(api_key=self.settings.open_ai_key)
            self.model = "text-embedding-3-large"
            logger.info(f"Initialized EmbeddingService with model: {self.model}")
        else:
            self.client = None
            self.model = None
            logger.warning("EmbeddingService initialized without OpenAI API key")

    async def embed_text(self, text: str) -> List[float]:
        if not self.client:
            raise ValueError("OpenAI client not initialized. Please provide OPEN_AI_KEY in environment.")
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error creating embedding: {str(e)}")
            raise

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not self.client:
            raise ValueError("OpenAI client not initialized. Please provide OPEN_AI_KEY in environment.")
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts,
                encoding_format="float"
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"Error creating embeddings for batch: {str(e)}")
            raise

    def get_embedding_dimension(self) -> int:
        return 3072

embedding_service = EmbeddingService()