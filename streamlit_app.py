import streamlit as st
from PIL import Image, ImageEnhance, ImageOps, ImageDraw, ImageFilter, ImageChops
import io
import zipfile
import os
from datetime import datetime
import numpy as np
import math
import pandas as pd
from pathlib import Path

# ================ КОНФИГУРАЦИЯ СТРАНИЦЫ ================

st.set_page_config(
    page_title="PRO Студия для маркетплейсов",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================ КЛАССЫ ДЛЯ ПРОФЕССИОНАЛЬНОЙ ОБРАБОТКИ ================

class ImageProcessor:
    """Базовый класс для обработки изображений"""
    
    @staticmethod
    def resize_with_aspect(img, target_size, mode='contain', bg_color='white'):
        """Умное изменение размера с сохранением пропорций"""
        try:
            target_w, target_h = target_size
            
            if mode == 'stretch':
                return img.resize(target_size, Image.Resampling.LANCZOS)
            
            elif mode == 'cover':
                # Заполнение с обрезкой
                ratio = max(target_w/img.width, target_h/img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img_resized = img.resize(new_size, Image.Resampling.LANCZOS)
                
                # Обрезка до целевого размера
                left = (new_size[0] - target_w) // 2
                top = (new_size[1] - target_h) // 2
                return img_resized.crop((left, top, left + target_w, top + target_h))
            
            else:  # contain
                img.thumbnail(target_size, Image.Resampling.LANCZOS)
                new_img = Image.new('RGB', target_size, bg_color)
                offset = ((target_size[0] - img.width) // 2, (target_size[1] - img.height) // 2)
                new_img.paste(img, offset)
                return new_img
        except Exception as e:
            st.error(f"Ошибка при изменении размера: {str(e)}")
            return img
    
    @staticmethod
    def add_white_background(img):
        """Добавление белого фона для изображений с прозрачностью"""
        try:
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[-1])
                elif img.mode == 'P':
                    img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img)
                return background
            return img
        except Exception as e:
            st.error(f"Ошибка при добавлении фона: {str(e)}")
            return img
    
    @staticmethod
    def add_watermark(img, text, position='bottom-right', opacity=128):
        """Добавление водяного знака"""
        try:
            if not text:
                return img
            
            # Создаем слой для водяного знака
            watermark = Image.new('RGBA', img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(watermark)
            
            # Размер текста в зависимости от изображения
            font_size = min(img.width, img.height) // 20
            
            try:
                # Пробуем загрузить шрифт
                font_path = None
                possible_paths = [
                    "arial.ttf",
                    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                    "/System/Library/Fonts/Helvetica.ttf",
                    "C:\\Windows\\Fonts\\Arial.ttf"
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        font_path = path
                        break
                
                if font_path:
                    font = ImageFont.truetype(font_path, font_size)
                else:
                    font = ImageFont.load_default()
            except:
                font = ImageFont.load_default()
            
            # Получаем размер текста
            try:
                # Для новых версий Pillow
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            except:
                # Для старых версий
                text_width, text_height = draw.textsize(text, font=font)
            
            padding = 20
            if position == 'top-left':
                pos = (padding, padding)
            elif position == 'top-right':
                pos = (img.width - text_width - padding, padding)
            elif position == 'bottom-left':
                pos = (padding, img.height - text_height - padding)
            else:  # bottom-right
                pos = (img.width - text_width - padding, img.height - text_height - padding)
            
            # Рисуем текст с полупрозрачностью
            draw.text(pos, text, fill=(255, 255, 255, opacity), font=font)
            
            # Добавляем обводку для читаемости
            draw.text((pos[0]-1, pos[1]), text, fill=(0, 0, 0, opacity), font=font)
            draw.text((pos[0]+1, pos[1]), text, fill=(0, 0, 0, opacity), font=font)
            draw.text((pos[0], pos[1]-1), text, fill=(0, 0, 0, opacity), font=font)
            draw.text((pos[0], pos[1]+1), text, fill=(0, 0, 0, opacity), font=font)
            
            # Накладываем водяной знак
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            result = Image.alpha_composite(img, watermark)
            
            # Конвертируем обратно в исходный режим если нужно
            if img.mode == 'RGB':
                result = result.convert('RGB')
            
            return result
        except Exception as e:
            st.error(f"Ошибка при добавлении водяного знака: {str(e)}")
            return img

class StudioEnhancer:
    """Профессиональная студийная обработка"""
    
    @staticmethod
    def auto_white_balance(img):
        """Автоматический баланс белого"""
        try:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            img_array = np.array(img).astype(np.float32)
            r, g, b = img_array[:,:,0], img_array[:,:,1], img_array[:,:,2]
            
            # Находим серые области
            gray_scale = 0.299 * r + 0.587 * g + 0.114 * b
            mask = (gray_scale > 50) & (gray_scale < 200)
            
            if np.any(mask):
                r_mean = np.mean(r[mask])
                g_mean = np.mean(g[mask])
                b_mean = np.mean(b[mask])
                
                r_gain = g_mean / r_mean if r_mean > 0 else 1
                b_gain = g_mean / b_mean if b_mean > 0 else 1
                
                img_array[:,:,0] = np.clip(img_array[:,:,0] * r_gain, 0, 255)
                img_array[:,:,2] = np.clip(img_array[:,:,2] * b_gain, 0, 255)
            
            return Image.fromarray(img_array.astype('uint8'))
        except Exception as e:
            st.error(f"Ошибка при балансе белого: {str(e)}")
            return img
    
    @staticmethod
    def studio_lighting(img, intensity=1.2, warmth=0):
        """Студийное освещение"""
        try:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(1.1 * intensity)
            
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.15 * intensity)
            
            if warmth != 0:
                img_array = np.array(img).astype(np.float32)
                img_array[:,:,0] = np.clip(img_array[:,:,0] * (1 + warmth * 0.1), 0, 255)
                img_array[:,:,2] = np.clip(img_array[:,:,2] * (1 - warmth * 0.1), 0, 255)
                img = Image.fromarray(img_array.astype('uint8'))
            
            return img
        except Exception as e:
            st.error(f"Ошибка при освещении: {str(e)}")
            return img
    
    @staticmethod
    def remove_shadows(img, strength=1.0):
        """Удаление теней"""
        try:
            img_array = np.array(img.convert('L')).astype(np.float32)
            
            gradient_y = np.gradient(img_array, axis=0)
            gradient_x = np.gradient(img_array, axis=1)
            gradient_magnitude = np.sqrt(gradient_x**2 + gradient_y**2)
            
            brightness = img_array / 255.0
            shadow_mask = (brightness < 0.5) & (gradient_magnitude < 10)
            
            if np.any(shadow_mask):
                img_array[shadow_mask] = np.minimum(img_array[shadow_mask] * (1 + 0.3 * strength), 255)
                img = Image.fromarray(img_array.astype('uint8')).convert('RGB')
            
            return img
        except Exception as e:
            st.error(f"Ошибка при удалении теней: {str(e)}")
            return img
    
    @staticmethod
    def enhance_texture(img, strength=0.5):
        """Усиление текстуры"""
        try:
            img_array = np.array(img).astype(np.float32)
            img_gray = np.array(img.convert('L')).astype(np.float32)
            
            # Применяем размытие
            from PIL import ImageFilter
            blurred = Image.fromarray(img_gray.astype('uint8')).filter(ImageFilter.GaussianBlur(radius=2))
            texture_mask = img_gray - np.array(blurred)
            
            for c in range(min(3, img_array.shape[2])):
                img_array[:,:,c] = np.clip(img_array[:,:,c] + texture_mask * strength, 0, 255)
            
            return Image.fromarray(img_array.astype('uint8'))
        except Exception as e:
            st.error(f"Ошибка при усилении текстуры: {str(e)}")
            return img

class InfographicGenerator:
    """Генератор инфографики"""
    
    @staticmethod
    def create_size_chart(product_type, size_data):
        """Создание размерной сетки"""
        try:
            img = Image.new('RGB', (800, 600), 'white')
            draw = ImageDraw.Draw(img)
            
            # Заголовок
            draw.rectangle([0, 0, 800, 60], fill='#2c3e50')
            
            try:
                font = ImageFont.load_default()
                draw.text((40, 20), f"Размерная сетка - {product_type}", fill='white', font=font)
            except:
                draw.text((40, 20), f"Размерная сетка - {product_type}", fill='white')
            
            # Таблица размеров
            sizes = ['S', 'M', 'L', 'XL'] if not size_data else list(size_data.keys())
            measurements = ['Длина', 'Ширина', 'Высота'] if product_type in ['Мебель', 'Коробки'] else ['Обхват груди', 'Обхват талии', 'Обхват бедер']
            
            y_start = 100
            x_positions = [50, 200, 350, 500, 650]
            
            # Заголовки таблицы
            for i, size in enumerate(['Размер'] + sizes):
                if i < len(x_positions):
                    draw.text((x_positions[i], y_start-30), size, fill='#2c3e50')
            
            # Заполняем данными
            y_current = y_start + 40
            for measurement in measurements:
                draw.text((50, y_current), measurement, fill='#2c3e50')
                
                for i, size in enumerate(sizes):
                    if i < 4:
                        value = '—'
                        if size_data and size in size_data and measurement in size_data[size]:
                            value = size_data[size][measurement]
                        draw.text((200 + i*150, y_current), str(value), fill='#34495e')
                
                y_current += 40
                draw.line([(50, y_current-20), (750, y_current-20)], fill='#bdc3c7', width=1)
            
            return img
        except Exception as e:
            st.error(f"Ошибка при создании размерной сетки: {str(e)}")
            return Image.new('RGB', (800, 600), 'white')
    
    @staticmethod
    def create_usp_banner(product_name, usp_list):
        """Создание баннера с УТП"""
        try:
            img = Image.new('RGB', (1000, 400), '#f8f9fa')
            draw = ImageDraw.Draw(img)
            
            # Градиентный фон
            for i in range(400):
                color = int(255 - i * 0.3)
                draw.line([(0, i), (1000, i)], fill=(color, color, color))
            
            # Заголовок
            draw.text((100, 50), product_name.upper(), fill='#2c3e50')
            draw.text((100, 100), "Почему стоит выбрать?", fill='#34495e')
            
            # Список преимуществ
            y_position = 180
            for i, usp in enumerate(usp_list[:5]):
                # Иконка (круг)
                draw.ellipse([80, y_position-15, 110, y_position+15], fill='#27ae60')
                draw.text((87, y_position-8), "✓", fill='white')
                
                # Текст
                draw.text((130, y_position-10), usp, fill='#2c3e50')
                y_position += 40
            
            return img
        except Exception as e:
            st.error(f"Ошибка при создании баннера: {str(e)}")
            return Image.new('RGB', (1000, 400), '#f8f9fa')

# ================ КЛАСС ДЛЯ МАССОВОЙ ОБРАБОТКИ ================

class BatchProcessor:
    """Массовая обработка изображений с подстановкой данных"""
    
    def __init__(self):
        self.data = None
        self.images = {}
        self.mappings = {}
    
    def load_data_file(self, uploaded_file):
        """Загрузка файла с данными (CSV или Excel)"""
        try:
            if uploaded_file.name.endswith('.csv'):
                self.data = pd.read_csv(uploaded_file)
            elif uploaded_file.name.endswith(('.xlsx', '.xls')):
                self.data = pd.read_excel(uploaded_file)
            else:
                st.error("Неподдерживаемый формат файла. Используйте CSV или Excel.")
                return False
            
            st.success(f"Загружено {len(self.data)} строк и {len(self.data.columns)} колонок")
            return True
        except Exception as e:
            st.error(f"Ошибка загрузки файла: {str(e)}")
            return False
    
    def load_images(self, uploaded_files):
        """Загрузка изображений"""
        self.images = {}
        for file in uploaded_files:
            try:
                self.images[file.name] = Image.open(file)
            except Exception as e:
                st.error(f"Ошибка загрузки {file.name}: {str(e)}")
        return len(self.images)
    
    def create_mapping(self, data_column):
        """Создание соответствия между изображениями и данными"""
        self.mappings = {}
        
        for filename, img in self.images.items():
            # Ищем соответствие по паттерну в имени файла
            for idx, row in self.data.iterrows():
                if str(row[data_column]) in filename or filename.startswith(str(row[data_column])):
                    self.mappings[filename] = idx
                    break
        
        return len(self.mappings)
    
    def add_text_to_image(self, img, text, position, font_size=None, color=(0, 0, 0), 
                         opacity=255, rotation=0, bg_color=None, padding=10):
        """Добавление текста на изображение"""
        try:
            # Создаем копию изображения
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            txt_layer = Image.new('RGBA', img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(txt_layer)
            
            # Определяем размер шрифта
            if font_size is None:
                font_size = min(img.size) // 20
            
            try:
                font = ImageFont.load_default()
            except:
                font = ImageFont.load_default()
            
            # Получаем размер текста
            try:
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            except:
                text_width, text_height = len(text) * font_size // 2, font_size
            
            # Рассчитываем позицию
            if position == "top-left":
                x, y = padding, padding
            elif position == "top-center":
                x = (img.width - text_width) // 2
                y = padding
            elif position == "top-right":
                x = img.width - text_width - padding
                y = padding
            elif position == "center-left":
                x = padding
                y = (img.height - text_height) // 2
            elif position == "center":
                x = (img.width - text_width) // 2
                y = (img.height - text_height) // 2
            elif position == "center-right":
                x = img.width - text_width - padding
                y = (img.height - text_height) // 2
            elif position == "bottom-left":
                x = padding
                y = img.height - text_height - padding
            elif position == "bottom-center":
                x = (img.width - text_width) // 2
                y = img.height - text_height - padding
            elif position == "bottom-right":
                x = img.width - text_width - padding
                y = img.height - text_height - padding
            else:
                x, y = padding, padding
            
            # Добавляем фон для текста если нужно
            if bg_color:
                if len(bg_color) == 3:
                    bg_color = (*bg_color, opacity)
                bg_layer = Image.new('RGBA', (text_width + padding*2, text_height + padding*2), bg_color)
                txt_layer.paste(bg_layer, (x - padding, y - padding), bg_layer)
            
            # Рисуем текст
            text_color = (*color, opacity) if len(color) == 3 else color
            draw.text((x, y), text, fill=text_color, font=font)
            
            # Поворачиваем если нужно
            if rotation != 0:
                txt_layer = txt_layer.rotate(rotation, expand=0, center=(x + text_width//2, y + text_height//2))
            
            # Накладываем на изображение
            result = Image.alpha_composite(img, txt_layer)
            
            return result
        except Exception as e:
            st.error(f"Ошибка при добавлении текста: {str(e)}")
            return img
    
    def add_image_overlay(self, base_img, overlay_img, position, size_ratio=0.2, opacity=255):
        """Добавление изображения поверх основного"""
        try:
            if base_img.mode != 'RGBA':
                base_img = base_img.convert('RGBA')
            
            # Изменяем размер накладываемого изображения
            new_width = int(base_img.width * size_ratio)
            new_height = int(overlay_img.height * (new_width / overlay_img.width))
            overlay_resized = overlay_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            if overlay_resized.mode != 'RGBA':
                overlay_resized = overlay_resized.convert('RGBA')
            
            # Рассчитываем позицию
            padding = 20
            if position == "top-left":
                x, y = padding, padding
            elif position == "top-right":
                x = base_img.width - new_width - padding
                y = padding
            elif position == "bottom-left":
                x = padding
                y = base_img.height - new_height - padding
            elif position == "bottom-right":
                x = base_img.width - new_width - padding
                y = base_img.height - new_height - padding
            else:
                x, y = padding, padding
            
            # Накладываем с прозрачностью
            if opacity < 255:
                # Изменяем прозрачность
                if overlay_resized.mode == 'RGBA':
                    r, g, b, a = overlay_resized.split()
                    a = a.point(lambda p: p * opacity // 255)
                    overlay_resized = Image.merge('RGBA', (r, g, b, a))
            
            base_img.paste(overlay_resized, (x, y), overlay_resized)
            
            return base_img
        except Exception as e:
            st.error(f"Ошибка при наложении изображения: {str(e)}")
            return base_img

# ================ ФУНКЦИИ ИНТЕРФЕЙСА ================

def show_batch_processing_mode():
    """Режим массовой обработки с подстановкой данных"""
    
    st.header("📦 Массовая обработка с подстановкой данных")
    st.caption("Загрузите файл с данными и изображения для автоматической вставки информации")
    
    # Инициализация процессора
    if 'batch_processor' not in st.session_state:
        st.session_state.batch_processor = BatchProcessor()
    
    processor = st.session_state.batch_processor
    
    # Создаем вкладки
    tab1, tab2, tab3, tab4 = st.tabs([
        "📝 Текст", "🖼️ Изображение", "⚙️ Настройки", "📊 Результаты"
    ])
    
    with tab1:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("1. Загрузите файл с данными")
            data_file = st.file_uploader(
                "Загрузите CSV или Excel файл",
                type=["csv", "xlsx", "xls"],
                key="data_file"
            )
            
            if data_file:
                if processor.load_data_file(data_file):
                    st.dataframe(processor.data.head(10), use_container_width=True)
                    st.info(f"Всего записей: {len(processor.data)}")
            
            st.subheader("2. Загрузите изображения")
            image_files = st.file_uploader(
                "Загрузите изображения",
                type=["png", "jpg", "jpeg", "webp"],
                accept_multiple_files=True,
                key="batch_images"
            )
            
            if image_files:
                count = processor.load_images(image_files)
                st.success(f"Загружено {count} изображений")
        
        with col2:
            if data_file and image_files and processor.data is not None:
                st.subheader("3. Настройте соответствие")
                
                data_columns = processor.data.columns.tolist()
                
                match_column = st.selectbox(
                    "Колонка для сопоставления",
                    data_columns,
                    key="match_col",
                    help="Значения из этой колонки должны быть в именах файлов"
                )
                
                if st.button("🔄 Найти соответствия"):
                    matched = processor.create_mapping(match_column)
                    st.success(f"Найдено соответствий: {matched} из {len(processor.images)}")
                    
                    if matched > 0:
                        st.subheader("Примеры сопоставления:")
                        examples = []
                        for filename, idx in list(processor.mappings.items())[:3]:
                            row_data = processor.data.iloc[idx].to_dict()
                            examples.append({
                                "Файл": filename,
                                "Данные": row_data
                            })
                        st.json(examples)
    
    with tab2:
        if hasattr(processor, 'data') and processor.data is not None and len(processor.images) > 0:
            st.subheader("🖼️ Настройка вставки")
            
            col_i1, col_i2 = st.columns(2)
            
            with col_i1:
                # Выбор типа вставки
                insert_type = st.radio(
                    "Тип вставки",
                    ["Текст", "Изображение поверх", "Оставить как есть"],
                    horizontal=True
                )
                
                if insert_type == "Текст":
                    text_column = st.selectbox(
                        "Колонка с текстом",
                        processor.data.columns.tolist(),
                        key="text_col"
                    )
                    
                    prefix = st.text_input("Префикс", "")
                    suffix = st.text_input("Суффикс", "")
                    
                    text_position = st.selectbox(
                        "Позиция",
                        ["top-left", "top-center", "top-right", 
                         "center-left", "center", "center-right",
                         "bottom-left", "bottom-center", "bottom-right"],
                        key="text_pos"
                    )
                    
                    with st.expander("Дополнительно"):
                        font_size = st.slider("Размер шрифта", 10, 200, 40)
                        text_color = st.color_picker("Цвет текста", "#000000")
                        text_opacity = st.slider("Прозрачность", 0, 255, 255)
                        
                        add_bg = st.checkbox("Добавить фон")
                        if add_bg:
                            bg_color = st.color_picker("Цвет фона", "#FFFFFF")
                            bg_opacity = st.slider("Прозрачность фона", 0, 255, 200)
                
                elif insert_type == "Изображение поверх":
                    overlay_file = st.file_uploader(
                        "Загрузите изображение для наложения",
                        type=["png", "jpg", "jpeg"],
                        key="overlay_img"
                    )
                    
                    if overlay_file:
                        overlay_position = st.selectbox(
                            "Позиция",
                            ["top-left", "top-right", "bottom-left", "bottom-right"],
                            key="overlay_pos"
                        )
                        
                        overlay_size = st.slider("Размер (%)", 5, 50, 20) / 100
                        overlay_opacity = st.slider("Прозрачность", 0, 255, 255, key="overlay_opacity")
            
            with col_i2:
                # Предпросмотр
                if len(processor.images) > 0:
                    st.subheader("Предпросмотр")
                    preview_img = list(processor.images.values())[0].copy()
                    
                    if insert_type == "Текст" and 'text_column' in st.session_state and st.session_state.text_col:
                        if len(processor.mappings) > 0:
                            first_idx = list(processor.mappings.values())[0]
                            sample_text = str(processor.data.iloc[first_idx][st.session_state.text_col])
                            formatted_text = prefix + sample_text + suffix
                            
                            # Конвертируем цвет
                            rgb_color = tuple(int(text_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
                            bg_rgb = None
                            if add_bg:
                                bg_rgb = tuple(int(bg_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
                            
                            preview = processor.add_text_to_image(
                                preview_img, formatted_text, text_position, font_size, rgb_color,
                                text_opacity, 0, bg_rgb
                            )
                            st.image(preview, caption="Пример", use_container_width=True)
                    
                    elif insert_type == "Изображение поверх" and 'overlay_file' in locals() and overlay_file:
                        overlay_img = Image.open(overlay_file)
                        preview = processor.add_image_overlay(
                            preview_img, overlay_img, overlay_position, overlay_size, overlay_opacity
                        )
                        st.image(preview, caption="Пример", use_container_width=True)
                    
                    else:
                        st.image(preview_img, caption="Исходное изображение", use_container_width=True)
    
    with tab3:
        st.subheader("⚙️ Настройки обработки")
        
        col_s1, col_s2 = st.columns(2)
        
        with col_s1:
            output_format = st.selectbox(
                "Формат вывода",
                ["JPEG", "PNG", "WEBP"],
                key="batch_output"
            )
            
            quality = st.slider("Качество", 1, 100, 85, key="batch_quality")
            
            filename_template = st.text_input(
                "Шаблон имени файла",
                "{filename}_processed",
                help="Используйте {название_колонки} для подстановки"
            )
        
        with col_s2:
            resize_option = st.checkbox("Изменить размер", key="resize_check")
            if resize_option:
                col_w, col_h = st.columns(2)
                with col_w:
                    resize_width = st.number_input("Ширина", 100, 5000, 1000)
                with col_h:
                    resize_height = st.number_input("Высота", 100, 5000, 1000)
            
            auto_enhance = st.checkbox("Автоулучшение", key="batch_enhance")
    
    with tab4:
        st.subheader("📊 Результаты обработки")
        
        if st.button("🚀 ЗАПУСТИТЬ ОБРАБОТКУ", type="primary", use_container_width=True):
            
            if len(processor.mappings) == 0 and 'match_col' in st.session_state:
                processor.create_mapping(st.session_state.match_col)
            
            # Прогресс
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            processed_files = []
            total = len(processor.images)
            current = 0
            success_count = 0
            error_count = 0
            
            for filename, img in processor.images.items():
                try:
                    status_text.text(f"Обработка: {filename}")
                    
                    # Получаем данные для этого изображения
                    if filename in processor.mappings:
                        idx = processor.mappings[filename]
                        row_data = processor.data.iloc[idx].to_dict()
                    else:
                        row_data = {}
                    
                    current_img = img.copy()
                    
                    # Применяем настройки
                    if 'insert_type' in locals():
                        if insert_type == "Текст" and 'text_column' in st.session_state and st.session_state.text_col:
                            if st.session_state.text_col in row_data:
                                text_value = str(row_data[st.session_state.text_col])
                                formatted_text = prefix + text_value + suffix
                                
                                rgb_color = tuple(int(text_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
                                bg_rgb = None
                                if add_bg:
                                    bg_rgb = tuple(int(bg_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
                                
                                current_img = processor.add_text_to_image(
                                    current_img, formatted_text, text_position, font_size, rgb_color,
                                    text_opacity, 0, bg_rgb
                                )
                        
                        elif insert_type == "Изображение поверх" and 'overlay_file' in locals() and overlay_file:
                            overlay_img = Image.open(overlay_file)
                            current_img = processor.add_image_overlay(
                                current_img, overlay_img, overlay_position, overlay_size, overlay_opacity
                            )
                    
                    # Изменение размера
                    if 'resize_check' in st.session_state and st.session_state.resize_check:
                        current_img = current_img.resize((resize_width, resize_height), Image.Resampling.LANCZOS)
                    
                    # Автоулучшение
                    if 'batch_enhance' in st.session_state and st.session_state.batch_enhance:
                        enhancer = ImageEnhance.Contrast(current_img)
                        current_img = enhancer.enhance(1.1)
                        enhancer = ImageEnhance.Sharpness(current_img)
                        current_img = enhancer.enhance(1.2)
                    
                    # Сохраняем
                    img_bytes = io.BytesIO()
                    
                    if output_format == "JPEG" and current_img.mode == "RGBA":
                        current_img = current_img.convert('RGB')
                    
                    save_params = {'optimize': True}
                    if output_format in ["JPEG", "WEBP"]:
                        save_params['quality'] = quality
                    
                    current_img.save(img_bytes, format=output_format, **save_params)
                    
                    # Генерируем имя файла
                    try:
                        output_filename = filename_template.format(filename=os.path.splitext(filename)[0], **row_data)
                    except:
                        output_filename = f"processed_{filename}"
                    
                    if not output_filename.endswith(f".{output_format.lower()}"):
                        output_filename += f".{output_format.lower()}"
                    
                    processed_files.append((output_filename, img_bytes.getvalue()))
                    success_count += 1
                    
                except Exception as e:
                    st.error(f"Ошибка при обработке {filename}: {str(e)}")
                    error_count += 1
                
                current += 1
                progress_bar.progress(current / total)
            
            status_text.text("✅ Обработка завершена!")
            
            # Статистика
            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                st.metric("Успешно", success_count)
            with col_r2:
                st.metric("Ошибок", error_count)
            with col_r3:
                st.metric("Всего", total)
            
            # ZIP архив
            if processed_files:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for filename, data in processed_files:
                        zip_file.writestr(filename, data)
                
                zip_buffer.seek(0)
                
                st.download_button(
                    "📥 Скачать ZIP архив",
                    data=zip_buffer,
                    file_name=f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                    mime="application/zip",
                    use_container_width=True
                )

def show_basic_mode():
    """Базовый режим обработки"""
    st.header("🖼️ Базовая обработка изображений")
    
    uploaded_files = st.file_uploader(
        "Загрузите изображения",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        st.success(f"Загружено {len(uploaded_files)} файлов")
        
        if st.button("Обработать"):
            processed_files = []
            progress_bar = st.progress(0)
            
            for i, file in enumerate(uploaded_files):
                img = Image.open(file)
                
                # Базовая обработка
                if img.mode == 'RGBA':
                    img = ImageProcessor.add_white_background(img)
                
                # Сохраняем
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='JPEG', quality=85)
                processed_files.append((f"processed_{file.name}.jpg", img_bytes.getvalue()))
                
                progress_bar.progress((i + 1) / len(uploaded_files))
            
            # ZIP архив
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for filename, data in processed_files:
                    zip_file.writestr(filename, data)
            
            zip_buffer.seek(0)
            st.download_button("Скачать ZIP", data=zip_buffer, file_name="processed.zip")

# ================ ОСНОВНАЯ ФУНКЦИЯ ================

def main():
    st.title("🎨 PRO Студия для маркетплейсов")
    st.markdown("---")
    
    # Боковое меню
    with st.sidebar:
        st.header("📋 Меню")
        
        mode = st.radio(
            "Выберите режим",
            ["📦 Массовая обработка", "🖼️ Базовая обработка"]
        )
        
        st.markdown("---")
        st.caption("💡 Массовая обработка - вставка данных из CSV/Excel")
    
    # Вызов соответствующего режима
    if mode == "📦 Массовая обработка":
        show_batch_processing_mode()
    else:
        show_basic_mode()

# ================ ЗАПУСК ================

if __name__ == "__main__":
    main()
