import sys
import time

from PyQt6.QtCore import QPoint, Qt, QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (QApplication, QHBoxLayout, QMainWindow, QSplitter,
                             QWidget, QMessageBox)

from src.ui.canvas import Canvas
from src.ui.panels.bottom_panel import BottomPanel
from src.ui.panels.explorer_panel import ExplorerPanel
from src.services.html_export_service import HtmlExportService
from src.services.pdf_export_service import PdfExportService
from src.services.app_state_service import (AppStateService, AppState, WindowState, 
                                           ColumnWidthState, CanvasState, PanelState, 
                                           FurnitureItemState)
from src.services.supabase_client import SupabaseClient
from src.models.furniture import Furniture
from src.ui.widgets import FurnitureItem


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Living Collage Maker")
        self.previous_canvas_global_top_left = None # 이전 캔버스 전역 좌상단 좌표
        self.is_initializing_geometry = True # 초기화 중 플래그
        
        # 앱 상태 서비스 초기화
        self.app_state_service = AppStateService()
        
        # HTML 내보내기 서비스 초기화
        self.html_export_service = HtmlExportService(self)
        
        # PDF 내보내기 서비스 초기화
        self.pdf_export_service = PdfExportService(self)
        
        self.setup_ui()
        self.setup_menubar()
        
        # 상태 복원 (UI 설정 후에 호출)
        QTimer.singleShot(50, self.restore_app_state)
    
    def showEvent(self, event):
        """윈도우가 처음 표시될 때 호출됩니다."""
        super().showEvent(event)
        # UI가 완전히 로드된 후 geometry를 가져오기 위해 QTimer.singleShot 사용
        QTimer.singleShot(0, self.initialize_canvas_coordinates)

    def initialize_canvas_coordinates(self):
        """초기 캔버스 전역 좌상단 좌표를 저장합니다."""
        if self.canvas and self.canvas.isVisible(): # 캔버스가 존재하고 보이는지 확인
            self.previous_canvas_global_top_left = self.canvas.mapToGlobal(QPoint(0, 0))
            self.is_initializing_geometry = False # 초기화 완료
        else:
            # 캔버스가 아직 준비되지 않았으면 잠시 후 다시 시도
            QTimer.singleShot(100, self.initialize_canvas_coordinates)
    
    def resizeEvent(self, event):
        """창 크기가 변경될 때 호출됩니다."""
        super().resizeEvent(event) # 부모 클래스의 resizeEvent 호출
        if not self.is_initializing_geometry: # 초기화가 끝난 후에만 호출
            self.update_furniture_positions_on_canvas_move()
    
    def setup_ui(self):
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 캔버스
        self.canvas = Canvas()
        
        # 우측 패널
        self.explorer_panel = ExplorerPanel()
        
        # 하단 패널
        self.bottom_panel = BottomPanel()

        # 수평 스플리터 (캔버스 + 우측 패널)
        self.splitter_horizontal = QSplitter(Qt.Orientation.Horizontal)
        self.splitter_horizontal.addWidget(self.canvas)
        self.splitter_horizontal.addWidget(self.explorer_panel)
        
        # 수평 스플리터의 스트레치 비율 설정 (캔버스 확장 위주)
        self.splitter_horizontal.setStretchFactor(0, 1) # 캔버스
        self.splitter_horizontal.setStretchFactor(1, 0) # 탐색 패널
        self.splitter_horizontal.setSizes([800, 400]) # 초기 크기

        # 메인 수직 스플리터 (수평 스플리터 + 하단 패널)
        self.splitter_main_vertical = QSplitter(Qt.Orientation.Vertical)
        self.splitter_main_vertical.addWidget(self.splitter_horizontal)
        self.splitter_main_vertical.addWidget(self.bottom_panel)

        # 메인 수직 스플리터의 스트레치 비율 설정
        self.splitter_main_vertical.setStretchFactor(0, 1) # 상단 영역 확장 위주
        self.splitter_main_vertical.setStretchFactor(1, 0) # 하단 패널
        self.splitter_main_vertical.setSizes([700, 100]) # 초기 크기

        # 스플리터 시그널 연결
        self.splitter_main_vertical.splitterMoved.connect(self.handle_splitter_moved)
        self.splitter_horizontal.splitterMoved.connect(self.handle_splitter_moved)

        # 메인 레이아웃에 메인 수직 스플리터 추가
        main_layout = QHBoxLayout(central_widget) 
        main_layout.addWidget(self.splitter_main_vertical)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 초기 크기 설정
        self.resize(1200, 800)
    
    def handle_splitter_moved(self, pos, index):
        """스플리터 핸들이 움직였을 때 호출됩니다."""
        if not self.is_initializing_geometry: # 초기화가 끝난 후에만 호출
            self.update_furniture_positions_on_canvas_move()
    
    def update_furniture_positions_on_canvas_move(self):
        """캔버스 지오메트리 변경에 따라 가구 위치를 업데이트하는 공통 로직."""
        if self.is_initializing_geometry or not self.canvas or not self.canvas.isVisible() or self.previous_canvas_global_top_left is None:
            # 초기화 중이거나, 캔버스가 준비되지 않았거나, 이전 지오메트리가 없으면 반환
            if not self.is_initializing_geometry and self.canvas and self.canvas.isVisible() and not self.previous_canvas_global_top_left:
                 # 이 경우는 초기화 직후 splitterMoved가 먼저 호출될 수 있는 엣지 케이스 방지
                 self.previous_canvas_global_top_left = self.canvas.mapToGlobal(QPoint(0, 0))
            return

        current_canvas_global_top_left = self.canvas.mapToGlobal(QPoint(0, 0))
        
        if self.previous_canvas_global_top_left is current_canvas_global_top_left:
            pass 

        offset_x = current_canvas_global_top_left.x() - self.previous_canvas_global_top_left.x()
        offset_y = current_canvas_global_top_left.y() - self.previous_canvas_global_top_left.y()

        if offset_x != 0 or offset_y != 0:
            self.canvas.adjust_furniture_positions(-offset_x, -offset_y)
        
        # 현재 지오메트리를 다음 비교를 위해 저장
        self.previous_canvas_global_top_left = current_canvas_global_top_left # QRect는 값 타입처럼 동작하지만, 명시적 복사가 안전할 수 있음

    def canvas_size_changed(self):
        """캔버스 크기가 변경되었을 때 호출됩니다."""
        print("[MainWindow] 캔버스 크기 변경 감지")
        
        # 캔버스 좌표 시스템 재초기화
        if hasattr(self, 'previous_canvas_global_top_left'):
            self.previous_canvas_global_top_left = None
        
        # 좌표 시스템 다시 초기화
        QTimer.singleShot(100, self.initialize_canvas_coordinates)
        
        # UI 강제 업데이트
        self.update()

    def setup_menubar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu('파일')

        save_action = QAction('저장하기', self)
        save_action.triggered.connect(lambda: self.canvas.save_collage())
        file_menu.addAction(save_action)

        load_action = QAction('불러오기', self)
        load_action.triggered.connect(lambda: self.canvas.load_collage())
        file_menu.addAction(load_action)

        new_action = QAction('새 콜라주 만들기', self)
        new_action.triggered.connect(lambda: self.canvas.create_new_collage())
        file_menu.addAction(new_action)

        export_action = QAction('콜라주 내보내기', self)
        export_action.triggered.connect(lambda: self.canvas.export_collage())
        file_menu.addAction(export_action)

        html_export_action = QAction('콜라주 HTML로 내보내기', self)
        html_export_action.triggered.connect(self.export_html_collage)
        file_menu.addAction(html_export_action)
        
        pdf_export_action = QAction('콜라주 PDF로 내보내기', self)
        pdf_export_action.triggered.connect(self.export_pdf_collage)
        file_menu.addAction(pdf_export_action)
        
        file_menu.addSeparator()
        
        # 앱 상태 관리 메뉴
        reset_layout_action = QAction('레이아웃 초기화', self)
        reset_layout_action.triggered.connect(self.reset_app_layout)
        file_menu.addAction(reset_layout_action)
        
        clear_cache_action = QAction('앱 캐시 정리', self)
        clear_cache_action.triggered.connect(self.clear_app_cache)
        file_menu.addAction(clear_cache_action)
    
    def export_html_collage(self):
        """콜라주를 HTML 형식으로 내보냅니다."""
        self.html_export_service.export_collage_to_html(
            canvas_widget=self.canvas,
            furniture_items=self.canvas.furniture_items,
            parent_window=self
        )
    
    def export_pdf_collage(self):
        """콜라주를 PDF 형식으로 내보냅니다."""
        self.pdf_export_service.export_collage_to_pdf(
            canvas_widget=self.canvas,
            furniture_items=self.canvas.furniture_items,
            parent_window=self
        )
    
    def update_bottom_panel(self):
        """하단 패널을 업데이트합니다."""
        self.bottom_panel.update_panel(self.canvas.furniture_items)
    
    def closeEvent(self, event):
        """애플리케이션 종료 시 호출됩니다."""
        print("[애플리케이션] 종료 중... 상태 저장 및 스레드 정리 시작")
        try:
            # 앱 상태 저장
            self.save_app_state()
            
            # 탐색 패널의 모든 스레드 정리
            if hasattr(self.explorer_panel, 'furniture_model'):
                print("[애플리케이션] ExplorerPanel 스레드 정리 중...")
                self.explorer_panel.furniture_model.clear_furniture()
            
            # 잠시 대기하여 스레드들이 정리될 시간을 줍니다
            time.sleep(0.1)
            print("[애플리케이션] 스레드 정리 완료")
            
        except Exception as e:
            print(f"[애플리케이션] 종료 중 오류 발생: {e}")
        finally:
            event.accept()  # 종료 허용
    
    def save_app_state(self):
        """현재 앱 상태를 저장합니다."""
        try:
            print("[MainWindow] 앱 상태 저장 시작...")
            
            # 윈도우 상태 수집
            window_state = WindowState(
                width=self.width(),
                height=self.height(),
                x=self.x(),
                y=self.y()
            )
            
            # 컬럼 너비 상태 수집
            explorer_column_widths = {}
            if hasattr(self.explorer_panel, 'furniture_table'):
                for i in range(4):  # 탐색 패널은 4개 컬럼
                    explorer_column_widths[i] = self.explorer_panel.furniture_table.columnWidth(i)
            
            bottom_column_widths = {}
            if hasattr(self.bottom_panel, 'selected_panel'):
                bottom_column_widths = self.bottom_panel.selected_panel.column_widths.copy()
            
            column_widths_state = ColumnWidthState(
                explorer_panel=explorer_column_widths,
                bottom_panel=bottom_column_widths
            )
            
            # 캔버스 상태 수집
            canvas_state = CanvasState(
                width=self.canvas.canvas_area.width(),
                height=self.canvas.canvas_area.height()
            )
            
            # 패널 상태 수집
            panel_state = PanelState(
                horizontal_splitter_sizes=self.splitter_horizontal.sizes(),
                vertical_splitter_sizes=self.splitter_main_vertical.sizes()
            )
            
            # 가구 아이템 상태 수집
            furniture_items_state = []
            for i, item in enumerate(self.canvas.furniture_items):
                item_state = FurnitureItemState(
                    furniture_id=item.furniture.id,
                    position_x=item.x(),
                    position_y=item.y(),
                    width=item.width(),
                    height=item.height(),
                    z_order=i,
                    is_flipped=getattr(item, 'is_flipped', False),
                    color_temperature=getattr(item, 'color_temperature', 6500),
                    brightness=getattr(item, 'brightness', 100),
                    saturation=getattr(item, 'saturation', 100)
                )
                furniture_items_state.append(item_state)
            
            # 전체 앱 상태 생성
            app_state = AppState(
                window=window_state,
                column_widths=column_widths_state,
                canvas=canvas_state,
                panels=panel_state,
                furniture_items=furniture_items_state
            )
            
            # 상태 저장
            if self.app_state_service.save_app_state(app_state):
                print(f"[MainWindow] 앱 상태 저장 완료 - 가구 {len(furniture_items_state)}개")
            else:
                print("[MainWindow] 앱 상태 저장 실패")
                
        except Exception as e:
            print(f"[MainWindow] 앱 상태 저장 중 오류: {e}")
            import traceback
            traceback.print_exc()

    def restore_app_state(self):
        """앱 상태를 복원합니다."""
        try:
            print("[MainWindow] 앱 상태 복원 시작...")
            app_state = self.app_state_service.load_app_state()
            
            if not app_state:
                print("[MainWindow] 복원할 상태가 없습니다.")
                return
            
            # 윈도우 크기와 위치 복원
            if app_state.window:
                self.resize(app_state.window.width, app_state.window.height)
                self.move(app_state.window.x, app_state.window.y)
            
            # 스플리터 크기 복원
            if app_state.panels:
                if app_state.panels.horizontal_splitter_sizes:
                    self.splitter_horizontal.setSizes(app_state.panels.horizontal_splitter_sizes)
                
                if app_state.panels.vertical_splitter_sizes:
                    self.splitter_main_vertical.setSizes(app_state.panels.vertical_splitter_sizes)
            
            # 컬럼 너비 복원
            if app_state.column_widths:
                # 탐색 패널 컬럼 너비 복원
                if hasattr(self.explorer_panel, 'furniture_table') and app_state.column_widths.explorer_panel:
                    for column_index, width in app_state.column_widths.explorer_panel.items():
                        self.explorer_panel.furniture_table.setColumnWidth(column_index, width)
                
                # 하단 패널 컬럼 너비 복원
                if hasattr(self.bottom_panel, 'selected_panel') and app_state.column_widths.bottom_panel:
                    self.bottom_panel.selected_panel.column_widths = app_state.column_widths.bottom_panel
                    # 실제 테이블이 있으면 적용
                    if hasattr(self.bottom_panel.selected_panel, 'selected_table'):
                        for column_index, width in app_state.column_widths.bottom_panel.items():
                            self.bottom_panel.selected_panel.selected_table.setColumnWidth(column_index, width)
            
            # 캔버스 크기 복원
            if app_state.canvas and app_state.canvas.width > 0 and app_state.canvas.height > 0:
                self.canvas.canvas_area.setFixedSize(app_state.canvas.width, app_state.canvas.height)
                self.canvas.is_new_collage = False
            
            # 가구 아이템들 복원
            if app_state.furniture_items:
                QTimer.singleShot(50, lambda: self.restore_furniture_items(app_state.furniture_items))
            
            print(f"[MainWindow] 앱 상태 복원 완료 - 윈도우: {app_state.window.width}x{app_state.window.height}, 가구: {len(app_state.furniture_items)}개")
            
        except Exception as e:
            print(f"[MainWindow] 앱 상태 복원 중 오류: {e}")
            import traceback
            traceback.print_exc()
    
    def restore_furniture_items(self, furniture_items_state):
        """가구 아이템들을 복원합니다."""
        try:
            print(f"[MainWindow] 가구 아이템 복원 시작: {len(furniture_items_state)}개")
            
            # 기존 가구 아이템들 제거
            for item in self.canvas.furniture_items:
                item.deleteLater()
            self.canvas.furniture_items.clear()
            self.canvas.selected_item = None
            
            if not furniture_items_state:
                return
            
            # 탐색 패널에서 이미 로드된 가구 데이터 활용
            furniture_dict = {}
            if hasattr(self.explorer_panel, 'furniture_model') and self.explorer_panel.furniture_model.furniture_items:
                # 캐시된 데이터 사용
                for furniture in self.explorer_panel.furniture_model.furniture_items:
                    furniture_dict[furniture.id] = furniture
                print(f"[MainWindow] 캐시된 가구 데이터 사용: {len(furniture_dict)}개")
            else:
                # 캐시가 없으면 Supabase에서 조회
                supabase = SupabaseClient()
                all_furniture = supabase.get_furniture_list()
                furniture_dict = {furniture_data["id"]: Furniture(**furniture_data) for furniture_data in all_furniture}
                print(f"[MainWindow] Supabase에서 가구 데이터 조회: {len(furniture_dict)}개")
            
            # z_order 순으로 정렬하여 복원
            sorted_items = sorted(furniture_items_state, key=lambda x: x.z_order)
            restored_count = 0
            
            for item_state in sorted_items:
                if item_state.furniture_id in furniture_dict:
                    # 가구 데이터 가져오기
                    furniture = furniture_dict[item_state.furniture_id]
                    
                    # FurnitureItem 생성
                    item = FurnitureItem(furniture, self.canvas.canvas_area)
                    
                    # 위치와 크기 설정
                    item.move(QPoint(item_state.position_x, item_state.position_y))
                    item.setFixedSize(item_state.width, item_state.height)
                    
                    # 좌우 반전 설정
                    if item_state.is_flipped:
                        from PyQt6.QtGui import QTransform
                        transform = QTransform()
                        transform.scale(-1, 1)
                        item.pixmap = item.pixmap.transformed(transform)
                        item.is_flipped = True
                    
                    # 이미지 조정 설정
                    if (item_state.color_temperature != 6500 or 
                        item_state.brightness != 100 or 
                        item_state.saturation != 100):
                        
                        # 이미지 조정 정보 적용
                        item.color_temperature = item_state.color_temperature
                        item.brightness = item_state.brightness
                        item.saturation = item_state.saturation
                        
                        # 이미지에 조정 효과 적용
                        if hasattr(item, 'apply_image_adjustments'):
                            item.apply_image_adjustments()
                    
                    # 아이템 표시 및 목록에 추가
                    item.show()
                    self.canvas.furniture_items.append(item)
                    restored_count += 1
            
            # 하단 패널 업데이트
            self.canvas.update_bottom_panel()
            print(f"[MainWindow] 가구 아이템 복원 완료: {restored_count}개")
            
        except Exception as e:
            print(f"[MainWindow] 가구 아이템 복원 중 오류: {e}")
            import traceback
            traceback.print_exc()

    def reset_app_layout(self):
        """앱 레이아웃을 초기화합니다."""
        reply = QMessageBox.question(
            self, 
            "레이아웃 초기화", 
            "현재 레이아웃을 초기화하고 기본 설정으로 되돌리시겠습니까?\n"
            "창 크기, 패널 크기, 컬럼 너비가 기본값으로 변경됩니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                print("[MainWindow] 레이아웃 초기화 시작...")
                
                # 저장된 앱 상태 삭제
                self.app_state_service.clear_app_state()
                
                # 윈도우 크기 초기화
                self.resize(1200, 800)
                self.move(100, 100)
                
                # 스플리터 크기 초기화
                self.splitter_horizontal.setSizes([800, 400])
                self.splitter_main_vertical.setSizes([700, 100])
                
                # 탐색 패널 컬럼 너비 초기화
                if hasattr(self.explorer_panel, 'column_widths'):
                    self.explorer_panel.column_widths = {0: 100, 1: 100, 2: 200, 3: 100}
                    self.explorer_panel.setup_column_widths()
                
                # 하단 패널 컬럼 너비 초기화
                if hasattr(self.bottom_panel, 'selected_panel'):
                    self.bottom_panel.selected_panel.column_widths = {
                        0: 300, 1: 120, 2: 80, 3: 100, 4: 80, 5: 120, 6: 100,
                        7: 140, 8: 80, 9: 200, 10: 150, 11: 100, 12: 60
                    }
                    self.bottom_panel.selected_panel.setup_column_widths()
                
                # 캔버스는 현재 상태 유지 (가구 삭제하지 않음)
                
                QMessageBox.information(self, "완료", "레이아웃이 초기화되었습니다.")
                print("[MainWindow] 레이아웃 초기화 완료")
                
            except Exception as e:
                print(f"[MainWindow] 레이아웃 초기화 중 오류: {e}")
                QMessageBox.critical(self, "오류", f"레이아웃 초기화 중 오류가 발생했습니다:\n{str(e)}")

    def clear_app_cache(self):
        """앱 캐시를 정리합니다."""
        reply = QMessageBox.question(
            self, 
            "캐시 정리", 
            "애플리케이션 캐시를 정리하시겠습니까?\n"
            "이미지 캐시와 앱 상태가 삭제되며, 다음 시작 시 기본 설정으로 시작됩니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                print("[MainWindow] 캐시 정리 시작...")
                
                # 앱 상태 캐시 삭제
                app_state_cleared = self.app_state_service.clear_app_state()
                
                # 이미지 캐시 삭제 (ImageService를 통해)
                from src.services.image_service import ImageService
                image_service = ImageService()
                image_service.clear_cache()
                
                if app_state_cleared:
                    QMessageBox.information(
                        self, 
                        "완료", 
                        "캐시가 정리되었습니다.\n다음 시작 시 기본 설정으로 시작됩니다."
                    )
                    print("[MainWindow] 캐시 정리 완료")
                else:
                    QMessageBox.warning(self, "경고", "일부 캐시 정리에 실패했습니다.")
                
            except Exception as e:
                print(f"[MainWindow] 캐시 정리 중 오류: {e}")
                QMessageBox.critical(self, "오류", f"캐시 정리 중 오류가 발생했습니다:\n{str(e)}")

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Living Collage Maker")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()