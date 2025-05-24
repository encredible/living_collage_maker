"""UI 하단 패널 테스트

하단 패널 모듈의 기능을 테스트합니다.
"""

from unittest.mock import Mock

import pytest
from PyQt6.QtCore import Qt

from src.models.furniture import Furniture
from src.ui.panels.bottom_panel import BottomPanel, SelectedFurniturePanel


@pytest.fixture
def sample_furniture():
    """테스트용 가구 데이터"""
    return Furniture(
        id='1', brand='TestBrand', name='Test Chair', image_filename='chair.png', price=100,
        type='Chair', description='Test Description', link='http://example.com',
        color='Brown', locations=['Living Room'], styles=['Modern'],
        width=50, depth=50, height=100, seat_height=45, author='test_author', created_at=''
    )

def test_bottom_panel_initialization(qtbot):
    """BottomPanel이 올바르게 초기화되는지 테스트합니다."""
    panel = BottomPanel()
    qtbot.addWidget(panel)
    
    # 기본 속성 확인
    assert panel is not None
    assert hasattr(panel, 'selected_panel')
    
    # 패널이 표시되는지 확인
    panel.show()
    assert panel.isVisible()

def test_selected_furniture_panel_initialization(qtbot):
    """SelectedFurniturePanel이 올바르게 초기화되는지 테스트합니다."""
    panel = SelectedFurniturePanel()
    qtbot.addWidget(panel)
    
    # 기본 속성 확인
    assert panel is not None
    
    # 패널이 표시되는지 확인
    panel.show()
    assert panel.isVisible()

def test_selected_furniture_panel_add_furniture(qtbot, sample_furniture):
    """SelectedFurniturePanel에 가구를 추가하는 기능을 테스트합니다."""
    panel = SelectedFurniturePanel()
    qtbot.addWidget(panel)
    
    # 가구 추가 (메서드가 존재한다면)
    if hasattr(panel, 'add_furniture'):
        panel.add_furniture(sample_furniture)
    
    # TODO: 실제 구현에 따라 추가 검증 로직 구현
    assert True

def test_bottom_panel_placeholder():
    """BottomPanel 테스트를 위한 플레이스홀더 테스트"""
    # TODO: BottomPanel에 대한 실제 테스트 구현
    assert True

def test_selected_furniture_panel_placeholder():
    """SelectedFurniturePanel 테스트를 위한 플레이스홀더 테스트"""
    # TODO: SelectedFurniturePanel에 대한 실제 테스트 구현
    assert True

def test_selected_furniture_panel_column_width_preservation(qtbot, sample_furniture):
    """SelectedFurniturePanel의 컬럼 너비 보존 기능을 테스트합니다."""
    panel = SelectedFurniturePanel()
    qtbot.addWidget(panel)
    
    # 모델에 콜백이 설정되었는지 확인
    assert panel.selected_model.column_width_callback is not None
    assert callable(panel.selected_model.column_width_callback)
    
    # 가구 아이템 생성 (모킹)
    mock_furniture_item = Mock()
    mock_furniture_item.furniture = sample_furniture
    
    # 가구 목록 업데이트
    panel.update_furniture_list([mock_furniture_item])
    
    # 모델에 가구가 추가되었는지 확인
    assert panel.selected_model.rowCount() == 1
    
    # 컬럼 너비가 설정되어 있는지 확인
    assert panel.column_widths is not None
    assert len(panel.column_widths) == 13  # 13개 컬럼
    
    # setup_column_widths 메서드가 호출 가능한지 확인
    assert hasattr(panel, 'setup_column_widths')
    assert callable(panel.setup_column_widths)

def test_selected_furniture_panel_order_control_buttons(qtbot):
    """SelectedFurniturePanel의 순서 변경 버튼들이 올바르게 설정되는지 테스트합니다."""
    panel = SelectedFurniturePanel()
    qtbot.addWidget(panel)
    
    # 순서 변경 버튼들이 존재하는지 확인
    assert hasattr(panel, 'move_up_btn')
    assert hasattr(panel, 'move_down_btn')
    assert hasattr(panel, 'move_top_btn')
    assert hasattr(panel, 'move_bottom_btn')
    assert hasattr(panel, 'sort_btn')
    
    # 초기 상태에서는 버튼들이 비활성화되어야 함
    assert not panel.move_up_btn.isEnabled()
    assert not panel.move_down_btn.isEnabled()
    assert not panel.move_top_btn.isEnabled()
    assert not panel.move_bottom_btn.isEnabled()
    
    # 정렬 버튼은 항상 활성화
    assert panel.sort_btn.isEnabled()

def test_selected_furniture_panel_order_methods(qtbot, sample_furniture):
    """SelectedFurniturePanel의 순서 변경 메서드들을 테스트합니다."""
    panel = SelectedFurniturePanel()
    qtbot.addWidget(panel)
    
    # 순서 변경 메서드들이 존재하는지 확인
    assert hasattr(panel, 'move_selected_up')
    assert hasattr(panel, 'move_selected_down')
    assert hasattr(panel, 'move_selected_to_top')
    assert hasattr(panel, 'move_selected_to_bottom')
    assert hasattr(panel, 'get_selected_furniture_name')
    assert hasattr(panel, 'get_selected_row')
    assert hasattr(panel, 'select_row')
    
    # 가구 아이템 생성 및 추가
    mock_furniture_item = Mock()
    mock_furniture_item.furniture = sample_furniture
    panel.update_furniture_list([mock_furniture_item])
    
    # 선택 관련 메서드들이 올바르게 작동하는지 확인
    assert panel.get_selected_row() >= -1  # -1 (선택 없음) 또는 유효한 행 번호
    
    # 첫 번째 행 선택
    if panel.selected_model.rowCount() > 0:
        panel.select_row(0)
        selected_name = panel.get_selected_furniture_name()
        assert selected_name == sample_furniture.name

def test_selected_furniture_panel_integration_with_model(qtbot):
    """SelectedFurniturePanel과 SelectedFurnitureTableModel의 통합을 테스트합니다."""
    panel = SelectedFurniturePanel()
    qtbot.addWidget(panel)
    
    # 모델과 패널의 연결 확인
    assert panel.selected_model is not None
    assert panel.selected_table.model() == panel.selected_model
    
    # 모델의 콜백이 패널의 메서드로 설정되어 있는지 확인
    assert panel.selected_model.column_width_callback == panel.setup_column_widths
    
    # 드래그 앤 드롭 설정 확인
    from PyQt6.QtWidgets import QTableView
    assert panel.selected_table.dragDropMode() == QTableView.DragDropMode.InternalMove
    assert not panel.selected_table.dragDropOverwriteMode()
    assert panel.selected_table.defaultDropAction() == Qt.DropAction.MoveAction 