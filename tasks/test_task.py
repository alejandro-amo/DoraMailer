import os
"""
your regular tasks can simply specify a string with your address, but in this particular case we use 
DORA_TEST_RECIPIENT environment variable, so we import os module.
don't forget to configure your testing email address via DORA_TEST_RECIPIENT variable in your .env file. It's mandatory!
"""
recipient = os.getenv("DORA_TEST_RECIPIENT")
if not recipient:
    raise ValueError("DORA_TEST_RECIPIENT is not set in the environment.")

subject = "Test Subject"
template = "test_task.html"
to_addresses = [recipient]
cc_addresses = None
bcc_addresses = None
context = {}
"""
The provided base.html template requires one inline image which will be embedded in the email's closing section, serving as an avatar. You can reference inline images in HTML templates by specifying "cid:image0", "cid:image1", "cid:image2", etc., as the src attribute of the <img> HTML tag.
"""
inline_images = ["templates/img/avatar.jpg"]
