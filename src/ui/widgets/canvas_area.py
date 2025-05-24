"""
캔버스 영역 위젯
배경 이미지 표시 기능을 제공하는 캔버스 영역입니다.
"""

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush
from PyQt6.QtWidgets import QWidget


class CanvasArea(QWidget):
    """배경 이미지를 표시할 수 있는 캔버스 영역 위젯"""
    
    def __init__(self, parent_canvas=None):
        super().__init__()
        self.parent_canvas = parent_canvas
    
    def paintEvent(self, event):
        """배경 이미지와 번호표와 함께 캔버스 영역을 그립니다."""
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
        
        # 가구 아이템들의 번호표 그리기
        self.draw_furniture_number_labels(painter)
        
        # 부모 클래스의 paintEvent 호출 (필요한 경우)
        super().paintEvent(event)
    
    def draw_furniture_number_labels(self, painter):
        """가구 아이템들의 번호표를 그립니다."""
        if not self.parent_canvas or not hasattr(self.parent_canvas, 'furniture_items'):
            return
            
        # 번호표 설정
        label_size = 18  # 원형 라벨 크기 (24 -> 18로 축소)
        offset = 1       # 가구 영역에서 벗어날 거리 (3 -> 1로 더 가깝게)
        
        for furniture_item in self.parent_canvas.furniture_items:
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
            font.setPointSize(8)  # 폰트 크기도 조금 줄임
            painter.setFont(font)
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, str(furniture_item.number_label_value)) 