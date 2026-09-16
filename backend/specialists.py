"""Twelve separately compiled specialist subgraphs with bounded execution and telemetry."""

import asyncio
import time
from dataclasses import dataclass
from typing import Callable

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from backend.agent_models import inspect_evidence
from backend.db import Session
from backend.models import AgentRun
from backend.tools import PERMISSIONS, active_agent


@dataclass(frozen=True)
class Specialist:
    name: str
    objective: str
    handler: Callable
    required_output: str
    timeout_seconds: int = 90

    def compile(self, schema):
        async def execute(state):
            started = time.perf_counter()
            token = active_agent.set(self.name)
            status = "failed"
            inspection = {}
            try:
                inspection = await asyncio.wait_for(
                    inspect_evidence(self.name, self.objective, state), timeout=60
                )
                result = await asyncio.wait_for(self.handler(state), timeout=self.timeout_seconds)
                if self.required_output not in result:
                    raise ValueError(f"{self.name} omitted its required output")
                status = "completed"
                return result
            finally:
                active_agent.reset(token)
                with Session.begin() as db:
                    db.add(
                        AgentRun(
                            execution_id=state["thread_id"],
                            agent=self.name,
                            status=status,
                            duration_ms=(time.perf_counter() - started) * 1000,
                            detail={
                                "objective": self.objective,
                                "inspection": inspection,
                                "allowed_tools": sorted(PERMISSIONS[self.name]),
                            },
                        )
                    )

        graph = StateGraph(schema)
        # Retry transient reads only. Financial retries are explicit, idempotent workflow resumes.
        retry = (
            RetryPolicy(max_attempts=2, retry_on=(ConnectionError, TimeoutError))
            if self.name not in {"order", "refund", "procurement"}
            else None
        )
        graph.add_node("execute", execute, retry_policy=retry)
        graph.add_edge(START, "execute")
        graph.add_edge("execute", END)
        return graph.compile()
