import json
import os
import requests
from config import load_config
from googletrans import Translator as GoogleTranslator
from local_translator import translate_with_local, normalize_key, translate_with_fuzzy



#구글 번역 API
translator_google = GoogleTranslator()

#DeepL API
DEEPL_API_KEY = "199T3kUi6spHu3OCs"

#번역 데이터 파일로 저장, 로컬은 전용 말뭉치 사용
CACHE_FILE = "translation_cache.json"
translation_cache = {}
local_translation_data = {}

def load_translation_cache():
    global translation_cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                translation_cache = json.load(f)
            print(f"✅ 번역 캐시 {CACHE_FILE} 로드 완료")
        except Exception as e:
            print(f"⚠️ 캐시 로드 실패: {e}")

def save_translation_cache():
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(translation_cache, f, ensure_ascii=False, indent=2)
        print(f"💾 번역 캐시 {CACHE_FILE} 저장 완료")
    except Exception as e:
        print(f"⚠️ 캐시 저장 실패: {e}")

def translate_with_google(text, dest='ko'):
    try:
        translated = translator_google.translate(text, dest=dest)
        return translated.text
    except Exception as e:
        return f"[Google 오류] {e}"

def translate_with_deepl(text, target_lang='KO'):
    url = "https://api-free.deepl.com/v2/translate"
    headers = {
        "Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}"
    }
    data = {
        "text": text,
        "target_lang": target_lang
    }

    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        result = response.json()
        return result['translations'][0]['text']
    except Exception as e:
        return f"[DeepL 오류] {e}"

def translate_text(text, dest='ko'):
    normalized_key = normalize_key(text)

    config_data = load_config()  # ← 여기서 매번 최신 상태 반영!
    api_type = config_data.get("api", "google")

    try:
        if api_type == "google":
            translated = translate_with_google(text, dest=dest)
        elif api_type == "deepl":
            translated = translate_with_deepl(text, target_lang='KO')
        else:
            return "[번역 실패] 지원하지 않는 API"
    except Exception as e:
        return f"[번역 실패]: {e}"

    translation_cache[normalized_key] = translated  #translated가 없는 경우 캐시에 저장되지 않던 문제 해결
    return translated
