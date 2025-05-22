import sys

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtGui import QAction

from ui.canvas import Canvas
from ui.panels import ExplorerPanel, BottomPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Living Collage Maker")
        self.setup_ui()
        self.setup_menubar()
    
    def setup_ui(self):
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 상단 레이아웃 (캔버스와 우측 패널)
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)
        
        # 캔버스
        self.canvas = Canvas()
        top_layout.addWidget(self.canvas)
        
        # 우측 패널
        self.explorer_panel = ExplorerPanel()
        top_layout.addWidget(self.explorer_panel)
        
        main_layout.addLayout(top_layout)
        
        # 하단 패널
        self.bottom_panel = BottomPanel()
        main_layout.addWidget(self.bottom_panel)
        
        # 초기 크기 설정
        self.resize(1200, 800)
    
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

    def update_bottom_panel(self):
        """하단 패널을 업데이트합니다."""
        self.bottom_panel.update_panel(self.canvas.furniture_items)

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Living Collage Maker")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()