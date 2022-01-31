import configparser

config_name = 'config.ini'


class Config:
    def __init__(self):
        self._config = configparser.ConfigParser()
        self._config.read('config.ini')

    def get(self, section, key, fallback=None):
        return self._config.get(section, key, fallback=fallback)

    def add(self, section, key, value):
        if not self._config.has_section(section):
            self._config.add_section(section)
        self._config.set(section, key, value)

    def delete(self, section, key):
        self._config.remove_option(section, key)

    def delete_section(self, section):
        self._config.remove_section(section)

    def save(self):
        with open('config.ini', 'w') as cfg:
            self._config.write(cfg)

    def load(self):
        self._config.read('config.ini')

    def sections(self):
        return self._config.sections()

    def keys(self, section):
        return self._config.options(section)


config = Config()
