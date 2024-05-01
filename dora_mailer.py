import smtplib
import base64
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders
from typing import List, Optional, Union
from jinja2 import Environment, FileSystemLoader
from email.header import Header
from pathlib import Path
from email.utils import formataddr
from dotenv import load_dotenv
import importlib.util
import re
import os


def load_dora_config() -> dict[str, str]:
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        raise FileNotFoundError(
            f"Dora mailer conf loader: Can't find the .env file required for its configuration. It must be found in {Path(__file__).parent}")
    load_dotenv(dotenv_path=env_path)
    loaded_config = {}

    # load common configs
    common_configs = {
        "auth_mode": "DORA_AUTH_MODE",
        "sender_name": "DORA_SENDER_NAME",
        "templates_path": "DORA_TEMPLATES_PATH",
        "tasks_path": "DORA_TASKS_PATH",
        "test_recipient": "DORA_TEST_RECIPIENT"
    }
    for key, env_var in common_configs.items():
        value = os.getenv(env_var)
        if value is None:
            raise KeyError(f"Dora mailer common conf loader: Missing environment var: {env_var}")
        loaded_config[key] = value

    auth_mode = loaded_config['auth_mode']

    # smtp_security can be: "ssl", "starttls", or "none"
    smtp_base_configs = {
        "smtp_server": "DORA_SMTP_SERVER",
        "smtp_port": "DORA_SMTP_PORT",
        "smtp_security": "DORA_SMTP_SECURITY"
    }

    if auth_mode == 'smtp':
        smtp_configs = {
            **smtp_base_configs,
            "smtp_username": "DORA_SMTP_USERNAME",
            "smtp_password": "DORA_SMTP_PASSWORD"
        }
        for key, env_var in smtp_configs.items():
            value = os.getenv(env_var)
            if value is None:
                raise KeyError(f"Dora mailer SMTP conf loader: Missing environment var: {env_var}")
            loaded_config[key] = value

    elif auth_mode == 'oauth2':
        oauth2_configs = {
            **smtp_base_configs,
            "oauth2_sender_address": "DORA_OAUTH2_SENDER_ADDRESS",
            "oauth2_tenant_id": "DORA_OAUTH2_TENANT_ID",
            "oauth2_client_id": "DORA_OAUTH2_CLIENT_ID",
            "oauth2_client_secret": "DORA_OAUTH2_CLIENT_SECRET",
            "oauth2_token_url": "DORA_OAUTH2_TOKEN_URL",
            "oauth2_scope": "DORA_OAUTH2_SCOPE"
        }
        for key, env_var in oauth2_configs.items():
            value = os.getenv(env_var)
            if value is None:
                raise KeyError(f"Dora mailer OAuth2 conf loader: Missing environment var: {env_var}")
            loaded_config[key] = value
    else:
        raise RuntimeError(f"Invalid auth mode in .env file: {auth_mode}.")

    return loaded_config


class DoraMailer:
    def __init__(self, config: dict[str, str]):
        # base configs
        self.auth_mode = config.get("auth_mode").lower()
        self.sender_name = config["sender_name"]
        self.test_recipient = config['test_recipient']
        self.tasks_path = config['tasks_path']
        self.templates_path = config["templates_path"]
        templates_dir = Path(self.templates_path)
        self.template_env = Environment(loader=FileSystemLoader(templates_dir))

        # base smtp config. common to both authmodes, smtp and oauth
        self.security = config["smtp_security"].lower()
        self.smtp_server = config["smtp_server"]
        self.port = int(config["smtp_port"])

        # specific config when authmode = smtp
        if self.auth_mode == "smtp":
            self.smtp_username = config["smtp_username"]
            self.password = config["smtp_password"]

        # specific config when authmode = oauth2
        elif self.auth_mode == "oauth2":
            self.oauth2_sender_address = config["oauth2_sender_address"]
            self.oauth2_tenant_id = config["oauth2_tenant_id"]
            self.oauth2_client_id = config["oauth2_client_id"]
            self.oauth2_client_secret = config["oauth2_client_secret"]
            self.oauth2_token_url = config["oauth2_token_url"]
            self.oauth2_scope = config["oauth2_scope"]
        else:
            raise RuntimeError('Incorrect value for auth_mode. It has to be either "smtp" or "oauth2"')

    def _get_oauth2_access_token(self) -> str:
        data = {
            'client_id': self.oauth2_client_id,
            'scope': self.oauth2_scope,
            'client_secret': self.oauth2_client_secret,
            'grant_type': 'client_credentials'
        }
        r = requests.post(self.oauth2_token_url, data=data)
        r.raise_for_status()
        return r.json()['access_token']

    def _load_template(self, template_name: str, context: dict) -> str:
        template = self.template_env.get_template(template_name)
        return template.render(context)

    @staticmethod
    def _prepare_addresses(addresses: Union[str, List[str], None]) -> List[str]:
        if not addresses:
            return []
        if isinstance(addresses, str):
            addresses = [addresses]
        return [addr for addr in addresses if re.match(r"^[^@]+@[^@]+\.[^@]+$", addr)]

    def send_email(
            self,
            subject: str,
            template: str,
            to_addresses: Union[str, List[str]],
            context: Optional[dict] = None,
            cc_addresses: Optional[Union[str, List[str]]] = None,
            bcc_addresses: Optional[Union[str, List[str]]] = None,
            attachments: Optional[List[str]] = None,
            inline_images: Optional[List[str]] = None
    ) -> bool:
        context = context or {}
        to_addresses = self._prepare_addresses(to_addresses)
        cc_addresses = self._prepare_addresses(cc_addresses)
        bcc_addresses = self._prepare_addresses(bcc_addresses)
        if not (to_addresses or cc_addresses or bcc_addresses):
            print("Dora mailer: No valid recipient addresses provided.")
            return False

        attachments = attachments or []
        if isinstance(attachments, str): attachments = [attachments]
        inline_images = inline_images or []
        if isinstance(inline_images, str): inline_images = [inline_images]

        try:
            if self.security == "ssl":
                server = smtplib.SMTP_SSL(self.smtp_server, self.port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.port)
                if self.security == "starttls":
                    server.starttls()

            if self.auth_mode == "oauth2":
                server.ehlo()
                access_token = self._get_oauth2_access_token()
                auth_string = f"user={self.oauth2_sender_address}\x01auth=Bearer {access_token}\x01\x01"
                auth_encoded = base64.b64encode(auth_string.encode()).decode()
                server.docmd("AUTH", f"XOAUTH2 {auth_encoded}")
                from_address = self.oauth2_sender_address
            else:
                server.login(self.smtp_username, self.password)
                from_address = self.smtp_username

            with server:
                msg = MIMEMultipart('related')
                from_header = formataddr((str(Header(self.sender_name, 'utf-8')), from_address))
                msg['From'] = from_header
                msg['To'] = ', '.join(to_addresses)
                msg['CC'] = ', '.join(cc_addresses)
                msg['Subject'] = subject

                final_recipients = to_addresses + cc_addresses + bcc_addresses
                msg_alt = MIMEMultipart('alternative')
                msg.attach(msg_alt)
                msg_alt.attach(MIMEText(self._load_template(template, context), 'html'))

                for i, img_path in enumerate(inline_images):
                    with open(img_path, 'rb') as img_file:
                        msg_image = MIMEImage(img_file.read())
                        msg_image.add_header('Content-ID', f'<image{i}>')
                        msg.attach(msg_image)

                for file_path in attachments:
                    part = MIMEBase('application', "octet-stream")
                    with open(file_path, 'rb') as file:
                        part.set_payload(file.read())
                    encoders.encode_base64(part)
                    filename = Path(file_path).name
                    part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                    msg.attach(part)

                server.sendmail(from_address, final_recipients, msg.as_string())
            return True

        except Exception as e:
            print(f"Dora mailer SMTP engine: Error while sending email: {e}")
            return False

    def run_task(self, task_name: str) -> bool:
        task_path = Path(self.tasks_path) / f"{task_name}.py"
        if not task_path.exists():
            print(f"Dora mailer task engine: Task file not found: {task_path}")
            return False
        spec = importlib.util.spec_from_file_location(task_name, task_path)
        if spec is None or spec.loader is None:
            print(f"Dora mailer task engine: Failed to parse task file: {task_path}")
            return False
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            print(f"Dora mailer task engine: Error while executing task file: {e}")
            return False
        try:
            subject = getattr(module, "subject")
            template = getattr(module, "template")
            to_addresses = getattr(module, "to_addresses", None)
            cc_addresses = getattr(module, "cc_addresses", None)
            bcc_addresses = getattr(module, "bcc_addresses", None)
            context = getattr(module, "context", None)
            inline_images = getattr(module, "inline_images", None)
            attachments = getattr(module, "attachments", None)
        except AttributeError as e:
            print(f"Dora mailer task engine: Task file missing required variables: {e}")
            return False
        if not subject:
            print("Dora mailer task engine: missing subject variable.")
            return False
        if not template:
            print("Dora mailer task engine: missing template variable.")
            return False
        return self.send_email(
            subject=subject,
            template=template,
            to_addresses=to_addresses,
            bcc_addresses=bcc_addresses,
            cc_addresses=cc_addresses,
            context=context,
            inline_images=inline_images,
            attachments=attachments
        )


if __name__ == "__main__":
    import sys

    mailer = DoraMailer(load_dora_config())
    task_name = sys.argv[1] if len(sys.argv) > 1 else "test_task"
    success = mailer.run_task(task_name)
    print(
        f"\u2705 Task '{task_name}' completed. Email sent successfully." if success else f"\u274C Task '{task_name}' couldn't be completed.")
