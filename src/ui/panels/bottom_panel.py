"""하단 패널

선택된 가구를 표시하고 관리하는 BottomPanel과 SelectedFurniturePanel 클래스를 포함합니다.
"""

import webbrowser

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (QFrame, QTableView, QVBoxLayout, QWidget, QSizePolicy,
                             QHBoxLayout, QPushButton, QMenu)

from .common import SelectedFurnitureTableModel


class SelectedFurniturePanel(QWidget):
    """선택된 가구 목록을 표시하는 패널"""

    def __init__(self, parent=None):
        super().__init__(parent)
        # 컬럼 너비를 저장하는 딕셔너리 (기본값, 14개 컬럼)
        self.column_widths = {
            0: 50,   # 번호 (새로 추가)
            1: 300,  # 이름 (2배로 증가)
            2: 120,  # 브랜드
            3: 80,   # 타입
            4: 100,  # 가격
            5: 80,   # 색상
            6: 120,  # 위치
            7: 100,  # 스타일
            8: 140,  # 크기
            9: 80,   # 좌석높이
            10: 200, # 설명
            11: 150, # 링크
            12: 100, # 작성자
            13: 60,  # 개수 (맨 오른쪽)
        }
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # 순서 변경 버튼 영역 추가
        self.create_order_control_section(layout)

        # 선택된 가구 테이블
        self.selected_model = SelectedFurnitureTableModel()
        
        # 모델에 컬럼 너비 복원 콜백 설정
        self.selected_model.set_column_width_callback(self.setup_column_widths)
        
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

        # 드래그 앤 드롭 활성화
        self.selected_table.setDragDropMode(QTableView.DragDropMode.InternalMove)
        self.selected_table.setDragDropOverwriteMode(False)
        self.selected_table.setDefaultDropAction(Qt.DropAction.MoveAction)

        # 컬럼 너비 변경 감지 시그널 연결
        header = self.selected_table.horizontalHeader()
        header.sectionResized.connect(self.on_column_resized)

        # 테이블 선택 변경 시그널 연결
        self.selected_table.selectionModel().selectionChanged.connect(self.on_selection_changed)

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

    def create_order_control_section(self, layout):
        """순서 변경 컨트롤 영역을 생성합니다."""
        # 버튼 영역 컨테이너
        control_widget = QWidget()
        control_widget.setFixedHeight(40)  # 고정 높이
        control_widget.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                margin: 2px 0;
            }
        """)
        
        control_layout = QHBoxLayout(control_widget)
        control_layout.setContentsMargins(10, 5, 10, 5)
        control_layout.setSpacing(10)

        # 순서 변경 라벨
        from PyQt6.QtWidgets import QLabel
        order_label = QLabel("순서 변경:")
        order_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: #495057;
                border: none;
                background: none;
            }
        """)
        control_layout.addWidget(order_label)

        # 위로 이동 버튼
        self.move_up_btn = QPushButton("▲ 위로")
        self.move_up_btn.setFixedSize(80, 25)
        self.move_up_btn.setEnabled(False)
        self.move_up_btn.clicked.connect(self.move_selected_up)
        self.move_up_btn.setStyleSheet(self.get_button_style())
        control_layout.addWidget(self.move_up_btn)

        # 아래로 이동 버튼
        self.move_down_btn = QPushButton("▼ 아래로")
        self.move_down_btn.setFixedSize(80, 25)
        self.move_down_btn.setEnabled(False)
        self.move_down_btn.clicked.connect(self.move_selected_down)
        self.move_down_btn.setStyleSheet(self.get_button_style())
        control_layout.addWidget(self.move_down_btn)

        # 맨 위로 이동 버튼
        self.move_top_btn = QPushButton("⬆ 맨 위로")
        self.move_top_btn.setFixedSize(80, 25)
        self.move_top_btn.setEnabled(False)
        self.move_top_btn.clicked.connect(self.move_selected_to_top)
        self.move_top_btn.setStyleSheet(self.get_button_style())
        control_layout.addWidget(self.move_top_btn)

        # 맨 아래로 이동 버튼
        self.move_bottom_btn = QPushButton("⬇ 맨 아래로")
        self.move_bottom_btn.setFixedSize(80, 25)
        self.move_bottom_btn.setEnabled(False)
        self.move_bottom_btn.clicked.connect(self.move_selected_to_bottom)
        self.move_bottom_btn.setStyleSheet(self.get_button_style())
        control_layout.addWidget(self.move_bottom_btn)

        # 정렬 버튼
        self.sort_btn = QPushButton("🔄 정렬")
        self.sort_btn.setFixedSize(60, 25)
        self.sort_btn.clicked.connect(self.show_sort_menu)
        self.sort_btn.setStyleSheet(self.get_button_style())
        control_layout.addWidget(self.sort_btn)

        # 스페이서 추가
        control_layout.addStretch()

        # 컨트롤 영역을 고정 크기로 추가
        layout.addWidget(control_widget, 0)

    def get_button_style(self):
        """버튼 스타일을 반환합니다."""
        return """
            QPushButton {
                background-color: #007bff;
                border: 1px solid #007bff;
                color: white;
                border-radius: 3px;
                font-size: 12px;
                font-weight: bold;
                padding: 2px 8px;
            }
            QPushButton:hover {
                background-color: #0056b3;
                border-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
                border-color: #004085;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                border-color: #6c757d;
                color: #ffffff;
            }
        """

    def on_selection_changed(self):
        """테이블 선택이 변경될 때 버튼 상태를 업데이트합니다."""
        current_row = self.get_selected_row()
        has_selection = current_row >= 0
        row_count = self.selected_model.rowCount()

        # 버튼 활성화/비활성화
        self.move_up_btn.setEnabled(has_selection and current_row > 0)
        self.move_down_btn.setEnabled(has_selection and current_row < row_count - 1)
        self.move_top_btn.setEnabled(has_selection and current_row > 0)
        self.move_bottom_btn.setEnabled(has_selection and current_row < row_count - 1)

    def get_selected_row(self):
        """현재 선택된 행 번호를 반환합니다."""
        selection = self.selected_table.selectionModel().selectedRows()
        if selection:
            return selection[0].row()
        return -1

    def get_selected_furniture_name(self):
        """현재 선택된 가구의 이름을 반환합니다."""
        row = self.get_selected_row()
        if row >= 0:
            return self.selected_model.get_furniture_name_at_row(row)
        return None

    def move_selected_up(self):
        """선택된 가구를 위로 이동합니다."""
        furniture_name = self.get_selected_furniture_name()
        if furniture_name:
            new_row = self.selected_model.move_furniture_up(furniture_name)
            if new_row >= 0:
                # 모델 업데이트 완료 후 선택 복원 (약간의 지연을 두어 모델 업데이트 완료 대기)
                QTimer.singleShot(0, lambda: self.select_row(new_row))

    def move_selected_down(self):
        """선택된 가구를 아래로 이동합니다."""
        furniture_name = self.get_selected_furniture_name()
        if furniture_name:
            new_row = self.selected_model.move_furniture_down(furniture_name)
            if new_row >= 0:
                QTimer.singleShot(0, lambda: self.select_row(new_row))

    def move_selected_to_top(self):
        """선택된 가구를 맨 위로 이동합니다."""
        furniture_name = self.get_selected_furniture_name()
        if furniture_name:
            new_row = self.selected_model.move_furniture_to_top(furniture_name)
            if new_row >= 0:
                QTimer.singleShot(0, lambda: self.select_row(new_row))

    def move_selected_to_bottom(self):
        """선택된 가구를 맨 아래로 이동합니다."""
        furniture_name = self.get_selected_furniture_name()
        if furniture_name:
            new_row = self.selected_model.move_furniture_to_bottom(furniture_name)
            if new_row >= 0:
                QTimer.singleShot(0, lambda: self.select_row(new_row))

    def show_sort_menu(self):
        """정렬 옵션 메뉴를 표시합니다."""
        menu = QMenu(self)
        
        # 정렬 옵션들
        sort_options = [
            ("이름 (가나다순)", "name", True),
            ("이름 (가나다 역순)", "name", False),
            ("브랜드 (가나다순)", "brand", True),
            ("브랜드 (가나다 역순)", "brand", False),
            ("가격 (낮은순)", "price", True),
            ("가격 (높은순)", "price", False),
            ("타입 (가나다순)", "type", True),
            ("타입 (가나다 역순)", "type", False),
        ]
        
        for text, sort_by, ascending in sort_options:
            action = menu.addAction(text)
            action.triggered.connect(lambda checked, sb=sort_by, asc=ascending: self.sort_furniture(sb, asc))
        
        # 버튼 위치에서 메뉴 표시
        menu.exec(self.sort_btn.mapToGlobal(self.sort_btn.rect().bottomLeft()))

    def sort_furniture(self, sort_by: str, ascending: bool):
        """가구를 정렬합니다."""
        self.selected_model.sort_furniture(sort_by, ascending)
        # 정렬 후 첫 번째 행 선택 (약간의 지연을 두어 모델 업데이트 완료 대기)
        if self.selected_model.rowCount() > 0:
            QTimer.singleShot(0, lambda: self.select_row(0))

    def select_row(self, row: int):
        """지정된 행을 선택합니다."""
        if 0 <= row < self.selected_model.rowCount():
            index = self.selected_model.index(row, 0)
            self.selected_table.selectRow(row)
            self.selected_table.scrollTo(index)

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
            # 링크 컬럼(11번 컬럼)을 클릭한 경우 웹 브라우저로 링크 열기
            if index.column() == 11:  # 링크 컬럼
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
