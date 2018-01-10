import tornado.httpserver, tornado.ioloop, tornado.options, tornado.web
from tornado.options import define, options
from sqlalchemy.orm import scoped_session, sessionmaker
from views import *

from tornado.websocket import WebSocketHandler, WebSocketClosedError
from tornado.queues import Queue

define("port", default=8888, help="run on the given port", type=int)

settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "static"),
    "cookie_secret": "bZJc2sWbQLKos6GkHn/VB9oXwQt8S0R0kRvJ5/xJ89E=",
    "login_url": "/login",
}


class Subscription(WebSocketHandler):
    """Websocket for subscribers."""
    def initialize(self, publisher):
        self.publisher = publisher
        self.messages = Queue()
        self.finished = False

    def open(self):
        print("New subscriber.")
        self.publisher.register(self)
        self.run()

    def on_close(self):
        self._close()

    def _close(self):
        print("Subscriber left.")
        self.publisher.deregister(self)
        self.finished = True

    @gen.coroutine
    def submit(self, message):
        yield self.messages.put(message)

    @gen.coroutine
    def run(self):
        while not self.finished:
            message = yield self.messages.get()
            print("New message: " + str(message))
            self.send(message)

    def send(self, message):
        try:
            self.write_message(dict(value=message))
        except WebSocketClosedError:
            self._close()


class Publisher:
    """Handles new data to be passed on to subscribers."""
    def __init__(self):
        self.messages = Queue()
        self.subscribers = set()

    def register(self, subscriber):
        """Register a new subscriber."""
        self.subscribers.add(subscriber)

    def deregister(self, subscriber):
        """Stop publishing to a subscriber."""
        self.subscribers.remove(subscriber)

    @gen.coroutine
    def submit(self, message):
        """Submit a new message to publish to subscribers."""
        yield self.messages.put(message)

    @gen.coroutine
    def publish(self):
        while True:
            message = yield self.messages.get()
            if len(self.subscribers) > 0:
                print("Pushing message {} to {} subscribers...".format(
                    message, len(self.subscribers)))
                yield [subscriber.submit(message) for subscriber in self.subscribers]


@gen.coroutine
def generate_data(publisher):
    while True:
        data = random.randint(0, 9)
        yield publisher.submit(data)
        yield gen.sleep(random.randint(0, 2))


class Application(tornado.web.Application):
    def __init__(self):
        self.publisher = Publisher()
        handlers = [
            tornado.web.url(r"/", IndexHandler, name="main"),
            tornado.web.url(r"/upload", UploadHandler,  name="upload"),
            tornado.web.url(r"/login", LoginHandler,  name="login"),
            tornado.web.url(r"/logout", LogoutHandler, name="logout"),
            tornado.web.url(r"/file_list", FileListHandler, name="file_list"),
            tornado.web.url(r"/download_file/(?P<object_type>[^\/]+)/(?P<object_id>[^\/]+)", DownloadHandler, name="download_file"),
            tornado.web.url(r"/view_pages/(?P<file_id>.*)/$", PagesView, name="view_pages"),
            tornado.web.url('/socket', Subscription, dict(publisher=self.publisher)),

        ]
        tornado.web.Application.__init__(self, handlers, **settings)
        self.db = scoped_session(sessionmaker(bind=engine))


def main():
    create_all()
    app = Application()
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().add_callback(app.publisher.publish)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()