# -*-coding:utf-8
"""various cryptography tools"""

import logging
import base64
import threading
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Util.Padding import pad, unpad
from Crypto.Hash import SHA256

import tools.gen_tools as gen_tools
from tools.gen_ini import GenIni


class CryptoTools:

    _lock = threading.RLock()
    _instance = None

    _section: str = "CryptoTools"
    _cs: threading.RLock

    @classmethod
    def get_default_instance(cls) -> "CryptoTools":
        """get_default_instance returns pointer to the last initialized CryptoTools object
        In most cases there is only one such object initialized during the life cycle of a program
        (== singleton), so get_default_instance fits exactly into this concept."""

        with cls._lock:
            if cls._instance is None:
                raise RuntimeError("CryptoTools default instance not set")
            return cls._instance

    @classmethod
    def set_default_instance(cls, obj: "CryptoTools"):
        """set_default_instance sets the default CryptoTools instance"""

        with cls._lock:
            cls._instance = obj

    def __init__(self, default_password: str, ini: GenIni | None = None, section: str | None = None):

        self._cs = threading.RLock()

        if ini is None:
            ini = GenIni.get_default_instance()

        if section:
            self._section = section

        password = default_password
        passwordFile = ini.get_optional_string(self._section, "PasswordFile")
        if passwordFile:
            try:
                contents = gen_tools.read_text_file(passwordFile)
                if contents:
                    # ignore the supplied default password if the file is present
                    password = ''.join(c for c in contents if 32 < ord(c) <= 127)
            except:
                password = default_password

        # let's prepare the key and iv, but *not* the cipher, because we can't reuse it
        key_length = 32  # AES-256 = 32 bytes
        iv_length = 16   # AES block size
        iterations = 10000

        key_iv = PBKDF2(password, b'', dkLen=key_length + iv_length, count=iterations, hmac_hash_module=SHA256)
        self._key = key_iv[:key_length]
        self._iv = key_iv[key_length:]

    def aes256_cbc_encrypt(self, data: str) -> str:
        """
        Returns the AES-256-CBC encrypted string of the given plain text using the specified password or the default password.

        OpenSSL equivalent:
            openssl enc -base64 -e -aes-256-cbc -pbkdf2 -nosalt -pass pass:SuperSecretPassword
        (you can omit -pass and enter it interactively).
        """
        with self._cs:
            cipher = AES.new(self._key, AES.MODE_CBC, self._iv)
            encrypted = cipher.encrypt(pad(data.encode(), AES.block_size))
            return base64.b64encode(encrypted).decode()

    def aes256_cbc_decrypt(self, encrypted_b64: str) -> str:
        """
        Returns the plain text of the given AES-256-CBC encrypted string using the specified password or the default password.

        OpenSSL equivalent:
            openssl enc -base64 -d -aes-256-cbc -pbkdf2 -nosalt -pass pass:SuperSecretPassword
        (you can omit -pass and enter it interactively).
        """
        with self._cs:
            encrypted_bytes = base64.b64decode(encrypted_b64)
            cipher = AES.new(self._key, AES.MODE_CBC, self._iv)
            decrypted = unpad(cipher.decrypt(encrypted_bytes), AES.block_size)
            return decrypted.decode()

    def get_possibly_encrypted_configuration_string(self, section: str, key: str, default_value: str | None, ini: GenIni | None = None) -> str | None:
        """
        Returns the AES-256-CBC encrypted string of the specified configuration value.

        :param section: The INI section name.
        :param key: The configuration key name.
        """
        if ini is None:
            ini = GenIni.get_default_instance()

        raw = ini.get_optional_string(section, key)
        if raw is None:
            return default_value

        try:
            return self.aes256_cbc_decrypt(raw)
        except:
            logging.warning(f"it seems {section} -> {key} is not encrypted, using is as it is")
            logging.info(f"you should use the following encrypted value for {section} -> {key} : {self.aes256_cbc_encrypt(raw)}")

            return raw

    @staticmethod
    def self_test():

        cryptoTools = CryptoTools("yLCJt6ZcPVvILzwgQRKh")
        CryptoTools.set_default_instance(cryptoTools)
        plaintext = "Q20mSdspXdnNwFEkY0eJ"

        encrypted = cryptoTools.aes256_cbc_encrypt(plaintext)

        print("Encrypted (OpenSSL-style):")
        print(encrypted)

        decrypted = cryptoTools.aes256_cbc_decrypt(encrypted)
        print("Decrypted:")
        print(decrypted)
