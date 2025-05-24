# Living Collage Maker - 문서

Living Collage Maker는 사용자가 가구를 드래그 앤 드롭으로 배치하여 인테리어 콜라주를 만들 수 있는 애플리케이션입니다. 🆕

## 📖 문서 구조

### 기본 문서
- **[프로젝트 개요](docs/overview.md)**: 제품 개요 및 핵심 기능
- **[기술 사양](docs/technical-specs.md)**: 기술 스택 및 데이터 모델
- **[UI/UX 및 성능](docs/ui-performance.md)**: UI 디자인 및 성능 요구사항
- **[향후 계획 및 배포](docs/roadmap-deployment.md)**: 로드맵, 테스트, 배포 요구사항

## 🚀 주요 기능 요약

- **드래그 앤 드롭**: 가구를 캔버스에 직관적으로 배치
- **다중 선택**: Ctrl/Cmd 키를 이용한 여러 가구 동시 편집
- **이미지 조정**: 색온도, 밝기, 채도 조절
- **경계 체크**: 캔버스 영역 벗어남 방지
- **내보내기**: 이미지, HTML, PDF 형식 지원
- **상태 관리**: 작업 내용 자동 저장/복원

## 🔧 기술 스택

- **Frontend**: PyQt6
- **Backend**: Python, Supabase
- **PDF 생성**: reportlab
- **캐시 관리**: platformdirs 