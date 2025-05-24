import os
import sys
from datetime import datetime
from io import BytesIO
from typing import List

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from src.ui.canvas import FurnitureItem

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
    REPORTLAB_ERROR = None
except ImportError as e:
    REPORTLAB_AVAILABLE = False
    REPORTLAB_ERROR = f"reportlab 라이브러리가 설치되지 않았습니다: {e}\n\n설치 방법:\npip install reportlab"
except Exception as e:
    REPORTLAB_AVAILABLE = False
    REPORTLAB_ERROR = f"reportlab 로드 오류: {e}"


class PdfExportService(QObject):
    """콜라주를 PDF 형식으로 내보내는 서비스 클래스 (reportlab 사용)"""
    
    export_finished = pyqtSignal(bool, str)  # 성공 여부, 메시지
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.korean_font_name = 'Helvetica'  # 기본 폰트
        self.korean_font_bold = 'Helvetica-Bold'  # 기본 굵은 폰트
        self._register_korean_fonts()
    
    def _register_korean_fonts(self):
        """한글 폰트를 등록합니다."""
        if not REPORTLAB_AVAILABLE:
            return
            
        try:
            # 프로젝트 내부 폰트 경로 (우선 순위 1)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
            # 개발 환경에서의 폰트 경로
            dev_font_dir = os.path.join(current_dir, '..', 'assets', 'fonts')
            
            # PyInstaller 빌드 환경에서의 폰트 경로
            if getattr(sys, 'frozen', False):
                # PyInstaller로 빌드된 경우
                bundle_dir = sys._MEIPASS
                build_font_dir = os.path.join(bundle_dir, 'assets', 'fonts')
            else:
                build_font_dir = dev_font_dir
            
            # 폰트 경로 목록 (우선 순위대로)
            font_dirs = [build_font_dir, dev_font_dir]
            
            project_font_paths = []
            for font_dir in font_dirs:
                if os.path.exists(font_dir):
                    # macOS에서 띄어쓰기 문제 해결을 위해 나눔고딕코딩을 우선 사용 (고정폭 폰트)
                    project_font_paths.extend([
                        (os.path.join(font_dir, "NanumGothicCoding.ttf"), "나눔고딕코딩 Regular"),
                        (os.path.join(font_dir, "NanumGothicCoding-Bold.ttf"), "나눔고딕코딩 Bold"),
                        (os.path.join(font_dir, "NanumSquareR.ttf"), "나눔 스퀘어 Regular"),
                        (os.path.join(font_dir, "NanumSquareB.ttf"), "나눔 스퀘어 Bold"),
                    ])
                    break  # 첫 번째로 찾은 디렉토리 사용
            
            # 프로젝트 내부 폰트 시도
            for font_path, font_name in project_font_paths:
                if os.path.exists(font_path):
                    try:
                        # 나눔고딕코딩 Regular 폰트 등록 (우선순위 1 - 띄어쓰기 문제 해결)
                        if "나눔고딕코딩 Regular" in font_name:
                            pdfmetrics.registerFont(TTFont('NanumGothicCoding', font_path))
                            self.korean_font_name = 'NanumGothicCoding'
                            print(f"한글 폰트 등록 성공: {font_name} ({font_path})")
                        # 나눔고딕코딩 Bold 폰트 등록
                        elif "나눔고딕코딩 Bold" in font_name:
                            pdfmetrics.registerFont(TTFont('NanumGothicCoding-Bold', font_path))
                            self.korean_font_bold = 'NanumGothicCoding-Bold'
                            print(f"한글 폰트 등록 성공: {font_name} ({font_path})")
                        # 나눔 스퀘어 Regular 폰트 등록 (백업용)
                        elif "나눔 스퀘어 Regular" in font_name and self.korean_font_name == 'Helvetica':
                            pdfmetrics.registerFont(TTFont('NanumSquare', font_path))
                            self.korean_font_name = 'NanumSquare'
                            print(f"한글 폰트 등록 성공: {font_name} ({font_path})")
                        # 나눔 스퀘어 Bold 폰트 등록 (백업용)
                        elif "나눔 스퀘어 Bold" in font_name and self.korean_font_bold == 'Helvetica-Bold':
                            pdfmetrics.registerFont(TTFont('NanumSquare-Bold', font_path))
                            self.korean_font_bold = 'NanumSquare-Bold'
                            print(f"한글 폰트 등록 성공: {font_name} ({font_path})")
                    except Exception as e:
                        print(f"폰트 등록 실패 {font_name}: {e}")
                        continue
            
            # 프로젝트 폰트가 성공적으로 등록되었는지 확인
            if self.korean_font_name in ['NanumGothicCoding', 'NanumSquare']:
                print(f"{self.korean_font_name} 폰트가 성공적으로 등록되었습니다.")
                return
            
            # macOS 시스템 폰트 경로들 (우선 순위 2)
            macos_font_paths = [
                ("/Library/Fonts/NanumGothicCoding.ttf", "나눔고딕코딩"),
                ("/System/Library/Fonts/AppleSDGothicNeo.ttc", "애플 SD 고딕 Neo"),
                ("/Library/Fonts/NanumSquareOTF.otf", "나눔 스퀘어"),
                ("/System/Library/Fonts/Helvetica.ttc", "Helvetica"),
            ]
            
            # Windows 시스템 폰트 경로들 (우선 순위 3)
            windows_font_paths = [
                (r"C:\Windows\Fonts\malgun.ttf", "맑은 고딕"),      # 맑은 고딕
                (r"C:\Windows\Fonts\gulim.ttc", "굴림"),           # 굴림  
                (r"C:\Windows\Fonts\batang.ttc", "바탕"),          # 바탕
                (r"C:\Windows\Fonts\dotum.ttc", "돋움"),           # 돋움
            ]
            
            # 시스템 폰트 시도 (macOS 우선)
            all_system_fonts = macos_font_paths + windows_font_paths
            
            for font_path, font_name in all_system_fonts:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('KoreanFont', font_path))
                        pdfmetrics.registerFont(TTFont('KoreanFont-Bold', font_path))
                        self.korean_font_name = 'KoreanFont'
                        self.korean_font_bold = 'KoreanFont-Bold'
                        print(f"한글 폰트 등록 성공: {font_name} ({font_path})")
                        return
                    except Exception as e:
                        print(f"폰트 등록 실패 {font_name}: {e}")
                        continue
            
            # 폰트 등록 실패 시 기본 폰트 사용
            print("경고: 한글 폰트 등록에 실패했습니다. 기본 폰트를 사용합니다.")
            print("한글 텍스트가 올바르게 표시되지 않을 수 있습니다.")
            
        except Exception as e:
            print(f"폰트 등록 중 오류: {e}")
    
    def export_collage_to_pdf(self, canvas_widget, furniture_items: List[FurnitureItem], parent_window=None):
        """
        콜라주를 PDF 파일로 내보냅니다.
        
        Args:
            canvas_widget: Canvas 위젯 (콜라주 이미지 생성용)
            furniture_items: 가구 아이템 리스트
            parent_window: 부모 윈도우 (다이얼로그용)
        """
        try:
            # reportlab 설치 확인
            if not REPORTLAB_AVAILABLE:
                self._show_critical_message(
                    parent_window, 
                    "라이브러리 필요", 
                    REPORTLAB_ERROR
                )
                return
            
            # 가구 아이템이 없으면 경고
            if not furniture_items:
                self._show_warning_message(parent_window, "경고", "내보낼 콜라주가 없습니다.")
                return
            
            # PDF 파일 저장 위치 선택
            file_path, _ = QFileDialog.getSaveFileName(
                parent_window,
                "PDF 파일로 내보내기",
                "collage.pdf",
                "PDF 파일 (*.pdf)"
            )
            
            if not file_path:
                return  # 사용자가 취소한 경우
            
            # PDF 생성
            success = self._generate_pdf(canvas_widget, furniture_items, file_path)
            
            if not success:
                self._show_critical_message(parent_window, "오류", "PDF 생성에 실패했습니다.")
                return
            
            self._show_information_message(parent_window, "성공", f"PDF 파일이 성공적으로 저장되었습니다.\n{file_path}")
            self.export_finished.emit(True, "PDF 내보내기 성공")
            
        except Exception as e:
            error_msg = f"PDF 내보내기 중 오류가 발생했습니다: {str(e)}"
            self._show_critical_message(parent_window, "오류", error_msg)
            self.export_finished.emit(False, error_msg)
    
    def _generate_pdf(self, canvas_widget, furniture_items: List[FurnitureItem], pdf_path: str) -> bool:
        """reportlab을 사용하여 PDF를 생성합니다."""
        try:
            # PDF 문서 생성
            doc = SimpleDocTemplate(
                pdf_path,
                pagesize=A4,
                rightMargin=20*mm,
                leftMargin=20*mm,
                topMargin=20*mm,
                bottomMargin=20*mm
            )
            
            # 스타일 설정 (한글 폰트 사용)
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#2C3E50'),
                fontName=self.korean_font_name
            )
            
            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Normal'],
                fontSize=12,
                spaceAfter=20,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#7F8C8D'),
                fontName=self.korean_font_name
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=16,
                spaceBefore=20,
                spaceAfter=10,
                textColor=colors.HexColor('#2C3E50'),
                fontName=self.korean_font_name
            )
            
            furniture_title_style = ParagraphStyle(
                'FurnitureTitle',
                parent=styles['Heading3'],
                fontSize=14,
                spaceBefore=15,
                spaceAfter=8,
                textColor=colors.HexColor('#2C3E50'),
                fontName=self.korean_font_bold
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontName=self.korean_font_name,
                fontSize=10,
                spaceAfter=4
            )
            
            info_style = ParagraphStyle(
                'InfoStyle',
                parent=styles['Normal'],
                fontName=self.korean_font_name,
                fontSize=9,
                textColor=colors.HexColor('#5D6D7E'),
                spaceAfter=3
            )
            
            link_style = ParagraphStyle(
                'LinkStyle',
                parent=styles['Normal'],
                fontName=self.korean_font_name,
                fontSize=10,
                textColor=colors.HexColor('#3498DB'),
                underline=1,
                spaceAfter=8
            )
            
            # PDF 콘텐츠 구성
            story = []
            
            # 제목
            story.append(Paragraph("Living Collage", title_style))
            
            # 생성 시간
            current_time = datetime.now().strftime("%Y년 %m월 %d일 %H:%M")
            story.append(Paragraph(f"생성 시간: {current_time}", subtitle_style))
            
            # 콜라주 이미지 추가 (메모리에서 직접 처리)
            image_data = self._get_collage_image_data(canvas_widget)
            if image_data:
                try:
                    # Canvas에서 원본 이미지 크기 가져오기
                    original_pixmap = canvas_widget._generate_collage_image()
                    original_width = original_pixmap.width()
                    original_height = original_pixmap.height()
                    
                    # PDF 페이지 크기 계산 (A4 기준, 양쪽 여백 40mm 제외)
                    page_width = A4[0] - 40*mm  # 210mm - 40mm = 170mm
                    page_height = A4[1] - 40*mm  # 297mm - 40mm = 257mm
                    
                    # 원본 이미지 비율 계산
                    aspect_ratio = original_width / original_height
                    
                    # 너비를 최대한 활용하면서 비율 유지
                    image_width = page_width
                    image_height = image_width / aspect_ratio
                    
                    # 높이가 페이지를 벗어나면 높이 기준으로 조정
                    max_image_height = page_height * 0.6  # 페이지 높이의 60%까지만 사용
                    if image_height > max_image_height:
                        image_height = max_image_height
                        image_width = image_height * aspect_ratio
                    
                    print(f"[PDF] 원본 이미지 크기: {original_width}x{original_height}")
                    print(f"[PDF] PDF 이미지 크기: {image_width/mm:.1f}mm x {image_height/mm:.1f}mm")
                    print(f"[PDF] 비율 유지: {aspect_ratio:.2f}")
                    
                    # BytesIO를 사용해서 메모리에서 직접 이미지 처리 (비율 유지)
                    img = Image(image_data, width=image_width, height=image_height)
                    story.append(img)
                    story.append(Spacer(1, 20))
                except Exception as e:
                    print(f"이미지 추가 오류: {e}")
                    # 실패 시 기본 크기로 fallback
                    try:
                        img = Image(image_data, width=170*mm, height=120*mm)
                        story.append(img)
                        story.append(Spacer(1, 20))
                    except Exception as fallback_e:
                        print(f"이미지 fallback 오류: {fallback_e}")
            
            # 각 가구를 개별 섹션으로 표시
            for i, item in enumerate(furniture_items, 1):
                furniture = item.furniture
                
                # 가구 제목 (번호 포함)
                furniture_name = furniture.name or "이름 없음"
                story.append(Paragraph(f"{i}. {furniture_name}", furniture_title_style))
                
                # 기본 정보 섹션
                info_lines = []
                
                # 브랜드 정보
                if furniture.brand:
                    info_lines.append(f"<b>브랜드:</b> {furniture.brand}")
                
                # 타입 정보
                if furniture.type:
                    info_lines.append(f"<b>카테고리:</b> {furniture.type}")
                
                # 가격 정보
                if furniture.price:
                    price_str = f"{furniture.price:,}원"
                    info_lines.append(f"<b>가격:</b> {price_str}")
                
                # 크기 정보
                if furniture.width and furniture.depth and furniture.height:
                    size_str = f"{furniture.width} × {furniture.depth} × {furniture.height} mm"
                    info_lines.append(f"<b>크기 (가로×세로×높이):</b> {size_str}")
                
                # 좌석 높이
                if furniture.seat_height:
                    info_lines.append(f"<b>좌석 높이:</b> {furniture.seat_height}mm")
                
                # 기본 정보 출력
                for line in info_lines:
                    story.append(Paragraph(line, normal_style))
                
                # 설명
                if furniture.description:
                    story.append(Paragraph(f"<b>제품 설명:</b>", normal_style))
                    story.append(Paragraph(furniture.description, info_style))
                
                # 제품 링크 (하이퍼링크)
                if furniture.link:
                    link_text = f'<a href="{furniture.link}" color="#3498DB"><u>🔗 제품 상세보기</u></a>'
                    story.append(Paragraph(link_text, link_style))
                
                # 가구 간 구분선
                if i < len(furniture_items):
                    story.append(Spacer(1, 10))
                    # 구분선 표시
                    line_table = Table([['']], colWidths=[170*mm])
                    line_table.setStyle(TableStyle([
                        ('LINEBELOW', (0, 0), (-1, -1), 1, colors.HexColor('#E5E7E9')),
                    ]))
                    story.append(line_table)
                    story.append(Spacer(1, 10))
            
            # 푸터 정보
            story.append(Spacer(1, 20))
            footer_style = ParagraphStyle(
                'FooterStyle',
                parent=styles['Normal'],
                fontName=self.korean_font_name,
                fontSize=8,
                textColor=colors.HexColor('#95A5A6'),
                alignment=TA_CENTER
            )
            story.append(Paragraph("Living Collage Maker로 생성된 콜라주입니다.", footer_style))
            
            # PDF 빌드
            doc.build(story)
            return True
            
        except Exception as e:
            print(f"PDF 생성 오류: {e}")
            return False
    
    def _get_collage_image_data(self, canvas_widget) -> BytesIO:
        """콜라주 이미지를 BytesIO 객체로 반환합니다."""
        try:
            # Canvas에서 QPixmap 이미지 생성
            pixmap = canvas_widget._generate_collage_image()
            
            # QPixmap을 BytesIO로 변환
            byte_array = BytesIO()
            
            # QPixmap을 PNG 형식으로 BytesIO에 저장
            from PyQt6.QtCore import QBuffer, QIODevice
            from PyQt6.QtGui import QImageWriter
            
            buffer = QBuffer()
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            
            # QPixmap을 QImage로 변환 후 PNG로 저장
            image = pixmap.toImage()
            writer = QImageWriter(buffer, b"PNG")
            success = writer.write(image)
            
            if success:
                # QBuffer의 데이터를 BytesIO로 복사
                buffer.seek(0)
                byte_array.write(buffer.data())
                byte_array.seek(0)
                buffer.close()
                return byte_array
            else:
                buffer.close()
                return None
                
        except Exception as e:
            print(f"이미지 데이터 생성 오류: {e}")
            return None
    
    def _show_information_message(self, parent, title: str, message: str):
        """정보 메시지를 표시합니다."""
        QMessageBox.information(parent, title, message)
    
    def _show_warning_message(self, parent, title: str, message: str):
        """경고 메시지를 표시합니다."""
        QMessageBox.warning(parent, title, message)
    
    def _show_critical_message(self, parent, title: str, message: str):
        """오류 메시지를 표시합니다."""
        QMessageBox.critical(parent, title, message) 