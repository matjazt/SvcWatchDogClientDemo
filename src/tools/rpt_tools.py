# -*-coding:utf-8
"""report tools"""

# from decimal import Decimal


def amount(x: float) -> str:
    """
    Rounds amount to two decimals and converts to string.
    """
    return str(round(x, 2)).replace(".", ",")


def percent(x: float) -> str:
    """
    Converts x to percent (multiplies by 100) and converts to string, adding percent sign
    """
    return "{0:f}".format(round(x, 7) * 100).rstrip("0").rstrip(".") + " %"
