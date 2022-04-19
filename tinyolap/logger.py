# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import logging
import os

from utilities import utils


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
            if os.path.exists(self.log_file):
                os.remove(self.log_file)
            return True
        except OSError:
            return False
