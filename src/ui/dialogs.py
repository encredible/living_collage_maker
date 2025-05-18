from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                             QLabel, QSpinBox, QPushButton)

class CanvasSizeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("캔버스 크기 설정")
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 가로 크기 입력
        width_layout = QHBoxLayout()
        width_label = QLabel("가로 크기 (픽셀):")
        self.width_spin = QSpinBox()
        self.width_spin.setRange(400, 2000)
        self.width_spin.setValue(800)
        width_layout.addWidget(width_label)
        width_layout.addWidget(self.width_spin)
        layout.addLayout(width_layout)
        
        # 세로 크기 입력
        height_layout = QHBoxLayout()
        height_label = QLabel("세로 크기 (픽셀):")
        self.height_spin = QSpinBox()
        self.height_spin.setRange(300, 1500)
        self.height_spin.setValue(600)
        height_layout.addWidget(height_label)
        height_layout.addWidget(self.height_spin)
        layout.addLayout(height_layout)
        
        # 버튼
        button_layout = QHBoxLayout()
        ok_button = QPushButton("확인")
        cancel_button = QPushButton("취소")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
    
    def get_size(self):
        """입력된 캔버스 크기를 반환합니다."""
        return self.width_spin.value(), self.height_spin.value() 