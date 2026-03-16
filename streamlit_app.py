import streamlit as st
from PIL import Image, ImageEnhance, ImageOps
import io
import zipfile
import os
from datetime import datetime

def validate_image_size(size_str):
    """Валидация формата размера"""
    try:
        if 'x' not in size_str:
            return None
        w, h = size_str.split('x')
        w, h = int(w.strip()), int(h.strip())
        if w <= 0 or h <= 0 or w > 10000 or h > 10000:
            return None
        return (w, h)
    except:
        return None

def get_marketplace_presets():
    """Пресеты размеров для популярных маркетплейсов"""
    return {
        "Wildberries (Фото товара)": "900x1200",
        "Wildberries (Баннер)": "1280x400",
        "Ozon (Основное фото)": "1080x1080",
        "Ozon (Галерея)": "900x1200",
        "Яндекс.Маркет": "1000x1000",
        "СберМегаМаркет": "1200x1200",
        "AliExpress": "800x800"
    }

def optimize_for_marketplace(img, marketplace_type):
    """Специфическая оптимизация для конкретного маркетплейса"""
    if marketplace_type == "Wildberries":
        # Wildberries требует белый фон для некоторых категорий
        if st.session_state.get('add_white_bg', False):
            img = add_white_background(img)
    
    elif marketplace_type == "Ozon":
        # Ozon рекомендует квадратные фото для галереи
        if img.width != img.height:
            # Делаем изображение квадратным с белыми полями
            max_size = max(img.width, img.height)
            new_img = Image.new('RGB', (max_size, max_size), 'white')
            offset = ((max_size - img.width) // 2, (max_size - img.height) // 2)
            new_img.paste(img, offset)
            img = new_img
    
    return img

def add_white_background(img):
    """Добавление белого фона для изображений с прозрачностью"""
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
        return background
    return img

def auto_enhance_for_marketplace(img):
    """Автоматическое улучшение изображения для маркетплейсов"""
    # Улучшение контраста для лучшей видимости
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.1)
    
    # Улучшение резкости
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.2)
    
    # Улучшение насыщенности
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(1.05)
    
    return img

def process_single_image(uploaded_file, size_info, output_format, quality, preserve_aspect,
                         rotate_angle, flip_horizontal, flip_vertical,
                         brightness, contrast, sharpness,
                         frame_thickness, frame_color,
                         add_white_bg=False, auto_enhance=False, marketplace_preset=None):
    try:
        # Открываем изображение
        img = Image.open(uploaded_file)
        
        # Конвертируем в RGB если нужно
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # Добавление белого фона для PNG с прозрачностью
        if add_white_bg:
            img = add_white_background(img)
        
        # Автоулучшение для маркетплейсов
        if auto_enhance:
            img = auto_enhance_for_marketplace(img)
        
        # Применяем трансформации
        if rotate_angle != 0:
            img = img.rotate(rotate_angle, expand=True, fillcolor='white')
        
        if flip_horizontal:
            img = ImageOps.mirror(img)
        if flip_vertical:
            img = ImageOps.flip(img)
        
        # Изменяем размер
        target_size = size_info["size"]
        if preserve_aspect:
            img.thumbnail(target_size, Image.Resampling.LANCZOS)
            # Добавляем белые поля для точного соответствия размеру
            new_img = Image.new('RGB', target_size, 'white')
            offset = ((target_size[0] - img.width) // 2, (target_size[1] - img.height) // 2)
            new_img.paste(img, offset)
            img = new_img
        else:
            img = img.resize(target_size, Image.Resampling.LANCZOS)
        
        # Применяем улучшения
        if brightness != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(brightness)
        
        if contrast != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(contrast)
        
        if sharpness != 1.0:
            enhancer = ImageEnhape.Sharpness(img)
            img = enhancer.enhance(sharpness)
        
        # Добавляем рамку
        if frame_thickness > 0:
            img = ImageOps.expand(img, border=frame_thickness, fill=frame_color)
        
        # Сохраняем в байты
        img_bytes = io.BytesIO()
        save_params = {}
        if output_format in ["JPEG", "WEBP"]:
            save_params = {'quality': quality, 'optimize': True}
        
        # Для JPEG всегда сохраняем как RGB
        if output_format == "JPEG" and img.mode == "RGBA":
            img = img.convert('RGB')
        
        img.save(img_bytes, format=output_format, **save_params)
        data = img_bytes.getvalue()
        
        # Генерируем имя файла
        base_name = os.path.splitext(uploaded_file.name)[0]
        size_name = size_info["name"].replace('x', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{base_name}_{size_name}_{timestamp}.{output_format.lower()}"
        
        return filename, data
        
    except Exception as e:
        st.error(f"Ошибка при обработке {uploaded_file.name}: {str(e)}")
        return None

def main():
    st.set_page_config(
        page_title="Оптимизатор изображений для маркетплейсов",
        page_icon="🛍️",
        layout="wide"
    )
    
    st.title("🛍️ Оптимизатор изображений для маркетплейсов")
    st.markdown("---")
    
    # Инициализация session state
    if 'add_white_bg' not in st.session_state:
        st.session_state.add_white_bg = False
    
    # Основной контент в две колонки
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📁 Загрузка изображений")
        uploaded_files = st.file_uploader(
            "Выберите изображения (PNG, JPG, JPEG)",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True
        )
        
        if uploaded_files:
            st.success(f"Загружено: {len(uploaded_files)} файлов")
            # Превью первого изображения
            if len(uploaded_files) > 0:
                preview_img = Image.open(uploaded_files[0])
                st.image(preview_img, caption="Пример загруженного изображения", width=300)
    
    with col2:
        st.header("⚙️ Настройки обработки")
        
        # Пресеты маркетплейсов
        marketplace_presets = get_marketplace_presets()
        selected_preset = st.selectbox(
            "Пресет маркетплейса",
            ["Выберите пресет"] + list(marketplace_presets.keys())
        )
        
        if selected_preset != "Выберите пресет":
            preset_size = marketplace_presets[selected_preset]
            st.info(f"Рекомендуемый размер: {preset_size}")
        
        # Основные настройки
        output_format = st.selectbox(
            "Формат вывода",
            ["JPEG", "PNG", "WEBP"],
            help="JPEG - лучший выбор для фото, PNG - для изображений с текстом, WEBP - современный формат"
        )
        
        quality = st.slider(
            "Качество (для JPEG/WEBP)",
            1, 100, 85,
            help="Более высокое качество = больший размер файла"
        )
        
        # Выбор размеров
        st.subheader("📐 Размеры")
        size_option = st.radio(
            "Способ задания размеров",
            ["Ввести вручную", "Использовать пресеты"]
        )
        
        sizes_list = []
        if size_option == "Использовать пресеты":
            selected_sizes = st.multiselect(
                "Выберите размеры",
                list(marketplace_presets.values()),
                default=["900x1200"]
            )
            for size_str in selected_sizes:
                size_tuple = validate_image_size(size_str)
                if size_tuple:
                    sizes_list.append({"name": size_str.replace('x', '×'), "size": size_tuple})
        else:
            sizes_input = st.text_input(
                "Размеры (через запятую, например: 800x600, 1024x768)",
                "800x800, 900x1200, 1080x1080"
            )
            for size_str in sizes_input.split(","):
                size_tuple = validate_image_size(size_str)
                if size_tuple:
                    sizes_list.append({"name": size_str.strip().replace('x', '×'), "size": size_tuple})
        
        if not sizes_list:
            st.warning("⚠️ Пожалуйста, введите корректные размеры")
            return
    
    # Расширенные настройки в сайдбаре
    with st.sidebar:
        st.header("🎨 Расширенные настройки")
        
        st.subheader("Оптимизация для маркетплейсов")
        add_white_bg = st.checkbox(
            "Добавить белый фон",
            value=True,
            help="Удаляет прозрачность и добавляет белый фон"
        )
        st.session_state.add_white_bg = add_white_bg
        
        auto_enhance = st.checkbox(
            "Автоулучшение",
            value=True,
            help="Автоматическая оптимизация контраста, резкости и цвета"
        )
        
        st.subheader("Трансформации")
        preserve_aspect = st.checkbox("Сохранять пропорции", value=True)
        rotate_angle = st.slider("Поворот (градусы)", -180, 180, 0)
        
        col1, col2 = st.columns(2)
        with col1:
            flip_horizontal = st.checkbox("Отразить по горизонтали")
        with col2:
            flip_vertical = st.checkbox("Отразить по вертикали")
        
        st.subheader("Коррекция изображения")
        brightness = st.slider("Яркость", 0.1, 3.0, 1.0, 0.1)
        contrast = st.slider("Контраст", 0.1, 3.0, 1.0, 0.1)
        sharpness = st.slider("Резкость", 0.1, 3.0, 1.0, 0.1)
        
        st.subheader("Рамка")
        frame_thickness = st.slider("Толщина рамки", 0, 50, 0)
        if frame_thickness > 0:
            frame_color = st.color_picker("Цвет рамки", "#FFFFFF")
        else:
            frame_color = "#FFFFFF"
    
    # Обработка изображений
    if uploaded_files and sizes_list:
        st.markdown("---")
        st.header("🔄 Обработка")
        
        if st.button("🚀 Начать обработку", type="primary"):
            with st.spinner("Обработка изображений..."):
                all_files = []
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                total_tasks = len(uploaded_files) * len(sizes_list)
                completed = 0
                
                for uploaded_file in uploaded_files:
                    for size_info in sizes_list:
                        status_text.text(f"Обработка: {uploaded_file.name} -> {size_info['name']}")
                        
                        result = process_single_image(
                            uploaded_file, size_info, output_format, quality, preserve_aspect,
                            rotate_angle, flip_horizontal, flip_vertical,
                            brightness, contrast, sharpness,
                            frame_thickness, frame_color,
                            add_white_bg, auto_enhance, selected_preset
                        )
                        
                        if result:
                            filename, data = result
                            all_files.append((filename, data))
                        
                        completed += 1
                        progress_bar.progress(completed / total_tasks)
                
                if all_files:
                    # Создаем ZIP архив
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        for filename, data in all_files:
                            zip_file.writestr(filename, data)
                    
                    zip_buffer.seek(0)
                    
                    st.success(f"✅ Готово! Обработано {len(all_files)} изображений")
                    
                    # Информация о результате
                    total_size_mb = len(zip_buffer.getvalue()) / (1024 * 1024)
                    st.info(f"📦 Размер архива: {total_size_mb:.2f} MB")
                    
                    # Кнопка скачивания
                    st.download_button(
                        label="📥 Скачать ZIP архив",
                        data=zip_buffer,
                        file_name=f"images_for_marketplace_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                        mime="application/zip"
                    )
                else:
                    st.error("❌ Не удалось обработать изображения")
    
    elif uploaded_files and not sizes_list:
        st.info("📏 Пожалуйста, укажите размеры изображений")
    else:
        st.info("📁 Загрузите изображения для начала работы")

if __name__ == "__main__":
    main()
