import base64
import datetime
import json
import os

from PyQt6.QtCore import (QPoint, QRect, Qt, QTimer, QByteArray, QBuffer, QIODevice, QSize)
from PyQt6.QtGui import (QPainter, QPixmap, QTransform, QGuiApplication, QPen, QBrush, QColor)
from PyQt6.QtWidgets import (QFileDialog,
                             QMenu,
                             QMessageBox, QVBoxLayout,
                             QWidget, QRubberBand)

from src.models.furniture import Furniture
from src.services.supabase_client import SupabaseClient
from src.ui.dialogs import CanvasSizeDialog
from src.ui.utils import ImageAdjuster
from src.ui.widgets import FurnitureItem, CanvasArea


class Canvas(QWidget):
    CANVAS_MIN_HEIGHT = 200
    CANVAS_MIN_WIDTH = 300

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        # Canvas 자체의 최소 크기는 내부 canvas_area에 의해 결정되도록 할 수 있음
        # 또는 아주 작은 값으로 설정하여 canvas_area가 크기를 주도하도록 함
        self.setMinimumSize(100, 100) # Canvas의 최소 크기
        self.setStyleSheet(""" 
            Canvas { 
                background-color: #f0f2f5; /* 연한 회색 배경 */ 
                border: none;
                 margin: 15px;
                padding: 15px;
            }
        """)
        
        # 이미지 조정 시스템 초기화
        if not ImageAdjuster._initialized:
            ImageAdjuster.initialize()
        
        # Canvas의 메인 레이아웃 (마진 완전 제거)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)  # 위젯 간 간격도 제거
        
        # 캔버스 영역 (실제 가구가 배치되는 곳)
        self.canvas_area = CanvasArea(self)
        self.canvas_area.setMinimumSize(self.CANVAS_MIN_WIDTH, self.CANVAS_MIN_HEIGHT)
        self.canvas_area.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 3px solid #2C3E50;
                border-radius: 5px;
                margin: 0px;
                padding: 0px;
            }
        """)
        
        # 레이아웃에 canvas_area 추가 (마진 없이)
        layout.addWidget(self.canvas_area)
        
        # 초기 상태 설정
        self.is_new_collage = True
        self.furniture_items = []
        self.selected_items = []  # 다중 선택을 위해 리스트로 변경
        
        # 영역 선택 관련 속성
        self.rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self.canvas_area)
        self.rubber_band.hide()
        self.selection_start_point = QPoint()
        self.is_selecting = False
        
        # 배경 이미지 관련 속성 추가
        self.background_image = None
        self.has_background = False
        
        # 우클릭 메뉴 활성화 (canvas_area에 대해)
        self.canvas_area.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.canvas_area.customContextMenuRequested.connect(self.show_context_menu)
        
        # 캔버스 영역 마우스 이벤트 설정 (영역 선택 지원)
        self.canvas_area.mousePressEvent = self.canvas_mouse_press_event
        self.canvas_area.mouseMoveEvent = self.canvas_mouse_move_event
        self.canvas_area.mouseReleaseEvent = self.canvas_mouse_release_event
        
        # 키보드 포커스 설정 (키 이벤트 수신을 위해)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Undo/Redo 스택 초기화
        self.undo_stack = []
        self.redo_stack = []
        self._save_state_and_update_actions() # 초기 빈 캔버스 상태 저장
    
    def _get_current_state(self):
        """캔버스의 현재 상태를 딕셔너리 형태로 반환합니다."""
        state = {
            "canvas_size": (self.canvas_area.width(), self.canvas_area.height()),
            "furniture_items": [],
            "background_image_data": None, # 배경 이미지 데이터 추가
            "has_background": self.has_background
        }
        
        if self.has_background and self.background_image and not self.background_image.isNull():
            byte_array = QByteArray()
            buffer = QBuffer(byte_array)
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            success = self.background_image.save(buffer, "PNG")
            buffer.close()
            if success:
                state["background_image_data"] = base64.b64encode(byte_array.data()).decode('utf-8')

        for i, item_widget in enumerate(self.furniture_items):
            item_state = {
                "id": item_widget.furniture.id,
                "position": (item_widget.pos().x(), item_widget.pos().y()),
                "size": (item_widget.width(), item_widget.height()),
                "z_order": i,
                "is_flipped": getattr(item_widget, 'is_flipped', False),
                "color_temp": getattr(item_widget, 'color_temp', 6500),
                "brightness": getattr(item_widget, 'brightness', 100),
                "saturation": getattr(item_widget, 'saturation', 100)
            }
            state["furniture_items"].append(item_state)
        return state

    def _save_state(self):
        """현재 캔버스 상태를 Undo 스택에 저장합니다."""
        current_state = self._get_current_state()
        
        # 가장 최근 undo 상태가 현재 상태와 동일하면 저장하지 않음 (중복 방지)
        # 이 비교는 깊은 비교가 필요할 수 있으며, 간단히 참조 비교나 얕은 비교로는 부족할 수 있음.
        # 여기서는 일단 Python의 기본 dict 비교를 사용. 더 정확한 비교 로직이 필요할 수 있음.
        if self.undo_stack and self.undo_stack[-1] == current_state:
            # print("[Undo/Redo] 현재 상태가 이미 Undo 스택의 최상단과 동일하여 저장 건너뜀.")
            return

        if len(self.undo_stack) >= 50: # 최대 50개 상태 저장
            self.undo_stack.pop(0) # 가장 오래된 상태 제거
        
        self.undo_stack.append(current_state)
        self.redo_stack.clear() # 새 액션 발생 시 Redo 스택 비움
        print(f"[Undo/Redo] 상태 저장됨. Undo 스택 크기: {len(self.undo_stack)}, 최상단 아이템 수: {len(current_state['furniture_items'])}")
    
    def canvas_mouse_press_event(self, event):
        """캔버스 영역에서 마우스 버튼을 눌렀을 때의 처리"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 클릭된 위치에 가구 아이템이 있는지 확인
            clicked_item = self.get_furniture_item_at_position(event.pos())
            
            if clicked_item:
                # 가구 아이템을 클릭한 경우
                self.select_furniture_item(clicked_item)
                self.is_selecting = False
            else:
                # 빈 공간을 클릭한 경우 - 영역 선택 시작
                modifiers = QGuiApplication.keyboardModifiers()
                
                # Ctrl 키를 누르지 않은 경우에만 기존 선택 해제
                if not (modifiers & Qt.KeyboardModifier.ControlModifier):
                    self.deselect_all_items()
                
                # 영역 선택 시작
                self.selection_start_point = event.pos()
                self.is_selecting = True
                rect = QRect(self.selection_start_point, QSize(1, 1))
                self.rubber_band.setGeometry(rect)
                self.rubber_band.show()
            
            # 키보드 포커스 설정
            self.setFocus()
    
    def canvas_mouse_move_event(self, event):
        """캔버스 영역에서 마우스를 움직일 때의 처리"""
        if self.is_selecting and event.buttons() & Qt.MouseButton.LeftButton:
            # 영역 선택 중 - 러버밴드 업데이트
            current_pos = event.pos()
            self.rubber_band.setGeometry(QRect(self.selection_start_point, current_pos).normalized())
    
    def canvas_mouse_release_event(self, event):
        """캔버스 영역에서 마우스 버튼을 놓았을 때의 처리"""
        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            # 영역 선택 완료
            self.is_selecting = False
            self.rubber_band.hide()
            
            # 선택 영역 계산
            selection_rect = QRect(self.selection_start_point, event.pos()).normalized()
            
            # 최소 크기 확인 (우연한 클릭 방지)
            if selection_rect.width() > 5 and selection_rect.height() > 5:
                self.select_items_in_rectangle(selection_rect)
    
    def get_furniture_item_at_position(self, pos):
        """지정된 위치에 있는 가구 아이템을 반환합니다."""
        for item in reversed(self.furniture_items):  # 위에 있는 아이템부터 확인
            if item.geometry().contains(pos):
                return item
        return None
    
    def select_items_in_rectangle(self, rect):
        """지정된 사각형 영역 내의 가구 아이템들을 선택합니다."""
        modifiers = QGuiApplication.keyboardModifiers()
        selected_items_in_rect = []
        
        # 영역 내의 아이템들 찾기
        for item in self.furniture_items:
            item_rect = item.geometry()
            # 아이템이 선택 영역과 겹치는지 확인
            if rect.intersects(item_rect):
                selected_items_in_rect.append(item)
        
        if selected_items_in_rect:
            if modifiers & Qt.KeyboardModifier.ControlModifier:
                # Ctrl 키를 누른 상태: 기존 선택에 추가/제거
                for item in selected_items_in_rect:
                    if item in self.selected_items:
                        # 이미 선택된 아이템이면 해제
                        self.selected_items.remove(item)
                        item.is_selected = False
                    else:
                        # 선택되지 않은 아이템이면 추가
                        self.selected_items.append(item)
                        item.is_selected = True
                    item.update()
            else:
                # Ctrl 키를 누르지 않은 상태: 새로운 선택
                # 기존 선택 해제 (이미 deselect_all_items가 호출되었지만 안전장치)
                for item in self.selected_items:
                    if item not in selected_items_in_rect:
                        item.is_selected = False
                        item.update()
                
                # 새로 선택된 아이템들 설정
                self.selected_items = selected_items_in_rect[:]
                for item in self.selected_items:
                    item.is_selected = True
                    item.update()
            
            self.update_bottom_panel()
            # 번호표 즉시 업데이트
            self.canvas_area.update()
    
    # 가구 아이템 선택 처리 (다중 선택 지원)
    def select_furniture_item(self, item):
        modifiers = QGuiApplication.keyboardModifiers()
        
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            # Ctrl/Cmd 키를 누른 상태: 토글 선택
            if item in self.selected_items:
                # 이미 선택된 아이템이면 선택 해제
                self.selected_items.remove(item)
                item.is_selected = False
            else:
                # 선택되지 않은 아이템이면 추가 선택
                self.selected_items.append(item)
                item.is_selected = True
        else:
            # Ctrl/Cmd 키를 누르지 않은 상태
            if len(self.selected_items) > 1 and item in self.selected_items:
                # 다중 선택된 상태에서 이미 선택된 아이템을 클릭한 경우
                # 다중 선택을 유지하고 아무것도 하지 않음
                pass
            else:
                # 단일 선택 또는 선택되지 않은 아이템 클릭: 기존 로직
                # 기존 선택된 아이템들 모두 해제
                for selected_item in self.selected_items:
                    selected_item.is_selected = False
                    selected_item.update()
                
                # 새 아이템만 선택
                self.selected_items = [item] if item else []
                if item:
                    item.is_selected = True
        
        # 선택된 아이템들 화면 업데이트
        if item:
            item.update()
        
        self.update_bottom_panel()
        # 번호표 즉시 업데이트
        self.canvas_area.update()
    
    # 모든 가구 아이템 선택 해제
    def deselect_all_items(self):
        for item in self.selected_items:
            item.is_selected = False
            item.update()
        self.selected_items.clear()
        self.update_bottom_panel()
        # 번호표 즉시 업데이트
        self.canvas_area.update()
    
    # 하위 호환성을 위한 프로퍼티
    @property
    def selected_item(self):
        """하위 호환성을 위한 프로퍼티: 첫 번째 선택된 아이템 반환"""
        return self.selected_items[0] if self.selected_items else None
    
    @selected_item.setter
    def selected_item(self, value):
        """하위 호환성을 위한 setter: 단일 아이템 선택"""
        if value is None:
            self.deselect_all_items()
        else:
            # 기존 선택 해제
            for item in self.selected_items:
                item.is_selected = False
                item.update()
            # 새 아이템 선택
            self.selected_items = [value]
            value.is_selected = True
            value.update()
            self.update_bottom_panel()
    
    def show_context_menu(self, position):
        """캔버스 영역에서 우클릭했을 때 컨텍스트 메뉴를 표시합니다."""
        menu = QMenu(self)
        
        # 메뉴 아이템 추가
        save_action = menu.addAction("저장하기")
        load_action = menu.addAction("불러오기")
        menu.addSeparator()
        new_action = menu.addAction("새 콜라주")
        resize_action = menu.addAction("캔버스 크기 조절")
        export_action = menu.addAction("내보내기")
        
        # 메뉴 아이템 동작 연결
        save_action.triggered.connect(self.save_collage)
        load_action.triggered.connect(self.load_collage)
        new_action.triggered.connect(self.create_new_collage)
        resize_action.triggered.connect(self.resize_canvas)
        export_action.triggered.connect(self.export_collage)
        
        # 메뉴 표시
        menu.exec(self.canvas_area.mapToGlobal(position))
    
    def save_collage(self):
        """현재 콜라주를 JSON 파일로 저장합니다."""
        if not self.furniture_items and self.is_new_collage:
            self._show_warning_message("경고", "저장할 콜라주가 없습니다.")
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
                        "last_modified": datetime.datetime.now().isoformat(),
                        # 배경 이미지 정보 추가
                        "has_background": self.has_background,
                        "background_image_data": None
                    },
                    "furniture_items": []
                }
                
                # 배경 이미지가 있으면 데이터로 변환하여 저장
                if self.has_background and self.background_image and not self.background_image.isNull():
                    # QPixmap을 바이트 배열로 변환
                    byte_array = QByteArray()
                    buffer = QBuffer(byte_array)
                    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                    
                    # PNG 형식으로 저장
                    success = self.background_image.save(buffer, "PNG")
                    buffer.close()
                    
                    if success:
                        # 바이트 데이터를 base64로 인코딩하여 JSON에 저장
                        collage_data["canvas"]["background_image_data"] = base64.b64encode(byte_array.data()).decode('utf-8')
                        print("[Canvas] 배경 이미지 데이터 저장 완료")
                
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
                
                self._show_information_message("성공", "콜라주가 성공적으로 저장되었습니다.")
                
            except Exception as e:
                self._show_critical_message("오류", f"콜라주 저장 중 오류가 발생했습니다: {str(e)}")
    
    def load_collage(self):
        """저장된 콜라주를 JSON 파일에서 불러옵니다."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "콜라주 불러오기",
            os.path.expanduser("~/Desktop"),
            "JSON 파일 (*.json);;모든 파일 (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    collage_data = json.load(f)
                
                for item in self.furniture_items:
                    item.deleteLater()
                self.furniture_items.clear()
                self.selected_items.clear()
                
                canvas_width = collage_data["canvas"]["width"]
                canvas_height = collage_data["canvas"]["height"]
                # 저장된 콜라주도 동적으로 크기 조절 가능하도록 resize 사용
                self.canvas_area.resize(canvas_width, canvas_height)
                self.adjust_window_size_to_canvas(canvas_width, canvas_height) # 윈도우 크기 조정 메서드 호출

                # 배경 이미지 복원
                canvas_info = collage_data["canvas"]
                if canvas_info.get("has_background", False) and canvas_info.get("background_image_data"):
                    try:
                        # base64 디코딩
                        image_data = base64.b64decode(canvas_info["background_image_data"])
                        
                        # QPixmap으로 변환
                        background_pixmap = QPixmap()
                        success = background_pixmap.loadFromData(image_data)
                        
                        if success and not background_pixmap.isNull():
                            self.background_image = background_pixmap
                            self.has_background = True
                            print("[Canvas] 배경 이미지 복원 완료")
                        else:
                            print("[Canvas] 배경 이미지 데이터 복원 실패")
                    except Exception as e:
                        print(f"[Canvas] 배경 이미지 복원 중 오류: {e}")
                        self.background_image = None
                        self.has_background = False
                
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
                        # QMessageBox.warning(self, "경고", f"콜라주에 포함된 가구(ID: {furniture_id})를 현재 데이터베이스에서 찾을 수 없습니다. 해당 아이템은 제외됩니다.")
                        self._show_warning_message("경고", f"콜라주에 포함된 가구(ID: {furniture_id})를 현재 데이터베이스에서 찾을 수 없습니다. 해당 아이템은 제외됩니다.")
                        # 누락된 아이템 정보 기록 또는 처리
                        continue # 다음 아이템으로 넘어감
                
                # 하단 패널 업데이트
                self.update_bottom_panel()
                
                self._show_information_message("성공", "콜라주가 성공적으로 불러와졌습니다.")
                
            except Exception as e:
                import traceback
                traceback.print_exc()  # 자세한 오류 정보 출력
                self._show_critical_message("오류", f"콜라주 불러오기 중 오류가 발생했습니다: {str(e)}")
            except FileNotFoundError as e:
                self._show_critical_message("오류", f"콜라주 파일을 열 수 없습니다: {str(e)}")
            except Exception as e: # 가장 마지막에 위치해야 하는 일반 예외 처리
                import traceback
                traceback.print_exc()  # 자세한 오류 정보 출력
                self._show_critical_message("오류", f"콜라주 불러오기 중 예기치 않은 오류가 발생했습니다: {str(e)}")
    
    def create_new_collage(self):
        """새 콜라주를 생성합니다. 앱을 완전히 초기화합니다."""
        dialog = CanvasSizeDialog(self)
        if dialog.exec():
            width, height = dialog.get_size()
            
            # 1. 기존 가구 아이템 완전 제거
            for item in self.furniture_items:
                # 이미지 조정 다이얼로그가 열려있으면 닫기
                if hasattr(item, 'adjust_dialog') and item.adjust_dialog:
                    item.adjust_dialog.close()
                    item.adjust_dialog = None
                
                # 스레드들 안전하게 정리
                if hasattr(item, 'stop_all_threads'):
                    item.stop_all_threads()
                
                item.setParent(None)  # 부모 관계 해제
                item.deleteLater()
            self.furniture_items.clear()
            self.selected_items.clear()
            
            # 2. 캔버스 영역 완전 재생성
            old_canvas_area = self.canvas_area
            old_canvas_area.setParent(None)
            old_canvas_area.deleteLater()
            
            # 새 캔버스 영역 생성
            self.canvas_area = CanvasArea(self)
            # 최소 크기는 기본값만 설정 (리사이즈 가능하도록)
            print(f"[새 콜라주] 요청된 크기: {width}x{height}")
            print(f"[새 콜라주] 기본 최소 크기 설정: {self.CANVAS_MIN_WIDTH}x{self.CANVAS_MIN_HEIGHT}")
            
            self.canvas_area.setMinimumSize(self.CANVAS_MIN_WIDTH, self.CANVAS_MIN_HEIGHT)
            self.canvas_area.resize(width, height)
            
            print(f"[새 콜라주] 최종 캔버스 크기: {self.canvas_area.width()}x{self.canvas_area.height()}")
            print(f"[새 콜라주] 최종 최소 크기: {self.canvas_area.minimumWidth()}x{self.canvas_area.minimumHeight()}")
            
            self.canvas_area.setStyleSheet("""
                QWidget {
                    background-color: white;
                     border: 3px solid #2C3E50;
                    border-radius: 5px;
                    margin: 0px;
                    padding: 0px;
                }
            """)
            
            # 3. 레이아웃에 새 캔버스 영역 추가
            layout = self.layout()
            layout.addWidget(self.canvas_area)
            
            # 4. 이벤트 핸들러 재설정
            self.canvas_area.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.canvas_area.customContextMenuRequested.connect(self.show_context_menu)
            self.canvas_area.mousePressEvent = self.canvas_mouse_press_event
            self.canvas_area.mouseMoveEvent = self.canvas_mouse_move_event
            self.canvas_area.mouseReleaseEvent = self.canvas_mouse_release_event
            
            # 5. 상태 초기화 - is_new_collage는 크기 조절에 영향을 주지 않도록 함
            # self.is_new_collage = False  # 이 부분을 True로 변경하거나, resizeEvent에서 처리하도록 함
            self.is_new_collage = True # 새 콜라주는 일단 True로 유지 (다른 의미로 사용될 수 있음)

            # 6. UI 강제 업데이트
            self.canvas_area.show()
            self.update()
            
            # 7. 하단 패널 업데이트
            self.update_bottom_panel()
            
            # 8. 메인 윈도우에 초기화 알림
            main_window = self.window()
            if hasattr(main_window, 'initialize_canvas_coordinates'):
                main_window.initialize_canvas_coordinates()
            
            # 9. 캔버스 크기 변경 알림
            if hasattr(main_window, 'canvas_size_changed'):
                main_window.canvas_size_changed()
            
            # 10. 윈도우 크기를 캔버스 크기에 맞춰 조정
            self.adjust_window_size_to_canvas(width, height)
            
            # 11. 윈도우 크기 조정 후 캔버스 크기 재확인 및 보정
            QTimer.singleShot(100, lambda: self.verify_and_fix_canvas_size(width, height))
            
            print(f"[새 콜라주] 캔버스 완전 초기화 완료: {width}x{height}")
            print(f"[새 콜라주] 동적 리사이즈 비활성화됨 - is_new_collage: {self.is_new_collage}")
            self._save_state_and_update_actions() # 상태 저장
    
    def verify_and_fix_canvas_size(self, expected_width, expected_height):
        """윈도우 크기 조정 후 캔버스 크기가 의도한 크기와 일치하는지 확인하고 보정합니다."""
        current_width = self.canvas_area.width()
        current_height = self.canvas_area.height()
        
        print(f"[캔버스 크기 확인] 예상: {expected_width}x{expected_height}, 실제: {current_width}x{current_height}")
        
        # 크기가 다르면 강제로 다시 설정
        if current_width != expected_width or current_height != expected_height:
            print(f"[캔버스 크기 보정] {expected_width}x{expected_height}로 재설정")
            self.canvas_area.resize(expected_width, expected_height)
            
            # 한 번 더 확인
            QTimer.singleShot(50, lambda: print(f"[캔버스 크기 최종 확인] Area: {self.canvas_area.width()}x{self.canvas_area.height()}"))
        else:
            print(f"[캔버스 크기 확인] 올바른 크기 유지됨")
    
    def adjust_window_size_to_canvas(self, canvas_width, canvas_height):
        """캔버스 크기에 맞춰 윈도우 크기를 조정합니다."""
        main_window = self.window()
        if not main_window:
            return
        
        # MainWindow 객체인지 확인 (테스트 호환성)
        if not hasattr(main_window, 'splitter_horizontal') or not hasattr(main_window, 'splitter_main_vertical'):
            print(f"[윈도우 크기 조정] MainWindow가 아닌 환경에서 실행됨 - 크기 조정 건너뜀")
            return
        
        # 현재 스플리터 크기 확인 (실제 패널 크기 사용)
        splitter_sizes = main_window.splitter_horizontal.sizes()
        right_panel_width = splitter_sizes[1] if len(splitter_sizes) > 1 else 400
        
        vertical_splitter_sizes = main_window.splitter_main_vertical.sizes()
        bottom_panel_height = vertical_splitter_sizes[1] if len(vertical_splitter_sizes) > 1 else 200
        
        # 여백 및 기타 UI 요소 크기
        window_margin = 50  # 윈도우 여백
        menubar_height = 30  # 메뉴바 높이
        
        # 필요한 윈도우 크기 계산
        required_width = canvas_width + right_panel_width + window_margin
        required_height = canvas_height + bottom_panel_height + menubar_height + window_margin
        
        # 현재 화면 크기 확인 (화면보다 큰 크기로 설정하지 않도록)
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        
        # 화면 크기의 90%를 최대 크기로 제한
        max_width = int(screen_geometry.width() * 0.9)
        max_height = int(screen_geometry.height() * 0.9)
        
        # 최종 윈도우 크기 결정
        final_width = min(required_width, max_width)
        final_height = min(required_height, max_height)
        
        # 최소 윈도우 크기 보장
        final_width = max(final_width, 800)
        final_height = max(final_height, 600)
        
        print(f"[윈도우 크기 조정] 캔버스: {canvas_width}x{canvas_height}")
        print(f"[윈도우 크기 조정] 현재 스플리터 크기 - 우측 패널: {right_panel_width}, 하단 패널: {bottom_panel_height}")
        print(f"[윈도우 크기 조정] 계산된 윈도우 크기: {required_width}x{required_height}")
        print(f"[윈도우 크기 조정] 최종 윈도우 크기: {final_width}x{final_height}")
        
        # 윈도우 크기 조정
        main_window.resize(final_width, final_height)
        
        # 윈도우를 화면 중앙에 배치
        window_x = (screen_geometry.width() - final_width) // 2
        window_y = (screen_geometry.height() - final_height) // 2
        main_window.move(window_x, window_y)
        
        # 윈도우 크기 조정 후 스플리터 크기 재조정으로 캔버스 영역 보장
        QTimer.singleShot(50, lambda: self.adjust_splitter_for_canvas_size(canvas_width, canvas_height))
    
    def adjust_splitter_for_canvas_size(self, target_width, target_height):
        """스플리터 크기를 조정하여 캔버스가 목표 크기를 가질 수 있도록 합니다."""
        main_window = self.window()
        if not main_window:
            return
        
        # MainWindow 객체인지 확인 (테스트 호환성)
        if not hasattr(main_window, 'splitter_horizontal') or not hasattr(main_window, 'splitter_main_vertical'):
            print(f"[스플리터 조정] MainWindow가 아닌 환경에서 실행됨 - 조정 건너뜀")
            return
        
        # 현재 윈도우 전체 크기
        window_width = main_window.width()
        window_height = main_window.height()
        
        # 우측 패널은 현재 크기 유지하되, 캔버스가 목표 크기를 가질 수 있도록 조정
        current_horizontal_sizes = main_window.splitter_horizontal.sizes()
        current_vertical_sizes = main_window.splitter_main_vertical.sizes()
        
        # 수평 스플리터 조정 (캔버스 + 우측 패널)
        right_panel_width = current_horizontal_sizes[1] if len(current_horizontal_sizes) > 1 else 400
        available_width = window_width - 20  # 약간의 여백
        canvas_width_target = max(target_width, available_width - right_panel_width)
        
        new_horizontal_sizes = [canvas_width_target, right_panel_width]
        main_window.splitter_horizontal.setSizes(new_horizontal_sizes)
        
        # 수직 스플리터 조정 (상단 영역 + 하단 패널)
        bottom_panel_height = current_vertical_sizes[1] if len(current_vertical_sizes) > 1 else 200
        available_height = window_height - 50  # 메뉴바 등 여백
        top_area_height = max(target_height + 20, available_height - bottom_panel_height)  # 캔버스 + 약간의 여백
        
        new_vertical_sizes = [top_area_height, bottom_panel_height]
        main_window.splitter_main_vertical.setSizes(new_vertical_sizes)
        
        print(f"[스플리터 조정] 수평: {new_horizontal_sizes}, 수직: {new_vertical_sizes}")
        
        # 스플리터 조정 후 캔버스 크기 재확인
        QTimer.singleShot(50, lambda: self.verify_and_fix_canvas_size(target_width, target_height))

    def _show_warning_message(self, title: str, message: str):
        """경고 메시지 박스를 표시하는 내부 헬퍼 메소드."""
        QMessageBox.warning(self, title, message)

    def _show_critical_message(self, title: str, message: str):
        """오류 메시지 박스를 표시하는 내부 헬퍼 메소드."""
        QMessageBox.critical(self, title, message)

    def _show_information_message(self, title: str, message: str):
        """정보 메시지 박스를 표시하는 내부 헬퍼 메소드."""
        QMessageBox.information(self, title, message)
    
    def _generate_collage_image(self) -> QPixmap:
        """현재 콜라주를 QPixmap 이미지로 생성합니다."""
        # 캔버스 영역의 크기로 이미지 생성
        image = QPixmap(self.canvas_area.size())
        
        # 이미지에 현재 콜라주 그리기
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 배경 이미지가 있으면 먼저 그리기
        if self.has_background and self.background_image and not self.background_image.isNull():
            painter.drawPixmap(
                image.rect(),
                self.background_image,
                self.background_image.rect()
            )
        else:
            # 배경 이미지가 없으면 흰색 배경
            image.fill(Qt.GlobalColor.white)
        
        # 모든 가구 아이템 그리기
        for item in self.furniture_items:
            # 아이템의 위치와 크기
            pos = item.pos()
            widget_size = item.size() # The QWidget's current size on canvas

            if item.pixmap is None or item.pixmap.isNull(): # Safety check
                continue

            final_pixmap_to_draw = None
            draw_pos_x = pos.x()
            draw_pos_y = pos.y()

            if hasattr(item, 'maintain_aspect_ratio') and not item.maintain_aspect_ratio:
                # User has stretched/squashed the item, ignore original pixmap aspect ratio
                final_pixmap_to_draw = item.pixmap.scaled(
                    widget_size,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            else:
                # Default or user wants to maintain original pixmap aspect ratio
                final_pixmap_to_draw = item.pixmap.scaled(
                    widget_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                # Center the pixmap if KeepAspectRatio mode doesn't fill the widget_size
                draw_pos_x += (widget_size.width() - final_pixmap_to_draw.width()) // 2
                draw_pos_y += (widget_size.height() - final_pixmap_to_draw.height()) // 2
            
            painter.drawPixmap(draw_pos_x, draw_pos_y, final_pixmap_to_draw)
        
        # 번호표 그리기 (CanvasArea의 메서드 활용)
        self._draw_number_labels_on_image(painter)
        
        painter.end()
        return image
    
    def _draw_number_labels_on_image(self, painter):
        """이미지 내보내기용 번호표를 그립니다. (CanvasArea의 로직과 동일)"""
        # 번호표 설정
        label_size = 18  # 원형 라벨 크기
        offset = 1       # 가구 영역에서 벗어날 거리
        
        for furniture_item in self.furniture_items:
            # 번호 확인
            if not hasattr(furniture_item, 'number_label_value') or furniture_item.number_label_value <= 0:
                continue
            
            if not hasattr(furniture_item, 'show_number_label') or not furniture_item.show_number_label:
                continue
            
            # 가구 아이템의 위치와 크기
            item_rect = furniture_item.geometry()
            
            # 번호표 위치 (가구 영역 밖 좌측 상단)
            label_x = item_rect.left() - label_size - offset
            label_y = item_rect.top() - label_size - offset
            
            # 캔버스 영역을 벗어나지 않도록 조정
            if label_x < 0:
                label_x = item_rect.left() + offset  # 가구 안쪽으로
            if label_y < 0:
                label_y = item_rect.top() + offset  # 가구 안쪽으로
            
            label_rect = QRect(label_x, label_y, label_size, label_size)
            
            # 원형 배경 그리기
            painter.setPen(QPen(QColor("#ffffff"), 2))  # 흰색 테두리
            painter.setBrush(QBrush(QColor("#444444")))  # 다크 그레이 배경
            painter.drawEllipse(label_rect)
            
            # 숫자 텍스트 그리기
            painter.setPen(QPen(QColor("#ffffff")))  # 흰색 텍스트
            font = painter.font()
            font.setBold(True)
            font.setPointSize(8)  # 폰트 크기
            painter.setFont(font)
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, str(furniture_item.number_label_value))

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
                drop_pos = self.canvas_area.mapFrom(self, event.position().toPoint())
                furniture_data = eval(event.mimeData().data("application/x-furniture").data().decode())
                furniture = Furniture(**furniture_data)
                item = FurnitureItem(furniture, self.canvas_area)
                # FurnitureItem의 item_changed 시그널을 Canvas의 상태 저장 메서드에 연결
                item.item_changed.connect(self._save_state_and_update_actions)
                
                item.move(drop_pos - QPoint(item.width() // 2, item.height() // 2))
                item.show()
                self.furniture_items.append(item)
                self.select_furniture_item(item)
                # select_furniture_item에서 이미 update_bottom_panel을 호출하므로 여기서는 제거
                self._save_state_and_update_actions() # 여기서 한 번 저장 (아이템 추가 작업 자체)
                event.acceptProposedAction()
        except Exception as e:
            print(f"드롭 이벤트 처리 중 오류 발생: {e}")
            event.ignore()
    
    def adjust_furniture_positions(self, delta_x, delta_y):
        """캔버스 이동에 따라 모든 가구 아이템의 위치를 조정합니다."""
        # print(f"Adjusting furniture positions by dx={delta_x}, dy={delta_y}") # 디버깅용
        for item in self.furniture_items:
            new_x = item.x() + delta_x
            new_y = item.y() + delta_y
            item.move(new_x, new_y)
            # print(f"Moved {item.furniture.name} to ({new_x}, {new_y})") # 디버깅용
            
    def update_bottom_panel(self):
        """하단 패널을 업데이트합니다."""
        # 부모 위젯에서 bottom_panel을 찾아서 업데이트
        parent_widget = self.parent()
        while parent_widget:
            if hasattr(parent_widget, 'bottom_panel'):
                parent_widget.bottom_panel.update_panel(self.furniture_items)
                # 번호표 업데이트
                self.update_number_labels()
                return
            parent_widget = parent_widget.parent()
        
        # 부모 위젯에서 찾지 못한 경우 window()에서 찾기
        main_window = self.window()
        if main_window and hasattr(main_window, 'bottom_panel'):
            main_window.bottom_panel.update_panel(self.furniture_items)
            # 번호표 업데이트
            self.update_number_labels()
            return
        
        print("[Canvas] 하단 패널을 찾을 수 없습니다.")
    
    def update_number_labels(self):
        """캔버스의 가구 아이템들에 번호표를 업데이트합니다."""
        # 하단 패널에서 가구 순서 정보 가져오기
        parent_widget = self.parent()
        while parent_widget:
            if hasattr(parent_widget, 'bottom_panel'):
                bottom_panel = parent_widget.bottom_panel
                if hasattr(bottom_panel, 'selected_panel'):
                    selected_panel = bottom_panel.selected_panel
                    if hasattr(selected_panel, 'selected_model'):
                        model = selected_panel.selected_model
                        
                        # 캔버스의 각 가구 아이템에 번호 설정
                        for furniture_item in self.furniture_items:
                            furniture_name = furniture_item.furniture.name
                            
                            # 하단 패널에서 해당 가구의 순서 번호 찾기
                            number = 0
                            for i, order_name in enumerate(model.furniture_order):
                                if order_name == furniture_name:
                                    number = i + 1
                                    break
                            
                            # 가구 아이템에 번호 설정
                            furniture_item.set_number_label(number)
                        
                        # CanvasArea 다시 그리기 (번호표 표시를 위해)
                        self.canvas_area.update()
                        
                        print(f"[Canvas] 번호표 업데이트 완료: {len(self.furniture_items)}개 아이템")
                        return
                break
            parent_widget = parent_widget.parent()
        
        # 하단 패널을 찾을 수 없는 경우 기본 순서대로 번호 설정
        for i, furniture_item in enumerate(self.furniture_items):
            furniture_item.set_number_label(i + 1)
        
        # CanvasArea 다시 그리기
        self.canvas_area.update()

    def resizeEvent(self, event):
        """Canvas 크기 변경 시 호출됩니다."""
        super().resizeEvent(event)
        
        # 새 콜라주 상태일 때만 윈도우 크기에 맞춰 동적 조정 -> is_new_collage 조건 제거
        # 불러온 콜라주나 복원된 콜라주는 동적 조정하지 않음
        # if self.is_new_collage and hasattr(self, 'canvas_area') and self.canvas_area:
        if hasattr(self, 'canvas_area') and self.canvas_area: # is_new_collage 조건 제거
            # 캔버스 영역을 Canvas 크기에 맞춰 조정 (여백 고려)
            margin = 20  # 여백
            new_width = max(self.CANVAS_MIN_WIDTH, event.size().width() - margin)
            new_height = max(self.CANVAS_MIN_HEIGHT, event.size().height() - margin)
            
            # 현재 크기와 다를 때만 조정
            if (self.canvas_area.width() != new_width or 
                self.canvas_area.height() != new_height):
                self.canvas_area.resize(new_width, new_height)
                print(f"[Canvas 리사이즈] 동적 조정: {new_width}x{new_height}")
        # else:
            # print(f"[Canvas 리사이즈] 정적 크기 유지 또는 canvas_area 없음 - is_new_collage: {self.is_new_collage}")
    
    def set_canvas_background_and_resize(self, background_image: QPixmap, width: int, height: int):
        """배경 이미지를 설정하고 캔버스 크기를 조정합니다."""
        if background_image and not background_image.isNull():
            self.background_image = background_image
            self.has_background = True
            
            # 캔버스 크기를 배경 이미지 크기에 맞춰 조정
            self.canvas_area.resize(width, height)
            # self.canvas_area.setMinimumSize(width, height) # 이 라인 제거 또는 주석 처리
            
            # 캔버스 영역 다시 그리기
            self.canvas_area.update()
            
            # 부모 윈도우에 크기 변경 알림
            parent_window = self.window()
            if hasattr(parent_window, 'canvas_size_changed'):
                parent_window.canvas_size_changed()
            
            # 윈도우 크기를 캔버스 크기에 맞춰 조정
            self.adjust_window_size_to_canvas(width, height)
            
            print(f"[Canvas] 배경 이미지 설정 완료: {width}x{height}")
            self._save_state_and_update_actions() # 상태 저장
        else:
            print("[Canvas] 배경 이미지 설정 실패: 유효하지 않은 이미지")
    
    def remove_canvas_background(self):
        """캔버스 배경 이미지를 제거합니다."""
        if self.has_background:
            self.background_image = None
            self.has_background = False
            self.canvas_area.update()
            print("[Canvas] 배경 이미지가 제거되었습니다.")
            self._save_state_and_update_actions() # 상태 저장
        else:
            print("[Canvas] 제거할 배경 이미지가 없습니다.")
    
    def get_background_image(self) -> QPixmap:
        """현재 배경 이미지를 반환합니다."""
        return self.background_image if self.has_background else None

    def _save_state_and_update_actions(self):
        """상태를 저장하고 MainWindow의 Undo/Redo 액션 상태를 업데이트합니다."""
        self._save_state()
        # MainWindow에 undo/redo 가능 상태 업데이트 알림
        main_window = self.window()
        if hasattr(main_window, 'update_undo_redo_actions'):
            main_window.update_undo_redo_actions()

    def _restore_state(self, state):
        """주어진 상태로 캔버스를 복원합니다."""
        if not state:
            return

        # ... (기존 아이템 제거, 캔버스 크기 복원, 배경 복원 로직) ...
        # 기존 아이템 제거
        for item_to_remove in self.furniture_items:
            # 시그널 연결 해제 시도 (오류 방지)
            try:
                item_to_remove.item_changed.disconnect(self._save_state_and_update_actions)
            except TypeError:
                pass # 연결되지 않았을 경우
            item_to_remove.deleteLater()
        self.furniture_items.clear()
        self.selected_items.clear()

        # 캔버스 크기 복원
        canvas_w, canvas_h = state["canvas_size"]
        self.canvas_area.resize(canvas_w, canvas_h)

        # 배경 이미지 복원
        self.has_background = state.get("has_background", False)
        background_image_data = state.get("background_image_data")
        if self.has_background and background_image_data:
            try:
                image_data_bytes = base64.b64decode(background_image_data)
                pixmap = QPixmap()
                if pixmap.loadFromData(image_data_bytes):
                    self.background_image = pixmap
                else:
                    self.background_image = None
                    self.has_background = False
                    print("[Undo/Redo] 배경 이미지 데이터 로드 실패")
            except Exception as e:
                print(f"[Undo/Redo] 배경 이미지 복원 중 오류: {e}")
                self.background_image = None
                self.has_background = False
        else:
            self.background_image = None
            self.has_background = False

        supabase_client = SupabaseClient()
        all_furniture_db_data = {f_data['id']: f_data for f_data in supabase_client.get_furniture_list()}

        for item_state in sorted(state["furniture_items"], key=lambda x: x["z_order"]):
            furniture_id = item_state["id"]
            if furniture_id in all_furniture_db_data:
                furniture_db_data = all_furniture_db_data[furniture_id]
                furniture = Furniture(**furniture_db_data)
                item = FurnitureItem(furniture, self.canvas_area)
                
                # FurnitureItem의 item_changed 시그널을 Canvas의 상태 저장 메서드에 연결
                item.item_changed.connect(self._save_state_and_update_actions)
                
                item.move(QPoint(*item_state["position"]))
                item.setFixedSize(QSize(*item_state["size"]))
                item.is_flipped = item_state.get("is_flipped", False)
                if item.is_flipped:
                    transform = QTransform().scale(-1, 1)
                    if item.original_pixmap and not item.original_pixmap.isNull():
                        item.pixmap = item.original_pixmap.transformed(transform)
                    else:
                        item.pixmap = item.pixmap.transformed(transform)
                item.color_temp = item_state.get("color_temp", 6500)
                item.brightness = item_state.get("brightness", 100)
                item.saturation = item_state.get("saturation", 100)
                if (item.color_temp != 6500 or item.brightness != 100 or item.saturation != 100):
                    if item.original_pixmap is None or item.original_pixmap.isNull():
                        item.original_pixmap = item.pixmap.copy()
                    item.preview_pixmap = item.original_pixmap.copy()
                    item.apply_image_effects(item.color_temp, item.brightness, item.saturation)
                item.show()
                self.furniture_items.append(item)
            else:
                print(f"[Undo/Redo] 복원 중 가구 ID({furniture_id})를 찾을 수 없음")

        self.update_bottom_panel()
        self.canvas_area.update()
        main_window = self.window()
        if hasattr(main_window, 'update_undo_redo_actions'):
            main_window.update_undo_redo_actions()
        print(f"[Undo/Redo] 상태 복원됨.")

    def undo(self):
        """이전 상태로 되돌립니다."""
        if len(self.undo_stack) < 2: # 현재 UI 상태와 최소 한 개의 이전 상태가 있어야 undo 가능
            print("[Undo/Redo] Undo 스택에 이전 상태가 충분하지 않음 (스택 크기 < 2)")
            return

        current_ui_state = self.undo_stack.pop() # (1) 스택에서 현재 UI 상태를 꺼냄
        self.redo_stack.append(current_ui_state)  # (2) 현재 UI 상태를 redo 스택에 넣음
        
        # 이제 undo_stack의 최상단이 복원할 이전 상태가 됨
        state_to_restore = self.undo_stack[-1] # (3) 복원할 이전 상태를 가져옴 (pop하지 않음)
        self._restore_state(state_to_restore)    # (4) 이전 상태로 복원
        
        # _restore_state 호출 후 여기서 한 번 더 명시적으로 호출하여 일관성 보장
        main_window = self.window()
        if hasattr(main_window, 'update_undo_redo_actions'):
            main_window.update_undo_redo_actions()
        print(f"[Undo/Redo] Undo 실행. 복원된 상태 peek: {len(self.undo_stack[-1]['furniture_items']) if self.undo_stack else 'N/A'} items. Redo 스택 크기: {len(self.redo_stack)}")

    def redo(self):
        """되돌린 상태를 다시 실행합니다."""
        if not self.redo_stack:
            print("[Undo/Redo] Redo 스택 비어있음")
            return
            
        state_to_restore = self.redo_stack.pop() # (1) redo 스택에서 복원할 상태를 꺼냄
        self.undo_stack.append(state_to_restore)  # (2) 복원할 상태를 undo 스택에 다시 넣음 (가장 마지막 상태가 됨)
        
        self._restore_state(state_to_restore)    # (3) 해당 상태로 복원
        
        # _restore_state 호출 후 여기서 한 번 더 명시적으로 호출하여 일관성 보장
        main_window = self.window()
        if hasattr(main_window, 'update_undo_redo_actions'):
            main_window.update_undo_redo_actions()
        print(f"[Undo/Redo] Redo 실행. 복원된 상태: {len(state_to_restore['furniture_items'])} items. Undo 스택 크기: {len(self.undo_stack)}")

    def remove_furniture_item(self, item_to_remove):
        """지정된 가구 아이템을 캔버스에서 제거합니다."""
        if item_to_remove in self.furniture_items:
            self.furniture_items.remove(item_to_remove)
            item_to_remove.deleteLater()
            # 선택된 아이템이 제거된 아이템이라면 선택 해제
            if self.selected_item is item_to_remove:
                self.selected_item = None
            if item_to_remove in self.selected_items:
                self.selected_items.remove(item_to_remove)
            
            # 하단 패널 업데이트 (번호표 포함)
            self.update_bottom_panel()
            self._save_state_and_update_actions() # 상태 저장
            self.canvas_area.update() # 캔버스 영역 갱신
            print(f"아이템 제거됨: {item_to_remove.furniture.name}, 남은 아이템: {len(self.furniture_items)}")
        else:
            print(f"제거할 아이템을 찾을 수 없음: {item_to_remove}")

    def resize_canvas(self):
        """기존 가구들을 유지하면서 캔버스 크기만 조절합니다."""
        dialog = CanvasSizeDialog(self)
        # 현재 캔버스 크기를 기본값으로 설정
        dialog.width_input.setValue(self.canvas_area.width())
        dialog.height_input.setValue(self.canvas_area.height())
        
        if dialog.exec():
            new_width, new_height = dialog.get_size()
            
            # 캔버스 크기만 변경 (가구는 그대로 유지)
            self.canvas_area.resize(new_width, new_height)
            
            # 윈도우 크기를 새 캔버스 크기에 맞춰 조정
            self.adjust_window_size_to_canvas(new_width, new_height)
            
            # 부모 윈도우에 크기 변경 알림
            parent_window = self.window()
            if hasattr(parent_window, 'canvas_size_changed'):
                parent_window.canvas_size_changed()
            
            print(f"[캔버스 크기 조절] 새 크기: {new_width}x{new_height}")
            self._save_state_and_update_actions() # 상태 저장

    def export_collage(self):
        """현재 콜라주를 이미지 파일로 내보냅니다."""
        if not self.furniture_items:
            self._show_warning_message("경고", "내보낼 콜라주가 없습니다.")
            return
        
        # 파일 저장 다이얼로그
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "콜라주 내보내기",
            os.path.expanduser("~/Desktop/collage.png"),
            "PNG 파일 (*.png);;JPG 파일 (*.jpg);;모든 파일 (*.*)"
        )
        
        if file_path:
            try:
                # 콜라주 이미지 생성
                collage_image = self._generate_collage_image()
                
                # 파일 저장
                if collage_image.save(file_path):
                    self._show_information_message("성공", "콜라주가 성공적으로 내보내졌습니다.")
                else:
                    self._show_critical_message("오류", "콜라주 내보내기에 실패했습니다.")
                    
            except Exception as e:
                self._show_critical_message("오류", f"콜라주 내보내기 중 오류가 발생했습니다: {str(e)}")

    def keyPressEvent(self, event):
        """키보드 이벤트를 처리합니다."""
        if event.key() == Qt.Key.Key_Delete:
            # 선택된 아이템들 삭제
            if self.selected_items:
                items_to_remove = self.selected_items.copy()
                for item in items_to_remove:
                    self.remove_furniture_item(item)
        elif event.key() == Qt.Key.Key_Escape:
            # 모든 선택 해제
            self.deselect_all_items()
        elif event.key() in [Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right]:
            # 방향키로 선택된 가구 이동
            if self.selected_items:
                self.move_selected_items_with_arrow_keys(event.key())
        else:
            super().keyPressEvent(event)

    # Z-order 관련 메서드들
    def bring_to_front(self, item):
        """가구 아이템을 맨 앞으로 가져옵니다."""
        if item in self.furniture_items:
            # 상태 저장 (Undo/Redo용)
            self._save_state()
            
            # 리스트에서 제거 후 맨 뒤에 추가 (맨 앞으로)
            self.furniture_items.remove(item)
            self.furniture_items.append(item)
            
            # Qt 위젯 계층에서도 맨 앞으로
            item.raise_()
            
            # 하단 패널과 번호표 업데이트
            self.update_bottom_panel()
            self.update_number_labels()
            
            # Undo/Redo 액션 업데이트
            self._save_state_and_update_actions()

    def send_to_back(self, item):
        """가구 아이템을 맨 뒤로 보냅니다."""
        if item in self.furniture_items:
            # 상태 저장 (Undo/Redo용)
            self._save_state()
            
            # 리스트에서 제거 후 맨 앞에 추가 (맨 뒤로)
            self.furniture_items.remove(item)
            self.furniture_items.insert(0, item)
            
            # Qt 위젯 계층에서도 맨 뒤로
            item.lower()
            
            # 하단 패널과 번호표 업데이트
            self.update_bottom_panel()
            self.update_number_labels()
            
            # Undo/Redo 액션 업데이트
            self._save_state_and_update_actions()

    def move_selected_items_with_arrow_keys(self, key):
        """방향키로 선택된 가구 아이템들을 이동합니다."""
        if not self.selected_items:
            return
        
        # 이동 거리 설정 (Ctrl/Cmd 키를 누르면 정밀 이동)
        modifiers = QGuiApplication.keyboardModifiers()
        if modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier):
            move_distance = 1   # Ctrl/Cmd + 방향키: 1픽셀씩 정밀 이동
        else:
            move_distance = 5   # 방향키만: 5픽셀씩 이동
        
        # 방향에 따른 이동 벡터 계산
        delta_x = 0
        delta_y = 0
        
        if key == Qt.Key.Key_Left:
            delta_x = -move_distance
        elif key == Qt.Key.Key_Right:
            delta_x = move_distance
        elif key == Qt.Key.Key_Up:
            delta_y = -move_distance
        elif key == Qt.Key.Key_Down:
            delta_y = move_distance
        
        # 캔버스 경계 체크를 위한 준비
        canvas_rect = self.canvas_area.rect()
        
        # 모든 선택된 아이템이 경계를 벗어나지 않는지 확인
        valid_delta_x = delta_x
        valid_delta_y = delta_y
        
        for item in self.selected_items:
            new_x = item.x() + delta_x
            new_y = item.y() + delta_y
            
            # 경계 체크 및 조정
            if new_x < 0:
                valid_delta_x = max(valid_delta_x, -item.x())
            elif new_x + item.width() > canvas_rect.width():
                valid_delta_x = min(valid_delta_x, canvas_rect.width() - item.x() - item.width())
            
            if new_y < 0:
                valid_delta_y = max(valid_delta_y, -item.y())
            elif new_y + item.height() > canvas_rect.height():
                valid_delta_y = min(valid_delta_y, canvas_rect.height() - item.y() - item.height())
        
        # 실제로 이동할 거리가 있는 경우에만 이동
        if valid_delta_x != 0 or valid_delta_y != 0:
            # 상태 저장 (Undo/Redo용)
            self._save_state()
            
            # 모든 선택된 아이템 이동
            for item in self.selected_items:
                new_pos = QPoint(item.x() + valid_delta_x, item.y() + valid_delta_y)
                item.move(new_pos)
            
            # 캔버스 영역 업데이트 (번호표 위치 업데이트)
            self.canvas_area.update()
            
            # 상태 저장 및 액션 업데이트
            self._save_state_and_update_actions()

