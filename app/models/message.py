from dataclasses import dataclass
from typing import Optional

@dataclass
class Message:
    telegram_msg_id: int
    dc_msg_id: Optional[int] = None
    text: Optional[str] = None
    media_path: Optional[str] = None
    media_type: Optional[str] = None # text, image, video
    id: Optional[int] = None
