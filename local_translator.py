import re
import os
import json
import unicodedata
from difflib import get_close_matches

# 파일 경로
LOCAL_DATA_FILE = "translated_local_data.json"

# 데이터 캐시
local_translation_data = {}
local_reverse_data = {}

def correct_common_ocr_mistakes(text: str) -> str:
    """
    OCR에서 자주 잘못 인식되는 문자들 보정
    예: |, !, l → I 등
    """
    replacements = {
        "|": "I",
        "!": "I",
        "l": "I",  # 필요한 경우 유지
        "“": "\"", "”": "\"",
        "‘": "'", "’": "'",
        "—": "-", "–": "-",
        "…": "...",
    }
    for wrong, correct in replacements.items():
        text = text.replace(wrong, correct)
    return text


def normalize_key(text: str) -> str:
    """
    텍스트 정규화 함수:
    - 알파벳, 숫자, 쉼표, 공백만 남김
    - 기타 특수문자 제거
    - 소문자 변환 + 양 끝 공백 제거
    """
    text = correct_common_ocr_mistakes(text)
    text = re.sub(r"[^a-zA-Z0-9, ]+", "", text)  # 불필요한 특수문자 제거
    return text.strip().lower()

def load_local_translation_data():
    """로컬 번역 JSON 파일을 로딩하여 딕셔너리 구성"""
    global local_translation_data, local_reverse_data
    if not os.path.exists(LOCAL_DATA_FILE):
        print(f"⚠️ 로컬 번역 파일이 존재하지 않음: {LOCAL_DATA_FILE}")
        return

    try:
        with open(LOCAL_DATA_FILE, "r", encoding="utf-8") as f:
            entries = json.load(f)
            for entry in entries:
                en_key = normalize_key(entry["en"])
                ko_val = entry["ko"].strip()
                local_translation_data[en_key] = ko_val
                local_reverse_data[ko_val] = entry["en"].strip()
        print(f"📘 로컬 번역 데이터 로드 완료: {len(local_translation_data)}개")
    except Exception as e:
        print(f"⚠️ 로컬 데이터 로딩 실패: {e}")

def translate_with_local(text: str) -> str:
    """로컬 데이터에서 정확히 일치하는 번역 반환"""
    if not local_translation_data:
        load_local_translation_data()
    return local_translation_data.get(normalize_key(text), "[로컬 번역 없음]")

def translate_with_fuzzy(text: str, cutoff=0.9) -> str:
    if not local_translation_data:
        load_local_translation_data()

    normalized = normalize_key(text).lower()
    match = get_close_matches(normalized, local_translation_data.keys(), n=1, cutoff=cutoff)

    if match:
        return local_translation_data[match[0]]
    return "[로컬 번역 없음]"

def reverse_translate_local(korean_text: str) -> str:
    """한글 → 영어로 역번역 (선택적 기능)"""
    if not local_reverse_data:
        load_local_translation_data()
    return local_reverse_data.get(korean_text.strip(), "[역번역 없음]")
