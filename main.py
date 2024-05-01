import importlib.util
import os
import sys
from dora_mailer import *


def load_task_module(task_file):
    # Cargar el módulo de la tarea
    task_path = os.path.join('tasks', task_file)
    spec = importlib.util.spec_from_file_location("task_module", task_path)
    task_module = importlib.util.module_from_spec(spec)
    sys.modules["task_module"] = task_module
    spec.loader.exec_module(task_module)
    return task_module


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Mo se ha especificado ninguna tarea como argumento.")
        exit(1)
    else:
        task_file = f'{sys.argv[1]}.py'

    # Cargar el archivo de configuración
    mailer = DoraMailer.from_config('dora_mailer.conf')

    # Cargar las variables del archivo de tarea
    task_module = load_task_module(task_file)

    # Asumir que las variables están definidas en el módulo cargado
    subject = task_module.subject
    to_addresses = task_module.to_addresses
    cc_addresses = getattr(task_module, 'cc_addresses', [])
    bcc_addresses = getattr(task_module, 'bcc_addresses', [])
    inline_images = getattr(task_module, 'inline_images', [])
    attachments = getattr(task_module, 'attachments', [])
    template = task_module.template
    message = task_module.message

    # Convertir el mensaje de texto plano a HTML
    message = DoraMailer.txt_to_html(message)  # cambia saltos de línea a <br/>

    # Cargar el cuerpo del mensaje desde la plantilla
    body = mailer.load_template(template, {'message': message})

    # Enviar el correo
    success = mailer.send_email(subject, body, to_addresses, cc_addresses, bcc_addresses, attachments, inline_images)

    if success:
        print("Correo enviado con éxito")
        exit(0)
    else:
        print("Error al enviar el correo")
        exit(1)

