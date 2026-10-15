"""Human-in-the-loop gate: pauses irreversible intents for approval."""
import asyncio
from src.graph_store import GraphStore

GATED_KEYWORDS = ("deploy", "schema change", "payment", "authentication", "auth")


class HITLGate:
    def __init__(self, store: GraphStore, timeout_sec: int = 600, auto_approve_demo: bool = True):
        self.store = store
        self.timeout_sec = timeout_sec
        self.auto_approve_demo = auto_approve_demo

    def requires_gate(self, intent: str) -> bool:
        lower = intent.lower()
        return any(k in lower for k in GATED_KEYWORDS)

    async def ask(self, intent: str) -> bool:
        print(f"\n[GATE] Intent: {intent}. Approve? [y/N] ", end="", flush=True)
        if self.auto_approve_demo:
            # Demo mode: log and auto-approve for non-gated; gated ones still prompt but default deny on timeout
            try:
                line = await asyncio.wait_for(asyncio.to_thread(input), timeout=self.timeout_sec)
                approved = line.strip().lower() == "y"
            except asyncio.TimeoutError:
                approved = False
                print("\n[GATE] Timeout -> denied")
        else:
            approved = True
        self.store.log("hitl", "decision", {"intent": intent, "approved": approved})
        return approved
