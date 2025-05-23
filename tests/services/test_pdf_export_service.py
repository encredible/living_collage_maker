import os
import tempfile
from unittest.mock import MagicMock, patch, mock_open
import pytest
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QWidget
from io import BytesIO
from PyQt6.QtCore import QBuffer
from PyQt6.QtGui import QImageWriter

from src.services.pdf_export_service import PdfExportService, REPORTLAB_AVAILABLE, REPORTLAB_ERROR
from src.models.furniture import Furniture
from src.ui.canvas import FurnitureItem


@pytest.fixture
def pdf_export_service():
    """PdfExportService 인스턴스를 생성합니다."""
    return PdfExportService()


@pytest.fixture
def mock_furniture_item(qtbot):
    """테스트용 모킹된 가구 아이템을 생성합니다."""
    furniture = Furniture(
        id="test_sofa",
        name="테스트 소파",
        brand="테스트브랜드", 
        type="소파",
        price=500000,
        image_filename="test_sofa.jpg",
        description="편안한 테스트 소파",
        width=200,
        depth=100,
        height=85,
        seat_height=45,
        link="https://example.com/sofa"
    )
    
    # FurnitureItem은 실제 QWidget 부모가 필요함
    parent_widget = QWidget()
    qtbot.addWidget(parent_widget)
    
    item = FurnitureItem(furniture, parent_widget)
    return item


@patch('src.services.pdf_export_service.REPORTLAB_AVAILABLE', False)
@patch('src.services.pdf_export_service.REPORTLAB_ERROR', "테스트용 reportlab 오류")
def test_export_collage_to_pdf_reportlab_not_available(pdf_export_service, mocker):
    """reportlab이 설치되지 않았을 때 테스트"""
    mock_show_critical = mocker.patch.object(pdf_export_service, '_show_critical_message')
    
    pdf_export_service.export_collage_to_pdf(None, [], None)
    
    mock_show_critical.assert_called_once_with(
        None,
        "라이브러리 필요",
        "테스트용 reportlab 오류"
    )


@patch('src.services.pdf_export_service.REPORTLAB_AVAILABLE', True)
def test_export_collage_to_pdf_no_items(pdf_export_service, mocker):
    """가구 아이템이 없을 때 테스트"""
    mock_show_warning = mocker.patch.object(pdf_export_service, '_show_warning_message')
    
    pdf_export_service.export_collage_to_pdf(None, [], None)
    
    mock_show_warning.assert_called_once_with(None, "경고", "내보낼 콜라주가 없습니다.")


@patch('src.services.pdf_export_service.QFileDialog.getSaveFileName')
def test_export_collage_to_pdf_dialog_cancelled(mock_get_save_file_name, pdf_export_service, mock_furniture_item):
    """파일 저장 다이얼로그에서 취소한 경우 테스트"""
    mock_get_save_file_name.return_value = ("", "")  # 취소 시 빈 문자열 반환
    
    result = pdf_export_service.export_collage_to_pdf(None, [mock_furniture_item], None)
    
    assert result is None


@patch('src.services.pdf_export_service.QFileDialog.getSaveFileName')
def test_export_collage_to_pdf_generation_failure(
    mock_get_save_file_name, pdf_export_service, mock_furniture_item, mocker
):
    """PDF 생성 실패 테스트"""
    mock_get_save_file_name.return_value = ("/fake/path/test.pdf", "PDF 파일 (*.pdf)")
    mock_show_critical = mocker.patch.object(pdf_export_service, '_show_critical_message')
    
    # PDF 생성 실패 모킹
    mocker.patch.object(pdf_export_service, '_generate_pdf', return_value=False)
    
    pdf_export_service.export_collage_to_pdf(None, [mock_furniture_item], None)
    
    mock_show_critical.assert_called_once_with(None, "오류", "PDF 생성에 실패했습니다.")


@patch('src.services.pdf_export_service.QFileDialog.getSaveFileName')
def test_export_collage_to_pdf_successful(
    mock_get_save_file_name, pdf_export_service, mock_furniture_item, mocker
):
    """PDF 내보내기 성공 테스트"""
    test_save_path = "/fake/path/to/test_collage.pdf"
    mock_get_save_file_name.return_value = (test_save_path, "PDF 파일 (*.pdf)")
    
    mock_show_info = mocker.patch.object(pdf_export_service, '_show_information_message')
    
    # PDF 생성 성공으로 모킹
    mocker.patch.object(pdf_export_service, '_generate_pdf', return_value=True)
    
    # export_finished 시그널 직접 모킹
    with patch.object(pdf_export_service, 'export_finished') as mock_signal:
        pdf_export_service.export_collage_to_pdf(None, [mock_furniture_item], None)
        mock_signal.emit.assert_called_once_with(True, "PDF 내보내기 성공")
    
    mock_show_info.assert_called_once_with(None, "성공", f"PDF 파일이 성공적으로 저장되었습니다.\n{test_save_path}")


def test_export_collage_to_pdf_exception_handling(pdf_export_service, mock_furniture_item, mocker):
    """예외 처리 테스트"""
    mock_show_critical = mocker.patch.object(pdf_export_service, '_show_critical_message')
    
    # QFileDialog.getSaveFileName에서 예외 발생
    with patch('src.services.pdf_export_service.QFileDialog.getSaveFileName', side_effect=Exception("테스트 예외")):
        # export_finished 시그널 직접 모킹
        with patch.object(pdf_export_service, 'export_finished') as mock_signal:
            pdf_export_service.export_collage_to_pdf(None, [mock_furniture_item], None)
            mock_signal.emit.assert_called_once_with(False, "PDF 내보내기 중 오류가 발생했습니다: 테스트 예외")
    
    mock_show_critical.assert_called_once()


@pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab 라이브러리가 필요합니다")
def test_generate_pdf_success(pdf_export_service, mock_furniture_item, mocker):
    """PDF 생성 성공 테스트 (reportlab 사용 가능한 경우)"""
    from reportlab.platypus import SimpleDocTemplate
    from io import BytesIO
    
    mock_canvas = MagicMock()
    mock_doc = MagicMock()
    
    # 이미지 데이터 생성 모킹
    mock_image_data = BytesIO(b"fake_image_data")
    mocker.patch.object(pdf_export_service, '_get_collage_image_data', return_value=mock_image_data)
    
    with patch('src.services.pdf_export_service.SimpleDocTemplate', return_value=mock_doc) as mock_simple_doc:
        result = pdf_export_service._generate_pdf(mock_canvas, [mock_furniture_item], "/temp/test.pdf")
    
    assert result is True
    mock_simple_doc.assert_called_once()
    mock_doc.build.assert_called_once()


def test_generate_pdf_exception(pdf_export_service, mock_furniture_item, mocker):
    """PDF 생성 예외 테스트"""
    mock_canvas = MagicMock()
    
    with patch('src.services.pdf_export_service.SimpleDocTemplate', side_effect=Exception("PDF 생성 오류")):
        result = pdf_export_service._generate_pdf(mock_canvas, [mock_furniture_item], "/temp/test.pdf")
    
    assert result is False


def test_show_information_message(pdf_export_service, mocker):
    """정보 메시지 표시 테스트"""
    with patch('PyQt6.QtWidgets.QMessageBox.information') as mock_info:
        pdf_export_service._show_information_message(None, "제목", "메시지")
        mock_info.assert_called_once_with(None, "제목", "메시지")


def test_show_warning_message(pdf_export_service, mocker):
    """경고 메시지 표시 테스트"""
    with patch('PyQt6.QtWidgets.QMessageBox.warning') as mock_warning:
        pdf_export_service._show_warning_message(None, "제목", "메시지")
        mock_warning.assert_called_once_with(None, "제목", "메시지")


def test_show_critical_message(pdf_export_service, mocker):
    """오류 메시지 표시 테스트"""
    with patch('PyQt6.QtWidgets.QMessageBox.critical') as mock_critical:
        pdf_export_service._show_critical_message(None, "제목", "메시지")
        mock_critical.assert_called_once_with(None, "제목", "메시지")


def test_get_collage_image_data_success(pdf_export_service, mocker):
    """콜라주 이미지 데이터 생성 성공 테스트"""
    mock_canvas = MagicMock()
    mock_pixmap = MagicMock()
    mock_image = MagicMock()
    mock_buffer = MagicMock(spec=QBuffer)
    mock_writer = MagicMock(spec=QImageWriter)
    
    # Canvas와 Pixmap 모킹
    mock_canvas._generate_collage_image.return_value = mock_pixmap
    mock_pixmap.toImage.return_value = mock_image
    
    # QBuffer와 QImageWriter 모킹
    with patch('PyQt6.QtCore.QBuffer', return_value=mock_buffer):
        with patch('PyQt6.QtGui.QImageWriter', return_value=mock_writer):
            mock_buffer.open.return_value = True
            mock_writer.write.return_value = True
            mock_buffer.data.return_value = b"fake_image_data"
            mock_buffer.seek.return_value = True
            
            result = pdf_export_service._get_collage_image_data(mock_canvas)
    
    assert isinstance(result, BytesIO)
    mock_canvas._generate_collage_image.assert_called_once()
    mock_pixmap.toImage.assert_called_once()


def test_get_collage_image_data_failure(pdf_export_service, mocker):
    """콜라주 이미지 데이터 생성 실패 테스트"""
    mock_canvas = MagicMock()
    mock_pixmap = MagicMock()
    mock_image = MagicMock()
    mock_buffer = MagicMock(spec=QBuffer)
    mock_writer = MagicMock(spec=QImageWriter)
    
    # Canvas와 Pixmap 모킹
    mock_canvas._generate_collage_image.return_value = mock_pixmap
    mock_pixmap.toImage.return_value = mock_image
    
    # QImageWriter.write가 실패하도록 모킹
    with patch('PyQt6.QtCore.QBuffer', return_value=mock_buffer):
        with patch('PyQt6.QtGui.QImageWriter', return_value=mock_writer):
            mock_buffer.open.return_value = True
            mock_writer.write.return_value = False  # 실패
            
            result = pdf_export_service._get_collage_image_data(mock_canvas)
    
    assert result is None
    mock_buffer.close.assert_called_once()


def test_get_collage_image_data_exception(pdf_export_service, mocker):
    """콜라주 이미지 데이터 생성 예외 테스트"""
    mock_canvas = MagicMock()
    mock_canvas._generate_collage_image.side_effect = Exception("테스트 예외")
    
    result = pdf_export_service._get_collage_image_data(mock_canvas)
    
    assert result is None 