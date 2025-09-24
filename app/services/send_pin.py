import json
from collections import defaultdict
from dataclasses import dataclass

@dataclass
class SendPin:
    lat: float
    lon: float
    name: str

class SendPinStore:
    def __init__(self) -> None:
        self.data = defaultdict(list)

    def insert_pins(self, user_id: str, pin: SendPin) -> None:
        self.data[user_id].append({
            "type": "pin",
            "lat": pin.lat,
            "lon": pin.lon,
            "name": pin.name
        })

    def extract_pins(self, user_id: str) -> list[str]:
        if user_id not in self.data:
            return []
    
        pins: list[str] = []
        while self.data[user_id]:
            pins.append(f"data: {json.dumps(self.data[user_id].pop())}\n\n")
        return pins