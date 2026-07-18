# utils/translator.py
import configparser
import os


class Translator:
    LANGUAGE_CODES = {
            "english": "eng",
            "spanish": "spa",
            "br_portuguese": "brp",
            "french": "fra",
            "german": "deu",
            "italian": "ita",
            "portuguese": "por",
            "dutch": "nld",
            "polish": "pol", 
            "turkish": "tur",
            "vietnamese": "vie",
            "indonesian": "ind",
            "hindi": "hin",
            "russian": "rus",
            "japanese": "jpn",
            "chinese_simplified": "zhs",
            "chinese_traditional": "zht",
            "korean": "kor",
        }
    def __init__(self, lang_dir="lang", default_lang="english"):
        self.lang_dir = lang_dir
        self.default_lang = default_lang
        self.translations = {}
        self.current_lang = default_lang
        self.load_language(default_lang)

    def load_language(self, lang_key):
        code = self.LANGUAGE_CODES.get(lang_key, "eng")
        file_path = os.path.join(self.lang_dir, f"{code}.ini")
        if not os.path.exists(file_path):
            print(f"Warning: Language file '{file_path}' not found. Falling back to eng.ini.")
            code = "eng"
            file_path = os.path.join(self.lang_dir, "eng.ini")
        config = configparser.ConfigParser(interpolation=None)
        config.read(file_path, encoding='utf-8')
        if 'lang' not in config:
            raise ValueError(f"Invalid format: '{file_path}' must have [lang] section.")
        self.translations = config['lang']
        self.current_lang = code

    def tr(self, key, **kwargs):
        text = self.translations.get(key, f"??{key}??")
        
        if kwargs:
            try:
                text = text.format(**kwargs)
            except Exception as e:
                print(f"Error formatting translation '{key}': {e}")
                return f"??{key}??"
        
        text = text.replace('\\n', '\n')
        
        return text
