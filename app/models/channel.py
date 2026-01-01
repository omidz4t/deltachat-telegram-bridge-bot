from dataclasses import dataclass
from typing import Optional

@dataclass
class Channel:
    accid: int
    chat_id: int
    name: str
    link: Optional[str] = None
    photo_enabled: bool = True
    photo_message: str = "[Photo]"
    video_enabled: bool = True
    video_message: str = "[Video]"
    enabled: bool = True
