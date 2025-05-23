import os
import shutil
import pytest
from PyQt6.QtGui import QPixmap, QImage, QColor
from PyQt6.QtCore import QSize
from src.services.image_service import ImageService

@pytest.fixture
def image_service(tmp_path):
    """ImageService 인스턴스를 생성하고, 임시 캐시 디렉토리를 사용합니다."""
    service = ImageService()
    # 테스트용 임시 캐시 디렉토리 설정
    test_cache_dir = tmp_path / ".test_image_cache"
    os.makedirs(test_cache_dir, exist_ok=True)
    service.cache_dir = str(test_cache_dir)  # ImageService의 cache_dir을 임시 경로로 설정
    yield service
    # tmp_path는 pytest가 자동으로 정리하므로 shutil.rmtree는 필요 없음

@pytest.fixture
def dummy_pixmap(qtbot):
    """테스트용 QPixmap 객체를 생성합니다."""
    image = QImage(100, 100, QImage.Format.Format_RGB32)
    image.fill(QColor("red"))
    return QPixmap.fromImage(image)

@pytest.fixture
def large_dummy_pixmap(qtbot):
    """테스트용 큰 QPixmap 객체를 생성합니다 (optimize_image 테스트용)."""
    image = QImage(2000, 2000, QImage.Format.Format_RGB32)
    image.fill(QColor("blue"))
    return QPixmap.fromImage(image)

def test_get_cached_image_path_with_png_extension(image_service):
    """입력 파일명에 .png 확장자가 이미 있는 경우 올바른 경로를 반환하는지 테스트합니다."""
    filename = "test_image.png"
    expected_path = os.path.join(image_service.cache_dir, "test_image.png")
    assert image_service.get_cached_image_path(filename) == expected_path

def test_get_cached_image_path_with_jpg_extension(image_service):
    """입력 파일명에 .jpg 확장자가 있는 경우 .png로 변경된 경로를 반환하는지 테스트합니다."""
    filename = "test_image.jpg"
    expected_path = os.path.join(image_service.cache_dir, "test_image.png")
    assert image_service.get_cached_image_path(filename) == expected_path

def test_get_cached_image_path_with_no_extension(image_service):
    """입력 파일명에 확장자가 없는 경우 .png가 추가된 경로를 반환하는지 테스트합니다."""
    filename = "test_image"
    expected_path = os.path.join(image_service.cache_dir, "test_image.png")
    assert image_service.get_cached_image_path(filename) == expected_path

def test_get_cached_image_path_with_uppercase_extension(image_service):
    """입력 파일명의 확장자가 대문자인 경우 소문자 .png로 변경된 경로를 반환하는지 테스트합니다."""
    filename = "test_image.PNG"
    expected_path = os.path.join(image_service.cache_dir, "test_image.png")
    assert image_service.get_cached_image_path(filename) == expected_path

def test_get_cached_image_path_with_mixed_case_extension(image_service):
    """입력 파일명의 확장자가 혼합된 대소문자인 경우 소문자 .png로 변경된 경로를 반환하는지 테스트합니다."""
    filename = "test_image.PnG"
    expected_path = os.path.join(image_service.cache_dir, "test_image.png")
    assert image_service.get_cached_image_path(filename) == expected_path

def test_is_image_cached_file_not_exists(image_service):
    """캐시에 해당 파일이 존재하지 않을 때 False를 반환하는지 테스트합니다."""
    assert not image_service.is_image_cached("non_existent_image.png")

def test_is_image_cached_file_exists(image_service):
    """캐시에 해당 파일이 존재할 때 True를 반환하는지 테스트합니다."""
    filename = "existing_image.png"
    cache_path = image_service.get_cached_image_path(filename)
    # 임시로 캐시 파일 생성
    with open(cache_path, "w") as f:
        f.write("dummy content")
    assert image_service.is_image_cached(filename)

def test_optimize_image_small_image(image_service, dummy_pixmap):
    """작은 이미지는 원본 크기 그대로 반환하는지 테스트합니다."""
    optimized = image_service.optimize_image(dummy_pixmap)
    assert optimized.size() == dummy_pixmap.size()

def test_optimize_image_large_image(image_service, large_dummy_pixmap):
    """큰 이미지는 최대 크기(1920) 이하로 조절되어 반환되는지 테스트합니다."""
    optimized = image_service.optimize_image(large_dummy_pixmap)
    assert optimized.width() <= 1920
    assert optimized.height() <= 1920
    assert optimized.width() == 1920 or optimized.height() == 1920 # 둘 중 하나는 1920이어야 함 (비율 유지)

def test_optimize_image_null_pixmap(image_service):
    """입력 QPixmap이 null일 때 null QPixmap을 반환하는지 테스트합니다."""
    null_pixmap = QPixmap()
    optimized = image_service.optimize_image(null_pixmap)
    assert optimized.isNull()

def test_create_thumbnail_valid_pixmap(image_service, dummy_pixmap):
    """정상 QPixmap으로 썸네일이 올바르게 생성되는지 테스트합니다."""
    thumbnail_size = QSize(50, 50)
    thumbnail = image_service.create_thumbnail(dummy_pixmap, thumbnail_size)
    assert not thumbnail.isNull()
    # 원본 비율(1:1)이 유지되었으므로 썸네일도 50x50 이어야 함
    assert thumbnail.size() == thumbnail_size 

def test_create_thumbnail_different_aspect_ratio(image_service):
    """원본 이미지와 다른 비율의 썸네일 크기가 주어졌을 때, 비율을 유지하며 생성되는지 테스트합니다."""
    rect_image = QImage(200, 100, QImage.Format.Format_RGB32) # 2:1 비율
    rect_image.fill(QColor("green"))
    pixmap = QPixmap.fromImage(rect_image)
    
    thumbnail_size = QSize(80, 80) # 요청 크기는 1:1
    thumbnail = image_service.create_thumbnail(pixmap, thumbnail_size)
    assert not thumbnail.isNull()
    # 원본 2:1 비율 유지, 요청된 80x80 내에 맞게 생성되므로 80x40이 되어야 함
    assert thumbnail.width() == 80 
    assert thumbnail.height() == 40

def test_create_thumbnail_null_pixmap(image_service):
    """입력 QPixmap이 null일 때 null QPixmap을 반환하는지 테스트합니다."""
    null_pixmap = QPixmap()
    thumbnail_size = QSize(50, 50)
    thumbnail = image_service.create_thumbnail(null_pixmap, thumbnail_size)
    assert thumbnail.isNull() 

def test_pixmap_to_bytes_valid_pixmap(image_service, dummy_pixmap):
    """정상 QPixmap이 PNG 바이트 데이터로 변환되는지 테스트합니다."""
    byte_data = image_service.pixmap_to_bytes(dummy_pixmap)
    assert isinstance(byte_data, bytes)
    assert len(byte_data) > 0
    # 간단하게 PNG 시그니처 시작 부분만 확인 (더 정확한 검증은 이미지 라이브러리 필요)
    assert byte_data.startswith(b'\x89PNG') 

def test_pixmap_to_bytes_null_pixmap(image_service):
    """Null QPixmap 입력 시 빈 바이트 문자열을 반환하는지 테스트합니다."""
    null_pixmap = QPixmap()
    byte_data = image_service.pixmap_to_bytes(null_pixmap)
    assert byte_data == b'' 

def test_download_and_cache_image_new_image(image_service, dummy_pixmap):
    """새로운 이미지 데이터로 이미지가 캐시되고 QPixmap이 반환되는지 테스트합니다."""
    image_filename = "new_image.png"
    image_data = image_service.pixmap_to_bytes(dummy_pixmap)
    assert len(image_data) > 0
    pixmap = image_service.download_and_cache_image(image_data, image_filename)
    assert not pixmap.isNull()
    assert pixmap.size() == dummy_pixmap.size()
    cache_path = image_service.get_cached_image_path(image_filename)
    assert os.path.exists(cache_path)
    pixmap_from_cache = image_service.download_and_cache_image(image_data, image_filename)
    assert not pixmap_from_cache.isNull()

def test_download_and_cache_image_cached_image_when_no_input_data(image_service, dummy_pixmap):
    """디스크에 이미지가 캐시되어 있어도, 입력 이미지 데이터가 없으면 빈 QPixmap을 반환하는지 테스트합니다."""
    image_filename = "cached_image_no_input.png"
    image_data_for_caching = image_service.pixmap_to_bytes(dummy_pixmap)
    
    # 먼저 캐시 생성
    image_service.download_and_cache_image(image_data_for_caching, image_filename)
    cache_path = image_service.get_cached_image_path(image_filename)
    assert os.path.exists(cache_path)
    original_mtime = os.path.getmtime(cache_path)

    # 메모리 캐시를 비우고
    image_service.memory_cache.clear()

    # image_data를 None으로 전달하여 다시 요청
    pixmap = image_service.download_and_cache_image(None, image_filename) 
    assert pixmap.isNull() # image_data가 없으므로 캐시를 읽지 않고 빈 QPixmap 반환
    assert os.path.getmtime(cache_path) == original_mtime # 파일은 수정되지 않아야 함

def test_download_and_cache_image_invalid_data(image_service):
    """잘못된 이미지 데이터로 빈 QPixmap이 반환되는지 테스트합니다."""
    image_filename = "invalid_image.png"
    invalid_image_data = b"this is not a valid image"
    pixmap = image_service.download_and_cache_image(invalid_image_data, image_filename)
    assert pixmap.isNull()
    # 캐시 파일이 생성되지 않아야 함 (또는 생성 시도 후 실패)
    cache_path = image_service.get_cached_image_path(image_filename)
    assert not os.path.exists(cache_path) 

def test_download_and_cache_image_no_data(image_service):
    """이미지 데이터가 없을 때 (None) 빈 QPixmap이 반환되는지 테스트합니다."""
    image_filename = "no_data_image.png"
    pixmap = image_service.download_and_cache_image(None, image_filename)
    assert pixmap.isNull() 

def test_clear_cache(image_service, dummy_pixmap):
    """clear_cache 호출 시 디스크 및 메모리 캐시가 삭제되는지 테스트합니다."""
    # 1. 디스크 캐시에 파일 생성
    filename1 = "cached_file1.png"
    cache_path1 = image_service.get_cached_image_path(filename1)
    with open(cache_path1, "w") as f:
        f.write("dummy1")
    assert os.path.exists(cache_path1)

    # 2. 메모리 캐시에 아이템 추가 (download_and_cache_image를 통해)
    filename2_original = "cached_file2.jpg" # 원본 파일명 (확장자 다르게)
    normalized_filename2 = os.path.basename(image_service.get_cached_image_path(filename2_original))
    image_data = image_service.pixmap_to_bytes(dummy_pixmap)
    
    # download_and_cache_image의 반환값(QPixmap)에 대한 강한 참조를 유지
    # 이렇게 하지 않으면 WeakValueDictionary에서 바로 사라질 수 있음
    pixmap_ref = image_service.download_and_cache_image(image_data, filename2_original)
    assert not pixmap_ref.isNull() # 반환된 QPixmap이 유효한지 확인
    
    with image_service.cache_lock:
        assert normalized_filename2 in image_service.memory_cache # 정규화된 이름으로 확인

    # 3. clear_cache 호출
    image_service.clear_cache()

    # 4. 디스크 캐시 확인
    assert not os.path.exists(cache_path1)
    cache_path2 = image_service.get_cached_image_path(filename2_original) # 원본 이름으로 경로 조회
    assert not os.path.exists(cache_path2) 

    # 5. 메모리 캐시 확인
    with image_service.cache_lock:
        assert len(image_service.memory_cache) == 0
    
    # pixmap_ref 참조 해제 (선택적, 테스트 함수 종료 시 자동으로 해제됨)
    del pixmap_ref 