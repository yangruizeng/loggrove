# Created by zhouwang on 2018/5/17.

from .base import BaseRequestHandler, permission
import datetime
import hashlib

def check_argements(handler, pk=None):
    error = {}
    username = handler.get_argument('username', '')
    password = handler.get_argument('password', '')
    email = handler.get_argument('email', '')
    status = handler.get_argument('status', '')
    role = handler.get_argument('role', '')
    fullname = handler.get_argument('fullname', '')

    if not username:
        error['username'] = '用户名是必填项'
    else:
        select_sql = 'SELECT id FROM user WHERE username="%s" %s' % (username, 'and id!="%d"' % pk if pk else '')
        count = handler.mysqldb_cursor.execute(select_sql)
        if count:
            error['username'] = '用户名已存在'

    if handler.request.method == 'POST':    #添加用户时，需要判断密码
        if not password:
            error['password'] = '密码是必填项'
        else:
            password = hashlib.md5(password.encode('UTF-8')).hexdigest()

    if not email:
        error['email'] = '邮箱是必填项'
    if status not in ['1', '2']:
        error['status'] = '状态选择不正确'
    if role not in ['1', '2', '3']:
        error['role'] = '角色选择不正确'

    request_data = {
        'username':username,
        'password':password,
        'email':email,
        'status':status,
        'role':role,
        'fullname':fullname
    }
    return error, request_data


def add_valid(func):
    def _wrapper(self):
        error, self.reqdata = check_argements(self)
        if error:
            return {'code': 400, 'msg': 'Bad POST data', 'error': error}
        return func(self)
    return _wrapper


def query_valid(func):
    def _wrapper(self, pk):
        error = {}
        if not pk and self.request.arguments:
            argument_keys = self.request.arguments.keys()
            query_keys = ['id', 'username', 'email', 'fullname']
            error = {key:'参数不可用' for key in argument_keys if key not in query_keys}
        if error:
            return {'code': 400, 'msg': 'Bad GET param', 'error': error}
        return func(self, pk)
    return _wrapper


def update_valid(func):
    def _wrapper(self, pk):
        select_sql = 'SELECT id FROM user WHERE id="%d"' % pk
        count = self.mysqldb_cursor.execute(select_sql)
        if not count:
            return {'code': 404, 'msg': 'Update row not found'}
        error, self.reqdata = check_argements(self, pk)
        if error:
            return {'code': 400, 'msg': 'Bad PUT param', 'error': error}
        return func(self, pk)
    return _wrapper


def del_valid(func):
    def _wrapper(self, pk):
        select_sql = 'SELECT id FROM user WHERE id="%d"' % pk
        count = self.mysqldb_cursor.execute(select_sql)
        if not count:
            return {'code': 404, 'msg': 'Delete row not found'}
        return func(self, pk)
    return _wrapper


class User():
    def __init__(self):
        self.reqdata = {}

    @query_valid
    def _query(self, pk):
        select_sql = '''
                        SELECT
                            id,
                            username,
                            fullname,
                            email,
                            status,
                            role,  
                            date_format(join_time, "%%Y-%%m-%%d %%H:%%i:%%s") as join_time
                        FROM user
                        %s
                        ''' % self.format_where_param(pk, self.request.arguments)
        self.mysqldb_cursor.execute(select_sql)
        results = self.mysqldb_cursor.fetchall()
        return {'code': 200, 'msg': 'Query successful', 'data': results}

    @add_valid
    def _add(self):
        insert_sql = '''
            INSERT INTO 
              user (
                username, 
                password, 
                fullname, 
                email,
                join_time, 
                status, 
                role) 
            VALUES ("%s", "%s", "%s", "%s", "%s", "%s", "%s")
        ''' % (self.reqdata['username'],
               self.reqdata['password'],
               self.reqdata['fullname'],
               self.reqdata['email'],
               datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
               self.reqdata['status'],
               self.reqdata['role'])
        try:
            self.mysqldb_cursor.execute(insert_sql)
            self.mysqldb_conn.commit()
        except Exception as e:
            self.mysqldb_conn.rollback()
            return {'code': 500, 'msg': 'Add failed, %s' % str(e)}
        else:
            self.mysqldb_cursor.execute('SELECT LAST_INSERT_ID() as id')
            return {'code': 200, 'msg': 'Add successful', 'data': self.mysqldb_cursor.fetchall()}

    @update_valid
    def _update(self, pk):
        update_sql = '''
            UPDATE 
              user 
            SET 
              username="%s", 
              fullname="%s",
              email="%s",
              status="%s",
              role="%s"
            WHERE 
              id="%d"
        ''' % (
            self.reqdata['username'],
            self.reqdata['fullname'],
            self.reqdata['email'],
            self.reqdata['status'],
            self.reqdata['role'],
            pk)

        try:
            self.mysqldb_cursor.execute(update_sql)
            self.mysqldb_conn.commit()
        except Exception as e:
            self.mysqldb_conn.rollback()
            return {'code': 500, 'msg': 'Update failed, %s' % str(e)}
        else:
            return {'code': 200, 'msg': 'Update successful', 'data': {'id': pk}}

    @del_valid
    def _del(self, pk):
        delete_sql = 'DELETE FROM user WHERE id="%d"' % pk
        try:
            self.mysqldb_cursor.execute(delete_sql)
            self.mysqldb_conn.commit()
        except Exception as e:
            self.mysqldb_conn.rollback()
            return {'code': 500, 'msg': 'Delete failed, %s' % str(e)}
        else:
            return {'code': 200, 'msg': 'Delete successful'}


class Handler(BaseRequestHandler, User):
    @permission()
    def get(self, pk=0):
        ''' Query '''
        response_data = self._query(int(pk))
        return self._write(response_data)

    @permission(role=1)
    def post(self):
        response_data = self._add()
        self._write(response_data, audit=True)

    @permission(role=1)
    def put(self, pk=0):
        response_data = self._update(int(pk))
        self._write(response_data, audit=True)

    @permission(role=1)
    def delete(self, pk=0):
        response_data = self._del(int(pk))
        self._write(response_data, audit=True)