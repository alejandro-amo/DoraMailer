# Dora Mailer

Tool for simplifying and automating email sending with attachments and templated content.

## Configuration

Configuration is done via a `.env` file expected to be in the same folder as `dora_mailer.py`. A sample file is provided.

### Required variables in the .env file:

- `DORA_SMTP_SERVER`: IP address or hostname of the SMTP server.
- `DORA_SMTP_PORT`: Port of the SMTP server.
- `DORA_SMTP_SECURITY`: Either `"SSL"`, `"STARTTLS"`, or `"NONE"` depending on your server's security configuration.
- `DORA_SMTP_USERNAME`: Your SMTP username.
- `DORA_SMTP_PASSWORD`: Your SMTP password (or an application-specific password if MFA/2FA is enabled).
- `DORA_TEMPLATES_PATH`: Path to the folder containing Jinja2 templates (relative or absolute).
- `DORA_TASKS_PATH`: Path to the folder containing premade task files (relative or absolute).
- `DORA_TEST_RECIPIENT`: A valid email address for testing purposes. **Mandatory.**
- `DORA_SENDER_NAME`: Display name that Dora will use as the sender.

## Usage — non-preconfigured task inside Python

```python
from dora_mailer import DoraMailer, load_dora_config

mailerconfig = load_dora_config()
mailer = DoraMailer(mailerconfig)

mail_sent = mailer.send_email(
    subject="Subject of the email", 
    template="jinja2-template.html", 
    to_addresses="some@email.com",
    bcc_addresses=["bcc_person1@email.com", "bcc_person2@email.com"],
    cc_addresses=["cc_person1@email.com", "cc_person2@gmail.com"],
    inline_images=["templates/img/avatar.jpg"],
    attachments=None,
    context={
        "message": "This is dynamic text that will be added to the template in the {{message}} placeholder.",
        "another_context_variable": "You can add as many context variables as needed, as long as your template uses them."
    }
)

print("✅ Email sent OK.") if mail_sent else print("❌ Email couldn't be sent.")
```

## Usage — preconfigured task inside Python
```python
from dora_mailer import DoraMailer, load_dora_config

mailerconfig = load_dora_config()
mailer = DoraMailer(mailerconfig)

mail_sent = mailer.run_task("test_task")

print("✅ Email sent OK.") if mail_sent else print("❌ Email couldn't be sent.")
```
### a fancy one-liner
```python
print("✅ Email sent OK.") if DoraMailer(load_dora_config()).run_task("test_task") else print("❌ Email couldn't be sent.")
```


## Usage — preconfigured task via cron/console
Simply use the provided script `task_runner.sh` as follows:
```bash
./task_runner.sh test_task
```
where `test_task` is the name of any valid task file inside tasks folder. This method will create a task execution log in logs folder.

## Creating task files
Add your task config files to the tasks folder. Start by copying `test_task.py` and modify as needed.
### Example task file:
```python
subject = "Daily Reports"
template = "daily_report_template.html"
to_addresses = "boss@company.com"
attachments = ["path/to/first_report.xlsx"]
```

## Creating templates
Dora uses jinja2 template engine so everything that can be made with Jinja2, can be made with Dora's templates.

The provided `base.html` template requires at least one inline image. It is embedded at the bottom of the email as part of the closing section.
A default sample image is provided in `templates/img/avatar.jpg` for that purpose:

![Dora's avatar](templates/img/avatar.jpg)

You can reference inline images in the templates using `cid:image0`, `cid:image1`, etc. as the `src` attribute of the `img` tags.


Don't forget to provide the inline images as parameters in the `inline_images` variable (wether inside a task file or calling `send_email` directly).
