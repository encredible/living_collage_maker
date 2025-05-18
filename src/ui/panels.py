from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QScrollArea, QPushButton,
                             QComboBox, QGridLayout, QTableView, QFrame)
from PyQt6.QtCore import Qt, QSize, QMimeData, pyqtSignal, QAbstractTableModel, QModelIndex
from PyQt6.QtGui import QPixmap, QDrag, QStandardItemModel, QStandardItem, QPainter, QPen, QColor
from models.furniture import Furniture
from services.image_service import ImageService
from services.supabase_client import SupabaseClient

class FurnitureItem(QWidget):
    def __init__(self, furniture: Furniture, parent=None):
        super().__init__(parent)
        self.furniture = furniture
        self.image_service = ImageService()
        self.supabase = SupabaseClient()
        self.setup_ui()
        self.load_image()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        
        # 썸네일 이미지
        self.image_label = QLabel()
        self.image_label.setFixedSize(100, 100)  # 이미지 크기 증가
        self.image_label.setStyleSheet("""
            QLabel {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #f8f9fa;
            }
        """)
        layout.addWidget(self.image_label)
        
        # 가구 정보
        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)
        
        # 이름
        name_label = QLabel(self.furniture.name)
        name_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 15px;
                color: #2C3E50;
            }
        """)
        info_layout.addWidget(name_label)
        
        # 브랜드
        brand_label = QLabel(self.furniture.brand)
        brand_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #666;
            }
        """)
        info_layout.addWidget(brand_label)
        
        # 타입
        type_label = QLabel(self.furniture.type)
        type_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #666;
            }
        """)
        info_layout.addWidget(type_label)
        
        # 가격
        price_label = QLabel(f"₩{self.furniture.price:,}")
        price_label.setStyleSheet("""
            QLabel {
                font-size: 15px;
                color: #2C3E50;
                font-weight: bold;
            }
        """)
        info_layout.addWidget(price_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # 드래그 시작 설정
        self.setMouseTracking(True)
        
        # 최소 높이 설정
        self.setMinimumHeight(140)  # 썸네일 + 여백을 고려한 높이
    
    def load_image(self):
        """가구 이미지를 로드합니다."""
        try:
            # Supabase에서 이미지 다운로드
            image_data = self.supabase.get_furniture_image(self.furniture.image_filename)
            
            # 이미지 캐시 및 썸네일 생성
            pixmap = self.image_service.download_and_cache_image(
                image_data, 
                self.furniture.image_filename
            )
            thumbnail = self.image_service.create_thumbnail(pixmap, (100, 100))  # 썸네일 크기 증가
            
            # 썸네일 표시
            self.image_label.setPixmap(thumbnail)
            self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
        except Exception as e:
            print(f"이미지 로드 중 오류 발생: {e}")
            # 에러 이미지 표시
            self.image_label.setText("이미지 로드 실패")
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            
            # 드래그 데이터 설정
            furniture_data = {
                'id': self.furniture.id,
                'name': self.furniture.name,
                'image_filename': self.furniture.image_filename,
                'price': self.furniture.price,
                'brand': self.furniture.brand,
                'type': self.furniture.type,
                'description': self.furniture.description,
                'link': self.furniture.link,
                'color': self.furniture.color,
                'locations': self.furniture.locations,
                'styles': self.furniture.styles,
                'width': self.furniture.width,
                'depth': self.furniture.depth,
                'height': self.furniture.height,
                'seat_height': self.furniture.seat_height,
                'author': self.furniture.author,
                'created_at': self.furniture.created_at
            }
            
            # MIME 데이터 설정
            mime_data.setData("application/x-furniture", str(furniture_data).encode())
            drag.setMimeData(mime_data)
            
            # 드래그 시작
            drag.exec()

class FurnitureTableModel(QStandardItemModel):
    def __init__(self):
        super().__init__()
        self.setHorizontalHeaderLabels(["썸네일", "브랜드", "이름", "가격"])
        self.furniture_items = []
        self.image_service = ImageService()
        self.supabase = SupabaseClient()
        self.thumbnail_cache = {}
    
    def mimeTypes(self):
        return ["application/x-furniture"]
    
    def mimeData(self, indexes):
        mime_data = QMimeData()
        if not indexes:
            return mime_data
            
        # 선택된 행의 가구 데이터 가져오기
        row = indexes[0].row()
        if row < len(self.furniture_items):
            furniture = self.furniture_items[row]
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
            mime_data.setData("application/x-furniture", str(furniture_data).encode())
        return mime_data
    
    def add_furniture(self, furniture: Furniture):
        # 썸네일 아이템
        thumbnail_item = QStandardItem()
        thumbnail = self.get_thumbnail(furniture)
        thumbnail_item.setData(thumbnail, Qt.ItemDataRole.DecorationRole)
        thumbnail_item.setEditable(False)
        thumbnail_item.setData(furniture, Qt.ItemDataRole.UserRole)  # 가구 데이터 저장
        
        # 브랜드 아이템
        brand_item = QStandardItem(furniture.brand)
        brand_item.setEditable(False)
        brand_item.setData(furniture, Qt.ItemDataRole.UserRole)  # 가구 데이터 저장
        
        # 이름 아이템
        name_item = QStandardItem(furniture.name)
        name_item.setEditable(False)
        name_item.setData(furniture, Qt.ItemDataRole.UserRole)  # 가구 데이터 저장
        
        # 가격 아이템
        price_item = QStandardItem(f"₩{furniture.price:,}")
        price_item.setEditable(False)
        price_item.setData(furniture, Qt.ItemDataRole.UserRole)  # 가구 데이터 저장
        
        # 행 추가
        self.appendRow([thumbnail_item, brand_item, name_item, price_item])
        self.furniture_items.append(furniture)
    
    def get_thumbnail(self, furniture: Furniture):
        """가구의 썸네일 이미지를 가져옵니다."""
        # 캐시된 썸네일이 있는지 확인
        if furniture.image_filename in self.thumbnail_cache:
            return self.thumbnail_cache[furniture.image_filename]
        
        try:
            # Supabase에서 이미지 다운로드
            image_data = self.supabase.get_furniture_image(furniture.image_filename)
            
            # 이미지 캐시 및 썸네일 생성
            pixmap = self.image_service.download_and_cache_image(
                image_data, 
                furniture.image_filename
            )
            thumbnail = self.image_service.create_thumbnail(pixmap, QSize(100, 100))
            
            # 썸네일 캐시에 저장
            self.thumbnail_cache[furniture.image_filename] = thumbnail
            
            return thumbnail
        except Exception as e:
            print(f"썸네일 생성 중 오류 발생: {e}")
            # 에러 이미지 생성
            error_pixmap = QPixmap(100, 100)
            error_pixmap.fill(QColor("#f0f0f0"))
            painter = QPainter(error_pixmap)
            painter.setPen(QPen(QColor("#2C3E50")))
            painter.drawText(error_pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "이미지 로드 실패")
            painter.end()
            return error_pixmap
    
    def clear_furniture(self):
        self.removeRows(0, self.rowCount())
        self.furniture_items.clear()
        self.thumbnail_cache.clear()  # 캐시 초기화

class SelectedFurnitureTableModel(QStandardItemModel):
    def __init__(self):
        super().__init__()
        self.setHorizontalHeaderLabels(["브랜드", "이름", "가격", ""])
        self.furniture_items = []
    
    def add_furniture(self, furniture: Furniture):
        row = [QStandardItem(furniture.brand),
               QStandardItem(furniture.name),
               QStandardItem(f"₩{furniture.price:,}"),
               QStandardItem("")]  # 삭제 버튼을 위한 빈 셀
        self.appendRow(row)
        self.furniture_items.append(furniture)
    
    def clear_furniture(self):
        self.removeRows(0, self.rowCount())
        self.furniture_items.clear()

class ExplorerPanel(QWidget):
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
        
        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        
        # 새 콜라주 버튼
        new_collage_btn = QPushButton("새 콜라주 만들기")
        new_collage_btn.setStyleSheet("""
            QPushButton {
                background-color: #2C3E50;
                color: white;
                border: none;
                padding: 10px;
                font-size: 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #34495E;
            }
        """)
        new_collage_btn.clicked.connect(self.create_new_collage)
        button_layout.addWidget(new_collage_btn)
        
        # 내보내기 버튼
        export_btn = QPushButton("콜라주 내보내기")
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                border: none;
                padding: 10px;
                font-size: 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2ECC71;
            }
        """)
        export_btn.clicked.connect(self.export_collage)
        button_layout.addWidget(export_btn)
        
        layout.addLayout(button_layout)
        
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
        filter_layout.addWidget(self.search_input, 0, 0, 1, 2)
        
        # 브랜드 필터
        self.brand_filter = QComboBox()
        self.brand_filter.addItem("전체 브랜드")
        self.brand_filter.setStyleSheet("""
            QComboBox {
                padding: 6px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }
        """)
        self.brand_filter.currentTextChanged.connect(self.filter_furniture)
        filter_layout.addWidget(QLabel("브랜드:"), 1, 0)
        filter_layout.addWidget(self.brand_filter, 1, 1)
        
        # 타입 필터
        self.type_filter = QComboBox()
        self.type_filter.addItem("전체 타입")
        self.type_filter.setStyleSheet("""
            QComboBox {
                padding: 6px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }
        """)
        self.type_filter.currentTextChanged.connect(self.filter_furniture)
        filter_layout.addWidget(QLabel("타입:"), 2, 0)
        filter_layout.addWidget(self.type_filter, 2, 1)
        
        # 가격 범위 필터
        self.price_filter = QComboBox()
        self.price_filter.addItems(["전체 가격", "~10만원", "10만원~30만원", "30만원~50만원", "50만원~"])
        self.price_filter.setStyleSheet("""
            QComboBox {
                padding: 6px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }
        """)
        self.price_filter.currentTextChanged.connect(self.filter_furniture)
        filter_layout.addWidget(QLabel("가격:"), 3, 0)
        filter_layout.addWidget(self.price_filter, 3, 1)
        
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
        self.furniture_table.setDragEnabled(True)  # 드래그 활성화
        self.furniture_table.setDragDropMode(QTableView.DragDropMode.DragOnly)  # 드래그만 허용
        
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
            
            # Supabase에서 가구 데이터 조회
            response = self.supabase.client.table('furniture').select('*').execute()
            
            print(f"Supabase 응답: {response}")
            print(f"데이터 개수: {len(response.data) if response.data else 0}")
            
            if response.data:
                # 기존 데이터 초기화
                self.furniture_model.clear_furniture()
                
                # 필터 옵션 초기화
                self.brand_filter.clear()
                self.brand_filter.addItem("전체 브랜드")
                self.type_filter.clear()
                self.type_filter.addItem("전체 타입")
                
                # 데이터 추가
                for item in response.data:
                    try:
                        print(f"가구 데이터 처리 중: {item.get('name', 'Unknown')}")
                        furniture = Furniture(**item)
                        self.furniture_model.add_furniture(furniture)
                        
                        # 필터 옵션 업데이트
                        if furniture.brand and furniture.brand not in [self.brand_filter.itemText(i) for i in range(1, self.brand_filter.count())]:
                            self.brand_filter.addItem(furniture.brand)
                        if furniture.type and furniture.type not in [self.type_filter.itemText(i) for i in range(1, self.type_filter.count())]:
                            self.type_filter.addItem(furniture.type)
                    except Exception as e:
                        print(f"개별 가구 데이터 처리 중 오류 발생: {e}")
                        continue
                
                # 테이블 크기 조정
                self.furniture_table.resizeColumnsToContents()
                self.furniture_table.resizeRowsToContents()
                
                print(f"총 {self.furniture_model.rowCount()}개의 가구 데이터가 로드되었습니다.")
            else:
                print("가구 데이터가 없습니다.")
            
        except Exception as e:
            print(f"가구 데이터 로드 중 오류 발생: {e}")
            # TODO: 사용자에게 오류 메시지 표시
    
    def create_new_collage(self):
        """새 콜라주를 생성합니다."""
        from ui.canvas import Canvas
        # 메인 윈도우에서 캔버스 위젯 찾기
        main_window = self.window()
        if main_window:
            # 캔버스 위젯 찾기
            canvas = main_window.findChild(Canvas)
            if canvas:
                canvas.create_new_collage()
    
    def export_collage(self):
        """현재 콜라주를 이미지로 내보냅니다."""
        from ui.canvas import Canvas
        # 메인 윈도우에서 캔버스 위젯 찾기
        main_window = self.window()
        if main_window:
            # 캔버스 위젯 찾기
            canvas = main_window.findChild(Canvas)
            if canvas:
                canvas.export_collage()
    
    def filter_furniture(self):
        """가구 목록을 필터링합니다."""
        search_text = self.search_input.text().lower()
        selected_brand = self.brand_filter.currentText()
        selected_type = self.type_filter.currentText()
        selected_price = self.price_filter.currentText()
        
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
            if selected_price != "전체 가격":
                price = furniture.price
                if selected_price == "~10만원" and price > 100000:
                    show_item = False
                elif selected_price == "10만원~30만원" and (price < 100000 or price > 300000):
                    show_item = False
                elif selected_price == "30만원~50만원" and (price < 300000 or price > 500000):
                    show_item = False
                elif selected_price == "50만원~" and price < 500000:
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

class BottomPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("bottom_panel")  # 이름 추가
        self.setup_ui()
        print("[하단패널] 초기화 완료")
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 선택된 가구 목록 테이블
        self.selected_model = SelectedFurnitureTableModel()
        self.selected_table = QTableView()
        self.selected_table.setModel(self.selected_model)
        self.selected_table.setStyleSheet("""
            QTableView {
                border: none;
                background-color: white;
            }
            QTableView::item {
                border-bottom: 1px solid #eee;
                padding: 5px;
            }
        """)
        self.selected_table.horizontalHeader().setStretchLastSection(True)
        self.selected_table.verticalHeader().setVisible(False)
        self.selected_table.setShowGrid(False)
        layout.addWidget(self.selected_table)
        
        # 하단 정보 패널
        info_panel = QFrame()
        info_panel.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-top: 1px solid #ddd;
            }
        """)
        info_layout = QHBoxLayout(info_panel)
        info_layout.setContentsMargins(10, 10, 10, 10)
        
        # 선택된 가구 목록
        self.selected_items_label = QLabel("선택된 가구: 0개")
        self.selected_items_label.setStyleSheet("font-size: 14px; color: #2C3E50;")
        info_layout.addWidget(self.selected_items_label)
        
        # 총 가격
        self.total_price_label = QLabel("총 가격: ₩0")
        self.total_price_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #2C3E50;
                font-weight: bold;
            }
        """)
        info_layout.addWidget(self.total_price_label)
        
        layout.addWidget(info_panel)
    
    def update_panel(self, items):
        """하단 패널을 업데이트합니다."""
        print(f"[하단패널] 업데이트 시작, 아이템 수: {len(items)}")
        self.selected_model.clear_furniture()
        total_price = 0
        
        for item in items:
            print(f"[하단패널] 가구 추가: {item.furniture.name}")
            self.selected_model.add_furniture(item.furniture)
            total_price += item.furniture.price
        
        self.selected_items_label.setText(f"선택된 가구: {len(items)}개")
        self.total_price_label.setText(f"총 가격: ₩{total_price:,}")
        
        # 테이블 크기 조정
        self.selected_table.resizeColumnsToContents()
        self.selected_table.resizeRowsToContents()
        print(f"[하단패널] 업데이트 완료, 총 가격: ₩{total_price:,}") 