import os
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import QBuffer, QIODevice, Qt, QSize
import hashlib

class ImageService:
    def __init__(self):
        self.cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.image')
        os.makedirs(self.cache_dir, exist_ok=True)
        self.memory_cache = {}  # 메모리 캐시 추가
    
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
        cache_path = self.get_cached_image_path(image_filename)
        
        # 캐시된 이미지가 있으면 캐시에서 로드
        if self.is_image_cached(image_filename):
            print(f"[캐시] 이미지 로드: {image_filename}")
            pixmap = QPixmap(cache_path)
            if not pixmap.isNull():
                self.memory_cache[image_filename] = pixmap  # 메모리 캐시에 저장
                return pixmap
        
        # 캐시된 이미지가 없으면 다운로드하고 캐시
        print(f"[스토리지] 이미지 다운로드: {image_filename}")
        pixmap = QPixmap()
        pixmap.loadFromData(image_data)
        
        if not pixmap.isNull():
            # 이미지를 캐시 디렉토리에 PNG 형식으로 저장
            pixmap.save(cache_path, "PNG")
            print(f"[캐시] 이미지 저장 완료: {image_filename}")
            # 메모리 캐시에 저장
            self.memory_cache[image_filename] = pixmap
        else:
            print(f"[오류] 이미지 로드 실패: {image_filename}")
        
        return pixmap
    
    def create_thumbnail(self, pixmap, size):
        """썸네일을 생성합니다."""
        if pixmap.isNull():
            return pixmap
        
        # 원본 비율 유지하면서 크기 조정
        return pixmap.scaled(
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
    
    def clear_cache(self):
        """캐시를 모두 삭제합니다."""
        # 메모리 캐시 삭제
        self.memory_cache.clear()
        
        # 파일 캐시 삭제
        if os.path.exists(self.cache_dir):
            for file in os.listdir(self.cache_dir):
                os.remove(os.path.join(self.cache_dir, file))
            print("[캐시] 모든 캐시 파일이 삭제되었습니다.")
    
    def pixmap_to_bytes(self, pixmap: QPixmap) -> bytes:
        """QPixmap을 bytes로 변환합니다."""
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        pixmap.save(buffer, "PNG")
        return buffer.data() 