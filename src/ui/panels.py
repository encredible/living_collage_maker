"""패널 모듈 (하위 호환성)

이 파일은 기존 코드와의 하위 호환성을 위해 유지되며,
새로운 패널 패키지의 클래스들을 re-export합니다.

새로운 구조:
- src.ui.panels.explorer_panel: ExplorerPanel (우측 탐색 패널)
- src.ui.panels.bottom_panel: BottomPanel, SelectedFurniturePanel (하단 패널)
- src.ui.panels.common: 공통 구성요소들
"""

# 새로운 패널 패키지에서 클래스들을 import하여 re-export
from .panels.bottom_panel import BottomPanel, SelectedFurniturePanel
from .panels.common import (
    FurnitureItem,
    FurnitureTableModel,
    ImageLoaderThread,
    SelectedFurnitureTableModel
)
from .panels.explorer_panel import ExplorerPanel

# 하위 호환성을 위한 __all__ 정의
__all__ = [
    'ExplorerPanel',
    'BottomPanel',
    'SelectedFurniturePanel', 
    'FurnitureItem',
    'FurnitureTableModel',
    'SelectedFurnitureTableModel',
    'ImageLoaderThread'
] 