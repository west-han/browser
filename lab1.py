import socket
import ssl

class URL:
    def __init__(self, url):
        self.scheme, url = url.split('://', 1)

        assert self.scheme in ["http", "https"]

        if self.scheme == "http":
            self.port = 80
        else :
            self.port = 443

        if "/" not in url:
            url = url + "/"
        self.host, url = url.split("/", 1)
        self.path = "/" + url

        if ":" in url:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)

    def request(self):
        s = socket.socket(
            family=socket.AF_INET,  # 주소 패밀리
            type=socket.SOCK_STREAM,  # 소켓 타입
            proto=socket.IPPROTO_TCP,  # 프로토콜 직접 지정, 연결 지향형 소켓을 생성(SOCK_STREAM)하므로 TCP로 지정
        )

        s.connect((self.host, self.port))  # 파이썬 socket 모듈의 connect 메소드는 address:(ip, port) 튜플을 인자로 받음

        if self.scheme == 'https' :
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)

        # HTTP 메시지는 개행문자로 CRLF 사용
        request = "GET {} HTTP/1.0\r\n".format(self.path)  # request line
        request += ("Host: {}\r\n".format(self.host))  # header
        request += "\r\n"  # 헤더 끝, 헤더와 바디 구분을 위한 빈 라인 출력

        # 요청 시에는 텍스트 -> 바이트 인코딩, 응답을 받을 때는 바이트 -> 텍스트 디코딩
        s.send(request.encode(encoding="utf-8")) # 헤더 전송, 실제로 서버에 전송한 바이트수 반환

        # 소켓의 read 메소드를 사용하는 경우 소켓의 상태를 확인해 데이터를 읽어오는 동기 입력을 처리하기 위한 루프 작성 필요
        # 대신 위와 같은 루프를 추상화해 제공하는 makefile 헬퍼 함수 사용
        # socket.makefile()은 내부적으로 socket.SocketIO를 생성한 뒤, 이를 감싸서 파일 스트림처럼 다룰 수 있는
        # file-like object(TextIOWrapper 또는 BufferedReader)를 반환한다.
        response = s.makefile("r", encoding="utf-8", newline="\r\n")

        statusline = response.readline() # status line
        version, status, explanation = statusline.split(" ", 2)  # HTTP/1.1 200 OK

        response_headers = dict() # 헤더를 저장할 map

        while True:
            line = response.readline()
            if line == "\r\n": break # empty line 까지만 읽기
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()  # casefold(): 소문자 변환, strip(): trim

        # 중요한 헤더 - 데이터가 특별한 형태로 전송되었는지 확인
        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers

        body = response.read()
        s.close()

        return body

def show(body):
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif not in_tag:
            print(c, end="")

def load(url):
    body = url.request()
    show(body)

if __name__ == "__main__":
    import sys
    load(URL(sys.argv[1]))