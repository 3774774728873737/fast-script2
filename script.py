from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
import cv2
from fastapi.middleware.cors import CORSMiddleware
from moviepy.editor import VideoFileClip, clips_array
from moviepy.editor import *
import os
import base64
import uvicorn
from typing import List
import subprocess
import time
import random
import string
global audioname


audioname = None


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    # Save the uploaded audio file
    i = 1
    while True:
        if os.path.exists(f"audio{i}.mp3"):
            i += 1
        else:
            break

    with open(f"audio{i}.mp3", "wb") as f:
        f.write(await file.read())

    global audioname
    audioname = f"audio{i}.mp3"
    time.sleep(4)

    return {"message": "Videos uploaded successfully"}


@app.post("/upload-videos")
async def upload_videos(files: List[UploadFile] = File(...)):
    print(files)
    i = 1
    for file in files:
        with open(f"video{i}.mp4", "wb") as f:
            f.write(await file.read())
        i+=1

    return {"message": "Videos uploaded successfully"}


@app.post("/upload")
async def upload_file(file: UploadFile = File(...), videoNumber: int = Form(...)):
    with open(f"video{videoNumber}.mp4", "wb") as f:
        f.write(await file.read())

    # Generate thumbnail image for the uploaded video
    video_capture = cv2.VideoCapture(f"video{videoNumber}.mp4")
    success, frame = video_capture.read()
    if success:
        # Save the thumbnail as a temporary file
        thumbnail_path = f"thumbnail{videoNumber}23.jpg"
        cv2.imwrite(thumbnail_path, frame)

        # Read the thumbnail image and convert it to base64
        with open(thumbnail_path, "rb") as thumbnail_file:
            thumbnail_data = thumbnail_file.read()
            thumbnail_base64 = base64.b64encode(thumbnail_data).decode("utf-8")

    else:
        thumbnail_base64 = None

    return JSONResponse({"message": "Video uploaded successfully", "imagePath": thumbnail_base64})



def generate_unique_filename():
    timestamp = str(int(time.time()))
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    unique_filename = timestamp + '_' + random_string
    return unique_filename



@app.post("/combine")
async def combine_videos(files: List[UploadFile] = File(...), audio: UploadFile = File(None)):



    print(len(files))
    file1 = generate_unique_filename()
    audionames = generate_unique_filename()
    outputname = generate_unique_filename()


    i = 1
    for i, file in enumerate(files, start=1):
        print(file1)
        with open(f"{file1}{i}.mp4", "wb") as f:
            f.write(await file.read())
        i+=1
    count = 0

    if audio is not None:
        # Save the uploaded audio file
        with open(f"{audionames}.mp3", "wb") as f:
            f.write(await audio.read())
            audios = f"-i {audionames}.mp3"
            count = count + 1

    else:
        audios = ""
        print("no audio")



    global audioname

    length = 6


    audio_merge = ";"
    command = ['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=codec_type', '-of', 'default=noprint_wrappers=1:nokey=1', "video1.mp4"]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip() == 'audio':
        audio_merge = audio_merge + "[0:a]"
        count = count + 1
    else:
        print("no audio")
        pass

    command = ['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=codec_type', '-of', 'default=noprint_wrappers=1:nokey=1', "video2.mp4"]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip() == 'audio':
        audio_merge = audio_merge + "[1:a]"
        count = count + 1
    else:
        pass

    command = ['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=codec_type', '-of', 'default=noprint_wrappers=1:nokey=1', "video3.mp4"]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip() == 'audio':
        audio_merge = audio_merge + "[2:a]"
        count = count + 1
    else:
        pass


    if count > 0:
        audio_merge = audio_merge + f"amerge=inputs={count}[a]"
        maping = "-map \"[a]\""

    else:
        audio_merge = ""
        maping = ""
        
    print(audio_merge)

    # run a single command
    command = f"""ffmpeg -y -i {file1}1.mp4 -i {file1}2.mp4 -i {file1}3.mp4 {audios} -vsync 2 -filter_complex "[0:v]scale=426:720[v0];[1:v]scale=426:720[v1];[2:v]scale=426:720[v2];[v0][v1][v2]hstack=3,scale=1280:720[v]{audio_merge} " -map "[v]" {maping} -c:v libx264 -crf 23 -preset veryfast -c:a libmp3lame -b:a 128k -t {length} {outputname}.mp4"""
    subprocess.run(command, shell=True)

    return FileResponse(f"{outputname}.mp4", media_type="video/mp4")
