# -*- coding: utf-8 -*-
"""Logging setup"""
import logging
import sys

def setup_logger(logger_name: str="owlbear"):
    log_level = logging.INFO
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)

    if not logger.hasHandlers():
        log_handler = logging.StreamHandler(stream=sys.stdout)
        log_handler.setLevel(log_level)
        logger.addHandler(log_handler)

    return logger
