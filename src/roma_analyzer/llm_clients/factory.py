# -*- coding: utf-8 -*-
"""
ROMA-01 Trading Analyzer - LLM Client Factory

Provides unified interface for multiple LLM providers.
"""

from typing import Dict, Any
from loguru import logger


class LLMClientFactory:
    """Factory for creating LLM clients."""
    
    def create_client(self, config: Dict[str, Any]):
        """
        Create LLM client based on provider.
        
        Args:
            config: LLM configuration with provider, api_key, model
            
        Returns:
            DSPy LM instance
        """
        provider = config.get("provider", "").lower()
        api_key = config.get("api_key", "")
        model = config.get("model", "")
        temperature = config.get("temperature", 0.15)
        max_tokens = config.get("max_tokens", 4000)
        
        if not api_key:
            logger.warning(f"No API key provided for {provider}")
        
        if provider == "deepseek":
            return self._create_deepseek_client(model, api_key, temperature, max_tokens)
        elif provider == "qwen":
            return self._create_qwen_client(model, api_key, temperature, max_tokens)
        elif provider == "anthropic":
            return self._create_anthropic_client(model, api_key, temperature, max_tokens)
        elif provider == "openai":
            return self._create_openai_client(model, api_key, temperature, max_tokens)
        elif provider == "xai":
            return self._create_xai_client(model, api_key, temperature, max_tokens)
        elif provider == "google":
            return self._create_google_client(model, api_key, temperature, max_tokens)
        else:
            logger.warning(f"Unknown provider: {provider}, using custom OpenAI client")
            return self._create_custom_client(model, api_key, temperature, max_tokens)
    
    def _create_deepseek_client(self, model: str, api_key: str, temperature: float, max_tokens: int):
        """Create DeepSeek client."""
        import dspy
        lm = dspy.LM(
            model=model or "deepseek-chat",
            api_key=api_key,
            api_base="https://api.deepseek.com",
            temperature=temperature,
            max_tokens=max_tokens,
        )
        logger.info(f"Created DeepSeek client: {model}")
        return lm
    
    def _create_qwen_client(self, model: str, api_key: str, temperature: float, max_tokens: int):
        """Create Qwen client."""
        import dspy
        location = "china" if model else "international"
        api_base = (
            "https://dashscope.aliyuncs.com/compatible-mode/v1"
            if location == "china"
            else "https://api.together.xyz/v1"
        )
        lm = dspy.LM(
            model=model or "qwen-max",
            api_key=api_key,
            api_base=api_base,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        logger.info(f"Created Qwen client: {model}")
        return lm
    
    def _create_anthropic_client(self, model: str, api_key: str, temperature: float, max_tokens: int):
        """Create Anthropic (Claude) client."""
        import dspy
        lm = dspy.LM(
            model=model or "claude-sonnet-4-5-20250929",
            api_key=api_key,
            api_base="https://api.anthropic.com",
            temperature=temperature,
            max_tokens=max_tokens,
        )
        logger.info(f"Created Anthropic client: {model}")
        return lm
    
    def _create_openai_client(self, model: str, api_key: str, temperature: float, max_tokens: int):
        """Create OpenAI (GPT) client."""
        import dspy
        lm = dspy.LM(
            model=model or "gpt-4o",
            api_key=api_key,
            api_base="https://api.openai.com/v1",
            temperature=temperature,
            max_tokens=max_tokens,
        )
        logger.info(f"Created OpenAI client: {model}")
        return lm
    
    def _create_xai_client(self, model: str, api_key: str, temperature: float, max_tokens: int):
        """Create xAI (Grok) client."""
        import dspy
        lm = dspy.LM(
            model=model or "grok-2-latest",
            api_key=api_key,
            api_base="https://api.x.ai/v1",
            temperature=temperature,
            max_tokens=max_tokens,
        )
        logger.info(f"Created xAI client: {model}")
        return lm
    
    def _create_google_client(self, model: str, api_key: str, temperature: float, max_tokens: int):
        """Create Google (Gemini) client."""
        import dspy
        lm = dspy.LM(
            model=model or "gemini-2.0-flash-exp",
            api_key=api_key,
            api_base="https://generativelanguage.googleapis.com/v1beta/openai",
            temperature=temperature,
            max_tokens=max_tokens,
        )
        logger.info(f"Created Google client: {model}")
        return lm
    
    def _create_custom_client(self, model: str, api_key: str, temperature: float, max_tokens: int):
        """Create custom OpenAI-compatible client."""
        import dspy
        lm = dspy.LM(
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        logger.info(f"Created custom client: {model}")
        return lm
