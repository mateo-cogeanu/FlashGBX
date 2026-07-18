# core/config_manager.py
import configparser
import os
from pathlib import Path


class ConfigManager:
    APP_VERSION = "1.1.0"
    
    def __init__(self, config_file="config.ini"):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.load_config()
    
    def load_config(self):
        if os.path.exists(self.config_file):
            self.config.read(self.config_file, encoding='utf-8')
            
            if not self.config.has_option('SETTINGS', 'version') or \
               self.config.get('SETTINGS', 'version') != self.APP_VERSION:
                self.config.set('SETTINGS', 'version', self.APP_VERSION)
                self.save_config()
        else:
            self.config['SETTINGS'] = {
                'version': self.APP_VERSION,
                'language': 'english',
                'default_preset': 'Default',
                'max_workers': str(min(4, os.cpu_count() or 4)),
            }
            
            self.config['PATHS'] = {
                'output_folder': '',
                'last_video_path': '',
            }
            
            self.config['UI'] = {
                'preview_mode': 'False',
            }
            
            self.save_config()
    
    def save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as configfile:
                self.config.write(configfile)
            return True
        except Exception:
            return False
    
    def get(self, section, key, default=None):
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default
    
    def getboolean(self, section, key, default=False):
        try:
            return self.config.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default
    
    def getint(self, section, key, default=0):
        try:
            return self.config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default
    
    def set(self, section, key, value):
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = str(value)
        self.save_config()
