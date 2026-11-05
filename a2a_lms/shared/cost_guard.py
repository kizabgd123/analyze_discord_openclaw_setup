"""Autonomous Agent Cost Guard, Step Budget, and ReAct Tracing Module.
Enforces limits, tracks estimated token usage and costs, and records execution traces.
Following principles from the autonomous-agents skill.
"""

import time
import logging
from typing import List, Optional, Dict, Any
from a2a_lms.shared.schemas import AgentTraceStep, ExecutionMetrics

logger = logging.getLogger("a2a_lms.cost_guard")


class StepLimitExceededError(RuntimeError):
    """Raised when autonomous agent loop exceeds configured maximum steps."""
    pass


class CostLimitExceededError(RuntimeError):
    """Raised when estimated token/API spend exceeds safety budget."""
    pass


class AgentExecutionTimeoutError(TimeoutError):
    """Raised when a single step exceeds its configured execution timeout."""
    pass


class CostAndStepGuard:
    """Manages token cost estimation, step counts, timeouts, and ReAct traces."""

    # Approximate Gemini/LLM token cost per 1k tokens ($0.00015 input, $0.00060 output)
    COST_PER_1K_INPUT_USD = 0.00015
    COST_PER_1K_OUTPUT_USD = 0.00060

    def __init__(
        self,
        max_steps: int = 15,
        max_cost_usd: float = 0.50,
        default_step_timeout_sec: float = 120.0,
    ):
        self.max_steps = max_steps
        self.max_cost_usd = max_cost_usd
        self.default_step_timeout_sec = default_step_timeout_sec

        self.current_step = 0
        self.total_estimated_tokens = 0
        self.total_cost_usd = 0.0
        self.start_time = time.time()
        self.traces: List[AgentTraceStep] = []
        self.resumed_from_checkpoint = False
        self.checkpoint_id: Optional[str] = None

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate (~4 chars per token)."""
        if not text:
            return 0
        return max(1, len(text) // 4)

    def before_step(self, agent_name: str, planned_action: str):
        """Pre-step verification: checks step limit and budget before execution."""
        self.current_step += 1
        if self.current_step > self.max_steps:
            raise StepLimitExceededError(
                f"Agent exceeded maximum step limit ({self.max_steps}). "
                f"Halted to prevent infinite loop."
            )

        if self.total_cost_usd >= self.max_cost_usd:
            raise CostLimitExceededError(
                f"Agent exceeded maximum budget (${self.max_cost_usd:.4f}). "
                f"Current spend: ${self.total_cost_usd:.4f}."
            )

        logger.debug(
            f"[CostGuard] Step {self.current_step}/{self.max_steps} | "
            f"Agent: {agent_name} | Action: {planned_action} | "
            f"Current Cost: ${self.total_cost_usd:.4f}"
        )

    def record_step(
        self,
        agent_name: str,
        thought: str,
        action: str,
        observation: str,
        reflection: Optional[str] = None,
        input_text: str = "",
        output_text: str = "",
    ) -> AgentTraceStep:
        """Records a completed ReAct trace step and tallies token/cost usage."""
        in_tokens = self.estimate_tokens(input_text or thought)
        out_tokens = self.estimate_tokens(output_text or observation)
        step_tokens = in_tokens + out_tokens
        self.total_estimated_tokens += step_tokens

        step_cost = (
            (in_tokens / 1000.0) * self.COST_PER_1K_INPUT_USD
            + (out_tokens / 1000.0) * self.COST_PER_1K_OUTPUT_USD
        )
        self.total_cost_usd += step_cost

        trace_step = AgentTraceStep(
            step_number=self.current_step,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            agent_name=agent_name,
            thought=thought,
            action=action,
            observation=observation,
            reflection=reflection,
            tokens_used=step_tokens,
        )
        self.traces.append(trace_step)

        logger.info(
            f"[Trace Step {self.current_step}] {agent_name} -> {action} "
            f"({step_tokens} tokens, ${step_cost:.5f})"
        )
        return trace_step

    def get_metrics(self, grounding_confidence: float = 1.0) -> ExecutionMetrics:
        """Computes summary metrics for the agent execution session."""
        duration = round(time.time() - self.start_time, 2)
        return ExecutionMetrics(
            total_steps=self.current_step,
            total_estimated_tokens=self.total_estimated_tokens,
            estimated_cost_usd=round(self.total_cost_usd, 5),
            execution_time_seconds=duration,
            resumed_from_checkpoint=self.resumed_from_checkpoint,
            checkpoint_id=self.checkpoint_id,
            grounding_confidence=grounding_confidence,
        )
