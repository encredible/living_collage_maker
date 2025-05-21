import os
import time
from functools import lru_cache

from dotenv import load_dotenv
from supabase import create_client, Client


class SupabaseClient:
    def __init__(self):
        load_dotenv()
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL과 SUPABASE_KEY가 .env 파일에 설정되어 있어야 합니다.")
        
        self.client: Client = create_client(
            supabase_url=self.url,
            supabase_key=self.key
        )
        
        # 이미지 캐시
        self._image_cache = {}
        self._image_cache_time = {}
        self._cache_duration = 3600  # 1시간
    
    @lru_cache(maxsize=100)
    def get_furniture_list(self):
        """가구 목록을 가져옵니다. (캐시 적용)"""
        response = self.client.table("furniture").select(
            "id,name,brand,type,price,image_filename,description,link,color,locations,styles,width,depth,height,seat_height,author,created_at"
        ).execute()
        return response.data
    
    def get_furniture_image(self, filename: str):
        """가구 이미지를 가져옵니다. (메모리 캐시 적용)"""
        current_time = time.time()
        
        # 캐시된 이미지가 있고 유효한 경우
        if filename in self._image_cache:
            cache_time = self._image_cache_time.get(filename, 0)
            if current_time - cache_time < self._cache_duration:
                return self._image_cache[filename]
        
        try:
            response = self.client.storage.from_("furniture-images").download(filename)
            
            # 캐시 업데이트
            self._image_cache[filename] = response
            self._image_cache_time[filename] = current_time
            
            return response
        except Exception as e:
            print(f"이미지 다운로드 중 오류 발생: {e}")
            return None
    
    def clear_cache(self):
        """캐시를 모두 삭제합니다."""
        self._image_cache.clear()
        self._image_cache_time.clear()
        self.get_furniture_list.cache_clear()
    
    def __del__(self):
        """객체가 삭제될 때 캐시 정리"""
        self.clear_cache() 