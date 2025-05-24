import time

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QPixmap


class ImageProcessor(QThread):
    """이미지 처리를 별도 스레드에서 수행하는 클래스"""
    finished = pyqtSignal(QPixmap)
    error = pyqtSignal(str)  # 에러 시그널 추가
    
    def __init__(self, pixmap, color_temp, brightness, saturation):
        super().__init__()
        self.pixmap = pixmap.copy() if pixmap and not pixmap.isNull() else QPixmap()  # 안전한 복사
        self.color_temp = color_temp
        self.brightness = brightness
        self.saturation = saturation
        self.should_stop = False
        
    def run(self):
        """스레드 실행 메서드"""
        try:
            if self.should_stop:
                return
                
            # 입력 이미지 유효성 검사
            if self.pixmap.isNull() or self.pixmap.width() == 0 or self.pixmap.height() == 0:
                print("[ImageProcessor] 유효하지 않은 이미지입니다.")
                return
                
            start_time = time.time()
            
            # ImageAdjuster를 import하여 사용
            from .image_adjuster import ImageAdjuster
            
            # 처리 중 중단 요청 확인
            if self.should_stop:
                return
            
            result = ImageAdjuster.apply_effects(
                self.pixmap, 
                self.color_temp, 
                self.brightness, 
                self.saturation
            )
            
            # 처리 완료 후 중단 요청 확인
            if self.should_stop:
                return
                
            # 결과 유효성 검사
            if result.isNull():
                print("[ImageProcessor] 이미지 처리 결과가 비어있습니다.")
                self.error.emit("이미지 처리 결과가 비어있습니다.")
                return
                
            end_time = time.time()
            processing_time = (end_time - start_time) * 1000
            
            if processing_time > 1: # 1ms 이상 소요 시 디버깅용 로그
                print(f"[ImageProcessor] 처리 시간: {processing_time:.2f}ms (크기: {self.pixmap.width()}x{self.pixmap.height()})")
            
            # 결과의 복사본을 emit (메모리 안전성)
            self.finished.emit(result.copy())
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            error_msg = f"이미지 처리 중 오류 발생: {str(e)}"
            print(f"[ImageProcessor] {error_msg}")
            self.error.emit(error_msg)
        
    def quit(self):
        """스레드를 안전하게 종료합니다."""
        self.should_stop = True
        super().quit() 