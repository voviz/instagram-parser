from seleniumbase import get_driver

from src.core.logs import custom_logger


def check_driver_installation() -> None:
    custom_logger.info('Check webdriver installation ... ')
    driver = get_driver('chrome', headless=True)
    driver.get('https://www.google.com/chrome')
    driver.quit()
    custom_logger.info('End of check driver installation process ...')


def chunks(lst: list, n: int):
    """
    Yield successive n-sized chunks from lst.
    @param lst: list of data
    @param n: number of chunks to separate
    @return: iterator
    """
    for i in range(0, len(lst), n):
        yield lst[i: i + n]
