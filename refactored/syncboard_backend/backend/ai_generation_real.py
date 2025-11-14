"""
Real AI generation with RAG (Retrieval Augmented Generation).
Uses OpenAI to generate content based on user's knowledge bank.
"""

import os
import logging
from typing import Dict, List, Optional
import openai

logger = logging.getLogger(__name__)

# Available models
MODELS = {
    "gpt-4o-mini": "gpt-4o-mini",
    "gpt-4o": "gpt-4o",
    "gpt-4": "gpt-4-turbo-preview",
}

# Initialize OpenAI client
openai.api_key = os.getenv("OPENAI_API_KEY")


async def generate_with_rag(
    prompt: str,
    model: str,
    vector_store,
    allowed_doc_ids: List[int],
    documents: Dict[int, str],
    top_k: int = 5
) -> str:
    """
    Generate AI content using Retrieval Augmented Generation.

    Args:
        prompt: User's prompt/question
        model: OpenAI model to use
        vector_store: Vector store for semantic search
        allowed_doc_ids: Document IDs the user has access to
        documents: All documents dict
        top_k: Number of relevant documents to retrieve

    Returns:
        Generated text response
    """
    # Get relevant documents using semantic search
    search_results = vector_store.search(prompt, top_k=top_k, allowed_doc_ids=allowed_doc_ids)

    # Filter to only user's documents
    relevant_docs = []
    for doc_id, score, snippet in search_results:  # FIX: Unpack all 3 values
        if doc_id in allowed_doc_ids and doc_id in documents:
            relevant_docs.append({
                "content": documents[doc_id],
                "relevance": score
            })

    # Build context from relevant documents
    context = "\n\n---\n\n".join([
        f"[Document {i+1} - Relevance: {doc['relevance']:.2f}]\n{doc['content']}"
        for i, doc in enumerate(relevant_docs[:top_k])
    ])

    # Construct system message
    system_message = """You are an AI assistant helping users with their knowledge bank.
You have access to the user's documents and can use them to provide informed, accurate responses.
Always cite which documents you're referencing when possible."""

    # Construct user message with context
    if context:
        user_message = f"""Based on the following documents from my knowledge bank:

{context}

---

Please answer this question: {prompt}"""
    else:
        user_message = f"""I don't have any relevant documents in my knowledge bank for this question, but please try to help anyway:

{prompt}"""

    # Call OpenAI API
    try:
        response = openai.chat.completions.create(
            model=MODELS.get(model, "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=1000
        )

        generated_text = response.choices[0].message.content
        logger.info(f"Generated response using {len(relevant_docs)} relevant documents")
        return generated_text

    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        raise Exception(f"Failed to generate response: {str(e)}")
