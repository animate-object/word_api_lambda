from typing import List, Dict, Union,  Any
from itertools import chain, combinations
import logging
import json
import pymysql
import sys
from env import DB_HOST, DB_USER, DB_PASS, DB_NAME

logger = logging.getLogger()
logger.setLevel(logging.INFO)

rds_host = DB_HOST
user = DB_USER
password = DB_PASS
db_name = DB_NAME

try:
    conn = pymysql.connect(rds_host, user=user,
                           passwd=password, db=db_name, connect_timeout=5)
except pymysql.MySQLError as e:
    logger.error(
        "ERROR: Unexpected error: Could not connect to MySQL instance.")
    logger.error(e)
    sys.exit()

Letters = str
Words = List[str]
Min = int
Max = int


class LambdaStatusException(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message

    def toResponse(self):
        response(self.status, self.message)


def response(statusCode, body):
    return dict(statusCode=statusCode, body=body)


def get_all_combinations_for_letters_and_lengths(letters: Letters, lengths: List[int]) -> List[str]:
    all_combinations = chain(*[combinations(letters, n)
                               for n in lengths])
    return(list(''.join(combination) for combination in all_combinations))


def get_all_words_for_letters(letters: Letters, minLength: Min, maxLength: Max) -> Words:
    word_lengths = list(range(minLength + maxLength))
    all_combinations_to_search = get_all_combinations_for_letters_and_lengths(
        letters, word_lengths)
    logger.debug('Searching for %d sorted combinations.',
                 len(all_combinations_to_search))
    return query_database_for_combinations(all_combinations_to_search)


def query_database_for_combinations(search_combinations: List[str]) -> Words:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT * FROM `word` WHERE `alpha` IN ({', '.join(search_combinations)});")
        for row in cur:
            logger.info(str(row))
    return []


def parse_event(event: Dict) -> (Letters, Min, Max):
    try:
        letters_arg = event['letters']
        if any([not l.isalpha() for l in letters_arg]) or len(letters_arg) > 16:
            raise LambdaStatusException(400,
                                        f"Invalid arg letters: {letters_arg}. Letters must be a member of the english alphabet. Max 16 letters allowed")
        letters = letters_arg.lower()

        max_arg = str(event.get('maxLength'))
        min_arg = str(event.get('minLength'))
        max_ = int(max_arg) if max_arg.isdigit() else 7
        min_ = int(min_arg) if min_arg.isdigit() else 1

        if (max_ > 7 or max_ < 1):
            raise LambdaStatusException(
                400, f"Invalid maxLength arg, maxLength must be between 1 and 7")
        elif (min_ > 7 or min_ < 1):
            raise LambdaStatusException(
                400, f"Invalid minLength arg, minLength must be between 1 and 7")

        return letters, min_, max_
    except:
        raise RuntimeError(400, 'Error parsing event payload.')


def handle(event, context):
    logger.debug("Function called with args %s",
                 json.dumps(dict(event=event, context=context)))
    letters, min_, max_ = parse_event(event)

    try:
        data = get_all_words_for_letters(letters, min_, max_)
        return response(200, data)
    except LambdaStatusException as e:
        return e.toResponse()
    except Exception:
        return response(500, 'Unexpected error.')
