import json
import os

CONFIG_PATH = "./config.json"


# 레이아웃 불러오기
def load_layout():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}  # 파일 없으면 빈 값 반환


# 레이아웃 저장
def save_config(data):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# 기존 코드 호환용
# translator.py에서 from config import load_config 처리 시 대응
def load_config():
    return load_layout()
