"""UI 패널 공통 모듈 테스트

패널 공통 모듈의 기능을 테스트합니다.
"""

import unittest.mock
from unittest.mock import patch, MagicMock

import pytest
from PyQt6.QtCore import QObject, QEvent, QPointF, pyqtSignal, QSize, Qt
from PyQt6.QtGui import QMouseEvent, QPixmap
from PyQt6.QtWidgets import QLabel

from src.models.furniture import Furniture
from src.ui.panels.common import ImageLoaderThread, FurnitureItem, FurnitureTableModel, SelectedFurnitureTableModel


@pytest.fixture
def mock_image_service():
    """Mock ImageService"""
    mock = MagicMock()
    mock.get_furniture_image.return_value = b"image_data"
    mock.download_and_cache_image.return_value = QPixmap(100, 100)
    mock.create_thumbnail.return_value = QPixmap(50, 50)
    return mock

@pytest.fixture  
def mock_supabase_client():
    """Mock SupabaseClient"""
    mock = MagicMock()
    mock.get_furniture_image.return_value = b"image_data"
    return mock

@pytest.fixture
def sample_furniture():
    """테스트용 가구 데이터"""
    return Furniture(
        id='1', brand='TestBrand', name='Test Chair', image_filename='chair.png', price=100,
        type='Chair', description='Test Description', link='http://example.com',
        color='Brown', locations=['Living Room'], styles=['Modern'],
        width=50, depth=50, height=100, seat_height=45, author='test_author', created_at=''
    )

@pytest.fixture
def image_loader_thread(mock_image_service, mock_supabase_client, sample_furniture):
    """테스트용 ImageLoaderThread"""
    return ImageLoaderThread(mock_image_service, mock_supabase_client, sample_furniture)

class SignalListener(QObject):
    signal_received = pyqtSignal(str, QPixmap)
    
    def __init__(self):
        super().__init__()
        self.received_filename = None
        self.received_pixmap = None
    
    def on_signal_received(self, filename, pixmap):
        self.received_filename = filename
        self.received_pixmap = pixmap

# ImageLoaderThread 테스트들
def test_image_loader_thread_run_success(qtbot, image_loader_thread, mock_image_service, mock_supabase_client, sample_furniture):
    """ImageLoaderThread.run()이 성공적으로 실행되는지 테스트합니다."""
    listener = SignalListener()
    image_loader_thread.image_loaded.connect(listener.on_signal_received)
    
    # 스레드 실행
    image_loader_thread.start()
    image_loader_thread.wait()
    
    # 처리 완료까지 잠시 대기 (Qt 이벤트 처리)
    qtbot.wait(100)
    
    # Supabase 클라이언트 호출 검증
    mock_supabase_client.get_furniture_image.assert_called_once_with(sample_furniture.image_filename)
    
    # ImageService 호출 검증
    mock_image_service.download_and_cache_image.assert_called_once_with(b"image_data", sample_furniture.image_filename)
    
    # 시그널 발생 검증
    assert listener.received_filename == sample_furniture.image_filename
    assert listener.received_pixmap is not None

def test_image_loader_thread_run_supabase_error(qtbot, image_loader_thread, mock_image_service, mock_supabase_client, sample_furniture):
    """ImageLoaderThread.run() 중 Supabase 오류 발생 시를 테스트합니다."""
    mock_supabase_client.get_furniture_image.side_effect = Exception("DB Error")
    
    listener = SignalListener()
    image_loader_thread.image_loaded.connect(listener.on_signal_received)
    
    with patch('src.ui.panels.common.print') as mock_print:
        image_loader_thread.start()
        image_loader_thread.wait()
        qtbot.wait(100)
    
    # 에러 로그 출력 검증 (새로운 로그 형식)
    expected_calls = [
        '[ImageLoaderThread] 시작: chair.png',
        '[ImageLoaderThread] 오류 발생: chair.png - DB Error',
        '[ImageLoaderThread] 종료: chair.png',
        '[ImageLoaderThread] 완료됨: chair.png'
    ]
    mock_print.assert_has_calls([unittest.mock.call(msg) for msg in expected_calls])
    
    # ImageService는 호출되지 않아야 함
    mock_image_service.download_and_cache_image.assert_not_called()
    
    # 시그널도 발생하지 않아야 함
    assert listener.received_filename is None
    assert listener.received_pixmap is None

def test_image_loader_thread_run_image_service_error(qtbot, image_loader_thread, mock_image_service, mock_supabase_client, sample_furniture):
    """ImageLoaderThread.run() 중 ImageService 오류 발생 시를 테스트합니다."""
    mock_image_service.download_and_cache_image.side_effect = Exception("Service Error")
    
    listener = SignalListener()
    image_loader_thread.image_loaded.connect(listener.on_signal_received)
    
    with patch('src.ui.panels.common.print') as mock_print:
        image_loader_thread.start()
        image_loader_thread.wait()
        qtbot.wait(100)
    
    # 에러 로그 출력 검증 (새로운 로그 형식)
    expected_calls = [
        '[ImageLoaderThread] 시작: chair.png',
        '[ImageLoaderThread] 오류 발생: chair.png - Service Error', 
        '[ImageLoaderThread] 종료: chair.png',
        '[ImageLoaderThread] 완료됨: chair.png'
    ]
    mock_print.assert_has_calls([unittest.mock.call(msg) for msg in expected_calls])
    
    # Supabase는 호출되어야 함
    mock_supabase_client.get_furniture_image.assert_called_once()
    
    # 시그널은 발생하지 않아야 함
    assert listener.received_filename is None
    assert listener.received_pixmap is None

# FurnitureItem 테스트들
@pytest.fixture
def furniture_item_widget(qtbot, sample_furniture, mock_image_service, mock_supabase_client):
    """테스트용 FurnitureItem 위젯을 생성하고 qtbot에 등록합니다."""
    mock_image_service.create_thumbnail.return_value = QPixmap(100,100)

    # FurnitureItem 내부에서 ImageService()와 SupabaseClient()를 직접 생성하므로, patch 필요
    with patch('src.ui.panels.common.ImageService', return_value=mock_image_service), \
         patch('src.ui.panels.common.SupabaseClient', return_value=mock_supabase_client):
        widget = FurnitureItem(sample_furniture)
        qtbot.addWidget(widget)
    return widget

def test_furniture_item_init_ui(furniture_item_widget, sample_furniture):
    """FurnitureItem 생성 시 UI 요소가 올바르게 초기화되는지 테스트합니다."""
    assert furniture_item_widget.furniture == sample_furniture
    labels = furniture_item_widget.findChildren(QLabel)
    label_texts = {label.text() for label in labels}

    assert sample_furniture.name in label_texts
    assert sample_furniture.brand in label_texts
    assert sample_furniture.type in label_texts
    assert f"₩{sample_furniture.price:,}" in label_texts # 통화 기호 추가
    
    assert furniture_item_widget.image_label is not None
    # __init__에서 load_image가 호출되고, 성공적으로 썸네일이 설정되었는지 확인
    assert furniture_item_widget.image_label.pixmap() is not None 
    assert furniture_item_widget.image_label.pixmap().size() == QSize(100, 100)

def test_furniture_item_load_image_success(qtbot, mock_image_service, mock_supabase_client, sample_furniture):
    """load_image 성공 시 서비스 호출 및 UI 업데이트를 테스트합니다."""
    mock_image_service.reset_mock()
    mock_supabase_client.reset_mock()
    
    # ImageService().download_and_cache_image()가 반환할 QPixmap 모의 객체
    downloaded_pixmap_mock = QPixmap(200, 200) # 원본 이미지 크기라고 가정
    mock_image_service.download_and_cache_image.return_value = downloaded_pixmap_mock

    # ImageService().create_thumbnail()이 반환할 QPixmap 모의 객체
    thumbnail_pixmap_mock = QPixmap(50,50) 
    mock_image_service.create_thumbnail.return_value = thumbnail_pixmap_mock

    with patch('src.ui.panels.common.ImageService', return_value=mock_image_service), \
         patch('src.ui.panels.common.SupabaseClient', return_value=mock_supabase_client):
        # FurnitureItem을 생성하면 __init__ 내부에서 self.load_image()가 호출됨
        widget = FurnitureItem(sample_furniture)
        qtbot.addWidget(widget)

    # SupabaseClient 호출 검증
    mock_supabase_client.get_furniture_image.assert_called_once_with(sample_furniture.image_filename)
    
    # ImageService 호출 검증
    mock_image_service.download_and_cache_image.assert_called_once_with(
        b"image_data", sample_furniture.image_filename # mock_supabase_client가 반환하는 데이터
    )
    # load_image 내부의 create_thumbnail 호출 시 인자 검증
    # 첫 번째 인자는 download_and_cache_image의 반환값, 두 번째 인자는 (100,100)
    mock_image_service.create_thumbnail.assert_called_once_with(downloaded_pixmap_mock, (100, 100))
    
    # UI 검증: image_label에 create_thumbnail의 결과(thumbnail_pixmap_mock)가 설정되어야 함
    assert widget.image_label.pixmap() is not None
    assert widget.image_label.pixmap().size() == thumbnail_pixmap_mock.size() # (50,50)
    assert widget.image_label.text() == "" # 성공 시 텍스트는 비어있어야 함

@patch('src.ui.panels.common.print')
def test_furniture_item_load_image_supabase_error(mock_print, qtbot, mock_image_service, mock_supabase_client, sample_furniture):
    """load_image 중 Supabase 오류 발생 시 UI 업데이트를 테스트합니다."""
    mock_supabase_client.get_furniture_image.side_effect = Exception("DB Error")
    # create_thumbnail은 호출되지 않으므로, 반환값 설정은 필수는 아님
    mock_image_service.create_thumbnail.return_value = QPixmap()

    with patch('src.ui.panels.common.ImageService', return_value=mock_image_service), \
         patch('src.ui.panels.common.SupabaseClient', return_value=mock_supabase_client):
        widget = FurnitureItem(sample_furniture)
        qtbot.addWidget(widget)

    mock_image_service.download_and_cache_image.assert_not_called()
    mock_image_service.create_thumbnail.assert_not_called()
    assert widget.image_label.text() == "이미지 로드 실패"
    mock_print.assert_any_call(f"이미지 로드 중 오류 발생: DB Error")

@patch('src.ui.panels.common.print')
def test_furniture_item_load_image_service_error(mock_print, qtbot, mock_image_service, mock_supabase_client, sample_furniture):
    """load_image 중 ImageService.download_and_cache_image 오류 발생 시 UI 업데이트를 테스트합니다."""
    mock_image_service.download_and_cache_image.side_effect = Exception("Service DL Error")
    # create_thumbnail은 호출되지 않으므로, 반환값 설정은 필수는 아님
    mock_image_service.create_thumbnail.return_value = QPixmap()

    with patch('src.ui.panels.common.ImageService', return_value=mock_image_service), \
         patch('src.ui.panels.common.SupabaseClient', return_value=mock_supabase_client):
        widget = FurnitureItem(sample_furniture)
        qtbot.addWidget(widget)

    mock_supabase_client.get_furniture_image.assert_called_once()
    mock_image_service.download_and_cache_image.assert_called_once() # 호출은 됨
    mock_image_service.create_thumbnail.assert_not_called() # 여기서 오류나면 create_thumbnail 미호출
    assert widget.image_label.text() == "이미지 로드 실패"
    mock_print.assert_any_call(f"이미지 로드 중 오류 발생: Service DL Error")

@patch('src.ui.panels.common.print') # create_thumbnail에서 오류 발생하는 케이스 추가
def test_furniture_item_load_image_thumbnail_error(mock_print, qtbot, mock_image_service, mock_supabase_client, sample_furniture):
    """load_image 중 ImageService.create_thumbnail 오류 발생 시 UI 업데이트를 테스트합니다."""
    # download_and_cache_image는 성공했다고 가정
    mock_image_service.download_and_cache_image.return_value = QPixmap(200,200)
    mock_image_service.create_thumbnail.side_effect = Exception("Thumbnail Creation Error")

    with patch('src.ui.panels.common.ImageService', return_value=mock_image_service), \
         patch('src.ui.panels.common.SupabaseClient', return_value=mock_supabase_client):
        widget = FurnitureItem(sample_furniture)
        qtbot.addWidget(widget)

    mock_supabase_client.get_furniture_image.assert_called_once()
    mock_image_service.download_and_cache_image.assert_called_once()
    mock_image_service.create_thumbnail.assert_called_once() # 호출은 됨
    assert widget.image_label.text() == "이미지 로드 실패" # 에러 메시지 표시 확인
    mock_print.assert_any_call(f"이미지 로드 중 오류 발생: Thumbnail Creation Error")

def test_furniture_item_mouse_press_event_drag(qtbot, furniture_item_widget, sample_furniture):
    """mousePressEvent 발생 시 QDrag 동작을 테스트합니다."""
    captured_mime_data = []

    def mock_set_mime_data(mime_data_arg):
        captured_mime_data.append(mime_data_arg)

    with patch('src.ui.panels.common.QDrag') as MockQDrag:
        mock_drag_instance = MockQDrag.return_value
        # QDrag.exec()는 이벤트 루프를 시작하므로, 테스트 중에는 반환값을 모킹하여 바로 리턴하도록 함
        mock_drag_instance.exec.return_value = Qt.DropAction.CopyAction 
        mock_drag_instance.setMimeData.side_effect = mock_set_mime_data

        event = QMouseEvent(
            QEvent.Type.MouseButtonPress, 
            QPointF(10, 10), 
            Qt.MouseButton.LeftButton, 
            Qt.MouseButton.LeftButton, 
            Qt.KeyboardModifier.NoModifier
        )
        furniture_item_widget.mousePressEvent(event)

        MockQDrag.assert_called_once_with(furniture_item_widget)
        assert len(captured_mime_data) == 1, "setMimeData가 호출되지 않았거나 여러 번 호출되었습니다."
        mime_data = captured_mime_data[0]
        
        assert mime_data.hasFormat("application/x-furniture")
        
        # FurnitureItem의 mousePressEvent에서 mime_data에 설정하는 데이터 생성 방식 확인 필요
        # 현재 코드는 Furniture 객체의 모든 속성을 포함하는 dict를 str로 변환하여 저장
        expected_data_dict = {
            'id': sample_furniture.id,
            'name': sample_furniture.name,
            'image_filename': sample_furniture.image_filename,
            'price': sample_furniture.price,
            'brand': sample_furniture.brand,
            'type': sample_furniture.type,
            'description': sample_furniture.description,
            'link': sample_furniture.link,
            'color': sample_furniture.color,
            'locations': sample_furniture.locations,
            'styles': sample_furniture.styles,
            'width': sample_furniture.width,
            'depth': sample_furniture.depth,
            'height': sample_furniture.height,
            'seat_height': sample_furniture.seat_height,
            'author': sample_furniture.author,
            'created_at': sample_furniture.created_at 
        }
        # 실제 MIME 데이터는 bytearray이므로 .data()를 한 번 더 호출하거나 bytes()로 변환 후 decode
        actual_data_str = bytes(mime_data.data("application/x-furniture")).decode()
        assert actual_data_str == str(expected_data_dict)
        mock_drag_instance.exec.assert_called_once()

# FurnitureTableModel 테스트들
@pytest.fixture
def furniture_table_model(qtbot, mock_image_service, mock_supabase_client):
    with patch('src.ui.panels.common.ImageService', return_value=mock_image_service), \
         patch('src.ui.panels.common.SupabaseClient', return_value=mock_supabase_client):
        model = FurnitureTableModel()
    return model

def test_furniture_table_model_init(furniture_table_model):
    assert furniture_table_model.columnCount() == 8
    expected_headers = ["썸네일", "브랜드", "이름", "가격", "타입", "위치", "색상", "스타일"]
    for i, header in enumerate(expected_headers):
        assert furniture_table_model.headerData(i, Qt.Orientation.Horizontal) == header

def test_furniture_table_model_add_furniture_single(furniture_table_model, sample_furniture, mock_image_service):
    with patch.object(furniture_table_model, 'load_thumbnail_async') as mock_load_thumbnail:
        furniture_table_model.add_furniture(sample_furniture)
        
        assert furniture_table_model.rowCount() == 1
        assert len(furniture_table_model.furniture_items) == 1
        assert furniture_table_model.furniture_items[0] == sample_furniture
        
        # 각 컬럼의 데이터가 올바르게 설정되었는지 확인
        assert furniture_table_model.item(0, 1).text() == sample_furniture.brand  # 브랜드
        assert furniture_table_model.item(0, 2).text() == sample_furniture.name   # 이름
        assert furniture_table_model.item(0, 3).text() == f"₩{sample_furniture.price:,}"  # 가격
        assert furniture_table_model.item(0, 4).text() == sample_furniture.type  # 타입
        assert furniture_table_model.item(0, 5).text() == ", ".join(sample_furniture.locations)  # 위치
        assert furniture_table_model.item(0, 6).text() == sample_furniture.color  # 색상
        assert furniture_table_model.item(0, 7).text() == ", ".join(sample_furniture.styles)  # 스타일
        
        # 썸네일 로딩 메서드가 호출되었는지 확인
        mock_load_thumbnail.assert_called_once_with(sample_furniture, furniture_table_model.item(0, 0))

def test_furniture_table_model_add_multiple_furniture(furniture_table_model, sample_furniture):
    # 가구 2개 추가
    furniture2 = Furniture(
        id='2', brand='SecondBrand', name='Second Chair', image_filename='chair2.png', price=200,
        type='Chair', description='Second Description', link='http://example2.com',
        color='Blue', locations=['Bedroom'], styles=['Modern'],
        width=60, depth=60, height=110, seat_height=50, author='test_author2', created_at=''
    )
    
    with patch.object(furniture_table_model, 'load_thumbnail_async'):
        furniture_table_model.add_furniture(sample_furniture)
        furniture_table_model.add_furniture(furniture2)
        
        assert furniture_table_model.rowCount() == 2
        assert len(furniture_table_model.furniture_items) == 2
        assert furniture_table_model.furniture_items[0] == sample_furniture
        assert furniture_table_model.furniture_items[1] == furniture2
        
        # 첫 번째 가구 검증
        assert furniture_table_model.item(0, 1).text() == sample_furniture.brand
        # 두 번째 가구 검증
        assert furniture_table_model.item(1, 1).text() == furniture2.brand

def test_furniture_table_model_clear_furniture(furniture_table_model, sample_furniture):
    """clear_furniture 메서드가 올바르게 동작하는지 테스트합니다."""
    # 가구 추가
    with patch.object(furniture_table_model, 'load_thumbnail_async'):
        furniture_table_model.add_furniture(sample_furniture)
        assert furniture_table_model.rowCount() == 1
        assert len(furniture_table_model.furniture_items) == 1
    
    # 스레드가 실행 중인 것처럼 모킹
    mock_thread = MagicMock()
    mock_thread.isRunning.return_value = True
    furniture_table_model.loading_threads['chair.png'] = mock_thread
    
    # clear 실행
    furniture_table_model.clear_furniture()
    
    # 스레드 정리 확인 (수정된 대기 시간: 3000ms)
    mock_thread.stop.assert_called_once()
    mock_thread.quit.assert_called_once()
    mock_thread.wait.assert_called_once_with(3000)
    assert len(furniture_table_model.loading_threads) == 0
    
    # 모델 데이터 초기화 확인
    assert furniture_table_model.rowCount() == 0
    assert len(furniture_table_model.furniture_items) == 0
    assert len(furniture_table_model.thumbnail_cache) == 0
    
    # 헤더는 다시 설정되어야 함
    expected_headers = ["썸네일", "브랜드", "이름", "가격", "타입", "위치", "색상", "스타일"]
    for i, header in enumerate(expected_headers):
        assert furniture_table_model.headerData(i, Qt.Orientation.Horizontal) == header

# SelectedFurnitureTableModel 테스트들
def test_selected_furniture_table_model():
    """SelectedFurnitureTableModel의 기본 동작을 테스트합니다."""
    model = SelectedFurnitureTableModel()
    
    # 초기 상태 확인 (새로운 13개 컬럼, 총 가격 제거됨)
    assert model.columnCount() == 13
    expected_headers = [
        "이름", "브랜드", "타입", "가격", "색상", 
        "위치", "스타일", "크기(W×D×H)", "좌석높이", "설명", "링크", "작성자", "개수"
    ]
    for i, header in enumerate(expected_headers):
        assert model.headerData(i, Qt.Orientation.Horizontal) == header
    
    # 가구 추가 테스트
    sample_furniture = Furniture(
        id='1', brand='TestBrand', name='Test Chair', image_filename='chair.png', price=100,
        type='Chair', description='Test Description', link='http://example.com',
        color='Brown', locations=['Living Room'], styles=['Modern'],
        width=60, depth=50, height=80, seat_height=45, author='TestAuthor'
    )
    
    model.add_furniture(sample_furniture)
    
    # 모델에 행이 추가되었는지 확인
    assert model.rowCount() == 1
    
    # 각 컬럼의 데이터 확인 (13개 컬럼)
    assert model.item(0, 0).text() == "Test Chair"  # 이름
    assert model.item(0, 1).text() == "TestBrand"   # 브랜드
    assert model.item(0, 2).text() == "Chair"       # 타입
    assert model.item(0, 3).text() == "₩100"        # 가격
    assert model.item(0, 4).text() == "Brown"       # 색상
    assert model.item(0, 5).text() == "Living Room" # 위치
    assert model.item(0, 6).text() == "Modern"      # 스타일
    assert model.item(0, 7).text() == "60×50×80mm"  # 크기
    assert model.item(0, 8).text() == "45mm"        # 좌석높이
    assert model.item(0, 9).text() == "Test Description"  # 설명
    assert model.item(0, 10).text() == "http://example.com"  # 링크
    assert model.item(0, 11).text() == "TestAuthor"
    assert model.item(0, 12).text() == "1"          # 개수
    
    # 같은 가구 다시 추가 (개수 증가 확인)
    model.add_furniture(sample_furniture)
    assert model.rowCount() == 1  # 여전히 1행 (같은 가구)
    assert model.item(0, 12).text() == "2"  # 개수가 2로 증가
    
    # 총계 계산 테스트
    assert model.get_total_count() == 2
    assert model.get_total_price() == 200  # 100 * 2
    
    # 다른 가구 추가
    another_furniture = Furniture(
        id='2', brand='AnotherBrand', name='Test Table', image_filename='table.png', price=200,
        type='Table', description='Another Description', link='http://example2.com',
        color='White', locations=['Dining Room'], styles=['Classic'],
        width=120, depth=80, height=75, seat_height=None, author='AnotherAuthor'
    )
    
    model.add_furniture(another_furniture)
    assert model.rowCount() == 2  # 이제 2행
    
    # 총계 다시 확인
    assert model.get_total_count() == 3  # 의자 2개 + 테이블 1개
    assert model.get_total_price() == 400  # (100 * 2) + (200 * 1)
    
    # 초기화 테스트
    model.clear_furniture()
    assert model.rowCount() == 0
    assert model.get_total_count() == 0
    assert model.get_total_price() == 0


def test_selected_furniture_order_management():
    """가구 순서 변경 기능을 테스트합니다."""
    model = SelectedFurnitureTableModel()
    
    # 테스트 가구들 생성
    chair = Furniture(
        id='1', brand='TestBrand', name='Chair', image_filename='chair.png', price=100,
        type='Chair', description='Test Chair', link='', color='Brown', 
        locations=['Living Room'], styles=['Modern'], width=60, depth=50, height=80
    )
    
    table = Furniture(
        id='2', brand='TestBrand', name='Table', image_filename='table.png', price=200,
        type='Table', description='Test Table', link='', color='White', 
        locations=['Dining Room'], styles=['Modern'], width=120, depth=80, height=75
    )
    
    sofa = Furniture(
        id='3', brand='TestBrand', name='Sofa', image_filename='sofa.png', price=300,
        type='Sofa', description='Test Sofa', link='', color='Gray', 
        locations=['Living Room'], styles=['Modern'], width=200, depth=100, height=80
    )
    
    # 가구 추가
    model.add_furniture(chair)
    model.add_furniture(table)
    model.add_furniture(sofa)
    
    # 초기 순서 확인 (추가 순서대로)
    assert model.get_furniture_name_at_row(0) == "Chair"
    assert model.get_furniture_name_at_row(1) == "Table"
    assert model.get_furniture_name_at_row(2) == "Sofa"
    
    # 테이블을 위로 이동 (1 -> 0)
    new_row = model.move_furniture_up("Table")
    assert new_row == 0
    assert model.get_furniture_name_at_row(0) == "Table"
    assert model.get_furniture_name_at_row(1) == "Chair"
    assert model.get_furniture_name_at_row(2) == "Sofa"
    
    # 소파를 아래로 이동 (2 -> 2, 이미 맨 아래이므로 변화 없음)
    new_row = model.move_furniture_down("Sofa")
    assert new_row == -1  # 이동 불가
    
    # 소파를 맨 위로 이동
    new_row = model.move_furniture_to_top("Sofa")
    assert new_row == 0
    assert model.get_furniture_name_at_row(0) == "Sofa"
    assert model.get_furniture_name_at_row(1) == "Table"
    assert model.get_furniture_name_at_row(2) == "Chair"
    
    # 테이블을 맨 아래로 이동
    new_row = model.move_furniture_to_bottom("Table")
    assert new_row == 2
    assert model.get_furniture_name_at_row(0) == "Sofa"
    assert model.get_furniture_name_at_row(1) == "Chair"
    assert model.get_furniture_name_at_row(2) == "Table"
    
    # 소파를 특정 위치로 이동 (0 -> 1)
    success = model.move_furniture_to_position("Sofa", 1)
    assert success == True
    assert model.get_furniture_name_at_row(0) == "Chair"
    assert model.get_furniture_name_at_row(1) == "Sofa"
    assert model.get_furniture_name_at_row(2) == "Table"


def test_selected_furniture_sorting():
    """가구 정렬 기능을 테스트합니다."""
    model = SelectedFurnitureTableModel()
    
    # 테스트 가구들 생성 (의도적으로 순서를 섞어서)
    furniture_data = [
        ("Zebra Chair", "BrandC", 300, "Chair"),
        ("Apple Table", "BrandA", 100, "Table"),
        ("Banana Sofa", "BrandB", 200, "Sofa"),
    ]
    
    for name, brand, price, type_name in furniture_data:
        furniture = Furniture(
            id=name, brand=brand, name=name, image_filename=f'{name}.png', price=price,
            type=type_name, description=f'Test {name}', link='', color='Brown', 
            locations=['Room'], styles=['Modern'], width=100, depth=100, height=100
        )
        model.add_furniture(furniture)
    
    # 이름으로 오름차순 정렬
    model.sort_furniture("name", True)
    assert model.get_furniture_name_at_row(0) == "Apple Table"
    assert model.get_furniture_name_at_row(1) == "Banana Sofa"
    assert model.get_furniture_name_at_row(2) == "Zebra Chair"
    
    # 이름으로 내림차순 정렬
    model.sort_furniture("name", False)
    assert model.get_furniture_name_at_row(0) == "Zebra Chair"
    assert model.get_furniture_name_at_row(1) == "Banana Sofa"
    assert model.get_furniture_name_at_row(2) == "Apple Table"
    
    # 브랜드로 오름차순 정렬
    model.sort_furniture("brand", True)
    assert model.get_furniture_name_at_row(0) == "Apple Table"  # BrandA
    assert model.get_furniture_name_at_row(1) == "Banana Sofa"  # BrandB
    assert model.get_furniture_name_at_row(2) == "Zebra Chair"  # BrandC
    
    # 가격으로 오름차순 정렬
    model.sort_furniture("price", True)
    assert model.get_furniture_name_at_row(0) == "Apple Table"  # 100
    assert model.get_furniture_name_at_row(1) == "Banana Sofa"  # 200
    assert model.get_furniture_name_at_row(2) == "Zebra Chair"  # 300
    
    # 가격으로 내림차순 정렬
    model.sort_furniture("price", False)
    assert model.get_furniture_name_at_row(0) == "Zebra Chair"  # 300
    assert model.get_furniture_name_at_row(1) == "Banana Sofa"  # 200
    assert model.get_furniture_name_at_row(2) == "Apple Table"  # 100
    
    # 타입으로 정렬
    model.sort_furniture("type", True)
    assert model.get_furniture_name_at_row(0) == "Zebra Chair"   # Chair
    assert model.get_furniture_name_at_row(1) == "Banana Sofa"   # Sofa
    assert model.get_furniture_name_at_row(2) == "Apple Table"   # Table


def test_selected_furniture_drag_drop():
    """드래그 앤 드롭 기능을 테스트합니다."""
    model = SelectedFurnitureTableModel()
    
    # 드래그 앤 드롭 설정 확인
    assert Qt.DropAction.MoveAction in model.supportedDropActions()
    assert "application/x-furniture-order" in model.mimeTypes()
    
    # 가구 추가
    chair = Furniture(
        id='1', brand='TestBrand', name='Chair', image_filename='chair.png', price=100,
        type='Chair', description='Test Chair', link='', color='Brown', 
        locations=['Living Room'], styles=['Modern'], width=60, depth=50, height=80
    )
    
    model.add_furniture(chair)
    assert model.rowCount() == 1
    
    # MIME 데이터 생성 테스트
    index = model.index(0, 0)
    mime_data = model.mimeData([index])
    assert mime_data is not None
    assert mime_data.hasFormat("application/x-furniture-order")
    
    # MIME 데이터에서 가구 이름 확인
    furniture_name = mime_data.data("application/x-furniture-order").data().decode('utf-8')
    assert furniture_name == "Chair" 

def test_selected_furniture_column_width_preservation():
    """가구 순서 변경 시 컬럼 너비 복원 기능을 테스트합니다."""
    model = SelectedFurnitureTableModel()
    
    # 콜백 호출 횟수를 추적하는 모킹 함수
    callback_call_count = [0]  # 리스트를 사용해서 내부 함수에서 수정 가능하게 함
    
    def mock_column_width_callback():
        callback_call_count[0] += 1
    
    # 콜백 설정
    model.set_column_width_callback(mock_column_width_callback)
    
    # 가구 추가 (refresh_model이 호출됨)
    chair = Furniture(
        id='1', brand='TestBrand', name='Chair', image_filename='chair.png', price=100,
        type='Chair', description='Test Chair', link='', color='Brown', 
        locations=['Living Room'], styles=['Modern'], width=60, depth=50, height=80
    )
    
    model.add_furniture(chair)
    assert callback_call_count[0] == 1  # add_furniture -> refresh_model -> 콜백 호출
    
    # 순서 변경 (refresh_model이 다시 호출됨)
    model.move_furniture_up("Chair")  # 이미 맨 위이므로 실제로는 변경 안됨
    
    # 다른 가구 추가 후 순서 변경
    table = Furniture(
        id='2', brand='TestBrand', name='Table', image_filename='table.png', price=200,
        type='Table', description='Test Table', link='', color='White', 
        locations=['Dining Room'], styles=['Modern'], width=120, depth=80, height=75
    )
    
    model.add_furniture(table)
    assert callback_call_count[0] == 2  # 두 번째 add_furniture -> refresh_model -> 콜백 호출
    
    # 실제로 순서 변경이 일어나는 경우
    model.move_furniture_up("Table")  # Table을 위로 이동
    assert callback_call_count[0] == 3  # move_furniture_up -> refresh_model -> 콜백 호출
    
    # 정렬 기능 테스트
    model.sort_furniture("name", True)
    assert callback_call_count[0] == 4  # sort_furniture -> refresh_model -> 콜백 호출
    
    # 콜백이 제대로 설정되고 호출되는지 확인
    assert model.column_width_callback is not None
    assert callable(model.column_width_callback) 