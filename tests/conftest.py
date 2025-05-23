import sys
import os
# from PyQt6.QtWidgets import QApplication # QApplication 직접 임포트 및 사용 제거

# 프로젝트 루트 디렉토리 (tests 폴더의 부모 디렉토리)를 sys.path에 추가합니다.
# 이렇게 하면 pytest가 'src' 모듈을 찾을 수 있게 됩니다.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# QApplication 인스턴스를 테스트 세션 시작 시 한 번 생성합니다.
# 이는 QPixmap 등을 사용하는 테스트에서 발생할 수 있는 문제를 예방합니다.
# pytest-qt 플러그인이 QApplication 인스턴스(qapp fixture)를 관리하도록 합니다.
# _app = None

# def pytest_sessionstart(session):
#     global _app
#     _app = QApplication.instance() # 이미 인스턴스가 있는지 확인
#     if _app is None: # 인스턴스가 없으면 새로 생성
#         _app = QApplication(sys.argv)

# def pytest_sessionfinish(session):
#     # 필요한 경우 세션 종료 시 정리 작업 (여기서는 특별히 필요 없음)
#     pass 