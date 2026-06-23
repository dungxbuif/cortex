from dataclasses import dataclass

@dataclass
class OrchestratorConfig:
    max_turns: int = 5
    llm_timeout_seconds: float = 30.0
    tool_timeout_seconds: float = 10.0
