# Living Collage Maker - 로드맵 및 배포

## 🚀 향후 개선사항 (로드맵)

### 7.1 우선순위 높음 ✅ 완료
- [x] **이미지 최적화 및 캐시 관리 개선**
- [x] **에러 처리 및 사용자 피드백 강화**
- [x] **가구 좌우 반전 기능 구현**
- [x] **가구 다중 선택 기능 구현** 🆕
  - [x] Ctrl/Cmd 키를 이용한 다중 선택 시스템
  - [x] 다중 선택된 아이템들의 동시 이동 기능
  - [x] 다중 선택된 아이템들의 일괄 삭제 기능
  - [x] Delete/Backspace 키를 이용한 키보드 삭제
  - [x] 선택 상태 유지 로직 개선
- [x] **캔버스 경계 체크 시스템 구현** 🆕
  - [x] 가구 이동 시 캔버스 영역 벗어남 방지
  - [x] 가구 리사이즈 시 캔버스 영역 벗어남 방지
  - [x] 다중 선택 이동에서의 경계 체크
  - [x] 비율 유지 모드에서의 경계 체크
- [x] **가구 이미지 색온도, 밝기, 채도 조절 기능**
- [x] **작업 내용 저장/불러오기 기능**
  - [x] 기본 저장/불러오기 구현
  - [x] 이미지 조정 정보 저장/불러오기 구현
- [x] **콜라주 HTML로 내보내기 기능**
  - [x] HTML 문서 생성 기능 구현
  - [x] 콜라주 이미지 별도 파일 저장 기능
  - [x] 가구 정보 표시 및 하이퍼링크 기능
  - [x] 기본 CSS 스타일링 적용
- [x] **콜라주 PDF로 내보내기 기능**
  - [x] reportlab 라이브러리 통합
  - [x] 직접 PDF 생성 서비스 구현
  - [x] 한글 폰트 지원 및 fallback 메커니즘
  - [x] 이미지 임베딩 및 하이퍼링크 기능
  - [x] 전문적인 레이아웃 및 스타일링
- [x] **애플리케이션 상태 관리 기능**
  - [x] 자동 상태 저장/복원 시스템 구현
  - [x] 크로스플랫폼 캐시 디렉토리 사용
  - [x] 윈도우, 패널, 컬럼 너비, 캔버스 상태 저장
  - [x] 가구 아이템 상태 저장 (위치, 크기, 이미지 조정 등)
  - [x] 레이아웃 초기화 및 캐시 정리 기능
  - [x] 에러 처리 및 fallback 메커니즘

### 7.2 우선순위 중간 🚧 계획 중
- [ ] **캔버스 배경 설정 기능** 🆕
  - [ ] 이미지 파일 선택 및 배경 설정
  - [ ] 배경 이미지 크기에 맞춘 자동 캔버스 크기 조정
  - [ ] 배경 제거 기능
  - [ ] 배경 이미지 데이터 저장/불러오기
  - [ ] 다양한 이미지 형식 지원 (JPG, PNG, BMP, GIF)

- [ ] **가구 회전 기능 구현**
  - [ ] 90도 단위 회전
  - [ ] 자유 회전 (각도 입력)
  - [ ] 회전 중심점 설정
  - [ ] 회전 시 경계 체크

- [ ] **가구 크기 조절 시 그리드 스냅 기능**
  - [ ] 그리드 표시 옵션
  - [ ] 스냅 거리 설정
  - [ ] 가이드 라인 표시
  - [ ] 그리드 크기 조절

- [ ] **가구 배치 히스토리 (실행 취소/다시 실행)**
  - [ ] 작업 기록 스택 구현
  - [ ] Ctrl+Z, Ctrl+Y 단축키
  - [ ] 히스토리 제한 (메모리 관리)
  - [ ] 선택적 실행 취소 (특정 작업만)

- [ ] **가구 그룹화 기능**
  - [ ] 다중 선택된 가구 그룹화
  - [ ] 그룹 단위 이동/크기 조절
  - [ ] 그룹 해제 기능
  - [ ] 중첩 그룹 지원

- [ ] **가구 정렬 기능**
  - [ ] 정렬 도구 패널
  - [ ] 좌/우/중앙/상/하 정렬
  - [ ] 균등 분배 기능
  - [ ] 그리드 정렬

- [ ] **가구 복제 기능**
  - [ ] Ctrl+D 단축키로 복제
  - [ ] 복제본 위치 오프셋
  - [ ] 다중 선택 복제
  - [ ] 복제 시 속성 유지

- [ ] **가구 레이어 관리**
  - [ ] 레이어 패널 추가
  - [ ] 앞으로/뒤로 이동
  - [ ] 맨 앞/맨 뒤로 이동
  - [ ] 레이어 잠금 기능

### 7.3 우선순위 낮음 💡 아이디어
- [ ] **3D 뷰 모드**
  - [ ] 간단한 3D 렌더링
  - [ ] 카메라 각도 조절
  - [ ] 조명 설정
  - [ ] 3D 내보내기

- [ ] **가구 커스터마이징 기능**
  - [ ] 색상 변경 도구
  - [ ] 패턴/텍스처 적용
  - [ ] 크기 비율 조절
  - [ ] 재질 속성 변경

- [ ] **가구 추천 시스템**
  - [ ] AI 기반 추천
  - [ ] 스타일 매칭
  - [ ] 가격대별 추천
  - [ ] 공간 크기 고려

- [ ] **공유 기능**
  - [ ] 클라우드 동기화
  - [ ] 소셜 미디어 공유
  - [ ] 공동 작업 모드
  - [ ] 댓글 시스템

- [ ] **가구 가격 비교 기능**
  - [ ] 다중 쇼핑몰 연동
  - [ ] 실시간 가격 업데이트
  - [ ] 할인 정보 알림
  - [ ] 가격 추이 그래프

## 🧪 테스트 요구사항

### 9.1 단위 테스트 (총 152개 테스트) ✅
#### 데이터 모델 테스트
- [x] **Furniture 모델 테스트** (12개)
  - 필드 검증, 기본값 설정, 타입 체크
- [x] **가구 상태 모델 테스트** (8개)
  - 위치, 크기, 이미지 조정 상태

#### 서비스 레이어 테스트
- [x] **이미지 서비스 테스트** (28개)
  - 캐시 관리, 비동기 로딩, 최적화
- [x] **PDF 서비스 테스트** (16개)
  - PDF 생성, 한글 폰트, 하이퍼링크
- [x] **HTML 서비스 테스트** (12개)
  - HTML 생성, 스타일링, 이미지 참조
- [x] **상태 관리 서비스 테스트** (20개)
  - 저장/불러오기, 마이그레이션, 에러 처리

#### UI 컴포넌트 테스트
- [x] **캔버스 테스트** (24개)
  - 드래그 앤 드롭, 렌더링, 이벤트 처리
- [x] **패널 테스트** (16개)
  - 필터링, 선택, 업데이트
- [x] **위젯 테스트** (20개)
  - 가구 아이템, 크기 조절, 이미지 표시

#### 고급 기능 테스트
- [x] **다중 선택 기능 테스트** (8개) 🆕
  - Ctrl/Cmd 키 조합, 동시 이동, 일괄 삭제
- [x] **경계 체크 시스템 테스트** (8개) 🆕
  - 이동 제한, 크기 조절 제한, 다중 선택 경계 체크

### 9.2 통합 테스트
- [x] **데이터베이스 연동 테스트**
  - Supabase 연결, 데이터 동기화
  - 오프라인 모드, 에러 복구
- [x] **파일 시스템 테스트**
  - 크로스플랫폼 캐시, 권한 처리
  - 파일 락, 동시 접근

### 9.3 UI 테스트
- [x] **사용자 상호작용 테스트**
  - 드래그 앤 드롭 시나리오
  - 메뉴 기능 검증
  - 키보드 단축키 테스트
- [x] **키보드 이벤트 테스트** 🆕
  - Delete/Backspace 키 삭제
  - Ctrl/Cmd 조합키 처리
- [x] **마우스 이벤트 테스트** 🆕
  - 다중 선택 클릭 패턴
  - 경계 체크 드래그 제한

### 9.4 성능 테스트
- [x] **대용량 데이터 처리 테스트**
  - 100개 가구 동시 로딩
  - 대용량 이미지 처리
  - 메모리 사용량 모니터링
- [x] **메모리 누수 테스트**
  - 장시간 실행 테스트
  - 리소스 해제 검증
- [x] **스레드 안전성 테스트**
  - 동시성 문제 검증
  - 데드락 방지 테스트

### 9.5 자동화된 테스트
- [x] **CI/CD 파이프라인**
  - 커밋 시 자동 테스트
  - 테스트 커버리지 측정
  - 성능 회귀 검사
- [x] **테스트 데이터 관리**
  - 목 데이터 생성
  - 테스트 환경 격리
  - 데이터 초기화

## 📦 배포 요구사항

### 10.1 시스템 요구사항
#### 최소 요구사항
- **Python**: 3.8 이상
- **PyQt6**: 6.4.0 이상
- **메모리**: 최소 4GB RAM
- **저장공간**: 최소 1GB 사용 가능 공간
- **인터넷**: 초기 설정 및 가구 데이터 로딩용

#### 권장 요구사항
- **Python**: 3.11 이상
- **메모리**: 8GB RAM 이상
- **저장공간**: 2GB 이상
- **인터넷**: 안정적인 브로드밴드 연결

### 10.2 지원 운영체제
- **Windows**: 10 이상 (x64)
- **macOS**: 10.14 (Mojave) 이상
- **Linux**: Ubuntu 18.04 LTS 이상

### 10.3 의존성 라이브러리
```requirements.txt
PyQt6>=6.4.0
supabase>=2.0.0
Pillow>=9.0.0
reportlab>=4.0.0
platformdirs>=3.0.0
requests>=2.28.0
aiohttp>=3.8.0
pytest>=7.0.0
pytest-qt>=4.2.0
pytest-asyncio>=0.21.0
```

### 10.4 배포 방식
#### 개발자 배포
- **소스 코드**: GitHub 저장소
- **패키지 관리**: pip를 통한 의존성 설치
- **가상환경**: venv 또는 conda 사용 권장

#### 사용자 배포 (향후 계획)
- **실행 파일**: PyInstaller를 사용한 단일 실행 파일
- **인스톨러**: NSIS (Windows), DMG (macOS), AppImage (Linux)
- **앱스토어**: Microsoft Store, Mac App Store (검토 중)

### 10.5 설치 가이드
#### 개발자 설치
```bash
# 저장소 클론
git clone https://github.com/username/living_collage_maker.git
cd living_collage_maker

# 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt

# 애플리케이션 실행
python src/main.py
```

#### 사용자 설치 (향후)
- 인스톨러 다운로드 및 실행
- 자동 의존성 설치
- 바탕화면 바로가기 생성

### 10.6 환경 설정
#### 환경 변수
```bash
# Supabase 설정 (필수)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# 옵션 설정
CACHE_DIR=custom_cache_directory
DEBUG_MODE=true
LOG_LEVEL=INFO
```

#### 설정 파일
- **위치**: `~/.config/LivingCollageMaker/settings.json`
- **내용**: UI 설정, 캐시 설정, 성능 옵션

### 10.7 배포 프로세스
#### 버전 관리
- **Semantic Versioning**: MAJOR.MINOR.PATCH
- **릴리즈 노트**: 각 버전별 변경사항 문서화
- **브랜치 전략**: Git Flow 모델 사용

#### 품질 보증
- **자동 테스트**: 모든 테스트 통과 확인
- **코드 리뷰**: 주요 변경사항 검토
- **성능 검증**: 벤치마크 테스트 실행

#### 배포 단계
1. **개발 완료**: 기능 개발 및 테스트
2. **스테이징**: 프로덕션 환경과 유사한 테스트
3. **프리릴리즈**: 베타 테스터 배포
4. **프로덕션**: 정식 릴리즈

### 10.8 사용자 지원
#### 문서화
- **사용자 매뉴얼**: 기능별 상세 가이드
- **FAQ**: 자주 묻는 질문 및 답변
- **문제 해결**: 일반적인 문제 및 해결방법

#### 커뮤니티 지원
- **GitHub Issues**: 버그 리포트 및 기능 요청
- **위키**: 사용자 기여 문서
- **포럼**: 사용자 간 정보 공유

### 10.9 라이선스 및 법적 고지
- **소프트웨어 라이선스**: MIT License
- **써드파티 라이브러리**: 각 라이브러리 라이선스 준수
- **이미지 저작권**: 사용자 책임
- **개인정보 보호**: 로컬 캐시만 사용, 개인정보 미수집 