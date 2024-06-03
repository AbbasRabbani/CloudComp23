# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import base64
import copy
import io
import socket
from pkg_resources import resource_filename

import flask
from flask_restless import APIManager
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from kombu import Connection
from kombu.pools import producers
from oslo_config import cfg
from oslo_log import log
from PIL import Image
from sqlalchemy.dialects import mysql

from faafo import queues
from faafo import version

LOG = log.getLogger('faafo.api')
CONF = cfg.CONF

api_opts = [
    cfg.StrOpt('listen-address',
               default='0.0.0.0',
               help='Listen address.'),
    cfg.IntOpt('bind-port',
               default='80',
               help='Bind port.'),
    cfg.StrOpt('database-url',
               default='sqlite:////tmp/sqlite.db',
               help='Database connection URL.')
]

CONF.register_opts(api_opts)

log.register_options(CONF)
log.set_defaults()

CONF(project='api', prog='faafo-api',
     default_config_files=['/etc/faafo/faafo.conf'],
     version=version.version_info.version_string())

log.setup(CONF, 'api',
          version=version.version_info.version_string())

template_path = resource_filename(__name__, "templates")
app = flask.Flask('faafo.api', template_folder=template_path)
app.config['DEBUG'] = CONF.debug
app.config['SQLALCHEMY_DATABASE_URI'] = CONF.database_url

with app.app_context():
    db = SQLAlchemy(app)

Bootstrap(app)


def list_opts():
    """Entry point for oslo-config-generator."""
    return [(None, copy.deepcopy(api_opts))]


class Fractal(db.Model):
    uuid = db.Column(db.String(36), primary_key=True)
    checksum = db.Column(db.String(256), unique=True)
    url = db.Column(db.String(256), nullable=True)
    duration = db.Column(db.Float)
    size = db.Column(db.Integer, nullable=True)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    iterations = db.Column(db.Integer, nullable=False)
    xa = db.Column(db.Float, nullable=False)
    xb = db.Column(db.Float, nullable=False)
    ya = db.Column(db.Float, nullable=False)
    yb = db.Column(db.Float, nullable=False)

    if CONF.database_url.startswith('mysql'):
        LOG.debug('Using MySQL database backend')
        image = db.Column(mysql.MEDIUMBLOB, nullable=True)
    else:
        image = db.Column(db.LargeBinary, nullable=True)

    generated_by = db.Column(db.String(256), nullable=True)

    def __repr__(self):
        return '<Fractal %s>' % self.uuid


with app.app_context():
    db.create_all()

manager = APIManager(app=app, session=db.session)
connection = Connection(CONF.transport_url)


@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
@app.route('/index/<int:page>', methods=['GET'])
def index(page=1):
    hostname = socket.gethostname()
    fractals = Fractal.query.filter(
        (Fractal.checksum is not None) & (Fractal.size is not None)).paginate(
            page=page, per_page=5)
    return flask.render_template('index.html', fractals=fractals, hostname=hostname)


@app.route('/fractal/<string:fractalid>', methods=['GET'])
def get_fractal(fractalid):
    fractal = Fractal.query.filter_by(uuid=fractalid).first()
    if not fractal:
        response = flask.jsonify({'code': 404,
                                  'message': 'Fracal not found'})
        response.status_code = 404
    else:
        image_data = base64.b64decode(fractal.image)
        image = Image.open(io.BytesIO(image_data))
        output = io.BytesIO()
        image.save(output, "PNG")
        image.seek(0)
        response = flask.make_response(output.getvalue())
        response.content_type = "image/png"

    return response


def generate_fractal(**kwargs):
    LOG.debug("Postprocessor called!" + str(kwargs))
    with producers[connection].acquire(block=True) as producer:
        producer.publish(kwargs['result'],
                         serializer='json',
                         exchange=queues.task_exchange,
                         declare=[queues.task_exchange],
                         routing_key='normal')


def convert_image_to_binary(**kwargs):
    LOG.debug("Preprocessor call: " + str(kwargs))
    if 'image' in kwargs['data']['data']['attributes']:
        LOG.debug("Converting image to binary...")
        kwargs['data']['data']['attributes']['image'] = \
            str(kwargs['data']['data']['attributes']['image']).encode("ascii")


def main():
    print("Starting API server - new...")
    with app.app_context():
        manager.create_api(Fractal, methods=['GET', 'POST', 'DELETE', 'PATCH'],
                           postprocessors={'POST_RESOURCE': [generate_fractal]},
                           preprocessors={'PATCH_RESOURCE': [convert_image_to_binary]},
                           exclude=['image'],
                           url_prefix='/v1',
                           allow_client_generated_ids=True)
    app.run(host=CONF.listen_address, port=CONF.bind_port, debug=True)
