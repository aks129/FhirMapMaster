"""
Test suite for Enhanced LLM Service
Tests multi-provider LLM integration and mapping suggestions
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd

from utils.core.llm_service_v2 import (
    EnhancedLLMService,
    OpenAIProvider,
    AnthropicProvider,
    MappingContext,
    MappingSuggestion,
    LLMProvider,
    LLMResponseCache,
    CostTracker,
    PatternLibrary
)


class TestMappingContext:
    """Test MappingContext data structure."""

    def test_mapping_context_creation(self):
        context = MappingContext(
            field_name="patient_id",
            data_type="string",
            sample_values=["PAT123", "PAT456"],
            table_context={},
            fhir_resource_type="Patient",
            implementation_guide="US Core",
            ig_version="7.0.0"
        )

        assert context.field_name == "patient_id"
        assert context.fhir_resource_type == "Patient"
        assert len(context.sample_values) == 2


class TestMappingSuggestion:
    """Test MappingSuggestion data structure."""

    def test_suggestion_creation(self):
        suggestion = MappingSuggestion(
            fhir_path="Patient.id",
            source_expression="{{ patient_id }}",
            confidence=85.0,
            rationale="Direct ID mapping",
            transformation_type="direct",
            provider="openai"
        )

        assert suggestion.fhir_path == "Patient.id"
        assert suggestion.confidence == 85.0
        assert suggestion.transformation_type == "direct"


class TestLLMResponseCache:
    """Test LLM response caching functionality."""

    def test_cache_operations(self):
        cache = LLMResponseCache(cache_size=10)

        context = MappingContext(
            field_name="test_field",
            data_type="string",
            sample_values=["test"],
            table_context={},
            fhir_resource_type="Patient",
            implementation_guide="US Core",
            ig_version="7.0.0"
        )

        suggestion = MappingSuggestion(
            fhir_path="Patient.test",
            source_expression="{{ test_field }}",
            confidence=80.0,
            rationale="Test mapping",
            transformation_type="direct"
        )

        # Test cache miss
        assert cache.get(context) is None

        # Test cache set and hit
        cache.set(context, [suggestion])
        cached_result = cache.get(context)

        assert cached_result is not None
        assert len(cached_result) == 1
        assert cached_result[0].fhir_path == "Patient.test"

    def test_cache_eviction(self):
        cache = LLMResponseCache(cache_size=2)

        contexts = []
        for i in range(3):
            context = MappingContext(
                field_name=f"field_{i}",
                data_type="string",
                sample_values=[f"value_{i}"],
                table_context={},
                fhir_resource_type="Patient",
                implementation_guide="US Core",
                ig_version="7.0.0"
            )
            contexts.append(context)

            suggestion = MappingSuggestion(
                fhir_path=f"Patient.field_{i}",
                source_expression=f"{{{{ field_{i} }}}}",
                confidence=80.0,
                rationale="Test",
                transformation_type="direct"
            )
            cache.set(context, [suggestion])

        # First context should be evicted
        assert cache.get(contexts[0]) is None
        assert cache.get(contexts[1]) is not None
        assert cache.get(contexts[2]) is not None


class TestCostTracker:
    """Test cost tracking functionality."""

    def test_cost_recording(self):
        tracker = CostTracker()

        tracker.record_cost("openai", 0.05)
        tracker.record_cost("openai", 0.03)
        tracker.record_cost("anthropic", 0.02)

        summary = tracker.get_summary()

        assert summary["openai"]["total_cost"] == 0.08
        assert summary["openai"]["total_calls"] == 2
        assert summary["openai"]["avg_cost"] == 0.04

        assert summary["anthropic"]["total_cost"] == 0.02
        assert summary["anthropic"]["total_calls"] == 1


class TestPatternLibrary:
    """Test pattern library functionality."""

    def test_pattern_storage_and_retrieval(self):
        library = PatternLibrary()

        suggestion = MappingSuggestion(
            fhir_path="Patient.name[0].given[0]",
            source_expression="{{ first_name }}",
            confidence=90.0,
            rationale="First name mapping",
            transformation_type="direct"
        )

        library.add_pattern("first_name", suggestion)

        # Test pattern retrieval
        similar_patterns = library.get_similar_patterns("fname", limit=5)

        assert len(similar_patterns) == 1
        assert similar_patterns[0].fhir_path == "Patient.name[0].given[0]"
        # Confidence should be reduced for pattern matches
        assert similar_patterns[0].confidence < 90.0


class TestOpenAIProvider:
    """Test OpenAI provider implementation."""

    @pytest.fixture
    def mock_openai_response(self):
        return {
            "choices": [{
                "message": {
                    "content": '{"suggestions": [{"fhir_path": "Patient.id", "source_expression": "{{ patient_id }}", "confidence": 85, "rationale": "Direct ID mapping", "transformation_type": "direct"}]}'
                }
            }]
        }

    @patch('openai.OpenAI')
    def test_provider_initialization(self, mock_openai):
        provider = OpenAIProvider("test-api-key", "gpt-4")
        assert provider.model == "gpt-4"
        mock_openai.assert_called_once_with(api_key="test-api-key")

    @patch('openai.OpenAI')
    async def test_generate_suggestions(self, mock_openai):
        mock_client = Mock()
        mock_openai.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"suggestions": [{"fhir_path": "Patient.id", "source_expression": "{{ patient_id }}", "confidence": 85, "rationale": "Direct ID mapping", "transformation_type": "direct"}]}'

        mock_client.chat.completions.create.return_value = mock_response

        provider = OpenAIProvider("test-key")
        context = MappingContext(
            field_name="patient_id",
            data_type="string",
            sample_values=["PAT123"],
            table_context={},
            fhir_resource_type="Patient",
            implementation_guide="US Core",
            ig_version="7.0.0"
        )

        suggestions = await provider.generate_suggestions(context)

        assert len(suggestions) == 1
        assert suggestions[0].fhir_path == "Patient.id"
        assert suggestions[0].confidence == 85.0

    def test_cost_estimation(self):
        provider = OpenAIProvider("test-key", "gpt-4")
        cost = provider.estimate_cost(1000)

        # Should return a reasonable cost estimate
        assert cost > 0
        assert cost < 1.0  # Should be less than $1 for 1000 tokens


class TestAnthropicProvider:
    """Test Anthropic provider implementation."""

    @patch('anthropic.Anthropic')
    def test_provider_initialization(self, mock_anthropic):
        provider = AnthropicProvider("test-api-key")
        mock_anthropic.assert_called_once_with(api_key="test-api-key")

    @patch('anthropic.Anthropic')
    async def test_generate_suggestions(self, mock_anthropic):
        mock_client = Mock()
        mock_anthropic.return_value = mock_client

        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = '{"suggestions": [{"fhir_path": "Patient.id", "source_expression": "{{ patient_id }}", "confidence": 90, "rationale": "ID field mapping", "transformation_type": "direct"}]}'

        mock_client.messages.create.return_value = mock_response

        provider = AnthropicProvider("test-key")
        context = MappingContext(
            field_name="patient_id",
            data_type="string",
            sample_values=["PAT123"],
            table_context={},
            fhir_resource_type="Patient",
            implementation_guide="US Core",
            ig_version="7.0.0"
        )

        suggestions = await provider.generate_suggestions(context)

        assert len(suggestions) == 1
        assert suggestions[0].fhir_path == "Patient.id"
        assert suggestions[0].confidence == 90.0


class TestEnhancedLLMService:
    """Test the main Enhanced LLM Service."""

    @pytest.fixture
    def service(self):
        return EnhancedLLMService()

    @pytest.fixture
    def sample_context(self):
        return MappingContext(
            field_name="patient_id",
            data_type="string",
            sample_values=["PAT123", "PAT456"],
            table_context={},
            fhir_resource_type="Patient",
            implementation_guide="US Core",
            ig_version="7.0.0"
        )

    def test_service_initialization(self, service):
        assert isinstance(service.cache, LLMResponseCache)
        assert isinstance(service.cost_tracker, CostTracker)
        assert isinstance(service.pattern_library, PatternLibrary)

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
    def test_provider_initialization_with_env_vars(self):
        service = EnhancedLLMService()
        providers = service.get_available_providers()
        assert 'openai' in providers

    async def test_generate_mapping_suggestions_with_cache(self, service, sample_context):
        # Mock suggestion
        suggestion = MappingSuggestion(
            fhir_path="Patient.id",
            source_expression="{{ patient_id }}",
            confidence=85.0,
            rationale="Cached suggestion",
            transformation_type="direct"
        )

        # Add to cache
        service.cache.set(sample_context, [suggestion])

        # Should return cached result
        suggestions = await service.generate_mapping_suggestions(sample_context)
        assert len(suggestions) == 1
        assert suggestions[0].rationale == "Cached suggestion"

    def test_learning_from_feedback(self, service, sample_context):
        suggestion = MappingSuggestion(
            fhir_path="Patient.id",
            source_expression="{{ patient_id }}",
            confidence=85.0,
            rationale="Test suggestion",
            transformation_type="direct"
        )

        # Test positive feedback
        service.learn_from_feedback(sample_context, suggestion, accepted=True)

        # Should add to pattern library
        patterns = service.pattern_library.get_similar_patterns("patient_id")
        assert len(patterns) > 0

    def test_suggestion_ranking(self, service, sample_context):
        suggestions = [
            MappingSuggestion(
                fhir_path="Patient.id",
                source_expression="{{ patient_id }}",
                confidence=60.0,
                rationale="Low confidence",
                transformation_type="direct",
                provider="openai"
            ),
            MappingSuggestion(
                fhir_path="Patient.identifier[0].value",
                source_expression="{{ patient_id }}",
                confidence=90.0,
                rationale="High confidence",
                transformation_type="direct",
                provider="anthropic"
            )
        ]

        ranked = service._rank_suggestions(suggestions, sample_context)

        # Higher confidence should be first
        assert ranked[0].confidence == 90.0
        assert ranked[1].confidence == 60.0


class TestIntegration:
    """Integration tests for the LLM service."""

    @pytest.fixture
    def sample_dataframe(self):
        return pd.DataFrame({
            'patient_id': ['PAT001', 'PAT002'],
            'first_name': ['John', 'Jane'],
            'last_name': ['Doe', 'Smith'],
            'birth_date': ['1980-01-15', '1975-03-22'],
            'gender': ['M', 'F']
        })

    async def test_full_mapping_workflow(self, sample_dataframe):
        """Test complete mapping workflow."""
        service = EnhancedLLMService()

        # Mock providers since we don't have real API keys in tests
        mock_suggestion = MappingSuggestion(
            fhir_path="Patient.id",
            source_expression="{{ patient_id }}",
            confidence=85.0,
            rationale="Direct ID mapping",
            transformation_type="direct",
            provider="mock"
        )

        # Mock the suggestion generation
        with patch.object(service, 'generate_mapping_suggestions', return_value=[mock_suggestion]):

            for column in sample_dataframe.columns:
                context = MappingContext(
                    field_name=column,
                    data_type=str(sample_dataframe[column].dtype),
                    sample_values=sample_dataframe[column].head(3).tolist(),
                    table_context={},
                    fhir_resource_type="Patient",
                    implementation_guide="US Core",
                    ig_version="7.0.0"
                )

                suggestions = await service.generate_mapping_suggestions(context)
                assert len(suggestions) > 0

                # Test feedback learning
                service.learn_from_feedback(context, suggestions[0], accepted=True)

        # Verify cost tracking worked
        cost_summary = service.get_cost_summary()
        assert isinstance(cost_summary, dict)


# Pytest configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    pytest.main([__file__])