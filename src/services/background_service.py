"""
배경 이미지 관리 서비스
캔버스의 배경 이미지 설정, 제거, 저장/불러오기 기능을 제공합니다.
"""

import os
from typing import Optional, Tuple
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QByteArray, QBuffer, QIODevice


class BackgroundService:
    """캔버스 배경 이미지 관리 서비스"""
    
    def __init__(self):
        self.current_background_image: Optional[QPixmap] = None
        self.current_background_path: str = ""
        self.has_background: bool = False
    
    def set_background_image(self, image_path: str) -> bool:
        """
        배경 이미지를 설정합니다.
        
        Args:
            image_path: 이미지 파일 경로
            
        Returns:
            bool: 설정 성공 여부
        """
        if not os.path.exists(image_path):
            print(f"[BackgroundService] 배경 이미지 파일을 찾을 수 없습니다: {image_path}")
            return False
        
        # 이미지 로드
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            print(f"[BackgroundService] 배경 이미지 로드에 실패했습니다: {image_path}")
            return False
        
        self.current_background_image = pixmap
        self.current_background_path = image_path
        self.has_background = True
        
        print(f"[BackgroundService] 배경 이미지 설정 완료: {image_path}")
        print(f"[BackgroundService] 이미지 크기: {pixmap.width()}x{pixmap.height()}")
        
        return True
    
    def remove_background(self) -> None:
        """배경 이미지를 제거합니다."""
        self.current_background_image = None
        self.current_background_path = ""
        self.has_background = False
        print("[BackgroundService] 배경 이미지가 제거되었습니다.")
    
    def get_background_image(self) -> Optional[QPixmap]:
        """
        현재 배경 이미지를 반환합니다.
        
        Returns:
            Optional[QPixmap]: 배경 이미지 또는 None
        """
        return self.current_background_image
    
    def get_background_size(self) -> Optional[Tuple[int, int]]:
        """
        배경 이미지의 크기를 반환합니다.
        
        Returns:
            Optional[Tuple[int, int]]: (width, height) 또는 None
        """
        if self.current_background_image and not self.current_background_image.isNull():
            return (self.current_background_image.width(), self.current_background_image.height())
        return None
    
    def is_background_set(self) -> bool:
        """
        배경 이미지가 설정되어 있는지 확인합니다.
        
        Returns:
            bool: 배경 이미지 설정 여부
        """
        return self.has_background and self.current_background_image is not None
    
    def save_background_data(self, image_path: str) -> bytes:
        """
        이미지 파일을 바이트 데이터로 변환하여 저장용 데이터를 생성합니다.
        
        Args:
            image_path: 이미지 파일 경로
            
        Returns:
            bytes: 이미지 바이트 데이터
        """
        if not os.path.exists(image_path):
            return b''
        
        try:
            with open(image_path, 'rb') as f:
                return f.read()
        except Exception as e:
            print(f"[BackgroundService] 배경 이미지 데이터 저장 실패: {e}")
            return b''
    
    def load_background_from_data(self, image_data: bytes) -> QPixmap:
        """
        바이트 데이터에서 배경 이미지를 로드합니다.
        
        Args:
            image_data: 이미지 바이트 데이터
            
        Returns:
            QPixmap: 로드된 이미지
        """
        if not image_data:
            return QPixmap()
        
        pixmap = QPixmap()
        pixmap.loadFromData(image_data)
        
        if not pixmap.isNull():
            self.current_background_image = pixmap
            self.current_background_path = ""  # 데이터에서 로드된 경우 경로는 빈 문자열
            self.has_background = True
            print(f"[BackgroundService] 데이터에서 배경 이미지 로드 완료: {pixmap.width()}x{pixmap.height()}")
        
        return pixmap
    
    def get_current_background_path(self) -> str:
        """
        현재 배경 이미지의 파일 경로를 반환합니다.
        
        Returns:
            str: 배경 이미지 파일 경로
        """
        return self.current_background_path
    
    def get_background_data_for_save(self) -> bytes:
        """
        현재 배경 이미지를 저장용 바이트 데이터로 변환합니다.
        
        Returns:
            bytes: 저장용 바이트 데이터
        """
        if not self.current_background_image or self.current_background_image.isNull():
            return b''
        
        # QPixmap을 바이트 배열로 변환
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        
        # PNG 형식으로 저장
        success = self.current_background_image.save(buffer, "PNG")
        buffer.close()
        
        if success:
            return byte_array.data()
        else:
            print("[BackgroundService] 배경 이미지를 바이트 데이터로 변환하는데 실패했습니다.")
            return b'' 