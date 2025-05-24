# Living Collage Maker - 기술 사양

## 💻 기술 스택

### 3.1 프론트엔드
- **PyQt6**: 메인 GUI 프레임워크
- **QTableView 및 QStandardItemModel**: 가구 목록 표시
- **QGraphicsView**: 향후 구현 예정

### 3.2 백엔드
- **Python**: 메인 개발 언어
- **Supabase**: 데이터베이스 및 이미지 저장
- **SQLite**: 로컬 캐시
- **reportlab**: PDF 생성 라이브러리
- **platformdirs**: 크로스플랫폼 캐시 디렉토리 관리

## 📊 데이터 모델

### 4.1 가구 (Furniture)
```python
@dataclass
class Furniture:
    # 필수 필드
    id: str
    brand: str
    name: str
    image_filename: str
    price: int
    type: str
    
    # 선택적 필드 (기본값 설정)
    description: str = ''
    link: str = ''
    color: str = ''
    locations: List[str] = field(default_factory=list)
    styles: List[str] = field(default_factory=list)
    width: int = 0
    depth: int = 0
    height: int = 0
    seat_height: Optional[int] = None
    author: str = ''
    created_at: str = ''
```

### 4.2 가구 아이템 상태 (CollageFurnitureState)
```python
@dataclass
class CollageFurnitureState:
    # 가구 식별
    furniture_id: str
    
    # 위치 및 크기
    x: float
    y: float
    width: float
    height: float
    
    # 표시 설정
    z_order: int
    is_flipped: bool = False
    
    # 이미지 조정
    color_temperature: float = 6500.0  # 2000K-10000K
    brightness: float = 100.0         # 0-200%
    saturation: float = 100.0         # 0-200%
```

### 4.3 가구 아이템 UI 기능

#### 하단 패널 순서 변경 🆕
하단 패널에서 가구 아이템들의 순서를 변경할 수 있는 기능:

```python
# 순서 변경 방식
class FurnitureOrderManager:
    DRAG_DROP = "drag_drop"      # 드래그 앤 드롭
    BUTTON_CONTROL = "button"    # 버튼을 통한 이동
    AUTO_SORT = "auto_sort"      # 자동 정렬

# 정렬 기준
class SortCriteria(Enum):
    NAME_ASC = "name_asc"        # 이름 오름차순
    NAME_DESC = "name_desc"      # 이름 내림차순
    BRAND_ASC = "brand_asc"      # 브랜드 오름차순
    BRAND_DESC = "brand_desc"    # 브랜드 내림차순
    PRICE_ASC = "price_asc"      # 가격 오름차순
    PRICE_DESC = "price_desc"    # 가격 내림차순
    TYPE_ASC = "type_asc"        # 타입 오름차순
    TYPE_DESC = "type_desc"      # 타입 내림차순
    CUSTOM = "custom"            # 사용자 정의 순서
```

**기능 사양:**
- **자동 번호 매기기**: 가구 목록의 첫 번째 컬럼에 1번부터 순차적으로 번호 표시 🆕
- 드래그 앤 드롭을 통한 직관적인 순서 변경
- 버튼을 통한 한 칸씩 이동 (위/아래)
- 맨 위/맨 아래로 한 번에 이동
- 다양한 기준으로 자동 정렬
- 순서 변경 후 상태 저장 및 복원
- 실시간 시각적 피드백
- **컬럼 너비 자동 보존**: 순서 변경 후에도 사용자 조정 컬럼 너비 유지 🆕

#### 리사이즈 핸들
가구 아이템의 크기 조절을 위한 핸들 시스템:

```python
# 리사이즈 핸들 위치 (8방향)
class ResizeHandle(Enum):
    TOP_LEFT = 0      # 좌상단
    TOP = 1          # 상단 중앙
    TOP_RIGHT = 2    # 우상단
    LEFT = 3         # 좌측 중앙
    RIGHT = 4        # 우측 중앙
    BOTTOM_LEFT = 5  # 좌하단
    BOTTOM = 6       # 하단 중앙
    BOTTOM_RIGHT = 7 # 우하단
```

**기능 사양:**
- 8방향 리사이즈 핸들 제공 (모서리 4개, 변 중앙 4개)
- 핸들 크기: 8x8 픽셀
- 핸들 색상: #2C3E50 (선택 시에만 표시)
- Shift 키 홀드: 비율 유지 리사이즈
- 최소 크기 제한: 100x100 픽셀
- 캔버스 경계 제한: 리사이즈 시 캔버스 영역을 벗어나지 않도록 제한

### 4.4 캔버스 상태 (CanvasState)
```python
@dataclass
class CanvasState:
    width: int
    height: int
    furniture_items: List[CollageFurnitureState]
    
    # 배경 설정 🆕
    background_image_path: str = ''  # 배경 이미지 파일 경로
    background_image_data: Optional[bytes] = None  # 배경 이미지 데이터 (저장용)
    has_background: bool = False  # 배경 이미지 존재 여부
    
    # 작업 메타데이터
    title: str = ''
    description: str = ''
    created_at: str = ''
    modified_at: str = ''
    version: str = '1.0'
```

### 4.5 애플리케이션 상태 (AppState)
```python
@dataclass
class AppState:
    # 윈도우 상태
    window_geometry: Dict[str, int]  # x, y, width, height
    
    # 패널 상태
    splitter_sizes: Dict[str, List[int]]  # horizontal, vertical
    
    # 컬럼 너비
    column_widths: Dict[str, Dict[str, int]]
    
    # 캔버스 상태
    canvas_state: Optional[CanvasState] = None
```

## 🏗️ 아키텍처

### 5.1 레이어 구조
```
┌─────────────────────────────────────┐
│           UI Layer (PyQt6)          │
├─────────────────────────────────────┤
│         Service Layer               │
│  ├─ ImageService                    │
│  ├─ PDFService                      │
│  ├─ HTMLService                     │
│  ├─ AppStateService                 │
│  └─ BackgroundService               │
├─────────────────────────────────────┤
│         Data Layer                  │
│  ├─ SupabaseClient                  │
│  ├─ ImageCacheManager              │
│  └─ LocalStateManager              │
└─────────────────────────────────────┘
```

### 5.2 캐시 관리 시스템
- **메모리 캐시**: WeakReference를 사용한 임시 저장
- **디스크 캐시**: platformdirs를 사용한 영구 저장
- **이미지 최적화**: 최대 1920px, 85% 품질
- **자동 정리**: 앱 종료 시 임시 파일 정리

### 5.3 스레드 관리
- **메인 스레드**: UI 업데이트
- **백그라운드 스레드**: 이미지 로딩, 파일 I/O
- **스레드 풀**: 병렬 이미지 처리

## 🔧 API 설계

### 6.1 이미지 서비스 API
```python
class ImageService:
    async def load_image(self, url: str) -> QPixmap
    def get_cached_image(self, furniture_id: str) -> Optional[QPixmap]
    def clear_cache(self) -> None
    def optimize_image(self, image: QPixmap) -> QPixmap
```

### 6.2 PDF 서비스 API
```python
class PDFService:
    def generate_pdf(self, 
                    collage_image: QPixmap,
                    furniture_list: List[Furniture],
                    output_path: str) -> bool
    def register_korean_fonts(self) -> None
```

### 6.3 HTML 서비스 API
```python
class HTMLService:
    def generate_html(self,
                     collage_image: QPixmap,
                     furniture_list: List[Furniture],
                     output_path: str) -> bool
    def generate_html_content(self, furniture_list: List[Furniture]) -> str
```

### 6.4 상태 관리 API
```python
class AppStateService:
    def save_state(self, state: AppState) -> None
    def load_state(self) -> Optional[AppState]
    def clear_cache(self) -> None
    def migrate_legacy_cache(self) -> None
```

### 6.5 배경 관리 API 🆕
```python
class BackgroundService:
    def set_background_image(self, image_path: str) -> bool
    def remove_background(self) -> None
    def get_background_image(self) -> Optional[QPixmap]
    def get_background_size(self) -> Optional[Tuple[int, int]]
    def is_background_set(self) -> bool
    def save_background_data(self, image_path: str) -> bytes
    def load_background_from_data(self, image_data: bytes) -> QPixmap
```

## 📁 파일 시스템 구조

### 7.1 애플리케이션 구조
```
living_collage_maker/
├── src/
│   ├── main.py                 # 애플리케이션 진입점
│   ├── models/
│   │   └── furniture.py        # 데이터 모델
│   ├── services/
│   │   ├── image_service.py    # 이미지 관리
│   │   ├── pdf_service.py      # PDF 생성
│   │   ├── html_service.py     # HTML 생성
│   │   ├── app_state_service.py # 상태 관리
│   │   └── background_service.py # 배경 관리 🆕
│   ├── ui/
│   │   ├── main_window.py      # 메인 윈도우
│   │   ├── canvas_widget.py    # 캔버스
│   │   ├── furniture_panel.py  # 가구 패널
│   │   └── bottom_panel.py     # 하단 패널
│   └── utils/
│       ├── constants.py        # 상수 정의
│       └── helpers.py          # 유틸리티 함수
├── tests/                      # 테스트 파일
├── docs/                       # 문서
├── requirements.txt            # 의존성
└── README.md                   # 프로젝트 설명
```

### 7.2 캐시 디렉토리 구조
```
LivingCollageMaker/
├── Cache/
│   ├── images/                 # 이미지 캐시
│   │   ├── thumbnails/         # 썸네일
│   │   └── full_size/          # 원본 크기
│   └── app_state.json          # 애플리케이션 상태
└── temp/                       # 임시 파일
```

## 🔐 보안 고려사항

### 8.1 데이터 보안
- Supabase 연결 시 HTTPS 사용
- API 키는 환경 변수로 관리
- 로컬 캐시 암호화 (향후 구현)

### 8.2 파일 시스템 보안
- 사용자 디렉토리 외부 접근 제한
- 임시 파일 자동 정리
- 파일 확장자 검증

## ⚡ 성능 최적화

### 9.1 이미지 처리
- 지연 로딩 (Lazy Loading)
- 이미지 리사이징 및 압축
- 메모리 사용량 모니터링

### 9.2 UI 반응성
- 비동기 작업 처리
- 프로그레스 바 표시
- 백그라운드 스레드 활용

### 9.3 메모리 관리
- WeakReference 사용
- 가비지 컬렉션 최적화
- 리소스 자동 해제 

# 번호 컬럼 자동 생성 로직
def refresh_model(self):
    for furniture_name in self.furniture_order:
        row_number = self.furniture_order.index(furniture_name) + 1
        row_data = [
            str(row_number),  # 번호 (1부터 시작)
            furniture.name,   # 이름
            # ... 기타 컬럼들 ...
        ] 