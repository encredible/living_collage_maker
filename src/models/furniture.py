from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class Furniture:
    # 필수 필드
    id: str
    brand: str
    name: str
    image_filename: str
    price: int
    type: str
    
    # 선택적 필드 (기본값 설정)
    description: str = ''
    link: str = ''
    color: str = ''
    locations: List[str] = field(default_factory=list)
    styles: List[str] = field(default_factory=list)
    width: int = 0
    depth: int = 0
    height: int = 0
    seat_height: Optional[int] = None
    author: str = ''
    created_at: str = ''
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Furniture':
        """딕셔너리에서 Furniture 객체를 생성합니다."""
        # 필수 필드 검증
        required_fields = ['id', 'brand', 'name', 'image_filename', 'price', 'type']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"필수 필드가 누락되었습니다: {field}")
        
        # 데이터 타입 변환 및 기본값 설정
        processed_data = {
            'id': str(data['id']),
            'brand': str(data['brand']),
            'name': str(data['name']),
            'image_filename': str(data['image_filename']),
            'price': int(data['price']),
            'type': str(data['type']),
            'description': str(data.get('description', '')),
            'link': str(data.get('link', '')),
            'color': str(data.get('color', '')),
            'locations': list(data.get('locations', [])),
            'styles': list(data.get('styles', [])),
            'width': int(data.get('width', 0)),
            'depth': int(data.get('depth', 0)),
            'height': int(data.get('height', 0)),
            'seat_height': int(data['seat_height']) if data.get('seat_height') is not None else None,
            'author': str(data.get('author', '')),
            'created_at': str(data.get('created_at', ''))
        }
        
        return cls(**processed_data) 