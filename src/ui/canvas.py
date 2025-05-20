from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton,
                             QMenu, QMessageBox, QFileDialog, QSlider, QHBoxLayout, 
                             QDialog, QGroupBox, QVBoxLayout, QGraphicsColorizeEffect,
                             QGraphicsOpacityEffect)
from PyQt6.QtCore import Qt, QSize, QPoint, QRect, QTimer, QThread, pyqtSignal
import weakref
from PyQt6.QtGui import (QPainter, QColor, QPen, QPixmap, QDrag, QPainterPath, 
                        QTransform, QImage, QBrush, QPainterPath, QColorSpace)
from models.furniture import Furniture
from ui.dialogs import CanvasSizeDialog
from ui.panels import ExplorerPanel, BottomPanel
from services.image_service import ImageService
from services.supabase_client import SupabaseClient
import os
import json
import datetime
import numpy as np
import time

class ImageProcessor(QThread):
    """이미지 처리를 별도 스레드에서 수행하는 클래스"""
    # 처리 완료 시 신호 발생
    finished = pyqtSignal(QPixmap)
    
    def __init__(self, pixmap, color_temp, brightness, saturation):
        super().__init__()
        self.pixmap = pixmap
        self.color_temp = color_temp
        self.brightness = brightness
        self.saturation = saturation
        self.should_stop = False
        
    def run(self):
        """스레드 실행 메서드"""
        # 작업 시작 전 중단 확인
        if self.should_stop:
            return
            
        # 처리 시작 시간 기록
        start_time = time.time()
        
        # 이미지 처리 수행
        result = ImageAdjuster.apply_effects(
            self.pixmap, 
            self.color_temp, 
            self.brightness, 
            self.saturation
        )
        
        # 종료 상태 확인
        if self.should_stop:
            return
            
        # 처리 종료 시간 및 소요 시간 기록
        end_time = time.time()
        processing_time = (end_time - start_time) * 1000
        
        # 로그 출력 (1ms 이상 소요된 경우만)
        if processing_time > 1:
            print(f"[ImageProcessor] 처리 시간: {processing_time:.2f}ms (크기: {self.pixmap.width()}x{self.pixmap.height()})")
        
        # 처리 완료 신호 발생
        self.finished.emit(result)
        
    def quit(self):
        """스레드를 안전하게 종료합니다."""
        self.should_stop = True
        super().quit()

class ImageAdjuster:
    """이미지 조정을 처리하는 클래스"""
    
    # 효과 캐시 (key: (픽셀맵 ID, 크기, 색온도, 밝기, 채도))
    _effect_cache = {}
    _cache_size = 50  # 최대 캐시 항목 수를 늘림
    
    # 색온도, 밝기, 채도 조합에 따른 빠른 룩업 테이블
    _temperature_lut = {}  # 색온도 룩업 테이블 (미리 계산)
    _initialized = False
    
    # 처리 방식 선택
    _use_numpy = True  # NumPy 벡터화 처리 사용 여부
    
    # 이미지 고유 ID 카운터
    _image_id_counter = 0
    _image_id_map = weakref.WeakKeyDictionary()  # 픽셀맵 -> 고유 ID 매핑
    
    @staticmethod
    def initialize():
        """이미지 조정 시스템을 초기화합니다."""
        if ImageAdjuster._initialized:
            return
        
        # 룩업 테이블 초기화
        ImageAdjuster._init_temperature_lut()
        
        # NumPy 사용 가능 여부 확인
        try:
            import numpy as np
            test_array = np.array([1, 2, 3])
            ImageAdjuster._use_numpy = True
            print("[ImageAdjuster] NumPy 벡터화 처리 사용 가능")
        except Exception as e:
            ImageAdjuster._use_numpy = False
            print(f"[ImageAdjuster] NumPy 사용 불가: {e}")
        
        ImageAdjuster._initialized = True
        print("[ImageAdjuster] 시스템 초기화 완료")
    
    @staticmethod
    def _init_temperature_lut():
        """색온도 변환을 위한 룩업 테이블을 초기화합니다."""
        # 주요 색온도 값 미리 계산 (500K 단위로 더 세밀하게)
        temps = [2000, 2500, 3000, 3500, 4000, 4500, 5000, 5500, 6000, 6500, 7000, 7500, 8000, 8500, 9000, 9500, 10000]
        
        for temp in temps:
            r_temp, g_temp, b_temp = ImageAdjuster.calculate_temperature_rgb(temp)
            ImageAdjuster._temperature_lut[temp] = (r_temp, g_temp, b_temp)
            
        print(f"[ImageAdjuster] 색온도 룩업 테이블 초기화 완료: {len(ImageAdjuster._temperature_lut)} 항목")
    
    @staticmethod
    def get_temperature_rgb(temperature):
        """가장 가까운 사전 계산된 색온도 값을 반환합니다."""
        # 정확히 일치하는 값이 있으면 바로 반환
        if temperature in ImageAdjuster._temperature_lut:
            return ImageAdjuster._temperature_lut[temperature]
            
        # 가장 가까운 값 찾기
        closest_temp = min(ImageAdjuster._temperature_lut.keys(), key=lambda x: abs(x - temperature))
        
        # 1000K 이내 차이면 사전 계산 값 사용
        if abs(closest_temp - temperature) <= 1000:
            return ImageAdjuster._temperature_lut[closest_temp]
            
        # 그렇지 않으면 직접 계산
        return ImageAdjuster.calculate_temperature_rgb(temperature)
    
    @staticmethod
    def apply_effects(pixmap, color_temp, brightness, saturation):
        """이미지에 색온도, 밝기, 채도 효과를 적용합니다."""
        if pixmap is None or pixmap.isNull():
            print("[ImageAdjuster] 입력 이미지가 없습니다.")
            return QPixmap()

        try:
            # 픽셀맵에 고유 ID 할당 (객체 ID 대신 고유 ID 사용)
            if pixmap not in ImageAdjuster._image_id_map:
                ImageAdjuster._image_id_counter += 1
                ImageAdjuster._image_id_map[pixmap] = ImageAdjuster._image_id_counter
                
            image_id = ImageAdjuster._image_id_map[pixmap]
            
            # 캐시 키 생성 (이미지 고유 ID, 이미지 크기, 색온도, 밝기, 채도)
            # 크기별로 다른 캐시 키 사용 (크기별 캐싱)
            size_key = f"{pixmap.width()}x{pixmap.height()}"
            cache_key = (image_id, size_key, round(color_temp), round(brightness), round(saturation))
            
            # 캐시에 결과가 있으면 복사본 반환 (참조 공유 방지)
            if cache_key in ImageAdjuster._effect_cache:
                cached_pixmap = ImageAdjuster._effect_cache[cache_key]
                # 깊은 복사 수행하여 반환 (서로 다른 객체가 되도록)
                return cached_pixmap.copy()
            
            # 이미지 복사본 생성 (원본 변경 방지)
            pixmap_copy = pixmap.copy()
            
            # NumPy 처리 사용
            if ImageAdjuster._use_numpy:
                result_pixmap = ImageAdjuster.apply_effects_numpy(
                    pixmap_copy,
                    color_temp,
                    brightness,
                    saturation
                )
            else:
                # 기존 방식으로 처리
                # 이미지를 QImage로 변환
                image = pixmap_copy.toImage()
                
                # 결과 이미지 생성 (미리 메모리 할당)
                width = image.width()
                height = image.height()
                result = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
                
                # 색온도에 따른 RGB 계수 계산
                r_temp, g_temp, b_temp = ImageAdjuster.get_temperature_rgb(color_temp)
                brightness_factor = brightness / 100.0
                saturation_factor = saturation / 100.0
                
                # 룩업 테이블 생성 (256개 값에 대해 미리 계산)
                lut = {}
                for v in range(256):
                    # 색온도와 밝기 미리 적용
                    r = min(255, max(0, int(v * r_temp * brightness_factor)))
                    g = min(255, max(0, int(v * g_temp * brightness_factor)))
                    b = min(255, max(0, int(v * b_temp * brightness_factor)))
                    
                    # 각 색상값을 키로 미리 계산
                    lut[v] = (r, g, b)
                
                # 픽셀 건너뛰기 단계 설정 (더 큰 값으로 설정)
                pixel_step = 2 if max(width, height) > 200 else 1
                
                # 성능 향상을 위해 더 큰 스텝으로 처리
                for y in range(0, height, pixel_step):
                    for x in range(0, width, pixel_step):
                        # 픽셀 색상 가져오기
                        pixel = image.pixelColor(x, y)
                        alpha = pixel.alpha()
                        
                        # 룩업 테이블에서 값 가져오기
                        r, g, b = lut[pixel.red()], lut[pixel.green()], lut[pixel.blue()]
                        r, g, b = r[0], g[1], b[2]  # 튜플에서 값 추출
                        
                        # 채도 적용 (그레이스케일 값 계산)
                        gray = int(0.299 * r + 0.587 * g + 0.114 * b)
                        
                        # 채도 적용
                        r = min(255, max(0, int(gray + (r - gray) * saturation_factor)))
                        g = min(255, max(0, int(gray + (g - gray) * saturation_factor)))
                        b = min(255, max(0, int(gray + (b - gray) * saturation_factor)))
                        
                        # 새로운 색상 생성
                        color = QColor(r, g, b, alpha)
                        
                        # 주변 픽셀도 같은 색으로 채우기
                        for py in range(y, min(y + pixel_step, height)):
                            for px in range(x, min(x + pixel_step, width)):
                                result.setPixelColor(px, py, color)
                
                # 처리된 이미지로 QPixmap 생성
                result_pixmap = QPixmap.fromImage(result)
            
            # 결과를 새로운 객체로 깊은 복사
            final_result = result_pixmap.copy()
            
            # 결과 캐싱
            if len(ImageAdjuster._effect_cache) >= ImageAdjuster._cache_size:
                # 캐시가 꽉 찼으면 첫 번째 항목 제거
                ImageAdjuster._effect_cache.pop(next(iter(ImageAdjuster._effect_cache)))
            
            # 결과 캐싱
            ImageAdjuster._effect_cache[cache_key] = final_result.copy()
            
            return final_result
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[ImageAdjuster] 이미지 처리 중 오류 발생: {e}")
            return pixmap.copy()  # 오류 발생 시 원본의 복사본 반환
            
    @staticmethod
    def apply_effects_numpy(pixmap, color_temp, brightness, saturation):
        """NumPy 벡터화를 사용한 효율적인 이미지 처리"""
        try:
            import numpy as np
            
            # QImage로 변환 (Deep Copy 생성)
            image = pixmap.toImage()
            
            # 이미지 포맷 저장 (원본 포맷 유지)
            original_format = image.format()
            
            # 이미지 크기
            width = image.width()
            height = image.height()
            
            # ARGB 형식으로 NumPy 배열 생성
            ptr = image.constBits()  # constBits 사용 (읽기 전용)
            ptr.setsize(image.sizeInBytes())
            
            # 깊은 복사본 생성 (변경 가능하도록)
            arr = np.array(ptr).reshape(height, width, 4).copy()
            
            # 알파 채널 분리 (투명도)
            alpha = arr[:, :, 3].copy()
            
            # 완전 투명한 픽셀 마스크 생성 (알파값이 0인 픽셀)
            transparent_mask = (alpha == 0)
            
            # 반투명 픽셀 마스크 생성 (0 < 알파 < 255)
            semitransparent_mask = np.logical_and(alpha > 0, alpha < 255)
            
            # BGRA -> RGB 변환 (QImage에서는 BGRA 순서로 저장됨)
            r = arr[:, :, 2].astype(np.float32)
            g = arr[:, :, 1].astype(np.float32)
            b = arr[:, :, 0].astype(np.float32)
            
            # 색온도 RGB 계수 적용
            r_temp, g_temp, b_temp = ImageAdjuster.get_temperature_rgb(color_temp)
            brightness_factor = brightness / 100.0
            saturation_factor = saturation / 100.0
            
            # 완전히 투명한 픽셀의 색상값 저장
            # 나중에 복원하기 위함 (투명 픽셀의 색상은 무시되어야 함)
            r_transparent = r[transparent_mask].copy() if np.any(transparent_mask) else None
            g_transparent = g[transparent_mask].copy() if np.any(transparent_mask) else None
            b_transparent = b[transparent_mask].copy() if np.any(transparent_mask) else None
            
            # 색온도와 밝기 적용
            r *= r_temp * brightness_factor
            g *= g_temp * brightness_factor
            b *= b_temp * brightness_factor
            
            # 채도 적용
            gray = 0.299 * r + 0.587 * g + 0.114 * b
            
            # 채도 적용 벡터화 처리
            r = gray + (r - gray) * saturation_factor
            g = gray + (g - gray) * saturation_factor
            b = gray + (b - gray) * saturation_factor
            
            # 값 범위 제한 (0-255)
            r = np.clip(r, 0, 255).astype(np.uint8)
            g = np.clip(g, 0, 255).astype(np.uint8)
            b = np.clip(b, 0, 255).astype(np.uint8)
            
            # 알파값이 0인 완전 투명한 픽셀의 RGB 값 복원
            # 투명 픽셀은 보이지 않으므로 원래 색상을 유지
            if np.any(transparent_mask) and r_transparent is not None:
                r[transparent_mask] = r_transparent
                g[transparent_mask] = g_transparent
                b[transparent_mask] = b_transparent
            
            # 반투명 픽셀의 경우, 프리멀티플라이드 알파 처리
            if np.any(semitransparent_mask):
                alpha_factor = alpha[semitransparent_mask].astype(np.float32) / 255.0
                # 프리멀티플라이드 알파 처리는 제거 (이미지 깨짐 현상 방지)
                # 대신 원래 색상값 그대로 유지
            
            # 결과 배열에 다시 채널 할당 (BGRA 순서)
            arr[:, :, 0] = b
            arr[:, :, 1] = g
            arr[:, :, 2] = r
            arr[:, :, 3] = alpha  # 원본 알파 채널 유지
            
            # QImage 생성 (원본 포맷 유지)
            result_image = QImage(arr.data, width, height, image.bytesPerLine(), original_format)
            
            # 고품질 변환 설정
            result_pixmap = QPixmap.fromImage(result_image)
            
            # 항상 복사본 반환
            return result_pixmap.copy()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[ImageAdjuster] NumPy 이미지 처리 오류: {e}")
            # 에러 발생 시 기본 방식으로 처리
            ImageAdjuster._use_numpy = False
            return pixmap.copy()
    
    @staticmethod
    def calculate_temperature_rgb(temperature):
        """색온도에 따른 RGB 계수를 계산합니다."""
        # 기준 색온도 (6500K)
        reference_temp = 6500
        
        r_factor = 1.0
        g_factor = 1.0
        b_factor = 1.0
        
        # 색온도에 따른 RGB 조정 계수 계산
        if temperature < reference_temp:
            # 따뜻한 색상 (노란색/주황색 쪽으로)
            temp_factor = (reference_temp - temperature) / reference_temp
            r_factor = 1.0 + temp_factor * 0.2  # 빨간색 증가
            g_factor = 1.0
            b_factor = 1.0 - temp_factor * 0.6  # 파란색 크게 감소
        else:
            # 차가운 색상 (파란색 쪽으로)
            temp_factor = (temperature - reference_temp) / reference_temp
            r_factor = 1.0 - temp_factor * 0.4  # 빨간색 감소
            g_factor = 1.0 - temp_factor * 0.2  # 초록색 약간 감소
            b_factor = 1.0 + temp_factor * 0.2  # 파란색 증가
        
        return r_factor, g_factor, b_factor

class FurnitureItem(QWidget):
    def __init__(self, furniture: Furniture, parent=None):
        super().__init__(parent)
        self.furniture = furniture
        self.image_service = ImageService()
        self.supabase = SupabaseClient()
        
        # 이미지 조정 시스템 초기화
        if not ImageAdjuster._initialized:
            ImageAdjuster.initialize()
        
        # 이미지 로드
        self.load_image()
        
        # 드래그 앤 드롭 설정
        self.setMouseTracking(True)
        self.is_resizing = False
        self.resize_handle = QRect(self.width() - 20, self.height() - 20, 20, 20)
        self.maintain_aspect_ratio = False  # 비율 유지 여부를 저장하는 변수 추가
        self.is_flipped = False  # 좌우 반전 여부를 저장하는 변수 추가
        
        # 이미지 조정 관련 속성 추가
        self.color_temp = 6500  # 기본 색온도 (K)
        self.brightness = 100  # 기본 밝기 (%)
        self.saturation = 100  # 기본 채도 (%)
        self.original_pixmap = None  # 원본 이미지 저장
        self.adjust_dialog = None  # 조정 다이얼로그
        
        # 슬라이더 디바운싱을 위한 타이머
        self.update_timer = QTimer(self)
        self.update_timer.setSingleShot(True)
        self.update_timer.setInterval(100)  # 100ms 딜레이
        self.update_timer.timeout.connect(self.apply_pending_update)
    
    def update_resize_handle(self):
        """크기가 변경될 때 리사이즈 핸들 위치를 업데이트합니다."""
        self.resize_handle = QRect(self.width() - 20, self.height() - 20, 20, 20)
    
    def resizeEvent(self, event):
        """위젯 크기가 변경될 때 리사이즈 핸들 위치를 자동으로 업데이트합니다."""
        super().resizeEvent(event)
        self.update_resize_handle()
    
    def load_image(self):
        """가구 이미지를 로드합니다."""
        try:
            # Supabase에서 이미지 다운로드
            image_data = self.supabase.get_furniture_image(self.furniture.image_filename)
            
            # 이미지 캐시 및 썸네일 생성
            self.pixmap = self.image_service.download_and_cache_image(
                image_data, 
                self.furniture.image_filename
            )
            
            # 명시적 깊은 복사 추가 (캐시 참조 공유 방지)
            if not self.pixmap.isNull():
                self.pixmap = self.pixmap.copy()
            
            # 원본 이미지 저장 (픽셀 데이터 복사본 생성)
            if not self.pixmap.isNull():
                self.original_pixmap = self.pixmap.copy()
                print(f"[이미지 로드] 원본 이미지 저장 완료: {self.furniture.image_filename}")
            else:
                print(f"[이미지 로드] 빈 이미지 감지: {self.furniture.image_filename}")
            
            # 이미지가 유효하지 않은 경우 기본 이미지 생성
            if self.pixmap.isNull():
                self.pixmap = QPixmap(200, 200)
                self.pixmap.fill(QColor("#f0f0f0"))
                painter = QPainter(self.pixmap)
                painter.setPen(QPen(QColor("#2C3E50")))
                painter.drawText(self.pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "이미지 로드 실패")
                painter.end()
                self.original_pixmap = self.pixmap.copy()
            
            # 이미지 비율에 맞게 크기 설정
            self.original_ratio = self.pixmap.width() / self.pixmap.height()
            initial_width = 200
            initial_height = int(initial_width / self.original_ratio)
            self.setFixedSize(initial_width, initial_height)
            self.update_resize_handle()
            
        except Exception as e:
            print(f"이미지 로드 중 오류 발생: {e}")
            # 에러 이미지 생성
            self.pixmap = QPixmap(200, 200)
            self.pixmap.fill(QColor("#f0f0f0"))
            painter = QPainter(self.pixmap)
            painter.setPen(QPen(QColor("#2C3E50")))
            painter.drawText(self.pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "이미지 로드 실패")
            painter.end()
            self.original_pixmap = self.pixmap.copy()
            self.setFixedSize(200, 200)
            self.update_resize_handle()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 이미지 그리기 (비율 유지 여부에 따라 다르게 처리)
        if self.maintain_aspect_ratio:
            # 비율 유지하면서 그리기
            scaled_pixmap = self.pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            x = (self.width() - scaled_pixmap.width()) // 2
            y = (self.height() - scaled_pixmap.height()) // 2
            painter.drawPixmap(x, y, scaled_pixmap)
        else:
            # 비율 무시하고 꽉 채우기
            scaled_pixmap = self.pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            painter.drawPixmap(0, 0, scaled_pixmap)
        
        # 테두리 그리기
        pen = QPen(QColor("#2C3E50"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        
        # 리사이즈 핸들 그리기
        painter.fillRect(self.resize_handle, QColor("#2C3E50"))
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.resize_handle.contains(event.pos()):
                self.is_resizing = True
            else:
                self.raise_()  # 위젯을 최상위로
                self.old_pos = event.pos()
    
    def mouseMoveEvent(self, event):
        if self.is_resizing:
            # Shift 키가 눌린 상태인지 확인
            self.maintain_aspect_ratio = event.modifiers() & Qt.KeyboardModifier.ShiftModifier
            
            if self.maintain_aspect_ratio:
                # 비율 유지하면서 크기 조절
                new_width = max(100, event.pos().x())
                new_height = int(new_width / self.original_ratio)
            else:
                # 비율 무시하고 자유롭게 크기 조절
                new_width = max(100, event.pos().x())
                new_height = max(100, event.pos().y())
            
            self.setFixedSize(new_width, new_height)
            self.update_resize_handle()
        elif event.buttons() & Qt.MouseButton.LeftButton:
            # 드래그로 이동
            delta = event.pos() - self.old_pos
            self.move(self.pos() + delta)
    
    def mouseReleaseEvent(self, event):
        self.is_resizing = False
    
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        delete_action = menu.addAction("삭제")
        flip_action = menu.addAction("좌우 반전")
        menu.addSeparator()
        adjust_action = menu.addAction("이미지 조정")  # 이미지 조정 메뉴 추가
        action = menu.exec(event.globalPos())
        
        if action == delete_action:
            print(f"[삭제] 가구 아이템 삭제 시작: {self.furniture.name}")
            # 부모 캔버스 영역에서 캔버스 찾기
            canvas_area = self.parent()
            if canvas_area:
                canvas = canvas_area.parent()
                if canvas and hasattr(canvas, 'furniture_items'):
                    if self in canvas.furniture_items:
                        print(f"[삭제] 캔버스에서 가구 아이템 제거: {self.furniture.name}")
                        canvas.furniture_items.remove(self)
                        # 하단 패널 업데이트
                        main_window = canvas.window()
                        if main_window:
                            print("[삭제] 메인 윈도우 찾음")
                            # 하단 패널 찾기
                            for child in main_window.findChildren(QWidget):
                                if isinstance(child, BottomPanel):
                                    print(f"[삭제] 하단 패널 찾음, 현재 가구 수: {len(canvas.furniture_items)}")
                                    child.update_panel(canvas.furniture_items)
                                    break
                                else:
                                    print(f"[삭제] 다른 위젯 발견: {type(child).__name__}")
                        else:
                            print("[삭제] 메인 윈도우를 찾을 수 없음")
                    else:
                        print(f"[삭제] 가구 아이템이 캔버스 목록에 없음: {self.furniture.name}")
                else:
                    print("[삭제] 캔버스를 찾을 수 없거나 furniture_items 속성이 없음")
            else:
                print("[삭제] 캔버스 영역을 찾을 수 없음")
            self.deleteLater()
            print(f"[삭제] 가구 아이템 삭제 완료: {self.furniture.name}")
        elif action == flip_action:
            # 이미지 좌우 반전
            transform = QTransform()
            transform.scale(-1, 1)  # x축 방향으로 -1을 곱하여 좌우 반전
            self.pixmap = self.pixmap.transformed(transform)
            self.is_flipped = not self.is_flipped  # 반전 상태 토글
            self.update()  # 위젯 다시 그리기
        elif action == adjust_action:
            # 이미지 조정 다이얼로그 표시
            self.show_adjustment_dialog()

    def show_adjustment_dialog(self):
        """이미지 조정 다이얼로그를 표시합니다."""
        # 원본 이미지 확인
        if self.original_pixmap is None or self.original_pixmap.isNull():
            print("[이미지 조정] 원본 이미지가 없습니다. 현재 이미지를 원본으로 사용합니다.")
            self.original_pixmap = self.pixmap.copy()
        
        # 현재 이미지 백업 (깊은 복사)
        self.backup_pixmap = self.pixmap.copy()
        
        # 미리보기용 축소 이미지 생성 (더 작게)
        PREVIEW_MAX_SIZE = 250  # 미리보기 최대 크기를 더 작게 설정 (성능 향상)
        
        # 미리보기 이미지 크기 계산
        if self.original_pixmap.width() > self.original_pixmap.height():
            preview_width = min(PREVIEW_MAX_SIZE, self.original_pixmap.width())
            preview_height = int(self.original_pixmap.height() * (preview_width / self.original_pixmap.width()))
        else:
            preview_height = min(PREVIEW_MAX_SIZE, self.original_pixmap.height())
            preview_width = int(self.original_pixmap.width() * (preview_height / self.original_pixmap.height()))
        
        # 미리보기 이미지 생성
        self.preview_pixmap = self.original_pixmap.scaled(
            preview_width, preview_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation  # 빠른 변환 사용
        )
        
        # 명시적 깊은 복사 추가
        self.preview_pixmap = self.preview_pixmap.copy()
        
        # 이미지 처리 스레드
        self.processor = None
        
        # 처리 중 플래그 (동시에 여러 처리 방지)
        self.is_processing = False
        
        # 타이머 설정 업데이트
        self.update_timer.setInterval(150)  # 150ms로 늘려 CPU 부하 감소
        
        self.adjust_dialog = QDialog(self)
        self.adjust_dialog.setWindowTitle("이미지 조정")
        self.adjust_dialog.setMinimumWidth(400)
        self.adjust_dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)  # 테두리 제거
        self.adjust_dialog.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                border: 1px solid #aaa;
                border-radius: 5px;
            }
            QGroupBox {
                border: none;
                margin-top: 10px;
                font-weight: bold;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 0px;
                padding: 0px 5px 0px 0px;
                margin-top: 2px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: #f0f0f0;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #2C3E50;
                border: 1px solid #5c5c5c;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:focus {
                background: #1a557c;
                border: 2px solid #3498db;
            }
            QPushButton {
                padding: 5px 15px;
                background-color: #2C3E50;
                color: white;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #3E5871;
            }
            QLabel {
                font-size: 12px;
            }
        """)
        
        # 다이얼로그를 이동 가능하게 만들기 위한 변수
        self.dragging_dialog = False
        self.drag_dialog_pos = None
        
        # 메인 레이아웃
        layout = QVBoxLayout(self.adjust_dialog)
        layout.setContentsMargins(15, 15, 15, 15)  # 여백 추가
        
        # 제목 표시줄 추가 (드래그 가능한 영역)
        title_bar = QWidget()
        title_bar.setFixedHeight(30)
        title_bar.setStyleSheet("""
            background-color: #2C3E50;
            border-radius: 3px 3px 0 0;
            color: white;
        """)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 0, 10, 0)
        
        # 제목 라벨
        title_label = QLabel("이미지 조정")
        title_label.setStyleSheet("font-weight: bold; color: white;")
        title_layout.addWidget(title_label)
        
        # 닫기 버튼
        close_button = QPushButton("×")
        close_button.setFixedSize(20, 20)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                font-weight: bold;
                font-size: 16px;
                border: none;
            }
            QPushButton:hover {
                background-color: #e74c3c;
                border-radius: 10px;
            }
        """)
        close_button.clicked.connect(self.cancel_image_adjustments)
        title_layout.addWidget(close_button)
        
        # 제목 표시줄을 레이아웃에 추가
        layout.addWidget(title_bar)
        
        # 제목 표시줄에 마우스 이벤트 설정
        title_bar.mousePressEvent = self.dialog_mouse_press_event
        title_bar.mouseMoveEvent = self.dialog_mouse_move_event
        title_bar.mouseReleaseEvent = self.dialog_mouse_release_event
        
        # 슬라이더 생성 함수
        def create_slider_group(title, value, min_val, max_val, step):
            group = QGroupBox(title)
            group_layout = QVBoxLayout(group)
            
            # 슬라이더 생성
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(min_val, max_val)
            slider.setValue(value)
            slider.setTickPosition(QSlider.TickPosition.TicksBelow)
            slider.setTickInterval(step)
            
            # 페이지 스텝 설정 (더 큰 단위의 이동)
            slider.setPageStep(step)
            
            # 레이블 생성
            label = QLabel(f"{title}: {value}")
            if title == "색온도":
                label.setText(f"{title}: {value}K")
            else:
                label.setText(f"{title}: {value}%")
            
            group_layout.addWidget(label)
            group_layout.addWidget(slider)
            
            return group, slider, label
        
        # 슬라이더 그룹 생성
        temp_group, self.temp_slider, self.temp_label = create_slider_group("색온도", self.color_temp, 2000, 10000, 1000)
        brightness_group, self.brightness_slider, self.brightness_label = create_slider_group("밝기", self.brightness, 0, 200, 25)
        saturation_group, self.saturation_slider, self.saturation_label = create_slider_group("채도", self.saturation, 0, 200, 25)
        
        # 슬라이더에 포커스 관련 설정 추가
        self.temp_slider.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.brightness_slider.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.saturation_slider.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        
        # 초기화 버튼
        reset_button = QPushButton("초기화")
        reset_button.clicked.connect(self.reset_image_adjustments)
        
        # 확인 버튼
        apply_button = QPushButton("적용")
        apply_button.clicked.connect(self.apply_image_adjustments)
        
        # 취소 버튼
        cancel_button = QPushButton("취소")
        cancel_button.clicked.connect(self.cancel_image_adjustments)
        
        button_layout.addWidget(reset_button)
        button_layout.addWidget(apply_button)
        button_layout.addWidget(cancel_button)
        
        # 슬라이더 값 변경 시 이벤트 연결
        self.temp_slider.valueChanged.connect(lambda: self.preview_adjustments(self.temp_slider))
        self.brightness_slider.valueChanged.connect(lambda: self.preview_adjustments(self.brightness_slider))
        self.saturation_slider.valueChanged.connect(lambda: self.preview_adjustments(self.saturation_slider))
        
        # 슬라이더 슬립페이지 이벤트 분리 - 마우스 놓을 때만 업데이트
        self.temp_slider.sliderReleased.connect(self.force_update_preview)
        self.brightness_slider.sliderReleased.connect(self.force_update_preview)
        self.saturation_slider.sliderReleased.connect(self.force_update_preview)
        
        # 키보드 이벤트 추가
        self.temp_slider.keyPressEvent = lambda e: self.slider_key_press_event(e, self.temp_slider)
        self.brightness_slider.keyPressEvent = lambda e: self.slider_key_press_event(e, self.brightness_slider)
        self.saturation_slider.keyPressEvent = lambda e: self.slider_key_press_event(e, self.saturation_slider)
        
        # 레이아웃에 위젯 추가
        layout.addWidget(temp_group)
        layout.addWidget(brightness_group)
        layout.addWidget(saturation_group)
        layout.addLayout(button_layout)
        
        # 다이얼로그 표시 전에 미리보기 업데이트
        self.pending_temp = self.color_temp
        self.pending_brightness = self.brightness
        self.pending_saturation = self.saturation
        
        # 초기 미리보기 업데이트(타이머 없이 직접 실행)
        self.force_update_preview()
        
        # 다이얼로그 표시
        self.adjust_dialog.exec()

    def dialog_mouse_press_event(self, event):
        """다이얼로그 드래그를 위한 마우스 누르기 이벤트"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging_dialog = True
            self.drag_dialog_pos = event.globalPosition().toPoint() - self.adjust_dialog.pos()
            event.accept()
    
    def dialog_mouse_move_event(self, event):
        """다이얼로그 드래그를 위한 마우스 이동 이벤트"""
        if self.dragging_dialog and event.buttons() & Qt.MouseButton.LeftButton:
            self.adjust_dialog.move(event.globalPosition().toPoint() - self.drag_dialog_pos)
            event.accept()
    
    def dialog_mouse_release_event(self, event):
        """다이얼로그 드래그를 위한 마우스 놓기 이벤트"""
        self.dragging_dialog = False
    
    def slider_key_press_event(self, event, slider):
        """슬라이더의 키보드 이벤트 처리"""
        step = slider.pageStep() // 4 or 1  # pageStep의 1/4 또는 최소 1
        
        if event.key() == Qt.Key.Key_Left:
            slider.setValue(slider.value() - step)
            event.accept()
        elif event.key() == Qt.Key.Key_Right:
            slider.setValue(slider.value() + step)
            event.accept()
        else:
            # 기본 키 이벤트 처리
            type(slider).__base__.keyPressEvent(slider, event)

    def preview_adjustments(self, focused_slider=None):
        """슬라이더 값에 따라 이미지 미리보기를 업데이트합니다."""
        # 슬라이더 값 가져오기
        temp = self.temp_slider.value()
        brightness = self.brightness_slider.value()
        saturation = self.saturation_slider.value()
        
        # 레이블 업데이트만 즉시 수행 (UI 반응성 유지)
        self.temp_label.setText(f"색온도: {temp}K")
        self.brightness_label.setText(f"밝기: {brightness}%")
        self.saturation_label.setText(f"채도: {saturation}%")
        
        # 보류 중인 값 저장 (마지막으로 적용될 값)
        self.pending_temp = temp
        self.pending_brightness = brightness
        self.pending_saturation = saturation
        
        # 슬라이더에 포커스 설정
        if focused_slider:
            focused_slider.setFocus()
        
        # 이미 타이머가 활성화되어 있으면 추가 처리 생략 (디바운싱)
        if self.update_timer.isActive():
            return
            
        # 타이머 시작 (100ms 후에 이미지 처리 수행)
        self.update_timer.start()
    
    def apply_pending_update(self):
        """지연된 업데이트를 적용합니다."""
        # 현재 활성화된 처리 스레드가 있으면 중지
        if hasattr(self, 'processor') and self.processor is not None and self.processor.isRunning():
            self.processor.quit()  # 작업이 실패할 수 있으므로 종료만 요청
            # 스레드가 종료될 시간을 주지 않고 바로 다음 스레드 생성
            # 무한정 기다리면 UI가 멈출 수 있음
        
        # 저장된 값으로 업데이트
        temp = self.pending_temp
        brightness = self.pending_brightness
        saturation = self.pending_saturation
        
        # 미리보기 이미지 크기를 더 작게 조정 (슬라이더 움직임 중에는 더 작은 이미지로 처리)
        SMALL_PREVIEW_SIZE = 200  # 더 작은 미리보기 크기
        
        # 미리보기용 작은 이미지 생성 (처리 속도 향상)
        temp_preview = self.preview_pixmap.scaled(
            SMALL_PREVIEW_SIZE, SMALL_PREVIEW_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation
        )
        
        # 이미지 처리를 별도 스레드에서 실행
        self.processor = ImageProcessor(
            temp_preview,  # 작은 미리보기 이미지 사용
            temp, 
            brightness, 
            saturation
        )
        # 처리 완료 시 콜백 연결
        self.processor.finished.connect(self.update_processed_image_and_unlock)
        
        # 스레드 시작 (우선순위 낮게 설정)
        self.processor.start(QThread.Priority.LowPriority)

    def update_processed_image_and_unlock(self, processed_pixmap):
        """이미지 처리 결과를 업데이트하고 처리 잠금을 해제합니다."""
        # 처리된 이미지의 깊은 복사본 생성 후 적용
        self.pixmap = processed_pixmap.copy()
        
        # 위젯 화면 갱신
        self.update()
        
        # 처리 잠금 해제
        self.is_processing = False

    def apply_image_adjustments(self):
        """조정된 이미지를 적용하고 다이얼로그를 닫습니다."""
        try:
            # 현재 슬라이더 값을 저장
            self.color_temp = self.temp_slider.value()
            self.brightness = self.brightness_slider.value()
            self.saturation = self.saturation_slider.value()
            
            # 이미 처리 중인 경우 취소
            if hasattr(self, 'is_processing') and self.is_processing:
                return
                
            # 원본 이미지가 없는 경우 현재 이미지 사용
            if self.original_pixmap is None or self.original_pixmap.isNull():
                self.original_pixmap = self.pixmap.copy()
            
            # 처리 중 플래그 설정
            self.is_processing = True
            
            # 진행 중인 처리가 있으면 중지
            if hasattr(self, 'final_processor') and self.final_processor is not None and self.final_processor.isRunning():
                self.final_processor.quit()
                
            # 다이얼로그 버튼 비활성화
            if hasattr(self, 'adjust_dialog') and self.adjust_dialog:
                for button in self.adjust_dialog.findChildren(QPushButton):
                    button.setEnabled(False)
                
            # 마지막으로 원본 이미지에 최종 효과 적용
            self.final_processor = ImageProcessor(
                self.original_pixmap,  # 원본 이미지 사용
                self.color_temp,
                self.brightness,
                self.saturation
            )
            
            # 처리 완료 시 콜백 연결
            self.final_processor.finished.connect(self.finalize_adjustments)
            
            # 스레드 시작
            self.final_processor.start()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[이미지 조정] 적용 중 오류 발생: {e}")
            self.is_processing = False
            
            # 다이얼로그 닫기
            if hasattr(self, 'adjust_dialog') and self.adjust_dialog:
                self.adjust_dialog.accept()
    
    def finalize_adjustments(self, final_pixmap):
        """이미지 조정 결과를 최종 적용하고 다이얼로그를 닫습니다."""
        try:
            # 결과 깊은 복사 생성
            final_result = final_pixmap.copy()
            
            # 좌우 반전 유지 (고품질 변환 사용)
            if self.is_flipped:
                transform = QTransform()
                transform.scale(-1, 1)
                final_result = final_result.transformed(transform, Qt.TransformationMode.SmoothTransformation)
                final_result = final_result.copy()  # 변환 후에도 깊은 복사
            
            # 최종 결과 적용 - 원본 크기로 복원 (필요한 경우)
            if final_result.size() != self.original_pixmap.size():
                final_result = final_result.scaled(
                    self.original_pixmap.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                final_result = final_result.copy()  # 스케일링 후에도 깊은 복사
            
            self.pixmap = final_result
            self.update()
            
            # 처리 플래그 해제
            self.is_processing = False
            
            # 다이얼로그 닫기
            if hasattr(self, 'adjust_dialog') and self.adjust_dialog:
                self.adjust_dialog.accept()
                
            # 파라미터 출력
            print(f"이미지 효과 적용 완료: 색온도={self.color_temp}K, 밝기={self.brightness}%, 채도={self.saturation}%")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[이미지 조정] 최종화 중 오류 발생: {e}")
            self.is_processing = False
            
            # 다이얼로그 닫기
            if hasattr(self, 'adjust_dialog') and self.adjust_dialog:
                self.adjust_dialog.accept()
    
    def cancel_image_adjustments(self):
        """이미지 조정을 취소하고 원래 이미지로 복원합니다."""
        # 백업 이미지로 복원
        if hasattr(self, 'backup_pixmap'):
            self.pixmap = self.backup_pixmap.copy()
            self.update()
        
        # 처리 중인 스레드 중지
        self.stop_all_threads()
        
        # 다이얼로그 닫기
        if hasattr(self, 'adjust_dialog') and self.adjust_dialog:
            self.adjust_dialog.reject()
    
    def stop_all_threads(self):
        """모든 실행 중인 이미지 처리 스레드를 중지합니다."""
        # 미리보기 처리 스레드 중지
        if hasattr(self, 'processor') and self.processor is not None and self.processor.isRunning():
            self.processor.quit()
            
        # 최종 처리 스레드 중지
        if hasattr(self, 'final_processor') and self.final_processor is not None and self.final_processor.isRunning():
            self.final_processor.quit()
    
    def reset_image_adjustments(self):
        """이미지 조정을 초기값으로 되돌립니다."""
        # 슬라이더 초기화
        self.temp_slider.setValue(6500)  # 기본 색온도
        self.brightness_slider.setValue(100)  # 기본 밝기
        self.saturation_slider.setValue(100)  # 기본 채도
        
        # 미리보기 업데이트
        self.preview_adjustments()
    
    def apply_image_effects(self, temp, brightness, saturation):
        """이미지에 색온도, 밝기, 채도 효과를 적용합니다."""
        try:
            # ImageAdjuster 클래스를 사용하여 효과 적용
            if self.original_pixmap is None or self.original_pixmap.isNull():
                print("[이미지 조정] 원본 이미지가 없습니다. 현재 이미지를 원본으로 사용합니다.")
                self.original_pixmap = self.pixmap.copy()
                
            # 좌우 반전 상태 저장
            was_flipped = self.is_flipped
            
            # preview_pixmap이 없는 경우(불러오기 시) 원본 이미지 사용
            source_pixmap = None
            if hasattr(self, 'preview_pixmap') and not self.preview_pixmap.isNull():
                # 항상 미리보기 이미지의 깊은 복사본 사용
                source_pixmap = self.preview_pixmap.copy()
            else:
                # 원본 이미지의 깊은 복사본 사용
                source_pixmap = self.original_pixmap.copy()
                
                # preview_pixmap 설정 - 고품질 스케일링 적용
                self.preview_pixmap = self.original_pixmap.scaled(
                    self.original_pixmap.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                # preview_pixmap도 깊은 복사본으로 설정
                self.preview_pixmap = self.preview_pixmap.copy()
                
                print(f"[이미지 조정] 미리보기 이미지 생성: {source_pixmap.width()}x{source_pixmap.height()}")
            
            # 효과 적용
            print(f"[이미지 조정] 효과 적용 시작: 색온도={temp}K, 밝기={brightness}%, 채도={saturation}%")
            adjusted_pixmap = ImageAdjuster.apply_effects(
                source_pixmap,  # 미리보기 또는 원본 이미지의 복사본 사용
                temp, 
                brightness, 
                saturation
            )
            
            # 결과 적용 - 항상 깊은 복사본 사용
            if not adjusted_pixmap.isNull():
                # 이미지 객체가 별도의 메모리를 사용하도록 명시적 복사
                self.pixmap = adjusted_pixmap.copy()
                
                # 좌우 반전이 적용되어 있었다면 다시 적용 (고품질 변환 사용)
                if was_flipped:
                    transform = QTransform()
                    transform.scale(-1, 1)
                    self.pixmap = self.pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)
                    # 변환 후에도 복사본 생성
                    self.pixmap = self.pixmap.copy()
                
                # 위젯 업데이트
                self.update()
                print(f"[이미지 조정] 효과 적용 성공: 색온도={temp}K, 밝기={brightness}%, 채도={saturation}%")
            else:
                print("[이미지 조정] 효과 적용 실패: 결과 이미지가 유효하지 않습니다.")
                # 원본으로 복원
                self.pixmap = self.original_pixmap.copy()
                if was_flipped:
                    transform = QTransform()
                    transform.scale(-1, 1)
                    self.pixmap = self.pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)
                    self.pixmap = self.pixmap.copy()
                self.update()
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[이미지 조정] 오류 발생: {e}")
            # 오류 발생 시 원본으로 복원
            if hasattr(self, 'original_pixmap') and not self.original_pixmap.isNull():
                self.pixmap = self.original_pixmap.copy()
                if hasattr(self, 'is_flipped') and self.is_flipped:
                    transform = QTransform()
                    transform.scale(-1, 1)
                    self.pixmap = self.pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)
                    self.pixmap = self.pixmap.copy()
                self.update()
    
    def deleteLater(self):
        """가구 아이템이 삭제될 때 하단 패널을 업데이트합니다."""
        # 부모 캔버스에서 가구 아이템 목록에서 제거
        canvas = self.parent()
        if canvas and hasattr(canvas, 'furniture_items'):
            if self in canvas.furniture_items:
                canvas.furniture_items.remove(self)
                canvas.update_bottom_panel()
        super().deleteLater()

    def force_update_preview(self):
        """즉시 미리보기를 강제로 업데이트합니다. (슬라이더 놓을 때 호출)"""
        # 타이머 중지
        self.update_timer.stop()
        
        # 처리 중이면 건너뜀
        if hasattr(self, 'is_processing') and self.is_processing:
            return
            
        # 처리 중 표시
        self.is_processing = True
        
        # 현재 스레드 중지
        if hasattr(self, 'processor') and self.processor is not None and self.processor.isRunning():
            self.processor.quit()
            
        # 저장된 값으로 업데이트
        temp = self.pending_temp
        brightness = self.pending_brightness
        saturation = self.pending_saturation
        
        # 고품질 미리보기 처리
        self.processor = ImageProcessor(
            self.preview_pixmap,
            temp,
            brightness,
            saturation
        )
        
        # 처리 완료 시 콜백 연결
        self.processor.finished.connect(self.update_processed_image_and_unlock)
        
        # 스레드 시작
        self.processor.start()
        
    def update_processed_image_and_unlock(self, processed_pixmap):
        """이미지 처리 결과를 업데이트하고 처리 잠금을 해제합니다."""
        # 처리된 이미지의 깊은 복사본 생성 후 적용
        self.pixmap = processed_pixmap.copy()
        
        # 위젯 화면 갱신
        self.update()
        
        # 처리 잠금 해제
        self.is_processing = False

class Canvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumSize(800, 600)
        self.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 2px solid #2C3E50;
            }
        """)
        
        # 이미지 조정 시스템 초기화
        if not ImageAdjuster._initialized:
            ImageAdjuster.initialize()
        
        # 레이아웃 설정
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # 여백 제거
        
        # 캔버스 영역
        self.canvas_area = QWidget()
        self.canvas_area.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 2px solid #2C3E50;
            }
        """)
        layout.addWidget(self.canvas_area)
        
        # 초기 상태 설정
        self.is_new_collage = True
        self.furniture_items = []
        
        # 우클릭 메뉴 활성화
        self.canvas_area.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.canvas_area.customContextMenuRequested.connect(self.show_context_menu)
    
    def show_context_menu(self, position):
        """캔버스 영역에서 우클릭했을 때 컨텍스트 메뉴를 표시합니다."""
        menu = QMenu(self)
        
        # 메뉴 아이템 추가
        save_action = menu.addAction("저장하기")
        load_action = menu.addAction("불러오기")
        menu.addSeparator()
        new_action = menu.addAction("새 콜라주")
        export_action = menu.addAction("내보내기")
        
        # 메뉴 아이템 동작 연결
        save_action.triggered.connect(self.save_collage)
        load_action.triggered.connect(self.load_collage)
        new_action.triggered.connect(self.create_new_collage)
        export_action.triggered.connect(self.export_collage)
        
        # 메뉴 표시
        menu.exec(self.canvas_area.mapToGlobal(position))
    
    def save_collage(self):
        """현재 콜라주를 JSON 파일로 저장합니다."""
        if not self.furniture_items and self.is_new_collage:
            QMessageBox.warning(self, "경고", "저장할 콜라주가 없습니다.")
            return
        
        # 파일 저장 다이얼로그
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "콜라주 저장",
            os.path.expanduser("~/Desktop/collage.json"),
            "JSON 파일 (*.json);;모든 파일 (*.*)"
        )
        
        if file_path:
            try:
                # 저장할 데이터 생성
                collage_data = {
                    "canvas": {
                        "width": self.canvas_area.width(),
                        "height": self.canvas_area.height(),
                        "saved_at": datetime.datetime.now().isoformat(),
                        "last_modified": datetime.datetime.now().isoformat()
                    },
                    "furniture_items": []
                }
                
                # 가구 아이템 정보 수집
                for i, item in enumerate(self.furniture_items):
                    # 좌우 반전 여부 확인 (pixmap이 원본과 다른지 확인)
                    is_flipped = hasattr(item, 'is_flipped') and item.is_flipped
                    
                    item_data = {
                        "id": item.furniture.id,
                        "position": {
                            "x": item.pos().x(),
                            "y": item.pos().y()
                        },
                        "size": {
                            "width": item.width(),
                            "height": item.height()
                        },
                        "z_order": i,  # 리스트 순서대로 z-order 저장
                        "is_flipped": is_flipped,
                        "image_adjustments": {
                            "color_temp": item.color_temp,
                            "brightness": item.brightness,
                            "saturation": item.saturation
                        }
                    }
                    collage_data["furniture_items"].append(item_data)
                
                # JSON으로 저장
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(collage_data, f, ensure_ascii=False, indent=2)
                
                QMessageBox.information(self, "성공", "콜라주가 성공적으로 저장되었습니다.")
                
            except Exception as e:
                QMessageBox.critical(self, "오류", f"콜라주 저장 중 오류가 발생했습니다: {str(e)}")
    
    def load_collage(self):
        """저장된 콜라주를 JSON 파일에서 불러옵니다."""
        # 파일 열기 다이얼로그
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "콜라주 불러오기",
            os.path.expanduser("~/Desktop"),
            "JSON 파일 (*.json);;모든 파일 (*.*)"
        )
        
        if file_path:
            try:
                # JSON 파일 로드
                with open(file_path, 'r', encoding='utf-8') as f:
                    collage_data = json.load(f)
                
                # 기존 가구 아이템 제거
                for item in self.furniture_items:
                    item.deleteLater()
                self.furniture_items.clear()
                
                # 캔버스 크기 설정
                canvas_width = collage_data["canvas"]["width"]
                canvas_height = collage_data["canvas"]["height"]
                self.canvas_area.setFixedSize(canvas_width, canvas_height)
                self.is_new_collage = False
                
                # 가구 아이템 불러오기
                furniture_items_data = collage_data["furniture_items"]
                
                # Supabase 클라이언트 생성
                supabase = SupabaseClient()
                
                # 모든 가구 데이터 가져오기
                all_furniture = supabase.get_furniture_list()
                
                # 딕셔너리로 변환 (id를 키로 사용)
                furniture_dict = {}
                for furniture_data in all_furniture:
                    furniture_dict[furniture_data["id"]] = furniture_data
                
                for item_data in sorted(furniture_items_data, key=lambda x: x["z_order"]):
                    furniture_id = item_data["id"]
                    
                    # 가구 ID로 데이터베이스에서 가구 정보 검색
                    if furniture_id in furniture_dict:
                        # 딕셔너리 데이터로 Furniture 객체 생성
                        furniture_data = furniture_dict[furniture_id]
                        furniture = Furniture(**furniture_data)
                        
                        # 가구 아이템 생성
                        item = FurnitureItem(furniture, self.canvas_area)
                        
                        # 위치와 크기 설정
                        item.move(QPoint(item_data["position"]["x"], item_data["position"]["y"]))
                        item.setFixedSize(item_data["size"]["width"], item_data["size"]["height"])
                        
                        # 좌우 반전 설정
                        if item_data.get("is_flipped", False):
                            transform = QTransform()
                            transform.scale(-1, 1)  # x축 방향으로 -1을 곱하여 좌우 반전
                            item.pixmap = item.pixmap.transformed(transform)
                            item.is_flipped = True
                        
                        # 이미지 조정 설정
                        if "image_adjustments" in item_data:
                            adjustments = item_data["image_adjustments"]
                            item.color_temp = adjustments.get("color_temp", 6500)
                            item.brightness = adjustments.get("brightness", 100)
                            item.saturation = adjustments.get("saturation", 100)
                            
                            # 이미지 효과 적용
                            if (item.color_temp != 6500 or 
                                item.brightness != 100 or 
                                item.saturation != 100):
                                # 로드 시에는 원본 이미지가 생성되어 있는지 확인
                                if item.original_pixmap is None or item.original_pixmap.isNull():
                                    item.original_pixmap = item.pixmap.copy()
                                    print(f"[불러오기] 원본 이미지 복사: {furniture.name}")
                                
                                # 불러오기 시 원본 이미지 사이즈 확인
                                print(f"[불러오기] 이미지 크기: {item.original_pixmap.width()}x{item.original_pixmap.height()}")
                                
                                # 미리보기 이미지 속성 설정
                                item.preview_pixmap = item.original_pixmap.copy()
                                
                                # 이미지 효과 적용
                                print(f"[불러오기] 이미지 효과 적용: 색온도={item.color_temp}K, 밝기={item.brightness}%, 채도={item.saturation}%")
                                item.apply_image_effects(
                                    item.color_temp, 
                                    item.brightness, 
                                    item.saturation
                                )
                            
                        item.show()
                        self.furniture_items.append(item)
                    else:
                        print(f"가구 ID를 찾을 수 없습니다: {furniture_id}")
                
                # 하단 패널 업데이트
                self.update_bottom_panel()
                
                # 윈도우 크기 조정 (수정된 부분)
                window = self.window()
                if window:
                    # 현재 윈도우 크기 가져오기
                    current_width = window.width()
                    current_height = window.height()
                    
                    # 기본 여백 설정
                    right_panel_width = 400  # 우측 패널 너비
                    top_margin = 100  # 상단 여유 공간
                    
                    # 캔버스 기반 최소 크기 계산
                    canvas_based_width = canvas_width + right_panel_width
                    canvas_based_height = canvas_height + top_margin
                    
                    # 최소 윈도우 크기 계산 (현재 크기와 캔버스 기반 크기 중 더 큰 값 사용)
                    # 단, 기본 최소 크기(1200, 800)보다는 작아지지 않도록 설정
                    new_width = max(1200, current_width, canvas_based_width)
                    new_height = max(800, current_height, canvas_based_height)
                    
                    # 윈도우 크기 조정
                    window.setMinimumSize(new_width, new_height)
                    window.resize(new_width, new_height)
                
                QMessageBox.information(self, "성공", "콜라주가 성공적으로 불러와졌습니다.")
                
            except Exception as e:
                import traceback
                traceback.print_exc()  # 자세한 오류 정보 출력
                QMessageBox.critical(self, "오류", f"콜라주 불러오기 중 오류가 발생했습니다: {str(e)}")
    
    def create_new_collage(self):
        """새 콜라주를 생성합니다."""
        dialog = CanvasSizeDialog(self)
        if dialog.exec():
            width, height = dialog.get_size()
            
            # 기존 가구 아이템 제거
            for item in self.furniture_items:
                item.deleteLater()
            self.furniture_items.clear()
            
            # 캔버스 크기 설정
            self.canvas_area.setFixedSize(width, height)
            self.is_new_collage = False
            
            # 윈도우 크기 조정 (수정된 부분)
            window = self.window()
            if window:
                # 현재 윈도우 크기 가져오기
                current_width = window.width()
                current_height = window.height()
                
                # 기본 여백 설정
                right_panel_width = 400  # 우측 패널 너비
                top_margin = 100  # 상단 여유 공간
                
                # 캔버스 기반 최소 크기 계산
                canvas_based_width = width + right_panel_width
                canvas_based_height = height + top_margin
                
                # 최소 윈도우 크기 계산 (현재 크기와 캔버스 기반 크기 중 더 큰 값 사용)
                # 단, 기본 최소 크기(1200, 800)보다는 작아지지 않도록 설정
                new_width = max(1200, current_width, canvas_based_width)
                new_height = max(800, current_height, canvas_based_height)
                
                # 윈도우 크기 조정
                window.setMinimumSize(new_width, new_height)
                window.resize(new_width, new_height)
                
                # 캔버스 크기 조정
                self.setMinimumSize(width, height)
                self.resize(width, height)
            
            self.canvas_area.update()
            
            # 하단 패널 업데이트
            self.update_bottom_panel()
    
    def dragEnterEvent(self, event):
        """드래그 진입 이벤트를 처리합니다."""
        if event.mimeData().hasFormat("application/x-furniture"):
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        """드래그 이동 이벤트를 처리합니다."""
        if event.mimeData().hasFormat("application/x-furniture"):
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        """드롭 이벤트를 처리합니다."""
        try:
            if event.mimeData().hasFormat("application/x-furniture"):
                # 드롭 위치 계산 (캔버스 영역 기준)
                drop_pos = self.canvas_area.mapFrom(self, event.position().toPoint())
                
                # MIME 데이터에서 가구 정보 추출
                furniture_data = eval(event.mimeData().data("application/x-furniture").data().decode())
                
                # Furniture 객체 생성
                furniture = Furniture(**furniture_data)
                
                # 가구 아이템 생성 및 추가
                item = FurnitureItem(furniture, self.canvas_area)
                item.move(drop_pos - QPoint(item.width() // 2, item.height() // 2))  # 드롭 위치 기준으로 중앙에 배치
                item.show()
                self.furniture_items.append(item)
                
                # 하단 패널 업데이트
                self.update_bottom_panel()
                
                event.acceptProposedAction()
        except Exception as e:
            print(f"드롭 이벤트 처리 중 오류 발생: {e}")
            event.ignore()
    
    def update_bottom_panel(self):
        """하단 패널을 업데이트합니다."""
        # 메인 윈도우에서 하단 패널 업데이트
        main_window = self.window()
        if main_window:
            main_window.update_bottom_panel()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 배경 그리기
        painter.fillRect(self.rect(), QColor("#ffffff"))
        
        # 가이드라인 그리기
        if self.is_new_collage:
            pen = QPen(QColor("#2C3E50"))
            pen.setStyle(Qt.PenStyle.DashLine)
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(self.rect().adjusted(10, 10, -10, -10))
        else:
            # 캔버스 크기 표시
            pen = QPen(QColor("#2C3E50"))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
            
            # 크기 텍스트 표시
            painter.setPen(QPen(QColor("#2C3E50")))
            size_text = f"{self.width()} x {self.height()} px"
            painter.drawText(self.rect().adjusted(10, 10, -10, -10), 
                          Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                          size_text)
    
    def export_collage(self):
        """현재 콜라주를 이미지로 내보냅니다."""
        if not self.furniture_items:
            QMessageBox.warning(self, "경고", "내보낼 콜라주가 없습니다.")
            return
        
        # 파일 저장 다이얼로그
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "콜라주 저장",
            os.path.expanduser("~/Desktop/collage.png"),
            "PNG 이미지 (*.png);;JPEG 이미지 (*.jpg);;모든 파일 (*.*)"
        )
        
        if file_path:
            try:
                # 캔버스 영역의 크기로 이미지 생성
                image = QPixmap(self.canvas_area.size())
                image.fill(Qt.GlobalColor.white)
                
                # 이미지에 현재 콜라주 그리기
                painter = QPainter(image)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                
                # 모든 가구 아이템 그리기
                for item in self.furniture_items:
                    # 아이템의 위치를 캔버스 영역 기준으로 변환
                    pos = item.pos()
                    painter.drawPixmap(pos, item.pixmap.scaled(
                        item.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    ))
                
                painter.end()
                
                # 이미지 저장
                image.save(file_path)
                QMessageBox.information(self, "성공", "콜라주가 성공적으로 저장되었습니다.")
                
            except Exception as e:
                QMessageBox.critical(self, "오류", f"이미지 저장 중 오류가 발생했습니다: {str(e)}") 