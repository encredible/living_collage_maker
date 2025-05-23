import pytest
from PyQt6.QtGui import QPixmap, QImage, QColor
from src.ui.canvas import ImageAdjuster

@pytest.fixture(scope="session", autouse=True) # 원래대로 autouse=True
def initialize_image_adjuster(): 
    """ImageAdjuster를 세션 시작 시 한 번 초기화합니다."""
    if not ImageAdjuster._initialized:
        ImageAdjuster.initialize()
        # ImageAdjuster._use_numpy = False # 일단 NumPy 강제 비활성화 제거
        print("[Test Fixture] ImageAdjuster initialized (via conftest.py session autouse fixture).")

@pytest.fixture
def dummy_pixmap_small():
    """테스트용 작은 QPixmap 객체를 생성합니다 (10x10, 흰색)."""
    image = QImage(10, 10, QImage.Format.Format_RGB32)
    image.fill(QColor("white"))
    return QPixmap.fromImage(image)

@pytest.fixture
def dummy_pixmap_red_small():
    """테스트용 작은 QPixmap 객체를 생성합니다 (10x10, 빨간색)."""
    image = QImage(10, 10, QImage.Format.Format_RGB32)
    image.fill(QColor("red"))
    return QPixmap.fromImage(image) 