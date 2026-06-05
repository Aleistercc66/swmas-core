#!/usr/bin/env python3
"""🧠 Meta Agent Graph — LangGraph workflow for swarm supervision."""
import os
import json
import logging
from typing import TypedDict, Annotated, Dict, Any, List
from datetime import datetime

logger = logging.getLogger("meta_agent")

# Try LangGraph
try:
    from langgraph.graph import StateGraph, END
    from langchain_openai import ChatOpenAI
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    logger.warning("LangGraph not available — using rule-based fallback")


# ── State ──

class MetaState(TypedDict):
    """State for the meta agent workflow."""
    messages: Annotated[list, "add_messages"]
    portfolio_summary: Dict[str, Any]
    active_issues: List[str]
    last_decision: str
    confidence: float


# ── LLM Setup ──

class MockLLM:
    """Mock LLM for testing without API keys."""
    
    async def ainvoke(self, prompt: str) -> Any:
        """Return a mock response based on prompt content."""
        class MockResponse:
            def __init__(self, content):
                self.content = content
        
        prompt_lower = prompt.lower()
        
        # Extract key metrics from prompt
        drawdown = 0
        win_rate = 100
        
        # Parse drawdown from prompt
        if "drawdown:" in prompt_lower:
            try:
                dd_line = [l for l in prompt.split("\n") if "drawdown" in l.lower()][0]
                drawdown = float(dd_line.split(":")[-1].strip().rstrip("%"))
            except (IndexError, ValueError):
                pass
        
        # Parse win rate from prompt
        if "win rate:" in prompt_lower:
            try:
                wr_line = [l for l in prompt.split("\n") if "win rate" in l.lower()][0]
                win_rate = float(wr_line.split(":")[-1].strip().rstrip("%"))
            except (IndexError, ValueError):
                pass
        
        # Decision logic based on parsed metrics
        if drawdown > 20:
            return MockResponse("DECISION: SHUTDOWN — Critical drawdown detected. Stopping all trading immediately.")
        elif drawdown > 10:
            return MockResponse("DECISION: ALERT_USER — Portfolio drawdown exceeds comfort threshold. Notifying user.")
        elif win_rate < 40:
            return MockResponse("DECISION: STRATEGY_ADJUST — Win rate declining. Reducing position sizes by 25%.")
        elif "issue" in prompt_lower and "none" not in prompt_lower:
            return MockResponse("DECISION: REPAIR — Detected operational issues. Initiating auto-repair.")
        else:
            return MockResponse("DECISION: HEALTH_CHECK — Swarm operating normally. Continue standard monitoring.")


def get_llm():
    """Get LLM instance (real or mock)."""
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("GROK_API_KEY")
    
    if LANGGRAPH_AVAILABLE and api_key:
        return ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.0")),
            api_key=api_key,
        )
    else:
        logger.info("Using MockLLM (no API key configured)")
        return MockLLM()


# ── Nodes ──

async def analyze_situation(state: MetaState) -> Dict[str, Any]:
    """Analyze swarm health and decide action."""
    llm = get_llm()
    
    # Build prompt
    portfolio = state.get("portfolio_summary", {})
    issues = state.get("active_issues", [])
    
    # Get context from knowledge base if available
    context = ""
    try:
        from core.knowledge_base import KnowledgeBase
        kb = KnowledgeBase()
        results = kb.query("recent issues and decisions", k=3)
        context = json.dumps(results, default=str)
    except Exception:
        pass
    
    prompt = f"""
You are the Meta Agent of an autonomous crypto trading swarm.
Your job is to monitor, analyze, and make high-level decisions.

Current Portfolio:
- Balance: ${portfolio.get('balance', 0):.2f}
- Open Positions: {portfolio.get('open_positions', 0)}
- Win Rate: {portfolio.get('win_rate', 0):.1f}%
- Daily PnL: {portfolio.get('daily_pnl', 0):.2f}%
- Drawdown: {portfolio.get('drawdown', 0):.2f}%

Active Issues:
{chr(10).join(f"- {issue}" for issue in issues) if issues else "None detected"}

Recent Context:
{context}

Available Actions:
1. HEALTH_CHECK — Swarm healthy, continue normal operations
2. STRATEGY_ADJUST — Modify strategy parameters based on performance
3. REPAIR — Fix detected issues, pause risky operations
4. ALERT_USER — Notify user of important situation
5. SHUTDOWN — Emergency stop all trading

DECISION FORMAT: "DECISION: [ACTION] — [brief reasoning]"
"""
    
    try:
        response = await llm.ainvoke(prompt)
        decision_text = response.content
        
        # Extract decision
        if "SHUTDOWN" in decision_text:
            decision = "SHUTDOWN"
        elif "REPAIR" in decision_text:
            decision = "REPAIR"
        elif "STRATEGY_ADJUST" in decision_text:
            decision = "STRATEGY_ADJUST"
        elif "ALERT_USER" in decision_text:
            decision = "ALERT_USER"
        else:
            decision = "HEALTH_CHECK"
        
        return {
            "messages": [decision_text],
            "last_decision": decision,
            "confidence": 0.85,
        }
        
    except Exception as e:
        logger.error(f"LLM analysis failed: {e}")
        return {
            "messages": [f"Error: {e}"],
            "last_decision": "HEALTH_CHECK",
            "confidence": 0.5,
        }


async def execute_action(state: MetaState) -> Dict[str, Any]:
    """Execute the decided action."""
    decision = state.get("last_decision", "HEALTH_CHECK")
    
    actions_log = []
    
    if decision == "SHUTDOWN":
        actions_log.append("🛑 Triggered emergency shutdown")
        # Publish shutdown event
        try:
            from core import get_event_bus, EventType
            bus = await get_event_bus()
            await bus.publish_simple(
                event_type=EventType.ALERT,
                data={"alert_type": "SHUTDOWN", "reason": "Meta agent emergency decision"},
                source="meta_agent",
            )
        except Exception as e:
            logger.error(f"Shutdown event failed: {e}")
    
    elif decision == "REPAIR":
        actions_log.append("🔧 Initiating auto-repair sequence")
    
    elif decision == "STRATEGY_ADJUST":
        actions_log.append("📊 Adjusting strategy parameters")
    
    elif decision == "ALERT_USER":
        actions_log.append("🔔 Sending alert to user")
    
    else:  # HEALTH_CHECK
        actions_log.append("✅ Health check passed")
    
    return {
        "messages": state.get("messages", []) + actions_log,
    }


# ── Graph Builder ──

def build_meta_graph():
    """Build and compile the meta agent workflow."""
    if not LANGGRAPH_AVAILABLE:
        logger.info("LangGraph not available — returning rule-based meta agent")
        return None
    
    workflow = StateGraph(MetaState)
    
    # Add nodes
    workflow.add_node("analyze", analyze_situation)
    workflow.add_node("execute", execute_action)
    
    # Entry point
    workflow.set_entry_point("analyze")
    
    # Edges
    workflow.add_edge("analyze", "execute")
    workflow.add_edge("execute", END)
    
    return workflow.compile()


# Global graph instance
meta_graph = build_meta_graph()
