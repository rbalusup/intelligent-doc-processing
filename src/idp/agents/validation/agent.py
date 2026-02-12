"""Validation agent implementation."""

from idp.agents.base import BaseAgent
from idp.agents.validation.models import (
    ValidationInput,
    ValidationOutput,
)
from idp.agents.validation.rules import ValidationRuleRegistry
from idp.core.config import Settings
from idp.core.retry import RetryConfig
from idp.llm.client import BaseLLMClient


class ValidationAgent(BaseAgent[ValidationInput, ValidationOutput]):
    """Agent for validating extracted document data."""

    def __init__(
        self,
        llm_client: BaseLLMClient | None = None,
        settings: Settings | None = None,
        retry_config: RetryConfig | None = None,
        rule_registry: ValidationRuleRegistry | None = None,
    ) -> None:
        """Initialize the validation agent.

        Note: llm_client is optional for validation since most rules
        are deterministic. It can be used for future LLM-based validation.
        """
        # Create a dummy client if none provided
        if llm_client is None:
            from idp.llm.mock.client import MockLLMClient
            llm_client = MockLLMClient()

        super().__init__(llm_client, settings, retry_config)
        self._registry = rule_registry or ValidationRuleRegistry()

    @property
    def name(self) -> str:
        """Get the agent name."""
        return "ValidationAgent"

    async def _execute(self, input_data: ValidationInput) -> ValidationOutput:
        """Execute the validation."""
        document_type = input_data.document_type
        extraction = input_data.extraction

        self._logger.debug(
            "Validating extraction",
            document_id=input_data.document.id,
            document_type=document_type.value,
        )

        # Get applicable rules
        rules = self._registry.get_rules(document_type)
        output = ValidationOutput(
            valid=True,
            rules_checked=len(rules),
            rules_passed=0,
        )

        # Run each rule
        for rule in rules:
            try:
                issues = rule.validate(extraction)
                if issues:
                    for issue in issues:
                        output.add_issue(issue)
                else:
                    output.rules_passed += 1
            except Exception as e:
                self._logger.warning(
                    "Rule validation failed",
                    rule=rule.name,
                    error=str(e),
                )
                # Don't count failed rules as issues

        # Determine overall validity
        if input_data.strict_mode:
            # In strict mode, warnings are also failures
            output.valid = output.error_count == 0 and output.warning_count == 0
        else:
            # Normal mode: only errors cause failure
            output.valid = output.error_count == 0

        self._logger.info(
            "Validation completed",
            valid=output.valid,
            errors=output.error_count,
            warnings=output.warning_count,
            rules_checked=output.rules_checked,
        )

        return output
