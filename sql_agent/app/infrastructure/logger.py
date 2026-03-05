"""Logger"""
import logging

logging.basicConfig(level=logging.INFO)

class AppLogger:

    @staticmethod
    def info(message):
        logging.info(message)

    @staticmethod
    def error(message):
        logging.error(message)