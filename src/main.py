from typing import List, Dict, Union,  Any
from itertools import chain, combinations
import logging
import json
from env import get_db_connection, get_log_level

logging.getLogger().setLevel(level=get_log_level())


Letters = str
Words = List[str]


class Bounds:
    def __init__(self, min_, max_):
    self.min_ = min_
    self.max_ = max_

    def getMin(self):
        return self.min_

    def getMax(self):
        return self.max_


class LambdaStatusException(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message

    def toResponse(self):
        return response(self.status, self.message)


def response(statusCode, body):
    return dict(statusCode=statusCode,
                body=body,
                headers={'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json'})


def result(result_list: Words, letters: Letters, bounds: Bounds):
    return dict(
        result=dict(items=result_list, total=len(result_list)),
        query=dict(letters=letters, minLength=bounds.getMin(),
                   maxLength=bounds.getMax())
    )


def get_all_combinations_for_letters_and_lengths(letters: Letters, lengths: List[int]) -> List[str]:
    all_combinations = chain(*[combinations(letters, n)
                               for n in lengths])
    return(list(''.join(combination) for combination in all_combinations))


def get_all_words_for_letters(letters: Letters, bounds: Bounds) -> Words:
    word_lengths = list(range(bounds.getMin() + bounds.getMax()))
    all_combinations_to_search = get_all_combinations_for_letters_and_lengths(
        letters, word_lengths)
    logging.info('Searching for %d sorted combinations.',
                 len(all_combinations_to_search))
    return query_database_for_combinations(all_combinations_to_search)


def query_database_for_combinations(search_combinations: List[str]) -> Words:
    result = []
    with get_db_connection().cursor() as cur:
        search_param = ', '.join([f"'{comb}'" for comb in search_combinations])
        cur.execute(
            f"SELECT * FROM `word` WHERE `alpha` IN ({search_param});")
        for row in cur:
            result.append(row[0])
    return result


def parse_event(event: Dict) -> (Letters, Bounds):
    try:
        letters_arg = event['letters']
        if any([not l.isalpha() for l in letters_arg]) or len(letters_arg) > 16:
            raise LambdaStatusException(400,
                                        f"Invalid arg letters: {letters_arg}. Letters must be a member of the english alphabet. Max 16 letters allowed")
        letters = ''.join(sorted(letters_arg.lower()))

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

        return letters, Bounds(min_, max_)
    except:
        raise LambdaStatusException(
            400, f"Error parsing event payload {json.dumps(event)}.")


def handle(event, context):
    logging.info("Function called with args %s",
                 json.dumps(dict(event=event)))
    letters, bounds = parse_event(event)

    try:
        data = get_all_words_for_letters(letters, bounds)
        return response(200, result(data, letters, bounds.getMin(), bounds.getMax()))
    except LambdaStatusException as e:
        return e.toResponse()
    except (Exception, RuntimeError) as e:
        logging.error(e)
        return response(500, 'Unexpected error.')
