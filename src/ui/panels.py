from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QScrollArea, QPushButton,
                             QComboBox, QGridLayout, QTableView, QFrame, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, QSize, QMimeData, pyqtSignal, QAbstractTableModel, QModelIndex, QThread, pyqtSlot
from PyQt6.QtGui import QPixmap, QDrag, QStandardItemModel, QStandardItem, QPainter, QPen, QColor
from models.furniture import Furniture
from services.image_service import ImageService
from services.supabase_client import SupabaseClient
import threading
from concurrent.futures import ThreadPoolExecutor
import weakref  # Python 내장 weakref 모듈 사용

class ImageLoaderThread(QThread):
    image_loaded = pyqtSignal(str, QPixmap)
    
    def __init__(self, image_service, supabase, furniture):
        super().__init__()
        self.image_service = image_service
        self.supabase = supabase
        self.furniture = furniture
    
    def run(self):
        try:
            image_data = self.supabase.get_furniture_image(self.furniture.image_filename)
            pixmap = self.image_service.download_and_cache_image(image_data, self.furniture.image_filename)
            self.image_loaded.emit(self.furniture.image_filename, pixmap)
        except Exception as e:
            print(f"이미지 로드 중 오류 발생: {e}")

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
        self.thumbnail_cache = weakref.WeakValueDictionary()  # 약한 참조를 사용한 썸네일 캐시
        self.loading_threads = {}  # 로딩 중인 스레드 추적
        self._cleanup_timer = None
    
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
        thumbnail_item.setEditable(False)
        thumbnail_item.setData(furniture, Qt.ItemDataRole.UserRole)
        
        # 브랜드 아이템
        brand_item = QStandardItem(furniture.brand)
        brand_item.setEditable(False)
        brand_item.setData(furniture, Qt.ItemDataRole.UserRole)
        
        # 이름 아이템
        name_item = QStandardItem(furniture.name)
        name_item.setEditable(False)
        name_item.setData(furniture, Qt.ItemDataRole.UserRole)
        
        # 가격 아이템
        price_item = QStandardItem(f"₩{furniture.price:,}")
        price_item.setEditable(False)
        price_item.setData(furniture, Qt.ItemDataRole.UserRole)
        
        # 행 추가
        self.appendRow([thumbnail_item, brand_item, name_item, price_item])
        self.furniture_items.append(furniture)
        
        # 이미지 비동기 로딩 시작
        self.load_thumbnail_async(furniture, thumbnail_item)
    
    def load_thumbnail_async(self, furniture: Furniture, item: QStandardItem):
        """썸네일을 비동기적으로 로드합니다."""
        # 이미 로딩 중인 스레드가 있다면 중단
        if furniture.image_filename in self.loading_threads:
            try:
                self.loading_threads[furniture.image_filename].terminate()
                self.loading_threads[furniture.image_filename].wait()
            except:
                pass
        
        # 새 스레드 생성 및 시작
        thread = ImageLoaderThread(self.image_service, self.supabase, furniture)
        thread.image_loaded.connect(lambda filename, pixmap: self.on_image_loaded(filename, pixmap, item))
        self.loading_threads[furniture.image_filename] = thread
        thread.start()
    
    @pyqtSlot(str, QPixmap, QStandardItem)
    def on_image_loaded(self, filename: str, pixmap: QPixmap, item: QStandardItem):
        """이미지 로딩이 완료되면 호출됩니다."""
        if not pixmap.isNull():
            thumbnail = self.image_service.create_thumbnail(pixmap, QSize(100, 100))
            item.setData(thumbnail, Qt.ItemDataRole.DecorationRole)
            self.thumbnail_cache[filename] = thumbnail
        
        # 스레드 정리
        if filename in self.loading_threads:
            try:
                self.loading_threads[filename].wait()
                del self.loading_threads[filename]
            except:
                pass
    
    def clear_furniture(self):
        # 로딩 중인 스레드 중단
        for thread in self.loading_threads.values():
            try:
                thread.terminate()
                thread.wait()
            except:
                pass
        self.loading_threads.clear()
        
        self.removeRows(0, self.rowCount())
        self.furniture_items.clear()
        self.thumbnail_cache.clear()
    
    def __del__(self):
        """모델이 삭제될 때 리소스 정리"""
        self.clear_furniture()

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

class SelectedFurniturePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 제목
        title = QLabel("선택된 가구")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)
        
        # 가구 목록 테이블
        self.furniture_table = QTableView()
        self.furniture_table.setStyleSheet("""
            QTableView {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QTableView::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #ddd;
                font-weight: bold;
            }
        """)
        
        # 테이블 모델 설정
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels([
            "브랜드", "이름", "가격", "타입", "색상", "크기", 
            "좌석 높이", "위치", "스타일", "설명", "링크", "작성자", "작성일"
        ])
        self.furniture_table.setModel(self.model)
        
        # 테이블 설정
        self.furniture_table.horizontalHeader().setStretchLastSection(True)
        self.furniture_table.verticalHeader().setVisible(False)
        self.furniture_table.setShowGrid(False)
        self.furniture_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.furniture_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.furniture_table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        
        # 더블 클릭 이벤트 연결
        self.furniture_table.doubleClicked.connect(self.on_double_click)
        
        # 컬럼 너비 설정
        self.furniture_table.setColumnWidth(0, 100)  # 브랜드
        self.furniture_table.setColumnWidth(1, 150)  # 이름
        self.furniture_table.setColumnWidth(2, 100)  # 가격
        self.furniture_table.setColumnWidth(3, 100)  # 타입
        self.furniture_table.setColumnWidth(4, 80)   # 색상
        self.furniture_table.setColumnWidth(5, 120)  # 크기
        self.furniture_table.setColumnWidth(6, 80)   # 좌석 높이
        self.furniture_table.setColumnWidth(7, 100)  # 위치
        self.furniture_table.setColumnWidth(8, 100)  # 스타일
        self.furniture_table.setColumnWidth(9, 200)  # 설명
        self.furniture_table.setColumnWidth(10, 150) # 링크
        self.furniture_table.setColumnWidth(11, 100) # 작성자
        self.furniture_table.setColumnWidth(12, 150) # 작성일
        
        layout.addWidget(self.furniture_table)
        
        # 하단 정보 패널
        info_panel = QFrame()
        info_panel.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-top: 1px solid #ddd;
                padding: 10px;
            }
        """)
        info_layout = QHBoxLayout(info_panel)
        
        # 총 가격
        self.total_price_label = QLabel("총 가격: 0원")
        self.total_price_label.setStyleSheet("font-size: 14px; color: #666;")
        info_layout.addWidget(self.total_price_label)
        
        # 선택된 가구 수
        self.count_label = QLabel("선택된 가구: 0개")
        self.count_label.setStyleSheet("font-size: 14px; color: #666;")
        info_layout.addWidget(self.count_label)
        
        layout.addWidget(info_panel)
        
    def on_double_click(self, index):
        """테이블 셀 더블 클릭 이벤트 처리"""
        if index.column() == 10:  # 링크 컬럼
            link = self.model.item(index.row(), 10).text()
            if link != "미지정":
                import webbrowser
                webbrowser.open(link)
        
    def update_furniture_list(self, furniture_items):
        self.model.removeRows(0, self.model.rowCount())
        total_price = 0
        
        for item in furniture_items:
            furniture = item.furniture
            total_price += furniture.price
            
            row = [
                QStandardItem(furniture.brand),
                QStandardItem(furniture.name),
                QStandardItem(f"{furniture.price:,}원"),
                QStandardItem(furniture.type),
                QStandardItem(furniture.color or "미지정"),
                QStandardItem(f"{furniture.width}x{furniture.depth}x{furniture.height}mm"),
                QStandardItem(str(furniture.seat_height) + "mm" if furniture.seat_height else "미지정"),
                QStandardItem(", ".join(furniture.locations) if furniture.locations else "미지정"),
                QStandardItem(", ".join(furniture.styles) if furniture.styles else "미지정"),
                QStandardItem(furniture.description or "미지정"),
                QStandardItem(furniture.link or "미지정"),
                QStandardItem(furniture.author or "미지정"),
                QStandardItem(furniture.created_at or "미지정")
            ]
            
            # 링크 셀에 커서 변경 및 스타일 적용
            if furniture.link:
                row[10].setData(Qt.CursorShape.PointingHandCursor, Qt.ItemDataRole.UserRole)
                row[10].setData("color: blue; text-decoration: underline;", Qt.ItemDataRole.UserRole + 1)
            
            self.model.appendRow(row)
        
        self.total_price_label.setText(f"총 가격: {total_price:,}원")
        self.count_label.setText(f"선택된 가구: {len(furniture_items)}개")
        
        # 테이블 크기 조정
        self.furniture_table.resizeColumnsToContents()
        self.furniture_table.resizeRowsToContents()

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