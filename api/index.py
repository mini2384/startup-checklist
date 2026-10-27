import os
import sys

# 프로젝트 루트 경로를 sys.path에 추가하여 app.py 및 모듈 인식
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app import app

# Vercel이 WSGI 애플리케이션으로 인식할 수 있도록 export
app = app
