import concurrent.futures

from src.core.config import settings
from src.core.logs import custom_logger
from src.parser.parser import Parser
# from src.parser.utils import check_driver_installation


def main():
    custom_logger.info('Start parser ...')
    # check_driver_installation()
    parser = Parser()

    with concurrent.futures.ProcessPoolExecutor(max_workers=settings.PROCESS_COUNT) as executor:
        futures_stories = executor.submit(parser.run_async_function, parser.get_stories_data)
        future_ids = executor.submit(parser.run_async_function, parser.get_login_ids_list)
        future_posts = executor.submit(parser.run_async_function, parser.get_posts_list_by_id)

        for future in concurrent.futures.as_completed((future_ids, future_posts, futures_stories)):
            try:
                future.result()
            except Exception as e:  # noqa: PIE786
                custom_logger.exception(f'Global parser error: {e}')


if __name__ == '__main__':
    main()
