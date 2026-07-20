from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

class BaseConnector(ABC):
    """
    Abstract base class for all speech provider connectors.
    Provides common initialization and standard methods for agent discovery and call synchronization.
    """
    def __init__(self, api_key: str, config: Dict[str, Any] = None):
        self.api_key = api_key
        self.config = config or {}

    @abstractmethod
    def verify_key(self) -> tuple[bool, str]:
        """Validates API credentials with the provider."""
        pass

    @abstractmethod
    def list_agents(self) -> List[Dict[str, Any]]:
        """
        Fetches the list of agents available for this provider account and normalizes them.
        
        Returns:
            List[Dict[str, Any]]: List of normalized agent dictionaries containing:
                - external_id (str): Provider-specific agent ID
                - name (str): Display name of agent
                - description (Optional[str]): Description or summary
                - created_at (Optional[str | datetime]): Creation date
                - raw_metadata (Dict[str, Any]): Original raw metadata payload
        """
        pass

    @abstractmethod
    def list_calls(
        self,
        agent_id: Optional[str] = None,
        created_after: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetches historical/new call summaries from the provider.
        
        Returns:
            List[Dict[str, Any]]: List of normalized call summary dicts containing:
                - external_id (str): Provider-specific call identifier
                - agent_id (str): Provider-specific agent ID
                - started_at (Optional[datetime]): Call start timestamp
                - ended_at (Optional[datetime]): Call end timestamp
                - duration_sec (int): Total call duration in seconds
                - status (str): Call status (e.g. 'completed', 'ended', 'processing')
                - cost (Optional[float]): Estimated call cost
                - raw_metadata (Dict[str, Any]): Provider raw payload
        """
        pass

    @abstractmethod
    def get_call(self, call_id: str) -> Dict[str, Any]:
        """
        Fetches detailed call data, audio/recording URL, and speaker turn transcriptions.
        
        Returns:
            Dict[str, Any]: Standardized call data dictionary containing:
                - external_id (str): Provider call ID
                - agent_id (Optional[str]): External agent ID
                - agent_name (str): Name of agent
                - audio_url (str): Remote or downloaded static audio path
                - duration_sec (int): Call duration in seconds
                - started_at (Optional[datetime]): Start timestamp
                - ended_at (Optional[datetime]): End timestamp
                - cost (Optional[float]): Cost of call
                - transcript (str): Full text transcript
                - turns (List[Dict[str, Any]]): Chronological speaker turns:
                    - speaker (str): "user" or "agent"
                    - start_sec (float): Turn start time
                    - end_sec (float): Turn end time
                    - text (str): Text content
                - metadata (Dict[str, Any]): Raw provider payload
        """
        pass

    def fetch_call_data(self, call_id: str) -> Dict[str, Any]:
        """Backward-compatible wrapper for get_call."""
        return self.get_call(call_id)


