import cv2
import os

# 输入、输出文件夹
input_folder = r"D:\下载\视频"
output_folder = r"D:\下载\输出"
os.makedirs(output_folder, exist_ok=True)

target_width = 1080
target_height = 1920

for filename in os.listdir(input_folder):
    if not filename.lower().endswith(('.mp4', '.mov', '.avi')):
        continue
    in_path = os.path.join(input_folder, filename)
    out_path = os.path.join(output_folder, filename)
    cap = cv2.VideoCapture(in_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(out_path, fourcc, fps, (target_width, target_height))

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        h, w = frame.shape[:2]
        # 原视频高宽比
        src_ratio = w / h
        target_ratio = target_width / target_height

        # 1. 决定裁剪区域
        if src_ratio > target_ratio:
            # 横向裁剪
            new_w = int(h * target_ratio)
            start_x = (w - new_w) // 2
            crop = frame[:, start_x:start_x+new_w]
        else:
            # 纵向裁剪
            new_h = int(w / target_ratio)
            start_y = (h - new_h) // 2
            crop = frame[start_y:start_y+new_h, :]

        # 2. 缩放到目标分辨率
        resized_frame = cv2.resize(crop, (target_width, target_height))
        out.write(resized_frame)

    cap.release()
    out.release()
print('处理完成！')