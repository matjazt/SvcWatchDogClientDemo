﻿# -*-coding:utf-8
"""various generic tools"""
import os
import smtplib
import time
from typing import Optional


def send_mail(sender: str, recipients: str, smtp_server: str, timeout: float, contents: str) -> None:
    """send email"""
    # print(f"sender={sender}, recipients={recipients}, smtp_server={smtp_server}, timeout={timeout}:\n{contents}\n")

    with smtplib.SMTP(timeout=timeout) as server:
        server.connect(smtp_server)
        server.sendmail(sender, recipients.replace(
            " ", "").split(","), contents.encode("utf8"))


def show_menu(title, items):
    """show console menu"""
    print(
        f"\n{str(title).capitalize()}\n--------------------------------------------")
    m = len(max(items, key=len))

    for cmd in items.keys():
        print(f" %{m}s - %s" % (cmd, items[cmd]))

    print(f" %{m}s - quit" % "q")
    print("--------------------------------------------")


def read_text_file(filename: str, default_contents: Optional[str] = None, encoding: str = "utf-8-sig") -> Optional[str]:
    """read text file if possible, return string contents or specified default"""
    if not os.path.isfile(filename):
        return default_contents
    with open(filename, "r", encoding=encoding) as h:
        return h.read()
        # return "".join(all_lines)


def store_text_file(filename: str, contents: str, encoding: str = "utf-8-sig") -> None:
    """store text to the file (overwrite it or create a new one)"""
    with open(filename, "w", encoding=encoding) as h:
        h.write(contents)


def snake_to_camel(s: str) -> str:
    """convert from snake_case to CamelCase"""
    # return s.replace("_", " ").title().replace(" ", "")
    return "".join(word.title() for word in s.split("_"))


def camel_to_snake(s: str) -> str:
    """convert from CamelCase to snake_case"""
    return "".join(["_" + c.lower() if c.isupper() else c for c in s]).lstrip("_")


def string_length_check(s: str, min_length: int, max_length: int) -> bool:
    """
    Returns true if string length is between min_length and max_length (inclusive)
    """
    l = len(s)
    return l >= min_length and l <= max_length


def get_app_base_folder() -> str:
    """
    Returns base folder of the app, which is basically the folder of the script, unless the script is located
    in the "bin" or "src" subfolder. In that case, it returns path without the "bin" or "src" subfolder.
    """
    p = os.path.dirname(os.path.realpath(__file__))
    # "tools" because this particular file (gen_tools.py) should be placed into tools subfolder
    for d in ["tools", "src", "bin"]:
        s = os.path.split(p)
        if s[-1].lower() == d:
            p = s[0]
    return p


def cd_to_app_base_folder() -> None:
    """
    Changes current working direktory to the app base folder.
    """
    os.chdir(get_app_base_folder())


def steady_time() -> int:
    """
    Returns steady / monotonic time in milliseconds.
    """
    return round(time.monotonic() * 1000)


def empty_if_none(s: Optional[str]) -> str:
    """
    Returns empty string if s is None, otherwise returns s.
    """
    return "" if s is None else s
