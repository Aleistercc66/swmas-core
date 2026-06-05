#!/usr/bin/env python3
"""🧠 Meta Agent — LLM-powered swarm supervisor with event-driven architecture."""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from core import (
    get_logger, get_settings,
    get_event_bus, EventType, SwarmEvent,
    set_agent_healthy, set_agent_down,
)

logger = get_logger("meta_agent")

# Import knowledge base and graph
from core.knowledge_base import KnowledgeBase
from core.meta_agent_graph import meta_graph, MetaState


class MetaAgent:
    """LLM-powered meta agent that supervises the entire swarm."""
    
    def __init__(self):
        self.settings = get_settings()
        self.bus = None
        self.running = False
        self.kb = KnowledgeBase()
        self.state: MetaState = {
            "messages": [],
            "portfolio_summary": {
                "balance": 10000.0,
                "open_positions": 0,
                "win_rate": 50.0,
                "daily_pnl": 0.0,
                "drawdown": 0.0,
            },
            "active_issues": [],
            "last_decision": "HEALTH_CHECK",
            "confidence": 1.0,
        }
        self.consumer_tasks: List[asyncio.Task] = []
        self.analysis_task: Optional[asyncio.Task] = None
    
    async def __aenter__(self):
        self.bus = await get_event_bus()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.running = False
        for task in self.consumer_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        if self.analysis_task:
            self.analysis_task.cancel()
            try:
                await self.analysis_task
            except asyncio.CancelledError:
                pass
        if self.bus:
            await self.bus.disconnect()
    
    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Fetch current portfolio state from metrics or memory."""
        # In production, pull from Redis/DB
        return self.state["portfolio_summary"]
    
    async def detect_issues(self) -> List[str]:
        """Detect active issues from events and metrics."""
        issues = []
        portfolio = self.state["portfolio_summary"]
        
        if portfolio.get("drawdown", 0) > 15:
            issues.append(f"High drawdown: {portfolio['drawdown']:.1f}%")
        
        if portfolio.get("win_rate", 100) < 40:
            issues.append(f"Low win rate: {portfolio['win_rate']:.1f}%")
        
        if portfolio.get("open_positions", 0) > 5:
            issues.append(f"Too many open positions: {portfolio['open_positions']}")
        
        return issues
    
    async def handle_event(self, event: SwarmEvent):
        """Handle incoming swarm events."""
        try:
            event_type = event.event_type
            data = event.data
            
            # Store in knowledge base
            summary = f"{event_type} from {event.source}"
            self.kb.add_event(event_type, data, summary)
            
            # Update portfolio based on event type
            if event_type == EventType.POSITION_OPENED.value:
                self.state["portfolio_summary"]["open_positions"] += 1
                
            elif event_type == EventType.POSITION_CLOSED.value:
                self.state["portfolio_summary"]["open_positions"] -= 1
                pnl = data.get("pnl_pct", 0)
                self.state["portfolio_summary"]["daily_pnl"] += pnl
                
            elif event_type == EventType.POSITION_UPDATED.value:
                # Track PnL changes
                pnl = data.get("pnl_percent", 0)
                if pnl < -10:
                    self.state["active_issues"].append(
                        f"Position {data.get('symbol', '?')} at {pnl:.1f}% loss"
                    )
            
            # Detect issues
            self.state["active_issues"] = await self.detect_issues()
            
            # Log
            logger.info(
                f"🧠 Meta Agent processed {event_type} | "
                f"Open: {self.state['portfolio_summary']['open_positions']} | "
                f"Issues: {len(self.state['active_issues'])}"
            )
            
            set_agent_healthy("meta_agent")
            
        except Exception as e:
            logger.error(f"Meta agent event handler error: {e}")
            set_agent_down("meta_agent")
    
    async def _run_periodic_analysis(self):
        """Run full LLM analysis every 5 minutes."""
        while self.running:
            try:
                await asyncio.sleep(300)  # 5 minutes
                
                if not self.running:
                    break
                
                logger.info("🧠 Running periodic meta analysis...")
                
                # Update state
                self.state["portfolio_summary"] = await self.get_portfolio_summary()
                self.state["active_issues"] = await self.detect_issues()
                
                # Run LangGraph
                if meta_graph:
                    result = await meta_graph.ainvoke(self.state)
                    self.state["last_decision"] = result.get("last_decision", "HEALTH_CHECK")
                    self.state["confidence"] = result.get("confidence", 0.5)
                    
                    logger.info(
                        f"🧠 Meta Decision: {self.state['last_decision']} "
                        f"(confidence: {self.state['confidence']:.2f})"
                    )
                    
                    # Publish decision event
                    await self.bus.publish_simple(
                        event_type=EventType.ALERT,
                        data={
                            "alert_type": "META_DECISION",
                            "decision": self.state["last_decision"],
                            "confidence": self.state["confidence"],
                            "issues": self.state["active_issues"],
                            "portfolio": self.state["portfolio_summary"],
                        },
                        source="meta_agent",
                    )
                else:
                    # Rule-based fallback
                    decision = self._rule_based_decision()
                    self.state["last_decision"] = decision
                    logger.info(f"🧠 Rule-based decision: {decision}")
                
                # Clear resolved issues
                self.state["active_issues"] = []
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Periodic analysis error: {e}")
                await asyncio.sleep(60)
    
    def _rule_based_decision(self) -> str:
        """Fallback rule-based decision when LLM unavailable."""
        portfolio = self.state["portfolio_summary"]
        
        if portfolio.get("drawdown", 0) > 20:
            return "SHUTDOWN"
        elif portfolio.get("drawdown", 0) > 10:
            return "ALERT_USER"
        elif portfolio.get("win_rate", 100) < 35:
            return "STRATEGY_ADJUST"
        elif self.state["active_issues"]:
            return "REPAIR"
        else:
            return "HEALTH_CHECK"
    
    async def run(self):
        """Run meta agent."""
        logger.info("═══════════════════════════════════════")
        logger.info("🧠 META AGENT STARTED")
        logger.info("LLM-powered swarm supervision")
        logger.info("═══════════════════════════════════════")
        
        self.running = True
        
        # Subscribe to critical events
        critical_events = [
            EventType.POSITION_OPENED,
            EventType.POSITION_CLOSED,
            EventType.POSITION_UPDATED,
            EventType.RISK_ASSESSED,
            EventType.SIGNAL_GENERATED,
            EventType.ALERT,
        ]
        
        for et in critical_events:
            task = await self.bus.subscribe(
                event_type=et,
                consumer_name="meta_agent",
                handler=self.handle_event,
            )
            self.consumer_tasks.append(task)
        
        logger.info(f"Subscribed to {len(critical_events)} event types")
        
        # Start periodic analysis
        self.analysis_task = asyncio.create_task(self._run_periodic_analysis())
        
        logger.info("Waiting for swarm events...")
        
        try:
            while self.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Meta agent stopped")


async def main():
    async with MetaAgent() as agent:
        await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
