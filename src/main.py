import asyncio
import concurrent.futures
import time

from core.logs import custom_logger
from core.settings import settings
from parser.parser import Parser
from parser.utils import chunks

if __name__ == '__main__':
    try:
        parser = Parser()
        while True:
            # on_start run
            if logins_for_update := asyncio.run(parser.on_start()):
                with concurrent.futures.ProcessPoolExecutor(max_workers=settings.PROCESS_COUNT) as executor:
                    # extract logins with id and split it to chunk of 30 elems size
                    logins_with_id = list(chunks([login for login in logins_for_update if login.user_id], 30))
                    futures = [executor.submit(parser.sync_wrapper_reels_update, chunk) for chunk in
                               logins_with_id]
                    # add separate process to update new logins without ids
                    logins_without_id = [login for login in logins_for_update if not login.user_id]
                    futures.append(executor.submit(parser.sync_wrapper_ids_update, logins_without_id))
                    # wait for all process to finish
                    for future in concurrent.futures.as_completed(futures):
                        future.result()
                custom_logger.info(f'All {len(logins_for_update)} logins updated!')
                custom_logger.info(f'Automatic restart of the parser after '
                                   f'{settings.PARSER_BETWEEN_RESTARTS_SLEEP_SEC} secs ...')
                time.sleep(settings.PARSER_BETWEEN_RESTARTS_SLEEP_SEC)
            else:
                custom_logger.warning('No logins for update found!')
                custom_logger.warning('Check your db and credentials in .env file!')
                custom_logger.warning('Restart after 15 min ...')
                time.sleep(900)
    except BaseException as ex:
        custom_logger.error(ex)