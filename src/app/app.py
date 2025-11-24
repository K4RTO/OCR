import os
import re
import sys
import threading
import time
import zipfile
import io
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import gradio as gr
import pandas as pd
from datetime import datetime
import shutil
import subprocess
from apscheduler.schedulers.background import BackgroundScheduler

# --- Path Setup ---
# 始终使用相对于脚本文件的路径，无论是开发环境还是打包环境
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后的环境
    ROOT_DIR = Path(sys.executable).parent
    SRC_DIR = Path(sys._MEIPASS) / 'src'
    APP_DIR = SRC_DIR / 'app'
else:
    # 开发环境：app.py 在 src/app/ 目录下
    APP_DIR = Path(__file__).resolve().parent
    SRC_DIR = APP_DIR.parent
    ROOT_DIR = SRC_DIR.parent

sys.path.append(str(APP_DIR))

try:
    from mineru.utils.pdf_image_tools import load_images_from_pdf
    from mineru.utils.enum_class import ImageType
except ImportError as e:
    print(f"Error: Failed to import MinerU modules. Current sys.path: {sys.path}")
    print(f"Details: {e}")
    sys.exit(1)

# --- Path Configurations ---
CROP_BOX = (0, 300, 800, 500)
SHIPPING_ID_PATTERN = re.compile(r"发货单(?:号)?\s*[:：]\s*([A-Za-z0-9]+)")
INPUT_DIR = ROOT_DIR / "input"
OUTPUT_DIR = ROOT_DIR / "output"
DOWNLOADS_DIR = ROOT_DIR / "downloads"
DEBUG_DIR = ROOT_DIR / "debug"
OCR_IMAGES_DIR = DEBUG_DIR / "ocr_annotated"
SHUTDOWN_SENTINEL = ROOT_DIR / ".mineru_shutdown"
OUTPUT_FILE_COLUMNS = ["选择", "原始文件名", "重命名后文件名", "大小(KB)", "修改时间", "完整路径"]

# Global OCR model to load only once
OCR_MODEL = None

# 全局字典：存储文件名到文件路径的映射
FILE_PATH_MAP = {}


def clean_hidden_files(directory):
    """删除目录中的 .DS_Store 等隐藏垃圾文件"""
    dir_path = Path(directory)
    if not dir_path.exists():
        return

    for ds_store in dir_path.rglob(".DS_Store"):
        try:
            ds_store.unlink()
        except Exception as e:
            print(f"删除隐藏文件失败: {ds_store} ({e})")


def clean_empty_subdirs(directory):
    """递归删除目录下的空文件夹，保留根目录"""
    dir_path = Path(directory)
    if not dir_path.exists():
        return

    for child in dir_path.iterdir():
        if child.is_dir():
            clean_empty_subdirs(child)
            try:
                if not any(child.iterdir()):
                    child.rmdir()
            except Exception as e:
                print(f"删除空文件夹失败: {child} ({e})")


def normalize_file_manager_df(df):
    """确保文件管理器表格数据为DataFrame"""
    if df is None:
        return None

    if isinstance(df, pd.DataFrame):
        return df

    try:
        if isinstance(df, dict):
            return pd.DataFrame(df)
        return pd.DataFrame(df, columns=OUTPUT_FILE_COLUMNS)
    except Exception as e:
        print(f"转换文件表格失败: {e}")
        return None

def coerce_selection_column(df):
    """将“选择”列强制转换为布尔类型，兼容全选勾选产生的字符串 true 状态"""
    if df is None or "选择" not in df.columns:
        return df

    def to_bool(val):
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return val != 0
        if isinstance(val, str):
            return val.strip().lower() in {"true", "1", "yes", "y", "on", "checked"}
        return False

    df = df.copy()
    df["选择"] = df["选择"].apply(to_bool)
    return df


def get_ocr_model_lazy():
    """Initializes and returns the OCR model, loading it only once."""
    global OCR_MODEL
    if OCR_MODEL is None:
        print("=" * 60)
        print("正在加载 OCR 模型...")
        print("=" * 60)
        try:
            from mineru.model.ocr.pytorch_paddle import PytorchPaddleOCR

            # 使用相对路径定位模型文件
            local_models_root = APP_DIR / "local_models"

            det_model = "models/OCR/paddleocr_torch/ch_PP-OCRv5_det_infer.pth"
            rec_model = "models/OCR/paddleocr_torch/ch_PP-OCRv4_rec_server_doc_infer.pth"
            dict_path = APP_DIR / "mineru" / "model" / "utils" / "pytorchocr" / "utils" / "resources" / "dict" / "ppocrv4_doc_dict.txt"
            det_model_path = local_models_root / det_model
            rec_model_path = local_models_root / rec_model

            # 调试输出，帮助排查路径问题
            print(f"[路径] APP_DIR: {APP_DIR}")
            print(f"[路径] 检测模型: {det_model_path}")
            print(f"[路径] 识别模型: {rec_model_path}")
            print(f"[路径] 字典文件: {dict_path}")

            # 检查文件存在性
            det_exists = det_model_path.exists()
            rec_exists = rec_model_path.exists()
            dict_exists = dict_path.exists()

            print(f"[验证] 检测模型: {'✓' if det_exists else '✗'}")
            print(f"[验证] 识别模型: {'✓' if rec_exists else '✗'}")
            print(f"[验证] 字典文件: {'✓' if dict_exists else '✗'}")

            if not all([det_exists, rec_exists, dict_exists]):
                missing = []
                if not det_exists:
                    missing.append(f"  - 检测模型: {det_model_path}")
                if not rec_exists:
                    missing.append(f"  - 识别模型: {rec_model_path}")
                if not dict_exists:
                    missing.append(f"  - 字典文件: {dict_path}")
                error_msg = "找不到以下模型文件:\n" + "\n".join(missing)
                print(f"\n✗ 错误: {error_msg}")
                raise FileNotFoundError(error_msg)

            print("\n正在初始化 OCR 引擎（需要 5-10 秒）...")
            OCR_MODEL = PytorchPaddleOCR(
                lang='ch',
                det_model_path=str(det_model_path),
                rec_model_path=str(rec_model_path),
                rec_char_dict_path=str(dict_path)
            )
            print("✓ OCR 模型加载完成！")
            print("=" * 60)
        except Exception as e:
            print(f"\n✗ 错误: 无法从本地文件初始化OCR模型。")
            print(f"详细信息: {e}")

            # 检查是否是 Windows VC++ 缺失的问题
            error_msg = str(e)
            if "WinError 126" in error_msg or "c10.dll" in error_msg or "torch" in error_msg:
                print("\n" + "=" * 60)
                print("⚠ 检测到 Windows DLL 加载错误")
                print("=" * 60)
                print("\n这通常是因为缺少 Microsoft Visual C++ Redistributable")
                print("\n解决方案:")
                print("  1. 下载并安装 VC++ Redistributable:")
                print("     https://aka.ms/vs/17/release/vc_redist.x64.exe")
                print("\n  2. 或者重新运行 setup.bat，选择自动安装")
                print("\n  3. 安装完成后，重启此应用")
                print("=" * 60)
            else:
                import traceback
                traceback.print_exc()
                print("=" * 60)

            OCR_MODEL = None
    return OCR_MODEL

def draw_ocr_boxes(image, ocr_results, highlight_text=None):
    """
    在图片上绘制 OCR 识别框，并用红色高亮特定文本
    """
    draw_image = image.copy()
    draw = ImageDraw.Draw(draw_image)

    # Linux字体加载
    font = None
    font_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]

    # 尝试加载字体
    for font_path in font_candidates:
        try:
            font = ImageFont.truetype(font_path, 20)
            break
        except:
            continue

    # 如果所有字体都加载失败，使用默认字体
    if font is None:
        font = ImageFont.load_default()

    if ocr_results and ocr_results[0]:
        for box_info, rec_data in ocr_results[0]:
            box = box_info
            text, confidence = rec_data

            # 判断是否是需要高亮的文本
            is_highlight = highlight_text and highlight_text in text
            color = (255, 0, 0) if is_highlight else (0, 255, 0)  # 红色高亮，绿色普通
            width = 3 if is_highlight else 2

            # 绘制边框
            points = [(int(p[0]), int(p[1])) for p in box]
            draw.polygon(points, outline=color, width=width)

            # 绘制文本
            draw.text((int(box[0][0]), int(box[0][1]) - 25), text, fill=color, font=font)

    return draw_image

def extract_shipping_number_from_pdf(pdf_path: str, ocr_model, crop_box: tuple):
    """
    从PDF提取发货单号，并返回带标注的图片
    返回: (shipping_id, status_msg, annotated_image_path)
    """
    if ocr_model is None:
        return "Error", "OCR模型未加载", None

    try:
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()

        images_tuple = load_images_from_pdf(pdf_bytes, dpi=200, start_page_id=0, end_page_id=0, image_type=ImageType.PIL)
        images_list = images_tuple[0]

        if not images_list:
            return "Not Found", "无法从PDF中读取图像", None

        first_page_image = images_list[0]['img_pil']
        cropped_image = first_page_image.crop(crop_box)

        # OCR识别
        cropped_np_image = np.array(cropped_image)
        ocr_raw_results = ocr_model.ocr(cropped_np_image)

        full_text = ""
        if ocr_raw_results and ocr_raw_results[0]:
            for _, rec_data in ocr_raw_results[0]:
                text, _ = rec_data
                full_text += text + " "

        full_text = full_text.strip()

        # 查找发货单号
        match = SHIPPING_ID_PATTERN.search(full_text)

        # Fallback to full page OCR if not found in crop box
        use_full_page = False
        if not match:
            print(f"在 CROP_BOX 区域未找到单号，正在尝试全局页面识别...")
            full_page_np_image = np.array(first_page_image)
            ocr_full_page_results = ocr_model.ocr(full_page_np_image)
            use_full_page = True

            full_page_text = ""
            if ocr_full_page_results and ocr_full_page_results[0]:
                for _, rec_data in ocr_full_page_results[0]:
                    text, _ = rec_data
                    full_page_text += text + " "

            full_page_text = full_page_text.strip()
            match = SHIPPING_ID_PATTERN.search(full_page_text)
            ocr_raw_results = ocr_full_page_results

        shipping_id = "Not Found"
        if match:
            shipping_id = match.group(1)

        # 绘制标注图片
        OCR_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

        # 选择合适的图片进行标注
        if use_full_page:
            annotated_image = draw_ocr_boxes(first_page_image, ocr_raw_results, shipping_id if shipping_id != "Not Found" else None)
        else:
            annotated_image = draw_ocr_boxes(cropped_image, ocr_raw_results, shipping_id if shipping_id != "Not Found" else None)

        # 保存标注图片
        image_filename = f"{Path(pdf_path).stem}_ocr.png"
        image_path = OCR_IMAGES_DIR / image_filename
        annotated_image.save(image_path)

        # 创建缩略图
        thumbnail = annotated_image.copy()
        thumbnail.thumbnail((300, 300))
        thumbnail_path = OCR_IMAGES_DIR / f"{Path(pdf_path).stem}_thumb.png"
        thumbnail.save(thumbnail_path)

        status = f"成功: {shipping_id}" if shipping_id != "Not Found" else f"未找到单号。OCR内容: '{full_text[:50]}...'"

        return shipping_id, status, str(thumbnail_path)

    except Exception as e:
        return "Error", f"处理文件时发生意外错误: {e}", None

def process_uploads_and_extract(files):
    """处理上传的文件并提取单号"""
    global FILE_PATH_MAP
    clean_hidden_files(INPUT_DIR)
    clean_hidden_files(OUTPUT_DIR)

    if not files:
        return pd.DataFrame(columns=["原始文件名", "提取的单号", "提取图像"]), "", "请先上传文件。"

    timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    input_batch_dir = INPUT_DIR / timestamp_str
    input_batch_dir.mkdir(parents=True, exist_ok=True)

    processed_files = []
    FILE_PATH_MAP.clear()  # 清空之前的映射

    for file_obj in files:
        temp_path = file_obj.name
        original_filename = Path(temp_path).name
        dest_path = input_batch_dir / original_filename
        shutil.copy(temp_path, dest_path)
        processed_files.append(str(dest_path))
        FILE_PATH_MAP[original_filename] = str(dest_path)  # 存储映射

    # 获取 OCR 模型（已在启动时预加载）
    ocr_model = get_ocr_model_lazy()
    if ocr_model is None:
        return pd.DataFrame(columns=["原始文件名", "提取的单号", "提取图像"]), "", "错误：OCR 模型未加载，请重启应用。"

    results = []
    for pdf_path in processed_files:
        print(f"正在处理文件: {Path(pdf_path).name}")
        shipping_id, status, thumbnail_path = extract_shipping_number_from_pdf(pdf_path, ocr_model, CROP_BOX)

        results.append([
            Path(pdf_path).name,
            shipping_id,
            thumbnail_path if thumbnail_path else ""
        ])

    df = pd.DataFrame(results, columns=["原始文件名", "提取的单号", "提取图像"])
    return df, "", f"文件已存入 {input_batch_dir} 并完成提取。"

def view_ocr_image(df, evt: gr.SelectData):
    """查看选中行的OCR标注图片"""
    if df is None or df.empty:
        return None

    row_index = evt.index[0]
    thumbnail_path = df.iloc[row_index]["提取图像"]

    # 从缩略图路径获取完整图像路径
    full_image_path = thumbnail_path.replace("_thumb.png", "_ocr.png") if thumbnail_path else None

    if full_image_path and Path(full_image_path).exists():
        return full_image_path
    return None

def rename_files_and_organize(df):
    """重命名文件并整理到输出目录"""
    global FILE_PATH_MAP

    if df is None or df.empty:
        return "没有文件需要处理。"

    timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_batch_dir = OUTPUT_DIR / timestamp_str
    output_batch_dir.mkdir(parents=True, exist_ok=True)

    rename_log = []
    for index, row in df.iterrows():
        original_filename = row["原始文件名"]
        new_shipping_id = row["提取的单号"]

        # 从全局映射获取文件路径
        source_path_str = FILE_PATH_MAP.get(original_filename)
        if not source_path_str:
            log_msg = f"错误: 找不到文件 '{original_filename}' 的路径"
            print(log_msg)
            rename_log.append(log_msg)
            continue

        source_path = Path(source_path_str)
        original_filename = source_path.name

        if not source_path.exists():
            log_msg = f"错误: 文件 '{original_filename}' 不存在，已跳过。"
            print(log_msg)
            rename_log.append(log_msg)
            continue

        file_output_dir = output_batch_dir / source_path.stem
        file_output_dir.mkdir(exist_ok=True)

        dest_original_path = file_output_dir / original_filename
        shutil.copy(source_path, dest_original_path)

        if new_shipping_id in ["Not Found", "Error", "", None]:
            log_msg = f"文件 '{original_filename}' 的单号无效, 仅复制源文件。"
            print(log_msg)
            rename_log.append(log_msg)
            continue

        new_filename = f"{new_shipping_id}.pdf"
        new_path = file_output_dir / new_filename

        try:
            dest_original_path.rename(new_path)
            log_msg = f"成功: '{original_filename}' -> '{new_filename}'"
            print(log_msg)
            rename_log.append(log_msg)
        except Exception as e:
            log_msg = f"错误: 重命名 '{original_filename}' 时发生错误: {e}"
            print(log_msg)
            rename_log.append(log_msg)

    return f"处理完成，结果已存入 {output_batch_dir}。\n\n" + "\n".join(rename_log)


def open_directory(directory):
    """在Linux系统文件管理器中打开指定目录"""
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.Popen(["xdg-open", str(dir_path)])
        return f"已打开 {dir_path}"
    except Exception as e:
        return f"打开目录失败 (仅服务器端可用): {e}"

def list_output_files():
    """列出output目录的文件,显示原始名和重命名后的名字"""
    dir_path = OUTPUT_DIR
    clean_hidden_files(dir_path)
    if not dir_path.exists():
        return pd.DataFrame(columns=OUTPUT_FILE_COLUMNS)

    files_info = []
    # 遍历output目录下的所有批次文件夹
    for batch_dir in sorted(dir_path.iterdir()):
        if not batch_dir.is_dir():
            continue

        # 每个批次文件夹下有子文件夹,文件夹名是原始文件名(去掉.pdf后缀)
        for original_dir in sorted(batch_dir.iterdir()):
            if not original_dir.is_dir():
                continue

            original_name = original_dir.name  # 原始文件名(不含后缀)

            # 查找该目录下的PDF文件
            for pdf_file in original_dir.glob("*.pdf"):
                size_kb = pdf_file.stat().st_size / 1024
                mtime = datetime.fromtimestamp(pdf_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                renamed_name = pdf_file.name  # 重命名后的文件名

                files_info.append([
                    False,  # 选择
                    f"{original_name}.pdf",  # 原始文件名
                    renamed_name,  # 重命名后文件名
                    f"{size_kb:.2f}",  # 大小
                    mtime,  # 修改时间
                    str(pdf_file)  # 完整路径(隐藏)
                ])

    df = pd.DataFrame(files_info, columns=OUTPUT_FILE_COLUMNS)
    return coerce_selection_column(df)

def delete_selected_files(df):
    """删除选中的文件"""
    df = normalize_file_manager_df(df)
    df = coerce_selection_column(df)
    if df is None or df.empty:
        return "没有文件"

    # 获取所有选中的文件
    selected_files = df[df["选择"] == True]["完整路径"].tolist()

    if not selected_files:
        return "请先勾选要删除的文件"

    # 执行删除
    deleted = []
    failed = []
    for file_path_str in selected_files:
        file_path = Path(file_path_str)
        try:
            if file_path.exists():
                file_path.unlink()
                deleted.append(file_path.name)
            else:
                failed.append(f"{file_path.name} (不存在)")
        except Exception as e:
            failed.append(f"{file_path.name} ({e})")

    result_msg = f"成功删除 {len(deleted)} 个文件"
    if failed:
        result_msg += f"\n失败: {', '.join(failed)}"

    return result_msg


def download_selected_files_as_zip(df, directory):
    """将用户选中的文件打包为ZIP供下载"""
    df = normalize_file_manager_df(df)
    df = coerce_selection_column(df)

    if df is None or df.empty:
        return None

    # 获取所有选中的文件
    selected_files = df[df["选择"] == True]["完整路径"].tolist()

    if not selected_files:
        return None  # 没有选中文件

    # 创建一个内存中的ZIP文件
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path_str in selected_files:
            file_path = Path(file_path_str)
            if file_path.exists() and file_path.is_file():
                # 使用相对于directory的路径作为压缩包内的路径
                dir_path = Path(directory)
                try:
                    arcname = file_path.relative_to(dir_path)
                except ValueError:
                    # 如果文件不在directory下，使用文件名
                    arcname = file_path.name
                zipf.write(file_path, arcname)

    zip_buffer.seek(0)

    # 保存到downloads目录
    DOWNLOADS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"{timestamp}.zip"
    zip_path = DOWNLOADS_DIR / zip_filename

    with open(zip_path, 'wb') as f:
        f.write(zip_buffer.read())

    return str(zip_path)


def cleanup_cache_files():
    """清理调试与缓存目录"""
    for cache_dir in [DEBUG_DIR, OCR_IMAGES_DIR]:
        if not cache_dir.exists():
            continue
        for item in cache_dir.iterdir():
            try:
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink()
            except Exception as e:
                print(f"清理缓存失败: {item} ({e})")


def cleanup_input_directory():
    """清理input目录中的所有文件 (每5分钟执行)"""
    print(f"[定时任务] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 开始清理 input 目录")
    if INPUT_DIR.exists():
        try:
            for item in INPUT_DIR.iterdir():
                if item.is_file():
                    item.unlink()
                    print(f"  删除文件: {item.name}")
                elif item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                    print(f"  删除目录: {item.name}")
            clean_hidden_files(INPUT_DIR)
            print(f"[定时任务] input 目录清理完成")
        except Exception as e:
            print(f"[定时任务] input 目录清理失败: {e}")


def cleanup_output_directory():
    """清理output目录中的所有文件 (每天0点执行)"""
    print(f"[定时任务] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 开始清理 output 目录")
    if OUTPUT_DIR.exists():
        try:
            for item in OUTPUT_DIR.iterdir():
                if item.is_file():
                    item.unlink()
                    print(f"  删除文件: {item.name}")
                elif item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                    print(f"  删除目录: {item.name}")
            clean_hidden_files(OUTPUT_DIR)
            print(f"[定时任务] output 目录清理完成")
        except Exception as e:
            print(f"[定时任务] output 目录清理失败: {e}")


def cleanup_downloads_directory():
    """清理downloads目录中超过10分钟的文件 (每5分钟执行)"""
    print(f"[定时任务] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 开始清理 downloads 目录")
    if DOWNLOADS_DIR.exists():
        try:
            current_time = datetime.now()
            cleaned_count = 0
            for item in DOWNLOADS_DIR.iterdir():
                if item.is_file():
                    file_age = current_time - datetime.fromtimestamp(item.stat().st_mtime)
                    if file_age.total_seconds() > 600:  # 10分钟 = 600秒
                        item.unlink()
                        cleaned_count += 1
                        print(f"  删除文件: {item.name} (已存在 {file_age.total_seconds():.0f} 秒)")
                elif item.is_dir():
                    # 目录也检查时间
                    dir_age = current_time - datetime.fromtimestamp(item.stat().st_mtime)
                    if dir_age.total_seconds() > 600:
                        shutil.rmtree(item, ignore_errors=True)
                        cleaned_count += 1
                        print(f"  删除目录: {item.name}")
            clean_hidden_files(DOWNLOADS_DIR)
            if cleaned_count > 0:
                print(f"[定时任务] downloads 目录清理完成，删除了 {cleaned_count} 个文件/目录")
            else:
                print(f"[定时任务] downloads 目录无需清理（无超过10分钟的文件）")
        except Exception as e:
            print(f"[定时任务] downloads 目录清理失败: {e}")


def get_next_cleanup_time():
    """获取下次清理时间"""
    now = datetime.now()
    # 计算下次output清理时间(每天0点)
    if now.hour == 0 and now.minute < 5:
        next_cleanup = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        next_cleanup = (now + pd.Timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    return next_cleanup.strftime('%Y-%m-%d %H:%M:%S')


# --- Gradio UI ---
with gr.Blocks(theme=gr.themes.Soft(primary_hue="slate").set(
    body_background_fill="*neutral_950",
    body_background_fill_dark="*neutral_950",
    background_fill_primary="*neutral_900",
    background_fill_primary_dark="*neutral_900",
    background_fill_secondary="*neutral_800",
    background_fill_secondary_dark="*neutral_800",
    border_color_primary="*neutral_700",
    border_color_primary_dark="*neutral_700",
), css="""
    .thumbnail-cell img { max-width: 150px; max-height: 150px; object-fit: contain; }
    #pdf-upload button[aria-label="Upload"],
    #pdf-upload button[aria-label="Upload file"] {
        min-width: 150px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 14px;
        padding: 0.4rem 1rem;
        background: var(--button-primary-background-fill, var(--primary-500));
        border: 1px solid var(--button-primary-border-color, var(--primary-500));
        color: var(--button-primary-text-color, #fff);
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
    }
    #pdf-upload button[aria-label="Upload"]:hover,
    #pdf-upload button[aria-label="Upload file"]:hover {
        filter: brightness(1.05);
    }
    #pdf-upload button[aria-label="Upload"]::after,
    #pdf-upload button[aria-label="Upload file"]::after {
        content: " 上传文件";
        margin-left: 6px;
    }
    /* 隐藏DataFrame的添加行按钮 */
    button[title="Add row"], button[aria-label="Add row"] {
        display: none !important;
    }
    /* 提示用户只有单号列可编辑 */
    .dataframe tbody tr td:first-child,
    .dataframe tbody tr td:last-child {
        background-color: rgba(128, 128, 128, 0.1) !important;
        cursor: not-allowed;
    }
    /* 紫色主题样式 */
    #loading_status textarea,
    #status_extract textarea,
    #status_rename textarea,
    #file_op_status textarea {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        font-weight: 500 !important;
    }
    #ocr_viewer {
        border: 2px solid #667eea !important;
        border-radius: 8px !important;
    }
""") as demo:
    gr.Markdown("## OCR - 服务器版")
    gr.Markdown(
        """
        **使用说明:**
        1. 上传PDF文件并点击 **"开始提取"**
        2. 查看提取结果，点击表格行即可在右侧预览大图
        3. 如需修改单号，在表格中直接编辑后点击 **"确认并重命名"**
        4. 在文件管理器中勾选需要的文件，点击 **"📥 批量下载"**
        5. ⚠️ **重要**: 输出文件每天00:00自动清理，下载链接10分钟后失效，请及时下载
        """
    )

    # 显示清理时间信息
    cleanup_info = gr.Markdown(value="📋 **文件自动清理**: 每天 00:00 清理 (下次: " + get_next_cleanup_time() + ")")

    # 上传和提取部分
    with gr.Row():
        upload_button = gr.File(
            label="上传PDF文件",
            file_count="multiple",
            file_types=[".pdf"],
            elem_id="pdf-upload"
        )

    extract_button = gr.Button("开始提取", variant="primary")
    loading_status = gr.Textbox(label="加载状态", value="", interactive=False, visible=True)
    status_textbox_extract = gr.Textbox(label="提取状态", interactive=False)

    # 结果表格
    results_df = gr.DataFrame(
        headers=["原始文件名", "提取的单号（点击下方重命名）", "提取图像"],
        datatype=["str", "str", "str"],
        interactive=True,
        visible=True,
        wrap=True
    )

    # 图片查看器
    with gr.Row():
        with gr.Column(scale=2):
            ocr_image_viewer = gr.Image(label="OCR识别结果（点击表格行查看大图）", type="filepath")
        with gr.Column(scale=1):
            gr.Markdown("""
            **图片说明:**
            - 🟢 绿色框：普通识别文本
            - 🔴 红色框：发货单号
            - 点击表格任意行查看对应图片
            """)

    # 重命名部分
    rename_button = gr.Button("确认并重命名", variant="stop")
    status_textbox_rename = gr.Textbox(label="重命名状态", lines=5, interactive=False)

    gr.Markdown("---")
    gr.Markdown("### 文件管理器")

    # 文件浏览器
    with gr.Row():
        refresh_output_btn = gr.Button("刷新", size="sm")
        download_output_btn = gr.Button("📥 批量下载", size="sm", variant="primary")
        delete_output_btn = gr.Button("删除选中", variant="stop", size="sm")

    output_files_df = gr.DataFrame(
        headers=["", "原始文件名", "重命名后文件名", "大小(KB)", "修改时间"],
        label="已处理文件列表",
        datatype=["bool", "str", "str", "str", "str"],
        interactive=True,
        column_widths=["8%", "30%", "30%", "12%", "20%"],
        value=list_output_files()
    )

    file_op_status = gr.Textbox(label="操作状态", interactive=False)

    # 下载文件组件
    download_file = gr.File(label="下载文件", interactive=False)

    # 事件绑定
    extract_button.click(
        fn=process_uploads_and_extract,
        inputs=upload_button,
        outputs=[results_df, loading_status, status_textbox_extract]
    )

    results_df.select(
        fn=view_ocr_image,
        inputs=results_df,
        outputs=ocr_image_viewer
    )

    rename_button.click(
        fn=rename_files_and_organize,
        inputs=results_df,
        outputs=status_textbox_rename
    )

    # Output文件浏览器事件
    refresh_output_btn.click(
        fn=list_output_files,
        outputs=output_files_df
    )

    # 删除文件 - Output目录
    def handle_delete(df):
        msg = delete_selected_files(df)
        return msg, list_output_files()

    delete_output_btn.click(
        fn=handle_delete,
        inputs=output_files_df,
        outputs=[file_op_status, output_files_df]
    )

    # 下载output目录选中的文件
    def handle_download(df):
        zip_path = download_selected_files_as_zip(df, OUTPUT_DIR)
        if zip_path is None:
            return None, "❌ 请先勾选要下载的文件"
        return zip_path, f"✓ 已打包 {Path(zip_path).name}，点击下方下载"

    download_output_btn.click(
        fn=handle_download,
        inputs=output_files_df,
        outputs=[download_file, file_op_status]
    )

    # 页面加载时初始化文件列表和清理信息
    demo.load(
        fn=lambda: (list_output_files(), "📋 **文件自动清理**: 每天 00:00 清理 (下次: " + get_next_cleanup_time() + ")"),
        outputs=[output_files_df, cleanup_info]
    )

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("OCR - 服务器版启动中...")
    print("=" * 60)

    # 创建必要的目录
    INPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    DOWNLOADS_DIR.mkdir(exist_ok=True)
    DEBUG_DIR.mkdir(exist_ok=True)
    OCR_IMAGES_DIR.mkdir(exist_ok=True)
    print("✓ 目录初始化完成")

    # 预加载 OCR 模型（在启动时就加载，避免首次使用时等待）
    print("\n正在预加载 OCR 模型...")
    model = get_ocr_model_lazy()
    if model is None:
        print("\n⚠ 警告: OCR 模型加载失败，请检查上述错误信息")
        print("可以继续启动应用，但 OCR 功能将不可用")
        print("=" * 60)

    # 启动定时清理任务
    print("\n正在启动定时清理任务...")
    scheduler = BackgroundScheduler()

    # Input目录: 每5分钟清理一次
    scheduler.add_job(cleanup_input_directory, 'interval', minutes=5, id='cleanup_input')

    # Output目录: 每天00:00清理
    scheduler.add_job(cleanup_output_directory, 'cron', hour=0, minute=0, id='cleanup_output')

    # Downloads目录: 每5分钟清理超过10分钟的文件
    scheduler.add_job(cleanup_downloads_directory, 'interval', minutes=5, id='cleanup_downloads')

    scheduler.start()
    print("✓ 定时清理任务已启动")
    print("  - Input目录: 每5分钟清理一次")
    print("  - Output目录: 每天00:00清理")
    print("  - Downloads目录: 每5分钟清理超过10分钟的文件")

    # 启动 Gradio 应用
    print("\n正在启动 Web 服务...")
    print("=" * 60)

    # 根据操作系统自动适配
    is_macos = sys.platform.startswith("darwin")
    if is_macos:
        server_name = "127.0.0.1"
        open_browser = True
        print("开发模式 (macOS)")
        print("访问地址: http://127.0.0.1:8143")
    else:
        server_name = "0.0.0.0"
        open_browser = False
        print("服务器模式 (Linux)")
        print("访问地址: http://0.0.0.0:8143")
        print("外网访问: http://<服务器IP>:8143")

    print("=" * 60)

    try:
        demo.launch(
            server_name=server_name,
            server_port=8143,
            share=False,
            inbrowser=open_browser
        )
    except KeyboardInterrupt:
        print("\n正在关闭...")
        scheduler.shutdown()
        print("定时任务已停止")
