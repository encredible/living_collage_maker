import pytest
from PyQt6.QtWidgets import QApplication, QPushButton, QDialog
from unittest.mock import MagicMock

from src.ui.dialogs import CanvasSizeDialog

@pytest.fixture
def dialog(qtbot):
    """테스트용 CanvasSizeDialog 인스턴스를 생성합니다."""
    # QApplication 인스턴스가 이미 있는지 확인 (없으면 생성 - tests/conftest.py에서 처리)
    # if QApplication.instance() is None:
    #     QApplication([]) # QApplication 인스턴스가 없으면 생성
        
    d = CanvasSizeDialog()
    qtbot.addWidget(d)
    return d

def test_canvas_size_dialog_initial_values(dialog):
    """다이얼로그 생성 시 스핀박스의 초기값을 테스트합니다."""
    assert dialog.width_spin.value() == 800
    assert dialog.height_spin.value() == 600
    assert dialog.width_spin.minimum() == 400
    assert dialog.width_spin.maximum() == 2000
    assert dialog.height_spin.minimum() == 300
    assert dialog.height_spin.maximum() == 1500

def test_canvas_size_dialog_get_size(dialog):
    """get_size 메소드가 현재 스핀박스 값을 올바르게 반환하는지 테스트합니다."""
    dialog.width_spin.setValue(1000)
    dialog.height_spin.setValue(700)
    width, height = dialog.get_size()
    assert width == 1000
    assert height == 700

def test_canvas_size_dialog_accept_values(dialog, qtbot):
    """확인 버튼 클릭 시 (accept) 올바른 값을 반환하고 다이얼로그가 올바르게 종료되는지 테스트합니다."""
    dialog.width_spin.setValue(1200)
    dialog.height_spin.setValue(900)
    
    # dialog.accept는 여전히 모킹하여 호출 여부 확인 가능 (선택 사항)
    dialog.accept = MagicMock(wraps=dialog.accept)
    # dialog.done = MagicMock() # 이 라인 제거
    
    buttons = dialog.findChildren(QPushButton)
    ok_button_found = None
    for btn in buttons:
        if btn.text() == "확인":
            ok_button_found = btn
            break
    
    assert ok_button_found is not None, """"확인" 버튼을 찾을 수 없습니다."""
    
    # 버튼 클릭 전에 result() 값은 0일 수 있음 (또는 이전 상태)
    # print(f"Before click (accept): {dialog.result()}")

    ok_button_found.clicked.emit() # accept() 슬롯 호출 -> done(Accepted) 호출
    
    dialog.accept.assert_called_once() # accept 호출 확인
    assert dialog.result() == QDialog.DialogCode.Accepted # result() 값 확인

    # 다이얼로그가 accept되면 그 때의 스핀박스 값이 유지되어야 함.
    width, height = dialog.get_size()
    assert width == 1200
    assert height == 900

def test_canvas_size_dialog_reject(dialog, qtbot):
    """취소 버튼 클릭 시 (reject) 다이얼로그가 올바르게 종료되는지 테스트합니다."""
    initial_width, initial_height = dialog.get_size() # 초기 값 저장
    dialog.width_spin.setValue(500)
    dialog.height_spin.setValue(400)

    dialog.reject = MagicMock(wraps=dialog.reject)
    # dialog.done = MagicMock() # 이 라인 제거

    buttons = dialog.findChildren(QPushButton)
    cancel_button_found = None
    for btn in buttons:
        if btn.text() == "취소":
            cancel_button_found = btn
            break
    
    assert cancel_button_found is not None, """"취소" 버튼을 찾을 수 없습니다."""

    # print(f"Before click (reject): {dialog.result()}")
    cancel_button_found.clicked.emit() # reject() 슬롯 호출 -> done(Rejected) 호출

    dialog.reject.assert_called_once() # reject 호출 확인
    assert dialog.result() == QDialog.DialogCode.Rejected # result() 값 확인

    # 다이얼로그가 reject되면 값은 변경 전 상태로 유지되거나, 
    # 또는 reject 당시의 값으로 유지될 수 있음. 현재 코드는 reject 당시 값 유지.
    width, height = dialog.get_size()
    assert width == 500 # reject 당시의 값
    assert height == 400 # reject 당시의 값

# TODO: 스핀박스 값 범위 초과 시 동작 테스트 (setRange에 의해 자동으로 처리될 것이지만, 명시적 검증 가능)
# TODO: 부모 위젯 전달 시 동작 테스트 