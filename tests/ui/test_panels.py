import pytest
from unittest.mock import MagicMock, PropertyMock, patch
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt, QMimeData, QSize, QEvent, QPointF # QTimer 추가, Qt 추가, QSize, QEvent, QPointF 추가
from PyQt6.QtGui import QPixmap, QDrag, QMouseEvent, QGuiApplication, QStandardItemModel, QStandardItem # QDrag 추가, QGuiApplication 추가, QStandardItemModel, QStandardItem 추가
from PyQt6.QtWidgets import QApplication, QLabel # QApplication 임포트 (mousePressEvent 테스트용), QLabel 임포트

# 테스트 대상 모듈 임포트 시 src. 접두사 필요 여부 확인 (보통 필요)
from src.services.image_service import ImageService
from src.services.supabase_client import SupabaseClient
from src.models.furniture import Furniture
from src.ui.panels import ImageLoaderThread, FurnitureItem, FurnitureTableModel # ImageLoaderThread 임포트, FurnitureItem 임포트, FurnitureTableModel 임포트

# QApplication 인스턴스 관리는 conftest.py에서 처리

@pytest.fixture
def mock_image_service():
    service = MagicMock(spec=ImageService)
    # download_and_cache_image가 QPixmap을 반환하도록 설정
    service.download_and_cache_image.return_value = QPixmap() 
    return service

@pytest.fixture
def mock_supabase_client():
    client = MagicMock(spec=SupabaseClient)
    client.get_furniture_image.return_value = b"image_data" # 바이트 데이터 반환
    return client

@pytest.fixture
def sample_furniture():
    return Furniture(
        id="1", name="Test Chair", image_filename="chair.png", brand="TestBrand", type="Chair", 
        price=100, description="A test chair", link="http://example.com", color="Red",
        locations=["Living Room"], styles=["Modern"], width=50, depth=50, height=100,
        seat_height=45, author="test_author" 
    )

@pytest.fixture
def image_loader_thread(mock_image_service, mock_supabase_client, sample_furniture):
    thread = ImageLoaderThread(mock_image_service, mock_supabase_client, sample_furniture)
    return thread

# ImageLoaderThread.image_loaded 시그널을 받기 위한 QObject 헬퍼 클래스
class SignalListener(QObject):
    signal_received = pyqtSignal(str, QPixmap)
    
    def __init__(self):
        super().__init__()
        self.received_args = None

    def on_signal_received(self, filename, pixmap):
        self.received_args = (filename, pixmap)

def test_image_loader_thread_run_success(qtbot, image_loader_thread, mock_image_service, mock_supabase_client, sample_furniture):
    """ImageLoaderThread.run() 성공 시 시그널 발생 및 서비스 호출 검증"""
    listener = SignalListener()
    image_loader_thread.image_loaded.connect(listener.on_signal_received)
    
    # 스레드 실행 (qtbot.waitSignal은 QThread.start()와 함께 사용)
    with qtbot.waitSignal(image_loader_thread.image_loaded, timeout=1000) as blocker:
        image_loader_thread.start() # run() 메소드 직접 호출 대신 start() 사용

    # 서비스 메소드 호출 검증
    mock_supabase_client.get_furniture_image.assert_called_once_with(sample_furniture.image_filename)
    mock_image_service.download_and_cache_image.assert_called_once_with(
        b"image_data", sample_furniture.image_filename
    )
    
    # 시그널 발생 및 인자 검증
    assert blocker.signal_triggered, "image_loaded 시그널이 발생하지 않았습니다."
    assert listener.received_args is not None
    filename, pixmap = listener.received_args
    assert filename == sample_furniture.image_filename
    assert isinstance(pixmap, QPixmap) # QPixmap 인스턴스인지 확인

def test_image_loader_thread_run_supabase_error(qtbot, image_loader_thread, mock_image_service, mock_supabase_client, sample_furniture):
    """Supabase에서 이미지 로드 실패 시 동작 검증"""
    mock_supabase_client.get_furniture_image.side_effect = Exception("Supabase Error")
    
    listener = SignalListener()
    image_loader_thread.image_loaded.connect(listener.on_signal_received)
    
    # print_mock = MagicMock() # print 함수를 모킹할 수 있음
    
    # with patch('builtins.print', print_mock): # print 호출을 확인하고 싶을 경우
    image_loader_thread.start()
    image_loader_thread.wait() # 스레드가 완료될 때까지 대기

    # 서비스 메소드 호출 검증
    mock_supabase_client.get_furniture_image.assert_called_once_with(sample_furniture.image_filename)
    mock_image_service.download_and_cache_image.assert_not_called() # 호출되지 않아야 함
    
    # 시그널이 발생하지 않았는지 확인
    assert listener.received_args is None # 시그널 핸들러가 호출되지 않아야 함
    # print_mock.assert_called_once() # 에러 메시지가 출력되었는지 확인할 수 있음

def test_image_loader_thread_run_image_service_error(qtbot, image_loader_thread, mock_image_service, mock_supabase_client, sample_furniture):
    """ImageService에서 이미지 처리 실패 시 동작 검증"""
    mock_image_service.download_and_cache_image.side_effect = Exception("ImageService Error")
    
    listener = SignalListener()
    image_loader_thread.image_loaded.connect(listener.on_signal_received)
    
    image_loader_thread.start()
    image_loader_thread.wait()

    mock_supabase_client.get_furniture_image.assert_called_once_with(sample_furniture.image_filename)
    mock_image_service.download_and_cache_image.assert_called_once_with(
        b"image_data", sample_furniture.image_filename
    )
    
    assert listener.received_args is None

# FurnitureItem Tests
# -------------------
# QLabel, QSize, Qt, QMimeData, QEvent, QPointF, QPixmap, QDrag, QMouseEvent, QGuiApplication 등 필요한 모듈은
# 파일 상단에서 이미 임포트되었거나, pytest fixture 또는 conftest.py 에서 관리된다고 가정합니다.
# 만약 특정 임포트가 누락되었다면, 테스트 실행 시 ImportError가 발생할 것입니다.

@pytest.fixture
def furniture_item_widget(qtbot, sample_furniture, mock_image_service, mock_supabase_client):
    """테스트용 FurnitureItem 위젯을 생성하고 qtbot에 등록합니다."""
    mock_image_service.create_thumbnail.return_value = QPixmap(100,100)

    # FurnitureItem 내부에서 ImageService()와 SupabaseClient()를 직접 생성하므로, patch 필요
    with patch('src.ui.panels.ImageService', return_value=mock_image_service), \
         patch('src.ui.panels.SupabaseClient', return_value=mock_supabase_client):
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

    with patch('src.ui.panels.ImageService', return_value=mock_image_service), \
         patch('src.ui.panels.SupabaseClient', return_value=mock_supabase_client):
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

@patch('src.ui.panels.print')
def test_furniture_item_load_image_supabase_error(mock_print, qtbot, mock_image_service, mock_supabase_client, sample_furniture):
    """load_image 중 Supabase 오류 발생 시 UI 업데이트를 테스트합니다."""
    mock_supabase_client.get_furniture_image.side_effect = Exception("DB Error")
    # create_thumbnail은 호출되지 않으므로, 반환값 설정은 필수는 아님
    mock_image_service.create_thumbnail.return_value = QPixmap()

    with patch('src.ui.panels.ImageService', return_value=mock_image_service), \
         patch('src.ui.panels.SupabaseClient', return_value=mock_supabase_client):
        widget = FurnitureItem(sample_furniture)
        qtbot.addWidget(widget)

    mock_image_service.download_and_cache_image.assert_not_called()
    mock_image_service.create_thumbnail.assert_not_called()
    assert widget.image_label.text() == "이미지 로드 실패"
    mock_print.assert_any_call(f"이미지 로드 중 오류 발생: DB Error")

@patch('src.ui.panels.print')
def test_furniture_item_load_image_service_error(mock_print, qtbot, mock_image_service, mock_supabase_client, sample_furniture):
    """load_image 중 ImageService.download_and_cache_image 오류 발생 시 UI 업데이트를 테스트합니다."""
    mock_image_service.download_and_cache_image.side_effect = Exception("Service DL Error")
    # create_thumbnail은 호출되지 않으므로, 반환값 설정은 필수는 아님
    mock_image_service.create_thumbnail.return_value = QPixmap()

    with patch('src.ui.panels.ImageService', return_value=mock_image_service), \
         patch('src.ui.panels.SupabaseClient', return_value=mock_supabase_client):
        widget = FurnitureItem(sample_furniture)
        qtbot.addWidget(widget)

    mock_supabase_client.get_furniture_image.assert_called_once()
    mock_image_service.download_and_cache_image.assert_called_once() # 호출은 됨
    mock_image_service.create_thumbnail.assert_not_called() # 여기서 오류나면 create_thumbnail 미호출
    assert widget.image_label.text() == "이미지 로드 실패"
    mock_print.assert_any_call(f"이미지 로드 중 오류 발생: Service DL Error")

@patch('src.ui.panels.print') # create_thumbnail에서 오류 발생하는 케이스 추가
def test_furniture_item_load_image_thumbnail_error(mock_print, qtbot, mock_image_service, mock_supabase_client, sample_furniture):
    """load_image 중 ImageService.create_thumbnail 오류 발생 시 UI 업데이트를 테스트합니다."""
    # download_and_cache_image는 성공했다고 가정
    mock_image_service.download_and_cache_image.return_value = QPixmap(200,200)
    mock_image_service.create_thumbnail.side_effect = Exception("Thumbnail Creation Error")

    with patch('src.ui.panels.ImageService', return_value=mock_image_service), \
         patch('src.ui.panels.SupabaseClient', return_value=mock_supabase_client):
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

    with patch('src.ui.panels.QDrag') as MockQDrag:
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
            # sample_furniture.created_at은 datetime 객체일 수 있음. 
            # MIME 데이터로 변환 시 문자열로 변환되는지 확인 필요.
            # FurnitureItem.mousePressEvent 코드를 보면 str(furniture_data).encode()로 변환.
            # 여기서 furniture_data는 dict. dict를 str()로 변환하면 datetime 객체도 repr 형태로 들어감.
            'created_at': sample_furniture.created_at 
        }
        # 실제 MIME 데이터는 bytearray이므로 .data()를 한 번 더 호출하거나 bytes()로 변환 후 decode
        actual_data_str = bytes(mime_data.data("application/x-furniture")).decode()
        assert actual_data_str == str(expected_data_dict)
        mock_drag_instance.exec.assert_called_once()

# FurnitureTableModel Tests
# -------------------------
from PyQt6.QtGui import QStandardItemModel, QStandardItem # Ensure these are imported
from PyQt6.QtCore import QThread, Qt # Ensure Qt is imported
# QPixmap should be imported from PyQt6.QtGui if not already
# from PyQt6.QtGui import QPixmap 
from src.ui.panels import FurnitureTableModel

@pytest.fixture
def furniture_table_model(qtbot, mock_image_service, mock_supabase_client):
    with patch('src.ui.panels.ImageService', return_value=mock_image_service), \
         patch('src.ui.panels.SupabaseClient', return_value=mock_supabase_client):
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
        
        thumbnail_item = furniture_table_model.item(0, 0)
        assert isinstance(thumbnail_item, QStandardItem)
        assert thumbnail_item.data(Qt.ItemDataRole.UserRole) == sample_furniture # 활성화
        mock_load_thumbnail.assert_called_once_with(sample_furniture, thumbnail_item)

        brand_item = furniture_table_model.item(0, 1)
        assert brand_item.text() == sample_furniture.brand
        assert brand_item.data(Qt.ItemDataRole.UserRole) == sample_furniture # 활성화
        
        name_item = furniture_table_model.item(0, 2)
        assert name_item.text() == sample_furniture.name
        assert name_item.data(Qt.ItemDataRole.UserRole) == sample_furniture # 활성화
        
        price_item = furniture_table_model.item(0, 3)
        assert price_item.text() == f"₩{sample_furniture.price:,}"
        assert price_item.data(Qt.ItemDataRole.UserRole) == sample_furniture # 활성화

        type_item = furniture_table_model.item(0, 4)
        assert type_item.text() == sample_furniture.type
        assert type_item.data(Qt.ItemDataRole.UserRole) == sample_furniture # 활성화

        location_item = furniture_table_model.item(0, 5)
        expected_locations_str = ", ".join(sample_furniture.locations) if sample_furniture.locations else ""
        assert location_item.text() == expected_locations_str
        assert location_item.data(Qt.ItemDataRole.UserRole) == sample_furniture # 활성화

        color_item = furniture_table_model.item(0, 6)
        assert color_item.text() == sample_furniture.color
        assert color_item.data(Qt.ItemDataRole.UserRole) == sample_furniture # 활성화

        style_item = furniture_table_model.item(0, 7)
        expected_styles_str = ", ".join(sample_furniture.styles) if sample_furniture.styles else ""
        assert style_item.text() == expected_styles_str
        assert style_item.data(Qt.ItemDataRole.UserRole) == sample_furniture # 활성화

def test_furniture_table_model_add_multiple_furniture(furniture_table_model, sample_furniture):
    furniture2 = Furniture(
        id="2", name="Test Sofa", image_filename="sofa.png", brand="TestBrand2", type="Sofa",
        price=200, description="A test sofa", link="http://example.com/sofa", color="Blue",
        locations=['Office'], styles=['Classic'], width=150, depth=80, height=90,
        seat_height=40, author="test_author2"
    )
    with patch.object(furniture_table_model, 'load_thumbnail_async') as mock_load_thumbnail:
        furniture_table_model.add_furniture(sample_furniture)
        furniture_table_model.add_furniture(furniture2)

        assert furniture_table_model.rowCount() == 2
        assert len(furniture_table_model.furniture_items) == 2
        assert furniture_table_model.furniture_items[1] == furniture2
        assert mock_load_thumbnail.call_count == 2


def test_furniture_table_model_clear_furniture(furniture_table_model, sample_furniture):
    from PyQt6.QtGui import QPixmap # 함수 내 로컬 임포트
    # ImageLoaderThread는 파일 상단에서 이미 임포트되어 있다고 가정합니다.
    # from src.ui.panels import ImageLoaderThread 

    with patch.object(furniture_table_model, 'load_thumbnail_async'):
        furniture_table_model.add_furniture(sample_furniture)
        
        # 실제 ImageLoaderThread 인스턴스처럼 보이도록 spec 설정
        mock_loader_thread = MagicMock(spec=ImageLoaderThread) 
        mock_loader_thread.isRunning.return_value = True
        
        # 실제 코드에서처럼 image_filename을 키로 사용
        key_for_thread = sample_furniture.image_filename
        furniture_table_model.loading_threads[key_for_thread] = mock_loader_thread
        
        strong_ref_pixmap = QPixmap()
        # thumbnail_cache는 clear_furniture에서 .clear()되므로, 
        # 여기에 아이템 추가는 테스트 자체의 성공/실패에 큰 영향은 없습니다.
        # 다만, clear_furniture 호출 전 상태를 명확히 하기 위해 추가합니다.
        furniture_table_model.thumbnail_cache['dummy_cache_key_for_test'] = strong_ref_pixmap

    # clear_furniture 호출 전 상태 확인
    assert furniture_table_model.rowCount() == 1, "rowCount should be 1 before clear"
    assert len(furniture_table_model.loading_threads) == 1, "loading_threads should have 1 item before clear"
    # loading_threads에 우리가 넣은 mock 객체가 있는지 확인
    assert furniture_table_model.loading_threads.get(key_for_thread) == mock_loader_thread, "mock_loader_thread not found in loading_threads"
    assert len(furniture_table_model.thumbnail_cache) == 1, "thumbnail_cache should have 1 item before clear"

    # 테스트 대상 메소드 호출
    furniture_table_model.clear_furniture()
    
    # clear_furniture 호출 후 상태 확인
    assert furniture_table_model.rowCount() == 0, "rowCount should be 0 after clear"
    assert len(furniture_table_model.furniture_items) == 0, "furniture_items should be empty after clear"
    assert len(furniture_table_model.thumbnail_cache) == 0, "thumbnail_cache should be empty after clear"
    # clear_furniture() 내부에서 self.loading_threads.clear()가 호출되므로 최종적으로 0이 됩니다.
    assert len(furniture_table_model.loading_threads) == 0, "loading_threads should be empty after clear" 
    
    # mock_loader_thread의 메소드 호출 검증
    mock_loader_thread.terminate.assert_called_once()
    mock_loader_thread.wait.assert_called_once()