from agent.state import AgentState
from agent.memory import Memory
from agent.planner import Planner
from agent.executor import Executor
from agent.observation import Observation


class Agent:
    def __init__(self) -> None:
        self.state = AgentState.IDLE
        self.memory = Memory()
        self.planner = Planner()
        self.executor = Executor()
        self.observation = Observation()

    async def run(self, prompt: str) -> str:
        self.state = AgentState.THINKING
        self.memory.add({"role": "user", "content": prompt})

        subtasks = self.planner.decompose(prompt)
        results = []

        for subtask in subtasks:
            self.state = AgentState.THINKING
            result = await self.executor.execute("think", {"prompt": subtask})
            results.append(str(result))

        self.state = AgentState.DONE
        final = "\n".join(results)
        self.memory.add({"role": "assistant", "content": final})
        return final

    def get_state(self) -> AgentState:
        return self.state

    def get_history(self) -> list[dict]:
        return self.memory.recent(20)
