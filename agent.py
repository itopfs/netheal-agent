import json
import os
from pathlib import Path
from typing import AsyncGenerator

from anthropic import AsyncAnthropic
from dotenv import load_dotenv

from llm import build_system_prompt
from simulator.simulator import NetworkSimulator
from tool_registry import ToolRegistry

load_dotenv()

BASE = Path(__file__).parent
TOOLS_DIR = BASE / "tools"
DEFAULT_MODEL = "claude-opus-5"
MAX_ITERATIONS = 25


def _resolve_model() -> str:
    # Treat blank / whitespace env values as unset (common Vercel misconfig).
    return (os.getenv("AGENT_MODEL") or "").strip() or DEFAULT_MODEL


def _resolve_api_key() -> str:
    return (os.getenv("ANTHROPIC_API_KEY") or "").strip()


class AgentLoop:
    def __init__(self, scenario_path: Path):
        self.simulator = NetworkSimulator()
        self.simulator.load(scenario_path / "network.json")

        self.registry = ToolRegistry()
        self.registry.load_tools(TOOLS_DIR)

        self.system_prompt = build_system_prompt()
        api_key = _resolve_api_key()
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. "
                "Add it in Vercel → Project → Settings → Environment Variables, then redeploy."
            )
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = _resolve_model()
        self._history: list[dict] = []

    async def run(self, incident: dict) -> AsyncGenerator[dict, None]:
        tools = self.registry.get_anthropic_tools()
        messages = [
            {
                "role": "user",
                "content": (
                    "## Incident Report\n"
                    f"```json\n{json.dumps(incident, indent=2)}\n```\n\n"
                    "Investigate and resolve this network issue. "
                    "Before every tool call, briefly state your reasoning."
                ),
            },
        ]

        yield {"type": "topology_update", "state": self.simulator.get_topology_state()}

        for iteration in range(1, MAX_ITERATIONS + 1):
            yield {"type": "log", "iteration": iteration, "model": self.model}

            llm_input = {
                "model": self.model,
                "max_tokens": 4096,
                "system": self.system_prompt,
                "tools": tools,
                "tool_choice": {"type": "any"},
                "messages": messages,
            }
            print(f"\n{'═'*60}")
            print(f"[iter {iteration}] LLM INPUT")
            print(f"{'═'*60}")
            print(json.dumps(llm_input, indent=2, default=str))
            print(f"{'═'*60}")

            try:
                response = await self.client.messages.create(**llm_input)
            except Exception as exc:
                yield {
                    "type": "error",
                    "message": (
                        f"Anthropic API error: {exc}. "
                        f"Check ANTHROPIC_API_KEY and AGENT_MODEL "
                        f"(currently using model '{self.model}')."
                    ),
                }
                return

            print(f"\n{'─'*60}")
            print(f"[iter {iteration}] RAW LLM RESPONSE")
            print(f"{'─'*60}")
            print(json.dumps(response.model_dump(), indent=2))
            print(f"{'─'*60}")

            # Extract text reasoning and tool use from content blocks
            text_reason = ""
            tool_use_blocks = []
            for block in response.content:
                if block.type == "text":
                    text_reason = block.text.strip()
                elif block.type == "tool_use":
                    tool_use_blocks.append(block)

            if not tool_use_blocks:
                yield {"type": "error", "message": "Model returned no tool call."}
                break

            # One tool per iteration — execute only the first call
            tool_use_block = tool_use_blocks[0]
            tool_name = tool_use_block.name
            tool_params = tool_use_block.input

            raw_content = []
            for block in response.content:
                if block.type == "text":
                    raw_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    raw_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })

            yield {
                "type": "decision",
                "iteration": iteration,
                "reason": text_reason,
                "tool": tool_name,
                "params": tool_params,
                "raw_content": raw_content,
            }

            if tool_name == "finish":
                yield {
                    "type": "done",
                    "iteration": iteration,
                    "reason": tool_params.get("reason", "Issue resolved."),
                    "summary": tool_params.get("summary", ""),
                }
                yield {"type": "report", "text": self._build_report(incident, tool_params)}
                methodology = await self._build_methodology(incident, tool_params)
                if methodology:
                    yield {"type": "methodology", "text": methodology}
                break

            result = self.registry.execute(tool_name, tool_params, self.simulator)

            print(f"\n{'·'*60}")
            print(f"[iter {iteration}] TOOL EXECUTION")
            print(f"  tool:   {tool_name}")
            print(f"  params: {json.dumps(tool_params)}")
            print(f"  result:\n{result}")
            print(f"{'·'*60}")

            self._history.append({
                "iteration": iteration,
                "reason": text_reason,
                "tool": tool_name,
                "params": tool_params,
                "result": result,
            })

            yield {
                "type": "observation",
                "iteration": iteration,
                "tool": tool_name,
                "result": result,
            }

            yield {"type": "topology_update", "state": self.simulator.get_topology_state()}

            messages.append({"role": "assistant", "content": response.content})
            # Every tool_use block must have a matching tool_result — API requirement
            tool_results = []
            for i, block in enumerate(tool_use_blocks):
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result if i == 0 else "Only one tool is executed per iteration.",
                })
            messages.append({"role": "user", "content": tool_results})

        else:
            yield {"type": "error", "message": f"Reached iteration limit ({MAX_ITERATIONS})."}

    async def _build_methodology(self, incident: dict, finish_params: dict) -> str:
        history_lines = "\n".join(
            f"  {i+1}. {s['tool']}({', '.join(f'{k}={v}' for k, v in s['params'].items())})"
            f" → {(s['result'].splitlines()[0] if s['result'] else '').strip()[:120]}"
            for i, s in enumerate(self._history)
        )
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=400,
            system=(
                "You are a senior network engineer reflecting on a completed troubleshooting session. "
                "Write a concise explanation (4–6 sentences) covering: "
                "(1) why you started with the first diagnostic tool and what in the incident report suggested that entry point, "
                "(2) what structured methodology guided your approach — for example OSI model layers (bottom-up or top-down), "
                "TCP/IP stack, divide-and-conquer, or path isolation — and why that fit this incident, "
                "(3) how each tool result narrowed the search and led to the next step. "
                "Be concrete — reference the actual tools and findings."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Incident report:\n{json.dumps(incident, indent=2)}\n\n"
                        f"Tools used in order:\n{history_lines}\n\n"
                        f"Root cause: {finish_params.get('reason', '')}\n"
                        f"Fix applied: {finish_params.get('summary', '')}"
                    ),
                },
            ],
        )
        text = next((b.text for b in response.content if b.type == "text"), "")
        return text.strip()

    def _build_report(self, incident: dict, finish_params: dict) -> dict:
        steps = []
        for step in self._history:
            params_str = ", ".join(f"{k}={v}" for k, v in step["params"].items())
            result_lines = [l.strip() for l in step["result"].splitlines() if l.strip()][:2]
            steps.append({
                "iteration": step["iteration"],
                "tool": f"{step['tool']}({params_str})",
                "reason": step["reason"],
                "found": " | ".join(result_lines),
            })
        return {
            "problem": incident.get("problem", "?"),
            "source": incident.get("source", "?"),
            "destination": incident.get("destination", "?"),
            "steps": steps,
            "root_cause": finish_params.get("reason", "?"),
            "fix": finish_params.get("summary", "?"),
            "total": len(self._history) + 1,
        }
