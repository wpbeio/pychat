# coding=utf-8
from asyncore import dispatcher
from asynchat import async_chat
import asyncore
import socket


__author__ = 'beio'

PORT = 6000
NAME = 'beiochat'


class EndSession(Exception):
    """结束session，爆出错误信息 """
    pass


class Commandhandle(object):

    """简单的命令处理函数"""

    def unknown(self, session, cmd):
        session.push('未知的命令行：{0}\r\n'.format(cmd).encode('gbk'))

    def handle(self, session, line):
        if not line.strip():  # strip删除首尾空字符
            return
        parts = line.split(' ', 1)  # split''分割字符串，num代表分割次数
        cmd = parts[0]

        try:
            line = parts[1].strip()
        except IndexError:
            line = ''

        meth = getattr(self, 'do_' + cmd, None)

        try:
            meth(session, line)
        except TypeError:
            self.unknown(session, cmd)


class Room(Commandhandle):
    """处理命令行，保存用户session"""

    def __init__(self, server):

        self.server = server
        self.sessions = []

    def add(self, session):
        self.sessions.append(session)

    def remove(self, session):
        self.sessions.remove(session)

    def broadcast(self, line):
        for session in self.sessions:
            session.push(line.encode('gbk'))

    def do_logout(self, session, line):
        raise EndSession


class LoginRoom(Room):
    """单人链接到聊天室"""

    def add(self, session):
        Room.add(self, session)
        self.broadcast('欢迎来到{0} \r\n'.format(self.server.name))

    def unknown(self, session, cmd):
        session.push('请登录\n使用 "login <youname>"\r\n'.encode('gbk'))

    def do_login(self, session, line):
        name = line.strip()
        if not name:
            session.push('请输入你的名字'.encode('gbk'))
        elif name in self.server.users:
            session.push('名称重复，轻重试'.encode('gbk'))
        else:
            session.name = name
            session.enter(self.server.main_room)


class ChatRoom(Room):
    """用于和多人聊天的房间"""

    def add(self, session):
        self.broadcast('{0}进入房间\r\n'.format(session.name))
        self.server.users[session.name] = session
        Room.add(self, session)

    def remove(self, session):
        Room.remove(self, session)
        self.broadcast('{0}离开房间'.format(session.name))

    def do_say(self, session, line):
        self.broadcast('{0}: {1}\r\n'.format(session.name, line))

    def do_look(self, session, line):
        # 查看房间里面的人
        session.push('房间成员 ：\r\n'.encode('gbk'))
        for other in self.sessions:
            session.push('{0}\r\n'.format(other.name).encode('gbk'))

    def do_who(self, session, line):
        # 查看现在谁在线
        session.push('在线室友\r\n'.encode('gbk'))
        for name in self.server.users:
            session.push('{0}\r\n'.format(name).encode('gbk'))


class LogoutRoom(Room):
    """离开房间"""

    def add(self, session):
        try:
            del self.server.users[session.name]
        except KeyError:
            pass


class ChatSession(async_chat):
    """实现为每个连接创建一个dispatcher对象，用于收集来自客户端的数据进行响应，使用asyn_chat"""

    def __init__(self, server, sock):
        async_chat.__init__(self, sock)
        # super(ChatSession, self).__init__()  # super虽然可以解决多重继承的问题，但对于新
        self.server = server
        self.set_terminator(b'\r\n')
        self.data = []
        self.name = None
        self.enter(LoginRoom(server))
        # self.push("欢迎光临{0}\r\n".format(self.server.name).encode())

    def enter(self, room):
        try:
            cur = self.room
        except AttributeError:
            pass
        else:
            cur.remove(self)
        self.room = room
        room.add(self)

    # 在从socket中读取一些BIT文本是调用

    def collect_incoming_data(self, data):
        self.data.append(data.decode('gbk'))

# 在读取一个结束符是调用。结束符通过set_terminator方法设置，默认为"\r\n"

    def found_terminator(self):
        line = ''.join(self.data)
        self.data = []
        try:
            self.room.handle(self, line)
        except EndSession:
            self.handle_close()

        # self.server.broadcast(line)
        # print(line)

    def handle_close(self):
        async_chat.handle_close(self)
        self.enter(LogoutRoom(self.server))
        # self.server.disconnect(self)


class ChatServer(dispatcher):

    """ChatServer继承asyncore的dispatcher以创建基础的ChatServer类"""

    def __init__(self, port, name):
        dispatcher.__init__(self)
        # super(ChatServer, self).__init__()
        self.create_socket()
        self.set_reuse_addr()
        self.bind(('', port))
        self.listen(5)
        self.name = name
        self.users = {}
        self.main_room = ChatRoom(self)

    '''def disconnect(self, session):
        self.sessions.remove(session)

    def broadcast(self, line):
        for session in self.sessions:
            # print(line)
            print(line)
            session.push((line + '\r\n').encode())'''

    def handle_accept(self):
        conn, addr = self.accept()
        ChatSession(self, conn)
        # print('链接成功', addr[0])


if __name__ == '__main__':
    s = ChatServer(PORT, NAME)
    try:
        asyncore.loop()
    except KeyboardInterrupt:

        print
