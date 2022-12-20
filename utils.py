"""
Basic utils to be used.
"""
import os


def split(a, n):
    """
    Multiprocessing split function.
    @param a: The list of item
    @param n: the number of groups to firm
    @return: List of returned lists separating a.
    """
    k, m = divmod(len(a), n)
    return [a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n)]