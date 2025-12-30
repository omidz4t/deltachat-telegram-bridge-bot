from dataclasses import dataclass
from typing import Optional

@dataclass
class Channel:
    accid: int
    chat_id: int
    name: str
    link: Optional[str] = None
