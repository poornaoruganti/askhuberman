from src.shared.state_store import IngestionStateRepository
from src.shared.logging import get_logger, log_event

LOGGER = get_logger(__name__)

def update_state(input_data: dict):
    video_id = input_data.get("video_id")
    method_name = input_data.get("method")
    kwargs = input_data.get("kwargs", {})
    
    if not video_id or not method_name:
        raise ValueError("video_id and method are required")

    log_event(LOGGER, f"update_state calling {method_name}", extra={"video_id": video_id})
    
    repo = IngestionStateRepository()
    
    method = getattr(repo, method_name, None)
    if not method:
        raise ValueError(f"Method {method_name} not found on IngestionStateRepository")
        
    return method(video_id=video_id, **kwargs)
