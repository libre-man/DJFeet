from tempfile import TemporaryDirectory
import os
import multiprocessing as mp
from flask import Flask, request, jsonify
from functools import wraps
import queue
import requests
import pydub

import dj_feet.pickers as pickers
import dj_feet.core as core
from .config import Config
from .helpers import get_args


class MyFlask(Flask):
    def __init__(self, name):
        super(MyFlask, self).__init__(name)
        self._started = self._queue = self._worker = None
        self.got_options = False
        self.reset()

    def reset(self):
        self.got_options = False
        self._started = self._queue = self._worker = None

    def setup(self):
        self._started = False
        self._queue = mp.Queue(128)
        self._worker = mp.Process(
            target=backend_worker,
            args=(self._queue, app.config['REMOTE'], app.config['ID'],
                  app.config['OUTPUT_DIR']))
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
STOP, PROCESS_SONG, START_LOOP, OPTIONS = range(4)


def backend_worker(worker_queue, remote, app_id, output_dir):
    with TemporaryDirectory() as cache_dir, TemporaryDirectory() as wav_dir:
        cfg = Config()
        cfg.FIXED_OPTIONS['cache_dir'] = cache_dir
        cfg.FIXED_OPTIONS['song_folder'] = wav_dir
        cfg.FIXED_OPTIONS['output_folder'] = output_dir

        try:
            while True:
                out = worker_queue.get()
                task, *args = out

                if task == PROCESS_SONG:
                    mp3_file_location, file_id, *args = args
                    filename, _ = os.path.splitext(
                        os.path.basename(mp3_file_location))
                    song = pydub.AudioSegment.from_mp3(mp3_file_location)
                    wav_file_location = os.path.join(wav_dir,
                                                     (filename + '.wav'))
                    song.export(wav_file_location, format='wav')
                    picker = cfg.get_class(pickers.Picker, None)
                    kwargs = {
                        key: val
                        for key, val in cfg.user_config['Picker'][
                            picker.__name__].items()
                        if key in get_args(picker.process_song_file)
                    }
                    kwargs.update({'song_file': wav_file_location})
                    picker.process_song_file(**kwargs)
                    requests.post(
                        remote + '/music_processed/', json={'id': file_id})

                elif task == START_LOOP:
                    core.loop(remote, app_id,
                              cfg.get_controller(),
                              cfg.get_picker(),
                              cfg.get_transitioner(), cfg.get_communicator())

                elif task == OPTIONS:
                    new_options, *args = args
                    for basecls, vals in new_options.items():
                        cfg.update_config_class_options(basecls, vals['name'],
                                                        vals['options'])
                        cfg.update_config_main_options({basecls: vals['name']})

                elif task == STOP:
                    return
        except Exception as exp:
            requests.post('/died/', json={'id': app_id})
            raise exp


def needs_options(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if app.got_options:
            return f(*args, **kwargs)
        else:
            return jsonify(ok=False), 412  # HTTP 412 precondition

    return decorated_function


def not_started(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if app.started:
            return jsonify(ok=False), 410  # HTTP 410 gone
        else:
            return f(*args, **kwargs)

    return decorated_function


@app.route('/set_options/', methods=['POST'])
def set_config():
    if app.got_options:
        return jsonify(ok=False), 412
    app.got_options = True
    app.queue.put((OPTIONS, request.json))
    return jsonify(ok=True)


@app.route('/start/', methods=['POST'])
@not_started
@needs_options
def start_music():
    try:
        queue_item = app.queue.get_nowait()
        app.queue.put(queue_item)
        return jsonify(ok=False)
    except queue.Empty:
        app.queue.put((START_LOOP, ))
        app.started = True
        return jsonify(ok=True)


@app.route('/add_music/', methods=['POST'])
@not_started
@needs_options
def add_music():
    try:
        app.queue.put_nowait(
            (PROCESS_SONG, request.json['file_location'], request.json['id']))
        return jsonify(ok=True)
    except queue.Full:
        return jsonify(ok=False)


def im_alive():
    requests.post(
        app.config['REMOTE'] + "/im_alive/",
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
