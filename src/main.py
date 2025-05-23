import sys
import time

from PyQt6.QtCore import QPoint, Qt, QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (QApplication, QHBoxLayout, QMainWindow, QSplitter,
                             QWidget)

from src.ui.canvas import Canvas
from src.ui.panels.bottom_panel import BottomPanel
from src.ui.panels.explorer_panel import ExplorerPanel
from src.services.html_export_service import HtmlExportService


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Living Collage Maker")
        self.previous_canvas_global_top_left = None # 이전 캔버스 전역 좌상단 좌표
        self.is_initializing_geometry = True # 초기화 중 플래그
        
        # HTML 내보내기 서비스 초기화
        self.html_export_service = HtmlExportService(self)
        
        self.setup_ui()
        self.setup_menubar()
    
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
    
    def export_html_collage(self):
        """콜라주를 HTML 형식으로 내보냅니다."""
        self.html_export_service.export_collage_to_html(
            canvas_widget=self.canvas,
            furniture_items=self.canvas.furniture_items,
            parent_window=self
        )
    
    def update_bottom_panel(self):
        """하단 패널을 업데이트합니다."""
        self.bottom_panel.update_panel(self.canvas.furniture_items)
    
    def closeEvent(self, event):
        """애플리케이션 종료 시 호출됩니다."""
        print("[애플리케이션] 종료 중... 스레드 정리 시작")
        try:
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

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Living Collage Maker")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()