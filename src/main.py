import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout
from ui.canvas import Canvas
from ui.panels import ExplorerPanel, BottomPanel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Living Collage Maker")
        self.setup_ui()
    
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
    
    def update_bottom_panel(self):
        """하단 패널을 업데이트합니다."""
        self.bottom_panel.update_panel(self.canvas.furniture_items)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 