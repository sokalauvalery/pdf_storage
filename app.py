import tornado.httpserver, tornado.ioloop, tornado.options, tornado.web
from tornado.options import define, options
from sqlalchemy.orm import scoped_session, sessionmaker
from views import *

define("port", default=8888, help="run on the given port", type=int)

settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "static"),
    "cookie_secret": "bZJc2sWbQLKos6GkHn/VB9oXwQt8S0R0kRvJ5/xJ89E=",
    "login_url": "/login",
}


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            tornado.web.url(r"/", IndexHandler, name="main"),
            tornado.web.url(r"/upload", UploadHandler,  name="upload"),
            tornado.web.url(r"/login", LoginHandler,  name="login"),
            tornado.web.url(r"/logout", LogoutHandler, name="logout"),
            tornado.web.url(r"/download_file/(?P<object_type>[^\/]+)/(?P<object_id>[^\/]+)", DownloadHandler, name="download_file"),
            tornado.web.url(r"/view_pages/(?P<file_id>.*)/$", PagesView, name="view_pages")
        ]
        tornado.web.Application.__init__(self, handlers, **settings)
        self.db = scoped_session(sessionmaker(bind=engine))


def main():
    create_all()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()