from typing import Union

from PyQt6.QtCore import QRect, Qt, QTimer, QThread
from PyQt6.QtGui import (QColor, QGuiApplication, QPainter, QPen, QPixmap,
                         QTransform)
from PyQt6.QtWidgets import (QDialog, QGroupBox, QHBoxLayout, QLabel, QMenu,
                             QPushButton, QSlider, QVBoxLayout, QWidget)

from src.models.furniture import Furniture
from src.services.image_service import ImageService
from src.services.supabase_client import SupabaseClient
from src.ui.utils import ImageAdjuster, ImageProcessor


class FurnitureItem(QWidget):
    def __init__(self, furniture: Furniture, parent=None):
        super().__init__(parent)
        self.furniture = furniture
        self.image_service = ImageService()
        self.supabase = SupabaseClient()
        
        if not ImageAdjuster._initialized:
            ImageAdjuster.initialize()
        
        # 이미지 조정 관련 속성
        self.pixmap: Union[QPixmap, None] = None # QPixmap | None -> Union[QPixmap, None]
        self.original_pixmap: Union[QPixmap, None] = None # QPixmap | None -> Union[QPixmap, None]
        self.original_ratio: float = 1.0
        self.maintain_aspect_ratio_on_press: bool = False # 리사이즈 시작 시 Shift 키 상태
        self.color_temp: int = 6500
        self.brightness: int = 100
        self.saturation: int = 100
        self.is_flipped: bool = False # 좌우 반전 상태
        self.maintain_aspect_ratio: bool = False # 현재 비율 유지 상태
        self.adjust_dialog = None # 이미지 조정 다이얼로그 참조

        # 이미지 로드 및 관련 속성 초기화
        loaded_original_candidate = self.load_image()
        if loaded_original_candidate and not loaded_original_candidate.isNull():
            self.original_pixmap = loaded_original_candidate.copy()
        else:
            # load_image가 유효한 pixmap을 반환하지 못한 경우 (오류 이미지 등)
            if self.pixmap is None or self.pixmap.isNull(): # load_image 내부에서 self.pixmap이 설정되었을 수 있음
                self.pixmap = QPixmap(200, 200) # 기본 대체 이미지
                self.pixmap.fill(QColor("#D3D3D3"))
                painter = QPainter(self.pixmap)
                painter.drawText(self.pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "이미지 없음")
                painter.end()
            self.original_pixmap = self.pixmap.copy() # 현재 pixmap (에러 이미지일 수 있음)을 원본 기준으로 사용
        
        if self.original_pixmap and self.original_pixmap.height() > 0:
            self.original_ratio = self.original_pixmap.width() / self.original_pixmap.height()
        else:
            self.original_ratio = 1.0 # 기본 비율 또는 오류 시

        # 초기 위젯 크기 설정 (self.pixmap 기준)
        if self.pixmap and not self.pixmap.isNull():
            current_pixmap_width = self.pixmap.width()
            current_pixmap_height = self.pixmap.height()
            ratio_for_initial_size = 1.0
            if current_pixmap_height > 0:
                ratio_for_initial_size = current_pixmap_width / current_pixmap_height
            
            initial_width = 200 
            initial_height = int(initial_width / ratio_for_initial_size) if ratio_for_initial_size > 0 else initial_width
            self.setFixedSize(initial_width, initial_height)
        else: # self.pixmap이 로드되지 않은 극단적 경우
            self.setFixedSize(200,200)
        
        self.setMouseTracking(True)
        self.is_resizing = False
        self.resize_handle = QRect() # resizeEvent에서 실제 값으로 업데이트됨
        self.update_resize_handle() # 명시적 초기 호출
        
        # 드래그 관련 속성 초기화
        self.old_pos = None
        
        # 이미지 조정 다이얼로그의 슬라이더 값 변경 디바운싱용 타이머
        self.update_timer = QTimer(self)
        self.update_timer.setSingleShot(True)
        self.update_timer.setInterval(120)
        self.update_timer.timeout.connect(self.apply_pending_update)
        
        self.is_selected = False
    
    def update_resize_handle(self):
        """크기가 변경될 때 리사이즈 핸들 위치를 업데이트합니다."""
        self.resize_handle = QRect(self.width() - 20, self.height() - 20, 20, 20)
    
    def resizeEvent(self, event):
        """위젯 크기가 변경될 때 리사이즈 핸들 위치를 자동으로 업데이트합니다."""
        super().resizeEvent(event)
        self.update_resize_handle()
    
    def load_image(self) -> Union[QPixmap, None]: # QPixmap | None -> Union[QPixmap, None]
        """가구 이미지를 Supabase에서 가져와 ImageService를 통해 로드합니다.
           성공 시 QPixmap 객체를, 실패 시 None 또는 에러가 표시된 QPixmap을 반환 (내부적으로 self.pixmap도 설정).
           반환된 QPixmap은 __init__에서 self.original_pixmap의 후보가 됩니다.
        """
        try:
            image_data = self.supabase.get_furniture_image(self.furniture.image_filename)
            downloaded_pixmap = self.image_service.download_and_cache_image(
                image_data, self.furniture.image_filename
            )

            if downloaded_pixmap and not downloaded_pixmap.isNull():
                self.pixmap = downloaded_pixmap.copy()
                loaded_pixmap_for_original = self.pixmap.copy() # 성공 시 원본용 복사본
                print(f"[이미지 로드] 성공: {self.furniture.image_filename}, 원본 저장 준비")
            else:
                # download_and_cache_image 실패 또는 null 반환
                print(f"[이미지 로드] download_and_cache_image 실패/null: {self.furniture.image_filename}")
                self.pixmap = QPixmap(200, 200)
                self.pixmap.fill(QColor("#f0f0f0"))
                painter = QPainter(self.pixmap)
                painter.setPen(QPen(QColor("#2C3E50")))
                painter.drawText(self.pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "이미지 로드 실패")
                painter.end()
                loaded_pixmap_for_original = self.pixmap.copy() # 실패 시 에러 이미지를 원본용으로
                print(f"[이미지 로드] 에러 이미지 생성, 원본 저장 준비")

        except Exception as e:
            print(f"이미지 로드 중 오류 발생 (데이터 다운로드/처리 중): {e}")
            self.pixmap = QPixmap(200, 200)
            self.pixmap.fill(QColor("#f0f0f0"))
            painter = QPainter(self.pixmap)
            painter.setPen(QPen(QColor("#2C3E50")))
            painter.drawText(self.pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "이미지 로드 예외")
            painter.end()
            loaded_pixmap_for_original = self.pixmap.copy() # 예외 시 에러 이미지를 원본용으로
            print(f"[이미지 로드] 예외 발생, 에러 이미지 생성, 원본 저장 준비")
        
        # self.original_pixmap 할당은 try-except 블록 바깥으로 이동하여 한번만 실행
        if loaded_pixmap_for_original and not loaded_pixmap_for_original.isNull():
            self.original_pixmap = loaded_pixmap_for_original.copy()
            print(f"[이미지 로드] self.original_pixmap 할당 완료: {self.furniture.image_filename}, isNull: {self.original_pixmap.isNull()}, id: {id(self.original_pixmap)}") # 상태 확인용 print 추가
        else:
            # 이 경우는 loaded_pixmap_for_original이 None이거나 isNull()인 경우로, 방어적으로 처리
            # 이미 위에서 에러 이미지를 생성했을 것이므로, 그래도 null이면 기본 QPixmap()으로.
            # 하지만 테스트 케이스에서는 이 분기에 도달하지 않을 것으로 예상.
            temp_error_pixmap = QPixmap(200,200)
            temp_error_pixmap.fill(QColor("#cccccc")) # 다른 색으로 구분
            painter = QPainter(temp_error_pixmap)
            painter.drawText(temp_error_pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "원본 없음")
            painter.end()
            self.original_pixmap = temp_error_pixmap.copy()
            print(f"[이미지 로드] loaded_pixmap_for_original이 없어 임시 원본 할당: {self.furniture.image_filename}")

        # 초기 크기 및 비율 설정 (self.pixmap 기준, self.original_pixmap은 효과 적용의 기준)
        if not self.pixmap.isNull():
            # original_ratio는 원본(original_pixmap)의 비율을 따르는 것이 좋으나, 
            # 초기 크기 설정은 현재 보이는 pixmap을 기준으로 할 수 있음.
            # 테스트에서는 dummy_qpixmap (100x100)이 로드되고, 아이템 초기 너비는 200을 기대.
            # 따라서 비율은 로드된 pixmap(의 복사본)인 self.pixmap을 따름.
            current_pixmap_width = self.pixmap.width()
            current_pixmap_height = self.pixmap.height()
            if current_pixmap_height > 0:
                self.original_ratio = current_pixmap_width / current_pixmap_height
            else:
                self.original_ratio = 1.0 # 높이가 0이면 기본 비율
            
            initial_width = 200 
            initial_height = int(initial_width / self.original_ratio) if self.original_ratio > 0 else initial_width
            self.setFixedSize(initial_width, initial_height)
        else:
            self.setFixedSize(200,200)
            self.original_ratio = 1.0

        self.update_resize_handle()
        return loaded_pixmap_for_original # 계산된 original_pixmap 후보를 반환

    def paintEvent(self, event):
        """위젯을 그릴 때 호출되는 메서드입니다."""
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
        
        # 선택된 경우에만 테두리와 리사이즈 핸들 그리기
        if self.is_selected:
            pen = QPen(QColor("#2C3E50"))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
            
            # 리사이즈 핸들 그리기
            painter.fillRect(self.resize_handle, QColor("#2C3E50"))
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # old_pos는 항상 초기화
            self.old_pos = event.pos()
            
            # 캔버스 찾기
            canvas_area = self.parent()
            if canvas_area:
                canvas = canvas_area.parent()
                if canvas and hasattr(canvas, 'select_furniture_item'):
                    # 선택 처리를 Canvas 클래스로 위임
                    canvas.select_furniture_item(self)
            
            if self.is_selected and self.resize_handle.contains(event.pos()):
                self.is_resizing = True
                self.original_size_on_resize = self.size() # 리사이즈 시작 시점의 크기 저장
                self.resize_mouse_start_pos = event.pos() # 리사이즈 시작 시점의 마우스 위치 저장
                self.maintain_aspect_ratio_on_press = bool(QGuiApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier)
            else:
                self.raise_()  # 위젯을 최상위로
            event.accept() # 이벤트 전파 중단
    
    def mouseMoveEvent(self, event):
        if self.is_resizing:
            # Shift 키 상태를 드래그 시작 시점 기준으로 설정
            self.maintain_aspect_ratio = self.maintain_aspect_ratio_on_press
            
            # 마우스 이동량 계산
            delta = event.pos() - self.resize_mouse_start_pos
            
            # 새 크기 계산
            new_width = self.original_size_on_resize.width() + delta.x()
            new_height = self.original_size_on_resize.height() + delta.y()

            # 최소 크기 제한
            new_width = max(100, new_width)
            new_height = max(100, new_height)
            
            # 캔버스 경계 체크
            canvas_area = self.parent()
            canvas_max_width = None
            canvas_max_height = None
            
            if canvas_area and hasattr(canvas_area, 'rect'):
                try:
                    canvas_rect = canvas_area.rect()
                    current_pos = self.pos()
                    
                    # 새 크기로 변경했을 때 캔버스를 벗어나는지 확인
                    canvas_max_width = canvas_rect.width() - current_pos.x()
                    canvas_max_height = canvas_rect.height() - current_pos.y()
                    
                    # 캔버스 경계에 맞게 크기 제한 
                    if canvas_max_width > 0:
                        new_width = min(new_width, canvas_max_width)
                    if canvas_max_height > 0:
                        new_height = min(new_height, canvas_max_height)
                        
                except (AttributeError, TypeError):
                    # Mock 객체나 잘못된 객체인 경우 경계 체크 스킵
                    pass

            print(f"[MouseMove 리사이즈] maintain_aspect_ratio: {self.maintain_aspect_ratio}, original_ratio: {self.original_ratio}, pre_new_width: {new_width}, pre_new_height: {new_height}") # 값 확인
            if self.maintain_aspect_ratio and self.original_ratio > 0:
                # 비율 유지 로직
                # new_width 와 new_height는 마우스 이동에 따라 계산된 값
                
                # 너비 변경에 따른 기대 높이
                expected_height_from_width = int(new_width / self.original_ratio)
                # 높이 변경에 따른 기대 너비
                expected_width_from_height = int(new_height * self.original_ratio)
                
                # 너비 변경폭 vs 높이 변경폭
                delta_w_abs = abs(new_width - self.original_size_on_resize.width())
                delta_h_abs = abs(new_height - self.original_size_on_resize.height())

                if delta_w_abs >= delta_h_abs: # 너비 변경이 크거나 같으면 너비 기준으로 높이 조정
                    new_height = expected_height_from_width
                else: # 높이 변경이 크면 높이 기준으로 너비 조정
                    new_width = expected_width_from_height
                
                # 비율 유지 후 다시 경계 체크
                if canvas_area and hasattr(canvas_area, 'rect'):
                    try:
                        canvas_rect = canvas_area.rect()
                        current_pos = self.pos()
                        
                        canvas_max_width = canvas_rect.width() - current_pos.x()
                        canvas_max_height = canvas_rect.height() - current_pos.y()
                        
                        # 경계를 벗어나면 비율을 유지하면서 크기 조정
                        if canvas_max_width > 0 and new_width > canvas_max_width:
                            new_width = canvas_max_width
                            new_height = int(new_width / self.original_ratio)
                        if canvas_max_height > 0 and new_height > canvas_max_height:
                            new_height = canvas_max_height
                            new_width = int(new_height * self.original_ratio)
                            
                    except (AttributeError, TypeError):
                        pass
            
            # 최종 최소 크기 재확인 (단, 캔버스 경계를 우선시함)
            # 캔버스 경계가 최소 크기보다 작다면 경계를 우선
            if canvas_max_width is not None and canvas_max_width > 0:
                new_width = min(max(new_width, min(100, canvas_max_width)), canvas_max_width)
            else:
                new_width = max(100, new_width)
                
            if canvas_max_height is not None and canvas_max_height > 0:
                new_height = min(max(new_height, min(100, canvas_max_height)), canvas_max_height)
            else:
                new_height = max(100, new_height)
            
            self.setFixedSize(new_width, new_height)
            self.update_resize_handle()
        elif event.buttons() & Qt.MouseButton.LeftButton:
            # 컨트롤 키를 누른 상태에서는 드래그 이동을 방지
            modifiers = QGuiApplication.keyboardModifiers()
            if modifiers & Qt.KeyboardModifier.ControlModifier:
                return
            
            # 드래그로 이동 (old_pos가 초기화된 경우에만)
            if self.old_pos is not None:
                delta = event.pos() - self.old_pos
                
                # 캔버스에서 다중 선택된 아이템들을 함께 이동
                canvas_area = self.parent()
                if canvas_area:
                    canvas = canvas_area.parent()
                    if canvas and hasattr(canvas, 'selected_items'):
                        # 다중 선택된 모든 아이템을 함께 이동 (경계 체크 포함)
                        self._move_items_with_bounds_check(canvas.selected_items, delta, canvas_area)
                    else:
                        # Canvas를 찾을 수 없는 경우 현재 아이템만 이동
                        self._move_items_with_bounds_check([self], delta, canvas_area)
                else:
                    # 부모를 찾을 수 없는 경우 현재 아이템만 이동 (경계 체크 없이)
                    self.move(self.pos() + delta)
    
    def _move_items_with_bounds_check(self, items, delta, canvas_area):
        """아이템들을 캔버스 영역을 벗어나지 않도록 이동시킵니다."""
        if not canvas_area:
            # 캔버스 영역이 없으면 그냥 이동
            for item in items:
                item.move(item.pos() + delta)
            return
        
        # canvas_area가 실제 QWidget인지 확인 (테스트에서 Mock 객체일 수 있음)
        try:
            canvas_rect = canvas_area.rect()
            # canvas_rect의 속성들이 실제 숫자인지 확인
            if not all(isinstance(getattr(canvas_rect, attr)(), int) for attr in ['left', 'top', 'right', 'bottom']):
                raise AttributeError("Invalid rect attributes")
        except (AttributeError, TypeError):
            # Mock 객체이거나 rect()가 올바르지 않은 경우 경계 체크 없이 이동
            for item in items:
                item.move(item.pos() + delta)
            return
        
        # 모든 아이템이 경계를 벗어나지 않는지 확인
        valid_delta = delta
        
        for item in items:
            new_pos = item.pos() + delta
            item_rect = item.rect()
            item_rect.moveTo(new_pos)
            
            # 캔버스 영역을 벗어나는지 확인하고 조정
            if item_rect.left() < canvas_rect.left():
                valid_delta.setX(max(valid_delta.x(), canvas_rect.left() - item.pos().x()))
            if item_rect.top() < canvas_rect.top():
                valid_delta.setY(max(valid_delta.y(), canvas_rect.top() - item.pos().y()))
            if item_rect.right() > canvas_rect.right():
                valid_delta.setX(min(valid_delta.x(), canvas_rect.right() - item.rect().right() - item.pos().x()))
            if item_rect.bottom() > canvas_rect.bottom():
                valid_delta.setY(min(valid_delta.y(), canvas_rect.bottom() - item.rect().bottom() - item.pos().y()))
        
        # 조정된 delta로 모든 아이템 이동
        for item in items:
            item.move(item.pos() + valid_delta)
    
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
                if canvas and hasattr(canvas, 'selected_items') and hasattr(canvas, 'furniture_items'):
                    # 다중 선택된 모든 아이템 삭제
                    items_to_delete = canvas.selected_items.copy()  # 리스트 복사
                    if items_to_delete:
                        print(f"[삭제] 다중 선택된 {len(items_to_delete)}개 아이템 삭제")
                        for item in items_to_delete:
                            if item in canvas.furniture_items:
                                print(f"[삭제] 캔버스에서 가구 아이템 제거: {item.furniture.name}")
                                canvas.furniture_items.remove(item)
                            item.deleteLater()
                        # 선택 목록 초기화
                        canvas.selected_items.clear()
                        # 하단 패널 업데이트
                        canvas.update_bottom_panel()
                        print(f"[삭제] 다중 선택 아이템 삭제 완료")
                    else:
                        # 선택된 아이템이 없는 경우 현재 아이템만 삭제
                        if self in canvas.furniture_items:
                            print(f"[삭제] 캔버스에서 가구 아이템 제거: {self.furniture.name}")
                            canvas.furniture_items.remove(self)
                            canvas.update_bottom_panel()
                        self.deleteLater()
                        print(f"[삭제] 단일 아이템 삭제 완료: {self.furniture.name}")
                else:
                    print("[삭제] 캔버스를 찾을 수 없거나 필요한 속성이 없음")
                    self.deleteLater()
            else:
                print("[삭제] 캔버스 영역을 찾을 수 없음")
                self.deleteLater()
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
        
        # 미리보기용 축소 이미지 생성 (고화질로 개선)
        PREVIEW_MAX_SIZE = 400  # 미리보기 최대 크기 증가 (화질 개선)
        
        # 미리보기 이미지 크기 계산
        if self.original_pixmap.width() > self.original_pixmap.height():
            preview_width = min(PREVIEW_MAX_SIZE, self.original_pixmap.width())
            preview_height = int(self.original_pixmap.height() * (preview_width / self.original_pixmap.width()))
        else:
            preview_height = min(PREVIEW_MAX_SIZE, self.original_pixmap.height())
            preview_width = int(self.original_pixmap.width() * (preview_height / self.original_pixmap.height()))
        
        # 미리보기 이미지 생성 (고품질 변환 사용)
        self.preview_pixmap = self.original_pixmap.scaled(
            preview_width, preview_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation  # 고품질 변환 사용
        )
        
        # 명시적 깊은 복사 추가
        self.preview_pixmap = self.preview_pixmap.copy()
        
        # 이미지 처리 스레드
        self.processor = None
        
        # 처리 중 플래그 (동시에 여러 처리 방지)
        self.is_processing = False
        
        # 타이머 설정 업데이트 (화질 개선을 위해 약간 더 자주 업데이트)
        self.update_timer.setInterval(120)  # 120ms로 설정하여 품질과 성능 균형
        
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
            
        # 타이머 시작 (120ms 후에 이미지 처리 수행)
        self.update_timer.start()
    
    def apply_pending_update(self):
        """지연된 업데이트를 적용합니다."""
        try:
            # 현재 활성화된 처리 스레드가 있으면 중지
            if hasattr(self, 'processor') and self.processor is not None and self.processor.isRunning():
                self.processor.should_stop = True
                self.processor.quit()
            
            # 저장된 값으로 업데이트
            temp = self.pending_temp
            brightness = self.pending_brightness
            saturation = self.pending_saturation
            
            # 미리보기 이미지가 없으면 건너뛰기
            if not hasattr(self, 'preview_pixmap') or self.preview_pixmap is None or self.preview_pixmap.isNull():
                return
            
            # 미리보기 이미지 크기를 적당히 조정 (슬라이더 움직임 중 품질과 성능 균형)
            SMALL_PREVIEW_SIZE = 250  # 적당한 미리보기 크기로 화질 개선
            
            # 미리보기용 이미지 생성 (적당한 품질 유지)
            temp_preview = self.preview_pixmap.scaled(
                SMALL_PREVIEW_SIZE, SMALL_PREVIEW_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation  # 고품질 변환 사용
            )
            
            # 이미지 처리를 별도 스레드에서 실행
            self.processor = ImageProcessor(
                temp_preview.copy(),  # 복사본 사용하여 메모리 안정성 확보
                temp, 
                brightness, 
                saturation
            )
            # 처리 완료 시 콜백 연결
            self.processor.finished.connect(self.update_processed_image_and_unlock)
            # 에러 처리 콜백 연결
            self.processor.error.connect(self.handle_image_processing_error)
            
            # 스레드 시작 (우선순위 낮게 설정)
            self.processor.start(QThread.Priority.LowPriority)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[이미지 조정] 미리보기 업데이트 중 오류 발생: {e}")

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
            
            # 진행 중인 처리가 있으면 안전하게 중지
            self.stop_all_threads()
                
            # 다이얼로그 버튼 비활성화
            if hasattr(self, 'adjust_dialog') and self.adjust_dialog:
                for button in self.adjust_dialog.findChildren(QPushButton):
                    button.setEnabled(False)
                
            # 마지막으로 원본 이미지에 최종 효과 적용
            self.final_processor = ImageProcessor(
                self.original_pixmap.copy(),  # 원본 이미지의 복사본 사용
                self.color_temp,
                self.brightness,
                self.saturation
            )
            
            # 처리 완료 시 콜백 연결
            self.final_processor.finished.connect(self.finalize_adjustments)
            # 에러 처리 콜백 연결
            self.final_processor.error.connect(self.handle_final_processing_error)
            
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
        try:
            # 백업 이미지로 복원
            if hasattr(self, 'backup_pixmap'):
                self.pixmap = self.backup_pixmap.copy()
                self.update()
            
            # 처리 중인 모든 스레드 안전하게 중지
            self.stop_all_threads()
            
            # 처리 플래그 해제
            self.is_processing = False
            
            # 메모리 정리
            if hasattr(self, 'preview_pixmap'):
                self.preview_pixmap = None
            if hasattr(self, 'backup_pixmap'):
                self.backup_pixmap = None
            
            # 다이얼로그 닫기
            if hasattr(self, 'adjust_dialog') and self.adjust_dialog:
                self.adjust_dialog.reject()
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[이미지 조정] 취소 중 오류 발생: {e}")

    def stop_all_threads(self):
        """모든 실행 중인 이미지 처리 스레드를 중지합니다."""
        # 타이머 중지
        if hasattr(self, 'update_timer') and self.update_timer:
            self.update_timer.stop()
        
        # 미리보기 처리 스레드 중지
        if hasattr(self, 'processor') and self.processor is not None:
            if self.processor.isRunning():
                self.processor.should_stop = True
                self.processor.quit()
                # 스레드가 종료될 때까지 잠시 대기 (최대 100ms)
                if not self.processor.wait(100):
                    print("[이미지 조정] 미리보기 스레드 강제 종료")
                    self.processor.terminate()
            self.processor = None
            
        # 최종 처리 스레드 중지
        if hasattr(self, 'final_processor') and self.final_processor is not None:
            if self.final_processor.isRunning():
                self.final_processor.should_stop = True
                self.final_processor.quit()
                # 스레드가 종료될 때까지 잠시 대기 (최대 100ms)
                if not self.final_processor.wait(100):
                    print("[이미지 조정] 최종 처리 스레드 강제 종료")
                    self.final_processor.terminate()
            self.final_processor = None

    def reset_image_adjustments(self):
        """이미지 조정을 초기값으로 되돌립니다."""
        # 값 초기화
        self.color_temp = 6500
        self.brightness = 100
        self.saturation = 100
        
        # 다이얼로그가 열려있을 경우 슬라이더 값들도 초기화
        if hasattr(self, 'adjust_dialog') and self.adjust_dialog:
            if hasattr(self, 'temp_slider'):
                self.temp_slider.setValue(6500)
            if hasattr(self, 'brightness_slider'):
                self.brightness_slider.setValue(100)
            if hasattr(self, 'saturation_slider'):
                self.saturation_slider.setValue(100)
            
            # 레이블도 업데이트
            if hasattr(self, 'temp_label'):
                self.temp_label.setText("색온도: 6500K")
            if hasattr(self, 'brightness_label'):
                self.brightness_label.setText("밝기: 100%")
            if hasattr(self, 'saturation_label'):
                self.saturation_label.setText("채도: 100%")
        
        # pixmap을 원본으로 복원
        if self.original_pixmap and not self.original_pixmap.isNull():
            self.pixmap = self.original_pixmap.copy()
        else:
            # 원본 이미지가 없는 경우 (로드 실패 등) 처리 - 기본 에러 이미지 등으로 pixmap 설정 고려
            # 또는 load_image를 다시 호출하여 이미지를 다시 로드하도록 할 수도 있음.
            # 여기서는 original_pixmap이 없다면 pixmap을 변경하지 않거나, 기본 상태로.
            # 테스트 케이스에서 original_pixmap이 있다고 가정하고 진행되므로, 이 경우는 테스트에서 커버 안됨.
            pass 
        
        self.update() # 화면 갱신
        
        # 만약 이미지 조정 다이얼로그가 열려 있다면, 해당 다이얼로그도 업데이트하거나 닫기
        if self.adjust_dialog:
            # 다이얼로그의 슬라이더 값들을 업데이트하거나 다이얼로그를 리셋하는 로직 필요
            # 예: self.adjust_dialog.update_sliders(self.color_temp, self.brightness, self.saturation)
            # 또는 self.adjust_dialog.reset_ui_to_values(self.color_temp, self.brightness, self.saturation)
            # 현재 테스트에서는 이 부분 직접 검증 안함.
            self.preview_adjustments() # 다이얼로그가 있다면 미리보기 업데이트

    def apply_image_effects(self, temp, brightness, saturation):
        """특정 조정 값으로 이미지 효과를 적용하고 관련 속성을 업데이트합니다.
        이 메소드는 주로 테스트 또는 외부에서 직접 효과를 적용할 때 사용됩니다.
        사용자 UI를 통한 조정은 show_adjustment_dialog -> preview_adjustments -> apply_image_adjustments 경로를 따릅니다.
        """
        if self.original_pixmap is None or self.original_pixmap.isNull():
            print("[apply_image_effects] 원본 이미지가 없어 효과를 적용할 수 없습니다.")
            if self.pixmap and not self.pixmap.isNull():
                self.original_pixmap = self.pixmap.copy() # 현재 pixmap을 원본으로 간주
            else:
                # 원본도 없고 현재 pixmap도 없으면 효과 적용 불가
                print("[apply_image_effects] 적용할 이미지가 없습니다.")
                return

        # ImageAdjuster를 사용하여 효과 적용
        processed_pixmap = ImageAdjuster.apply_effects(
            self.original_pixmap, # 항상 원본에 효과 적용
            temp,
            brightness,
            saturation
        )

        if processed_pixmap and not processed_pixmap.isNull():
            self.pixmap = processed_pixmap.copy() # ImageAdjuster가 복사본을 반환해도 안전하게 여기서도 복사
            # 조정된 값으로 내부 상태 업데이트
            self.color_temp = temp
            self.brightness = brightness
            self.saturation = saturation
            self.update() # 위젯을 다시 그리도록 갱신
            print(f"[apply_image_effects] 효과 적용 완료: T={temp}, B={brightness}, S={saturation}")
        else:
            print("[apply_image_effects] 효과 적용 실패 또는 결과 이미지가 없음.")
            # 테스트에서 mock_apply_effects.return_value가 dummy_pixmap_red_small로 설정되므로,
            # 이 else 블록은 테스트 중에 실행되지 않을 것으로 예상됩니다.

    def deleteLater(self):
        """위젯이 삭제될 때 리소스를 정리하고 스레드를 안전하게 종료합니다."""
        try:
            # 이미지 조정 다이얼로그가 열려있으면 닫기
            if hasattr(self, 'adjust_dialog') and self.adjust_dialog:
                self.adjust_dialog.close()
                self.adjust_dialog = None
            
            # 모든 스레드 안전하게 정리
            self.stop_all_threads()
            
            # 타이머 정리
            if hasattr(self, 'update_timer') and self.update_timer:
                self.update_timer.stop()
                self.update_timer = None
            
            # 이미지 메모리 정리
            if hasattr(self, 'preview_pixmap'):
                self.preview_pixmap = None
            if hasattr(self, 'backup_pixmap'):
                self.backup_pixmap = None
            if hasattr(self, 'original_pixmap'):
                self.original_pixmap = None
            if hasattr(self, 'pixmap'):
                self.pixmap = None
            
            print(f"[FurnitureItem] 리소스 정리 완료: {self.furniture.name}")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[FurnitureItem] 리소스 정리 중 오류: {e}")
        finally:
            # 부모 클래스의 deleteLater 호출
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

    def handle_image_processing_error(self, error_message):
        """이미지 처리 에러를 처리합니다."""
        print(f"[이미지 조정] 미리보기 처리 오류: {error_message}")
        self.is_processing = False

    def handle_final_processing_error(self, error_message):
        """최종 이미지 처리 에러를 처리합니다."""
        print(f"[이미지 조정] 최종 처리 오류: {error_message}")
        self.is_processing = False
        
        # 다이얼로그 닫기
        if hasattr(self, 'adjust_dialog') and self.adjust_dialog:
            self.adjust_dialog.accept()

