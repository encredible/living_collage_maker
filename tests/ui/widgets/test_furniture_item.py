from unittest.mock import patch, ANY, MagicMock

import pytest
from PyQt6.QtCore import QBuffer, QIODevice, QPoint, Qt, QPointF, QEvent
from PyQt6.QtGui import QPixmap, QColor, QContextMenuEvent, QMouseEvent
from PyQt6.QtWidgets import QMenu, QWidget

from src.models.furniture import Furniture  # Furniture 모델 임포트
from src.services.image_service import ImageService  # ImageService 임포트 (모의 대상)
from src.services.supabase_client import SupabaseClient  # SupabaseClient 임포트 (모의 대상)
from src.ui.canvas import Canvas  # Canvas 클래스 임포트
from src.ui.widgets import FurnitureItem  # FurnitureItem 임포트


@pytest.fixture
def mock_furniture_data():
    """테스트용 기본 Furniture 객체 데이터를 반환합니다."""
    return {
        "id": "test-id-123",
        "name": "Test Sofa",
        "image_filename": "sofa.png",
        "price": 100000,
        "brand": "TestBrand",
        "type": "Sofa",
        "description": "A comfy test sofa.",
        "link": "http://example.com/sofa",
        "color": "Gray",
        "locations": ["Living Room"],
        "styles": ["Modern"],
        "width": 200, "depth": 100, "height": 80, "seat_height": 40,
        "author": "test_user",
        "created_at": "2023-01-01T00:00:00Z"
    }

@pytest.fixture
def furniture_obj(mock_furniture_data):
    """테스트용 Furniture 객체를 생성합니다."""
    return Furniture(**mock_furniture_data)

@pytest.fixture
def dummy_qpixmap():
    """테스트용 기본 QPixmap 객체를 생성합니다."""
    pixmap = QPixmap(100, 100)
    pixmap.fill(QColor("blue"))
    return pixmap

# QApplication 인스턴스는 tests/conftest.py 에서 자동으로 생성됩니다.

def test_furniture_item_creation(initialize_image_adjuster, furniture_obj, mocker, qtbot):
    """FurnitureItem 생성 시 load_image가 호출되는지 확인합니다."""
    mock_load_image = mocker.patch.object(FurnitureItem, 'load_image', return_value=None)
    # ImageService와 SupabaseClient의 생성자 모의 처리
    mocker.patch.object(ImageService, '__init__', autospec=True, return_value=None) # return_value=None 명시 또는 생략
    mocker.patch.object(SupabaseClient, '__init__', autospec=True, return_value=None) # return_value=None 명시 또는 생략

    item = FurnitureItem(furniture_obj) # 부모 없이 생성 가능, qtbot이 관리
    qtbot.addWidget(item) # qtbot에 위젯 등록

    assert item is not None
    assert item.furniture == furniture_obj
    mock_load_image.assert_called_once()

@patch('src.ui.widgets.furniture_item.SupabaseClient')
@patch('src.ui.widgets.furniture_item.ImageService')
def test_furniture_item_load_image_success(MockImageService, MockSupabaseClient, initialize_image_adjuster, furniture_obj, dummy_qpixmap, mocker, qtbot):
    """load_image 성공 시 pixmap 및 original_pixmap이 올바르게 설정되는지 테스트합니다."""
    mock_supabase_instance = MockSupabaseClient.return_value
    mock_image_service_instance = MockImageService.return_value
    mock_supabase_instance._image_cache = mocker.MagicMock() # 경고 해결

    mock_supabase_instance.get_furniture_image.return_value = b"fake_image_data"
    # download_and_cache_image가 dummy_qpixmap을 반환하도록 설정
    mock_image_service_instance.download_and_cache_image.return_value = dummy_qpixmap 
    
    item = FurnitureItem(furniture_obj)
    qtbot.addWidget(item) # qtbot에 위젯 등록

    mock_supabase_instance.get_furniture_image.assert_called_once_with(furniture_obj.image_filename)
    mock_image_service_instance.download_and_cache_image.assert_called_once_with(b"fake_image_data", furniture_obj.image_filename)
    
    # item.pixmap은 download_and_cache_image가 반환한 것의 복사본이어야 함
    assert item.pixmap is not dummy_qpixmap # 복사본이므로 다른 객체
    # 내용 비교 (QBuffer 사용)
    buffer_item_pixmap = QBuffer()
    buffer_item_pixmap.open(QIODevice.OpenModeFlag.ReadWrite)
    item.pixmap.save(buffer_item_pixmap, "PNG")
    item_pixmap_bytes = bytes(buffer_item_pixmap.data())
    buffer_item_pixmap.close()

    buffer_dummy_pixmap = QBuffer()
    buffer_dummy_pixmap.open(QIODevice.OpenModeFlag.ReadWrite)
    dummy_qpixmap.save(buffer_dummy_pixmap, "PNG")
    dummy_pixmap_bytes = bytes(buffer_dummy_pixmap.data())
    buffer_dummy_pixmap.close()

    assert item_pixmap_bytes == dummy_pixmap_bytes # 내용은 동일

    # item.original_pixmap도 dummy_qpixmap의 복사본이어야 함
    assert item.original_pixmap is not None
    assert item.original_pixmap is not dummy_qpixmap
    assert item.original_pixmap is not item.pixmap # pixmap과 original_pixmap도 서로 다른 복사본
    
    buffer_original_pixmap = QBuffer()
    buffer_original_pixmap.open(QIODevice.OpenModeFlag.ReadWrite)
    item.original_pixmap.save(buffer_original_pixmap, "PNG")
    original_pixmap_bytes = bytes(buffer_original_pixmap.data())
    buffer_original_pixmap.close()
    assert original_pixmap_bytes == dummy_pixmap_bytes # 내용 동일

    # 초기 크기 및 비율 테스트 (dummy_qpixmap 기준)
    # dummy_qpixmap의 크기는 100x100이므로 비율은 1.0
    assert dummy_qpixmap.width() == 100 and dummy_qpixmap.height() == 100
    expected_width = 200
    expected_height = int(expected_width / (dummy_qpixmap.width() / dummy_qpixmap.height()))
    assert item.width() == expected_width
    assert item.height() == expected_height

@patch('src.ui.widgets.furniture_item.SupabaseClient')
@patch('src.ui.widgets.furniture_item.ImageService')
def test_furniture_item_load_image_failure(MockImageService, MockSupabaseClient, initialize_image_adjuster, furniture_obj, mocker, qtbot):
    """load_image 실패 시 (null pixmap 반환) 기본 에러 이미지가 설정되는지 테스트합니다."""
    mock_supabase_instance = MockSupabaseClient.return_value
    mock_image_service_instance = MockImageService.return_value
    mock_supabase_instance._image_cache = mocker.MagicMock() # 경고 해결

    mock_supabase_instance.get_furniture_image.return_value = b"fake_image_data"
    # download_and_cache_image가 Null QPixmap을 반환하도록 모의 처리
    null_pixmap = QPixmap()
    mock_image_service_instance.download_and_cache_image.return_value = null_pixmap
    
    item = FurnitureItem(furniture_obj)
    qtbot.addWidget(item) # qtbot에 위젯 등록

    assert not item.pixmap.isNull()
    assert item.pixmap.width() == 200 # 기본 에러 이미지 크기
    assert item.pixmap.height() == 200
    # TODO: 에러 이미지가 실제로 그려졌는지 픽셀 검사 (선택 사항)
    assert item.original_pixmap is not None
    assert item.original_pixmap.size() == item.pixmap.size() # 실패 시 original_pixmap은 현재 pixmap(에러 이미지)과 동일한 크기

@patch('src.ui.utils.ImageAdjuster.apply_effects')
@patch('src.ui.widgets.furniture_item.SupabaseClient')
@patch('src.ui.widgets.furniture_item.ImageService')
def test_furniture_item_apply_image_effects(MockImageService, MockSupabaseClient, mock_apply_effects, initialize_image_adjuster, furniture_obj, dummy_qpixmap, dummy_pixmap_red_small, qtbot, mocker):
    """apply_image_effects 호출 시 ImageAdjuster.apply_effects가 호출되고 pixmap이 업데이트되는지 테스트합니다."""
    MockImageService.return_value.download_and_cache_image.return_value = dummy_qpixmap
    mock_supabase_instance = MockSupabaseClient.return_value # 이 라인 추가
    mock_supabase_instance._image_cache = mocker.MagicMock() # 경고 해결
    
    item = FurnitureItem(furniture_obj)
    qtbot.addWidget(item) # qtbot에 위젯 등록
    assert item.pixmap is not dummy_qpixmap

    mock_apply_effects.return_value = dummy_pixmap_red_small

    new_temp, new_brightness, new_saturation = 5000, 80, 120
    item.apply_image_effects(new_temp, new_brightness, new_saturation)

    mock_apply_effects.assert_called_once_with(
        ANY, # item.original_pixmap 대신 ANY 사용
        new_temp,
        new_brightness,
        new_saturation
    )
    
    # item.pixmap이 ImageAdjuster.apply_effects의 반환값(의 복사본)과 내용이 같은지 확인
    assert item.pixmap is not dummy_pixmap_red_small # 복사본이므로 다른 객체

    # 내용 비교 (QBuffer 사용)
    buffer_item_pixmap = QBuffer()
    buffer_item_pixmap.open(QIODevice.OpenModeFlag.ReadWrite)
    item.pixmap.save(buffer_item_pixmap, "PNG")
    item_pixmap_bytes = bytes(buffer_item_pixmap.data())
    buffer_item_pixmap.close()

    buffer_dummy_red_pixmap = QBuffer()
    buffer_dummy_red_pixmap.open(QIODevice.OpenModeFlag.ReadWrite)
    dummy_pixmap_red_small.save(buffer_dummy_red_pixmap, "PNG")
    dummy_red_pixmap_bytes = bytes(buffer_dummy_red_pixmap.data())
    buffer_dummy_red_pixmap.close()

    assert item_pixmap_bytes == dummy_red_pixmap_bytes # 내용은 동일

    assert item.color_temp == new_temp
    assert item.brightness == new_brightness
    assert item.saturation == new_saturation

@patch('src.ui.widgets.furniture_item.SupabaseClient')
@patch('src.ui.widgets.furniture_item.ImageService')
def test_furniture_item_reset_image_adjustments(MockImageService, MockSupabaseClient, initialize_image_adjuster, furniture_obj, dummy_qpixmap, qtbot, mocker):
    """reset_image_adjustments 호출 시 pixmap이 original_pixmap으로 복원되고 조정값이 초기화되는지 테스트합니다."""
    MockImageService.return_value.download_and_cache_image.return_value = dummy_qpixmap
    mock_supabase_instance = MockSupabaseClient.return_value # 이 라인 추가
    mock_supabase_instance._image_cache = mocker.MagicMock() # 경고 해결

    item = FurnitureItem(furniture_obj)
    qtbot.addWidget(item) # qtbot에 위젯 등록

    # 임의로 효과 값 변경 (실제 효과 적용은 모의하지 않음, 값만 변경)
    item.color_temp = 5000
    item.brightness = 80
    item.saturation = 120
    # pixmap도 임의로 변경 (original_pixmap과 다르게)
    changed_pixmap = QPixmap(50, 50)
    changed_pixmap.fill(QColor("green"))
    item.pixmap = changed_pixmap
    assert item.pixmap is not item.original_pixmap

    # 리셋 메소드 호출
    item.reset_image_adjustments()

    # pixmap이 original_pixmap의 복사본으로 설정되었는지 확인
    assert item.pixmap is not item.original_pixmap # 복사본이므로 다른 객체
    
    # 내용 비교 (QBuffer 사용)
    buffer_item_pixmap = QBuffer()
    buffer_item_pixmap.open(QIODevice.OpenModeFlag.ReadWrite)
    item.pixmap.save(buffer_item_pixmap, "PNG")
    item_pixmap_bytes = bytes(buffer_item_pixmap.data())
    buffer_item_pixmap.close()

    buffer_original_pixmap = QBuffer()
    buffer_original_pixmap.open(QIODevice.OpenModeFlag.ReadWrite)
    item.original_pixmap.save(buffer_original_pixmap, "PNG")
    original_pixmap_bytes = bytes(buffer_original_pixmap.data())
    buffer_original_pixmap.close()

    assert item_pixmap_bytes == original_pixmap_bytes # 내용은 동일
    
    # 조정값이 기본값으로 초기화되었는지 확인
    # self.temp_slider.setValue(6500) 등 UI 조작 관련 코드는 테스트에서 직접 검증하지 않음
    # (원본 코드 변경 불가 원칙)
    assert item.color_temp == 6500
    assert item.brightness == 100
    assert item.saturation == 100 

# --- pytest-qt를 사용한 UI 상호작용 테스트 --- #

@patch('src.ui.widgets.furniture_item.SupabaseClient')
@patch('src.ui.widgets.furniture_item.ImageService')
def test_furniture_item_selection_via_canvas(MockImageService, MockSupabaseClient, initialize_image_adjuster, furniture_obj, dummy_qpixmap, qtbot, mocker):
    """Canvas를 통해 FurnitureItem 클릭 시 선택 상태가 올바르게 변경되는지 테스트합니다."""
    mock_load_image = mocker.patch.object(FurnitureItem, 'load_image')
    MockImageService.return_value.download_and_cache_image.return_value = dummy_qpixmap
    MockSupabaseClient.return_value.get_furniture_image.return_value = b"fake_image_data"
    mock_supabase_instance = MockSupabaseClient.return_value # 이 라인 추가
    mock_supabase_instance._image_cache = mocker.MagicMock() # 경고 해결

    canvas_widget = Canvas()

    # item1: furniture_obj를 그대로 사용
    item1 = FurnitureItem(furniture_obj, parent=canvas_widget.canvas_area)
    item1.pixmap = dummy_qpixmap.copy()
    item1.original_pixmap = dummy_qpixmap.copy()
    item1.setFixedSize(dummy_qpixmap.size())
    item1.move(10, 10)
    item1.show()
    canvas_widget.furniture_items.append(item1)

    # item2: furniture_obj의 데이터를 기반으로 새 Furniture 객체 생성 (ID 변경)
    item2_data = furniture_obj.__dict__.copy() # 기본 dict 복사
    item2_data['id'] = "item2-id"
    item2_data['name'] = "Test Sofa 2"
    item2_furniture = Furniture(**item2_data)
    item2 = FurnitureItem(item2_furniture, parent=canvas_widget.canvas_area)
    item2.pixmap = dummy_qpixmap.copy()
    item2.original_pixmap = dummy_qpixmap.copy()
    item2.setFixedSize(dummy_qpixmap.size())
    item2.move(50, 50)
    item2.show()
    canvas_widget.furniture_items.append(item2)

    assert mock_load_image.call_count == 2

    qtbot.mouseClick(item1, Qt.MouseButton.LeftButton)
    assert item1.is_selected is True
    assert canvas_widget.selected_item is item1
    assert item2.is_selected is False

    qtbot.mouseClick(item2, Qt.MouseButton.LeftButton)
    assert item2.is_selected is True
    assert canvas_widget.selected_item is item2
    assert item1.is_selected is False

    qtbot.mouseClick(canvas_widget.canvas_area, Qt.MouseButton.LeftButton, pos=QPoint(200,200))
    assert item1.is_selected is False
    assert item2.is_selected is False
    assert canvas_widget.selected_item is None

@patch('src.ui.widgets.furniture_item.SupabaseClient')
@patch('src.ui.widgets.furniture_item.ImageService')
def test_furniture_item_drag_move(MockImageService, MockSupabaseClient, initialize_image_adjuster, furniture_obj, dummy_qpixmap, qtbot, mocker):
    """FurnitureItem을 마우스로 드래그하여 이동시키는지 테스트합니다."""
    mock_load_image = mocker.patch.object(FurnitureItem, 'load_image')
    MockImageService.return_value.download_and_cache_image.return_value = dummy_qpixmap
    MockSupabaseClient.return_value.get_furniture_image.return_value = b"fake_image_data"
    mock_supabase_instance = MockSupabaseClient.return_value # 이 라인 추가
    mock_supabase_instance._image_cache = mocker.MagicMock() # 경고 해결

    canvas_widget = Canvas()
    item = FurnitureItem(furniture_obj, parent=canvas_widget.canvas_area)
    item.pixmap = dummy_qpixmap.copy()
    item.original_pixmap = dummy_qpixmap.copy()
    item.setFixedSize(dummy_qpixmap.size())
    item.move(100, 100)
    item.show()
    canvas_widget.furniture_items.append(item)
    # qtbot.addWidget(item) # 명시적 addWidget은 필수는 아님

    mock_load_image.assert_called_once() # 이 아이템에 대해 load_image 호출 확인

    original_pos = item.pos()
    
    start_drag_pos = QPoint(5, 5)
    qtbot.mousePress(item, Qt.MouseButton.LeftButton, pos=start_drag_pos)
    
    end_drag_pos_local = QPoint(25, 35)
    qtbot.mouseMove(item, pos=end_drag_pos_local)
    
    qtbot.mouseRelease(item, Qt.MouseButton.LeftButton)

    expected_pos = original_pos + (end_drag_pos_local - start_drag_pos)
    assert item.pos() == expected_pos 

@patch('src.ui.widgets.furniture_item.SupabaseClient')
@patch('src.ui.widgets.furniture_item.ImageService')
def test_furniture_item_resize_drag_handle(MockImageService, MockSupabaseClient, initialize_image_adjuster, furniture_obj, dummy_qpixmap, qtbot, mocker):
    """리사이즈 핸들 드래그 시 FurnitureItem의 크기가 변경되는지 테스트합니다."""
    mock_load_image = mocker.patch.object(FurnitureItem, 'load_image')
    MockImageService.return_value.download_and_cache_image.return_value = dummy_qpixmap
    MockSupabaseClient.return_value.get_furniture_image.return_value = b"fake_image_data"
    mock_supabase_instance = MockSupabaseClient.return_value # 이 라인 추가
    mock_supabase_instance._image_cache = mocker.MagicMock() # 경고 해결

    canvas_widget = Canvas()
    item = FurnitureItem(furniture_obj, parent=canvas_widget.canvas_area)
    item.pixmap = dummy_qpixmap.copy() # 100x100
    item.original_pixmap = dummy_qpixmap.copy()
    item.original_ratio = 1.0 # 테스트를 위해 강제 설정 (dummy_qpixmap은 100x100)
    item.setFixedSize(dummy_qpixmap.size())
    item.move(50, 50)
    # item.setSelected(True) 대신 Canvas의 선택 메소드 사용
    canvas_widget.select_furniture_item(item) 
    item.show()
    canvas_widget.furniture_items.append(item)
    qtbot.addWidget(canvas_widget) # 캔버스 위젯도 qtbot에 등록

    initial_size = item.size()
    assert initial_size.width() == 100 and initial_size.height() == 100

    # 오른쪽 아래 리사이즈 핸들 위치 (대략적인 계산, 실제 핸들 위치에 따라 조정 필요)
    # FurnitureItem.paintEvent 로직에서 핸들 위치를 정확히 알아야 함.
    # 여기서는 아이템의 오른쪽 아래 모서리를 드래그한다고 가정
    # 오른쪽 아래 핸들은 self.resize_handles[7] (인덱스 7) -> QRect(w - s, h - s, s, s)
    # 핸들 크기 self.handle_size = 6
    handle_size = 6 
    # 핸들의 좌상단 점 클릭
    handle_pos_in_item = QPoint(initial_size.width() - handle_size, initial_size.height() - handle_size)

    # 드래그하여 크기를 50, 30 만큼 늘림
    drag_x_by = 50
    drag_y_by = 30

    item.update_resize_handle() # 핸들 위치 명시적 업데이트
    # 드래그 시작 (리사이즈 핸들 위치에서 마우스 버튼 누름)
    qtbot.mousePress(item, Qt.MouseButton.LeftButton, pos=handle_pos_in_item)

    # 드래그 이동 (마우스 이동)
    # item 좌표계 기준이므로, 핸들 초기 위치 + 드래그 양
    # 실제로는 global 좌표로 변환 후 item.mouseMoveEvent로 전달됨
    # qtbot.mouseMove는 target widget의 좌표계를 사용함
    move_to_pos_in_item = handle_pos_in_item + QPoint(drag_x_by, drag_y_by)
    qtbot.mouseMove(item, pos=move_to_pos_in_item, delay=-1)

    # 드래그 종료 (마우스 버튼 뗌)
    qtbot.mouseRelease(item, Qt.MouseButton.LeftButton, pos=move_to_pos_in_item, delay=-1)

    # 최종 크기 확인
    expected_width = initial_size.width() + drag_x_by
    expected_height = initial_size.height() + drag_y_by
    assert item.width() == expected_width
    assert item.height() == expected_height

@patch('src.ui.widgets.furniture_item.SupabaseClient')
@patch('src.ui.widgets.furniture_item.ImageService')
def test_furniture_item_resize_aspect_ratio_locked(MockImageService, MockSupabaseClient, initialize_image_adjuster, furniture_obj, dummy_qpixmap, qtbot, mocker):
    """Shift 누르고 리사이즈 핸들 드래그 시 종횡비가 유지되는지 테스트합니다."""
    mock_load_image = mocker.patch.object(FurnitureItem, 'load_image')
    MockImageService.return_value.download_and_cache_image.return_value = dummy_qpixmap # 100x100, 비율 1.0
    MockSupabaseClient.return_value.get_furniture_image.return_value = b"fake_image_data"
    mock_supabase_instance = MockSupabaseClient.return_value # 이 라인 추가
    mock_supabase_instance._image_cache = mocker.MagicMock() # 경고 해결

    canvas_widget = Canvas()
    item = FurnitureItem(furniture_obj, parent=canvas_widget.canvas_area)
    item.pixmap = dummy_qpixmap.copy()
    item.original_pixmap = dummy_qpixmap.copy()
    item.original_ratio = 1.0 # 테스트를 위해 강제 설정 (dummy_qpixmap은 100x100)
    item.setFixedSize(dummy_qpixmap.size())
    item.move(50, 50)
    # item.setSelected(True) 대신 Canvas의 선택 메소드 사용
    canvas_widget.select_furniture_item(item) 
    item.show()
    canvas_widget.furniture_items.append(item)
    qtbot.addWidget(canvas_widget)

    initial_size = item.size()
    initial_aspect_ratio = initial_size.width() / initial_size.height()
    assert initial_aspect_ratio == 1.0 # dummy_qpixmap은 100x100

    # 오른쪽 아래 리사이즈 핸들 위치
    item.update_resize_handle() # 핸들 위치 명시적 업데이트
    resize_handle_rect = item.resize_handle 
    # 핸들의 중심점을 클릭하도록 수정
    handle_click_pos = resize_handle_rect.center()

    drag_x_by = 50 # 너비를 50 늘리려고 시도
    drag_y_by = 30 # 높이를 30 늘리려고 시도 (Shift로 인해 무시될 수 있음)
    
    # mousePress에는 Modifier 전달 안 함. keyPress/Release로 제어
    qtbot.mousePress(item, Qt.MouseButton.LeftButton, pos=handle_click_pos)
    # Shift 키가 눌린 것처럼 maintain_aspect_ratio_on_press를 직접 설정
    item.maintain_aspect_ratio_on_press = True 

    # 드래그 이동 (마우스 이동)
    move_to_pos_in_item = handle_click_pos + QPoint(drag_x_by, drag_y_by)
    qtbot.mouseMove(item, pos=move_to_pos_in_item, delay=-1)
    
    # mouseRelease 이후에 Shift 키 놓기
    qtbot.mouseRelease(item, Qt.MouseButton.LeftButton, pos=move_to_pos_in_item, delay=-1)
    item.maintain_aspect_ratio_on_press = False # 원래대로 복원

    final_size = item.size()
    final_aspect_ratio = final_size.width() / final_size.height()

    # 너비가 150으로 변경되었으면, 종횡비 1.0 유지 시 높이도 150이어야 함.
    # 또는 높이가 (100+30)=130으로 변경되려고 했으면, 너비도 130이어야 함.
    # FurnitureItem의 리사이즈 로직이 너비/높이 중 어느 쪽의 변화를 우선하는지, 
    # 또는 마우스 이동 벡터에 따라 어떻게 결정하는지에 따라 달라짐.
    # 일반적으로는 더 크게 변한 쪽이나, x축 변화를 우선할 수 있음.
    # 여기서는 너비가 50 늘어나는 것을 기준으로 종횡비 유지 확인
    assert final_size.width() == initial_size.width() + drag_x_by
    assert abs(final_size.height() - (initial_size.height() * (final_size.width() / initial_size.width()))) < 1e-5 # 부동소수점 비교
    assert abs(final_aspect_ratio - initial_aspect_ratio) < 1e-5

@patch('src.ui.widgets.furniture_item.SupabaseClient')
@patch('src.ui.widgets.furniture_item.ImageService')
# @patch('src.ui.widgets.QMenu') # QMenu 모의 처리는 FurnitureItem 내부 처리 방식 변경으로 불필요
def test_furniture_item_context_menu_actions(MockImageService, MockSupabaseClient, initialize_image_adjuster, furniture_obj, dummy_qpixmap, qtbot, mocker):
    """FurnitureItem 컨텍스트 메뉴 액션 (삭제) 테스트합니다."""
    mock_load_image = mocker.patch.object(FurnitureItem, 'load_image')
    MockImageService.return_value.download_and_cache_image.return_value = dummy_qpixmap
    MockSupabaseClient.return_value.get_furniture_image.return_value = b"fake_image_data"
    mock_supabase_instance = MockSupabaseClient.return_value # 이 라인 추가
    mock_supabase_instance._image_cache = mocker.MagicMock() # 경고 해결

    canvas_widget = Canvas() # Canvas 인스턴스화
    # FurnitureItem 생성 시 parent 인자로 canvas_widget.canvas_area 전달
    item = FurnitureItem(furniture_obj, parent=canvas_widget.canvas_area) 
    item.pixmap = dummy_qpixmap.copy()
    item.original_pixmap = dummy_qpixmap.copy()
    item.setFixedSize(dummy_qpixmap.size())
    item.move(10, 10)
    item.show()
    canvas_widget.furniture_items.append(item)
    canvas_widget.select_furniture_item(item) # 아이템을 선택된 상태로 만듦 (Canvas 메소드 사용)
    qtbot.addWidget(canvas_widget) # Canvas 위젯을 qtbot에 추가

    # 1. 삭제 테스트
    # FurnitureItem의 deleteLater를 spy
    spy_delete_later = mocker.spy(item, 'deleteLater')
    
    # 컨텍스트 메뉴 요청 (마우스 오른쪽 버튼 클릭)
    # QMenu.exec()는 선택된 QAction을 반환. 이를 모의하여 delete_action이 선택된 것처럼 만듦.
    # FurnitureItem.contextMenuEvent 내부에서 QMenu를 생성하므로, QMenu를 mock할 필요는 없음.
    # 대신, menu.exec()의 반환 값을 제어할 수 있다면 좋겠지만, 여기서는 실제 클릭을 시뮬레이션.
    # FurnitureItem의 contextMenuEvent 내부에서 menu.exec()의 반환값을 기준으로 분기하므로,
    # QMenu.exec()를 패치하여 특정 QAction을 반환하도록 해야 함.

    # contextMenuEvent가 호출될 때 QMenu().exec()가 delete_action을 반환하도록 설정
    # 이를 위해 QMenu를 mock하고, addAction도 mock하여 delete_action을 특정 mock 객체로 만듦
    mock_menu = mocker.MagicMock(spec=QMenu)
    mock_delete_action = mocker.MagicMock(text="삭제") # 실제 action의 text와 동일하게
    mock_flip_action = mocker.MagicMock(text="좌우 반전")
    mock_adjust_action = mocker.MagicMock(text="이미지 조정")

    def side_effect_add_action(text):
        if text == "삭제":
            return mock_delete_action
        elif text == "좌우 반전":
            return mock_flip_action
        elif text == "이미지 조정":
            return mock_adjust_action
        return mocker.MagicMock() # 기타 액션

    mock_menu.addAction.side_effect = side_effect_add_action
    mock_menu.exec.return_value = mock_delete_action # exec_ 대신 exec 사용 (PyQt6)

    # qtbot.mouseClick으로 contextMenuEvent를 간접적으로 호출하는 대신,
    # QMenu patching이 적용된 상태에서 contextMenuEvent를 직접 호출하고 event 객체를 전달합니다.
    # 이렇게 하면 QMenu().exec()가 mock_delete_action을 반환하는 것을 더 확실하게 제어할 수 있습니다.
    mock_event = mocker.MagicMock(spec=QContextMenuEvent) # QContextMenuEvent 사용
    mock_event.globalPos.return_value = QPoint(10, 10) # 임의의 전역 위치

    with patch('src.ui.widgets.furniture_item.QMenu', return_value=mock_menu) as mock_qmenu_class:
        item.contextMenuEvent(mock_event) # 직접 호출

    # deleteLater 호출 확인
    spy_delete_later.assert_called_once()
    # Canvas의 리스트에서 제거되었는지 확인
    assert item not in canvas_widget.furniture_items

    # "맨 앞으로 보내기", "맨 뒤로 보내기"는 FurnitureItem의 컨텍스트 메뉴에 없으므로 관련 테스트 삭제
    # # 테스트를 위해 아이템 다시 추가 및 선택 (다른 액션 테스트용)
    # canvas_widget.furniture_items.append(item)
    # canvas_widget.select_furniture_item(item) # current_selected_item을 직접 할당하는 대신 이 메소드 사용 권장
    # 
    # # 맨 앞으로 가져오기 테스트
    # # 사용자가 '맨 앞으로 보내기'를 선택했다고 가정
    # if canvas_widget.current_selected_item: # current_selected_item이 있는지 확인
    #     # Canvas에 해당 기능이 실제로 있는지 확인 필요 (현재는 없음)
    #     # spy_bring_to_front.assert_called_once() 
    #     pass # Canvas에 bring_selected_item_to_front 메소드가 없으므로 테스트 불가
    # spy_bring_to_front.reset_mock()
    # 
    # # 맨 뒤로 보내기 테스트
    # # 사용자가 '맨 뒤로 보내기'를 선택했다고 가정
    # if canvas_widget.current_selected_item:
    #     # Canvas에 해당 기능이 실제로 있는지 확인 필요 (현재는 없음)
    #     # spy_send_to_back.assert_called_once()
    #     pass # Canvas에 send_selected_item_to_back 메소드가 없으므로 테스트 불가
    # spy_send_to_back.reset_mock() 

@patch('src.ui.widgets.furniture_item.SupabaseClient')
@patch('src.ui.widgets.furniture_item.ImageService')
def test_furniture_item_context_menu_flip_action(MockImageService, MockSupabaseClient, initialize_image_adjuster, furniture_obj, dummy_qpixmap, qtbot, mocker):
    """FurnitureItem 컨텍스트 메뉴 '좌우 반전' 액션 테스트합니다."""
    mock_load_image = mocker.patch.object(FurnitureItem, 'load_image')
    MockImageService.return_value.download_and_cache_image.return_value = dummy_qpixmap
    MockSupabaseClient.return_value.get_furniture_image.return_value = b"fake_image_data"
    mock_supabase_instance = MockSupabaseClient.return_value # 이 라인 추가
    mock_supabase_instance._image_cache = mocker.MagicMock() # 경고 해결

    canvas_widget = Canvas()
    item = FurnitureItem(furniture_obj, parent=canvas_widget.canvas_area)
    item.pixmap = dummy_qpixmap.copy() # 원본 QPixmap (변환 전)
    item.original_pixmap = dummy_qpixmap.copy()
    item.setFixedSize(dummy_qpixmap.size())
    item.move(10, 10)
    item.show()
    canvas_widget.furniture_items.append(item)
    canvas_widget.select_furniture_item(item)
    qtbot.addWidget(canvas_widget)

    assert item.is_flipped is False # 초기 상태는 반전되지 않음

    # QPixmap.transformed와 update 메소드를 spy
    # spy_transformed = mocker.spy(item.pixmap, 'transformed') # 이 방식 대신 QPixmap.transformed를 patch
    spy_update = mocker.spy(item, 'update')

    # 컨텍스트 메뉴 설정 (flip_action이 선택되도록)
    mock_menu = mocker.MagicMock(spec=QMenu)
    mock_delete_action = mocker.MagicMock(text="삭제")
    mock_flip_action = mocker.MagicMock(text="좌우 반전") # 실제 action의 text와 동일하게
    mock_adjust_action = mocker.MagicMock(text="이미지 조정")

    def side_effect_add_action(text):
        if text == "삭제":
            return mock_delete_action
        elif text == "좌우 반전":
            return mock_flip_action
        elif text == "이미지 조정":
            return mock_adjust_action
        return mocker.MagicMock()

    mock_menu.addAction.side_effect = side_effect_add_action
    mock_menu.exec.return_value = mock_flip_action # '좌우 반전' 액션이 선택된 것처럼 설정

    mock_event = mocker.MagicMock(spec=QContextMenuEvent)
    mock_event.globalPos.return_value = QPoint(10, 10)

    with patch('src.ui.widgets.furniture_item.QMenu', return_value=mock_menu), \
         patch('PyQt6.QtGui.QPixmap.transformed') as mock_transformed:
        # transformed가 새 QPixmap 객체를 반환하도록 설정
        mock_transformed.return_value = dummy_qpixmap.copy() # 내용을 유지하면서 새 객체 반환
        item.contextMenuEvent(mock_event)

    # pixmap.transformed가 호출되었는지 확인
    mock_transformed.assert_called_once()
    # is_flipped 상태가 True로 변경되었는지 확인
    assert item.is_flipped is True
    # update가 호출되어 위젯이 다시 그려졌는지 확인
    spy_update.assert_called_once()

    # 한 번 더 호출하여 원래대로 돌아오는지 확인
    mock_menu.exec.return_value = mock_flip_action # 다시 flip_action 선택
    mock_transformed.reset_mock()
    spy_update.reset_mock()

    with patch('src.ui.widgets.furniture_item.QMenu', return_value=mock_menu), \
         patch('PyQt6.QtGui.QPixmap.transformed') as mock_transformed_again:
        mock_transformed_again.return_value = dummy_qpixmap.copy()
        item.contextMenuEvent(mock_event)

    mock_transformed_again.assert_called_once()
    assert item.is_flipped is False # 다시 False로
    spy_update.assert_called_once()

@patch('src.ui.widgets.furniture_item.SupabaseClient')
@patch('src.ui.widgets.furniture_item.ImageService')
def test_furniture_item_context_menu_adjust_action(MockImageService, MockSupabaseClient, initialize_image_adjuster, furniture_obj, dummy_qpixmap, qtbot, mocker):
    """FurnitureItem 컨텍스트 메뉴 '이미지 조정' 액션 테스트합니다."""
    mock_load_image = mocker.patch.object(FurnitureItem, 'load_image')
    MockImageService.return_value.download_and_cache_image.return_value = dummy_qpixmap
    MockSupabaseClient.return_value.get_furniture_image.return_value = b"fake_image_data"
    mock_supabase_instance = MockSupabaseClient.return_value # 이 라인 추가
    mock_supabase_instance._image_cache = mocker.MagicMock() # 경고 해결

    canvas_widget = Canvas()
    item = FurnitureItem(furniture_obj, parent=canvas_widget.canvas_area)
    item.pixmap = dummy_qpixmap.copy()
    item.original_pixmap = dummy_qpixmap.copy() # original_pixmap 설정
    item.setFixedSize(dummy_qpixmap.size())
    item.move(10, 10)
    item.show()
    canvas_widget.furniture_items.append(item)
    canvas_widget.select_furniture_item(item)
    qtbot.addWidget(canvas_widget)

    # FurnitureItem.show_adjustment_dialog 메소드를 spy 대신 patch로 변경
    mock_show_dialog = mocker.patch.object(item, 'show_adjustment_dialog', return_value=None)

    # 컨텍스트 메뉴 설정 (adjust_action이 선택되도록)
    mock_menu = mocker.MagicMock(spec=QMenu)
    mock_delete_action = mocker.MagicMock(text="삭제")
    mock_flip_action = mocker.MagicMock(text="좌우 반전")
    mock_adjust_action = mocker.MagicMock(text="이미지 조정") # 실제 action의 text와 동일하게

    def side_effect_add_action(text):
        if text == "삭제":
            return mock_delete_action
        elif text == "좌우 반전":
            return mock_flip_action
        elif text == "이미지 조정":
            return mock_adjust_action
        return mocker.MagicMock()

    mock_menu.addAction.side_effect = side_effect_add_action
    mock_menu.exec.return_value = mock_adjust_action # '이미지 조정' 액션이 선택된 것처럼 설정

    mock_event = mocker.MagicMock(spec=QContextMenuEvent)
    mock_event.globalPos.return_value = QPoint(10, 10)

    with patch('src.ui.widgets.furniture_item.QMenu', return_value=mock_menu):
        item.contextMenuEvent(mock_event)

    # show_adjustment_dialog가 호출되었는지 확인
    mock_show_dialog.assert_called_once() 

def test_furniture_item_multiple_selection_movement(qtbot, mocker):
    """다중 선택된 아이템들이 함께 이동하는지 테스트합니다."""
    # Mock 설정
    mock_furniture1 = MagicMock(spec=Furniture)
    mock_furniture1.id = "multi_move1"
    mock_furniture1.image_filename = "multi1.png"
    
    mock_furniture2 = MagicMock(spec=Furniture)
    mock_furniture2.id = "multi_move2"
    mock_furniture2.image_filename = "multi2.png"
    
    # 부모 위젯
    parent_widget = QWidget()
    qtbot.addWidget(parent_widget)
    
    # 이미지 로딩 모킹
    dummy_pixmap = QPixmap(100, 100)
    dummy_pixmap.fill(Qt.GlobalColor.blue)
    mock_load_image = mocker.patch.object(FurnitureItem, 'load_image', return_value=dummy_pixmap)
    
    # FurnitureItem 생성
    item1 = FurnitureItem(mock_furniture1, parent_widget)
    item1.move(100, 100)
    item1.show()
    
    item2 = FurnitureItem(mock_furniture2, parent_widget)
    item2.move(200, 200)
    item2.show()
    
    # Canvas 모킹 - parent() 체인을 모킹
    mock_canvas_area = MagicMock()
    mock_canvas = MagicMock()
    mock_canvas.selected_items = [item1, item2]
    mock_canvas_area.parent.return_value = mock_canvas
    
    # parent() 메서드 오버라이드
    item1.parent = lambda: mock_canvas_area
    item2.parent = lambda: mock_canvas_area
    
    # 드래그 시작
    start_pos = QPoint(50, 50)
    item1.old_pos = start_pos
    
    # move 메서드 추적
    item1_moves = []
    item2_moves = []
    
    original_move1 = item1.move
    original_move2 = item2.move
    
    def track_item1_move(pos):
        item1_moves.append(pos)
        return original_move1(pos)
    
    def track_item2_move(pos):
        item2_moves.append(pos)
        return original_move2(pos)
    
    item1.move = track_item1_move
    item2.move = track_item2_move
    
    # 마우스 이동 이벤트 시뮬레이션
    move_delta = QPoint(20, 30)
    end_pos = start_pos + move_delta
    
    move_event = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(end_pos),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    
    # 이동 실행
    item1.mouseMoveEvent(move_event)
    
    # 두 아이템 모두 이동했는지 확인
    assert len(item1_moves) > 0, "item1이 이동해야 합니다"
    assert len(item2_moves) > 0, "item2도 함께 이동해야 합니다"


def test_furniture_item_single_movement_fallback(qtbot, mocker):
    """Canvas를 찾을 수 없는 경우 단일 아이템만 이동하는지 테스트합니다."""
    mock_furniture = MagicMock(spec=Furniture)
    mock_furniture.id = "single_move"
    mock_furniture.image_filename = "single.png"
    
    parent_widget = QWidget()
    qtbot.addWidget(parent_widget)
    
    # 이미지 로딩 모킹
    dummy_pixmap = QPixmap(100, 100)
    dummy_pixmap.fill(Qt.GlobalColor.red)
    mock_load_image = mocker.patch.object(FurnitureItem, 'load_image', return_value=dummy_pixmap)
    
    # FurnitureItem 생성 (Canvas 없이)
    item = FurnitureItem(mock_furniture, parent_widget)
    initial_pos = QPoint(100, 100)
    item.move(initial_pos)
    item.show()
    
    # 드래그 시작
    start_pos = QPoint(50, 50)
    item.old_pos = start_pos
    
    # move 메서드 추적
    move_calls = []
    original_move = item.move
    
    def track_move(pos):
        move_calls.append(pos)
        return original_move(pos)
    
    item.move = track_move
    
    # 마우스 이동 이벤트
    move_delta = QPoint(20, 30)
    end_pos = start_pos + move_delta
    
    move_event = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(end_pos),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    
    # 이동 실행
    item.mouseMoveEvent(move_event)
    
    # move가 호출되었는지 확인
    assert len(move_calls) > 0, "아이템이 이동해야 합니다" 

def test_furniture_item_no_movement_with_ctrl_key(qtbot, mocker):
    """컨트롤 키를 누른 상태에서는 드래그 이동이 방지되는지 테스트합니다."""
    mock_furniture = MagicMock(spec=Furniture)
    mock_furniture.id = "ctrl_no_move"
    mock_furniture.image_filename = "ctrl_test.png"
    
    parent_widget = QWidget()
    qtbot.addWidget(parent_widget)
    
    # 이미지 로딩 모킹
    dummy_pixmap = QPixmap(100, 100)
    dummy_pixmap.fill(Qt.GlobalColor.blue)
    mock_load_image = mocker.patch.object(FurnitureItem, 'load_image', return_value=dummy_pixmap)
    
    # FurnitureItem 생성
    item = FurnitureItem(mock_furniture, parent_widget)
    initial_pos = QPoint(100, 100)
    item.move(initial_pos)
    item.show()
    
    # 드래그 시작
    start_pos = QPoint(50, 50)
    item.old_pos = start_pos
    
    # 현재 위치 저장
    position_before_drag = item.pos()
    
    # 컨트롤 키를 누른 상태에서 마우스 이동 이벤트
    move_delta = QPoint(20, 30)
    end_pos = start_pos + move_delta
    
    with patch('PyQt6.QtGui.QGuiApplication.keyboardModifiers', 
               return_value=Qt.KeyboardModifier.ControlModifier):
        move_event = QMouseEvent(
            QEvent.Type.MouseMove,
            QPointF(end_pos),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.ControlModifier
        )
        
        # 이동 실행
        item.mouseMoveEvent(move_event)
    
    # 위치가 변경되지 않았는지 확인
    position_after_drag = item.pos()
    assert position_before_drag == position_after_drag, "컨트롤 키를 누른 상태에서는 드래그 이동이 방지되어야 합니다"


def test_furniture_item_bounds_check_movement(qtbot, mocker):
    """캔버스 영역을 벗어나지 않도록 이동이 제한되는지 테스트합니다."""
    mock_furniture = MagicMock(spec=Furniture)
    mock_furniture.id = "bounds_test"
    mock_furniture.image_filename = "bounds.png"
    
    # 캔버스 영역 크기 설정
    canvas_area = QWidget()
    canvas_area.setFixedSize(300, 200)  # 작은 캔버스 영역
    qtbot.addWidget(canvas_area)
    
    # 이미지 로딩 모킹
    dummy_pixmap = QPixmap(50, 50)
    dummy_pixmap.fill(Qt.GlobalColor.green)
    mock_load_image = mocker.patch.object(FurnitureItem, 'load_image', return_value=dummy_pixmap)
    
    # FurnitureItem 생성 (캔버스 영역 경계 근처에 배치)
    item = FurnitureItem(mock_furniture, canvas_area)
    item.setFixedSize(50, 50)
    item.move(250, 10)  # 오른쪽 경계 근처에 배치
    item.show()
    
    # Canvas 모킹
    mock_canvas = MagicMock()
    mock_canvas.selected_items = [item]
    canvas_area.parent = lambda: mock_canvas
    
    # 드래그 시작
    start_pos = QPoint(25, 25)  # 아이템 중앙
    item.old_pos = start_pos
    
    # 오른쪽으로 많이 이동하려고 시도 (경계를 벗어날 정도로)
    large_delta = QPoint(100, 0)  # 오른쪽으로 100px 이동 시도
    end_pos = start_pos + large_delta
    
    move_event = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(end_pos),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    
    # 이동 실행
    item.mouseMoveEvent(move_event)
    
    # 경계를 벗어나지 않았는지 확인
    item_right = item.pos().x() + item.width()
    canvas_right = canvas_area.width()
    
    assert item_right <= canvas_right, f"아이템이 캔버스 오른쪽 경계를 벗어남: {item_right} > {canvas_right}" 

def test_furniture_item_resize_bounds_check(qtbot, mocker):
    """리사이즈 시 캔버스 영역을 벗어나지 않도록 크기가 제한되는지 테스트합니다."""
    mock_furniture = MagicMock(spec=Furniture)
    mock_furniture.id = "resize_bounds_test"
    mock_furniture.image_filename = "resize_bounds.png"
    
    # 작은 캔버스 영역 설정
    canvas_area = QWidget()
    canvas_area.setFixedSize(400, 300)  # 작은 캔버스
    qtbot.addWidget(canvas_area)
    
    # 이미지 로딩 모킹
    dummy_pixmap = QPixmap(100, 100)
    dummy_pixmap.fill(Qt.GlobalColor.red)
    mock_load_image = mocker.patch.object(FurnitureItem, 'load_image', return_value=dummy_pixmap)
    
    # Canvas 모킹
    mock_canvas = MagicMock()
    canvas_area.parent = lambda: mock_canvas
    
    # FurnitureItem 생성 (캔버스 오른쪽 경계 근처에 배치)
    item = FurnitureItem(mock_furniture, canvas_area)
    item.setFixedSize(100, 100)
    item.move(320, 150)  # 오른쪽 경계 근처에 배치 (400-320=80만큼 공간 남음)
    item.show()
    
    # 선택 상태로 설정
    mock_canvas.select_furniture_item = MagicMock()
    mock_canvas.selected_items = [item]
    item.is_selected = True
    
    # 리사이즈 시작 설정
    item.is_resizing = True
    item.original_size_on_resize = item.size()
    item.resize_mouse_start_pos = QPoint(10, 10)  # 리사이즈 핸들 시작 위치
    item.maintain_aspect_ratio_on_press = False
    
    # 크게 리사이즈하려고 시도 (캔버스를 벗어날 정도로)
    large_delta = QPoint(200, 150)  # 매우 큰 증가량
    end_pos = item.resize_mouse_start_pos + large_delta
    
    resize_event = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(end_pos),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    
    # 리사이즈 실행
    item.mouseMoveEvent(resize_event)
    
    # 캔버스 경계를 벗어나지 않았는지 확인
    item_right = item.pos().x() + item.width()
    item_bottom = item.pos().y() + item.height()
    canvas_width = canvas_area.width()
    canvas_height = canvas_area.height()
    
    assert item_right <= canvas_width, f"아이템이 캔버스 오른쪽 경계를 벗어남: {item_right} > {canvas_width}"
    assert item_bottom <= canvas_height, f"아이템이 캔버스 아래쪽 경계를 벗어남: {item_bottom} > {canvas_height}"
    
    # 캔버스 경계 제한으로 인해 너비가 80 (=400-320)으로 제한되었는지 확인
    expected_max_width = canvas_width - item.pos().x()  # 400 - 320 = 80
    assert item.width() == expected_max_width, f"너비가 캔버스 경계에 맞게 제한되어야 함: {item.width()} != {expected_max_width}"
    
    # 높이는 충분한 공간이 있으므로 리사이즈된 값이어야 함
    assert item.height() > 100, "높이는 리사이즈되어 증가해야 함"


def test_furniture_item_resize_bounds_check_with_aspect_ratio(qtbot, mocker):
    """비율 유지 리사이즈 시에도 캔버스 경계를 벗어나지 않는지 테스트합니다."""
    mock_furniture = MagicMock(spec=Furniture)
    mock_furniture.id = "resize_aspect_bounds_test"
    mock_furniture.image_filename = "resize_aspect_bounds.png"
    
    # 작은 캔버스 영역 설정
    canvas_area = QWidget()
    canvas_area.setFixedSize(350, 250)
    qtbot.addWidget(canvas_area)
    
    # 이미지 로딩 모킹 (정사각형 이미지)
    dummy_pixmap = QPixmap(100, 100)
    dummy_pixmap.fill(Qt.GlobalColor.blue)
    mock_load_image = mocker.patch.object(FurnitureItem, 'load_image', return_value=dummy_pixmap)
    
    # Canvas 모킹
    mock_canvas = MagicMock()
    canvas_area.parent = lambda: mock_canvas
    
    # FurnitureItem 생성
    item = FurnitureItem(mock_furniture, canvas_area)
    item.setFixedSize(100, 100)
    item.move(200, 100)  # 중앙 근처에 배치
    item.original_ratio = 1.0  # 정사각형 비율
    item.show()
    
    # 선택 상태로 설정
    item.is_selected = True
    
    # 비율 유지 리사이즈 시작 설정
    item.is_resizing = True
    item.original_size_on_resize = item.size()
    item.resize_mouse_start_pos = QPoint(10, 10)
    item.maintain_aspect_ratio_on_press = True  # 비율 유지 모드
    
    # 크게 리사이즈하려고 시도
    large_delta = QPoint(300, 200)  # 캔버스를 벗어날 정도로 큰 증가량
    end_pos = item.resize_mouse_start_pos + large_delta
    
    resize_event = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(end_pos),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.ShiftModifier
    )
    
    # 리사이즈 실행
    item.mouseMoveEvent(resize_event)
    
    # 캔버스 경계를 벗어나지 않았는지 확인
    item_right = item.pos().x() + item.width()
    item_bottom = item.pos().y() + item.height()
    canvas_width = canvas_area.width()
    canvas_height = canvas_area.height()
    
    assert item_right <= canvas_width, f"아이템이 캔버스 오른쪽 경계를 벗어남: {item_right} > {canvas_width}"
    assert item_bottom <= canvas_height, f"아이템이 캔버스 아래쪽 경계를 벗어남: {item_bottom} > {canvas_height}"
    
    # 비율이 유지되었는지 확인 (정사각형)
    aspect_ratio = item.width() / item.height()
    assert abs(aspect_ratio - 1.0) < 0.1, f"정사각형 비율이 유지되지 않음: {aspect_ratio}"


def test_furniture_item_no_movement_with_ctrl_key(qtbot, mocker):
    """컨트롤 키를 누른 상태에서는 드래그 이동이 방지되는지 테스트합니다."""
    mock_furniture = MagicMock(spec=Furniture)
    mock_furniture.id = "ctrl_no_move"
    mock_furniture.image_filename = "ctrl_test.png"
    
    parent_widget = QWidget()
    qtbot.addWidget(parent_widget)
    
    # 이미지 로딩 모킹
    dummy_pixmap = QPixmap(100, 100)
    dummy_pixmap.fill(Qt.GlobalColor.blue)
    mock_load_image = mocker.patch.object(FurnitureItem, 'load_image', return_value=dummy_pixmap)
    
    # FurnitureItem 생성
    item = FurnitureItem(mock_furniture, parent_widget)
    initial_pos = QPoint(100, 100)
    item.move(initial_pos)
    item.show()
    
    # 드래그 시작
    start_pos = QPoint(50, 50)
    item.old_pos = start_pos
    
    # 현재 위치 저장
    position_before_drag = item.pos()
    
    # 컨트롤 키를 누른 상태에서 마우스 이동 이벤트
    move_delta = QPoint(20, 30)
    end_pos = start_pos + move_delta
    
    with patch('PyQt6.QtGui.QGuiApplication.keyboardModifiers', 
               return_value=Qt.KeyboardModifier.ControlModifier):
        move_event = QMouseEvent(
            QEvent.Type.MouseMove,
            QPointF(end_pos),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.ControlModifier
        )
        
        # 이동 실행
        item.mouseMoveEvent(move_event)
    
    # 위치가 변경되지 않았는지 확인
    position_after_drag = item.pos()
    assert position_before_drag == position_after_drag, "컨트롤 키를 누른 상태에서는 드래그 이동이 방지되어야 합니다" 