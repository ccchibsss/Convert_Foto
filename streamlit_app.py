import streamlit as st
from PIL import Image, ImageEnhance, ImageOps, ImageDraw, ImageFilter, ImageChops, ImageFont
import io
import zipfile
import os
from datetime import datetime
import numpy as np
import math
import pandas as pd
import base64
import hashlib
import json
from pathlib import Path
import openpyxl

# ================ КЛАСС ДЛЯ МАССОВОЙ ОБРАБОТКИ С ДАННЫМИ ================

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
            self.images[file.name] = Image.open(file)
        return len(self.images)
    
    def create_mapping(self, data_column, filename_pattern):
        """Создание соответствия между изображениями и данными"""
        self.mappings = {}
        
        for filename, img in self.images.items():
            # Ищем соответствие по паттерну в имени файла
            for idx, row in self.data.iterrows():
                if str(row[data_column]) in filename or filename.startswith(str(row[data_column])):
                    self.mappings[filename] = idx
                    break
        
        return len(self.mappings)
    
    @staticmethod
    def add_text_to_image(img, text, position, font_size=None, color=(0, 0, 0), 
                         opacity=255, rotation=0, bg_color=None, padding=10):
        """Добавление текста на изображение с расширенными настройками"""
        
        # Создаем копию изображения
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        txt_layer = Image.new('RGBA', img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)
        
        # Определяем размер шрифта
        if font_size is None:
            font_size = min(img.size) // 20
        
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        # Получаем размер текста
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
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
        elif isinstance(position, dict) and 'x' in position and 'y' in position:
            # Абсолютные координаты
            x = position['x']
            y = position['y']
        else:
            x, y = padding, padding
        
        # Добавляем фон для текста если нужно
        if bg_color:
            bg_layer = Image.new('RGBA', (text_width + padding*2, text_height + padding*2), 
                                (*bg_color, opacity))
            txt_layer.paste(bg_layer, (x - padding, y - padding), bg_layer)
        
        # Рисуем текст
        text_color = (*color, opacity)
        draw.text((x, y), text, fill=text_color, font=font)
        
        # Поворачиваем если нужно
        if rotation != 0:
            txt_layer = txt_layer.rotate(rotation, expand=0, center=(x + text_width//2, y + text_height//2))
        
        # Накладываем на изображение
        result = Image.alpha_composite(img, txt_layer)
        
        return result
    
    @staticmethod
    def add_image_overlay(base_img, overlay_img, position, size_ratio=0.2, opacity=255):
        """Добавление изображения (логотипа, иконки) поверх основного"""
        
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
            alpha = overlay_resized.split()[3]
            alpha = alpha.point(lambda p: p * opacity // 255)
            overlay_resized.putalpha(alpha)
        
        base_img.paste(overlay_resized, (x, y), overlay_resized)
        
        return base_img
    
    @staticmethod
    def add_qr_code(base_img, data, position, size=100):
        """Добавление QR-кода (требуется библиотека qrcode)"""
        try:
            import qrcode
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(data)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_img = qr_img.resize((size, size), Image.Resampling.LANCZOS)
            
            if qr_img.mode != 'RGBA':
                qr_img = qr_img.convert('RGBA')
            
            padding = 20
            if position == "top-left":
                x, y = padding, padding
            elif position == "top-right":
                x = base_img.width - size - padding
                y = padding
            elif position == "bottom-left":
                x = padding
                y = base_img.height - size - padding
            elif position == "bottom-right":
                x = base_img.width - size - padding
                y = base_img.height - size - padding
            
            base_img.paste(qr_img, (x, y), qr_img)
            return base_img
        except ImportError:
            st.warning("Библиотека qrcode не установлена. QR-код не будет добавлен.")
            return base_img
    
    @staticmethod
    def add_barcode(base_img, data, position, barcode_type='code128', height=50):
        """Добавление штрих-кода (требуется библиотека python-barcode)"""
        try:
            import barcode
            from barcode.writer import ImageWriter
            
            # Создаем штрих-код
            barcode_class = barcode.get_barcode_class(barcode_type)
            barcode_img = barcode_class(data, writer=ImageWriter())
            
            # Сохраняем в байты
            barcode_bytes = io.BytesIO()
            barcode_img.write(barcode_bytes)
            barcode_bytes.seek(0)
            
            # Загружаем как изображение
            bc_img = Image.open(barcode_bytes)
            
            # Изменяем размер
            aspect = bc_img.width / bc_img.height
            new_width = int(height * aspect)
            bc_img = bc_img.resize((new_width, height), Image.Resampling.LANCZOS)
            
            if bc_img.mode != 'RGBA':
                bc_img = bc_img.convert('RGBA')
            
            padding = 20
            if position == "top-left":
                x, y = padding, padding
            elif position == "top-right":
                x = base_img.width - new_width - padding
                y = padding
            elif position == "bottom-left":
                x = padding
                y = base_img.height - height - padding
            elif position == "bottom-right":
                x = base_img.width - new_width - padding
                y = base_img.height - height - padding
            
            base_img.paste(bc_img, (x, y), bc_img)
            return base_img
        except ImportError:
            st.warning("Библиотека python-barcode не установлена. Штрих-код не будет добавлен.")
            return base_img

# ================ ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С ДАННЫМИ ================

class DataTemplate:
    """Шаблоны для различных типов данных"""
    
    @staticmethod
    def get_data_templates():
        return {
            "Товары (артикул, название, цена)": {
                "columns": ["Артикул", "Название", "Цена", "Бренд"],
                "description": "Стандартный шаблон для товаров"
            },
            "Автозапчасти": {
                "columns": ["Артикул", "Название", "OEM номер", "Производитель", "Цена", "Совместимость"],
                "description": "Для автозапчастей с OEM номерами"
            },
            "Одежда": {
                "columns": ["Артикул", "Название", "Размер", "Цвет", "Цена", "Состав"],
                "description": "Для одежды с размерами и цветами"
            },
            "Складской учет": {
                "columns": ["SKU", "Наименование", "Количество", "Стеллаж", "Ряд", "Ячейка"],
                "description": "Для складских этикеток"
            },
            "Маркетплейсы": {
                "columns": ["Артикул WB", "Артикул Ozon", "Название", "Цена", "Скидка %", "Рейтинг"],
                "description": "Для работы с несколькими маркетплейсами"
            }
        }
    
    @staticmethod
    def create_sample_data(template_name):
        """Создание примера данных для шаблона"""
        templates = {
            "Товары (артикул, название, цена)": pd.DataFrame({
                "Артикул": ["ART001", "ART002", "ART003"],
                "Название": ["Товар 1", "Товар 2", "Товар 3"],
                "Цена": ["1000", "2500", "5000"],
                "Бренд": ["Бренд A", "Бренд B", "Бренд A"]
            }),
            "Автозапчасти": pd.DataFrame({
                "Артикул": ["FL001", "BR002", "AM003"],
                "Название": ["Масляный фильтр", "Тормозные колодки", "Амортизатор"],
                "OEM номер": ["04152-38010", "04466-33260", "48510-80400"],
                "Производитель": ["Bosch", "TRW", "KYB"],
                "Цена": ["450", "3200", "5800"],
                "Совместимость": ["Toyota", "Honda", "Nissan"]
            })
        }
        return templates.get(template_name, pd.DataFrame())

# ================ ОСНОВНОЙ ИНТЕРФЕЙС ДЛЯ МАССОВОЙ ОБРАБОТКИ ================

def show_batch_processing_mode():
    """Режим массовой обработки с подстановкой данных"""
    
    st.header("📦 Массовая обработка с подстановкой данных")
    st.caption("Загрузите файл с данными и изображения для автоматической вставки информации")
    
    # Инициализация процессора
    if 'batch_processor' not in st.session_state:
        st.session_state.batch_processor = BatchProcessor()
    
    processor = st.session_state.batch_processor
    
    # Создаем вкладки для разных типов вставки
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📝 Текст", "🖼️ Изображение", "📊 QR-код", "📈 Штрих-код", "⚙️ Настройки"
    ])
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("1. Загрузите файл с данными")
        
        # Шаблоны данных
        data_template = DataTemplate()
        templates = data_template.get_data_templates()
        
        template_choice = st.selectbox(
            "Или выберите шаблон",
            ["Выберите шаблон"] + list(templates.keys())
        )
        
        if template_choice != "Выберите шаблон":
            st.info(templates[template_choice]["description"])
            if st.button("📥 Создать пример данных"):
                sample_df = data_template.create_sample_data(template_choice)
                csv = sample_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "Скачать пример CSV",
                    data=csv,
                    file_name=f"{template_choice}_example.csv",
                    mime="text/csv"
                )
        
        data_file = st.file_uploader(
            "Загрузите CSV или Excel файл с данными",
            type=["csv", "xlsx", "xls"],
            key="data_file"
        )
        
        if data_file:
            if processor.load_data_file(data_file):
                st.dataframe(processor.data.head(10), use_container_width=True)
                
                # Показываем статистику
                st.info(f"Всего записей: {len(processor.data)}")
        
        st.subheader("2. Загрузите изображения")
        image_files = st.file_uploader(
            "Загрузите изображения для обработки",
            type=["png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True,
            key="batch_images"
        )
        
        if image_files:
            count = processor.load_images(image_files)
            st.success(f"Загружено {count} изображений")
            
            # Предпросмотр первого изображения
            with st.expander("Предпросмотр загруженных изображений"):
                cols = st.columns(3)
                for i, (name, img) in enumerate(list(processor.images.items())[:6]):
                    with cols[i % 3]:
                        st.image(img, caption=name[:20], width=150)
    
    with col2:
        if data_file and image_files and len(processor.data) > 0:
            st.subheader("3. Настройте соответствие")
            
            # Выбор колонки для сопоставления
            st.markdown("**Сопоставление изображений с данными**")
            data_columns = processor.data.columns.tolist()
            
            match_column = st.selectbox(
                "Выберите колонку для сопоставления",
                data_columns,
                help="Значения из этой колонки должны присутствовать в именах файлов"
            )
            
            # Показываем примеры сопоставления
            if st.button("🔄 Проверить сопоставление"):
                matched = processor.create_mapping(match_column, "")
                st.success(f"Найдено соответствий: {matched} из {len(processor.images)}")
                
                # Показываем примеры
                examples = []
                for filename, idx in list(processor.mappings.items())[:5]:
                    examples.append({
                        "Файл": filename,
                        "Соответствие": dict(processor.data.iloc[idx])
                    })
                
                if examples:
                    st.json(examples)
    
    # Вкладки с настройками вставки
    if data_file and image_files and len(processor.data) > 0:
        
        with tab1:
            st.subheader("📝 Вставка текста из данных")
            
            col_t1, col_t2 = st.columns(2)
            
            with col_t1:
                text_column = st.selectbox(
                    "Выберите колонку с текстом",
                    processor.data.columns.tolist(),
                    key="text_col"
                )
                
                # Форматирование текста
                prefix = st.text_input("Префикс (перед текстом)", "")
                suffix = st.text_input("Суффикс (после текста)", "")
                
                # Позиция текста
                text_position = st.selectbox(
                    "Позиция текста",
                    ["top-left", "top-center", "top-right", 
                     "center-left", "center", "center-right",
                     "bottom-left", "bottom-center", "bottom-right"],
                    key="text_pos"
                )
                
                # Дополнительные настройки
                with st.expander("Дополнительные настройки текста"):
                    font_size = st.slider("Размер шрифта", 10, 200, 40)
                    text_color = st.color_picker("Цвет текста", "#000000")
                    text_opacity = st.slider("Прозрачность текста", 0, 255, 255)
                    text_rotation = st.slider("Поворот текста", 0, 360, 0)
                    
                    add_bg = st.checkbox("Добавить фон для текста")
                    if add_bg:
                        bg_color = st.color_picker("Цвет фона", "#FFFFFF")
                        bg_opacity = st.slider("Прозрачность фона", 0, 255, 200)
                    else:
                        bg_color = None
                        bg_opacity = None
            
            with col_t2:
                # Предпросмотр
                st.markdown("**Предпросмотр**")
                if len(processor.images) > 0:
                    preview_img = list(processor.images.values())[0].copy()
                    
                    # Берем первый пример данных
                    if len(processor.mappings) > 0:
                        first_idx = list(processor.mappings.values())[0]
                        sample_text = str(processor.data.iloc[first_idx][text_column])
                        
                        # Применяем форматирование
                        formatted_text = prefix + sample_text + suffix
                        
                        # Конвертируем цвет
                        rgb_color = tuple(int(text_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
                        bg_rgb = tuple(int(bg_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) if bg_color else None
                        
                        preview = processor.add_text_to_image(
                            preview_img, formatted_text, text_position, font_size, rgb_color,
                            text_opacity, text_rotation, bg_rgb if add_bg else None
                        )
                        st.image(preview, caption="Пример с первым изображением", use_container_width=True)
        
        with tab2:
            st.subheader("🖼️ Вставка изображения (логотип, иконка)")
            
            col_i1, col_i2 = st.columns(2)
            
            with col_i1:
                overlay_file = st.file_uploader(
                    "Загрузите изображение для наложения",
                    type=["png", "jpg", "jpeg"],
                    key="overlay_img"
                )
                
                if overlay_file:
                    overlay_img = Image.open(overlay_file)
                    st.image(overlay_img, caption="Накладываемое изображение", width=150)
                    
                    overlay_position = st.selectbox(
                        "Позиция наложения",
                        ["top-left", "top-right", "bottom-left", "bottom-right"],
                        key="overlay_pos"
                    )
                    
                    overlay_size = st.slider("Размер изображения (% от основного)", 5, 50, 20) / 100
                    overlay_opacity = st.slider("Прозрачность", 0, 255, 255, key="overlay_opacity")
            
            with col_i2:
                if overlay_file and len(processor.images) > 0:
                    preview_img = list(processor.images.values())[0].copy()
                    preview = processor.add_image_overlay(
                        preview_img, overlay_img, overlay_position, overlay_size, overlay_opacity
                    )
                    st.image(preview, caption="Предпросмотр", use_container_width=True)
        
        with tab3:
            st.subheader("📊 Генерация QR-кода из данных")
            
            col_q1, col_q2 = st.columns(2)
            
            with col_q1:
                qr_column = st.selectbox(
                    "Выберите колонку для QR-кода",
                    processor.data.columns.tolist(),
                    key="qr_col"
                )
                
                qr_position = st.selectbox(
                    "Позиция QR-кода",
                    ["top-left", "top-right", "bottom-left", "bottom-right"],
                    key="qr_pos"
                )
                
                qr_size = st.slider("Размер QR-кода", 50, 300, 100)
                
                qr_prefix = st.text_input("Префикс для QR-кода", "")
                qr_suffix = st.text_input("Суффикс для QR-кода", "")
            
            with col_q2:
                if len(processor.images) > 0:
                    preview_img = list(processor.images.values())[0].copy()
                    
                    if len(processor.mappings) > 0:
                        first_idx = list(processor.mappings.values())[0]
                        qr_data = qr_prefix + str(processor.data.iloc[first_idx][qr_column]) + qr_suffix
                        
                        preview = processor.add_qr_code(preview_img, qr_data, qr_position, qr_size)
                        st.image(preview, caption="Предпросмотр QR-кода", use_container_width=True)
        
        with tab4:
            st.subheader("📈 Генерация штрих-кода")
            
            col_b1, col_b2 = st.columns(2)
            
            with col_b1:
                barcode_column = st.selectbox(
                    "Выберите колонку для штрих-кода",
                    processor.data.columns.tolist(),
                    key="barcode_col"
                )
                
                barcode_type = st.selectbox(
                    "Тип штрих-кода",
                    ["code128", "ean13", "ean8", "upc", "isbn"],
                    key="barcode_type"
                )
                
                barcode_position = st.selectbox(
                    "Позиция штрих-кода",
                    ["top-left", "top-right", "bottom-left", "bottom-right"],
                    key="barcode_pos"
                )
                
                barcode_height = st.slider("Высота штрих-кода", 30, 150, 50)
        
        with tab5:
            st.subheader("⚙️ Общие настройки обработки")
            
            col_s1, col_s2 = st.columns(2)
            
            with col_s1:
                output_format = st.selectbox(
                    "Формат вывода",
                    ["JPEG", "PNG", "WEBP"],
                    key="batch_output"
                )
                
                quality = st.slider("Качество", 1, 100, 85, key="batch_quality")
                
                # Настройки имени файла
                filename_template = st.text_input(
                    "Шаблон имени файла",
                    "{артикул}_processed.jpg",
                    help="Используйте {название_колонки} для подстановки значений"
                )
            
            with col_s2:
                # Дополнительные трансформации
                st.checkbox("Применить ко всем изображениям", value=True, key="apply_to_all")
                
                resize_option = st.checkbox("Изменить размер", key="resize_check")
                if resize_option:
                    resize_width = st.number_input("Ширина", 100, 5000, 1000)
                    resize_height = st.number_input("Высота", 100, 5000, 1000)
                
                auto_enhance = st.checkbox("Автоулучшение", key="batch_enhance")
    
    # Кнопка запуска массовой обработки
    if data_file and image_files and len(processor.data) > 0:
        st.markdown("---")
        
        if st.button("🚀 ЗАПУСТИТЬ МАССОВУЮ ОБРАБОТКУ", type="primary", use_container_width=True):
            
            # Создаем соответствие если еще не создано
            if len(processor.mappings) == 0:
                processor.create_mapping(match_column, "")
            
            # Прогресс-бар
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            processed_files = []
            total = len(processor.images)
            current = 0
            
            # Статистика
            success_count = 0
            error_count = 0
            
            for filename, img in processor.images.items():
                try:
                    status_text.text(f"Обработка: {filename}")
                    
                    # Получаем данные для этого изображения
                    if filename in processor.mappings:
                        idx = processor.mappings[filename]
                        row_data = processor.data.iloc[idx]
                    else:
                        st.warning(f"Нет данных для {filename}, пропускаем")
                        current += 1
                        progress_bar.progress(current / total)
                        continue
                    
                    # Копируем изображение
                    current_img = img.copy()
                    
                    # Применяем настройки из вкладок
                    
                    # 1. Текст
                    if 'text_col' in st.session_state and st.session_state.text_col:
                        text_value = str(row_data[st.session_state.text_col])
                        formatted_text = prefix + text_value + suffix
                        
                        rgb_color = tuple(int(text_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
                        bg_rgb = tuple(int(bg_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) if 'bg_color' in locals() and add_bg else None
                        
                        current_img = processor.add_text_to_image(
                            current_img, formatted_text, text_position, font_size, rgb_color,
                            text_opacity if 'text_opacity' in locals() else 255,
                            text_rotation if 'text_rotation' in locals() else 0,
                            bg_rgb if add_bg else None
                        )
                    
                    # 2. Наложение изображения
                    if 'overlay_file' in locals() and overlay_file is not None:
                        current_img = processor.add_image_overlay(
                            current_img, overlay_img, overlay_position, overlay_size, overlay_opacity
                        )
                    
                    # 3. QR-код
                    if 'qr_column' in st.session_state and st.session_state.qr_column:
                        qr_data = qr_prefix + str(row_data[st.session_state.qr_column]) + qr_suffix
                        current_img = processor.add_qr_code(current_img, qr_data, qr_position, qr_size)
                    
                    # 4. Штрих-код
                    if 'barcode_column' in st.session_state and st.session_state.barcode_column:
                        barcode_data = str(row_data[st.session_state.barcode_column])
                        current_img = processor.add_barcode(current_img, barcode_data, barcode_position, barcode_type, barcode_height)
                    
                    # 5. Изменение размера
                    if 'resize_check' in st.session_state and st.session_state.resize_check:
                        current_img = current_img.resize((resize_width, resize_height), Image.Resampling.LANCZOS)
                    
                    # 6. Автоулучшение
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
                        output_filename = filename_template.format(**row_data.to_dict())
                    except:
                        # Если шаблон не работает, используем стандартное имя
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
            
            # Показываем статистику
            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                st.metric("Успешно обработано", success_count)
            with col_r2:
                st.metric("Ошибок", error_count)
            with col_r3:
                st.metric("Всего файлов", total)
            
            # Создаем ZIP архив
            if processed_files:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for filename, data in processed_files:
                        zip_file.writestr(filename, data)
                
                zip_buffer.seek(0)
                
                st.download_button(
                    "📥 Скачать все обработанные изображения (ZIP)",
                    data=zip_buffer,
                    file_name=f"batch_processed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                    mime="application/zip",
                    use_container_width=True
                )

# ================ ДОБАВЛЯЕМ В ОСНОВНОЕ МЕНЮ ================

def main():
    st.set_page_config(
        page_title="PRO Студия для маркетплейсов",
        page_icon="🎨",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🎨 PRO Студия для маркетплейсов")
    st.markdown("---")
    
    # Обновленное боковое меню
    with st.sidebar:
        st.header("📋 Меню")
        
        mode = st.radio(
            "Выберите режим работы",
            ["📦 МАССОВАЯ ОБРАБОТКА С ДАННЫМИ",  # Новый режим
             "🖼️ Базовая обработка", 
             "📸 Студийная обработка", 
             "📊 Инфографика", 
             "🔧 Автозапчасти", 
             "🏠 Интерьерные фото", 
             "📋 Готовые шаблоны"]
        )
        
        st.markdown("---")
        st.caption("💡 Массовая обработка позволяет вставлять данные из CSV/Excel в изображения")
    
    # Вызываем соответствующий режим
    if mode == "📦 МАССОВАЯ ОБРАБОТКА С ДАННЫМИ":
        show_batch_processing_mode()
    elif mode == "🖼️ Базовая обработка":
        show_basic_mode()
    elif mode == "📸 Студийная обработка":
        show_studio_mode()
    elif mode == "📊 Инфографика":
        show_infographic_mode()
    elif mode == "🔧 Автозапчасти":
        show_auto_parts_mode()
    elif mode == "🏠 Интерьерные фото":
        show_interior_mode()
    elif mode == "📋 Готовые шаблоны":
        show_templates_mode()

# ================ ЗАПУСК ПРИЛОЖЕНИЯ ================

if __name__ == "__main__":
    main()
