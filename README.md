# Living Collage Maker

인테리어 콜라주를 만들 수 있는 데스크톱 애플리케이션입니다.

## 기능

- 가구 이미지 드래그 앤 드롭
- 이미지 크기 조절
- 가구 정보 표시
- 콜라주 저장/불러오기
- 마크다운/이미지 형식으로 내보내기

## 설치 방법

### 개발 환경에서 실행
1. Python 3.8 이상 설치
2. 필요한 패키지 설치:
   ```bash
   pip install -r requirements.txt
   ```
3. 프로그램 실행:
   ```bash
   python src/main.py
   ```

### 실행 파일로 실행 (Windows/macOS)
1. `dist` 폴더에서 `LivingCollageMaker.exe` (Windows) 또는 `LivingCollageMaker.app` (macOS) 실행
2. Python 설치가 필요 없음

## 실행 파일 빌드 방법

### Windows
```bash
python build.py
```

### macOS
```bash
python build.py
```

빌드된 실행 파일은 `dist` 폴더에서 찾을 수 있습니다.

## 시스템 요구사항
- Windows 10 이상 또는 macOS 10.15 이상
- 최소 4GB RAM
- 최소 1GB 저장 공간
- 인터넷 연결 필요

## 주의사항
- 첫 실행 시 이미지 캐시를 다운로드하므로 시간이 걸릴 수 있습니다
- 인터넷 연결이 필요합니다
- `.image` 폴더에 캐시된 이미지가 저장됩니다

## 개발 환경

- Python 3.8 이상
- PyQt6
- Supabase

## 라이선스

MIT License 