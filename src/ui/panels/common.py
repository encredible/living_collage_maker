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
            print("[FurnitureTableModel] 소멸자 호출됨")
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
            "이름", "브랜드", "타입", "가격", "개수", "총 가격", "색상", 
            "위치", "스타일", "크기(W×D×H)", "좌석높이", "설명", "링크", "작성자"
        ])
        self.furniture_count = {}  # 가구별 개수 저장
    
    def add_furniture(self, furniture: Furniture):
        furniture_key = furniture.name
        if furniture_key in self.furniture_count:
            self.furniture_count[furniture_key]['count'] += 1
        else:
            self.furniture_count[furniture_key] = {'furniture': furniture, 'count': 1}
        
        self.refresh_model()
    
    def clear_furniture(self):
        self.furniture_count.clear()
        self.clear()
        self.setHorizontalHeaderLabels([
            "이름", "브랜드", "타입", "가격", "개수", "총 가격", "색상", 
            "위치", "스타일", "크기(W×D×H)", "좌석높이", "설명", "링크", "작성자"
        ])

    def refresh_model(self):
        """모델을 새로고침합니다."""
        self.clear()
        self.setHorizontalHeaderLabels([
            "이름", "브랜드", "타입", "가격", "개수", "총 가격", "색상", 
            "위치", "스타일", "크기(W×D×H)", "좌석높이", "설명", "링크", "작성자"
        ])
        
        for item_info in self.furniture_count.values():
            furniture = item_info['furniture']
            count = item_info['count']
            total_price = furniture.price * count
            
            # 크기 정보 조합
            size_info = f"{furniture.width}×{furniture.depth}×{furniture.height}mm" if furniture.width > 0 or furniture.depth > 0 or furniture.height > 0 else "정보없음"
            
            # 좌석 높이 정보
            seat_height_info = f"{furniture.seat_height}mm" if furniture.seat_height is not None else "해당없음"
            
            # 설명 길이 제한 (너무 길면 잘라내기)
            description = furniture.description[:50] + "..." if len(furniture.description) > 50 else furniture.description
            
            # 각 컬럼 아이템 생성
            name_item = QStandardItem(furniture.name)
            brand_item = QStandardItem(furniture.brand)
            type_item = QStandardItem(furniture.type)
            price_item = QStandardItem(f"₩{furniture.price:,}")
            count_item = QStandardItem(str(count))
            total_price_item = QStandardItem(f"₩{total_price:,}")
            color_item = QStandardItem(furniture.color)
            locations_item = QStandardItem(", ".join(furniture.locations))
            styles_item = QStandardItem(", ".join(furniture.styles))
            size_item = QStandardItem(size_info)
            seat_height_item = QStandardItem(seat_height_info)
            description_item = QStandardItem(description)
            link_item = QStandardItem(furniture.link)
            author_item = QStandardItem(furniture.author)
            
            self.appendRow([
                name_item, brand_item, type_item, price_item, count_item, total_price_item,
                color_item, locations_item, styles_item, size_item, seat_height_item,
                description_item, link_item, author_item
            ]) 