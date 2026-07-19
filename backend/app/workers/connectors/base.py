from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseConnector(ABC):
    """
    Abstract base class for all speech provider connectors.
    Provides common initialization and requires subclasses to implement fetch_call_data.
    """
    def __init__(self, api_key: str, config: Dict[str, Any] = None):
        self.api_key = api_key
        self.config = config or {}

    @abstractmethod
    def fetch_call_data(self, call_id: str) -> Dict[str, Any]:
        """
        Fetches call metadata, audio URL, and speaker turns from the provider.
        
        Args:
            call_id (str): The unique call identifier from the provider.
            
        Returns:
            Dict[str, Any]: Standardized call data dictionary containing:
                - audio_url (str): URL to access/download the audio file.
                - duration_sec (int): Total duration of the call in seconds.
                - agent_name (str): Name of the agent/assistant who participated in the call.
                - turns (List[Dict[str, Any]]): Chronological speaker turns, where each turn has:
                    - speaker (str): "user" or "agent"
                    - start_sec (float): Start time of the turn in seconds.
                    - end_sec (float): End time of the turn in seconds.
                    - text (str): Text transcription of the turn.
                - metadata (Dict[str, Any]): Provider-specific raw metadata.
        """
        pass

    @abstractmethod
    def list_agents() -> list[Dict[str, Any]]:
        """
        Fetches the list of agents available for this provider account and normalizes them.
        
        Returns:
            list[Dict[str, Any]]: List of normalized agent dictionaries containing:
                - external_id (str): Provider-specific agent ID
                - name (str): Display name of agent
                - description (Optional[str]): Description or summary
                - created_at (Optional[str | datetime]): Creation date
                - raw_metadata (Dict[str, Any]): Original raw metadata payload
        """
        pass

