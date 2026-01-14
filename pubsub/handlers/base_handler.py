"""
Base handler class for pub-sub events.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any

logger = logging.getLogger(__name__)


class BaseHandler(ABC):
    """
    Abstract base class for event handlers.

    Subclasses must implement the handle() method.
    """

    def __init__(self, handler_name: str):
        """
        Initialize handler.

        Args:
            handler_name: Name for logging purposes
        """
        self.handler_name = handler_name

    @abstractmethod
    def handle(self, event_data: Dict[str, Any]) -> bool:
        """
        Handle an event.

        Args:
            event_data: Event data dictionary

        Returns:
            True if handled successfully, False otherwise
        """
        pass

    def can_handle(self, event_type: str) -> bool:
        """
        Check if this handler can process the given event type.

        Override in subclasses to restrict event types.

        Args:
            event_type: Type of event

        Returns:
            True if this handler can process the event
        """
        return True

    def log_event(self, event_data: Dict[str, Any], message: str):
        """Log event with context."""
        event_id = event_data.get('event_id', 'N/A')
        event_type = event_data.get('event_type', 'unknown')
        logger.info(f"[{self.handler_name}] Event {event_id} ({event_type}): {message}")
