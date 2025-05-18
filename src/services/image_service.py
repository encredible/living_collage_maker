import os
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import QBuffer, QIODevice, Qt, QSize
import hashlib
from concurrent.futures import ThreadPoolExecutor
import threading
import weakref

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
        # 파일 확장자가 .png가 아니면 .png로 변경
        if not image_filename.lower().endswith('.png'):
            image_filename = f"{os.path.splitext(image_filename)[0]}.png"
        return os.path.join(self.cache_dir, image_filename)
    
    def is_image_cached(self, image_filename):
        """이미지가 캐시되어 있는지 확인합니다."""
        return os.path.exists(self.get_cached_image_path(image_filename))
    
    def download_and_cache_image(self, image_data, image_filename):
        """이미지를 다운로드하고 캐시합니다."""
        if not image_data:
            print(f"[오류] 이미지 데이터가 없습니다: {image_filename}")
            return QPixmap()
            
        cache_path = self.get_cached_image_path(image_filename)
        
        try:
            # 메모리 캐시 확인
            with self.cache_lock:
                if image_filename in self.memory_cache:
                    print(f"[메모리 캐시] 이미지 로드: {image_filename}")
                    return self.memory_cache[image_filename]
            
            # 디스크 캐시 확인
            if self.is_image_cached(image_filename):
                print(f"[디스크 캐시] 이미지 로드: {image_filename}")
                pixmap = QPixmap(cache_path)
                if not pixmap.isNull():
                    with self.cache_lock:
                        self.memory_cache[image_filename] = pixmap
                    return pixmap
            
            # 캐시된 이미지가 없으면 다운로드하고 캐시
            print(f"[스토리지] 이미지 다운로드: {image_filename}")
            pixmap = QPixmap()
            if not pixmap.loadFromData(image_data):
                print(f"[오류] 이미지 로드 실패: {image_filename}")
                return QPixmap()
            
            # 이미지 크기 최적화
            optimized_pixmap = self.optimize_image(pixmap)
            
            # 이미지를 캐시 디스크에 PNG 형식으로 저장
            if not optimized_pixmap.save(cache_path, "PNG", quality=85):
                print(f"[오류] 이미지 저장 실패: {image_filename}")
            
            # 메모리 캐시에 저장
            with self.cache_lock:
                self.memory_cache[image_filename] = optimized_pixmap
            
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
        # 메모리 캐시 삭제
        with self.cache_lock:
            self.memory_cache.clear()
        
        # 파일 캐시 삭제
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
        return buffer.data()
    
    def __del__(self):
        """스레드 풀 종료"""
        try:
            self.executor.shutdown(wait=False)
        except:
            pass 