import hashlib
import http.server
import socketserver
import urllib.parse
import threading
import socket
import os
import random
import json
import cgi
import base64
from threading import Event

# BELOW IS JUST TO ENABLE REUSE TERMINAL ON CTRL-C PRESS
# #############################################
import signal
import sys


def signal_handler(sig, frame):
    print("Ctrl+C pressed. Exiting...")
    os._exit(0)


signal.signal(signal.SIGINT, signal_handler)
# #############################################

# get the absolute path of the current directory
current_dir = os.path.abspath(os.path.dirname(__file__))

# set the path to the users.txt file relative to the current directory
users_file = os.path.join(current_dir, "users.txt")

# set the path to the users.txt file relative to the current directory
questions_file = os.path.join(current_dir, "questions.txt")

LOGIN_FORM = """
    <!DOCTYPE html>
    <html lang="en">
        <head>
            <title>CITS3002 Project</title>
        </head>
        <body>
            <form method="get" action="/login">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username"><br><br>
                <label for="password">Password:</label>
                <input type="password" id="password" name="password"><br><br>
                <input type="submit" value="Login">
            </form>
        </body>
    </html>
"""

QUESTION_BANKS = []

# The port to listen on for HTTP connections
HTTP_PORT = 3002

# The port to listen on for TCP connections
TCP_PORT = 30020

MARKED_EVENT = Event()
MARKED_LIST = []


class ThreadedHTTPHandler(socketserver.ThreadingMixIn, http.server.HTTPServer):
    pass


class HTTPHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            # Send login form
            self._send_login_form()
        if self.path == "/home":
            self._handle_homepage()
        elif self.path.startswith("/login"):
            # Handle login request
            self._handle_login_request()
        elif self.path.startswith("/test"):
            self._handle_start_test()
        elif self.path.startswith("/logout"):
            self._handle_logout()

    def _send_login_form(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        login_form = LOGIN_FORM
        self.wfile.write(login_form.encode())

    def _handle_logout(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        # unset the 'username' cookie by setting its expiration date to a date in the past
        self.send_header(
            "Set-Cookie", "username=; expires=Thu, 01 Jan 1970 00:00:00 GMT"
        )
        self.end_headers()

        response = f"""
                <!DOCTYPE html>
                <html lang="en">
                    <head>
                        <title>CITS3002 Project</title>
                    </head>
                    <body>
                        <div>Succesfully logged out.</div>
                        <div><a href="/">Log in</a></div>
                        
                </html>     
            """
        # send the HTTP response body
        self.wfile.write(response.encode())

    def _handle_homepage(self):
        user = self._get_username_cookie()
        if not user:
            # user is not logged in, redirect to login page
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
        else:
            # user is logged in, send homepage response
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self._send_logged_in_response(user)

    def _handle_start_test(self):
        username = self._get_username_cookie()
        if not username:
            self.send_response(302)
            self.send_header("Location", "http://localhost:3002/")
            self.end_headers()
            return None

        query = urllib.parse.urlparse(self.path).query
        query_dict = urllib.parse.parse_qs(query)

        if not query_dict:
            self.send_response(302)
            self.send_header("Location", "http://localhost:3002/test?q=1")
            self.end_headers()
            return None

        current_question = int(query_dict.get("q", [""])[0])
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        username = self._get_username_cookie()
        questions = get_user_questions(username)

        if current_question <= 0 or not username or current_question > len(questions):
            response = f"""
                <!DOCTYPE html>
                <html lang="en">
                    <head>
                        <title>CITS3002 Project</title>
                    </head>
                    <body>
                        <div>Question not found</div>
                        <a href="javascript:void(0)" onclick="history.back();">Go Back</a>
                </html>     
            """
        else:
            response = create_question_form(questions, current_question)
        self.wfile.write(response.encode())

    def _handle_login_request(self):
        # Parse username and password from query string
        query = urllib.parse.urlparse(self.path).query
        query_dict = urllib.parse.parse_qs(query)
        username = query_dict.get("username", [""])[0]
        password = query_dict.get("password", [""])[0]

        # Check if username and password match
        if self._check_credentials(username, password):
            self.send_response(302)
            self.send_header("Content-type", "text/html")
            self.send_header("Set-Cookie", f"username={username}")
            self.send_header("Location", "/home")
            self.end_headers()
        else:
            # Send login form with error message
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            login_form = (
                """
                <p>Incorrect login - try again</p>
            """
                + LOGIN_FORM
            )
            self.wfile.write(login_form.encode())

    def _get_username_cookie(self):
        if "Cookie" in self.headers:
            cookies = self.headers["Cookie"].split(";")
            for cookie in cookies:
                name, value = cookie.strip().split("=")
                if name == "username":
                    username = value
                    break
            else:
                username = None
        else:
            username = None
        return username

    def _check_credentials(self, username, password):
        # Check if username and password match a line in users.txt
        with open(users_file, "r") as f:
            creds = json.loads(f.read())

        for credentials in creds:
            if (
                username == credentials["username"]
                and password == credentials["password"]
            ):
                return True
        return False

    def _send_logged_in_response(self, username):
        user_questions = get_user_questions(username)
        test_completed = False
        test_started = False
        if not user_questions:
            for qb in QUESTION_BANKS:
                data = (
                    json.dumps({"type": "LOGIN", "message": {"user": username}}) + "\n"
                )
                send_data_to_question_bank(qb["address"], qb["port"], data)
        else:
            marks = countMarks(user_questions)
            for question in user_questions:
                if question["correct"] == True or question["attempts"] == 3:
                    test_completed = True
                else:
                    test_completed = False
                    break

            for question in user_questions:
                if question["attempts"] > 0:
                    test_started = True
                    break

            for i, question in enumerate(user_questions):
                if question["attempts"] < 3 and question["correct"] == False:
                    first_unfinished_question = i + 1
                    break

        ## NEED TO CHANGE TO 2 AT END - SET TO 1 FOR DEVELOPMENT
        if len(QUESTION_BANKS) < 1:
            response = """<p>Not enough question banks connected</p>"""
        elif test_completed:
            response = f"""<p>You have finished this test already with a score of {marks}/{len(user_questions) * 3}</p>
                <a href='/test?q=1'>Review Answers</a>
            """
        elif test_started:
            response = f"""<p><a href='/test?q={first_unfinished_question}'>Continue Test</a></p>"""
        else:
            response = """<p><a href='/test?q=1'>Start Test</a></p>"""
        response = f"""
                <!DOCTYPE html>
                <html lang="en">
                    <head>
                        <title>CITS3002 Project</title>
                    </head>
                    <body>
                        <div><a href="/home">Home</a> | <a href="/logout">Logout</a></div>
                        <p>Hi, {username.capitalize()}.</p>
                        {response}
                    </body>
                </html>     
        """

        self.wfile.write(response.encode())

    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        answer = ""
        if self.path == "/upload":
            form = cgi.FieldStorage(
                fp=self.rfile, headers=self.headers, environ={"REQUEST_METHOD": "POST"}
            )

            file_item = form["bytes"]
            image_data = file_item.file.read()
            encoded_image = base64.b64encode(image_data)
            answer = encoded_image.decode("utf-8")
            question_id = form["question_id"].value
            question_number = form["question_number"].value

        else:
            post_data = self.rfile.read(content_length)
            params = urllib.parse.parse_qs(post_data.decode("utf-8"))

            # check for forms using the /submit-answers action
            if self.path == "/test":
                for key, value in params.items():
                    if key == "question_number":
                        question_number = value[0]
                    elif key == "question_id":
                        question_id = value[0]
                    elif key == "answer":
                        answer = value[0]

        # #THIS WILL SEND ALL ANSWERS MIGHT ONLY NEED TO SEND RELEVANT
        destination_qb = ""
        if "p" in question_id:
            destination_qb = "python"
        elif "j" in question_id:
            destination_qb = "java"

        username = self._get_username_cookie()

        for qb in QUESTION_BANKS:
            if qb["name"] == destination_qb:
                data = (
                    json.dumps(
                        {
                            "type": "MARK",
                            "message": {
                                "id": question_id,
                                "answer": answer,
                                "user": username,
                            },
                        }
                    )
                    + "\n"
                )
                print("Sent:", data)
                send_data_to_question_bank(qb["address"], qb["port"], data)
                # If username has not been marked then wait for a marked event
                while username not in MARKED_LIST:
                    MARKED_EVENT.wait()
                MARKED_LIST.remove(username)

        self.send_response(301)
        self.send_header("Location", f"http://localhost:3002/test?q={question_number}")
        self.end_headers()


class TCPHandler(threading.Thread):
    def __init__(self):
        super().__init__()
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.bind(("localhost", TCP_PORT))
        self.tcp_socket.listen()

    def run(self):
        try:
            while True:
                conn, addr = self.tcp_socket.accept()
                with conn:
                    data = b""
                    while True:
                        chunk = conn.recv(1024)
                        data += chunk
                        if b"\n" in chunk:
                            break
                    data = data.decode("utf-8")
                    print("Recieved:", data)

                    message = json.loads(data)
                    msg_type = message["type"]
                    msg_content = message["message"]

                    if msg_type == "QUESTION_BANK":
                        QUESTION_BANKS.append(
                            {
                                "name": msg_content["language"],
                                "address": addr[0],
                                "port": msg_content["port-used"],
                            }
                        )
                    elif msg_type == "QUESTIONS":
                        for question in msg_content["questions"]:
                            question["attempts"] = 0
                            question["correct"] = False
                        append_user_questions(
                            msg_content["user"], msg_content["questions"]
                        )

                    elif msg_type == "MARKED":
                        user = msg_content["user"]
                        update_user_questions(
                            user,
                            msg_content["id"],
                            msg_content["correct"],
                            msg_content["answer"],
                            msg_content["correct-answer"],
                        )
                        MARKED_LIST.append(user)
                        MARKED_EVENT.set()
                        MARKED_EVENT.clear()

        except KeyboardInterrupt:
            print("\nKeyboard interrupt detected. Cleaning up...")
        finally:
            self.tcp_socket.close()


def create_question_form(questions, question_num):
    question = questions[question_num - 1]
    question_links = ""
    for i in range(len(questions)):
        question_links = question_links + f' <a href="/test?q={i + 1}">{i+1}</a> '
    if question_num == 1:
        links = f"""{question_links}<a href="/test?q={question_num + 1}">Next</a>"""
    elif question_num == len(questions):
        links = f"""<a href="/test?q={question_num - 1}">Previous</a>{question_links}"""
    else:
        links = f"""<a href="/test?q={question_num - 1}">Previous</a> {question_links} <a href="/test?q={question_num + 1}">Next</a>"""

    current_attempts = question["attempts"]

    feedback = ""

    if current_attempts >= 1 and current_attempts < 3 and not question["correct"]:
        feedback = f"You've gotten this answer incorrect. You have {3 - current_attempts} attempts remaining. Please try again."

    form_format = """<form action="/test" method="post">"""
    if question["type"] == "image":
        form_format = (
            """<form action="/upload" enctype="multipart/form-data" method="post">"""
        )

    form = f"""
    <!DOCTYPE html>
    <html lang="en">
        <head>
            <title>CITS3002 Project</title>
        </head>
        <body>
            <div><a href="/home">Home</a> | <a href="/logout">Logout</a></div>
            <div>{links}</div>
            <div>Question {question_num}</div>
            <div>attempts: {current_attempts}</div>
            <div>marks: {countMarks(questions)}/{len(questions) * 3}</div>
            <div>{feedback}</div>
            {form_format}
            <input type="hidden" name="question_number" value="{question_num}">
            <input type="hidden" name="question_id" value="{question["id"]}">
            <input type="hidden" name="attmepts" value="{question["attempts"]}">
    """
    if question["correct"]:
        button = f"""
            <div>
                <p> You've gotten this question correct :)</p>
            </div>"""
    elif current_attempts >= 3:
        button = f"""
            <div>
                <p> 3 Attempts maximum </p>
            </div>"""
    else:
        button = """<button type="submit">Submit Answer</button>"""

    if question["type"] == "true-or-false":
        correct_answer = ""
        disabled = ""
        if current_attempts >= 3 or question["correct"]:
            disabled = "disabled"
            correct_answer = f"""
            <div><p>Correct answer: {question.get("correct-answer", "")}</p></div>
            """

        true_checked = ""
        false_checked = ""
        last_answer = question.get("last-answer", "")
        if last_answer == "True":
            true_checked = "checked"
        elif last_answer == "False":
            false_checked = "checked"

        form = (
            form
            + f"""
        <div>
            <p>{question["question"]}</p>
                <input type="radio" name="answer" value="True" {disabled} {true_checked}>
                <label for="html" {disabled}>True</label>
                <input type="radio" name="answer" value="False" {disabled} {false_checked}>
                <label for="html" {disabled}>False</label>
            {correct_answer}
        </div>"""
        )
    elif question["type"] == "code":
        sample_code = ""
        readonly = ""
        if current_attempts >= 3 or question["correct"]:
            readonly = "readonly"
            sample_code = f"""
            <div>
                <p>Example correct code:</p>
                <textarea rows="20" cols="100" name="answer" readonly>{question.get("correct-answer", "")}</textarea>
            </div>
            """

        form = (
            form
            + f"""
        <div>
            <p>{question["question"]}</p>
            <form action="/submit-answers" method="post">
                <label for="html">Answer</label>
                <textarea rows="20" cols="100" name="answer" {readonly}>{question.get("last-answer", "")}</textarea>
                {sample_code}
        </div>"""
        )

    elif question["type"] == "multi":
        options = question["question"].split(":")[1].split(",")
        options_form = ""

        correct_answer = ""
        disabled = ""
        if current_attempts >= 3 or question["correct"]:
            disabled = "disabled"
            correct_answer = f"""
            <div><p>Correct answer: {question.get("correct-answer", "")}</p></div>
            """

        last_answer = question.get("last-answer", "")

        for option in options:
            checked = ""
            if option == last_answer:
                checked = "checked"
            options_form = (
                options_form
                + f"""
                <input type="radio" name="answer" value="{option}" {disabled} {checked}>
                <label for="html" {disabled}>{option}</label>
                <br>
            """
            )

        form = (
            form
            + f"""
        <div>
            <p>{question["question"].split(":")[0]}</p>
                {options_form}
            {correct_answer}
        </div>"""
        )
    elif question["type"] == "image":
        options = question["question"].split("#")[1].split(",")
        options_form = ""
        correct_answer = ""
        disabled = ""

        if current_attempts >= 3 or question["correct"]:
            disabled = "disabled"
            correct_answer = question.get("correct-answer", "")

        for option in options:
            options_form = (
                options_form
                + f"""
                <a href={option}><img src="{option}"></img></a>
                <br>
            """
            )
        form = (
            form
            + f"""
        <div>
            <p>{question["question"].split("#")[0]}</p>
                {options_form}
                <label for="html">Upload correct image:</label>
                <input type="file" name="bytes" {disabled} accept="image/*">
            <img url="{correct_answer}"></img>
        </div>"""
        )

    form = (
        form
        + f"""
            </br>
            {button}
        </form>
        </body>
        </html>
        """
    )
    return form


def send_data_to_question_bank(host, port, data):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        s.sendall(bytes(str(data), "utf-8"))


def get_user_questions(user):
    if os.path.exists(questions_file):
        with open(questions_file, "r") as file:
            users_questions = json.loads(file.read())
            if user in users_questions:
                return users_questions[user]
    return None


def set_user_questions(user, questions):
    users_questions = {}
    if os.path.exists(questions_file):
        with open(questions_file, "r") as file:
            users_questions = json.load(file)
    users_questions[user] = questions
    with open(questions_file, "w") as file:
        json.dump(users_questions, file)


def append_user_questions(user, questions):
    users_questions = {}
    if os.path.exists(questions_file):
        with open(questions_file, "r") as file:
            users_questions = json.load(file)
    if user in users_questions:
        existing_questions = users_questions[user]
        existing_questions.extend(questions)
        # Shuffle questions
        random.shuffle(existing_questions)
        users_questions[user] = existing_questions
    else:
        users_questions[user] = questions
    with open(questions_file, "w") as file:
        json.dump(users_questions, file)


def update_user_questions(user, id, correct, lastAnswer, correctAnswer):
    questions = get_user_questions(user)
    for question in questions:
        if question["id"] == id and correct and question["attempts"] < 3:
            question["attempts"] = question["attempts"] + 1
            question["correct"] = True
        elif question["id"] == id and not correct and question["attempts"] < 3:
            question["attempts"] = question["attempts"] + 1

        if question["id"] == id and (correct or question["attempts"] == 3):
            question["correct-answer"] = correctAnswer

        if question["id"] == id:
            question["last-answer"] = lastAnswer

    set_user_questions(user, questions)


def countMarks(questions):
    count = 0
    for question in questions:
        if question["correct"]:
            count += 3 - question["attempts"] + 1
    return count


def start_server():
    marked_event = threading.Event()

    # Start the TCP handler thread
    tcp_handler = TCPHandler()
    tcp_handler.start()

    # Start the HTTP server
    http_server = ThreadedHTTPHandler(("localhost", HTTP_PORT), HTTPHandler)
    print(f"Serving at port {HTTP_PORT}")
    http_server.serve_forever()


if __name__ == "__main__":
    start_server()
