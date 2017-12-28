import tornado.httpserver, tornado.ioloop, tornado.options, tornado.web, os.path, random, string
from tornado.options import define, options
import os
from sqlalchemy.orm import scoped_session, sessionmaker
from models import User, File, create_all, engine
from tornado import web
from collections import namedtuple
import pdf2image


define("port", default=8888, help="run on the given port", type=int)

STORAGE_PATH = 'uploads/'

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
            tornado.web.url(r"/download_file/(?P<file_id>.*)/$", FileDownloadHandler, name="download_file"),
        ]
        tornado.web.Application.__init__(self, handlers, **settings)
        self.db = scoped_session(sessionmaker(bind=engine))



class BaseHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return self.application.db

    def get_template_namespace(self):
        ns = super(BaseHandler, self).get_template_namespace()
        ns.update({
            'username': None,
        })

        return ns

    def get_current_user(self):
        user_id = self.get_secure_cookie("user")
        if not user_id:
            return None
        return self.db.query(User).get(int(user_id))


class LoginHandler(BaseHandler):
    def get(self):
        self.render("templates/login.html")

    def post(self):
        username = self.get_argument("name")
        user = User(username=username)
        self.db.add(user)
        self.db.commit()
        self.set_secure_cookie("user", str(user.id))
        self.redirect(self.get_argument("next", self.reverse_url("main")))


class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("user")
        self.redirect(self.get_argument("next", self.reverse_url("main")))


class IndexHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        UserFile = namedtuple('UserFile', ['username', 'filename', 'path', 'upload_date', 'file_id'])
        users_files = self.db.query(User, File).filter(User.id == File.user_id).order_by(File.upload_date).all()
        users_files_view_data = []
        for ufile in users_files:
            users_files_view_data.append(UserFile(username=ufile.User.username,
                                                  filename=ufile.File.name,
                                                  upload_date=ufile.File.upload_date.strftime('%Y-%m-%d %H:%M:%S'),
                                                  path=ufile.File.storage_location,
                                                  file_id=ufile.File.id))
        # TODO: remove milliseconds from upload_date
        self.render("templates/index.html", username=self.current_user, users_files=users_files_view_data)


class UploadHandler(BaseHandler):
    # TODO: obviously we have to use some task mechanism like celery, and work with task instance to handle big
    # files upload and to provide progress bar
    @tornado.web.authenticated
    def post(self):
        current_user = self.current_user
        file_to_upload = self.request.files['file'][0]
        original_fname = file_to_upload['filename']
        # TODO: add possibility to save file with custom name
        extension = os.path.splitext(original_fname)[1]
        if extension != '.pdf':
            raise Exception('You can upload only pdf files.')
        random_file_name = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(24))
        final_filename = random_file_name + extension
        # TODO: probably use application config instead
        base_path = STORAGE_PATH
        # TODO: This solution will lead us to huge number of files in single directory problem.
        # Use some hierarchy logic to store files depending on date or something like
        user_storage_path = os.path.join(base_path, str(current_user.id))
        if not os.path.exists(user_storage_path):
            os.makedirs(user_storage_path)
        file_storage_path = os.path.join(user_storage_path, final_filename)
        with open(file_storage_path, 'wb') as f:
            f.write(file_to_upload['body'])
        file_record = File(name=original_fname, storage_location=file_storage_path, user=current_user)
        self.db.add(file_record)
        self.db.commit()
        self.redirect(self.get_argument("next", self.reverse_url("main")))


class FileDownloadHandler(BaseHandler):
    def get(self, file_id):
        file = self.db.query(File).get(file_id)
        buf_size = 4096
        with open(file.storage_location, 'rb') as f:
            self.set_header("Content-Type", 'application/pdf; charset="utf-8"')
            self.set_header("Content-Disposition", "attachment; filename={}".format(file.name))
            while True:
                data = f.read(buf_size)
                if not data:
                    break
                self.write(data)
        self.finish()


def main():
    create_all()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()