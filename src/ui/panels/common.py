"""공통 UI 구성요소들

패널들에서 공통으로 사용되는 위젯, 모델, 스레드 클래스들을 포함합니다.
"""

import weakref

from PyQt6.QtCore import QMimeData, QSize, Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QDrag, QPixmap, QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.models.furniture import Furniture
from src.services.image_service import ImageService
from src.services.supabase_client import SupabaseClient


class ImageLoaderThread(QThread):
    """이미지 로딩을 위한 워커 스레드"""
    image_loaded = pyqtSignal(str, QPixmap)
    
    def __init__(self, image_service, supabase, furniture):
        super().__init__()
        self.image_service = image_service
        self.supabase = supabase
        self.furniture = furniture
        self._stop_requested = False
        
        print(f"[ImageLoaderThread] 생성됨: {furniture.image_filename}")
        
        # 스레드가 완료되면 자동으로 정리되도록 설정
        self.finished.connect(self.deleteLater)
        self.finished.connect(lambda: print(f"[ImageLoaderThread] 완료됨: {self.furniture.image_filename}"))
    
    def run(self):
        try:
            print(f"[ImageLoaderThread] 시작: {self.furniture.image_filename}")
            
            if self._stop_requested:
                print(f"[ImageLoaderThread] 중지 요청으로 종료: {self.furniture.image_filename}")
                return
                
            # Supabase에서 이미지 데이터 가져오기
            image_data = self.supabase.get_furniture_image(self.furniture.image_filename)
            
            if self._stop_requested:
                print(f"[ImageLoaderThread] 중지 요청으로 종료: {self.furniture.image_filename}")
                return
                
            # 이미지 처리
            pixmap = self.image_service.download_and_cache_image(image_data, self.furniture.image_filename)
            
            if self._stop_requested:
                print(f"[ImageLoaderThread] 중지 요청으로 종료: {self.furniture.image_filename}")
                return
                
            # 시그널 발생
            if pixmap and not pixmap.isNull():
                print(f"[ImageLoaderThread] 시그널 발생: {self.furniture.image_filename}")
                self.image_loaded.emit(self.furniture.image_filename, pixmap)
                
        except Exception as e:
            if not self._stop_requested:
                print(f"[ImageLoaderThread] 오류 발생: {self.furniture.image_filename} - {e}")
        finally:
            print(f"[ImageLoaderThread] 종료: {self.furniture.image_filename}")
            # 스레드 완료 시 자동 정리
            self.quit()
    
    def stop(self):
        """스레드 중지 요청"""
        print(f"[ImageLoaderThread] 중지 요청: {self.furniture.image_filename}")
        self._stop_requested = True
        self.quit()  # 이벤트 루프 종료 요청


class FurnitureItem(QWidget):
    """가구 정보를 표시하는 위젯"""
    
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
    """가구 목록을 위한 테이블 모델"""
    
    def __init__(self):
        super().__init__()
        self.setHorizontalHeaderLabels(["썸네일", "브랜드", "이름", "가격", "타입", "위치", "색상", "스타일"])
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
            
            # MIME 데이터 설정
            mime_data.setData("application/x-furniture", str(furniture_data).encode())
            
        return mime_data
    
    def add_furniture(self, furniture: Furniture):
        # 썸네일 아이템
        thumbnail_item = QStandardItem()
        thumbnail_item.setText("")  # 텍스트 제거
        thumbnail_item.setSizeHint(QSize(100, 100))
        
        # 다른 정보 아이템들
        brand_item = QStandardItem(furniture.brand)
        name_item = QStandardItem(furniture.name)
        price_item = QStandardItem(f"₩{furniture.price:,}")
        type_item = QStandardItem(furniture.type)
        locations_item = QStandardItem(", ".join(furniture.locations))
        color_item = QStandardItem(furniture.color)
        styles_item = QStandardItem(", ".join(furniture.styles))
        
        # 행 추가
        row = [thumbnail_item, brand_item, name_item, price_item, type_item, locations_item, color_item, styles_item]
        self.appendRow(row)
        
        # 가구 리스트에 추가
        self.furniture_items.append(furniture)
        
        # 썸네일 비동기 로드
        self.load_thumbnail_async(furniture, thumbnail_item)
    
    def load_thumbnail_async(self, furniture: Furniture, item: QStandardItem):
        """비동기적으로 썸네일을 로드합니다."""
        # 이미 로딩 중인 경우 건너뛰기
        if furniture.image_filename in self.loading_threads:
            print(f"[FurnitureTableModel] 이미 로딩 중: {furniture.image_filename}")
            return
            
        print(f"[FurnitureTableModel] 썸네일 로딩 시작: {furniture.image_filename}")
        
        # 새로운 로더 스레드 생성
        loader = ImageLoaderThread(self.image_service, self.supabase, furniture)
        loader.image_loaded.connect(lambda filename, pixmap: self.on_image_loaded(filename, pixmap, item))
        
        # 스레드 추적
        self.loading_threads[furniture.image_filename] = loader
        print(f"[FurnitureTableModel] 스레드 등록: {furniture.image_filename}, 총 {len(self.loading_threads)}개")
        
        # 스레드 시작
        loader.start()
    
    @pyqtSlot(str, QPixmap, QStandardItem)
    def on_image_loaded(self, filename: str, pixmap: QPixmap, item: QStandardItem):
        """이미지 로드 완료 시 호출되는 콜백"""
        try:
            # 썸네일 생성 및 캐시
            if pixmap and not pixmap.isNull():
                thumbnail = self.image_service.create_thumbnail(pixmap, (100, 100))
                item.setData(thumbnail, Qt.ItemDataRole.DecorationRole)
                self.thumbnail_cache[filename] = thumbnail
        except Exception as e:
            print(f"썸네일 설정 중 오류 발생: {e}")
        finally:
            # 완료된 스레드 제거
            if filename in self.loading_threads:
                del self.loading_threads[filename]
    
    def clear_furniture(self):
        print(f"[FurnitureTableModel] 스레드 정리 시작: {len(self.loading_threads)}개 스레드")
        
        # 로딩 중인 스레드 중단
        for filename, thread in list(self.loading_threads.items()):  # 리스트로 복사하여 안전하게 순회
            try:
                print(f"[FurnitureTableModel] 스레드 정리 중: {filename}")
                if thread.isRunning():
                    thread.stop()  # 우리가 추가한 stop() 메서드 호출
                    thread.quit()
                    if not thread.wait(3000):  # 최대 3초 대기
                        print(f"[FurnitureTableModel] 스레드 강제 종료: {filename}")
                        thread.terminate()  # 강제 종료
                        thread.wait(1000)  # 종료 대기
                else:
                    print(f"[FurnitureTableModel] 스레드 이미 종료됨: {filename}")
            except Exception as e:
                print(f"[FurnitureTableModel] 스레드 정리 중 오류: {filename} - {e}")
        
        self.loading_threads.clear()
        print("[FurnitureTableModel] 모든 스레드 정리 완료")
        
        # 모델 데이터 초기화
        self.clear()
        self.setHorizontalHeaderLabels(["썸네일", "브랜드", "이름", "가격", "타입", "위치", "색상", "스타일"])
        self.furniture_items.clear()
        self.thumbnail_cache.clear()
    
    def __del__(self):
        try:
            if hasattr(self, 'loading_threads') and self.loading_threads:
                self.clear_furniture()
        except Exception as e:
            print(f"[FurnitureTableModel] 소멸자 오류: {e}")
            pass  # 소멸자에서는 예외를 무시


class SelectedFurnitureTableModel(QStandardItemModel):
    """선택된 가구 목록을 위한 테이블 모델"""
    
    def __init__(self):
        super().__init__()
        self.setHorizontalHeaderLabels([
            "이름", "브랜드", "타입", "가격", "색상", 
            "위치", "스타일", "크기(W×D×H)", "좌석높이", "설명", "링크", "작성자", "개수"
        ])
        self.furniture_count = {}  # 가구별 개수 저장
        self.furniture_order = []  # 가구 순서 저장 (가구 이름 리스트)
        self.column_width_callback = None  # 컬럼 너비 복원 콜백
    
    def set_column_width_callback(self, callback):
        """컬럼 너비 복원 콜백을 설정합니다."""
        self.column_width_callback = callback
    
    def supportedDropActions(self):
        """지원하는 드롭 액션을 반환합니다."""
        return Qt.DropAction.MoveAction
    
    def flags(self, index):
        """아이템의 플래그를 반환합니다."""
        default_flags = super().flags(index)
        if index.isValid():
            return default_flags | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled
        else:
            return default_flags | Qt.ItemFlag.ItemIsDropEnabled
    
    def mimeTypes(self):
        """지원하는 MIME 타입을 반환합니다."""
        return ["application/x-furniture-order"]
    
    def mimeData(self, indexes):
        """드래그할 데이터를 생성합니다."""
        if not indexes:
            return None
        
        # 첫 번째 선택된 행의 가구 이름 가져오기
        row = indexes[0].row()
        furniture_name = self.get_furniture_name_at_row(row)
        
        if furniture_name:
            mime_data = QMimeData()
            mime_data.setData("application/x-furniture-order", furniture_name.encode('utf-8'))
            return mime_data
        
        return None
    
    def dropMimeData(self, data, action, row, column, parent):
        """드롭된 데이터를 처리합니다."""
        if action != Qt.DropAction.MoveAction:
            return False
        
        if not data.hasFormat("application/x-furniture-order"):
            return False
        
        # 드래그된 가구 이름 가져오기
        furniture_name = data.data("application/x-furniture-order").data().decode('utf-8')
        
        # 드롭 위치 계산
        if row == -1:
            if parent.isValid():
                drop_row = parent.row()
            else:
                drop_row = self.rowCount()
        else:
            drop_row = row
        
        # 드롭 위치가 유효한지 확인
        if 0 <= drop_row <= len(self.furniture_order):
            # 가구 순서 변경
            if self.move_furniture_to_position(furniture_name, drop_row):
                return True
        
        return False
    
    def add_furniture(self, furniture: Furniture):
        furniture_key = furniture.name
        if furniture_key in self.furniture_count:
            self.furniture_count[furniture_key]['count'] += 1
        else:
            self.furniture_count[furniture_key] = {'furniture': furniture, 'count': 1}
            # 새 가구면 순서 리스트에 추가
            if furniture_key not in self.furniture_order:
                self.furniture_order.append(furniture_key)
        
        self.refresh_model()
    
    def clear_furniture(self):
        self.furniture_count.clear()
        self.furniture_order.clear()
        self.clear()
        self.setHorizontalHeaderLabels([
            "이름", "브랜드", "타입", "가격", "색상", 
            "위치", "스타일", "크기(W×D×H)", "좌석높이", "설명", "링크", "작성자", "개수"
        ])
    
    def move_furniture_up(self, furniture_name: str):
        """가구를 한 단계 위로 이동"""
        if furniture_name in self.furniture_order:
            current_index = self.furniture_order.index(furniture_name)
            if current_index > 0:
                # 위 항목과 위치 교환
                self.furniture_order[current_index], self.furniture_order[current_index - 1] = \
                    self.furniture_order[current_index - 1], self.furniture_order[current_index]
                self.refresh_model()
                return current_index - 1
        return -1
    
    def move_furniture_down(self, furniture_name: str):
        """가구를 한 단계 아래로 이동"""
        if furniture_name in self.furniture_order:
            current_index = self.furniture_order.index(furniture_name)
            if current_index < len(self.furniture_order) - 1:
                # 아래 항목과 위치 교환
                self.furniture_order[current_index], self.furniture_order[current_index + 1] = \
                    self.furniture_order[current_index + 1], self.furniture_order[current_index]
                self.refresh_model()
                return current_index + 1
        return -1
    
    def move_furniture_to_top(self, furniture_name: str):
        """가구를 맨 위로 이동"""
        if furniture_name in self.furniture_order:
            self.furniture_order.remove(furniture_name)
            self.furniture_order.insert(0, furniture_name)
            self.refresh_model()
            return 0
        return -1
    
    def move_furniture_to_bottom(self, furniture_name: str):
        """가구를 맨 아래로 이동"""
        if furniture_name in self.furniture_order:
            self.furniture_order.remove(furniture_name)
            self.furniture_order.append(furniture_name)
            self.refresh_model()
            return len(self.furniture_order) - 1
        return -1
    
    def move_furniture_to_position(self, furniture_name: str, new_position: int):
        """가구를 특정 위치로 이동 (드래그 앤 드롭용)"""
        if furniture_name in self.furniture_order:
            old_position = self.furniture_order.index(furniture_name)
            if old_position != new_position and 0 <= new_position < len(self.furniture_order):
                # 기존 위치에서 제거
                self.furniture_order.pop(old_position)
                # 새 위치에 삽입
                self.furniture_order.insert(new_position, furniture_name)
                self.refresh_model()
                return True
        return False
    
    def sort_furniture(self, sort_by: str, ascending: bool = True):
        """가구를 지정된 기준으로 정렬"""
        if not self.furniture_count:
            return
        
        # 정렬할 가구 리스트 생성
        furniture_list = []
        for furniture_name in self.furniture_order:
            if furniture_name in self.furniture_count:
                furniture_info = self.furniture_count[furniture_name]
                furniture = furniture_info['furniture']
                furniture_list.append((furniture_name, furniture))
        
        # 정렬 기준에 따른 키 함수 정의
        if sort_by == "name":
            key_func = lambda x: x[1].name.lower()
        elif sort_by == "brand":
            key_func = lambda x: x[1].brand.lower()
        elif sort_by == "price":
            key_func = lambda x: x[1].price or 0
        elif sort_by == "type":
            key_func = lambda x: x[1].type.lower()
        else:
            return  # 알 수 없는 정렬 기준
        
        # 정렬 수행
        furniture_list.sort(key=key_func, reverse=not ascending)
        
        # 순서 리스트 업데이트
        self.furniture_order = [item[0] for item in furniture_list]
        self.refresh_model()
    
    def get_furniture_name_at_row(self, row: int):
        """지정된 행의 가구 이름을 반환"""
        if 0 <= row < len(self.furniture_order):
            return self.furniture_order[row]
        return None
    
    def refresh_model(self):
        self.clear()
        self.setHorizontalHeaderLabels([
            "이름", "브랜드", "타입", "가격", "색상", 
            "위치", "스타일", "크기(W×D×H)", "좌석높이", "설명", "링크", "작성자", "개수"
        ])
        
        # 순서에 따라 가구별로 행 추가
        for furniture_name in self.furniture_order:
            if furniture_name in self.furniture_count:
                furniture_info = self.furniture_count[furniture_name]
                furniture = furniture_info['furniture']
                count = furniture_info['count']
                
                # 각 컬럼에 맞는 데이터 생성 (13개 컬럼)
                row_data = [
                    furniture.name or "",                                    # 이름
                    furniture.brand or "",                                   # 브랜드
                    furniture.type or "",                                    # 타입
                    f"₩{furniture.price:,}" if furniture.price else "",      # 가격
                    furniture.color or "",                                   # 색상
                    ", ".join(furniture.locations) if furniture.locations else "",  # 위치
                    ", ".join(furniture.styles) if furniture.styles else "",        # 스타일
                    self._format_size(furniture.width, furniture.depth, furniture.height),  # 크기
                    f"{furniture.seat_height}mm" if furniture.seat_height else "",   # 좌석높이
                    self._truncate_text(furniture.description or "", 50),    # 설명
                    furniture.link or "",                                    # 링크
                    furniture.author or "",                                  # 작성자
                    str(count)                                              # 개수
                ]
                
                # QStandardItem 리스트 생성 및 추가
                items = [QStandardItem(str(data)) for data in row_data]
                
                # 모든 아이템을 편집 불가능하게 설정
                for item in items:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                
                self.appendRow(items)
        
        # 모델 새로고침 후 컬럼 너비 복원
        if self.column_width_callback:
            self.column_width_callback()
    
    def _format_size(self, width, depth, height):
        """크기 정보를 포맷팅합니다."""
        if width and depth and height:
            return f"{width}×{depth}×{height}mm"
        return ""
    
    def _truncate_text(self, text, max_length):
        """텍스트를 지정된 길이로 자릅니다."""
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text
    
    def get_total_price(self):
        """전체 가구의 총 가격을 계산합니다."""
        total = 0
        for furniture_info in self.furniture_count.values():
            furniture = furniture_info['furniture']
            count = furniture_info['count']
            if furniture.price:
                total += furniture.price * count
        return total
    
    def get_total_count(self):
        """전체 가구의 총 개수를 계산합니다."""
        return sum(info['count'] for info in self.furniture_count.values()) 