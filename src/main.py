import asyncio
import concurrent.futures
import time

from src.core.config import settings
from src.core.logs import custom_logger
from src.parser.parser import Parser
from src.parser.utils import check_driver_installation

RESTART_WAIT_TIME = 900


def main():
    check_driver_installation()
    parser = Parser()

    while True:
        logins_for_update = asyncio.run(parser.on_start())

        if logins_for_update:
            process_logins(logins_for_update, parser)
            custom_logger.info(f'All {len(logins_for_update)} logins updated!')
            custom_logger.info(
                f'Automatic restart of the parser after {settings.PARSER_BETWEEN_RESTARTS_SLEEP_SEC} secs ...'
            )
            time.sleep(settings.PARSER_BETWEEN_RESTARTS_SLEEP_SEC)
        else:
            handle_no_logins()


def process_logins(logins_for_update, parser):
    with concurrent.futures.ProcessPoolExecutor(max_workers=settings.PROCESS_COUNT) as executor:
        logins_with_id = [login for login in logins_for_update if login.user_id]
        logins_without_id = [login for login in logins_for_update if not login.user_id]

        futures_stories = executor.submit(parser.sync_wrapper_stories_update, logins_with_id)
        future_ids = executor.submit(parser.sync_wrapper_ids_update, logins_without_id)
        future_posts = executor.submit(parser.sync_wrapper_posts_update, logins_with_id)

        for future in concurrent.futures.as_completed((future_ids, future_posts, futures_stories)):
            try:
                future.result()
            except Exception as e:  # noqa: PIE786
                custom_logger.error(f'Error while processing login: {e}')


def handle_no_logins():
    custom_logger.warning('No logins for update found!')
    custom_logger.warning('Check your db and credentials in .env file!')
    custom_logger.warning(f'Restart after {RESTART_WAIT_TIME // 60} min ...')
    time.sleep(RESTART_WAIT_TIME)


if __name__ == '__main__':
    main()
