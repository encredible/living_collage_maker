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
        if hasattr(self, '_image_cache') and self._image_cache is not None:
            self._image_cache.clear()
        if hasattr(self, '_image_cache_time') and self._image_cache_time is not None:
            self._image_cache_time.clear()
        
        # get_furniture_list의 lru_cache 클리어
        # 이 부분은 SupabaseClient 인스턴스가 살아있는 동안에만 의미가 있을 수 있으나,
        # __del__ 에서 호출될 때를 대비하여 hasattr로 lru_cache 래핑된 메소드가 있는지 확인하는 것이 더 안전할 수 있음.
        # 하지만 일반적으로 lru_cache는 클래스 레벨이나 함수 레벨에 적용되므로 인스턴스 삭제 시 
        # 명시적으로 인스턴스의 cache_clear()를 호출하는 것이 일반적인 패턴은 아님.
        # 여기서는 기존 로직을 유지하되, AttributeError 가능성을 줄이기 위해 hasattr를 사용할 수 있지만,
        # self.get_furniture_list가 존재하지 않을 가능성은 낮으므로 일단 유지.
        if hasattr(self, 'get_furniture_list') and hasattr(self.get_furniture_list, 'cache_clear'):
            self.get_furniture_list.cache_clear()
    
    def __del__(self):
        """객체가 삭제될 때 캐시 정리"""
        self.clear_cache() 