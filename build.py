import PyInstaller.__main__
import os
import shutil
import platform
import sys

def build():
    print(f"Python 버전: {sys.version}")
    print(f"운영체제: {platform.system()} {platform.release()}")
    print(f"아키텍처: {platform.machine()}")
    
    # 빌드 전 캐시 폴더 정리
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    
    # spec 파일을 사용하여 빌드
    PyInstaller.__main__.run([
        'LivingCollageMaker.spec',
        '--clean',
        '--noconfirm',
    ])
    
    print("\n빌드가 완료되었습니다. dist 폴더에서 실행 파일을 확인하세요.")
    print("실행 파일 경로:", os.path.join('dist', 'LivingCollageMaker'))

if __name__ == '__main__':
    build() 