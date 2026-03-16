import streamlit as st
from PIL import Image
import io
from datetime import datetime
import zipfile
from pathlib import Path

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

    def process_images(files, sizes, output_format, quality, preserve_aspect):
        total_tasks = len(files) * len(sizes)
        progress = st.progress(0)
        status_message = st.empty()

        zip_buffer = io.BytesIO()
        individual_files = []

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for uploaded_file in files:
                try:
                    original_name = Path(uploaded_file.name).stem
                    image = Image.open(uploaded_file).convert("RGBA" if output_format=="PNG" else "RGB")
                except Exception as e:
                    st.error(f"Ошибка открытия файла {uploaded_file.name}: {e}")
                    continue

                for size_info in sizes:
                    try:
                        filename_base = f"{original_name}_{size_info['name']}_{size_info['size'][0]}x{size_info['size'][1]}"
                        filename_base = "".join(c for c in filename_base if c.isalnum() or c in "._- ").strip()

                        if preserve_aspect:
                            resized_img = resize_with_aspect(image, size_info["size"])
                        else:
                            resized_img = resize_with_crop(image, size_info["size"])

                        if output_format in ["JPEG", "WEBP"] and resized_img.mode != "RGB":
                            resized_img = resized_img.convert("RGB")

                        img_bytes = io.BytesIO()
                        save_params = {'quality': quality} if output_format in ["JPEG", "WEBP"] else {}
                        resized_img.save(img_bytes, format=output_format, **save_params)
                        data = img_bytes.getvalue()

                        filename = f"{filename_base}.{output_format.lower()}"
                        zipf.writestr(filename, data)
                        individual_files.append((filename, data))
                        progress.progress((len(individual_files) + len(sizes)*(list(files).index(uploaded_file))) / total_tasks)
                    except Exception as e:
                        st.error(f"Ошибка обработки {size_info['name']} для файла {uploaded_file.name}: {e}")
                        continue
        status_message.text("✅ Обработка завершена!")

        zip_buffer.seek(0)
        zip_bytes = zip_buffer.getvalue()
        return zip_bytes, individual_files

    # ===================== НАСТРОЙКИ =====================

    st.set_page_config(
        page_title="ImageMagic Pro - Конвертер для маркетплейсов",
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
    st.markdown("<p class='sub-header'>Конвертер изображений для маркетплейсов</p>", unsafe_allow_html=True)

    # Настройки
    with st.sidebar:
        st.header("Настройки")
        output_format = st.selectbox("Формат сохраняемых изображений", ["JPEG", "PNG", "WEBP"])
        quality = st.slider("Качество изображения (%)", 1, 100, 85)
        preserve_aspect = st.checkbox("Сохранять пропорции при изменении размера", value=True)
        sizes_input = st.text_area(
            "Введите размеры через запятую (например: 512x512,1024x1024)",
            value="512x512,1024x1024"
        )
        sizes = parse_sizes(sizes_input)

    # Основная часть
    st.write("Загрузите изображения для обработки:")
    uploaded_files = st.file_uploader("Выберите файлы", accept_multiple_files=True, type=["png", "jpg", "jpeg", "webp"])

    if uploaded_files and sizes:
        zip_bytes, individual_files = process_images(
            uploaded_files, sizes, output_format, quality, preserve_aspect
        )

        # Скачивание ZIP
        st.download_button(
            label="📥 Скачать ZIP архив",
            data=zip_bytes,
            file_name=f"images_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            mime="application/zip"
        )
        st.write("или")
        # Отдельные файлы
        for filename, data in individual_files:
            st.download_button(
                label=f"📥 {filename}",
                data=data,
                file_name=filename,
                mime="image/*"
            )

if __name__ == "__main__":
    run_app()
