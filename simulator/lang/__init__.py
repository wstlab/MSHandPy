import os
import sys

LANG_DIR = os.path.dirname(__file__)

LANGUAGES = {
    'zh_CN': '中文',
    'en_US': 'English',
    'ja_JP': '日本語',
    'ko_KR': '한국어',
    'fr_FR': 'Français',
    'de_DE': 'Deutsch',
    'es_ES': 'Español',
    'ru_RU': 'Русский',
}

_current_lang = 'zh_CN'
_current_lang_data = None


def load_language(lang_code):
    global _current_lang, _current_lang_data
    
    if lang_code not in LANGUAGES:
        lang_code = 'zh_CN'
    
    try:
        module = __import__(f'simulator.lang.{lang_code}', fromlist=['lang'])
        _current_lang_data = module.lang
        _current_lang = lang_code
        return True
    except Exception as e:
        print(f"⚠️ 加载语言包失败 {lang_code}: {e}")
        return False


def t(key, default=None):
    if _current_lang_data is None:
        load_language('zh_CN')
    
    return _current_lang_data.get(key, default or key)


def get_current_lang():
    return _current_lang


def get_language_name(lang_code):
    return LANGUAGES.get(lang_code, lang_code)


def get_all_languages():
    return LANGUAGES


load_language('zh_CN')