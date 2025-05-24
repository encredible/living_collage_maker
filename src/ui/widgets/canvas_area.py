"""
캔버스 영역 위젯
배경 이미지 표시 기능을 제공하는 캔버스 영역입니다.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QPixmap
from PyQt6.QtCore import Qt


class CanvasArea(QWidget):
    """배경 이미지를 표시할 수 있는 캔버스 영역 위젯"""
    
    def __init__(self, parent_canvas=None):
        super().__init__()
        self.parent_canvas = parent_canvas
    
    def paintEvent(self, event):
        """배경 이미지와 함께 캔버스 영역을 그립니다."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 배경 이미지가 있으면 그리기
        if (self.parent_canvas and 
            hasattr(self.parent_canvas, 'background_image') and 
            self.parent_canvas.background_image and 
            not self.parent_canvas.background_image.isNull()):
            
            # 배경 이미지를 캔버스 영역 전체에 맞춰 그리기
            painter.drawPixmap(
                self.rect(),
                self.parent_canvas.background_image,
                self.parent_canvas.background_image.rect()
            )
        else:
            # 배경 이미지가 없으면 기본 흰색 배경
            painter.fillRect(self.rect(), Qt.GlobalColor.white)
        
        # 부모 클래스의 paintEvent 호출 (필요한 경우)
        super().paintEvent(event) 