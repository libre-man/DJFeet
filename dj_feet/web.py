import multiprocessing as mp
from flask import Flask, request, jsonify
from functools import wraps
import queue
import requests

import dj_feet.core as core
from .config import Config


class MyFlask(Flask):
    def __init__(self, name):
        super(MyFlask, self).__init__(name)
        self._started = self._queue = self._worker = None
        self.reset()

    def reset(self):
        self._started = self._queue = self._worker = None

    def setup(self):
        self._started = False
        self._queue = mp.Queue(128)
        self._worker = mp.Process(target=backend_worker, args=(self._queue, ))
        self._worker.start()

    @property
    def started(self):
        if self._started is None:
            self.setup()
        else:
            return self._started

    @started.setter
    def started(self, value):
        if self._started is None:
            self.setup()
        self._started = value

    @property
    def queue(self):
        if self._queue is None:
            self.setup()
        return self._queue

    @property
    def worker(self):
        if self._worker is None:
            self.setup()
        return self._worker


app = MyFlask(__name__)
STOP, PROCESS_SONG, START_LOOP, NOOP = range(4)


def backend_worker(queue):
    while True:
        out = queue.get()
        if out is None:
            continue
        task, *args = out
        if task == NOOP:
            print('NOOP')
        if task == PROCESS_SONG:
            pass
        elif task == START_LOOP:
            core.loop(app.config['REMOTE'], app.config['ID'], *args)
        elif task == STOP:
            return


def not_started(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if app.started:
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
        queue_item = app.queue.get_nowait()
        app.queue.put(queue_item)
        return jsonify(ok=False)
    except queue.Empty:
        app.queue.put((START_LOOP, args))
        app.started = True
        return jsonify(ok=True)


def im_alive():
    requests.post(
        app.config['REMOTE'] + "/im_alive",
        json={
            'id': app.config['ID'],
            'options': Config.get_all_options(),
        })


def start(id_string, input_dir, output_dir, remote_addr):
    app.config.update({
        'ID': int(id_string),
        'INPUT_DIR': input_dir,
        'OUTPUT_DIR': output_dir,
        'REMOTE': remote_addr,
    })
    app.reset()
    app.setup()
    im_alive()
    return app


if __name__ == '__main__':
    pass
