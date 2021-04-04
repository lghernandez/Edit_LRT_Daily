import paramiko, socks

from constants import USERNAME, PASSWORD


def create_sftp_connection(host, myuser=USERNAME, mypassword=PASSWORD):
    sock = socks.socksocket()

    sock.set_proxy(
        proxy_type=socks.SOCKS5,
        addr="127.0.0.1",
        port=1500,
    )

    sock.connect((host, 22))

    transport = paramiko.Transport(sock)
    transport.connect(username=myuser, password=mypassword)
    sftp_conn = paramiko.SFTPClient.from_transport(transport)
    return sftp_conn, transport


def create_ssh_connection(host, myuser=USERNAME, mypassword=PASSWORD):
    sock = socks.socksocket()

    sock.set_proxy(
        proxy_type=socks.SOCKS5,
        addr="127.0.0.1",
        port=1500,
    )

    sock.connect((host, 22))

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=host, username=myuser, password=mypassword, sock=sock)
    return ssh