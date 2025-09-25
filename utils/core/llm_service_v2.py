"""
Enhanced LLM Service with Multi-Provider Support
Implements the specification from specs/001-llm-mapping-engine/spec.md
"""

import os
import json
import time
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
from abc import ABC, abstractmethod

import streamlit as st
import pandas as pd
import openai
import anthropic
from anthropic import Anthropic

# Logging and monitoring
try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"


@dataclass
class MappingSuggestion:
    """Represents a single mapping suggestion."""
    fhir_path: str
    source_expression: str
    confidence: float  # 0-100
    rationale: str
    transformation_type: str  # direct, transform, regex, etc.
    validation_status: str = "pending"
    provider: str = "unknown"


@dataclass
class MappingContext:
    """Context information for mapping generation."""
    field_name: str
    data_type: str
    sample_values: List[str]
    table_context: Dict[str, Any]
    fhir_resource_type: str
    implementation_guide: str
    ig_version: str


class LLMProviderInterface(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    async def generate_suggestions(self, context: MappingContext) -> List[MappingSuggestion]:
        """Generate mapping suggestions for given context."""
        pass

    @abstractmethod
    def estimate_cost(self, prompt_tokens: int) -> float:
        """Estimate cost for given token count."""
        pass


class OpenAIProvider(LLMProviderInterface):
    """OpenAI provider implementation."""

    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        self.cost_per_token = {
            "gpt-4": {"input": 0.03/1000, "output": 0.06/1000},
            "gpt-3.5-turbo": {"input": 0.001/1000, "output": 0.002/1000}
        }

    async def generate_suggestions(self, context: MappingContext) -> List[MappingSuggestion]:
        """Generate mapping suggestions using OpenAI."""
        try:
            prompt = self._build_mapping_prompt(context)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )

            suggestions_data = json.loads(response.choices[0].message.content)
            return self._parse_suggestions(suggestions_data, "openai")

        except Exception as e:
            logger.error(f"OpenAI error: {str(e)}")
            return []

    def estimate_cost(self, prompt_tokens: int) -> float:
        """Estimate cost for OpenAI API call."""
        rates = self.cost_per_token.get(self.model, self.cost_per_token["gpt-4"])
        return prompt_tokens * rates["input"] + 500 * rates["output"]  # Assume ~500 output tokens

    def _get_system_prompt(self) -> str:
        return """You are a FHIR mapping expert specializing in healthcare data transformation.
        Your task is to suggest optimal mappings from source data fields to FHIR resource elements.

        Consider:
        - FHIR cardinality constraints
        - Implementation Guide requirements
        - Data type compatibility
        - Healthcare industry standards

        Return suggestions as JSON with fields: fhir_path, source_expression, confidence, rationale, transformation_type."""

    def _build_mapping_prompt(self, context: MappingContext) -> str:
        return f"""
        Map this healthcare data field to FHIR:

        Field: {context.field_name}
        Data Type: {context.data_type}
        Sample Values: {context.sample_values[:5]}
        Target Resource: {context.fhir_resource_type}
        Implementation Guide: {context.implementation_guide} {context.ig_version}

        Provide top 3 mapping suggestions with confidence scores and transformation logic.
        """

    def _parse_suggestions(self, data: Dict, provider: str) -> List[MappingSuggestion]:
        """Parse API response into MappingSuggestion objects."""
        suggestions = []
        for item in data.get("suggestions", []):
            suggestions.append(MappingSuggestion(
                fhir_path=item.get("fhir_path", ""),
                source_expression=item.get("source_expression", ""),
                confidence=float(item.get("confidence", 0)),
                rationale=item.get("rationale", ""),
                transformation_type=item.get("transformation_type", "direct"),
                provider=provider
            ))
        return suggestions


class AnthropicProvider(LLMProviderInterface):
    """Anthropic Claude provider implementation."""

    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229"):
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.cost_per_token = {
            "claude-3-opus-20240229": {"input": 15/1000000, "output": 75/1000000},
            "claude-3-sonnet-20240229": {"input": 3/1000000, "output": 15/1000000},
            "claude-3-haiku-20240307": {"input": 0.25/1000000, "output": 1.25/1000000}
        }

    async def generate_suggestions(self, context: MappingContext) -> List[MappingSuggestion]:
        """Generate mapping suggestions using Anthropic."""
        try:
            prompt = self._build_mapping_prompt(context)

            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.1,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Parse Claude's response (typically in structured text)
            suggestions_data = self._parse_claude_response(response.content[0].text)
            return self._parse_suggestions(suggestions_data, "anthropic")

        except Exception as e:
            logger.error(f"Anthropic error: {str(e)}")
            return []

    def estimate_cost(self, prompt_tokens: int) -> float:
        """Estimate cost for Anthropic API call."""
        rates = self.cost_per_token.get(self.model, self.cost_per_token["claude-3-sonnet-20240229"])
        return prompt_tokens * rates["input"] + 500 * rates["output"]

    def _build_mapping_prompt(self, context: MappingContext) -> str:
        return f"""You are a healthcare data mapping expert. Help map this field to FHIR.

Field Information:
- Name: {context.field_name}
- Type: {context.data_type}
- Sample Values: {context.sample_values[:5]}
- Target FHIR Resource: {context.fhir_resource_type}
- Implementation Guide: {context.implementation_guide} {context.ig_version}

Please provide 3 mapping suggestions in JSON format:
{{
  "suggestions": [
    {{
      "fhir_path": "FHIR element path",
      "source_expression": "transformation expression",
      "confidence": 85,
      "rationale": "explanation",
      "transformation_type": "direct|transform|regex|concat|etc"
    }}
  ]
}}"""

    def _parse_claude_response(self, response_text: str) -> Dict:
        """Parse Claude's text response to extract JSON."""
        try:
            # Find JSON block in response
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start != -1 and end != -1:
                json_text = response_text[start:end]
                return json.loads(json_text)
        except:
            pass

        # Fallback - return empty structure
        return {"suggestions": []}

    def _parse_suggestions(self, data: Dict, provider: str) -> List[MappingSuggestion]:
        """Parse API response into MappingSuggestion objects."""
        suggestions = []
        for item in data.get("suggestions", []):
            suggestions.append(MappingSuggestion(
                fhir_path=item.get("fhir_path", ""),
                source_expression=item.get("source_expression", ""),
                confidence=float(item.get("confidence", 0)),
                rationale=item.get("rationale", ""),
                transformation_type=item.get("transformation_type", "direct"),
                provider=provider
            ))
        return suggestions


class LLMResponseCache:
    """Cache for LLM responses to reduce API costs."""

    def __init__(self, cache_size: int = 1000):
        self.cache = {}
        self.cache_size = cache_size
        self.access_times = {}

    def _generate_key(self, context: MappingContext) -> str:
        """Generate cache key from context."""
        key_data = {
            "field_name": context.field_name,
            "data_type": context.data_type,
            "fhir_resource_type": context.fhir_resource_type,
            "implementation_guide": context.implementation_guide,
            "sample_values_hash": hashlib.md5(str(context.sample_values).encode()).hexdigest()
        }
        return hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()

    def get(self, context: MappingContext) -> Optional[List[MappingSuggestion]]:
        """Get cached suggestions."""
        key = self._generate_key(context)
        if key in self.cache:
            self.access_times[key] = time.time()
            return self.cache[key]
        return None

    def set(self, context: MappingContext, suggestions: List[MappingSuggestion]):
        """Cache suggestions."""
        key = self._generate_key(context)

        # Evict oldest entries if cache is full
        if len(self.cache) >= self.cache_size:
            oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
            del self.cache[oldest_key]
            del self.access_times[oldest_key]

        self.cache[key] = suggestions
        self.access_times[key] = time.time()


class CostTracker:
    """Track LLM API costs."""

    def __init__(self):
        self.costs = {}
        self.calls = {}

    def record_cost(self, provider: str, cost: float):
        """Record API call cost."""
        if provider not in self.costs:
            self.costs[provider] = 0
            self.calls[provider] = 0

        self.costs[provider] += cost
        self.calls[provider] += 1

    def get_summary(self) -> Dict[str, Dict[str, float]]:
        """Get cost summary by provider."""
        return {
            provider: {
                "total_cost": self.costs.get(provider, 0),
                "total_calls": self.calls.get(provider, 0),
                "avg_cost": self.costs.get(provider, 0) / max(1, self.calls.get(provider, 0))
            }
            for provider in set(list(self.costs.keys()) + list(self.calls.keys()))
        }


class PatternLibrary:
    """Library of learned mapping patterns."""

    def __init__(self):
        self.patterns = {}
        self.user_preferences = {}

    def add_pattern(self, field_pattern: str, successful_mapping: MappingSuggestion):
        """Add a successful mapping pattern."""
        if field_pattern not in self.patterns:
            self.patterns[field_pattern] = []

        self.patterns[field_pattern].append({
            "mapping": asdict(successful_mapping),
            "success_count": 1,
            "timestamp": time.time()
        })

    def get_similar_patterns(self, field_name: str, limit: int = 5) -> List[MappingSuggestion]:
        """Find similar successful patterns."""
        # Simple similarity matching - can be enhanced with ML
        matches = []
        field_lower = field_name.lower()

        for pattern, pattern_data in self.patterns.items():
            if any(word in pattern.lower() for word in field_lower.split('_')):
                for entry in pattern_data[:limit]:
                    suggestion = MappingSuggestion(**entry["mapping"])
                    suggestion.confidence *= 0.8  # Reduce confidence for pattern matches
                    matches.append(suggestion)

        return sorted(matches, key=lambda x: x.confidence, reverse=True)[:limit]


class EnhancedLLMService:
    """Main LLM service implementing the specification."""

    def __init__(self):
        self.providers = {}
        self.cache = LLMResponseCache()
        self.cost_tracker = CostTracker()
        self.pattern_library = PatternLibrary()
        self.initialize_providers()

    def initialize_providers(self):
        """Initialize available LLM providers."""
        # OpenAI
        openai_key = os.environ.get('OPENAI_API_KEY') or st.secrets.get("OPENAI_API_KEY")
        if openai_key:
            self.providers[LLMProvider.OPENAI] = OpenAIProvider(openai_key)

        # Anthropic
        anthropic_key = os.environ.get('ANTHROPIC_API_KEY') or st.secrets.get("ANTHROPIC_API_KEY")
        if anthropic_key:
            self.providers[LLMProvider.ANTHROPIC] = AnthropicProvider(anthropic_key)

        logger.info(f"Initialized {len(self.providers)} LLM providers")

    async def generate_mapping_suggestions(
        self,
        context: MappingContext,
        provider_preference: Optional[LLMProvider] = None,
        confidence_threshold: float = 0.7
    ) -> List[MappingSuggestion]:
        """Generate mapping suggestions with fallback and ranking."""

        # Check cache first
        cached_suggestions = self.cache.get(context)
        if cached_suggestions:
            logger.info(f"Using cached suggestions for {context.field_name}")
            return cached_suggestions

        # Get pattern-based suggestions
        pattern_suggestions = self.pattern_library.get_similar_patterns(context.field_name)

        # Try LLM providers
        llm_suggestions = []
        providers_to_try = [provider_preference] if provider_preference else list(self.providers.keys())

        for provider_type in providers_to_try:
            if provider_type in self.providers:
                try:
                    suggestions = await self.providers[provider_type].generate_suggestions(context)
                    llm_suggestions.extend(suggestions)

                    # Record cost
                    cost = self.providers[provider_type].estimate_cost(500)  # Estimated tokens
                    self.cost_tracker.record_cost(provider_type.value, cost)

                    logger.info(f"Got {len(suggestions)} suggestions from {provider_type.value}")
                    break  # Use first successful provider

                except Exception as e:
                    logger.error(f"Provider {provider_type.value} failed: {str(e)}")
                    continue

        # Combine and rank suggestions
        all_suggestions = llm_suggestions + pattern_suggestions
        ranked_suggestions = self._rank_suggestions(all_suggestions, context)

        # Filter by confidence threshold
        filtered_suggestions = [s for s in ranked_suggestions if s.confidence >= confidence_threshold]

        # Cache results
        self.cache.set(context, filtered_suggestions)

        return filtered_suggestions

    def _rank_suggestions(self, suggestions: List[MappingSuggestion], context: MappingContext) -> List[MappingSuggestion]:
        """Rank suggestions by confidence and other factors."""

        def scoring_function(suggestion: MappingSuggestion) -> float:
            score = suggestion.confidence

            # Boost pattern matches
            if suggestion.provider in ["pattern", "historical"]:
                score *= 1.1

            # Boost direct mappings for simple fields
            if suggestion.transformation_type == "direct" and "_id" in context.field_name.lower():
                score *= 1.05

            return score

        return sorted(suggestions, key=scoring_function, reverse=True)

    def learn_from_feedback(self, context: MappingContext, suggestion: MappingSuggestion, accepted: bool):
        """Learn from user feedback to improve future suggestions."""
        if accepted:
            # Add to pattern library
            pattern_key = self._generate_pattern_key(context)
            self.pattern_library.add_pattern(pattern_key, suggestion)

            logger.info(f"Learned positive pattern for {context.field_name}")
        else:
            # Could implement negative feedback handling
            logger.info(f"Received negative feedback for {context.field_name}")

    def _generate_pattern_key(self, context: MappingContext) -> str:
        """Generate pattern key for learning."""
        return f"{context.fhir_resource_type}_{context.field_name.lower()}"

    def get_cost_summary(self) -> Dict:
        """Get API cost summary."""
        return self.cost_tracker.get_summary()

    def get_available_providers(self) -> List[str]:
        """Get list of available providers."""
        return [provider.value for provider in self.providers.keys()]


# Global instance
enhanced_llm_service = EnhancedLLMService()