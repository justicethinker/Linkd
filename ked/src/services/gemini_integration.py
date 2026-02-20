"""Gemini API client integration for LLM tasks.

Provides centralized Gemini API access for:
- Persona synthesis
- Name extraction
- Identity resolution scoring
- Warm outreach generation
"""

import logging
import google.generativeai as genai
from ..config import settings

logger = logging.getLogger(__name__)

# Configure Gemini API
genai.configure(api_key=settings.gemini_api_key)


def get_gemini_client():
    """Get or create Gemini API client.
    
    Returns:
        Configured GenerativeModel client for Gemini API
    """
    try:
        # Return a default model for generation
        return genai.GenerativeModel("gemini-pro")
    except Exception as e:
        logger.error(f"Failed to get Gemini client: {e}")
        return None


async def generate_content(prompt: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
    """Generate content using Gemini API.
    
    Args:
        prompt: The prompt to send to Gemini
        max_tokens: Maximum tokens in the response
        temperature: Temperature for generation (0.0-1.0)
        
    Returns:
        Generated text response
    """
    try:
        client = get_gemini_client()
        if not client:
            raise RuntimeError("Gemini client not initialized")
        
        response = client.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )
        
        return response.text
    
    except Exception as e:
        logger.error(f"Gemini generation failed: {e}")
        raise


def embed_text(text: str, model: str = "embedding-001") -> list:
    """Generate embeddings for text using Gemini.
    
    Args:
        text: Text to embed
        model: Embedding model to use
        
    Returns:
        List of embeddings (768-dim, padded to 1536)
    """
    try:
        response = genai.embed_content(
            model=f"models/{model}",
            content=text,
        )
        
        embedding = response['embedding']
        
        # Pad to 1536 dimensions for consistency
        if len(embedding) < 1536:
            embedding = embedding + [0.0] * (1536 - len(embedding))
        else:
            embedding = embedding[:1536]
        
        return embedding
    
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise
