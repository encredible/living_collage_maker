"""하단 패널

선택된 가구를 표시하고 관리하는 BottomPanel과 SelectedFurniturePanel 클래스를 포함합니다.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QTableView, QVBoxLayout, QWidget

from .common import SelectedFurnitureTableModel


class SelectedFurniturePanel(QWidget):
    """선택된 가구 목록을 표시하는 패널"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # 선택된 가구 테이블
        self.selected_model = SelectedFurnitureTableModel()
        self.selected_table = QTableView()
        self.selected_table.setModel(self.selected_model)
        self.selected_table.setStyleSheet("""
            QTableView {
                border: 1px solid #ddd;
                background-color: white;
                gridline-color: #eee;
                selection-background-color: #e3f2fd;
                selection-color: #333;
            }
            QTableView::item {
                padding: 8px;
                border: none;
            }
            QTableView::item:selected {
                background-color: #e3f2fd;
                color: #333;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 8px;
                border: 1px solid #ddd;
                border-left: none;
                font-weight: bold;
                color: #333;
            }
            QHeaderView::section:first {
                border-left: 1px solid #ddd;
            }
        """)
        
        # 테이블 설정
        self.selected_table.horizontalHeader().setStretchLastSection(False)
        self.selected_table.verticalHeader().setVisible(False)
        self.selected_table.setShowGrid(True)
        self.selected_table.setGridStyle(Qt.PenStyle.SolidLine)
        self.selected_table.setAlternatingRowColors(True)
        self.selected_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.selected_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        
        # 컬럼 너비 설정 (14개 컬럼에 맞게 조정)
        header = self.selected_table.horizontalHeader()
        self.selected_table.setColumnWidth(0, 150)  # 이름
        self.selected_table.setColumnWidth(1, 120)  # 브랜드
        self.selected_table.setColumnWidth(2, 80)   # 타입
        self.selected_table.setColumnWidth(3, 100)  # 가격
        self.selected_table.setColumnWidth(4, 60)   # 개수
        self.selected_table.setColumnWidth(5, 120)  # 총 가격
        self.selected_table.setColumnWidth(6, 80)   # 색상
        self.selected_table.setColumnWidth(7, 120)  # 위치
        self.selected_table.setColumnWidth(8, 100)  # 스타일
        self.selected_table.setColumnWidth(9, 140)  # 크기
        self.selected_table.setColumnWidth(10, 80)  # 좌석높이
        self.selected_table.setColumnWidth(11, 200) # 설명
        self.selected_table.setColumnWidth(12, 150) # 링크
        self.selected_table.setColumnWidth(13, 100) # 작성자
        
        # 마지막 컬럼은 stretch하지 않도록 설정
        header.setStretchLastSection(False)
        
        # 높이 제한
        self.selected_table.setMaximumHeight(200)
        self.selected_table.setMinimumHeight(150)
        
        # 더블클릭 이벤트 연결
        self.selected_table.doubleClicked.connect(self.on_double_click)
        
        layout.addWidget(self.selected_table)
        
        # 구분선 추가
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("""
            QFrame {
                color: #ddd;
                background-color: #ddd;
                height: 1px;
                margin: 5px 0;
            }
        """)
        layout.addWidget(separator)
        
        print("[선택된 가구 패널] 초기화 완료")
    
    def on_double_click(self, index):
        """테이블 아이템 더블클릭 시 처리"""
        if index.isValid():
            # 여기에 더블클릭 처리 로직 추가 가능
            print(f"[선택된 가구 패널] 더블클릭: {index.row()}행")
    
    def update_furniture_list(self, furniture_items):
        """선택된 가구 목록을 업데이트합니다."""
        print(f"[선택된 가구 패널] 가구 목록 업데이트 시작, 아이템 수: {len(furniture_items)}")
        
        # 기존 데이터 초기화
        self.selected_model.clear_furniture()
        
        # 가구별 개수 집계
        furniture_count = {}
        for item in furniture_items:
            if hasattr(item, 'furniture'):
                furniture = item.furniture
                furniture_key = f"{furniture.name}_{furniture.brand}"
                
                if furniture_key in furniture_count:
                    furniture_count[furniture_key]['count'] += 1
                else:
                    furniture_count[furniture_key] = {
                        'furniture': furniture,
                        'count': 1
                    }
        
        # 집계된 데이터를 모델에 추가
        for item_info in furniture_count.values():
            furniture = item_info['furniture']
            count = item_info['count']
            
            # 개수만큼 모델에 추가 (내부적으로 집계됨)
            for _ in range(count):
                self.selected_model.add_furniture(furniture)
        
        print(f"[선택된 가구 패널] 가구 목록 업데이트 완료, 총 {len(furniture_count)}개 타입")


class BottomPanel(QWidget):
    """하단 패널 - 선택된 가구들을 표시하는 메인 패널"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("bottom_panel")
        self.setup_ui()
        print("[하단패널] 초기화 완료")
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 선택된 가구 패널
        self.selected_panel = SelectedFurniturePanel()
        layout.addWidget(self.selected_panel)
    
    def update_panel(self, items):
        """하단 패널을 업데이트합니다."""
        print(f"[하단패널] 업데이트 시작, 아이템 수: {len(items)}")
        self.selected_panel.update_furniture_list(items)
        print("[하단패널] 업데이트 완료") 