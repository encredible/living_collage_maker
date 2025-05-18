from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout
from .canvas import Canvas
from .panels import ExplorerPanel, InfoPanel
from services.supabase_client import SupabaseClient
from models.furniture import Furniture

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Living Collage Maker")
        self.setMinimumSize(1200, 800)
        
        # Supabase 클라이언트 초기화
        self.supabase = SupabaseClient()
        
        # 메인 위젯 설정
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 메인 레이아웃 설정
        layout = QHBoxLayout(main_widget)
        
        # 캔버스 영역 (왼쪽)
        self.canvas = Canvas()
        layout.addWidget(self.canvas, stretch=2)
        
        # 우측 패널 (오른쪽)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 탐색 패널
        self.explorer = ExplorerPanel()
        right_layout.addWidget(self.explorer)
        
        # 정보 패널
        self.info_panel = InfoPanel()
        right_layout.addWidget(self.info_panel)
        
        layout.addWidget(right_panel, stretch=1)
        
        # 초기 데이터 로드
        self.load_furniture_data()
    
    def load_furniture_data(self):
        """Supabase에서 가구 데이터를 로드합니다."""
        try:
            furniture_list = self.supabase.get_furniture_list()
            for furniture_data in furniture_list:
                # Furniture 객체 생성
                furniture = Furniture(
                    id=furniture_data['id'],
                    brand=furniture_data['brand'],
                    name=furniture_data['name'],
                    description=furniture_data['description'],
                    image_filename=furniture_data['image_filename'],
                    link=furniture_data['link'],
                    price=furniture_data['price'],
                    type=furniture_data['type'],
                    color=furniture_data['color'],
                    locations=furniture_data['locations'],
                    styles=furniture_data['styles'],
                    width=furniture_data['width'],
                    depth=furniture_data['depth'],
                    height=furniture_data['height'],
                    seat_height=furniture_data.get('seat_height'),
                    author=furniture_data['author'],
                    created_at=furniture_data['created_at']
                )
                
                # 탐색 패널에 가구 아이템 추가
                self.explorer.add_furniture_item(furniture)
                
        except Exception as e:
            print(f"데이터 로드 중 오류 발생: {e}") 