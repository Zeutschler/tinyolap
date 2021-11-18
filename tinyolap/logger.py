import logging
from enum import Enum
from os import path
from pathlib import Path
from timeit import default_timer as timer

import utils


class Logger:

    LOG_FILE_EXTENSION = ".log"

    def __init__(self, name: str = "tinyolap", level=logging.INFO):
        name = name.lower().strip()
        if not name.startswith("tinyolap."):
            name = "tinyolap." + name
        self.name = name
        self.root = name.split(".")[0]
        self.level = level
        self.file_path = utils.get_file_path(self.root + self.LOG_FILE_EXTENSION)

        self.logger = logging.getLogger(self.name)
        handler = logging.FileHandler(self.file_path, mode='w')
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(self.level)


    def __setup_logger(self):
        self.logger = logging.getLogger("storage_provider")
        handler = logging.FileHandler(self.file_path, mode='w')
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(self.LOG_LEVEL)

    def delete_log_file(self):
        """Deletes the database log file."""
        try:
            if path.exists(self.log_file):
                os.remove(self.log_file)
            return True
        except OSError:
            return False