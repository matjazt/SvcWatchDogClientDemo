# -*-coding:utf-8

from enum import Enum
import logging
from tools.crypto_tools import CryptoTools
from tools.gen_ini import GenIni
import smtplib
from email.message import EmailMessage

# TODO: INI predelaj v snake_case, sicer search ne bo tako uporaben kot bi lahko bil


class TlsMode(Enum):
    DISABLED = 1
    STARTTLS = 2
    FULL = 3


class EmailSender:

    def __init__(self, section: str, ini: GenIni | None = None, cryptoTools: CryptoTools | None = None):
        self._section = section
        self._ini = ini if ini else GenIni.get_default_instance()
        self._cryptoTools = cryptoTools if cryptoTools else CryptoTools.get_default_instance()

        self._default_source_address = self._ini.get_string(self._section, "DefaultSourceAddress", "")
        self._host = self._ini.get_string(self._section, "Host", "")
        self._port = self._ini.get_int(self._section, "Port", 25)
        self._timeout = self._ini.get_int(self._section, "Timeout", 60)
        self._username = self._ini.get_optional_string(self._section, "UserName")
        self._password = self._cryptoTools.get_possibly_encrypted_configuration_string(self._section, "Password", None)
        self._tls_mode = TlsMode[self._ini.get_string(self._section, "TlsMode", TlsMode.DISABLED.name).upper()]

    def is_configured(self) -> bool:
        """Check if the email configuration is valid."""
        return self._host != "" and self._port > 0 and self._timeout > 0

    def send_email(self, subject: str, body: str, to_addresses: list[str], source_address: str = ""):
        if not source_address:
            source_address = self._default_source_address

        if not to_addresses:
            logging.warning("no recipient addresses provided, email will not be sent")
            return

        msg = EmailMessage()
        msg.set_content(body, charset="utf-8")
        msg['Subject'] = subject
        msg['From'] = source_address
        msg['To'] = ", ".join(to_addresses)

        logging.debug(f"sending email to {msg['To']}")

        try:
            if self._tls_mode == TlsMode.FULL:
                with smtplib.SMTP_SSL(self._host, self._port, timeout=self._timeout) as smtp:
                    if self._username and self._password:
                        smtp.login(self._username, self._password)
                    smtp.send_message(msg)
            else:
                with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as smtp:
                    if self._tls_mode == TlsMode.STARTTLS:
                        smtp.ehlo()
                        smtp.starttls()
                        smtp.ehlo()
                    if self._username and self._password:
                        smtp.login(self._username, self._password)
                    smtp.send_message(msg)
            logging.info(f"email sent successfully to {msg['To']}")
        except Exception as e:
            logging.error(f"failed to send email: {e}")
