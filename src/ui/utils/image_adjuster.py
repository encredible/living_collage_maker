import weakref
from PyQt6.QtGui import QPixmap, QImage, QColor
from PyQt6.QtCore import Qt


class ImageAdjuster:
    """이미지 색온도, 밝기, 채도 조정을 처리하는 클래스"""
    
    _effect_cache = {} # 효과 캐시 (key: (픽셀맵 ID, 크기, 색온도, 밝기, 채도))
    _cache_size = 50
    
    _temperature_lut = {}  # 색온도 룩업 테이블 (미리 계산된 값)
    _initialized = False   # 초기화 여부 플래그
    _use_numpy = True      # NumPy 벡터화 처리 사용 여부
    
    _image_id_counter = 0
    _image_id_map = weakref.WeakKeyDictionary()  # QPixmap 객체 -> 고유 ID 매핑
    
    @staticmethod
    def initialize():
        """이미지 조정 시스템을 초기화합니다 (룩업 테이블 생성, NumPy 사용 가능 여부 확인)."""
        if ImageAdjuster._initialized:
            return
        
        ImageAdjuster._init_temperature_lut()
        
        try:
            import numpy as np
            np.array([1, 2, 3]) # NumPy 사용 가능성 테스트
            ImageAdjuster._use_numpy = True
        except Exception:
            ImageAdjuster._use_numpy = False
        
        ImageAdjuster._initialized = True
    
    @staticmethod
    def _init_temperature_lut():
        """색온도 변환을 위한 룩업 테이블 (LUT)을 미리 계산하여 초기화합니다."""
        temps = [2000, 2500, 3000, 3500, 4000, 4500, 5000, 5500, 6000, 6500, 7000, 7500, 8000, 8500, 9000, 9500, 10000]
        for temp in temps:
            ImageAdjuster._temperature_lut[temp] = ImageAdjuster.calculate_temperature_rgb(temp)
    
    @staticmethod
    def get_temperature_rgb(temperature):
        """주어진 색온도에 가장 가까운, 사전 계산된 RGB 계수를 반환하거나 직접 계산합니다."""
        if temperature in ImageAdjuster._temperature_lut:
            return ImageAdjuster._temperature_lut[temperature]
            
        closest_temp = min(ImageAdjuster._temperature_lut.keys(), key=lambda x: abs(x - temperature))
        
        if abs(closest_temp - temperature) <= 1000: # 1000K 이내 차이면 LUT 값 사용
            return ImageAdjuster._temperature_lut[closest_temp]
            
        return ImageAdjuster.calculate_temperature_rgb(temperature) # 그 외 직접 계산
    
    @staticmethod
    def apply_effects(pixmap, color_temp, brightness, saturation):
        """이미지에 색온도, 밝기, 채도 효과를 적용합니다. NumPy 사용 가능 시 벡터화 처리합니다."""
        if pixmap is None or pixmap.isNull():
            # print("[ImageAdjuster] 입력 이미지가 없습니다.") # TODO: 로깅 고려
            return QPixmap()

        try:
            if pixmap not in ImageAdjuster._image_id_map:
                ImageAdjuster._image_id_counter += 1
                ImageAdjuster._image_id_map[pixmap] = ImageAdjuster._image_id_counter
            image_id = ImageAdjuster._image_id_map[pixmap]
            
            size_key = f"{pixmap.width()}x{pixmap.height()}"
            cache_key = (image_id, size_key, round(color_temp), round(brightness), round(saturation))
            
            if cache_key in ImageAdjuster._effect_cache:
                return ImageAdjuster._effect_cache[cache_key].copy() # 캐시된 결과의 복사본 반환
            
            pixmap_copy = pixmap.copy() # 원본 변경 방지를 위해 복사본 사용
            
            if ImageAdjuster._use_numpy:
                result_pixmap = ImageAdjuster.apply_effects_numpy(
                    pixmap_copy, color_temp, brightness, saturation
                )
            else:
                # NumPy 미사용 시 QImage 기반 픽셀 단위 처리
                image = pixmap_copy.toImage()
                width, height = image.width(), image.height()
                result_image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
                
                r_temp, g_temp, b_temp = ImageAdjuster.get_temperature_rgb(color_temp)
                brightness_factor = brightness / 100.0
                saturation_factor = saturation / 100.0
                
                # 픽셀 값 변환 LUT 생성 (색온도, 밝기 선적용)
                pixel_transform_lut = {
                    v_in: (
                        min(255, max(0, int(v_in * r_temp * brightness_factor))),
                        min(255, max(0, int(v_in * g_temp * brightness_factor))),
                        min(255, max(0, int(v_in * b_temp * brightness_factor)))
                    ) for v_in in range(256)
                }
                
                pixel_step = 2 if max(width, height) > 200 else 1 # 성능 최적화를 위한 픽셀 스킵
                
                for y in range(0, height, pixel_step):
                    for x in range(0, width, pixel_step):
                        px_color = image.pixelColor(x, y)
                        alpha = px_color.alpha()
                        
                        r_adj, g_adj, b_adj = pixel_transform_lut[px_color.red()], \
                                              pixel_transform_lut[px_color.green()], \
                                              pixel_transform_lut[px_color.blue()]
                        
                        r, g, b = r_adj[0], g_adj[1], b_adj[2] # 값 추출 (여기서 이미 (r,g,b) 튜플이므로 불필요할 수 있음)
                                                
                        # 채도 적용
                        gray = int(0.299 * r + 0.587 * g + 0.114 * b)
                        r = min(255, max(0, int(gray + (r - gray) * saturation_factor)))
                        g = min(255, max(0, int(gray + (g - gray) * saturation_factor)))
                        b = min(255, max(0, int(gray + (b - gray) * saturation_factor)))
                        
                        final_color = QColor(r, g, b, alpha)
                        
                        for py_off in range(pixel_step): # 스킵된 픽셀 채우기
                            for px_off in range(pixel_step):
                                if (y + py_off) < height and (x + px_off) < width:
                                    result_image.setPixelColor(x + px_off, y + py_off, final_color)
                
                result_pixmap = QPixmap.fromImage(result_image)
            
            final_result = result_pixmap.copy() # 최종 결과도 깊은 복사하여 캐시 및 반환
            
            if len(ImageAdjuster._effect_cache) >= ImageAdjuster._cache_size: # 캐시 관리
                ImageAdjuster._effect_cache.pop(next(iter(ImageAdjuster._effect_cache)))
            ImageAdjuster._effect_cache[cache_key] = final_result.copy()
            
            return final_result
            
        except Exception as e:
            # import traceback # 개발 시 상세 오류 확인용
            # traceback.print_exc()
            # print(f"[ImageAdjuster] 이미지 처리 중 오류 발생: {e}") # TODO: 로깅 라이브러리로 대체 고려
            return pixmap.copy() # 오류 발생 시 원본의 복사본 반환
            
    @staticmethod
    def apply_effects_numpy(pixmap, color_temp, brightness, saturation):
        """NumPy 벡터화를 사용한 효율적인 이미지 처리"""
        try:
            import numpy as np
            
            image = pixmap.toImage() # QImage로 변환 (Deep Copy)
            original_format = image.format() # 원본 포맷 유지
            width = image.width()
            height = image.height()
            
            # QImage의 constBits()를 사용하여 메모리 직접 접근 후 NumPy 배열로 변환 (읽기 전용)
            ptr = image.constBits()
            ptr.setsize(image.sizeInBytes())
            # 변경 가능한 복사본 생성
            arr = np.array(ptr).reshape(height, width, 4).copy()
            
            alpha = arr[:, :, 3].copy() # 알파 채널
            transparent_mask = (alpha == 0) # 완전 투명 픽셀 마스크
            semitransparent_mask = np.logical_and(alpha > 0, alpha < 255) # 반투명 픽셀 마스크
            
            # QImage는 BGRA 순서이므로, RGB 채널 추출
            r = arr[:, :, 2].astype(np.float32)
            g = arr[:, :, 1].astype(np.float32)
            b = arr[:, :, 0].astype(np.float32)
            
            r_temp, g_temp, b_temp = ImageAdjuster.get_temperature_rgb(color_temp)
            brightness_factor = brightness / 100.0
            saturation_factor = saturation / 100.0
            
            # 완전 투명 픽셀의 원본 RGB 값 저장 (색상 처리 후 복원용)
            r_transparent = r[transparent_mask].copy() if np.any(transparent_mask) else None
            g_transparent = g[transparent_mask].copy() if np.any(transparent_mask) else None
            b_transparent = b[transparent_mask].copy() if np.any(transparent_mask) else None
            
            # 색온도 및 밝기 적용
            r *= r_temp * brightness_factor
            g *= g_temp * brightness_factor
            b *= b_temp * brightness_factor
            
            # 채도 적용
            gray = 0.299 * r + 0.587 * g + 0.114 * b
            r = gray + (r - gray) * saturation_factor
            g = gray + (g - gray) * saturation_factor
            b = gray + (b - gray) * saturation_factor
            
            # 값 범위를 [0, 255]로 제한하고 uint8로 변환
            r = np.clip(r, 0, 255).astype(np.uint8)
            g = np.clip(g, 0, 255).astype(np.uint8)
            b = np.clip(b, 0, 255).astype(np.uint8)
            
            # 알파값이 0인 완전 투명한 픽셀의 RGB 값 복원
            # 투명 픽셀은 보이지 않으므로 원래 색상을 유지
            if np.any(transparent_mask) and r_transparent is not None:
                r[transparent_mask] = r_transparent
                g[transparent_mask] = g_transparent
                b[transparent_mask] = b_transparent
            
            # 반투명 픽셀의 경우, 프리멀티플라이드 알파 처리
            if np.any(semitransparent_mask):
                alpha_factor = alpha[semitransparent_mask].astype(np.float32) / 255.0
                # 프리멀티플라이드 알파 처리는 제거 (이미지 깨짐 현상 방지)
                # 대신 원래 색상값 그대로 유지
            
            # 결과 배열에 다시 채널 할당 (BGRA 순서)
            arr[:, :, 0] = b
            arr[:, :, 1] = g
            arr[:, :, 2] = r
            arr[:, :, 3] = alpha  # 원본 알파 채널 유지
            
            # QImage 생성 (원본 포맷 유지)
            result_image = QImage(arr.data, width, height, image.bytesPerLine(), original_format)
            
            # 고품질 변환 설정
            result_pixmap = QPixmap.fromImage(result_image)
            
            # 항상 복사본 반환
            return result_pixmap.copy()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[ImageAdjuster] NumPy 이미지 처리 오류: {e}")
            # 에러 발생 시 기본 방식으로 처리
            ImageAdjuster._use_numpy = False
            return pixmap.copy()
    
    @staticmethod
    def calculate_temperature_rgb(temperature):
        """색온도에 따른 RGB 계수를 계산합니다."""
        # 기준 색온도 (6500K)
        reference_temp = 6500
        
        r_factor = 1.0
        g_factor = 1.0
        b_factor = 1.0
        
        # 색온도에 따른 RGB 조정 계수 계산
        if temperature < reference_temp:
            # 따뜻한 색상 (노란색/주황색 쪽으로)
            temp_factor = (reference_temp - temperature) / reference_temp
            r_factor = 1.0 + temp_factor * 0.2  # 빨간색 증가
            g_factor = 1.0
            b_factor = 1.0 - temp_factor * 0.6  # 파란색 크게 감소
        else:
            # 차가운 색상 (파란색 쪽으로)
            temp_factor = (temperature - reference_temp) / reference_temp
            r_factor = 1.0 - temp_factor * 0.4  # 빨간색 감소
            g_factor = 1.0 - temp_factor * 0.2  # 초록색 약간 감소
            b_factor = 1.0 + temp_factor * 0.2  # 파란색 증가
        
        return r_factor, g_factor, b_factor 