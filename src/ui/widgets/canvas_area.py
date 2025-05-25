"""
캔버스 영역 위젯
배경 이미지 표시 기능을 제공하는 캔버스 영역입니다.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtWidgets import QWidget


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
        
        # 내부 그림자 효과를 위한 추가 테두리 그리기
        rect = self.rect()
        
        # 내부 하이라이트 (왼쪽 상단)
        painter.setPen(QPen(QColor(255, 255, 255, 100), 1))  # 반투명 흰색
        painter.drawLine(rect.left() + 1, rect.top() + 1, rect.right() - 1, rect.top() + 1)  # 상단 라인
        painter.drawLine(rect.left() + 1, rect.top() + 1, rect.left() + 1, rect.bottom() - 1)  # 왼쪽 라인
        
        # 내부 그림자 (오른쪽 하단)
        painter.setPen(QPen(QColor(0, 0, 0, 30), 1))  # 반투명 검은색
        painter.drawLine(rect.right() - 2, rect.top() + 2, rect.right() - 2, rect.bottom() - 2)  # 오른쪽 라인
        painter.drawLine(rect.left() + 2, rect.bottom() - 2, rect.right() - 2, rect.bottom() - 2)  # 하단 라인
        
        # 부모 클래스의 paintEvent 호출 (필요한 경우)
        super().paintEvent(event) 