import logging
from typing import Dict, List, Callable, Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class AgentMessage(BaseModel):
    """Structured message protocol for agent-to-agent transactions."""
    transaction_id: str
    sender: str
    receiver: str
    topic: str
    payload: dict
    status: str = "sent"

class AgentEventBroker:
    """Core broker coordinating events and message loops."""
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, topic: str, handler: Callable):
        """Register a handler callback for a specific event topic."""
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(handler)
        logger.info(f"Broker: Registered handler on topic '{topic}'")

    async def publish(self, message: AgentMessage):
        """Asynchronously dispatch an agent message to all active topic subscribers."""
        topic = message.topic
        logger.info(f"Broker: Publishing message on topic '{topic}' from '{message.sender}'")
        
        if topic in self.subscribers:
            for handler in self.subscribers[topic]:
                try:
                    await handler(message)
                except Exception as e:
                    logger.error(f"Error executing event handler on topic '{topic}': {e}")
        else:
            logger.debug(f"Broker: No active subscribers found for topic '{topic}'")

# Global event broker instance
event_broker = AgentEventBroker()

def get_event_broker() -> AgentEventBroker:
    return event_broker
