from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
import cv2
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import subprocess
import os
import uuid

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this with your desired origins
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/upload-audio")
async def upload_audio(audio: UploadFile = File(None)):
    if audio:
        unique_id = str(uuid.uuid4())
        audio_file_name = f"static/audio_{unique_id}.mp3"
        with open(audio_file_name, "wb") as f:
            f.write(await audio.read())
        return JSONResponse({"message": "Audio uploaded successfully", "unique_id": unique_id})
    else:
        return JSONResponse({"message": "No audio uploaded"})

@app.post("/upload")
async def upload_file(files: List[UploadFile] = File(...), videoNumber: int = Form(...)):
    unique_id = str(uuid.uuid4())
    width = 426
    height = 720
    video_files = []
    for file in files:
        temp_file_name = f"static/temp_{unique_id}_{file.filename}"
        with open(temp_file_name, "wb") as f:
            f.write(await file.read())

        resized_file_name = f"static/resized_{unique_id}_{file.filename}"
        print("File name: ", file.filename)
        subprocess.run([
            "ffmpeg", "-i", temp_file_name, "-vf",
            f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}",
            resized_file_name
        ])
        video_files.append(resized_file_name)

    # concatenate videos into one
    list_file = f"static/list_{unique_id}.txt"
    with open(list_file, "w") as f:
        for video_file in video_files:
            f.write(f"file '{os.path.join(os.getcwd(), video_file)}'\n")

    # concatenate videos into one
    final_clip_name = f"static/video_{unique_id}_{videoNumber}.mp4"
    subprocess.run(["ffmpeg", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", final_clip_name])
    os.remove(list_file)  # remove the list file
    # Generate thumbnail image for the uploaded video
    video_capture = cv2.VideoCapture(final_clip_name)
    success, frame = video_capture.read()
    if success:
        thumbnail_path = f"static/thumbnail_{unique_id}_{videoNumber}.jpg"
        cv2.imwrite(thumbnail_path, frame)
    else:
        thumbnail_path = None

    return JSONResponse({"message": "Videos uploaded successfully", "imagePath": thumbnail_path, "unique_id": unique_id})

@app.get("/combine/{unique_ids}/{audio_id}")
async def combine_videos(unique_ids: str, audio_id: str = None):

    for file in os.listdir("static"):
        if file.startswith("test_"):
            os.remove(os.path.join("static", file))

    unique_ids = unique_ids.split(",")
    videos = [f"static/video_{unique_id}_{i+1}.mp4" for i, unique_id in enumerate(unique_ids)]
    
    width = 426
    height = 720
    unique_id = str(uuid.uuid4())
    video_filters = []
    ffmpeg_command = ["ffmpeg"]

    for i in range(3):  # for 3 video sections
        if i < len(videos):  # if video exists for this section
            video = videos[i]
            ffmpeg_command.extend(["-i", video])
            video_filters.append(f"[{i}:v]scale={width}:{height},pad=426:720:(426-iw)/2:(720-ih)/2:black[v{i}]")  # pad video to required size
            video_filters.append(f"[{i}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a{i}]")
        else:  # if no video exists for this section
            video_filters.append(f"color=black:s=426x720:d=30[v{i}]")  # generate blank video
            video_filters.append(f"aevalsrc=0:d=30[a{i}]")  # generate silent audio

    if audio_id != "0":  # if audio_id is provided, merge the audio with the video
        ffmpeg_command.extend(["-i", f"static/audio_{audio_id}.mp3"])
        video_filters.append(f"[{len(videos)}:a]aformat=sample_fmts=fltp:sample_rates=22100:channel_layouts=stereo[a{len(videos)}]")
        video_filters.append(f'{"[" + "][".join([f"a{i}" for i in range(len(videos) + 1)])}]amix=inputs={len(videos) + 1}[a]')
    else:
        video_filters.append(f'{"[" + "][".join([f"a{i}" for i in range(3)])}]amix=inputs={3}[a]')

    video_filters.append(f'{"[" + "][".join([f"v{i}" for i in range(3)])}]hstack=inputs={3}[v]')

    ffmpeg_command.extend(["-filter_complex", '; '.join(video_filters), "-map", "[v]", "-map", "[a]", "-b:v", "1000k", "-preset", "ultrafast", "-t", "30", "-r", "24", f"static/test_{unique_id}.mp4"])
    subprocess.run(ffmpeg_command)

    # remove all the temporary files
    for video in videos:
        os.remove(video)
    
    for file in os.listdir("static"):
        if file.startswith("video_") or file.startswith("resized_") or file.startswith("temp_") or file.startswith("thumbnail_") or file.startswith("audio_"):
            os.remove(os.path.join("static", file))
    
    return FileResponse(f"static/test_{unique_id}.mp4", media_type="video/mp4")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
