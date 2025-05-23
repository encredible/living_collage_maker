import json
import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from src.services.app_state_service import (
    AppStateService, AppState, WindowState, ColumnWidthState, 
    CanvasState, PanelState, FurnitureItemState
)


@pytest.fixture
def temp_cache_dir():
    """임시 캐시 디렉토리를 생성합니다."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def app_state_service(temp_cache_dir):
    """테스트용 AppStateService를 생성합니다."""
    with patch('src.services.app_state_service.user_cache_dir', return_value=temp_cache_dir):
        service = AppStateService()
        yield service


@pytest.fixture
def sample_app_state():
    """테스트용 샘플 AppState를 생성합니다."""
    return AppState(
        window=WindowState(width=1400, height=900, x=200, y=150),
        column_widths=ColumnWidthState(
            explorer_panel={0: 120, 1: 150, 2: 250, 3: 120},
            bottom_panel={0: 350, 1: 140, 2: 90, 3: 110}
        ),
        canvas=CanvasState(width=1000, height=700),
        panels=PanelState(
            horizontal_splitter_sizes=[900, 500],
            vertical_splitter_sizes=[800, 200]
        ),
        furniture_items=[
            FurnitureItemState(
                furniture_id="test-furniture-1",
                position_x=100,
                position_y=150,
                width=200,
                height=180,
                z_order=0,
                is_flipped=False,
                color_temperature=5500,
                brightness=110,
                saturation=90
            ),
            FurnitureItemState(
                furniture_id="test-furniture-2",
                position_x=300,
                position_y=250,
                width=150,
                height=120,
                z_order=1,
                is_flipped=True,
                color_temperature=7000,
                brightness=95,
                saturation=105
            )
        ]
    )


class TestAppStateService:
    """AppStateService 테스트 클래스"""
    
    def test_initialization(self, app_state_service, temp_cache_dir):
        """AppStateService 초기화 테스트"""
        assert app_state_service.cache_dir == temp_cache_dir
        assert app_state_service.state_file_path == os.path.join(temp_cache_dir, "app_state.json")
        assert os.path.exists(temp_cache_dir)
    
    def test_save_app_state_success(self, app_state_service, sample_app_state):
        """앱 상태 저장 성공 테스트"""
        result = app_state_service.save_app_state(sample_app_state)
        
        assert result is True
        assert os.path.exists(app_state_service.state_file_path)
        
        # 저장된 파일 내용 확인
        with open(app_state_service.state_file_path, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert saved_data['window']['width'] == 1400
        assert saved_data['window']['height'] == 900
        assert saved_data['canvas']['width'] == 1000
        assert saved_data['canvas']['height'] == 700
        assert len(saved_data['furniture_items']) == 2
        assert saved_data['furniture_items'][0]['furniture_id'] == "test-furniture-1"
        assert saved_data['furniture_items'][1]['is_flipped'] is True
    
    def test_save_app_state_error_handling(self, app_state_service):
        """앱 상태 저장 오류 처리 테스트"""
        # 읽기 전용 디렉토리로 변경하여 저장 실패 시뮬레이션
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            result = app_state_service.save_app_state(AppState())
            assert result is False
    
    def test_load_app_state_no_file(self, app_state_service):
        """저장된 파일이 없을 때 앱 상태 불러오기 테스트"""
        app_state = app_state_service.load_app_state()
        
        # 기본값이 반환되어야 함
        assert isinstance(app_state, AppState)
        assert app_state.window.width == 1200
        assert app_state.window.height == 800
        assert app_state.canvas.width == 800
        assert app_state.canvas.height == 600
        assert len(app_state.furniture_items) == 0
    
    def test_load_app_state_success(self, app_state_service, sample_app_state):
        """앱 상태 불러오기 성공 테스트"""
        # 먼저 상태 저장
        app_state_service.save_app_state(sample_app_state)
        
        # 상태 불러오기
        loaded_state = app_state_service.load_app_state()
        
        assert isinstance(loaded_state, AppState)
        assert loaded_state.window.width == 1400
        assert loaded_state.window.height == 900
        assert loaded_state.canvas.width == 1000
        assert loaded_state.canvas.height == 700
        assert len(loaded_state.furniture_items) == 2
        
        # 가구 아이템 상세 확인
        furniture_1 = loaded_state.furniture_items[0]
        assert furniture_1.furniture_id == "test-furniture-1"
        assert furniture_1.position_x == 100
        assert furniture_1.position_y == 150
        assert furniture_1.is_flipped is False
        assert furniture_1.color_temperature == 5500
        
        furniture_2 = loaded_state.furniture_items[1]
        assert furniture_2.furniture_id == "test-furniture-2"
        assert furniture_2.is_flipped is True
        assert furniture_2.color_temperature == 7000
    
    def test_load_app_state_corrupted_file(self, app_state_service):
        """손상된 파일 불러오기 테스트"""
        # 손상된 JSON 파일 생성
        with open(app_state_service.state_file_path, 'w') as f:
            f.write("invalid json content {")
        
        # 기본값이 반환되어야 함
        app_state = app_state_service.load_app_state()
        assert isinstance(app_state, AppState)
        assert app_state.window.width == 1200  # 기본값
    
    def test_clear_app_state(self, app_state_service, sample_app_state):
        """앱 상태 삭제 테스트"""
        # 먼저 상태 저장
        app_state_service.save_app_state(sample_app_state)
        assert os.path.exists(app_state_service.state_file_path)
        
        # 상태 삭제
        result = app_state_service.clear_app_state()
        assert result is True
        assert not os.path.exists(app_state_service.state_file_path)
    
    def test_clear_app_state_no_file(self, app_state_service):
        """삭제할 파일이 없을 때 테스트"""
        result = app_state_service.clear_app_state()
        assert result is True  # 파일이 없어도 성공으로 처리


class TestDataClasses:
    """데이터 클래스들의 테스트"""
    
    def test_window_state_defaults(self):
        """WindowState 기본값 테스트"""
        state = WindowState()
        assert state.width == 1200
        assert state.height == 800
        assert state.x == 100
        assert state.y == 100
    
    def test_column_width_state_defaults(self):
        """ColumnWidthState 기본값 테스트"""
        state = ColumnWidthState()
        assert len(state.explorer_panel) == 4
        assert len(state.bottom_panel) == 13
        assert state.explorer_panel[0] == 100  # 썸네일
        assert state.bottom_panel[0] == 300     # 이름
    
    def test_canvas_state_defaults(self):
        """CanvasState 기본값 테스트"""
        state = CanvasState()
        assert state.width == 800
        assert state.height == 600
    
    def test_panel_state_defaults(self):
        """PanelState 기본값 테스트"""
        state = PanelState()
        assert state.horizontal_splitter_sizes == [800, 400]
        assert state.vertical_splitter_sizes == [700, 100]
    
    def test_furniture_item_state(self):
        """FurnitureItemState 테스트"""
        state = FurnitureItemState(
            furniture_id="test-id",
            position_x=50,
            position_y=75,
            width=200,
            height=150
        )
        assert state.furniture_id == "test-id"
        assert state.position_x == 50
        assert state.position_y == 75
        assert state.z_order == 0  # 기본값
        assert state.is_flipped is False  # 기본값
        assert state.color_temperature == 6500  # 기본값
    
    def test_app_state_defaults(self):
        """AppState 기본값 테스트"""
        state = AppState()
        assert isinstance(state.window, WindowState)
        assert isinstance(state.column_widths, ColumnWidthState)
        assert isinstance(state.canvas, CanvasState)
        assert isinstance(state.panels, PanelState)
        assert state.furniture_items == [] 