import tkinter
import tkinter.font
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

class Text:
    def __init__(self, text):
        self.text = text

class Tag:
    def __init__(self, tag):
        self.tag = tag

def lex(body):
    out = []
    buffer = ""

    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
            if buffer: out.append(Text(buffer))
            buffer = ""
        elif c == ">":
            in_tag = False
            out.append(Tag(buffer))
            buffer = ""
        elif not in_tag:
            buffer += c
    if not in_tag and buffer:
        out.append(Text(buffer)) # 태그로 감싸지 않은 텍스트 flush, 현대 브라우저들의 기본 동작이 미완성 태그를 drop하는 방식이므로 이를 따름
    return out

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18

class Layout:
    def __init__(self, tokens):
        self.display_list = []
        self.line = []
        self.cursor_x = VSTEP
        self.cursor_y = HSTEP
        self.weight = "normal"
        self.style = "roman"
        self.size = 12
        for tok in tokens:
            self.token(tok)
        self.flush()

    def token(self, tok):
        if isinstance(tok, Text):
            for word in tok.text.split():
                self.word(word)
        elif tok.tag == "i":
            self.style = "italic"
        elif tok.tag == "/i":
            self.style = "normal"
        elif tok.tag == "b":
            self.style = "bold"
        elif tok.tag == "/b":
            self.style = "normal"
        elif tok.tag == 'small':
            self.size -= 2
        elif tok.tag == '/small':
            self.size += 2
        elif tok.tag == 'big':
            self.size += 4
        elif tok.tag == '/big':
            self.size -= 4
        elif tok.tag == 'br':
            self.flush()
        elif tok.tag == '/p':
            self.flush()
            self.cursor_y += VSTEP # 문단 사이 간격 추가

        return self.display_list

    def word(self, word):
        font = tkinter.font.Font(
            size=self.size,
            weight=self.weight,
            slant=self.style
        )
        w = font.measure(word) # 단어의 가로 길이
        if self.cursor_x + w > WIDTH - HSTEP: #
            self.flush()
            # self.cursor_y += font.metrics("linespace") * 1.25 # linespace(텍스트 높이)의 1.25배
            # self.cursor_x = HSTEP
        # self.display_list.append((self.cursor_x, self.cursor_y, word, font)) # 렌더링 대상 문자와 레이아웃 상의 좌표 튜플 저장
        self.line.append((self.cursor_x, word, font)) # 텍스트 수직 정렬을 맞추기 위해 display_list에 추가하기 전에 우선 y 위치 값이 없는 임시 데이터 저장
        self.cursor_x += w + font.measure(" ") # split()으로 공백이 사라졌으므로 단어 가로 길이 + 공백 너비만큼 더하기


    # 1. 기준선에 맞춰 단어 정렬, display_list에 모든 단어 추가, cursor_x와 cursor_y 업데이트
    def flush(self):
        if not self.line: return
        metrics = [font.metrics() for x, word, font in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics]) # cf. 폰트의 메트릭 - ascent, x-height, descent

        baseline = self.cursor_y + 1.25 * max_ascent # self.y에서 leading + max_ascent만큼 아래를 기준선으로

        for x, word, font in self.line:
            y = baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font))

        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent

        self.cursor_x = HSTEP
        self.line = []

SCROLL_STEP = 100
class Browser:
    def __init__(self):
        self.windows = tkinter.Tk() # 데스크톱 환경에 윈도우 생성 요청, 윈도우를 조작하기 위한 객체 반환
        self.canvas = tkinter.Canvas(self.windows, width=WIDTH, height=HEIGHT) # 윈도우에 대한 캔버스 생성
        self.canvas.pack() # Tk가 캔버스를 창에 배치하기 위해 호출해야 하는 메소드
        self.scroll = 0
        self.windows.bind("<Down>", self.scrolldown) # 이벤트핸들러 바인딩
        self.display_list = []

    def load(self, url):
        body = url.request()
        tokens = lex(body)
        self.display_list = Layout(tokens).display_list
        self.draw()

    def draw(self):
        for x, y, c, font in self.display_list:
            if y > HEIGHT + self.scroll:
                continue
            if y + VSTEP < self.scroll: # VSTEP 더하는 이유는 글자가 완전히 화면 밖으로 나가는 경우만 스킵하기 위함
                continue
            self.canvas.create_text(x, y - self.scroll, text=c) # anchor="nw" : 좌표의 기준을 텍스트의 북서쪽 모서리로 설정

    def scrolldown(self, event):
        self.scroll += SCROLL_STEP
        self.canvas.delete("all")
        self.draw()

if __name__ == "__main__":
    import sys
    Browser().load(URL(sys.argv[1]))
    tkinter.mainloop() # 화면 조작 이벤트를 리스닝, 핸들링 하는 이벤트 루프 실행

