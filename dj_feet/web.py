import multiprocessing as mp
from flask import Flask, request, g, jsonify
from functools import wraps
import queue
import requests

import dj_feet.core as core
from .config import Config

app = Flask(__name__)
STOP, PROCESS_SONG, START_LOOP = range(3)


def backend_worker(queue):
    while True:
        out = queue.get()
        if out is None:
            continue
        task, *args = out
        if task == PROCESS_SONG:
            pass
        elif task == START_LOOP:
            core.loop(app.config['REMOTE'], app.config['ID'], *args)
        elif task == STOP:
            return


def not_started(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'started' in g and g.started:
            return jsonify(ok=False), 410  # HTTP 410 gone
        else:
            return f(*args, **kwargs)

    return decorated_function


@app.route('/start', methods=['POST'])
@not_started
def start_music():
    config_dict = {
        "main": {},
        "Transitioner": {},
        "Picker": {},
        "Controller": {},
        "Communicator": {}
    }
    for key, val in request.json.items():
        name = val['name']
        config_dict['main'][key] = name
        config_dict[name] = val['options'].copy()
    config = Config()
    config.user_config = config_dict
    args = [
        config.get_controller(), config.get_picker(),
        config.get_transitioner(), config.get_communicator()
    ]
    try:
        queue_item = g.queue.get_nowait()
        g.queue.put(queue_item)
        return jsonify(ok=False)
    except queue.Empty:
        g.queue.put((START_LOOP, args))
        g.started = True
        return jsonify(ok=True)


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
    g.started = False
    q = mp.Queue(128)
    g.worker = mp.Process(target=backend_worker, args=(q, ))
    g.queue = q
    g.worker.start()
    im_alive()
    return app


if __name__ == '__main__':
    pass
