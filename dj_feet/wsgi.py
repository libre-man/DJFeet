import dj_feet.web as web
from os import getenv

app = web.start(
    getenv('SDAAS_ID'),
    getenv('SDAAS_INPUT_DIR'),
    getenv('SDAAS_OUTPUT_DIR'), getenv('SDAAS_REMOTE_URL'))
