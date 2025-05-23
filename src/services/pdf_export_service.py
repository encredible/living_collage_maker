import os
from datetime import datetime
from typing import List
from io import BytesIO

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from src.models.furniture import Furniture
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
            # Windows 시스템 폰트 경로들
            font_paths = [
                (r"C:\Windows\Fonts\malgun.ttf", "맑은 고딕"),      # 맑은 고딕
                (r"C:\Windows\Fonts\gulim.ttc", "굴림"),           # 굴림  
                (r"C:\Windows\Fonts\batang.ttc", "바탕"),          # 바탕
                (r"C:\Windows\Fonts\dotum.ttc", "돋움"),           # 돋움
            ]
            
            # 사용 가능한 첫 번째 폰트 등록
            for font_path, font_name in font_paths:
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
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontName=self.korean_font_name
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
                    # BytesIO를 사용해서 메모리에서 직접 이미지 처리
                    img = Image(image_data, width=170*mm, height=120*mm)
                    story.append(img)
                    story.append(Spacer(1, 20))
                except Exception as e:
                    print(f"이미지 추가 오류: {e}")
            
            # 가구 목록 제목
            story.append(Paragraph("목록", heading_style))
            
            # 가구 정보 테이블 생성
            table_data = []
            table_data.append(['제품명', '브랜드', '타입', '가격', '크기'])
            
            for item in furniture_items:
                furniture = item.furniture
                
                # 가격 포맷팅
                price_str = f"{furniture.price:,}원" if furniture.price else "가격 정보 없음"
                
                # 크기 정보
                if furniture.width and furniture.depth and furniture.height:
                    size_str = f"{furniture.width}×{furniture.depth}×{furniture.height}mm"
                else:
                    size_str = "크기 정보 없음"
                
                table_data.append([
                    furniture.name or "이름 없음",
                    furniture.brand or "브랜드 정보 없음", 
                    furniture.type or "타입 정보 없음",
                    price_str,
                    size_str
                ])
            
            # 테이블 생성 및 스타일 적용
            table = Table(table_data, colWidths=[50*mm, 35*mm, 25*mm, 30*mm, 40*mm])
            table.setStyle(TableStyle([
                # 헤더 스타일
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), self.korean_font_bold),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                
                # 데이터 행 스타일
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), self.korean_font_name),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                
                # 전체 테이블 스타일
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#BDC3C7')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')])
            ]))
            
            story.append(table)
            
            # 가구별 상세 정보
            for item in furniture_items:
                furniture = item.furniture
                story.append(Spacer(1, 15))
                
                # 가구 이름
                furniture_title_style = ParagraphStyle(
                    'FurnitureTitle',
                    parent=styles['Heading3'],
                    fontSize=14,
                    spaceAfter=10,
                    textColor=colors.HexColor('#2C3E50'),
                    fontName=self.korean_font_bold
                )
                story.append(Paragraph(furniture.name or "이름 없음", furniture_title_style))
                
                # 상세 정보
                details = []
                if furniture.description:
                    details.append(f"<b>설명:</b> {furniture.description}")
                if furniture.seat_height:
                    details.append(f"<b>좌석 높이:</b> {furniture.seat_height}mm")
                if furniture.link:
                    details.append(f"<b>제품 바로가기:</b> {furniture.link}")
                
                for detail in details:
                    story.append(Paragraph(detail, normal_style))
            
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