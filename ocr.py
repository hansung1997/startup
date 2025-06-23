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

'''
[본인 확인용]
KEEP_WORDS - 텍스트를 정제할 때(노이즈/불필요 단어 제거), '중요 기능어, 대명사, 접속사, 전치사 등은 무조건 남겨야 함'
is_complete_sentence - 번역 타이밍에서 "이제 번역해도 되는 완결 문장인가?"를 구두점(., ?, !) 기준으로 체크
'''

# 캐시 파일 경로
OCR_CACHE_PATH = "ocr_cache.json" #OCR 결과와 번역 캐시 저장용
ocr_cache = []

#영어문장 정제/교정에 활용
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
TRANSLATE_TRIGGER_SENTENCES = 2  # 번역 트리거: 2개 이상의 문장(구두점) 나오면

#spacy로 대조 후 유사한 단어 처리 시 벡터저장.
nlp = spacy.load("en_core_web_md")  # 중간 크기 모델 (벡터 있음)

# 사전 준비 (한 번만 처리) 단어들 불러오기.
valid_word_docs = {word: nlp(word) for word in KEEP_WORDS}

def should_translate_now(word_buffer):
    merged = " ".join(word_buffer)
    # 완결 구두점 개수 세기
    sentence_end_count = len(re.findall(r"[.?!]", merged))
    return sentence_end_count >= TRANSLATE_TRIGGER_SENTENCES

#단어 조합이 중복되지 않을 경우에만 캐시에 추가
def is_unique_combination(words, cache, threshold=0.85):
    sentence = " ".join(words)
    return not any(is_similar(sentence, entry["원문"], threshold) for entry in cache)

#한 문장이 완결(마침표, 물음표, 느낌표 등)로 끝났는지 체크 전치사, 접속사 등으로 끝나면 번역하지 않음
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

#OCR 추출 텍스트에서 불필요한 특수문자 제거
def clean_text(text):
    '''
    KEEP_WORDS에 있는 기능어는 무조건 남김
    Spacy로 유사 단어 자동 교정 지원(활성화 시)
    '''

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

#입력 이미지(OpenCV) → 그레이스케일 변환 → 블러(잡음 감소) → 이진화 → 리사이즈
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

    return cv_image

# 이미지 전처리 및 OCR-번역 처리 함수
def extract_text(image, delay=TRANSLATION_DELAY, scale_factor=1.5, lower_color=(0, 0, 0), upper_color=(255, 255, 255)):
    #디버그
    #print(f"[extract_text] 입력 타입: {type(image)}, shape: {getattr(image, 'shape', None)}")
    #if image is None or not hasattr(image, 'shape'):
    #    print("[extract_text] 입력 이미지가 None이거나 유효하지 않음!")
    #    return None
    
    global word_buffer, buffer_timestamp, ocr_cache # 전역 버퍼와 캐시 사용

    now = time.time() # 현재 시각(타임스탬프) 저장

    # --- 이미지 전처리 단계 ---
    image = smart_resize(image, max_scale=0.8, min_height_ratio=0.1) # 크기 자동 조정
    processed_image = preprocess_image(image, scale_factor, lower_color, upper_color) # 밝기/마스크/블러 등 적용

    try:
        config = r'--oem 3 --psm 11'  # pytesseract 옵션: LSTM 기반 + 단일 텍스트라인 추정
        ocr_result = pytesseract.image_to_string(processed_image, lang='eng', config=config).strip()  # OCR로 텍스트 추출
        cleaned_text = clean_text(ocr_result) # 텍스트 전처리(특수문자 정리, 단어 교정 등)
    except Exception as e:
        print(f"[OCR 오류] {e}") # 오류 발생 시 출력
        return None # 실패시 None 반환

    if not cleaned_text: # 텍스트가 비어 있으면
        return None

    words = cleaned_text.split() # 정제된 텍스트를 단어 단위로 분할

    new_words_added = False # 새 단어 추가 여부 플래그
    for word in words:
        # 중복 단어 버퍼링 방지
        if word not in word_buffer:
            word_buffer.append(word) # 새로운 단어만 버퍼에 추가
            new_words_added = True # 플래그 활성화

    if new_words_added:
        buffer_timestamp = now # 마지막 단어 추가 시각 갱신

    # --- 번역 조건 검사: 내부 함수로 정의 ---
    def should_translate_now():
        if len(word_buffer) >= MIN_WORDS_FOR_TRANSLATION: # 단어 개수가 기준 이상이면
            return True
        if word_buffer and word_buffer[-1][-1] in ".!?": # 마지막 단어가 문장부호로 끝나면
            return True
        if now - buffer_timestamp >= delay: # 버퍼에 머문 시간이 지연 기준 이상이면
            return True
        return False

    # 조건 충족 시 번역 시도
    if should_translate_now():
        full_sentence = " ".join(word_buffer).strip() # 버퍼 전체를 한 문장으로 조립

        # --- 중복 번역 방지 ---
        is_duplicate = any(is_similar(full_sentence, entry["원문"], threshold=0.85) for entry in ocr_cache)
        if not is_duplicate:
            try:
                translated = translate_text(full_sentence) # 번역 API 호출
                print(f"문장 번역 완료: {full_sentence} → {translated}") # 번역 결과 출력
                ocr_cache.append({"원문": full_sentence, "번역문": translated}) # 캐시에 저장
                save_cache_to_file() # 캐시 파일 저장
            except Exception as e:
                print(f"[번역 오류] {e}") # 번역 과정에서 오류 발생 시 출력
            word_buffer.clear() # 버퍼 초기화
            return translated # 번역 결과 반환
        else:
            print(f"[중복 문장 감지 → 번역 생략]: \"{full_sentence}\"") # 중복 시 메시지 출력
            word_buffer.clear() # 버퍼 초기화

    return None # 번역 조건이 안 맞으면 None 반환

def load_cache_from_file():
    global ocr_cache #이미 번역된 문장을 담아두는 캐시 리스트 (JSON 파일로 저장/불러오기)
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