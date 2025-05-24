"""하단 패널

선택된 가구를 표시하고 관리하는 BottomPanel과 SelectedFurniturePanel 클래스를 포함합니다.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QTableView, QVBoxLayout, QWidget, QSizePolicy
import webbrowser

from .common import SelectedFurnitureTableModel


class SelectedFurniturePanel(QWidget):
    """선택된 가구 목록을 표시하는 패널"""

    def __init__(self, parent=None):
        super().__init__(parent)
        # 컬럼 너비를 저장하는 딕셔너리 (기본값, 13개 컬럼)
        self.column_widths = {
            0: 300,  # 이름 (2배로 증가)
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
            12: 60,  # 개수 (맨 오른쪽)
        }
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

        # 테이블 편집 방지
        self.selected_table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)

        # 컬럼 너비 변경 감지 시그널 연결
        header = self.selected_table.horizontalHeader()
        header.sectionResized.connect(self.on_column_resized)

        # 초기 컬럼 너비 설정
        self.setup_column_widths()

        # 테이블 크기 정책 설정 - 하단 패널 크기에 따라 동적 조정
        size_policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.selected_table.setSizePolicy(size_policy)
        
        # 최소 높이만 설정 (최대 높이 제한 제거하여 동적 크기 조정 가능)
        self.selected_table.setMinimumHeight(100)  # 최소 높이를 100으로 줄임

        # 더블클릭 이벤트 연결
        self.selected_table.doubleClicked.connect(self.on_double_click)

        # 테이블을 레이아웃에 추가 (stretch factor 1로 설정하여 확장 가능)
        layout.addWidget(self.selected_table, 1)

        # 총계 표시 영역 추가 (stretch factor 0으로 고정 크기 유지)
        self.create_summary_section(layout)

        print("[선택된 가구 패널] 초기화 완료")

    def create_summary_section(self, layout):
        """총계 표시 영역을 생성합니다."""
        from PyQt6.QtWidgets import QHBoxLayout, QLabel

        # 총계 영역 컨테이너
        summary_widget = QWidget()
        # 높이 고정 설정
        summary_widget.setFixedHeight(50)  # 고정 높이 설정
        summary_widget.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                margin: 5px 0;
            }
        """)
        summary_layout = QHBoxLayout(summary_widget)
        summary_layout.setContentsMargins(15, 10, 15, 10)

        # 총 가구 개수 라벨
        self.total_count_label = QLabel("총 가구: 0개")
        self.total_count_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 14px;
                color: #495057;
                border: none;
            }
        """)

        # 총 가격 라벨
        self.total_price_label = QLabel("총 가격: ₩0")
        self.total_price_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 14px;
                color: #495057;
                border: none;
            }
        """)

        # 스페이서 추가하여 오른쪽 정렬
        summary_layout.addWidget(self.total_count_label)
        summary_layout.addStretch()
        summary_layout.addWidget(self.total_price_label)

        # 총계 영역을 고정 크기로 추가 (stretch factor 0)
        layout.addWidget(summary_widget, 0)

        # 구분선 추가
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        # 구분선도 고정 높이 설정
        separator.setFixedHeight(10)  # 구분선 고정 높이
        separator.setStyleSheet("""
            QFrame {
                color: #ddd;
                background-color: #ddd;
                height: 1px;
                margin: 5px 0;
            }
        """)
        # 구분선도 고정 크기로 추가 (stretch factor 0)
        layout.addWidget(separator, 0)

    def on_column_resized(self, logical_index, old_size, new_size):
        """컬럼 너비가 변경될 때 호출되는 메서드"""
        # 변경된 컬럼 너비를 저장
        self.column_widths[logical_index] = new_size
        print(f"[컬럼 너비 변경] 컬럼 {logical_index}: {old_size} -> {new_size}")

    def setup_column_widths(self):
        """저장된 컬럼 너비를 적용하는 메서드"""
        header = self.selected_table.horizontalHeader()

        # 저장된 너비로 각 컬럼 설정
        for column_index, width in self.column_widths.items():
            self.selected_table.setColumnWidth(column_index, width)

        # 마지막 컬럼은 stretch하지 않도록 설정
        header.setStretchLastSection(False)

    def update_summary(self):
        """총계 정보를 업데이트합니다."""
        total_count = self.selected_model.get_total_count()
        total_price = self.selected_model.get_total_price()

        self.total_count_label.setText(f"총 가구: {total_count}개")
        self.total_price_label.setText(f"총 가격: ₩{total_price:,}")

    def on_double_click(self, index):
        """테이블 아이템 더블클릭 시 처리"""
        if index.isValid():
            # 링크 컬럼(10번 컬럼)을 클릭한 경우 웹 브라우저로 링크 열기
            if index.column() == 10:  # 링크 컬럼
                link_text = self.selected_model.data(index, Qt.ItemDataRole.DisplayRole)
                if link_text and link_text.strip():
                    print(f"[선택된 가구 패널] 링크 열기: {link_text}")
                    webbrowser.open(link_text)
                else:
                    print("[선택된 가구 패널] 링크가 비어 있습니다.")
            else:
                print(f"[선택된 가구 패널] 더블클릭: {index.row()}행, {index.column()}열")

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

        # 모델 업데이트 후 컬럼 너비 재설정 및 총계 업데이트
        self.setup_column_widths()
        self.update_summary()

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
