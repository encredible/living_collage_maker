import os
import tempfile
from unittest.mock import patch, MagicMock, mock_open

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QFileDialog, QWidget

from src.models.furniture import Furniture
from src.services.html_export_service import HtmlExportService
from src.ui.canvas import FurnitureItem


@pytest.fixture
def html_export_service(qtbot):
    """HTML 내보내기 서비스 픽스처"""
    service = HtmlExportService()
    return service


@pytest.fixture
def mock_furniture_data():
    """테스트용 가구 데이터"""
    return {
        "id": "test-furniture-001",
        "name": "테스트 소파",
        "brand": "테스트브랜드",
        "type": "소파",
        "price": 500000,
        "description": "편안한 테스트 소파입니다.",
        "color": "베이지",
        "width": 200,
        "depth": 90,
        "height": 80,
        "seat_height": 45,
        "locations": ["거실", "침실"],
        "styles": ["모던", "미니멀"],
        "link": "https://example.com/sofa",
        "image_filename": "test_sofa.png",
        "author": "test_author",
        "created_at": "2023-01-01"
    }


@pytest.fixture
def mock_furniture_item(mock_furniture_data, qtbot, mocker):
    """테스트용 가구 아이템"""
    furniture = Furniture(**mock_furniture_data)
    
    # FurnitureItem의 의존성들을 모킹
    mocker.patch('src.services.supabase_client.SupabaseClient')
    mocker.patch('src.services.image_service.ImageService')
    mock_load_image = mocker.patch.object(FurnitureItem, 'load_image')
    dummy_pixmap = QPixmap(100, 100)
    dummy_pixmap.fill(Qt.GlobalColor.blue)
    mock_load_image.return_value = dummy_pixmap
    
    # 실제 QWidget을 부모로 사용
    parent_widget = QWidget()
    qtbot.addWidget(parent_widget)
    
    item = FurnitureItem(furniture, parent=parent_widget)
    
    return item


@patch('src.services.html_export_service.QFileDialog.getSaveFileName')
@patch('builtins.open', new_callable=mock_open)
def test_export_collage_to_html_successful(
    mock_builtin_open, mock_get_save_file_name, html_export_service, 
    mock_furniture_item, qtbot, mocker
):
    """HTML 내보내기 성공 테스트"""
    # 파일 저장 경로 설정
    test_save_path = "/fake/path/to/test_collage.html"
    mock_get_save_file_name.return_value = (test_save_path, "HTML 파일 (*.html)")
    
    # Canvas 위젯 모킹
    mock_canvas = MagicMock()
    mock_canvas._generate_collage_image.return_value = QPixmap(800, 600)
    
    # 메시지 박스 모킹
    mock_info_msg = mocker.patch.object(html_export_service, '_show_information_message')
    
    # QPixmap.save 모킹
    with patch('PyQt6.QtGui.QPixmap.save', return_value=True):
        html_export_service.export_collage_to_html(
            canvas_widget=mock_canvas,
            furniture_items=[mock_furniture_item],
            parent_window=None
        )
    
    # 검증
    mock_get_save_file_name.assert_called_once()
    mock_canvas._generate_collage_image.assert_called_once()
    mock_builtin_open.assert_called_once_with(test_save_path, 'w', encoding='utf-8')
    mock_info_msg.assert_called_once()


@patch('src.services.html_export_service.QFileDialog.getSaveFileName')
def test_export_collage_to_html_no_items(
    mock_get_save_file_name, html_export_service, mocker
):
    """가구 아이템이 없을 때 경고 메시지 테스트"""
    mock_canvas = MagicMock()
    mock_warning_msg = mocker.patch.object(html_export_service, '_show_warning_message')
    
    html_export_service.export_collage_to_html(
        canvas_widget=mock_canvas,
        furniture_items=[],
        parent_window=None
    )
    
    mock_warning_msg.assert_called_once_with(None, "경고", "내보낼 콜라주가 없습니다.")
    mock_get_save_file_name.assert_not_called()


@patch('src.services.html_export_service.QFileDialog.getSaveFileName')
def test_export_collage_to_html_cancelled_dialog(
    mock_get_save_file_name, html_export_service, mock_furniture_item, mocker
):
    """파일 저장 다이얼로그 취소 테스트"""
    mock_get_save_file_name.return_value = ("", "")  # 취소
    mock_canvas = MagicMock()
    
    mock_builtin_open = mocker.patch('builtins.open', new_callable=mock_open)
    mock_info_msg = mocker.patch.object(html_export_service, '_show_information_message')
    
    html_export_service.export_collage_to_html(
        canvas_widget=mock_canvas,
        furniture_items=[mock_furniture_item],
        parent_window=None
    )
    
    mock_get_save_file_name.assert_called_once()
    mock_builtin_open.assert_not_called()
    mock_info_msg.assert_not_called()


@patch('src.services.html_export_service.QFileDialog.getSaveFileName')
@patch('builtins.open', new_callable=mock_open)
def test_export_collage_to_html_image_save_failure(
    mock_builtin_open, mock_get_save_file_name, html_export_service, 
    mock_furniture_item, mocker
):
    """이미지 저장 실패 테스트"""
    test_save_path = "/fake/path/to/test_collage.html"
    mock_get_save_file_name.return_value = (test_save_path, "HTML 파일 (*.html)")
    
    mock_canvas = MagicMock()
    mock_canvas._generate_collage_image.return_value = QPixmap(800, 600)
    
    mock_critical_msg = mocker.patch.object(html_export_service, '_show_critical_message')
    
    # QPixmap.save가 False를 반환하도록 설정 (저장 실패)
    with patch('PyQt6.QtGui.QPixmap.save', return_value=False):
        html_export_service.export_collage_to_html(
            canvas_widget=mock_canvas,
            furniture_items=[mock_furniture_item],
            parent_window=None
        )
    
    mock_critical_msg.assert_called_once_with(None, "오류", "콜라주 이미지 저장에 실패했습니다.")
    mock_builtin_open.assert_not_called()


def test_generate_html_content(html_export_service, mock_furniture_item):
    """HTML 콘텐츠 생성 테스트"""
    html_content = html_export_service._generate_html_content([mock_furniture_item], "test_image.png")
    
    # HTML 기본 구조 확인
    assert "<!DOCTYPE html>" in html_content
    assert "<html lang=\"ko\">" in html_content
    assert "Living Collage" in html_content
    assert "test_image.png" in html_content
    
    # 가구 정보 확인
    assert "테스트 소파" in html_content
    assert "테스트브랜드" in html_content
    assert "500,000원" in html_content
    assert "가로 200mm" in html_content  # mm 단위 그대로 사용
    assert "좌석높이:" in html_content and "45mm" in html_content  # mm 단위 그대로 사용
    assert "제품 바로가기" in html_content
    assert "https://example.com/sofa" in html_content
    
    # 제거된 정보들이 없는지 확인
    assert "베이지" not in html_content  # 색상 정보 제거됨
    assert "거실, 침실" not in html_content  # 위치 정보 제거됨
    assert "모던, 미니멀" not in html_content  # 스타일 정보 제거됨


def test_generate_link_info_with_link(html_export_service):
    """링크가 있는 경우 링크 정보 생성 테스트"""
    link_html = html_export_service._generate_link_info("https://example.com/product")
    
    assert '<a href="https://example.com/product" target="_blank">제품 바로가기</a>' in link_html


def test_generate_link_info_without_link(html_export_service):
    """링크가 없는 경우 링크 정보 생성 테스트"""
    link_html = html_export_service._generate_link_info("")
    
    assert '<span class="no-link">링크 없음</span>' in link_html


def test_generate_size_info(html_export_service):
    """크기 정보 생성 테스트"""
    furniture = Furniture(
        id="test", name="test", brand="test", type="test", price=1000,
        image_filename="test.png", width=100, depth=50, height=80, seat_height=45
    )
    
    size_html = html_export_service._generate_size_info(furniture)
    
    assert "가로 100mm" in size_html  # mm 단위 그대로 사용
    assert "세로 50mm" in size_html   # mm 단위 그대로 사용
    assert "높이 80mm" in size_html   # mm 단위 그대로 사용
    assert "좌석높이:" in size_html
    assert "45mm" in size_html        # mm 단위 그대로 사용


def test_generate_size_info_no_dimensions(html_export_service):
    """크기 정보가 없는 경우 테스트"""
    furniture = Furniture(
        id="test", name="test", brand="test", type="test", price=1000,
        image_filename="test.png", width=0, depth=0, height=0, seat_height=None
    )
    
    size_html = html_export_service._generate_size_info(furniture)
    
    assert size_html == ""


def test_generate_list_info_with_items(html_export_service):
    """리스트 정보가 있는 경우 테스트"""
    list_html = html_export_service._generate_list_info("위치", ["거실", "침실", "서재"])
    
    assert "위치:" in list_html
    assert "거실, 침실, 서재" in list_html


def test_generate_list_info_empty_list(html_export_service):
    """리스트가 비어있는 경우 테스트"""
    list_html = html_export_service._generate_list_info("위치", [])
    
    assert list_html == ""


def test_generate_optional_info_with_value(html_export_service):
    """선택적 정보가 있는 경우 테스트"""
    info_html = html_export_service._generate_optional_info("설명", "편안한 소파입니다.")
    
    assert "설명:" in info_html
    assert "편안한 소파입니다." in info_html


def test_generate_optional_info_empty_value(html_export_service):
    """선택적 정보가 비어있는 경우 테스트"""
    info_html = html_export_service._generate_optional_info("설명", "")
    
    assert info_html == ""


def test_save_collage_image_success(html_export_service, mocker):
    """콜라주 이미지 저장 성공 테스트"""
    mock_canvas = MagicMock()
    test_pixmap = QPixmap(100, 100)
    mock_canvas._generate_collage_image.return_value = test_pixmap
    
    with patch.object(test_pixmap, 'save', return_value=True) as mock_save:
        result = html_export_service._save_collage_image(mock_canvas, "/fake/path/image.png")
    
    assert result is True
    mock_canvas._generate_collage_image.assert_called_once()
    mock_save.assert_called_once_with("/fake/path/image.png", "PNG")


def test_save_collage_image_failure(html_export_service, mocker):
    """콜라주 이미지 저장 실패 테스트"""
    mock_canvas = MagicMock()
    test_pixmap = QPixmap(100, 100)
    mock_canvas._generate_collage_image.return_value = test_pixmap
    
    with patch.object(test_pixmap, 'save', return_value=False) as mock_save:
        result = html_export_service._save_collage_image(mock_canvas, "/fake/path/image.png")
    
    assert result is False
    mock_save.assert_called_once_with("/fake/path/image.png", "PNG")


def test_css_styles_content(html_export_service):
    """CSS 스타일 내용 테스트"""
    css_content = html_export_service._get_css_styles()
    
    # 주요 CSS 클래스들이 포함되어 있는지 확인
    assert ".container" in css_content
    assert ".collage-image" in css_content
    assert ".furniture-card" in css_content
    assert ".furniture-list" in css_content
    assert "background-color" in css_content
    assert "border" in css_content 