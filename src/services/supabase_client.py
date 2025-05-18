import os
from supabase import create_client, Client
from dotenv import load_dotenv

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
    
    def get_furniture_list(self):
        """가구 목록을 가져옵니다."""
        response = self.client.table("furniture").select("*").execute()
        return response.data
    
    def get_furniture_image(self, filename: str):
        """가구 이미지를 가져옵니다."""
        try:
            response = self.client.storage.from_("furniture-images").download(filename)
            return response
        except Exception as e:
            print(f"이미지 다운로드 중 오류 발생: {e}")
            return None 