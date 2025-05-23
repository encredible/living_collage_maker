import weakref

import pytest
from PyQt6.QtCore import QBuffer, QIODevice
from PyQt6.QtGui import (QColor, QPixmap, QImage)

from src.ui.utils import ImageAdjuster


# ImageAdjuster 초기화 (테스트 시작 시 한 번만) -> tests/ui/conftest.py로 이동
# @pytest.fixture(scope="session", autouse=True)
# def initialize_image_adjuster():
#     ImageAdjuster.initialize()

@pytest.fixture
def dummy_pixmap_small():
    """테스트용 작은 QPixmap 객체를 생성합니다 (10x10)."""
    image = QImage(10, 10, QImage.Format.Format_RGB32)
    image.fill(QColor("white"))
    return QPixmap.fromImage(image)

def test_calculate_temperature_rgb_known_values(initialize_image_adjuster):
    """calculate_temperature_rgb가 특정 색온도에 대해 예상 RGB 계수를 반환하는지 테스트합니다."""
    # 6500K (기준)
    r, g, b = ImageAdjuster.calculate_temperature_rgb(6500)
    assert r == 1.0, "6500K에서 R 채널 값 오류"
    assert g == 1.0, "6500K에서 G 채널 값 오류"
    assert b == 1.0, "6500K에서 B 채널 값 오류"

    # 2000K (따뜻한 색)
    # temp_factor = (6500 - 2000) / 6500 = 45/65 = 9/13
    # r_factor = 1.0 + (9/13) * 0.2  (approx 1.138)
    # g_factor = 1.0
    # b_factor = 1.0 - (9/13) * 0.6  (approx 0.585)
    r, g, b = ImageAdjuster.calculate_temperature_rgb(2000)
    assert r > 1.1 and r < 1.2, "2000K에서 R 채널 값 범위 오류"
    assert g == 1.0, "2000K에서 G 채널 값 오류, 1.0이어야 함"
    assert b > 0.5 and b < 0.6, "2000K에서 B 채널 값 범위 오류"
    assert r > g > b, "2000K에서 RGB 채널 순서 오류 (R > G > B 예상)"

    # 10000K (차가운 색)
    # temp_factor = (10000 - 6500) / 6500 = 35/65 = 7/13
    # r_factor = 1.0 - (7/13) * 0.4 (approx 0.785)
    # g_factor = 1.0 - (7/13) * 0.2 (approx 0.893)
    # b_factor = 1.0 + (7/13) * 0.2 (approx 1.107)
    r, g, b = ImageAdjuster.calculate_temperature_rgb(10000)
    assert r > 0.7 and r < 0.8, "10000K에서 R 채널 값 범위 오류"
    assert g > 0.8 and g < 0.9, "10000K에서 G 채널 값 범위 오류"
    assert b > 1.1 and b < 1.2, "10000K에서 B 채널 값 범위 오류"
    assert b > g > r, "10000K에서 RGB 채널 순서 오류 (B > G > R 예상)"

def test_get_temperature_rgb_exact_lut_match(initialize_image_adjuster, monkeypatch):
    """룩업 테이블에 정확히 일치하는 온도가 입력되면 해당 LUT 값을 반환하는지 테스트합니다."""
    # ImageAdjuster가 초기화되어 _temperature_lut이 채워져 있다고 가정
    # 예시: 룩업 테이블에 3000K가 있고, 그 값이 (0.8, 0.9, 1.0)이라고 가정
    # 실제 _init_temperature_lut 로직을 통해 계산된 값을 사용하는 것이 더 정확함
    # 여기서는 테스트를 위해 직접 값을 설정 (실제 LUT 값과 다를 수 있음)
    mock_lut = {3000: (0.8, 0.9, 1.0), 6500: (1.0, 1.0, 1.0)}
    monkeypatch.setattr(ImageAdjuster, '_temperature_lut', mock_lut)
    
    assert ImageAdjuster.get_temperature_rgb(3000) == (0.8, 0.9, 1.0)
    assert ImageAdjuster.get_temperature_rgb(6500) == (1.0, 1.0, 1.0)

def test_get_temperature_rgb_closest_lut_match(initialize_image_adjuster, monkeypatch):
    """룩업 테이블에 없는 값 중 가까운 값이 입력되면 가장 가까운 LUT 값을 반환하는지 테스트합니다."""
    # 실제 _init_temperature_lut 로직을 통해 계산된 값을 사용하는 것이 더 정확함
    # 여기서는 테스트를 위해 직접 값을 설정
    # _init_temperature_lut은 500K 단위로 생성함
    # 2000, 2500, 3000 ...
    # calculate_temperature_rgb(2500) -> r=1.107, g=1.0, b=0.677
    # calculate_temperature_rgb(3000) -> r=1.077, g=1.0, b=0.754
    mock_lut = {
        2500: ImageAdjuster.calculate_temperature_rgb(2500),
        3000: ImageAdjuster.calculate_temperature_rgb(3000) 
    }
    monkeypatch.setattr(ImageAdjuster, '_temperature_lut', mock_lut)
    
    # 2700K는 2500K와 3000K 사이이며, 3000K에 더 가까움 (차이 300, 200)
    # 하지만 get_temperature_rgb는 min(key, key=lambda x: abs(x-temp)) 로 찾으므로 2500K (차이 200)
    # 그 후 if abs(closest_temp - temperature) <= 1000 조건 (200 <= 1000) 참
    assert ImageAdjuster.get_temperature_rgb(2700) == mock_lut[2500] # 2500K의 값을 반환해야 함
    assert ImageAdjuster.get_temperature_rgb(2400) == mock_lut[2500] # 2500K에 더 가까움
    assert ImageAdjuster.get_temperature_rgb(3100) == mock_lut[3000] # 3000K에 더 가까움

def test_get_temperature_rgb_direct_calculation(initialize_image_adjuster, monkeypatch):
    """룩업 테이블에 없는 먼 값이 입력되면 calculate_temperature_rgb를 직접 호출하는지 테스트합니다."""
    # 룩업 테이블이 비어있거나, 매우 다른 온도값인 경우
    mock_lut = {6500: (1.0, 1.0, 1.0)} # LUT에 값이 거의 없다고 가정
    monkeypatch.setattr(ImageAdjuster, '_temperature_lut', mock_lut)
    
    # calculate_temperature_rgb가 호출되었는지 확인하기 위해 모의(mock) 처리
    # pytest-mock 플러그인의 mocker fixture 사용 필요
    # 여기서는 직접 호출된 결과와 calculate_temperature_rgb의 결과가 같은지 비교
    test_temp = 1500 # LUT의 6500K와 매우 다름 (차이 5000K > 1000K)
    expected_direct_calc = ImageAdjuster.calculate_temperature_rgb(test_temp)
    
    assert ImageAdjuster.get_temperature_rgb(test_temp) == expected_direct_calc

def test_apply_effects_null_pixmap(initialize_image_adjuster):
    """apply_effects에 Null QPixmap이 입력되면 Null QPixmap을 반환하는지 테스트합니다."""
    # ImageAdjuster.initialize()는 fixture에 의해 이미 호출됨
    result = ImageAdjuster.apply_effects(QPixmap(), 6500, 100, 100)
    assert result.isNull()

def test_apply_effects_returns_copy(initialize_image_adjuster, dummy_pixmap_small):
    """apply_effects가 반환하는 QPixmap이 입력이나 캐시와 다른 복사본인지 테스트합니다."""
    pixmap = dummy_pixmap_small
    
    # 첫 번째 호출 (캐시에 저장됨)
    result1 = ImageAdjuster.apply_effects(pixmap, 6500, 100, 100)
    assert not result1.isNull()
    assert result1 is not pixmap # 입력과 다른 객체여야 함
    
    # 캐시된 결과를 가져올 때도 복사본이어야 함
    # apply_effects 내부에서 캐시에서 가져올 때도 .copy()를 함
    result2 = ImageAdjuster.apply_effects(pixmap, 6500, 100, 100)
    assert not result2.isNull()
    assert result2 is not pixmap
    assert result2 is not result1 # 이전 결과와도 다른 객체여야 함 (캐시된 원본과도 달라야 함)
    # 내부 캐시 객체와 다른지 확인하려면 ImageAdjuster._effect_cache에 접근해야 함
    # cache_key = (ImageAdjuster._image_id_map[pixmap], f"{pixmap.width()}x{pixmap.height()}", 6500, 100, 100)
    # assert result1 is not ImageAdjuster._effect_cache[cache_key] # 캐시된 객체 자체는 아님

def test_apply_effects_basic_changes_non_numpy(initialize_image_adjuster, monkeypatch, dummy_pixmap_small):
    """NumPy를 사용하지 않을 때, 효과 적용 시 이미지가 변경되는지 기본적으로 테스트합니다."""
    monkeypatch.setattr(ImageAdjuster, '_use_numpy', False)
    pixmap = dummy_pixmap_small.copy() # 원본 유지를 위해 복사본 사용
    original_image = pixmap.toImage()

    # 밝기를 매우 낮게 설정하여 이미지가 어두워지는지 (원본과 달라지는지) 확인
    # dummy_pixmap_small은 흰색(255,255,255)이므로, 밝기 0이면 검은색(0,0,0)이 되어야 함
    result_dark_pixmap = ImageAdjuster.apply_effects(pixmap, 6500, 0, 100) # 밝기 0
    assert not result_dark_pixmap.isNull()
    result_dark_image = result_dark_pixmap.toImage()
    assert result_dark_image.pixelColor(0,0).red() < 10 # 거의 검은색인지 확인 (완전 0이 아닐 수 있음)
    assert result_dark_image.pixelColor(0,0).green() < 10
    assert result_dark_image.pixelColor(0,0).blue() < 10
    
    # 채도를 0으로 설정하여 흑백(grayscale) 이미지가 되는지 확인
    # 흰색 이미지에 채도 0은 여전히 흰색이므로, 다른 색상 이미지로 테스트하거나
    # 또는 R,G,B 값이 동일해지는지만 확인
    # 여기서는 간단히 원본과 다른지, 그리고 R=G=B인지 확인
    colored_image = QImage(10, 10, QImage.Format.Format_RGB32)
    colored_image.fill(QColor("red")) # 빨간색 이미지
    colored_pixmap = QPixmap.fromImage(colored_image)

    result_bw_pixmap = ImageAdjuster.apply_effects(colored_pixmap, 6500, 100, 0) # 채도 0
    assert not result_bw_pixmap.isNull()
    result_bw_image = result_bw_pixmap.toImage()
    # 흑백이면 R, G, B 값이 거의 같아야 함
    c = result_bw_image.pixelColor(0,0)
    assert abs(c.red() - c.green()) < 5 and abs(c.green() - c.blue()) < 5, "흑백 변환 오류"

def test_apply_effects_cache_usage(initialize_image_adjuster, monkeypatch, dummy_pixmap_small, mocker):
    """apply_effects가 캐시를 올바르게 사용하는지 테스트합니다."""
    pixmap = dummy_pixmap_small
    monkeypatch.setattr(ImageAdjuster, '_effect_cache', {})
    monkeypatch.setattr(ImageAdjuster, '_image_id_map', weakref.WeakKeyDictionary())
    monkeypatch.setattr(ImageAdjuster, '_image_id_counter', 0)
    monkeypatch.setattr(ImageAdjuster, '_use_numpy', False)

    result1 = ImageAdjuster.apply_effects(pixmap, 6500, 100, 100)
    image_id1 = ImageAdjuster._image_id_map[pixmap]
    size_key1 = f"{pixmap.width()}x{pixmap.height()}"
    cache_key1 = (image_id1, size_key1, 6500, 100, 100)
    assert cache_key1 in ImageAdjuster._effect_cache
    
    buffer_cached = QBuffer()
    buffer_cached.open(QIODevice.OpenModeFlag.ReadWrite)
    ImageAdjuster._effect_cache[cache_key1].save(buffer_cached, "PNG")
    cached_image_bytes = bytes(buffer_cached.data()) # QByteArray -> bytes
    buffer_cached.close()

    buffer_result1 = QBuffer()
    buffer_result1.open(QIODevice.OpenModeFlag.ReadWrite)
    result1.save(buffer_result1, "PNG")
    result1_bytes = bytes(buffer_result1.data()) # QByteArray -> bytes
    buffer_result1.close()

    assert cached_image_bytes == result1_bytes
    assert ImageAdjuster._effect_cache[cache_key1] is not result1

    result2 = ImageAdjuster.apply_effects(pixmap, 6500, 100, 100)
    buffer_result2 = QBuffer()
    buffer_result2.open(QIODevice.OpenModeFlag.ReadWrite)
    result2.save(buffer_result2, "PNG")
    result2_bytes = bytes(buffer_result2.data()) # QByteArray -> bytes
    buffer_result2.close()

    assert result2_bytes == result1_bytes
    assert result2 is not result1

def test_apply_effects_cache_eviction(initialize_image_adjuster, monkeypatch, dummy_pixmap_small):
    """캐시 크기 초과 시 오래된 항목이 제거되는지 테스트합니다."""
    pixmap = dummy_pixmap_small
    # 캐시 크기를 작게 설정
    monkeypatch.setattr(ImageAdjuster, '_cache_size', 1)
    monkeypatch.setattr(ImageAdjuster, '_effect_cache', {})
    monkeypatch.setattr(ImageAdjuster, '_image_id_map', weakref.WeakKeyDictionary())
    monkeypatch.setattr(ImageAdjuster, '_image_id_counter', 0)

    # 1. 첫 번째 효과 적용 (캐시됨)
    ImageAdjuster.apply_effects(pixmap, 6500, 100, 100) # key1 (id, size, 6500, 100, 100)
    image_id = ImageAdjuster._image_id_map[pixmap]
    size_key = f"{pixmap.width()}x{pixmap.height()}"
    cache_key1 = (image_id, size_key, 6500, 100, 100)
    assert cache_key1 in ImageAdjuster._effect_cache
    assert len(ImageAdjuster._effect_cache) == 1

    # 2. 다른 효과 적용 (새로운 항목 캐시, 이전 항목 제거되어야 함)
    ImageAdjuster.apply_effects(pixmap, 6000, 90, 80) # key2 (id, size, 6000, 90, 80)
    cache_key2 = (image_id, size_key, 6000, 90, 80)
    assert len(ImageAdjuster._effect_cache) == 1 # 크기가 1이므로
    assert cache_key2 in ImageAdjuster._effect_cache # 새 항목이 있어야 함
    assert cache_key1 not in ImageAdjuster._effect_cache # 이전 항목은 제거되어야 함

def test_apply_effects_basic_changes_numpy(initialize_image_adjuster, monkeypatch, dummy_pixmap_small, mocker):
    """NumPy를 사용할 때, 효과 적용 시 이미지가 변경되는지 기본적으로 테스트합니다."""
    # NumPy가 사용 가능하다고 가정하고 _use_numpy를 True로 설정
    # 실제 ImageAdjuster.initialize()에서 NumPy를 찾지 못하면 _use_numpy는 False가 됨
    # 이 테스트는 initialize() 후에 _use_numpy를 강제로 True로 설정하여 NumPy 경로를 테스트함
    # 만약 NumPy가 없으면 ImageAdjuster.apply_effects_numpy 내부에서 예외 발생 후
    # _use_numpy가 False로 바뀌고 기본 로직을 타게 되므로, 이 테스트는 NumPy가 있다는 가정 하에 의미가 있음.
    monkeypatch.setattr(ImageAdjuster, '_use_numpy', True)
    
    # apply_effects_numpy 메소드가 호출되었는지 확인하기 위해 스파이 설정
    spy_apply_effects_numpy = mocker.spy(ImageAdjuster, 'apply_effects_numpy')

    pixmap = dummy_pixmap_small.copy() # 원본 유지를 위해 복사본 사용

    # 밝기를 매우 낮게 설정 (흰색 -> 검은색 근처)
    result_dark_pixmap = ImageAdjuster.apply_effects(pixmap, 6500, 0, 100) # 밝기 0
    assert not result_dark_pixmap.isNull()
    result_dark_image = result_dark_pixmap.toImage()
    assert result_dark_image.pixelColor(0,0).red() < 10 
    assert result_dark_image.pixelColor(0,0).green() < 10
    assert result_dark_image.pixelColor(0,0).blue() < 10
    spy_apply_effects_numpy.assert_called_once() # numpy 메소드가 호출되었는지 확인
    spy_apply_effects_numpy.reset_mock() # 다음 호출을 위해 스파이 초기화

    # 채도를 0으로 설정 (빨간색 -> 흑백)
    colored_image = QImage(10, 10, QImage.Format.Format_RGB32)
    colored_image.fill(QColor("red"))
    colored_pixmap = QPixmap.fromImage(colored_image)

    result_bw_pixmap = ImageAdjuster.apply_effects(colored_pixmap, 6500, 100, 0) # 채도 0
    assert not result_bw_pixmap.isNull()
    result_bw_image = result_bw_pixmap.toImage()
    c = result_bw_image.pixelColor(0,0)
    assert abs(c.red() - c.green()) < 10 and abs(c.green() - c.blue()) < 10 # 값 차이가 매우 작아야 함 (NumPy 구현에 따라 약간의 오차 허용)
    spy_apply_effects_numpy.assert_called_once()

# 더 많은 테스트 케이스를 ImageAdjuster에 추가할 수 있습니다.
# 예를 들어, apply_effects_numpy를 직접 더 상세히 테스트하거나,
# 다양한 크기의 이미지, 다양한 효과 조합 등을 테스트할 수 있습니다. 