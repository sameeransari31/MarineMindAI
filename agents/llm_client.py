"""
LLM Client — wraps HuggingFace Inference API (OpenAI-compatible endpoint).
Used by all agents for text generation.
"""
import os
import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def call_llm(messages: list[dict], temperature: float = 0.3, max_tokens: int = 1024) -> str:
    """
    Call the HuggingFace-hosted LLM via OpenAI-compatible chat completions endpoint.
    
    Args:
        messages: List of {"role": ..., "content": ...} dicts.
        temperature: Sampling temperature.
        max_tokens: Max tokens in response.
    
    Returns:
        The assistant's reply as a string.
    """
    api_url = settings.HUGGINGFACE_API_URL
    api_token = settings.HUGGINGFACE_API_TOKEN
    model = settings.HUGGINGFACE_MODEL

    if not api_url or not api_token:
        raise ValueError("HUGGINGFACE_API_URL and HUGGINGFACE_API_TOKEN must be set in .env")

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.exceptions.Timeout:
        logger.error("LLM API call timed out")
        return "I'm sorry, the request timed out. Please try again."
    except requests.exceptions.HTTPError as e:
        logger.error(f"LLM API HTTP error: {e.response.status_code} - {e.response.text}")
        return "I'm sorry, there was an error processing your request. Please try again later."
    except Exception as e:
        logger.error(f"LLM API unexpected error: {e}")
        return "An unexpected error occurred. Please try again."
