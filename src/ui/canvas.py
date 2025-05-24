import datetime
import json
import os

from PyQt6.QtCore import (QPoint, QRect, Qt)
from PyQt6.QtGui import (QColor, QPainter, QPen, QPixmap, QTransform)
from PyQt6.QtWidgets import (QFileDialog,
                             QMenu,
                             QMessageBox, QVBoxLayout,
                             QWidget)
from PyQt6.QtGui import QGuiApplication

from src.models.furniture import Furniture
from src.services.supabase_client import SupabaseClient
from src.ui.dialogs import CanvasSizeDialog
from src.ui.utils import ImageAdjuster
from src.ui.widgets import FurnitureItem


class Canvas(QWidget):
    CANVAS_COLOR = QColor("#e0e0e0") # 클래스 변수로 CANVAS_COLOR 추가

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        # Canvas 자체의 최소 크기는 내부 canvas_area에 의해 결정되도록 할 수 있음
        # 또는 아주 작은 값으로 설정하여 canvas_area가 크기를 주도하도록 함
        self.setMinimumSize(100, 100) # Canvas의 최소 크기
        self.setStyleSheet(""" 
            QWidget { 
                background-color: transparent; /* Canvas 자체는 투명하게 처리 */ 
                border: none; /* Canvas 자체의 테두리는 제거 */
            }
        """)
        
        # 이미지 조정 시스템 초기화
        if not ImageAdjuster._initialized:
            ImageAdjuster.initialize()
        
        # Canvas의 메인 레이아웃
        # 이 레이아웃은 canvas_area만을 포함하고, canvas_area의 크기에 맞춰 Canvas 크기가 조절되도록 함
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 캔버스 영역 (실제 가구가 배치되는 곳, 이 위젯의 크기를 사용자가 조절)
        self.canvas_area = QWidget() # QWidget으로 유지
        self.canvas_area.setMinimumSize(300, 200) # canvas_area의 최소 크기
        self.canvas_area.setStyleSheet("""
            QWidget { /* canvas_area 스타일 */
                background-color: white;
                border: 2px solid #2C3E50; /* 작업 영역 테두리 */
            }
        """)
        layout.addWidget(self.canvas_area) # Canvas의 레이아웃에 canvas_area 추가
        
        # 초기 상태 설정
        self.is_new_collage = True
        self.furniture_items = []
        self.selected_items = []  # 다중 선택을 위해 리스트로 변경
        
        # 우클릭 메뉴 활성화 (canvas_area에 대해)
        self.canvas_area.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.canvas_area.customContextMenuRequested.connect(self.show_context_menu)
        
        # 캔버스 영역 클릭 이벤트 설정 (canvas_area에 대해)
        self.canvas_area.mousePressEvent = self.canvas_mouse_press_event
        
        # 키보드 포커스 설정 (키 이벤트 수신을 위해)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def canvas_mouse_press_event(self, event):
        # 빈 공간 클릭 시 선택 해제 (Ctrl/Cmd 키를 누르지 않은 경우만)
        if event.button() == Qt.MouseButton.LeftButton:
            modifiers = QGuiApplication.keyboardModifiers()
            if not (modifiers & Qt.KeyboardModifier.ControlModifier):
                self.deselect_all_items()
            # 키보드 포커스 설정 (키 이벤트 수신을 위해)
            self.setFocus()
    
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
    
    # 모든 가구 아이템 선택 해제
    def deselect_all_items(self):
        for item in self.selected_items:
            item.is_selected = False
            item.update()
        self.selected_items.clear()
        self.update_bottom_panel()
    
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
                # canvas_area 크기 설정 (이때 eventFilter가 호출되어 Canvas 크기도 조절됨)
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
                        # QMessageBox.warning(self, "경고", f"콜라주에 포함된 가구(ID: {furniture_id})를 현재 데이터베이스에서 찾을 수 없습니다. 해당 아이템은 제외됩니다.")
                        self._show_warning_message("경고", f"콜라주에 포함된 가구(ID: {furniture_id})를 현재 데이터베이스에서 찾을 수 없습니다. 해당 아이템은 제외됩니다.")
                        # 누락된 아이템 정보 기록 또는 처리
                        continue # 다음 아이템으로 넘어감
                
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
        """새 콜라주를 생성합니다."""
        dialog = CanvasSizeDialog(self)
        if dialog.exec():
            width, height = dialog.get_size()
            
            # 기존 가구 아이템 제거
            for item in self.furniture_items:
                item.deleteLater()
            self.furniture_items.clear()
            
            self.selected_items.clear()
            
            # canvas_area 크기 설정 (이때 eventFilter가 호출되어 Canvas 크기도 조절됨)
            self.canvas_area.setFixedSize(width, height)
            self.is_new_collage = False # <--- 여기를 False로 수정
            
            # self.canvas_area.update() # 필요시 canvas_area 직접 업데이트
            # self.update() # Canvas 업데이트 (paintEvent 호출하여 크기 텍스트 등 갱신)
            
            # 하단 패널 업데이트
            self.update_bottom_panel()
            self.is_new_collage = True # 새 콜라주 상태로 설정

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
        return image
    
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
                
                # 새로 추가된 아이템을 선택 상태로 설정
                self.select_furniture_item(item)
                
                # 하단 패널 업데이트
                # self.update_bottom_panel() # select_furniture_item 내부에서 호출되므로 중복 제거
                
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
        # 메인 윈도우에서 하단 패널 업데이트
        main_window = self.window()
        if main_window and hasattr(main_window, 'bottom_panel'):
            # MainWindow의 bottom_panel 속성에 직접 접근
            main_window.bottom_panel.update_panel(self.furniture_items)
        else:
            print("[Canvas] MainWindow 또는 bottom_panel을 찾을 수 없습니다.")
    
    def paintEvent(self, event):
        # Canvas 자체의 paintEvent는 이제 배경을 그리지 않거나 최소한의 것만 그림
        # 대부분의 그리기는 self.canvas_area에서 일어나거나, 
        # self.canvas_area의 내용을 기반으로 Canvas가 추가적인 정보를 그림(예: 크기 텍스트)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Canvas의 배경은 투명하게 처리했으므로, 여기서는 아무것도 그리지 않거나
        # canvas_area 주변에만 필요한 것을 그릴 수 있음.

        # canvas_area의 현재 크기를 가져와서 Canvas에 표시 (디버깅 또는 정보 제공용)
        if not self.is_new_collage and hasattr(self, 'canvas_area'):
            pen = QPen(QColor("#888888")) # 다른 색으로 표시
            pen.setWidth(1)
            painter.setPen(pen)
            size_text = f"Area: {self.canvas_area.width()} x {self.canvas_area.height()} px"
            # Canvas의 왼쪽 상단에 canvas_area 크기 표시
            painter.drawText(QRect(5, 5, self.width() - 10, 20), 
                          Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                          size_text)
        # super().paintEvent(event) # 만약 QWidget의 기본 paintEvent가 필요하다면
    
    def export_collage(self):
        """현재 콜라주를 이미지로 내보냅니다."""
        if not self.furniture_items:
            self._show_warning_message("경고", "내보낼 콜라주가 없습니다.")
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
                # 공통 이미지 생성 메서드 사용
                image = self._generate_collage_image()
                
                # 이미지 저장
                image.save(file_path)
                self._show_information_message("성공", "콜라주가 성공적으로 저장되었습니다.")
                
            except Exception as e:
                self._show_critical_message("오류", f"이미지 저장 중 오류가 발생했습니다: {str(e)}")

    def keyPressEvent(self, event):
        """키보드 이벤트 처리"""
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            # Delete 또는 Backspace 키로 선택된 아이템들 삭제
            if self.selected_items:
                print(f"[키보드 삭제] 선택된 {len(self.selected_items)}개 아이템 삭제")
                items_to_delete = self.selected_items.copy()
                for item in items_to_delete:
                    if item in self.furniture_items:
                        self.furniture_items.remove(item)
                    item.deleteLater()
                self.selected_items.clear()
                self.update_bottom_panel()
                print("[키보드 삭제] 완료")
        else:
            super().keyPressEvent(event)

    def resize_canvas(self):
        """캔버스 크기를 조절합니다."""
        # 현재 캔버스 크기를 초기값으로 사용
        current_width = self.canvas_area.width()
        current_height = self.canvas_area.height()
        
        # 캔버스 크기 다이얼로그 표시
        dialog = CanvasSizeDialog(
            initial_width=current_width,
            initial_height=current_height,
            title="캔버스 크기 조절",
            parent=self
        )
        
        if dialog.exec():
            new_width, new_height = dialog.get_canvas_size()
            
            # 캔버스 크기 변경
            self.canvas_area.setFixedSize(new_width, new_height)
            
            # 캔버스 밖으로 벗어난 가구들 처리
            self.handle_furniture_out_of_bounds()
            
            # 부모 윈도우에 크기 변경 알림
            parent_window = self.window()
            if hasattr(parent_window, 'canvas_size_changed'):
                parent_window.canvas_size_changed()
            
            self._show_information_message(
                "알림", 
                f"캔버스 크기가 {new_width}x{new_height}로 변경되었습니다."
            )
    
    def handle_furniture_out_of_bounds(self):
        """캔버스 영역을 벗어난 가구들을 캔버스 내로 이동시킵니다."""
        canvas_width = self.canvas_area.width()
        canvas_height = self.canvas_area.height()
        
        moved_items = []
        
        for item in self.furniture_items:
            item_rect = item.geometry()
            moved = False
            
            # 오른쪽 경계 체크
            if item_rect.right() > canvas_width:
                new_x = max(0, canvas_width - item.width())
                item.move(new_x, item.y())
                moved = True
            
            # 아래쪽 경계 체크
            if item_rect.bottom() > canvas_height:
                new_y = max(0, canvas_height - item.height())
                item.move(item.x(), new_y)
                moved = True
            
            # 왼쪽 경계 체크 (음수 좌표)
            if item.x() < 0:
                item.move(0, item.y())
                moved = True
            
            # 위쪽 경계 체크 (음수 좌표)
            if item.y() < 0:
                item.move(item.x(), 0)
                moved = True
            
            if moved:
                moved_items.append(item.furniture.name)
        
        # 이동된 가구가 있으면 알림
        if moved_items:
            if len(moved_items) == 1:
                message = f"'{moved_items[0]}' 가구가 캔버스 내로 이동되었습니다."
            else:
                message = f"{len(moved_items)}개의 가구가 캔버스 내로 이동되었습니다."
            
            self._show_information_message("가구 위치 조정", message)