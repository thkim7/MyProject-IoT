from flask import Flask, render_template, request, Response, url_for, redirect   # flask 모듈과 관련함수 불러옴
import RPi.GPIO as GPIO     # 라즈베리파이 GPIO 관련 모듈을 불러옴
import time                 # 시간 관련 모듈을 불러옴
from PIL import ImageFont, ImageDraw, Image
import datetime
import cv2
import numpy as np
import smtplib
from email.mime.text import MIMEText

ip = "192.168.137.129"
GPIO.setmode(GPIO.BCM)      # GPIO 핀들의 번호를 지정하는 규칙 설정
GPIO.setwarnings(False)
servo_pin = 12                   # 서보핀은 라즈베리파이 GPIO 12번핀으로
GPIO.setup(servo_pin, GPIO.OUT)  # 서보핀을 출력으로 설정 
GPIO.setup(23, GPIO.OUT)
GPIO.setup(24, GPIO.OUT)
servo = GPIO.PWM(servo_pin, 50)  # 서보핀을 PWM 모드 50Hz로 사용
servo.start(0)  # 서보모터의 초기값을 0으로 설정
servo_min_duty = 3               # 최소 듀티비를 2으로
servo_max_duty = 12              # 최대 듀티비를 13로
smtp = smtplib.SMTP('smtp.gmail.com', 587)
smtp.starttls()
smtp.login('xogusrla7@gmail.com', 'lqwehskdopevljzt')
GPIO.output(23, False)
GPIO.output(24, False)

app = Flask(__name__)
global is_capture
capture = cv2.VideoCapture(-1)
capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
font = ImageFont.truetype('fonts/SCDream6.otf', 20)
global push_btn, current_deg
push_btn = False
current_deg = 90                 # 현재 각도를 90도로
is_capture = False
global is_detected, cnt_record, max_cnt_record
is_detected = False
push_btn = False
cnt_record = 0
max_cnt_record = 30
face_cascade = cv2.CascadeClassifier('haarcascade/haarcascade_frontalface_default.xml')

def flask_sleep(set_time):
    past_time = time.time()
    while True:                             # 이부분은 sleep(0.5)와 같음(움직이는 시간동안 대기)
        current_time = time.time()
        if current_time - past_time > set_time:
            break
       
def set_servo_degree(degree):    # 각도를 입력하면 듀티비를 알아서 설정해주고 서보모터를 움직이는 함수
    # #8.5편에 나온 방법대로 서보모터가 떨리지 않게 함
    # 각도는 최소0, 최대 180으로 설정
    GPIO.setup(servo_pin, GPIO.OUT)         # 모터를 움직여야 하니 서보핀을 출력으로 설정
    if degree > 180:                        # 입력받은 각도를 0~180도 사이로 재조정
        degree = 180
    elif degree < 0:
        degree = 0
    duty = servo_min_duty+(degree*(servo_max_duty-servo_min_duty)/180.0)    # 각도를 듀티비로 환산
    # 환산한 듀티비를 서보모터에 전달
    servo.ChangeDutyCycle(duty)             # 해당 각도대로 서보모터를 움직임
    flask_sleep(0.5)
    GPIO.setup(servo_pin, GPIO.IN)          # 0.5초간 기다린 후 서보핀을 입력으로 설정(서보모터가 움직이지 않음)
    return degree                           # 입력받은 각도를 출력
            
def gen_frames():  
    global is_capture, is_detected, push_btn, cnt_record, max_cnt_record
    while True:
        now = datetime.datetime.now()
        nowDatetime = now.strftime('%Y-%m-%d %H:%M:%S')
        nowDatetime_path = now.strftime('%Y-%m-%d %H:%M:%S')
        ref, frame = capture.read()  # 현재 영상을 받아옴
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor = 1.5, minNeighbors = 3, minSize = (20, 20))
        is_mail_sent = False
        
        if len(faces):
                is_detected = True
                cnt_record = max_cnt_record
                if not is_mail_sent:
                    msg = MIMEText('intruder alert!!')
                    msg['Subject'] = 'intruder alert!!'
                    msg['To'] = 'xogusrla0097@naver.com'
                    smtp.sendmail('xogusrla7@gmail.com', 'xogusrla0097@naver.com', msg.as_string())
                    is_mail_sent = True
                    GPIO.output(24, True)
                    GPIO.output(23, False)
        else:
            cnt_record -= 1
            if cnt_record == 0:
                is_detected = False
                is_mail_sent = False
                GPIO.output(24, False)
                GPIO.output(23, True)
                
        if not ref:
            break
        else:
            if not is_detected and push_btn:
                frame = np.zeros([480, 640, 3], dtype="uint8")
                frame = Image.fromarray(frame)    
                draw = ImageDraw.Draw(frame)    
            # xy는 텍스트 시작위치, text는 출력할 문자열, font는 글꼴, fill은 글자색(파랑,초록,빨강)   
                draw.text(xy=(10, 15),  text="IoT응용 프로젝트 "+nowDatetime, font=font, fill=(255, 255, 255))
                frame = np.array(frame)
            elif is_detected or not push_btn:
                frame = Image.fromarray(frame)
                draw = ImageDraw.Draw(frame)
                draw.text(xy=(10, 15), text="IoT응용 프로젝트 "+nowDatetime, font=font, fill=(255, 255, 255))
                frame = np.array(frame)
            ref, buffer = cv2.imencode('.jpg', frame) 
            frame1 = frame           
            frame = buffer.tobytes()
            if is_capture:
                is_capture = False
                cv2.imwrite("capture " + nowDatetime_path + ".png", frame1)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')  # 그림파일들을 쌓아두고 호출을 기다림


app = Flask(__name__)                                               # Flask라는 이름의 객체 생성
@app.route('/')
def index():
    global push_btn                                                 # push_btn을 전역변수로 불러옴
    return render_template('index4#8.html', deg=current_deg, push_btn = push_btn)        # index4#8.html의 형식대로 웹페이지를 보여줌

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/servo_control')        # 서보모터를 제어하기 위한 주소
def servo_control():                # 서보모터를 제어하기 위한 뷰함수
    deg = request.args.get('deg')   # html파일에서 각도를 입력받음
    deg = int(deg)                  # 각도를 정수형으로 바꿔주고 적절한 범위로바꿔줌
    if deg < 0: deg = 0
    elif deg > 180: deg = 180
    deg = set_servo_degree(deg)     # 서보모터 각도를 바꿔줌
    # index4#8.html로 돌아가는데, 이때, deg 값을 넘겨줌(이 넘겨준 값은 html에서 사용할 수 있음)
    return render_template('index4#8.html', deg=deg)

@app.route('/push_capture')
def push_capture():
    global is_capture
    is_capture = True
    return redirect(url_for('index'))

@app.route('/push_switch')
def push_switch():
    global push_btn
    push_btn = not push_btn
    return redirect(url_for('index'))

if __name__ == "__main__":  # 웹사이트를 호스팅하여 접속자에게 보여주기 위한 부분
    app.run(host="192.168.137.129", port = "8084")
    # host는 현재 라즈베리파이의 내부 IP, port는 임의로 설정
    # 해당 내부 IP와 port를 포트포워딩 해두면 외부에서도 접속가능