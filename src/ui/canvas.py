from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton,
                             QMenu, QMessageBox, QFileDialog)
from PyQt6.QtCore import Qt, QSize, QPoint, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QPixmap, QDrag, QPainterPath, QTransform
from models.furniture import Furniture
from ui.dialogs import CanvasSizeDialog
from ui.panels import ExplorerPanel, BottomPanel
from services.image_service import ImageService
from services.supabase_client import SupabaseClient
import os

class FurnitureItem(QWidget):
    def __init__(self, furniture: Furniture, parent=None):
        super().__init__(parent)
        self.furniture = furniture
        self.image_service = ImageService()
        self.supabase = SupabaseClient()
        
        # 이미지 로드
        self.load_image()
        
        # 드래그 앤 드롭 설정
        self.setMouseTracking(True)
        self.is_resizing = False
        self.resize_handle = QRect(self.width() - 20, self.height() - 20, 20, 20)
        self.maintain_aspect_ratio = False  # 비율 유지 여부를 저장하는 변수 추가
    
    def load_image(self):
        """가구 이미지를 로드합니다."""
        try:
            # Supabase에서 이미지 다운로드
            image_data = self.supabase.get_furniture_image(self.furniture.image_filename)
            
            # 이미지 캐시 및 썸네일 생성
            self.pixmap = self.image_service.download_and_cache_image(
                image_data, 
                self.furniture.image_filename
            )
            
            # 이미지가 유효하지 않은 경우 기본 이미지 생성
            if self.pixmap.isNull():
                self.pixmap = QPixmap(200, 200)
                self.pixmap.fill(QColor("#f0f0f0"))
                painter = QPainter(self.pixmap)
                painter.setPen(QPen(QColor("#2C3E50")))
                painter.drawText(self.pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "이미지 로드 실패")
                painter.end()
            
            # 이미지 비율에 맞게 크기 설정
            self.original_ratio = self.pixmap.width() / self.pixmap.height()
            initial_width = 200
            initial_height = int(initial_width / self.original_ratio)
            self.setFixedSize(initial_width, initial_height)
            
        except Exception as e:
            print(f"이미지 로드 중 오류 발생: {e}")
            # 에러 이미지 생성
            self.pixmap = QPixmap(200, 200)
            self.pixmap.fill(QColor("#f0f0f0"))
            painter = QPainter(self.pixmap)
            painter.setPen(QPen(QColor("#2C3E50")))
            painter.drawText(self.pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "이미지 로드 실패")
            painter.end()
            self.setFixedSize(200, 200)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 이미지 그리기 (비율 유지 여부에 따라 다르게 처리)
        if self.maintain_aspect_ratio:
            # 비율 유지하면서 그리기
            scaled_pixmap = self.pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            x = (self.width() - scaled_pixmap.width()) // 2
            y = (self.height() - scaled_pixmap.height()) // 2
            painter.drawPixmap(x, y, scaled_pixmap)
        else:
            # 비율 무시하고 꽉 채우기
            scaled_pixmap = self.pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            painter.drawPixmap(0, 0, scaled_pixmap)
        
        # 테두리 그리기
        pen = QPen(QColor("#2C3E50"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        
        # 리사이즈 핸들 그리기
        painter.fillRect(self.resize_handle, QColor("#2C3E50"))
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.resize_handle.contains(event.pos()):
                self.is_resizing = True
            else:
                self.raise_()  # 위젯을 최상위로
                self.old_pos = event.pos()
    
    def mouseMoveEvent(self, event):
        if self.is_resizing:
            # Shift 키가 눌린 상태인지 확인
            self.maintain_aspect_ratio = event.modifiers() & Qt.KeyboardModifier.ShiftModifier
            
            if self.maintain_aspect_ratio:
                # 비율 유지하면서 크기 조절
                new_width = max(100, event.pos().x())
                new_height = int(new_width / self.original_ratio)
            else:
                # 비율 무시하고 자유롭게 크기 조절
                new_width = max(100, event.pos().x())
                new_height = max(100, event.pos().y())
            
            self.setFixedSize(new_width, new_height)
            self.resize_handle = QRect(new_width - 20, new_height - 20, 20, 20)
        elif event.buttons() & Qt.MouseButton.LeftButton:
            # 드래그로 이동
            delta = event.pos() - self.old_pos
            self.move(self.pos() + delta)
    
    def mouseReleaseEvent(self, event):
        self.is_resizing = False
    
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        delete_action = menu.addAction("삭제")
        flip_action = menu.addAction("좌우 반전")
        action = menu.exec(event.globalPos())
        
        if action == delete_action:
            print(f"[삭제] 가구 아이템 삭제 시작: {self.furniture.name}")
            # 부모 캔버스 영역에서 캔버스 찾기
            canvas_area = self.parent()
            if canvas_area:
                canvas = canvas_area.parent()
                if canvas and hasattr(canvas, 'furniture_items'):
                    if self in canvas.furniture_items:
                        print(f"[삭제] 캔버스에서 가구 아이템 제거: {self.furniture.name}")
                        canvas.furniture_items.remove(self)
                        # 하단 패널 업데이트
                        main_window = canvas.window()
                        if main_window:
                            print("[삭제] 메인 윈도우 찾음")
                            # 하단 패널 찾기
                            for child in main_window.findChildren(QWidget):
                                if isinstance(child, BottomPanel):
                                    print(f"[삭제] 하단 패널 찾음, 현재 가구 수: {len(canvas.furniture_items)}")
                                    child.update_panel(canvas.furniture_items)
                                    break
                                else:
                                    print(f"[삭제] 다른 위젯 발견: {type(child).__name__}")
                        else:
                            print("[삭제] 메인 윈도우를 찾을 수 없음")
                    else:
                        print(f"[삭제] 가구 아이템이 캔버스 목록에 없음: {self.furniture.name}")
                else:
                    print("[삭제] 캔버스를 찾을 수 없거나 furniture_items 속성이 없음")
            else:
                print("[삭제] 캔버스 영역을 찾을 수 없음")
            self.deleteLater()
            print(f"[삭제] 가구 아이템 삭제 완료: {self.furniture.name}")
        elif action == flip_action:
            # 이미지 좌우 반전
            transform = QTransform()
            transform.scale(-1, 1)  # x축 방향으로 -1을 곱하여 좌우 반전
            self.pixmap = self.pixmap.transformed(transform)
            self.update()  # 위젯 다시 그리기

    def deleteLater(self):
        """가구 아이템이 삭제될 때 하단 패널을 업데이트합니다."""
        # 부모 캔버스에서 가구 아이템 목록에서 제거
        canvas = self.parent()
        if canvas and hasattr(canvas, 'furniture_items'):
            if self in canvas.furniture_items:
                canvas.furniture_items.remove(self)
                canvas.update_bottom_panel()
        super().deleteLater()

class Canvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumSize(800, 600)
        self.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 2px solid #2C3E50;
            }
        """)
        
        # 레이아웃 설정
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # 여백 제거
        
        # 캔버스 영역
        self.canvas_area = QWidget()
        self.canvas_area.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 2px solid #2C3E50;
            }
        """)
        layout.addWidget(self.canvas_area)
        
        # 초기 상태 설정
        self.is_new_collage = True
        self.furniture_items = []
    
    def create_new_collage(self):
        """새 콜라주를 생성합니다."""
        dialog = CanvasSizeDialog(self)
        if dialog.exec():
            width, height = dialog.get_size()
            
            # 기존 가구 아이템 제거
            for item in self.furniture_items:
                item.deleteLater()
            self.furniture_items.clear()
            
            # 캔버스 크기 설정
            self.canvas_area.setFixedSize(width, height)
            self.is_new_collage = False
            
            # 윈도우 크기 조정
            window = self.window()
            if window:
                # 윈도우 크기를 캔버스 크기 + 여유 공간으로 설정
                window_width = width + 400  # 우측 패널 너비 고려
                window_height = height + 100  # 상단 여유 공간
                
                # 최소 크기 설정
                min_width = max(800, window_width)
                min_height = max(600, window_height)
                
                # 윈도우 크기 조정
                window.setMinimumSize(min_width, min_height)
                window.resize(min_width, min_height)
                
                # 캔버스 크기 조정
                self.setMinimumSize(width, height)
                self.resize(width, height)
            
            self.canvas_area.update()
            
            # 하단 패널 업데이트
            self.update_bottom_panel()
    
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
                
                # 하단 패널 업데이트
                self.update_bottom_panel()
                
                event.acceptProposedAction()
        except Exception as e:
            print(f"드롭 이벤트 처리 중 오류 발생: {e}")
            event.ignore()
    
    def update_bottom_panel(self):
        """하단 패널을 업데이트합니다."""
        # 메인 윈도우에서 하단 패널 업데이트
        main_window = self.window()
        if main_window:
            main_window.update_bottom_panel()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 배경 그리기
        painter.fillRect(self.rect(), QColor("#ffffff"))
        
        # 가이드라인 그리기
        if self.is_new_collage:
            pen = QPen(QColor("#2C3E50"))
            pen.setStyle(Qt.PenStyle.DashLine)
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(self.rect().adjusted(10, 10, -10, -10))
        else:
            # 캔버스 크기 표시
            pen = QPen(QColor("#2C3E50"))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
            
            # 크기 텍스트 표시
            painter.setPen(QPen(QColor("#2C3E50")))
            size_text = f"{self.width()} x {self.height()} px"
            painter.drawText(self.rect().adjusted(10, 10, -10, -10), 
                           Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                           size_text)
    
    def export_collage(self):
        """현재 콜라주를 이미지로 내보냅니다."""
        if not self.furniture_items:
            QMessageBox.warning(self, "경고", "내보낼 콜라주가 없습니다.")
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
                
                # 이미지 저장
                image.save(file_path)
                QMessageBox.information(self, "성공", "콜라주가 성공적으로 저장되었습니다.")
                
            except Exception as e:
                QMessageBox.critical(self, "오류", f"이미지 저장 중 오류가 발생했습니다: {str(e)}") 