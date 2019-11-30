from typing import List, Dict, Union,  Any
from itertools import chain, combinations
import logging
import json
from env import get_db_connection, get_log_level

logging.getLogger().setLevel(level=get_log_level())


class Bounds:
    def __init__(self, min_, max_):
        self.min_ = min_
        self.max_ = max_

    def getMin(self):
        return self.min_

    def getMax(self):
        return self.max_


Letters = str
Words = List[str]
SpellableQuery = (Bounds, Letters)
MatchSubstringQuery = (Bounds, Bounds)
Query = Union()


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


def spellable_result(result_list: Words, letters: Letters, bounds: Bounds):
    return dict(
        result=dict(items=result_list, total=len(result_list)),
        query=dict(letters=letters, minLength=bounds.getMin(),
                   maxLength=bounds.getMax())
    )


def get_all_combinations_for_letters_and_lengths(letters: Letters, lengths: List[int]) -> List[str]:
    all_combinations = chain(*[combinations(letters, n)
                               for n in lengths])
    return(list(''.join(combination) for combination in all_combinations))


def get_spellable_words_for_letters(letters: Letters, bounds: Bounds) -> Words:
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


def query_database_matching_substrings(substringBounds, bounds) -> Dict:
    result = {}
    subMin = substringBounds.getMin() + 1
    subMax = substringBounds.getMax() + 1
    with get_db_connection().cursor() as cur:
        cur.execute(f"""
        SELECT substring(`ordered`, {subMin + 1}, {subMax + 1}), COUNT(*)
            FROM `word`
            WHERE LENGTH(`ordered`) > 0
            AND LENGTH(`ordered`) < 4
            GROUP BY substring(`ordered`, {subMin + 1}, {subMax + 1});
        """)
        for row in cur:
            result[row[0]] = row[1]
    return result


def parse_spellable_query(event: Dict) -> (Letters, Bounds):
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


def parse_matching_substring_query(event: Dict) -> (Bounds, Bounds):
    try:
        max_arg = str(event.get('maxLength'))
        min_arg = str(event.get('minLength'))
        max_ = int(max_arg) if max_arg.isdigit() else 7
        min_ = int(min_arg) if min_arg.isdigit() else 1

        start_arg = str(event.get('startLength'))
        end_arg = str(event.get('endLength'))
        start = int(start_arg) if start_arg.isdigit() else 0
        end = int(end_arg) if end_arg.isdigit() else 2

        if (max_ > 7 or max_ < 1):
            raise LambdaStatusException(
                400, f"Invalid maxLength arg, maxLength must be between 1 and 7")
        elif (min_ > 7 or min_ < 1):
            raise LambdaStatusException(
                400, f"Invalid minLength arg, minLength must be between 1 and 7")

        return Bounds(min_, max_), Bounds(start, end)
    except:
        raise LambdaStatusException(
            400, f"Error parsing event payload {json.dumps(event)}.")


def parse_event(event: Dict) -> Query:
    # Legacy path
    if (event['letters']):
        logging.info("Legacy spellable query parsed")
        return parse_spellable_query(event)
    if (event['queryType']):
        queryType = event['queryType']
        if (queryType == 'spellable'):
            return parse_spellable_query(event['query'])
        elif (queryType == 'matchSubstring'):
            return parse_matching_substring_query(event['query'])
        raise LambdaStatusException(400, f"Invalid query type {queryType}")
    raise LambdaStatusException(
        400, f"Error parsing event payload {json.dumps(event)}.")


def handle(event, context):
    logging.info("Function called with args %s",
                 json.dumps(dict(event=event)))
    query = parse_event(event)

    try:
        if (type(query) == SpellableQuery):
            letters, bounds = query
            data = get_spellable_words_for_letters(letters, bounds)
            return response(200, spellable_result(data, letters, bounds))
        elif (type(query) == MatchSubstringQuery):
            substringBounds, bounds = query
            data = query_database_matching_substrings(substringBounds, bounds)
            return response(200, "")

    except LambdaStatusException as e:
        return e.toResponse()
    except (Exception, RuntimeError) as e:
        logging.error(e)
        return response(500, 'Unexpected error.')
