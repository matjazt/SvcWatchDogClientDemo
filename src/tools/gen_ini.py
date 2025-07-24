# -*-coding:utf-8
"""
Generic INI file tools
"""

import os
import threading

from tools import gen_tools


class GenIni:
    """INI file parser class, supporting:
    * semi-automatic timestamp-based reload (you *do* have to call auto_refresh periodically)
    * thread safe API
    * getters accept a default value which they return in case the required setting is not present in the INI file
    * case insensitive section and key names
    * multiple values for a single key (in the order, specified in the INI file)
    * detection of missing keys
    """

    _lock = threading.RLock()
    _instance = None

    @classmethod
    def get_default_instance(cls) -> "GenIni":
        """get_default_instance returns pointer to the last initialized GenIni object
        In most cases there is only one such object initialized during the life cycle of a program
        (== singleton), so get_instance fits exactly into this concept."""

        with cls._lock:
            if cls._instance is None:
                raise RuntimeError("GenIni default instance not set")
            return cls._instance

    @classmethod
    def set_default_instance(cls, obj: "GenIni"):
        """set_default_instance sets the default GenIni instance"""

        with cls._lock:
            cls._instance = obj

    def __init__(self, file_name: str | None = None, do_load: bool = True):

        # main data: dict of dicts of lists (section->key->valueIndex).
        # Sections and keys are both lower case.
        self._data = dict()

        # missing values; dict of "[section]/key" => value
        self._default_values = dict()

        self._cs = threading.RLock()
        self._file_timestamp = None

        if file_name is None:
            self._file_name = None
        else:
            self.open(file_name, do_load)

    def __repr__(self):
        return f"{self.__class__.__name__}({self._file_name})"

    def save(self, file_name: str | None = None):
        """Store INI file; WARNING: comments will not be stored"""
        with self._cs:
            if file_name is None:
                file_name = self._file_name
            if file_name is None:
                raise ValueError(
                    "output file_name unknown - cannot save configuration file")
            gen_tools.store_text_file(file_name, self.get_whole_file())

    def open(self, file_name: str, do_load: bool = True):
        """Remember the file name, load and parse the file if bLoad==True"""
        with self._cs:
            self._file_name = file_name
            self._file_timestamp = None
            if do_load:
                self.auto_refresh()

    def auto_refresh(self):
        """Load and parse the file if its timestamp changed since last read. Return True if reload was done, False otherwise.
        The section any key names are converted to lowcase to enable case insensitive searching."""

        if self._file_name is None:
            return False

        with self._cs:
            # check if file timestamp changed since last read
            try:
                file_stat = os.stat(self._file_name)
                file_timestamp = float(file_stat.st_mtime)
            except:
                file_timestamp = None

            if file_timestamp == self._file_timestamp:
                return False

            # remember the timestamp
            self._file_timestamp = file_timestamp

            # load data
            self._data = dict()
            self._default_values = dict()
            section_name = None

            load_errors: list[str] = list()

            # section = None - zakaj ?

            with open(self._file_name, "r", encoding="utf-8-sig") as f:
                while 1:

                    line = f.readline()
                    if not line:
                        break

                    line = line.strip(" \n\r")

                    if line == "" or line.startswith("#") or line.startswith(";"):
                        continue

                    if line.startswith("["):
                        # sekcija
                        if line.endswith("]") and len(line) >= 3:

                            # OK, imamo sekcijo
                            section_name = line[1:-1].lower()

                            # če se ta sekcija prvič pojavi, potem jo dodamo, sicer
                            # ne (če gre za "podaljšek")
                            if section_name not in self._data:
                                self._data[section_name] = dict()
                        else:
                            # napača
                            load_errors.append("invalid section line: " + line)
                    else:

                        if section_name is None:
                            load_errors.append("no section defined: " + line)
                        else:
                            eq_index = line.find("=")
                            if eq_index < 1:
                                load_errors.append("invalid key line: " + line)
                            else:
                                key = line[0:eq_index].lower().strip()
                                value = line[eq_index + 1:].strip()

                                # po potrebi odstranimo narekovaje
                                if len(value) > 1 and value.startswith('"') and value.endswith('"'):
                                    value = value[1:-1]

                                section = self._data[section_name]

                                if key in section:
                                    value_list = section[key]
                                else:
                                    value_list: list[str] = []
                                    section[key] = value_list

                                value_list.append(value)

            return True

    def _store_default_value(self, section: str, key: str, value: object):
        if value is not None:
            self._default_values["[%s]/%s" % (section, key)] = value

    def get_default_values(self) -> str:
        """gets the default values, not yet configured in the INI file"""

        buf = ""
        with self._cs:
            all_keys = list(self._default_values.keys())
            all_keys.sort()
            for k in all_keys:
                value = self._default_values[k]
                if not isinstance(value, str):
                    value = str(value)

                v = ("%r" % value)[2:-1]
                if len(v) > 0 and v[-1] == " ":
                    v = '"' + v + '"'
                buf += "%s=%s\n" % (k, v)
        return buf

    def get_whole_file(self) -> str:
        """get the entire file (with lowercase sections and keys, without comments)"""

        buf = ""
        empty = ""
        with self._cs:
            for section, keys in self._data.items():
                buf += "%s[%s]\n" % (empty, section)
                empty = "\n"
                for key, values in keys.items():
                    for v in values:
                        if len(v) > 0 and v[-1] == " ":
                            v = '"' + v + '"'
                        buf += "%s=%s\n" % (key, v)

        return buf

    def get_file_name(self) -> str | None:
        """get the file name of the INI file"""
        with self._cs:
            return self._file_name

    def add_section(self, section: str):
        """Add a new section."""
        section = section.lower()
        with self._cs:
            if section not in self._data:
                self._data[section] = dict()

    def get_sections(self) -> list[str]:
        """Get the list of all sections"""
        with self._cs:
            return list(self._data.keys())

    def add_key(self, section: str, key: str, value: object) -> object:
        """Add a new value to any section."""

        section = section.lower()
        key = key.lower()

        self.add_section(section)

        with self._cs:
            self._data[section].setdefault(key, list()).append(str(value))
        return value

    def delete_key(self, section: str, key: str):
        """Deletes a key if it exists"""

        section = section.lower()

        with self._cs:
            if section in self._data:
                s = self._data[section]
                key = key.lower()
                if key in s:
                    del s[key]

    def add_or_update_key(self, section: str, key: str, value: object):
        """Add a new value to any section or update an existing one"""

        self.delete_key(section, key)
        self.add_key(section, key, str(value))

    def _get_value(self, section: str, key: str, value_index: int):
        with self._cs:
            return self._data[section][key][value_index]

    def get_all_values(self, section: str, key: str) -> list[str]:
        """get a list of all values, configured for the given section and key (there can be more than one)"""
        section = section.lower()
        key = key.lower()

        with self._cs:
            try:
                return self._data[section][key]
            except:
                return list()

    def get_optional_string(self, section: str, key: str, default_value: str | None = None, value_index: int = 0) -> str | None:
        """Return the key value as string, or default value if the key is not present"""
        section = section.lower()
        key = key.lower()

        try:
            string_value = self._get_value(section, key, value_index)
        except:
            string_value = default_value
            self._store_default_value(section, key, default_value)

        # print "%s %s => %s" % (section, key, strValue)
        return string_value

    def get_string(self, section: str, key: str, default_value: str, value_index: int = 0) -> str:
        """Return the key value as string, or default value if the key is not present"""
        return self.get_optional_string(section, key, default_value, value_index)  # type: ignore

    def get_optional_int(self, section: str, key: str, default_value: int | None = None, value_index: int = 0) -> int | None:
        """Return the key value as integer, or default value if the key is not present or if it's not an integer."""
        section = section.lower()
        key = key.lower()

        try:
            string_value = self._get_value(section, key, value_index)
            value = int(string_value, 0)
        except:
            value = default_value
            self._store_default_value(section, key, default_value)

        # print "%s %s => %r" % (section, key, iValue)
        return value

    def get_int(self, section: str, key: str, default_value: int, value_index: int = 0) -> int:
        """Return the key value as integer, or default value if the key is not present or if it's not an integer."""
        return self.get_optional_int(section, key, default_value, value_index)  # type: ignore

    def get_optional_float(self, section: str, key: str, default_value: float | None = None, value_index: int = 0) -> float | None:
        """Return the key value as float, or default value if the key is not present or if it's not a float."""
        section = section.lower()
        key = key.lower()

        try:
            string_value = self._get_value(section, key, value_index)
            value = float(string_value)
        except:
            value = default_value
            self._store_default_value(section, key, default_value)

        return value

    def get_float(self, section: str, key: str, default_value: float, value_index: int = 0) -> float:
        """Return the key value as float, or default value if the key is not present or if it's not a float."""
        return self.get_optional_float(section, key, default_value, value_index)  # type: ignore

    def get_bool(self, section: str, key: str, default_value: bool, value_index: int = 0) -> bool:
        """Return the key value as boolean, or default value if the key is not present or if it's not an integer.
        The value is considered True if it is "1", "true", "yes", "on" (case insensitive).
        The value is considered False if it is "0", "false", "no", "off" (case insensitive).
        """
        section = section.lower()
        key = key.lower()

        try:
            string_value = self._get_value(section, key, value_index).strip().lower()
            if string_value in ["1", "true", "yes", "on"]:
                return True
            elif string_value in ["0", "false", "no", "off"]:
                return False
        except:
            pass

        self._store_default_value(section, key, default_value)
        return default_value
