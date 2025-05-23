import os
import threading
import weakref
from concurrent.futures import ThreadPoolExecutor

from PyQt6.QtCore import QBuffer, QIODevice, Qt
from PyQt6.QtGui import QPixmap


class ImageService:
    def __init__(self):
        self.cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.image')
        os.makedirs(self.cache_dir, exist_ok=True)
        self.memory_cache = weakref.WeakValueDictionary()  # 약한 참조를 사용한 메모리 캐시
        self.cache_lock = threading.Lock()  # 스레드 안전성을 위한 락
        self.executor = ThreadPoolExecutor(max_workers=4)  # 이미지 로딩을 위한 스레드 풀
        self._cleanup_timer = None
    
    def get_cached_image_path(self, image_filename):
        """캐시된 이미지의 경로를 반환합니다."""
        name, ext = os.path.splitext(image_filename)
        # 파일 확장자가 .png가 아니거나, 대소문자가 다른 경우 .png로 통일
        final_filename = f"{name}.png"
        return os.path.join(self.cache_dir, final_filename)
    
    def is_image_cached(self, image_filename):
        """이미지가 캐시되어 있는지 확인합니다."""
        return os.path.exists(self.get_cached_image_path(image_filename))
    
    def download_and_cache_image(self, image_data, image_filename):
        """이미지를 다운로드하고 캐시합니다."""
        if not image_data:
            return QPixmap()

        cache_path = self.get_cached_image_path(image_filename)
        normalized_filename = os.path.basename(cache_path)
        
        try:
            # 메모리 캐시 확인
            with self.cache_lock:
                if normalized_filename in self.memory_cache:
                    return self.memory_cache[normalized_filename]
            
            # 디스크 캐시 확인
            # is_image_cached는 내부적으로 get_cached_image_path를 호출하므로 image_filename 원본을 넘겨도 됨
            if self.is_image_cached(image_filename): 
                pixmap = QPixmap(cache_path)
                if not pixmap.isNull():
                    with self.cache_lock:
                        self.memory_cache[normalized_filename] = pixmap # 정규화된 파일명으로 저장
                    return pixmap
            
            # 캐시된 이미지가 없으면 다운로드하고 캐시
            pixmap = QPixmap()
            if not pixmap.loadFromData(image_data):
                return QPixmap()
            
            optimized_pixmap = self.optimize_image(pixmap)
            
            if not optimized_pixmap.save(cache_path, "PNG", quality=85):
                print(f"[오류] 이미지 저장 실패: {normalized_filename}")
            
            with self.cache_lock:
                self.memory_cache[normalized_filename] = optimized_pixmap
            
            return optimized_pixmap
            
        except Exception as e:
            print(f"[오류] 이미지 처리 중 예외 발생: {e}")
            return QPixmap()
    
    def optimize_image(self, pixmap):
        """이미지 크기를 최적화합니다."""
        if pixmap.isNull():
            return pixmap
            
        # 이미지가 너무 큰 경우 크기 조정
        max_size = 1920  # 최대 크기
        if pixmap.width() > max_size or pixmap.height() > max_size:
            return pixmap.scaled(
                max_size, max_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        return pixmap
    
    def create_thumbnail(self, pixmap, size):
        """썸네일을 생성합니다."""
        if pixmap.isNull():
            return pixmap
        
        # 원본 비율 유지하면서 크기 조정
        return pixmap.scaled(
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation  # 빠른 변환 모드 사용
        )
    
    def clear_cache(self):
        """캐시를 모두 삭제합니다."""
        with self.cache_lock:
            self.memory_cache.clear()
        
        if os.path.exists(self.cache_dir):
            for file in os.listdir(self.cache_dir):
                try:
                    os.remove(os.path.join(self.cache_dir, file))
                except Exception as e:
                    print(f"[오류] 캐시 파일 삭제 실패: {e}")
            print("[캐시] 모든 캐시 파일이 삭제되었습니다.")
    
    def pixmap_to_bytes(self, pixmap: QPixmap) -> bytes:
        """QPixmap을 bytes로 변환합니다."""
        if pixmap.isNull():
            return b''
            
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if not pixmap.save(buffer, "PNG", quality=85):
            return b''
        return bytes(buffer.data()) # bytes()로 명시적 변환
    
    def __del__(self):
        """스레드 풀 종료"""
        try:
            self.executor.shutdown(wait=False)
        except:
            pass 