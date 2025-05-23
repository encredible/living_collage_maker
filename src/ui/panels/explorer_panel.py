"""우측 탐색 패널

가구 탐색, 검색, 필터링 기능을 제공하는 ExplorerPanel 클래스를 포함합니다.
"""

from PyQt6.QtCore import QMimeData, Qt, pyqtSignal
from PyQt6.QtGui import QDrag
from PyQt6.QtWidgets import (QComboBox, QGridLayout, QHBoxLayout, QLabel,
                             QLineEdit, QTableView, QVBoxLayout, QWidget)

from src.models.furniture import Furniture
from src.services.supabase_client import SupabaseClient
from .common import FurnitureTableModel


class ExplorerPanel(QWidget):
    """가구 탐색 및 필터링을 위한 우측 패널"""
    
    furniture_selected = pyqtSignal(Furniture)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.supabase = SupabaseClient()
        self.setup_ui()
        self.load_furniture_data()  # 초기 데이터 로드
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 검색 및 필터 영역
        filter_layout = QGridLayout()
        filter_layout.setSpacing(10)
        
        # 검색 입력
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("가구 검색...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }
        """)
        self.search_input.textChanged.connect(self.filter_furniture)
        filter_layout.addWidget(self.search_input, 0, 0, 1, 3)
        
        # 필터 스타일
        filter_style = """
            QComboBox {
                padding: 6px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }
            QLabel {
                font-size: 14px;
                color: #666;
            }
        """
        
        # 첫 번째 행: 브랜드, 타입, 가격
        self.brand_filter = QComboBox()
        self.brand_filter.addItem("전체 브랜드")
        self.brand_filter.setStyleSheet(filter_style)
        self.brand_filter.currentTextChanged.connect(self.filter_furniture)
        filter_layout.addWidget(QLabel("브랜드:"), 1, 0)
        filter_layout.addWidget(self.brand_filter, 1, 1)
        
        self.type_filter = QComboBox()
        self.type_filter.addItem("전체 타입")
        self.type_filter.setStyleSheet(filter_style)
        self.type_filter.currentTextChanged.connect(self.filter_furniture)
        filter_layout.addWidget(QLabel("타입:"), 1, 2)
        filter_layout.addWidget(self.type_filter, 1, 3)
        
        # 가격 필터를 QLineEdit 두 개로 변경
        price_filter_layout = QHBoxLayout()
        price_filter_layout.setSpacing(5)
        
        self.min_price_input = QLineEdit()
        self.min_price_input.setPlaceholderText("최소 가격")
        self.min_price_input.setStyleSheet("""
            QLineEdit {
                padding: 6px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
                width: 80px;
            }
        """)
        self.min_price_input.textChanged.connect(self.filter_furniture)
        
        price_label = QLabel("~")
        price_label.setStyleSheet("font-size: 14px; color: #666;")
        
        self.max_price_input = QLineEdit()
        self.max_price_input.setPlaceholderText("최대 가격")
        self.max_price_input.setStyleSheet("""
            QLineEdit {
                padding: 6px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
                width: 80px;
            }
        """)
        self.max_price_input.textChanged.connect(self.filter_furniture)
        
        price_filter_layout.addWidget(self.min_price_input)
        price_filter_layout.addWidget(price_label)
        price_filter_layout.addWidget(self.max_price_input)
        
        price_widget = QWidget()
        price_widget.setLayout(price_filter_layout)
        
        filter_layout.addWidget(QLabel("가격:"), 1, 4)
        filter_layout.addWidget(price_widget, 1, 5)
        
        # 두 번째 행: 색상, 위치, 스타일
        self.color_filter = QComboBox()
        self.color_filter.addItem("전체 색상")
        self.color_filter.setStyleSheet(filter_style)
        self.color_filter.currentTextChanged.connect(self.filter_furniture)
        filter_layout.addWidget(QLabel("색상:"), 2, 0)
        filter_layout.addWidget(self.color_filter, 2, 1)
        
        self.location_filter = QComboBox()
        self.location_filter.addItem("전체 위치")
        self.location_filter.setStyleSheet(filter_style)
        self.location_filter.currentTextChanged.connect(self.filter_furniture)
        filter_layout.addWidget(QLabel("위치:"), 2, 2)
        filter_layout.addWidget(self.location_filter, 2, 3)
        
        self.style_filter = QComboBox()
        self.style_filter.addItem("전체 스타일")
        self.style_filter.setStyleSheet(filter_style)
        self.style_filter.currentTextChanged.connect(self.filter_furniture)
        filter_layout.addWidget(QLabel("스타일:"), 2, 4)
        filter_layout.addWidget(self.style_filter, 2, 5)
        
        layout.addLayout(filter_layout)
        
        # 가구 목록 테이블
        self.furniture_model = FurnitureTableModel()
        self.furniture_table = QTableView()
        self.furniture_table.setModel(self.furniture_model)
        self.furniture_table.setStyleSheet("""
            QTableView {
                border: none;
                background-color: white;
            }
            QTableView::item {
                border-bottom: 1px solid #eee;
                padding: 5px;
            }
        """)
        self.furniture_table.horizontalHeader().setStretchLastSection(True)
        self.furniture_table.verticalHeader().setVisible(False)
        self.furniture_table.setShowGrid(False)
        self.furniture_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.furniture_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.furniture_table.setDragEnabled(True)
        self.furniture_table.setDragDropMode(QTableView.DragDropMode.DragOnly)
        
        # 컬럼 크기 설정
        self.furniture_table.setColumnWidth(0, 100)  # 썸네일 컬럼
        self.furniture_table.setColumnWidth(1, 100)  # 브랜드 컬럼
        self.furniture_table.setColumnWidth(2, 200)  # 이름 컬럼
        self.furniture_table.setColumnWidth(3, 100)  # 가격 컬럼
        
        # 셀 수정 비활성화
        self.furniture_table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.furniture_table)
    
    def load_furniture_data(self):
        """Supabase에서 가구 데이터를 로드합니다."""
        try:
            print("가구 데이터 로딩 시작...")
            
            # Supabase에서 가구 데이터 조회 (모든 필드 선택)
            response = self.supabase.client.table('furniture').select(
                'id,name,brand,type,price,image_filename,description,link,color,locations,styles,width,depth,height,seat_height,author,created_at'
            ).execute()
            
            print(f"데이터 개수: {len(response.data) if response.data else 0}")
            
            if response.data:
                # 기존 데이터 초기화
                self.furniture_model.clear_furniture()
                
                # 필터 옵션 초기화
                self.brand_filter.clear()
                self.brand_filter.addItem("전체 브랜드")
                self.type_filter.clear()
                self.type_filter.addItem("전체 타입")
                self.color_filter.clear()
                self.color_filter.addItem("전체 색상")
                self.location_filter.clear()
                self.location_filter.addItem("전체 위치")
                self.style_filter.clear()
                self.style_filter.addItem("전체 스타일")
                
                # 데이터 추가
                for item in response.data:
                    try:
                        # Furniture 객체 생성
                        furniture = Furniture.from_dict(item)
                        self.furniture_model.add_furniture(furniture)
                        
                        # 필터 옵션 업데이트
                        if furniture.brand and furniture.brand not in [self.brand_filter.itemText(i) for i in range(1, self.brand_filter.count())]:
                            self.brand_filter.addItem(furniture.brand)
                        if furniture.type and furniture.type not in [self.type_filter.itemText(i) for i in range(1, self.type_filter.count())]:
                            self.type_filter.addItem(furniture.type)
                        if furniture.color and furniture.color not in [self.color_filter.itemText(i) for i in range(1, self.color_filter.count())]:
                            self.color_filter.addItem(furniture.color)
                        for location in furniture.locations:
                            if location not in [self.location_filter.itemText(i) for i in range(1, self.location_filter.count())]:
                                self.location_filter.addItem(location)
                        for style in furniture.styles:
                            if style not in [self.style_filter.itemText(i) for i in range(1, self.style_filter.count())]:
                                self.style_filter.addItem(style)
                            
                    except Exception as e:
                        print(f"개별 가구 데이터 처리 중 오류 발생: {str(e)}")
                        print(f"문제가 된 데이터: {item}")
                        import traceback
                        print(traceback.format_exc())
                        continue
                
                print(f"총 {self.furniture_model.rowCount()}개의 가구 데이터가 로드되었습니다.")
            else:
                print("가구 데이터가 없습니다.")
            
        except Exception as e:
            print(f"가구 데이터 로드 중 오류 발생: {str(e)}")
            import traceback
            print(traceback.format_exc())
    
    def __del__(self):
        """패널이 삭제될 때 로딩 중인 스레드 정리"""
        if hasattr(self, 'furniture_model'):
            self.furniture_model.clear_furniture()
    
    def filter_furniture(self):
        """가구 목록을 필터링합니다."""
        search_text = self.search_input.text().lower()
        selected_brand = self.brand_filter.currentText()
        selected_type = self.type_filter.currentText()
        selected_color = self.color_filter.currentText()
        selected_location = self.location_filter.currentText()
        selected_style = self.style_filter.currentText()
        
        # 가격 필터 값 가져오기
        min_price = self.min_price_input.text().strip()
        max_price = self.max_price_input.text().strip()
        
        for row in range(self.furniture_model.rowCount()):
            furniture = self.furniture_model.furniture_items[row]
            show_item = True
            
            # 검색어 필터링
            if search_text:
                if (search_text not in furniture.name.lower() and 
                    search_text not in furniture.brand.lower() and 
                    search_text not in furniture.description.lower()):
                    show_item = False
            
            # 브랜드 필터링
            if selected_brand != "전체 브랜드" and furniture.brand != selected_brand:
                show_item = False
            
            # 타입 필터링
            if selected_type != "전체 타입" and furniture.type != selected_type:
                show_item = False
            
            # 가격 필터링
            price = furniture.price
            if min_price:
                try:
                    min_val = int(min_price)
                    if price < min_val:
                        show_item = False
                except ValueError:
                    pass
            if max_price:
                try:
                    max_val = int(max_price)
                    if price > max_val:
                        show_item = False
                except ValueError:
                    pass
            
            # 색상 필터링
            if selected_color != "전체 색상" and furniture.color != selected_color:
                show_item = False
            
            # 위치 필터링
            if selected_location != "전체 위치" and selected_location not in furniture.locations:
                show_item = False
            
            # 스타일 필터링
            if selected_style != "전체 스타일" and selected_style not in furniture.styles:
                show_item = False
            
            # 아이템 표시/숨김
            self.furniture_table.setRowHidden(row, not show_item)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # 선택된 행의 인덱스 가져오기
            index = self.furniture_table.indexAt(event.pos())
            if index.isValid():
                # 해당 행의 가구 데이터 가져오기
                furniture = self.furniture_model.furniture_items[index.row()]
                
                # 드래그 시작
                drag = QDrag(self)
                mime_data = QMimeData()
                
                # 드래그 데이터 설정
                furniture_data = {
                    'id': furniture.id,
                    'name': furniture.name,
                    'image_filename': furniture.image_filename,
                    'price': furniture.price,
                    'brand': furniture.brand,
                    'type': furniture.type,
                    'description': furniture.description,
                    'link': furniture.link,
                    'color': furniture.color,
                    'locations': furniture.locations,
                    'styles': furniture.styles,
                    'width': furniture.width,
                    'depth': furniture.depth,
                    'height': furniture.height,
                    'seat_height': furniture.seat_height,
                    'author': furniture.author,
                    'created_at': furniture.created_at
                }
                
                # MIME 데이터 설정
                mime_data.setData("application/x-furniture", str(furniture_data).encode())
                drag.setMimeData(mime_data)
                
                # 드래그 시작
                drag.exec() 