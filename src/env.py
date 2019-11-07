
from base64 import b64decode
import logging
import os
import boto3
import pymysql


DB_PASS_ENCRYPTED = os.environ.get('DB_PASSWORD')
DB_USER = os.environ.get('DB_USER')
DB_HOST = os.environ.get('DB_HOST')
DB_NAME = os.environ.get('DB_NAME')
LOG_LEVEL = os.environ.get('LOG_LEVEL')


def get_log_level() -> int:
    if LOG_LEVEL == None or LOG_LEVEL == "INFO":
        return logging.INFO
    elif LOG_LEVEL == "DEBUG":
        return logging.DEBUG
    elif LOG_LEVEL == "WARNING":
        return logging.WARNING
    elif LOG_LEVEL == "ERROR":
        return logging.ERROR


class DbConfig:
    def __init__(self, encrypted_pw, user, host, name):
        if any([required is None for required in [encrypted_pw, user, host, name]]):
            logging.error("Required option was None, pw %s, user %s, host %s, name %s",
                          *['present' if option else 'not present' for option in [encrypted_pw, user, host, name]]
                          )
            raise RuntimeError("Missing required envvar.")
        self.pw = self.decrypt(encrypted_pw)
        self.user = user
        self.host = host
        self.name = name
        logging.info("Application configured.")

    def decrypt(self, encrypted):
        try:
            return boto3.client('kms').decrypt(
                CiphertextBlob=b64decode(encrypted))['Plaintext']
        except:
            raise RuntimeError("Error decrypting pw.")

    def getHost(self):
        return self.host

    def getPw(self):
        return self.pw

    def getName(self):
        return self.name

    def getUser(self):
        return self.user


DB_CONFIG = None


def get_db_config() -> DbConfig:
    global DB_CONFIG
    if (DB_CONFIG == None):
        logging.info(
            "DBConfig not initialized. Parsing environment variables.")
        DB_CONFIG = DbConfig(DB_PASS_ENCRYPTED, DB_USER, DB_HOST, DB_NAME)
        logging.info("DbConfig set.")
    else:
        logging.info("Reusing previous DbConfig.")
    return DB_CONFIG


DB_CONNECTION = None


def get_db_connection():
    global DB_CONNECTION
    config = get_db_config()
    if (DB_CONNECTION == None):
        try:
            logging.info('Attempting to open DbConnection')
            DB_CONNECTION = pymysql.connect(
                config.getHost(),
                user=config.getUser(),
                passwd=config.getPw(),
                db=config.getName(),
                connect_timeout=5
            )
            logging.info('Set DbConnection to be reused')
        except pymysql.MySQLError as e:
            logging.error(
                "ERROR: Unexpected error: Could not connect Db.")
            logging.error(e)
            raise RuntimeError("Error connecting to DB")
    else:
        logging.info("Reusing DbConnection")
    return DB_CONNECTION
