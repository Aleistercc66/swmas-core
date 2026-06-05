#!/usr/bin/env python3
"""
Message Router — Clean, Categorized, Controlled Message Flow
Every message gets: type, priority, delivery_mode
"""
from enum import Enum
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import json
import time

class MessageType(Enum):
    URGENT = "urgent"       # Action needed NOW
    ALERT = "alert"         # Important opportunity
    SIGNAL = "signal"       # Trading signal
    REPORT = "report"       # Summary/analysis
    STATUS = "status"       # System health
    REQUEST = "request"     # Needs user decision
    LOG = "log"             # Debug/operation info
    CHAT = "chat"           # Direct conversation

class Priority(Enum):
    P0_CRITICAL = 0   # Instant, repeated if no ack
    P1_HIGH = 1       # < 2 min delivery
    P2_MEDIUM = 2     # < 15 min delivery
    P3_LOW = 3        # Batch hourly
    P4_INFO = 4       # Daily digest or silent

class DeliveryMode(Enum):
    INSTANT = "instant"     # Send immediately
    BATCHED = "batched"     # Collect and send digest
    ON_DEMAND = "ondemand"  # Only when requested
    SILENT = "silent"       # Logfile only

# Type → Priority mapping
TYPE_PRIORITY = {
    MessageType.URGENT: Priority.P0_CRITICAL,
    MessageType.ALERT: Priority.P1_HIGH,
    MessageType.SIGNAL: Priority.P1_HIGH,
    MessageType.REQUEST: Priority.P1_HIGH,
    MessageType.REPORT: Priority.P3_LOW,
    MessageType.STATUS: Priority.P4_INFO,
    MessageType.LOG: Priority.P4_INFO,
    MessageType.CHAT: Priority.P2_MEDIUM,
}

# Priority → Delivery mapping
PRIORITY_DELIVERY = {
    Priority.P0_CRITICAL: DeliveryMode.INSTANT,
    Priority.P1_HIGH: DeliveryMode.INSTANT,
    Priority.P2_MEDIUM: DeliveryMode.BATCHED,
    Priority.P3_LOW: DeliveryMode.BATCHED,
    Priority.P4_INFO: DeliveryMode.SILENT,
}

class MessageRouter:
    """Central message routing and filtering system"""
    
    def __init__(self):
        self.batch_queue: List[Dict] = []
        self.last_alert_time: Dict[str, datetime] = {}  # Dedup cache
        self.dedup_window = timedelta(hours=1)
        self.muted_systems: set = set()
        self.digest_mode = False
        self.urgent_only = False
        
    def classify(self, content: str, msg_type: MessageType = None) -> tuple:
        """Classify a message into type and priority"""
        if msg_type is None:
            msg_type = self._detect_type(content)
        
        priority = TYPE_PRIORITY.get(msg_type, Priority.P2_MEDIUM)
        delivery = PRIORITY_DELIVERY.get(priority, DeliveryMode.BATCHED)
        
        return msg_type, priority, delivery
    
    def _detect_type(self, content: str) -> MessageType:
        """Auto-detect message type from content"""
        content_lower = content.lower()
        
        if any(w in content_lower for w in ['critical', 'emergency', 'compromised', 'hack', 'urgent action']):
            return MessageType.URGENT
        elif any(w in content_lower for w in ['gem', 'alert', 'opportunity', 'found', 'momentum']):
            return MessageType.ALERT
        elif any(w in content_lower for w in ['buy', 'sell', 'signal', 'entry', 'tp', 'sl']):
            return MessageType.SIGNAL
        elif any(w in content_lower for w in ['report', 'summary', 'daily', 'pnl']):
            return MessageType.REPORT
        elif any(w in content_lower for w in ['status', 'running', 'healthy', 'uptime']):
            return MessageType.STATUS
        elif any(w in content_lower for w in ['decision', 'approve', 'confirm', 'question']):
            return MessageType.REQUEST
        elif any(w in content_lower for w in ['error', 'debug', 'scan complete', 'log']):
            return MessageType.LOG
        else:
            return MessageType.CHAT
    
    def should_send(self, content: str, system: str = "general") -> tuple:
        """
        Main routing decision.
        Returns: (should_send: bool, formatted_content: str, priority: Priority)
        """
        msg_type, priority, delivery = self.classify(content)
        
        # Check muted systems
        if system in self.muted_systems:
            return False, content, priority
        
        # Check urgent-only mode
        if self.urgent_only and priority.value > Priority.P1_HIGH.value:
            return False, content, priority
        
        # Check deduplication for alerts
        if msg_type in [MessageType.ALERT, MessageType.SIGNAL]:
            dedup_key = f"{system}:{self._extract_token(content)}"
            last_time = self.last_alert_time.get(dedup_key)
            if last_time and (datetime.now() - last_time) < self.dedup_window:
                return False, content, priority  # Duplicate, skip
            self.last_alert_time[dedup_key] = datetime.now()
        
        # Format based on priority
        formatted = self._format_message(content, msg_type, priority)
        
        # Route based on delivery mode
        if delivery == DeliveryMode.INSTANT:
            return True, formatted, priority
        elif delivery == DeliveryMode.BATCHED:
            self._add_to_batch(formatted, msg_type, priority, system)
            return False, formatted, priority  # Will be sent in digest
        elif delivery == DeliveryMode.SILENT:
            self._log_silent(formatted, system)
            return False, formatted, priority
        else:
            return True, formatted, priority
    
    def _extract_token(self, content: str) -> str:
        """Extract token symbol for deduplication"""
        import re
        # Look for token symbols - avoid raw dollar sign in source
        pattern = re.escape("$") + r"([A-Z]{2,10})"
        tokens = re.findall(pattern, content)
        return tokens[0] if tokens else "unknown"
    
    def _format_message(self, content: str, msg_type: MessageType, priority: Priority) -> str:
        """Apply formatting template based on type and priority"""
        timestamp = datetime.now().strftime("%H:%M")
        
        if priority == Priority.P0_CRITICAL:
            return f"🔴 **CRITICAL [{timestamp}]** 🔴\n\n{content}\n\n⚠️ ACKNOWLEDGE REQUIRED"
        elif priority == Priority.P1_HIGH:
            return f"🟠 **[{timestamp}]** {content}"
        elif priority == Priority.P2_MEDIUM:
            return f"🟡 **[{timestamp}]** {content}"
        elif priority == Priority.P3_LOW:
            return f"🔵 [{timestamp}] {content}"
        else:
            return content
    
    def _add_to_batch(self, content: str, msg_type: MessageType, priority: Priority, system: str):
        """Add message to batch queue"""
        self.batch_queue.append({
            'content': content,
            'type': msg_type.value,
            'priority': priority.value,
            'system': system,
            'time': datetime.now().isoformat()
        })
    
    def _log_silent(self, content: str, system: str):
        """Log silent message to file"""
        log_line = f"[{datetime.now().isoformat()}] [{system}] {content}\n"
        with open('/tmp/silent_messages.log', 'a') as f:
            f.write(log_line)
    
    def get_digest(self) -> Optional[str]:
        """Get batched messages as digest. Returns None if empty."""
        if not self.batch_queue:
            return None
        
        # Group by system
        by_system = {}
        for msg in self.batch_queue:
            sys = msg['system']
            if sys not in by_system:
                by_system[sys] = []
            by_system[sys].append(msg)
        
        lines = [f"📦 **DIGEST — {datetime.now().strftime('%H:%M')}** 📦\n"]
        
        for system, messages in by_system.items():
            lines.append(f"\n**{system.upper()}** ({len(messages)} messages)")
            for msg in messages[:5]:  # Max 5 per system
                lines.append(f"  • {msg['content'][:100]}...")
            if len(messages) > 5:
                lines.append(f"  ... and {len(messages) - 5} more")
        
        self.batch_queue = []  # Clear after digest
        return "\n".join(lines)
    
    # User control commands
    def mute(self, system: str):
        self.muted_systems.add(system)
        
    def unmute(self, system: str):
        self.muted_systems.discard(system)
        
    def set_digest(self, enabled: bool):
        self.digest_mode = enabled
        
    def set_urgent_only(self, enabled: bool):
        self.urgent_only = enabled
        
    def get_status(self) -> str:
        return f"""🎛️ **Message Router Status**

Muted systems: {', '.join(self.muted_systems) or 'None'}
Digest mode: {'ON' if self.digest_mode else 'OFF'}
Urgent only: {'ON' if self.urgent_only else 'OFF'}
Batch queue: {len(self.batch_queue)} messages waiting
"""

# Global router instance
router = MessageRouter()

# Convenience function for systems
def send_system_message(content: str, system: str = "general", msg_type: MessageType = None) -> bool:
    """
    Main entry point for all system messages.
    Returns True if message should be sent immediately.
    """
    should_send, formatted, priority = router.should_send(content, system)
    return should_send, formatted, priority

# Example usage:
if __name__ == "__main__":
    # Test classification
    tests = [
        ("CRITICAL: Wallet compromised!", None),
        ("Gem found: BONKUJI +200% momentum!", None),
        ("BUY TOKEN at $0.05 | TP: $0.10", None),
        ("Daily report: PnL +12.5%", None),
        ("Scan complete. 0 gems found.", None),
        ("Hey, what's the status?", None),
    ]
    
    for content, msg_type in tests:
        detected_type, priority, delivery = router.classify(content, msg_type)
        print(f"'{content[:40]}...' → {detected_type.value} | {priority.name} | {delivery.value}")
