from translator import load_translation_cache, save_translation_cache
from ocr import load_cache_from_file, save_cache_to_file

def load_all_caches():
    load_translation_cache()
    load_cache_from_file()

def save_all_caches():
    save_translation_cache()
    save_cache_to_file()
