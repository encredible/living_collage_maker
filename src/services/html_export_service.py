import os
from pathlib import Path
from typing import List
from datetime import datetime

from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtGui import QPixmap, QPainter

from src.models.furniture import Furniture
from src.ui.canvas import FurnitureItem


class HtmlExportService(QObject):
    """콜라주를 HTML 형식으로 내보내는 서비스 클래스"""
    
    export_finished = pyqtSignal(bool, str)  # 성공 여부, 메시지
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def export_collage_to_html(self, canvas_widget, furniture_items: List[FurnitureItem], parent_window=None):
        """
        콜라주를 HTML 파일로 내보냅니다.
        
        Args:
            canvas_widget: Canvas 위젯 (콜라주 이미지 생성용)
            furniture_items: 가구 아이템 리스트
            parent_window: 부모 윈도우 (다이얼로그용)
        """
        try:
            # 가구 아이템이 없으면 경고
            if not furniture_items:
                self._show_warning_message(parent_window, "경고", "내보낼 콜라주가 없습니다.")
                return
            
            # 파일 저장 위치 선택
            file_path, _ = QFileDialog.getSaveFileName(
                parent_window,
                "HTML 파일로 내보내기",
                "collage.html",
                "HTML 파일 (*.html)"
            )
            
            if not file_path:
                return  # 사용자가 취소한 경우
            
            # 파일 경로 정보 추출
            file_dir = os.path.dirname(file_path)
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            html_file_path = file_path
            image_file_path = os.path.join(file_dir, f"{file_name}.png")
            
            # 콜라주 이미지 저장
            success = self._save_collage_image(canvas_widget, image_file_path)
            if not success:
                self._show_critical_message(parent_window, "오류", "콜라주 이미지 저장에 실패했습니다.")
                return
            
            # HTML 파일 생성
            html_content = self._generate_html_content(furniture_items, f"{file_name}.png")
            
            # HTML 파일 저장
            self._save_html_file(html_file_path, html_content)
            
            self._show_information_message(parent_window, "성공", f"HTML 파일이 성공적으로 저장되었습니다.\n{html_file_path}")
            self.export_finished.emit(True, "HTML 내보내기 성공")
            
        except Exception as e:
            error_msg = f"HTML 내보내기 중 오류가 발생했습니다: {str(e)}"
            self._show_critical_message(parent_window, "오류", error_msg)
            self.export_finished.emit(False, error_msg)
    
    def _save_collage_image(self, canvas_widget, image_file_path: str) -> bool:
        """콜라주 이미지를 PNG 파일로 저장합니다. (Canvas의 _generate_collage_image 사용)"""
        try:
            # Canvas의 공통 이미지 생성 메서드 사용
            image = canvas_widget._generate_collage_image()
            
            # 이미지 저장
            return image.save(image_file_path, "PNG")
            
        except Exception as e:
            print(f"이미지 저장 오류: {e}")
            return False
    
    def _generate_html_content(self, furniture_items: List[FurnitureItem], image_filename: str) -> str:
        """HTML 콘텐츠를 생성합니다."""
        current_time = datetime.now().strftime("%Y년 %m월 %d일 %H:%M")
        
        # HTML 문서 시작
        html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Living Collage - 내 콜라주</title>
    <style>
        {self._get_css_styles()}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Living Collage</h1>
            <p class="created-time">생성일: {current_time}</p>
        </header>
        
        <section class="collage-section">
            <div class="image-container">
                <img src="{image_filename}" alt="콜라주 이미지" class="collage-image">
            </div>
        </section>
        
        <section class="furniture-section">
            <div class="furniture-list">
                {self._generate_furniture_cards(furniture_items)}
            </div>
        </section>
    </div>
</body>
</html>"""
        
        return html_content
    
    def _get_css_styles(self) -> str:
        """CSS 스타일을 반환합니다."""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: white;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        
        header {
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #2C3E50;
        }
        
        h1 {
            color: #2C3E50;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        h2 {
            color: #2C3E50;
            font-size: 1.8em;
            margin-bottom: 20px;
            border-bottom: 1px solid #ddd;
            padding-bottom: 10px;
        }
        
        .created-time {
            color: #666;
            font-size: 1.1em;
        }
        
        .collage-section {
            margin-bottom: 30px;
        }
        
        .image-container {
            text-align: center;
            margin: 20px 0;
        }
        
        .collage-image {
            max-width: 100%;
            width: 100%;
            height: auto;
            border: 2px solid #2C3E50;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        
        .furniture-section {
            margin-top: 20px;
        }
        
        .furniture-list {
            display: grid;
            grid-template-columns: 1fr;
            gap: 20px;
            margin-top: 20px;
        }
        
        .furniture-card {
            background: #fff;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .furniture-card h3 {
            color: #2C3E50;
            margin-bottom: 15px;
            font-size: 1.3em;
            margin: 0;
        }
        
        .furniture-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 15px;
        }
        
        .link-inline {
            margin-left: 15px;
        }
        
        .furniture-info {
            margin-bottom: 10px;
        }
        
        .info-label {
            font-weight: bold;
            color: #555;
            display: inline-block;
            width: 80px;
        }
        
        .info-value {
            color: #333;
        }
        
        .price {
            color: #E74C3C;
            font-weight: bold;
            font-size: 1.1em;
        }
        
        .link-inline a {
            color: #2C3E50;
            text-decoration: none;
            background-color: #f8f9fa;
            padding: 6px 12px;
            border: 1px solid #2C3E50;
            border-radius: 4px;
            display: inline-block;
            transition: all 0.3s ease;
            font-size: 0.9em;
        }
        
        .link-inline a:hover {
            background-color: #2C3E50;
            color: white;
        }
        
        .no-link {
            color: #999;
            font-style: italic;
            font-size: 0.9em;
        }
        
        .list-items {
            color: #666;
        }
        """
    
    def _generate_furniture_cards(self, furniture_items: List[FurnitureItem]) -> str:
        """가구 카드들을 생성합니다."""
        cards_html = ""
        
        for item in furniture_items:
            furniture = item.furniture
            cards_html += f"""
            <div class="furniture-card">
                <div class="furniture-header">
                    <h3>{furniture.name}</h3>
                    <div class="link-inline">
                        {self._generate_link_info(furniture.link)}
                    </div>
                </div>
                
                <div class="furniture-info">
                    <span class="info-label">브랜드:</span>
                    <span class="info-value">{furniture.brand}</span>
                </div>
                
                <div class="furniture-info">
                    <span class="info-label">타입:</span>
                    <span class="info-value">{furniture.type}</span>
                </div>
                
                <div class="furniture-info">
                    <span class="info-label">가격:</span>
                    <span class="info-value price">{furniture.price:,}원</span>
                </div>
                
                {self._generate_optional_info("설명", furniture.description)}
                {self._generate_size_info(furniture)}
            </div>
            """
        
        return cards_html
    
    def _generate_optional_info(self, label: str, value: str) -> str:
        """선택적 정보를 생성합니다."""
        if value and value.strip():
            return f"""
                <div class="furniture-info">
                    <span class="info-label">{label}:</span>
                    <span class="info-value">{value}</span>
                </div>
            """
        return ""
    
    def _generate_size_info(self, furniture: Furniture) -> str:
        """크기 정보를 생성합니다."""
        size_parts = []
        if furniture.width > 0:
            size_parts.append(f"가로 {furniture.width}mm")
        if furniture.depth > 0:
            size_parts.append(f"세로 {furniture.depth}mm")
        if furniture.height > 0:
            size_parts.append(f"높이 {furniture.height}mm")
        
        size_info = ""
        if size_parts:
            size_value = " × ".join(size_parts)
            size_info += f"""
                <div class="furniture-info">
                    <span class="info-label">크기:</span>
                    <span class="info-value">{size_value}</span>
                </div>
            """
        
        if furniture.seat_height is not None and furniture.seat_height > 0:
            size_info += f"""
                <div class="furniture-info">
                    <span class="info-label">좌석높이:</span>
                    <span class="info-value">{furniture.seat_height}mm</span>
                </div>
            """
        
        return size_info
    
    def _generate_list_info(self, label: str, items: List[str]) -> str:
        """리스트 형태의 정보를 생성합니다."""
        if items and len(items) > 0:
            items_str = ", ".join(items)
            return f"""
                <div class="furniture-info">
                    <span class="info-label">{label}:</span>
                    <span class="info-value list-items">{items_str}</span>
                </div>
            """
        return ""
    
    def _generate_link_info(self, link: str) -> str:
        """링크 정보를 생성합니다."""
        if link and link.strip():
            return f'<a href="{link}" target="_blank">제품 바로가기</a>'
        else:
            return '<span class="no-link">링크 없음</span>'
    
    def _save_html_file(self, file_path: str, content: str):
        """HTML 파일을 저장합니다."""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _show_information_message(self, parent, title: str, message: str):
        """정보 메시지를 표시합니다."""
        QMessageBox.information(parent, title, message)
    
    def _show_warning_message(self, parent, title: str, message: str):
        """경고 메시지를 표시합니다."""
        QMessageBox.warning(parent, title, message)
    
    def _show_critical_message(self, parent, title: str, message: str):
        """오류 메시지를 표시합니다."""
        QMessageBox.critical(parent, title, message) 