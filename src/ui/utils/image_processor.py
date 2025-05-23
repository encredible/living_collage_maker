import time
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QPixmap


class ImageProcessor(QThread):
    """이미지 처리를 별도 스레드에서 수행하는 클래스"""
    finished = pyqtSignal(QPixmap)
    
    def __init__(self, pixmap, color_temp, brightness, saturation):
        super().__init__()
        self.pixmap = pixmap
        self.color_temp = color_temp
        self.brightness = brightness
        self.saturation = saturation
        self.should_stop = False
        
    def run(self):
        """스레드 실행 메서드"""
        if self.should_stop:
            return
            
        start_time = time.time()
        
        # ImageAdjuster를 import하여 사용
        from .image_adjuster import ImageAdjuster
        
        result = ImageAdjuster.apply_effects(
            self.pixmap, 
            self.color_temp, 
            self.brightness, 
            self.saturation
        )
        
        if self.should_stop:
            return
            
        end_time = time.time()
        processing_time = (end_time - start_time) * 1000
        
        if processing_time > 1: # 1ms 이상 소요 시 디버깅용 로그
            print(f"[ImageProcessor] 처리 시간: {processing_time:.2f}ms (크기: {self.pixmap.width()}x{self.pixmap.height()})") # TODO: 로깅 라이브러리로 대체 고려
        
        self.finished.emit(result)
        
    def quit(self):
        """스레드를 안전하게 종료합니다."""
        self.should_stop = True
        super().quit() 