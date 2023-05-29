def chunks(lst: list, n: int):
    """
    Yield successive n-sized chunks from lst.
    @param lst: list of data
    @param n: number of chunks to separate
    @return: iterator
    """
    for i in range(0, len(lst), n):
        yield lst[i:i + n]