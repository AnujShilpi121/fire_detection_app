# fireapp/views.py
import os
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import random
from django.conf import settings
import cv2
import numpy as np
from django.http import StreamingHttpResponse
from django.views.decorators import gzip
from django.shortcuts import render, redirect
# from keras._tf_keras.keras.models import load_model
from tensorflow.keras.models import load_model
from datetime import datetime
import MySQLdb
import threading
import playsound
from django.views.decorators.csrf import csrf_exempt

model = load_model("forest_fire_model_20e.h5")
labels = ["No Fire", "Fire"]

fire_detected = False
fire_start_time = None
fire_start_datetime = None
streaming = True  # Global flag to control streaming

def db_connect():
    return MySQLdb.connect(
        host="localhost",
        user="root",
        password="Anuj@123s",
        database="fire_detection_db"
    )

def play_alarm():
    playsound.playsound("fireapp/static/fireapp/alarm/fire_alarm.mp3")

class VideoCamera:
    def __init__(self):
        self.video = cv2.VideoCapture(0)

    def __del__(self):
        self.video.release()

    def get_frame(self):
        global fire_detected, fire_start_time, fire_start_datetime

        success, frame = self.video.read()
        if not success:
            return None

        img = cv2.resize(frame, (150, 150))
        img_array = np.expand_dims(img, axis=0) / 255.0

        prediction = model.predict(img_array)[0][0]
        label = labels[1] if prediction > 0.5 else labels[0]
        confidence = prediction if prediction > 0.5 else 1 - prediction
        color = (0, 0, 255) if label == "Fire" else (0, 255, 0)

        cv2.putText(frame, f"{label} ({confidence * 100:.2f}%)", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        cv2.rectangle(frame, (5, 5), (frame.shape[1]-5, frame.shape[0]-5), color, 2)

        current_time = datetime.now().timestamp()
        if label == "Fire":
            if not fire_detected:
                fire_detected = True
                fire_start_time = current_time
                fire_start_datetime = datetime.now()
                threading.Thread(target=play_alarm, daemon=True).start()
        else:
            if fire_detected:
                fire_detected = False
                duration = round(current_time - fire_start_time, 2)
                fire_date = fire_start_datetime.strftime("%Y-%m-%d")
                fire_clock_time = fire_start_datetime.strftime("%H:%M:%S")

                conn = db_connect()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO fireevents (date, time, duration) VALUES (%s, %s, %s)",
                               (fire_date, fire_clock_time, duration))
                conn.commit()
                cursor.close()
                conn.close()

        ret, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes()

def gen(camera):
    global streaming
    streaming = True
    while streaming:
        frame = camera.get_frame()
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@gzip.gzip_page
def start_detection(request):
    return render(request, 'fireapp/stream.html')  # show the video feed page with Stop button

def video_feed(request):
    return StreamingHttpResponse(gen(VideoCamera()), content_type="multipart/x-mixed-replace; boundary=frame")

@csrf_exempt
def stop_detection(request):
    global streaming
    streaming = False
    return redirect('home')

def home(request):
    image_dir = os.path.join(settings.BASE_DIR, 'fireapp', 'static', 'fireapp', 'images')
    image_files = [f"fireapp/images/{img}" for img in os.listdir(image_dir) if
                   img.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]

    selected_image = random.choice(image_files) if image_files else None
    return render(request, 'fireapp/index.html', {'bg_image': selected_image})

def show_logs(request):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM FireEvents")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    image_dir = os.path.join(settings.BASE_DIR, 'fireapp', 'static', 'fireapp', 'images')
    image_files = [f"fireapp/images/{img}" for img in os.listdir(image_dir) if
                   img.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    selected_image = random.choice(image_files) if image_files else None

    return render(request, 'fireapp/logs.html', {'logs': rows, 'bg_image': selected_image})

def delete_log(request, id):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM fireevents WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('show_logs')

def delete_all_logs(request):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM fireevents")
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('show_logs')
