import tornado
from tornado import gen
from collections import namedtuple
from models import *
import os
import random
import string
from pdf_tools import extract_pdf_pages_as_images
from config import constants
from concurrent.futures import ThreadPoolExecutor


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
    @gen.coroutine
    def get(self):
        self.render("templates/login.html")

    @gen.coroutine
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
        self.render("templates/index.html", username=self.current_user)


class FileListHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        UserFile = namedtuple('UserFile', ['username', 'filename', 'path', 'upload_date', 'file_id'])
        users_files = self.db.query(User, File, UploadTask).filter(User.id == File.user_id).\
            filter(UploadTask.file_id == File.id).order_by(File.upload_date).all()
        users_files_view_data = []
        incomplete_uploading = []
        failed_uploading = []
        for ufile in users_files:
            file_meta = UserFile(username=ufile.User.username,
                                 filename=ufile.File.name,
                                 upload_date=ufile.File.upload_date.strftime('%Y-%m-%d %H:%M:%S'),
                                 path=ufile.File.storage_location,
                                 file_id=ufile.File.id)
            if ufile.File.id in [f.File.id for f in filter(lambda x: x.UploadTask.state == TaskState.running,
                                                           users_files)]:
                incomplete_uploading.append(file_meta)
            elif ufile.File.id in [f.File.id for f in filter(lambda x: x.UploadTask.state == TaskState.failed and
                                                                       x.User.id == self.get_current_user().id,
                                                             users_files)]:
                failed_uploading.append((file_meta, ufile.UploadTask))
            else:
                users_files_view_data.append(file_meta)

        self.render("templates/file_list.html", username=self.current_user, users_files=users_files_view_data,
                    incomplete_uploading=incomplete_uploading, failed_uploading=failed_uploading)


class UploadHandler(BaseHandler):
    executor = ThreadPoolExecutor(5)

    # TODO: obviously we have to use some task mechanism like celery, and work with task instance to handle big
    # files upload and to provide progress bar
    @tornado.gen.coroutine
    # @tornado.web.authenticated
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
        base_path = constants['STORAGE_PATH']
        # TODO: This solution will lead us to huge number of files in single directory problem.
        # Use some hierarchy logic to store files depending on date or something like
        user_storage_path = os.path.join(base_path, str(current_user.id))
        if not os.path.exists(user_storage_path):
            os.makedirs(user_storage_path)
        file_storage_path = os.path.join(user_storage_path, final_filename)

        file_record = File(name=original_fname, storage_location=file_storage_path, user=current_user)
        self.db.add(file_record)
        self.db.commit()

        upload_task = UploadTask(file=file_record)
        self.db.add(upload_task)
        self.db.commit()

        user_pages_storage_path = os.path.join(user_storage_path, random_file_name)
        if not os.path.exists(user_pages_storage_path):
            os.makedirs(user_pages_storage_path)

        self.executor.submit(self.upload_file, file_to_upload['body'], file_storage_path, file_record.id,
                             user_pages_storage_path)
        self.redirect(self.get_argument("next", self.reverse_url("main")))

    def upload_file(self, body, storage_path, file_id, user_pages_storage_path):
        # TODO: add periodic task for cleanup
        file_record = self.db.query(File).get(int(file_id))
        task = self.db.query(UploadTask).filter(UploadTask.file_id == file_id).first()
        try:
            with open(storage_path, 'wb') as f:
                f.write(body)
            for page, path in extract_pdf_pages_as_images(file_record.storage_location, user_pages_storage_path):
                self.db.add(Page(name=page, storage_location=path, file=file_record))
            task.state = TaskState.finished
        # TODO: this is bad... i'am gonna fix it
        except Exception as e:
            task.state = TaskState.failed
            task.message = str(e)
        self.db.commit()
        self.application.publisher.submit('UPDATE_FILE_LIST')


class DownloadHandler(BaseHandler):
    # TODO: Use composite design pattern here!
    downloadable_object_registry = {'file': File, 'page': Page}

    @gen.coroutine
    def get(self, object_type, object_id):
        download_obj_type = self.downloadable_object_registry.get(object_type)
        download_obj = self.db.query(download_obj_type).get(object_id)
        buf_size = 4096
        with open(download_obj.get_storage_location(), 'rb') as f:
            self.set_header("Content-Type", 'application/pdf; charset="utf-8"')
            self.set_header("Content-Disposition", "attachment; filename={}".format(download_obj.get_output_filename()))
            while True:
                data = f.read(buf_size)
                if not data:
                    break
                self.write(data)
        self.finish()


class PagesView(BaseHandler):
    @gen.coroutine
    def get(self, file_id):
        pages = self.db.query(Page).filter(Page.file_id == file_id).all()
        file = self.db.query(File).get(file_id)
        self.render("templates/pages.html", pages=pages, file=file)