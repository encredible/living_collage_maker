import json
import os
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from platformdirs import user_cache_dir

from src.models.furniture import Furniture


@dataclass
class WindowState:
    """윈도우 상태 정보"""
    width: int = 1200
    height: int = 800
    x: int = 100
    y: int = 100


@dataclass
class ColumnWidthState:
    """컬럼 너비 상태 정보"""
    explorer_panel: Dict[int, int] = None  # 탐색 패널 컬럼 너비
    bottom_panel: Dict[int, int] = None    # 하단 패널 컬럼 너비
    
    def __post_init__(self):
        if self.explorer_panel is None:
            self.explorer_panel = {
                0: 100,  # 썸네일
                1: 100,  # 브랜드
                2: 200,  # 이름
                3: 100,  # 가격
            }
        if self.bottom_panel is None:
            self.bottom_panel = {
                0: 300,  # 이름
                1: 120,  # 브랜드
                2: 80,   # 타입
                3: 100,  # 가격
                4: 80,   # 색상
                5: 120,  # 위치
                6: 100,  # 스타일
                7: 140,  # 크기
                8: 80,   # 좌석높이
                9: 200,  # 설명
                10: 150, # 링크
                11: 100, # 작성자
                12: 60,  # 개수
            }


@dataclass
class CanvasState:
    """캔버스 상태 정보"""
    width: int = 800
    height: int = 600


@dataclass
class PanelState:
    """패널 크기 상태 정보"""
    horizontal_splitter_sizes: List[int] = None  # [캔버스 영역, 우측 패널]
    vertical_splitter_sizes: List[int] = None    # [상단 영역, 하단 패널]
    
    def __post_init__(self):
        if self.horizontal_splitter_sizes is None:
            self.horizontal_splitter_sizes = [800, 400]
        if self.vertical_splitter_sizes is None:
            self.vertical_splitter_sizes = [700, 100]


@dataclass
class FurnitureItemState:
    """가구 아이템 상태 정보"""
    furniture_id: str
    position_x: int
    position_y: int
    width: int
    height: int
    z_order: int = 0
    is_flipped: bool = False
    # 이미지 조정 정보
    color_temperature: int = 6500
    brightness: int = 100
    saturation: int = 100


@dataclass
class AppState:
    """전체 애플리케이션 상태"""
    window: WindowState = None
    column_widths: ColumnWidthState = None
    canvas: CanvasState = None
    panels: PanelState = None
    furniture_items: List[FurnitureItemState] = None
    
    def __post_init__(self):
        if self.window is None:
            self.window = WindowState()
        if self.column_widths is None:
            self.column_widths = ColumnWidthState()
        if self.canvas is None:
            self.canvas = CanvasState()
        if self.panels is None:
            self.panels = PanelState()
        if self.furniture_items is None:
            self.furniture_items = []


class AppStateService:
    """애플리케이션 상태 저장 및 복원 서비스"""
    
    def __init__(self):
        # 캐시 디렉토리 설정 (이미지 서비스와 같은 위치 사용)
        self.cache_dir = user_cache_dir("LivingCollageMaker", "LivingCollageMaker")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.state_file_path = os.path.join(self.cache_dir, "app_state.json")
    
    def save_app_state(self, app_state: AppState) -> bool:
        """애플리케이션 상태를 파일에 저장합니다."""
        try:
            state_dict = asdict(app_state)
            
            with open(self.state_file_path, 'w', encoding='utf-8') as f:
                json.dump(state_dict, f, ensure_ascii=False, indent=2)
            
            print(f"[AppStateService] 상태 저장 완료: {self.state_file_path}")
            return True
            
        except Exception as e:
            print(f"[AppStateService] 상태 저장 실패: {e}")
            return False
    
    def load_app_state(self) -> Optional[AppState]:
        """파일에서 애플리케이션 상태를 불러옵니다."""
        if not os.path.exists(self.state_file_path):
            print("[AppStateService] 저장된 상태 파일이 없습니다. 기본값 사용")
            return AppState()
        
        try:
            with open(self.state_file_path, 'r', encoding='utf-8') as f:
                state_dict = json.load(f)
            
            # 딕셔너리를 AppState 객체로 변환
            app_state = self._dict_to_app_state(state_dict)
            print(f"[AppStateService] 상태 불러오기 완료")  # 파일 경로 제거
            return app_state
            
        except Exception as e:
            print(f"[AppStateService] 상태 불러오기 실패: {e}")
            return AppState()  # 기본값 반환
    
    def _dict_to_app_state(self, state_dict: Dict[str, Any]) -> AppState:
        """딕셔너리를 AppState 객체로 변환합니다."""
        try:
            # WindowState 변환
            window_data = state_dict.get('window', {})
            window_state = WindowState(**window_data)
            
            # ColumnWidthState 변환
            column_data = state_dict.get('column_widths', {})
            
            # 딕셔너리 키를 정수로 변환 (JSON에서 불러올 때 키가 문자열로 변환됨)
            explorer_panel_widths = {}
            if column_data.get('explorer_panel'):
                for key, value in column_data['explorer_panel'].items():
                    explorer_panel_widths[int(key)] = value
            
            bottom_panel_widths = {}
            if column_data.get('bottom_panel'):
                for key, value in column_data['bottom_panel'].items():
                    bottom_panel_widths[int(key)] = value
            
            column_state = ColumnWidthState(
                explorer_panel=explorer_panel_widths,
                bottom_panel=bottom_panel_widths
            )
            
            # CanvasState 변환
            canvas_data = state_dict.get('canvas', {})
            canvas_state = CanvasState(**canvas_data)
            
            # PanelState 변환
            panel_data = state_dict.get('panels', {})
            panel_state = PanelState(
                horizontal_splitter_sizes=panel_data.get('horizontal_splitter_sizes', [800, 400]),
                vertical_splitter_sizes=panel_data.get('vertical_splitter_sizes', [700, 100])
            )
            
            # FurnitureItemState 리스트 변환
            furniture_items_data = state_dict.get('furniture_items', [])
            furniture_items = []
            for item_data in furniture_items_data:
                furniture_item = FurnitureItemState(**item_data)
                furniture_items.append(furniture_item)
            
            return AppState(
                window=window_state,
                column_widths=column_state,
                canvas=canvas_state,
                panels=panel_state,
                furniture_items=furniture_items
            )
            
        except Exception as e:
            print(f"[AppStateService] 딕셔너리 변환 중 오류: {e}")
            return AppState()  # 기본값 반환
    
    def clear_app_state(self) -> bool:
        """저장된 애플리케이션 상태를 삭제합니다."""
        try:
            if os.path.exists(self.state_file_path):
                os.remove(self.state_file_path)
                print(f"[AppStateService] 상태 파일 삭제 완료: {self.state_file_path}")
            return True
            
        except Exception as e:
            print(f"[AppStateService] 상태 파일 삭제 실패: {e}")
            return False 