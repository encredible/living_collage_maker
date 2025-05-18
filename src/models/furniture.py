from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Furniture:
    id: str
    brand: str
    name: str
    description: str
    image_filename: str
    link: str
    price: int
    type: str
    color: str
    locations: List[str]
    styles: List[str]
    width: int
    depth: int
    height: int
    seat_height: Optional[int]
    author: str
    created_at: str 