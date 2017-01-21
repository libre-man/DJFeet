from .config import Config
import dj_feet.core as core
from flask import Flask, request
import requests

app = Flask(__name__)
APP_ID = None


def im_alive():
    requests.post(
        app.config['REMOTE'] + "/im_alive",
        data={
            'id': app.config['ID'],
            'options': Config.get_all_options(),
        })


def start(id_string, input_dir, output_dir, remote_addr):
    app_id = int(id_string)
    app.config.update({
        'ID': app_id,
        'INPUT_DIR': input_dir,
        'OUTPUT_DIR': output_dir,
        'REMOTE': remote_addr,
    })
    im_alive()
    return app


if __name__ == '__main__':
    pass
