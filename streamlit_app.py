import streamlit as st
from PIL import Image, ImageOps, ImageEnhance
import io
from datetime import datetime
import zipfile
from pathlib import Path
import concurrent.futures

def run_app():
    # ===================== ФУНКЦИИ =====================

    def resize_with_crop(image, target_size):
        target_width, target_height = target_size
        image_ratio = image.width / image.height
        target_ratio = target_width / target_height

        if image_ratio > target_ratio:
            new_height = target_height
            new_width = int(new_height * image_ratio)
        else:
            new_width = target_width
            new_height = int(new_width / image_ratio)

        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        left = (new_width - target_width) // 2
        top = (new_height - target_height) // 2
        right = left + target_width
        bottom = top + target_height
        return resized.crop((left, top, right, bottom))

    def resize_with_aspect(image, target_size):
        target_width, target_height = target_size
        original_width, original_height = image.size
        ratio = min(target_width / original_width, target_height / original_height)
        new_size = (int(original_width * ratio), int(original_height * ratio))
        resized_image = image.resize(new_size, Image.Resampling.LANCZOS)
        new_image = Image.new("RGB", (target_width, target_height), (255, 255, 255))
        paste_x = (target_width - new_size[0]) // 2
        paste_y = (target_height - new_size[1]) // 2
        new_image.paste(resized_image, (paste_x, paste_y))
        return new_image

    def parse_sizes(sizes_input):
        sizes = []
        for size_str in sizes_input.split(","):
            size_str = size_str.strip()
            if "x" in size_str:
                parts = size_str.lower().split("x")
                if len(parts) == 2:
                    try:
                        w, h = int(parts[0]), int(parts[1])
                        sizes.append({"name": size_str, "size": (w, h)})
                    except:
                        continue
        return sizes

    def add_frame(image, frame_thickness, frame_color):
        width, height = image.size
        new_width = width + 2 * frame_thickness
        new_height = height + 2 * frame_thickness
        framed_img = Image.new("RGB", (new_width, new_height), frame_color)
        framed_img.paste(image, (frame_thickness, frame_thickness))
        return framed_img

    def rotate_flip(image, rotate_angle, flip_horizontal, flip_vertical):
        if rotate_angle != 0:
            image = image.rotate(rotate_angle, expand=True)
        if flip_horizontal:
            image = ImageOps.mirror(image)
        if flip_vertical:
            image = ImageOps.flip(image)
        return image

    def apply_filters(image, brightness=1.0, contrast=1.0, sharpness=1.0):
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(brightness)
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(contrast)
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(sharpness)
        return image

    def process_single_image(args):
        (uploaded_file, size_info, output_format, quality, preserve_aspect,
         rotate_angle, flip_horizontal, flip_vertical,
         brightness, contrast, sharpness,
         frame_thickness, frame_color) = args
        filename_base = f"{Path(uploaded_file.name).stem}_{size_info['name']}_{size_info['size'][0]}x{size_info['size'][1]}"
        filename_base = "".join(c for c in filename_base if c.isalnum() or c in "._- ").strip()

        try:
            image = Image.open(uploaded_file).convert("RGBA" if output_format=="PNG" else "RGB")
            # Основные преобразования
            if preserve_aspect:
                resized_img = resize_with_aspect(image, size_info["size"])
            else:
                resized_img = resize_with_crop(image, size_info["size"])

            # Поворот и отражение
            resized_img = rotate_flip(resized_img, rotate_angle, flip_horizontal, flip_vertical)

            # Фильтры
            resized_img = apply_filters(resized_img, brightness, contrast, sharpness)

            # Добавление рамки
            if frame_thickness > 0:
                resized_img = add_frame(resized_img, frame_thickness, frame_color)

            # Конвертация формата
            if output_format in ["JPEG", "WEBP"] and resized_img.mode != "RGB":
                resized_img = resized_img.convert("RGB")

            # Сохранение
            img_bytes = io.BytesIO()
            save_params = {'quality': quality} if output_format in ["JPEG", "WEBP"] else {}
            resized_img.save(img_bytes, format=output_format, **save_params)
            data = img_bytes.getvalue()

            filename = f"{filename_base}.{output_format.lower()}"
            return filename, data
        except Exception as e:
            return None

    def process_images(files, sizes, output_format, quality, preserve_aspect,
                       rotate_angle, flip_horizontal, flip_vertical,
                       brightness, contrast, sharpness,
                       frame_thickness, frame_color):
        total_tasks = len(files) * len(sizes)
        progress = st.progress(0)
        status_message = st.empty()

        zip_buffer = io.BytesIO()
        individual_files = []

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            tasks = []
            for uploaded_file in files:
                for size_info in sizes:
                    tasks.append((uploaded_file, size_info, output_format, quality, preserve_aspect,
                                  rotate_angle, flip_horizontal, flip_vertical,
                                  brightness, contrast, sharpness,
                                  frame_thickness, frame_color))
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                results = list(executor.map(process_single_image, tasks))
                for idx, result in enumerate(results):
                    if result:
                        filename, data = result
                        zipf.writestr(filename, data)
                        individual_files.append((filename, data))
                    progress.progress((idx + 1) / total_tasks)
        status_message.text("✅ Обработка завершена!")

        zip_buffer.seek(0)
        return zip_buffer.getvalue(), individual_files

    # ===================== НАСТРОЙКИ =====================

    st.set_page_config(
        page_title="ImageMagic Pro - Многофункциональный редактор",
        page_icon="✨",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # CSS стили
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #FF4B4B;
        text-align: center;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-top: 0;
        margin-bottom: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # Заголовки
    st.markdown("<h1 class='main-header'>ImageMagic Pro</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-header'>Многофункциональный редактор изображений</p>", unsafe_allow_html=True)

    # В боковой панели
    with st.sidebar:
        st.header("Настройки обработки")
        output_format = st.selectbox("Формат выхода", ["JPEG", "PNG", "WEBP"])
        quality = st.slider("Качество", 1, 100, 85)
        preserve_aspect = st.checkbox("Сохранять пропорции", value=True)

        st.header("Трансформации")
        rotate_angle = st.slider("Поворот (градусы)", 0, 360, 0)
        flip_horizontal = st.checkbox("Отразить по горизонтали")
        flip_vertical = st.checkbox("Отразить по вертикали")

        st.header("Фильтры")
        brightness = st.slider("Яркость", 0.1, 3.0, 1.0, step=0.1)
        contrast = st.slider("Контрастность", 0.1, 3.0, 1.0, step=0.1)
        sharpness = st.slider("Резкость", 0.1, 3.0, 1.0, step=0.1)

        st.header("Добавление рамки")
        frame_thickness = st.slider("Толщина рамки (пиксели)", 0, 50, 0)
        frame_color = st.color_picker("Цвет рамки", "#000000")

        st.header("Размеры для обработки")
        sizes_input = st.text_area("Введите размеры (через запятую, например, 600x600, 800x800)", value="600x600, 800x800")
        sizes = parse_sizes(sizes_input)

    # Загрузка изображений
    st.write("Загрузите изображения для обработки:")
    uploaded_files = st.file_uploader("Выберите файлы", accept_multiple_files=True, type=["png", "jpg", "jpeg", "webp"])

    # Обработка
    if uploaded_files and sizes:
        zip_bytes, individual_files = process_images(
            uploaded_files, sizes, output_format, quality, preserve_aspect,
            rotate_angle, flip_horizontal, flip_vertical,
            brightness, contrast, sharpness,
            frame_thickness, frame_color
        )

        # Скачивание ZIP
        st.download_button(
            label="📥 Скачать ZIP архив",
            data=zip_bytes,
            file_name=f"images_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            mime="application/zip"
        )

        # Отдельные файлы
        st.write("Или скачайте отдельные файлы:")
        for filename, data in individual_files:
            st.download_button(
                label=f"📥 {filename}",
                data=data,
                file_name=filename,
                mime="image/*"
            )

if __name__ == "__main__":
    run_app()
