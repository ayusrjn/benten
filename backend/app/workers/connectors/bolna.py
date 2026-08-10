import requests
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from app.workers.connectors.base import BaseConnector

logger = logging.getLogger(__name__)

class BolnaConnector(BaseConnector):
    """
    Connector for Bolna.ai API.
    Retrieves agents, executions (calls), transcripts, recordings, and speaker turns.
    """
    def verify_key(self) -> tuple[bool, str]:
        try:
            url = "https://api.bolna.ai/v2/agent/all"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                return True, "Successfully connected to Bolna API"
            elif res.status_code in (401, 403):
                return False, "Invalid Bolna API key"
            return False, f"Bolna API returned status code {res.status_code}"
        except Exception as e:
            return False, f"Failed to connect to Bolna: {str(e)}"

    def get_call(self, call_id: str) -> Dict[str, Any]:
        url = f"https://api.bolna.ai/executions/{call_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        duration_sec = int(
            data.get("conversation_duration")
            or data.get("duration")
            or data.get("duration_sec")
            or data.get("telephony_data", {}).get("duration")
            or 0
        )
        audio_url = (
            data.get("recording_url")
            or data.get("recording")
            or data.get("audio_url")
            or data.get("telephony_data", {}).get("recording_url")
        )
        agent_id = data.get("agent_id")
        agent_name = data.get("agent_name") or (f"Bolna Agent ({agent_id})" if agent_id else "Bolna Agent")
        
        # Parse timestamps and cost
        started_at = None
        created_at_val = data.get("created_at") or data.get("started_at")
        if created_at_val:
            try:
                if isinstance(created_at_val, (int, float)):
                    # Epoch time (seconds vs milliseconds check)
                    if created_at_val > 1e11:
                        created_at_val = created_at_val / 1000.0
                    started_at = datetime.fromtimestamp(created_at_val, tz=timezone.utc)
                else:
                    started_at = datetime.fromisoformat(str(created_at_val).replace("Z", "+00:00"))
            except Exception:
                pass
                
        ended_at = None
        if started_at and duration_sec:
            ended_at = datetime.fromtimestamp(started_at.timestamp() + duration_sec, tz=timezone.utc)
            
        cost_val = data.get("total_cost") or data.get("cost") or data.get("price")
        cost = float(cost_val) if isinstance(cost_val, (int, float)) else None
        
        transcript = data.get("transcript") or ""
        turns = []
        
        # Try structured turns first (e.g. key: "turns", "transcript_object", "messages")
        raw_turns = data.get("turns") or data.get("transcript_object") or data.get("messages")
        if raw_turns and isinstance(raw_turns, list):
            for turn in raw_turns:
                if not isinstance(turn, dict):
                    continue
                role = turn.get("role") or turn.get("speaker") or "agent"
                speaker = "agent" if role in ("agent", "assistant", "bot") else "user"
                text = turn.get("text") or turn.get("message") or turn.get("content") or ""
                
                start_sec = turn.get("start_sec") or turn.get("start") or turn.get("timestamp") or 0.0
                end_sec = turn.get("end_sec") or turn.get("end") or (float(start_sec) + max(0.5, len(text) / 15.0))
                
                turns.append({
                    "speaker": speaker,
                    "start_sec": round(float(start_sec), 2),
                    "end_sec": round(float(end_sec), 2),
                    "text": text
                })
        
        # Parse plain-text transcript prefix pattern fallback if structured turns are absent
        if not turns and transcript:
            lines = transcript.split('\n')
            current_time = 0.0
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                speaker = "agent"
                text = line
                
                # Check for "Speaker: text" structure
                if ":" in line:
                    prefix, payload = line.split(":", 1)
                    prefix_clean = prefix.strip().lower()
                    if prefix_clean in ("agent", "assistant", "bot", "system"):
                        speaker = "agent"
                        text = payload.strip()
                    elif prefix_clean in ("user", "customer", "human", "speaker"):
                        speaker = "user"
                        text = payload.strip()
                    else:
                        # Unrecognized prefix, treat search for user/agent inside prefix or default
                        if "user" in prefix_clean or "customer" in prefix_clean:
                            speaker = "user"
                        text = payload.strip()
                
                est_dur = max(1.5, len(text) / 15.0)
                end_time = current_time + est_dur
                
                if duration_sec > 0:
                    end_time = min(end_time, duration_sec)
                    
                turns.append({
                    "speaker": speaker,
                    "start_sec": round(current_time, 2),
                    "end_sec": round(end_time, 2),
                    "text": text
                })
                
                current_time = end_time
                if duration_sec > 0 and current_time >= duration_sec:
                    break
        
        # Fallback duration calculation
        if not duration_sec and turns:
            duration_sec = int(turns[-1]["end_sec"])
            
        return {
            "external_id": call_id,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "audio_url": audio_url,
            "duration_sec": duration_sec,
            "started_at": started_at,
            "ended_at": ended_at,
            "cost": cost,
            "transcript": transcript,
            "turns": turns,
            "metadata": data
        }

    def fetch_call_data(self, call_id: str) -> Dict[str, Any]:
        return self.get_call(call_id)

    def list_calls(
        self,
        agent_id: Optional[str] = None,
        created_after: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieves call history list.
        If agent_id is provided, fetches executions for that agent.
        Otherwise lists all agents first and aggregates executions.
        """
        calls_list = []
        headers = {"Authorization": f"Bearer {self.api_key}"}

        # Sub-helper to fetch/normalize executions for a single agent
        def fetch_for_agent(aid: str) -> List[Dict[str, Any]]:
            # page_size=limit page_number=1 to pull up to the limit
            # GET /v2/agent/{agent_id}/executions
            agent_calls = []
            url = f"https://api.bolna.ai/v2/agent/{aid}/executions"
            params = {"page_number": 1, "page_size": min(limit, 100)}
            try:
                res = requests.get(url, headers=headers, params=params, timeout=10)
                res.raise_for_status()
                data = res.json()
                
                # Standardize array responses
                if isinstance(data, list):
                    raw_execs = data
                elif isinstance(data, dict):
                    raw_execs = data.get("data") or data.get("executions") or []
                else:
                    raw_execs = []
                if not isinstance(raw_execs, list):
                    raw_execs = []
                    
                for ex in raw_execs:
                    if not isinstance(ex, dict):
                        continue
                    cid = ex.get("execution_id") or ex.get("id")
                    if not cid:
                        continue
                        
                    started_val = ex.get("created_at") or ex.get("started_at")
                    started_dt = None
                    if started_val:
                        try:
                            if isinstance(started_val, (int, float)):
                                if started_val > 1e11:
                                    started_val = started_val / 1000.0
                                started_dt = datetime.fromtimestamp(started_val, tz=timezone.utc)
                            else:
                                started_dt = datetime.fromisoformat(str(started_val).replace("Z", "+00:00"))
                        except Exception:
                            pass
                            
                    dur = int(
                        ex.get("conversation_duration")
                        or ex.get("duration")
                        or ex.get("duration_sec")
                        or ex.get("telephony_data", {}).get("duration")
                        or 0
                    )
                    cost_val = ex.get("total_cost") or ex.get("cost") or ex.get("price")
                    cost = float(cost_val) if isinstance(cost_val, (int, float)) else None
                    
                    agent_calls.append({
                        "external_id": cid,
                        "agent_id": aid,
                        "started_at": started_dt,
                        "ended_at": datetime.fromtimestamp(started_dt.timestamp() + dur, tz=timezone.utc) if started_dt and dur else None,
                        "duration_sec": dur,
                        "status": ex.get("status") or "completed",
                        "cost": cost,
                        "raw_metadata": ex
                    })
            except Exception as e:
                logger.exception(f"Failed to fetch execution records for Bolna agent {aid}: {e}")
            return agent_calls

        if agent_id:
            calls_list = fetch_for_agent(agent_id)
        else:
            try:
                agents = self.list_agents()
                for ag in agents:
                    calls_list.extend(fetch_for_agent(ag["external_id"]))
            except Exception as e:
                logger.exception(f"Failed to aggregate call history: {e}")

        # Post extraction filter by created_after
        if created_after:
            if created_after.tzinfo is None:
                created_after = created_after.replace(tzinfo=timezone.utc)
            calls_list = [
                c for c in calls_list 
                if c["started_at"] and (c["started_at"].replace(tzinfo=timezone.utc) if c["started_at"].tzinfo is None else c["started_at"]) > created_after
            ]
            
        # Sort and limit
        calls_list.sort(key=lambda x: x["started_at"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return calls_list[:limit]

    def list_agents(self) -> List[Dict[str, Any]]:
        agents_list = []
        url = "https://api.bolna.ai/v2/agent/all"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            raw_agents = data if isinstance(data, list) else data.get("agents", [])
            for item in raw_agents:
                agent_id = item.get("id") or item.get("agent_id")
                agents_list.append({
                    "external_id": agent_id,
                    "name": item.get("agent_name") or f"Bolna Agent ({agent_id})",
                    "description": f"Status: {item.get('agent_status') or item.get('status', 'active')}",
                    "created_at": item.get("created_at"),
                    "raw_metadata": item
                })
        except Exception as e:
            logger.exception("Failed to fetch agent list from Bolna API")
            raise
            
        return agents_list
