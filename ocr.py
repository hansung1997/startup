#이 아래는 tesseract ocr을 이용하여 ocr 구현.
import pytesseract
import numpy as np
import json
import os
import cv2
import re
import spacy
import time

from translator import translate_text
from difflib import SequenceMatcher

# 캐시 파일 경로
OCR_CACHE_PATH = "ocr_cache.json" #OCR 결과와 번역 캐시 저장용
ocr_cache = []
KEEP_WORDS = {
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
    "us", "them", "my", "your", "our", "their", "his", "its", "mine",
    "yours", "ours", "theirs",         # 대명사
    "me", "him", "her", "us", "them", "my", "your",      # 목적격/소유격
    "in", "on", "at", "to", "from", "for", "by", "with", "about", "into",
    "over", "under", "through", "of", "off", "along", "around", "before",
    "after", "between", "among",        # 전치사
    "a", "an", "the",                                     # 관사
    "and", "or", "but", "because", "if", "when", "while", "although",
    "though", "unless", "since",     # 접속사 등
    "not", "no", "yes", "do", "does", "did", "will", "would", "can",
    "could", "shall", "should", "must", "might", "may", #기타 필수 기능어

} #주요 단어 목록 (기능어, 대명사 등). 문장을 정제할 때 유지 대상

# 텍스트 추출
from collections import deque

word_buffer = deque() #단어 단위로 확인 후 캐시 저장
MIN_WORDS_FOR_TRANSLATION = 5  # 최소 단어 수 기준
TRANSLATION_DELAY = 1.5        # 버퍼 유지 시간 (초)

buffer_timestamp = 0  # 마지막 단어가 추가된 시간 추적

# 버퍼 구조
text_buffer = {
    "merged_text": "",  # 전체 텍스트 버퍼
    "sentences": [],    # 문장 단위 리스트 "." 마다 나눔
    "start_time": 0
}

#spacy로 대조 후 유사한 단어 처리 시 벡터저장.
nlp = spacy.load("en_core_web_md")  # 중간 크기 모델 (벡터 있음)

# 사전 준비 (한 번만 처리) 단어들 불러오기.
valid_word_docs = {word: nlp(word) for word in KEEP_WORDS}

#구두점 또는 최소 단어 수 기준 번역 트리거
def should_translate_now(word_buffer):
    last_words = " ".join(word_buffer)
    return (
        len(word_buffer) >= MIN_WORDS_FOR_TRANSLATION or
        re.search(r"[.?!]", last_words.strip())
    )

#단어 조합이 중복되지 않을 경우에만 캐시에 추가
def is_unique_combination(words, cache, threshold=0.85):
    sentence = " ".join(words)
    return not any(is_similar(sentence, entry["원문"], threshold) for entry in cache)

def is_complete_sentence(text):
    text = text.strip()
    if not text:
        return False
    if text[-1] in '.?!':
        return True

    # 완성되지 않은 접속사/전치사 등으로 끝나는 경우는 False
    incomplete_words = {
        "and", "or", "but", "because", "so", "if", "when", "while", "although",
        "though", "unless", "since", "for", "with", "to", "from", "of", "in", "on", "at", "about", "into",
        "over", "under", "through", "off", "along", "around", "before", "after", "between", "among"
    }
    last_word = text.split()[-1].lower()
    if last_word in incomplete_words:
        return False

    return True


#텍스트 지연 함수()
def is_similar(a, b, threshold=0.9):
    return SequenceMatcher(None, a, b).ratio() >= threshold

#spacy 사용 함수. (단어 유사성 비교.) 현재는 사용 x
def get_most_similar_word(token, threshold=0.75):
    token_doc = nlp(token)
    best_match = None
    best_score = 0.0

    for ref_word, ref_doc in valid_word_docs.items():
        score = token_doc.similarity(ref_doc)
        if score > best_score and score >= threshold:
            best_score = score
            best_match = ref_word

    return best_match  # 없으면 None

def clean_text(text):
    # 특수문자 제거 (콤마 유지, 점/기호 제거)
    #text = re.sub(r"[^가-힣a-zA-Z0-9,\s]", "", text)  # 특수문자 정리
    
    #여긴 (, ' ? ! 같은 필수 특수문자는 남겨두고 제거)
    text = re.sub(r"[^가-힣a-zA-Z0-9\s,!?']", "", text)

    tokens = text.split()

    result = []
    for token in tokens:
        lower_token = token.lower()
        if lower_token in KEEP_WORDS:
            result.append(lower_token)
        elif token.isalnum() and len(token) >= 3:
            similar = get_most_similar_word(lower_token)
            if similar:
                result.append(similar)  #유사하면 교정
            else:
                result.append(token)  #유사하지 않아도 원본 그대로 유지
        else:
            result.append(token)  #기타 기호/숫자도 유지

    return " ".join(result)

def preprocess_image(cv_image, scale_factor=1.5, lower_color=(0, 0, 0), upper_color=(255, 255, 255)):

    if cv_image is None or (hasattr(cv_image, 'size') and cv_image.size == 0):
        print("[OCR 오류] 받은 이미지가 None이거나 비어 있음!")
        return None

    #이미지 전처리 함수
    #- scale_factor: 이미지 확대/축소 비율
    #- lower_color: HSV 색상 범위 하한값 (텍스트 색상)
    #- upper_color: HSV 색상 범위 상한값 (텍스트 색상)

    # 그레이스케일
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

    # 블러 + 이진화
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 확대 (작은 텍스트 대응)
    resized = cv2.resize(binary, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_LINEAR)

    # 색상 필터링 추가
    hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array(lower_color), np.array(upper_color))

    # 마스크 크기를 이미지 크기와 동일하게 조정
    mask = cv2.resize(mask, (resized.shape[1], resized.shape[0]), interpolation=cv2.INTER_NEAREST)

    # 데이터 타입이 uint8인지 확인
    if mask.dtype != np.uint8:
        mask = mask.astype(np.uint8)

    # 필터링
    filtered = cv2.bitwise_and(resized, resized, mask=mask)

    cv2.imwrite("debug_capture.png", filtered)

    return filtered  # PIL 대신(이제 사용안함) OpenCV image 반환

def smart_resize(cv_image, max_scale=1.0, min_height_ratio=0.12):
    '''
        사용자가 지정한 화면 크기를 기준으로:
        - 가로가 너무 길고,
        - 세로가 너무 작을 경우 축소를 제한
        - max_scale = 1.0은 최대 100%로 출력
    '''
    height, width = cv_image.shape[:2]

    if height / width < min_height_ratio:
        return cv_image

    if max(width, height) > 1200:
        scale = min(max_scale, 1200 / max(width, height))
        new_size = (int(width * scale), int(height * scale))
        return cv2.resize(cv_image, new_size, interpolation=cv2.INTER_AREA)




def extract_text(image, delay=TRANSLATION_DELAY, scale_factor=1.5, lower_color=(0, 0, 0), upper_color=(255, 255, 255)):
    global word_buffer, buffer_timestamp, ocr_cache

    now = time.time()

    # 이미지 전처리
    image = smart_resize(image, max_scale=0.8, min_height_ratio=0.1)
    processed_image = preprocess_image(image, scale_factor, lower_color, upper_color)

    try:
        config = r'--oem 3 --psm 11'
        ocr_result = pytesseract.image_to_string(processed_image, lang='eng', config=config).strip()
        cleaned_text = clean_text(ocr_result)
    except Exception as e:
        print(f"[OCR 오류] {e}")
        return None

    if not cleaned_text:
        return None

    words = cleaned_text.split()

    new_words_added = False
    for word in words:
        # 중복 단어 필터링
        if word not in word_buffer:
            word_buffer.append(word)
            new_words_added = True

    if new_words_added:
        buffer_timestamp = now

    def should_translate_now():
        if len(word_buffer) >= MIN_WORDS_FOR_TRANSLATION:
            return True
        if word_buffer and word_buffer[-1][-1] in ".!?":
            return True
        if now - buffer_timestamp >= delay:
            return True
        return False

    if should_translate_now():
        full_sentence = " ".join(word_buffer).strip()

        # 중복 확인
        is_duplicate = any(is_similar(full_sentence, entry["원문"], threshold=0.85) for entry in ocr_cache)
        if not is_duplicate:
            try:
                translated = translate_text(full_sentence)
                print(f"문장 번역 완료: {full_sentence} → {translated}")
                ocr_cache.append({"원문": full_sentence, "번역문": translated})
                save_cache_to_file()
            except Exception as e:
                print(f"[번역 오류] {e}")
            word_buffer.clear()
            return translated
        else:
            print(f"[중복 문장 감지 → 번역 생략]: \"{full_sentence}\"")
            word_buffer.clear()

    return None

def load_cache_from_file():
    global ocr_cache
    if os.path.exists(OCR_CACHE_PATH):
        try:
            with open(OCR_CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    ocr_cache = data
                else:
                    print("⚠️ 캐시가 리스트가 아님. 초기화합니다.")
                    ocr_cache = []
        except Exception as e:
            print(f"[OCR 캐시 로드 오류] {e}")
            ocr_cache = []

def save_cache_to_file():
    try:
        with open(OCR_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(ocr_cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[OCR 캐시 저장 오류] {e}")