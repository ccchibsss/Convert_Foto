import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps
import io
import zipfile
from datetime import datetime
import os
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import multiprocessing
import threading
import queue
import json
import base64
import random
import math
from io import BytesIO
import psutil
import gc
import warnings
from pathlib import Path
import hashlib
import pickle
from functools import lru_cache
import cv2
from tqdm import tqdm
warnings.filterwarnings('ignore')

# ================ КОНФИГУРАЦИЯ СТРАНИЦЫ ================
st.set_page_config(
    page_title="🚀 MEGA Photo Editor ПРОФИ | 10000+ фото",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================ ОПТИМИЗАЦИЯ ПАМЯТИ ================
@st.cache_data(max_entries=50, ttl=3600)
def load_image_cached(image_bytes):
    """Кэширование загруженных изображений"""
    return Image.open(io.BytesIO(image_bytes)).convert('RGBA')

def optimize_image_memory(img, max_size=2000):
    """Оптимизация памяти изображения"""
    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        new_size = tuple(int(dim * ratio) for dim in img.size)
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    return img

def clear_memory():
    """Очистка памяти"""
    gc.collect()
    if hasattr(gc, 'garbage'):
        del gc.garbage[:]

# ================ ИНИЦИАЛИЗАЦИЯ СОСТОЯНИЯ ================
def init_session_state():
    """Инициализация состояния сессии"""
    # Изображения с кэшированием
    if 'images' not in st.session_state:
        st.session_state.images = []
    if 'image_hashes' not in st.session_state:
        st.session_state.image_hashes = {}
    if 'processed_images' not in st.session_state:
        st.session_state.processed_images = []
    if 'current_image_index' not in st.session_state:
        st.session_state.current_image_index = 0
    
    # Прогресс обработки
    if 'batch_queue' not in st.session_state:
        st.session_state.batch_queue = queue.Queue()
    if 'processing' not in st.session_state:
        st.session_state.processing = False
    if 'progress' not in st.session_state:
        st.session_state.progress = 0
    if 'total_files' not in st.session_state:
        st.session_state.total_files = 0
    if 'processed_count' not in st.session_state:
        st.session_state.processed_count = 0
    if 'failed_count' not in st.session_state:
        st.session_state.failed_count = 0
    
    # Настройки производительности
    if 'max_workers' not in st.session_state:
        cpu_count = multiprocessing.cpu_count()
        st.session_state.max_workers = min(cpu_count * 2, 32)
    if 'batch_size' not in st.session_state:
        st.session_state.batch_size = 100
    if 'memory_limit' not in st.session_state:
        st.session_state.memory_limit = psutil.virtual_memory().available // (1024 * 1024 * 1024)  # GB
    if 'use_gpu' not in st.session_state:
        st.session_state.use_gpu = check_gpu_available()
    
    # Остальные настройки (как в предыдущей версии)
    init_other_settings()

def init_other_settings():
    """Инициализация остальных настроек"""
    # Данные из Excel
    if 'excel_data' not in st.session_state:
        st.session_state.excel_data = None
    if 'excel_df' not in st.session_state:
        st.session_state.excel_df = None
    if 'selected_columns' not in st.session_state:
        st.session_state.selected_columns = []
    if 'data_elements' not in st.session_state:
        st.session_state.data_elements = []
    
    # Настройки фона
    if 'background_type' not in st.session_state:
        st.session_state.background_type = 'color'
    if 'background_color' not in st.session_state:
        st.session_state.background_color = '#667eea'
    if 'background_gradient' not in st.session_state:
        st.session_state.background_gradient = {
            'type': 'linear',
            'colors': ['#667eea', '#764ba2'],
            'angle': 45
        }
    if 'background_pattern' not in st.session_state:
        st.session_state.background_pattern = 'dots'
    if 'background_image' not in st.session_state:
        st.session_state.background_image = None
    if 'background_opacity' not in st.session_state:
        st.session_state.background_opacity = 1.0
    if 'background_blur' not in st.session_state:
        st.session_state.background_blur = 0
    
    # Настройки изображения
    if 'canvas_width' not in st.session_state:
        st.session_state.canvas_width = 1200
    if 'canvas_height' not in st.session_state:
        st.session_state.canvas_height = 1200
    if 'maintain_aspect' not in st.session_state:
        st.session_state.maintain_aspect = True
    if 'image_position' not in st.session_state:
        st.session_state.image_position = 'center'
    if 'image_scale' not in st.session_state:
        st.session_state.image_scale = 1.0
    if 'image_rotation' not in st.session_state:
        st.session_state.image_rotation = 0
    if 'image_offset_x' not in st.session_state:
        st.session_state.image_offset_x = 0
    if 'image_offset_y' not in st.session_state:
        st.session_state.image_offset_y = 0
    
    # Настройки текста
    if 'text_settings' not in st.session_state:
        st.session_state.text_settings = {
            'font_family': 'Montserrat',
            'font_size': 36,
            'font_color': '#FFFFFF',
            'bold': False,
            'italic': False,
            'alignment': 'center',
            'opacity': 1.0,
            'shadow': False,
            'shadow_color': '#000000',
            'shadow_offset': 3
        }
    
    # UI состояние
    if 'selected_element' not in st.session_state:
        st.session_state.selected_element = None
    if 'mouse_mode' not in st.session_state:
        st.session_state.mouse_mode = 'move'
    if 'show_grid' not in st.session_state:
        st.session_state.show_grid = True
    if 'snap_to_grid' not in st.session_state:
        st.session_state.snap_to_grid = True
    if 'grid_size' not in st.session_state:
        st.session_state.grid_size = 50

def check_gpu_available():
    """Проверка доступности GPU"""
    try:
        import torch
        return torch.cuda.is_available()
    except:
        return False

# ================ РАЗМЕРЫ ДЛЯ МАРКЕТПЛЕЙСОВ ================
MARKETPLACE_SIZES = {
    'Ozon': {
        'Главное фото': (1200, 1200),
        'Инфографика': (1200, 1800),
        'Галерея': (1000, 1000),
        'Баннер': (1920, 600)
    },
    'Wildberries': {
        'Главное фото': (900, 1200),
        'Инфографика': (900, 1200),
        'Галерея': (900, 900),
        'Баннер': (1280, 200)
    },
    'Яндекс Маркет': {
        'Главное фото': (1000, 1000),
        'Инфографика': (1000, 1333),
        'Галерея': (1000, 1000),
        'Баннер': (1920, 400)
    }
}

# ================ ОПТИМИЗИРОВАННЫЕ ФУНКЦИИ ОБРАБОТКИ ================
@lru_cache(maxsize=128)
def get_cached_font(font_family, font_size, bold, italic):
    """Кэширование шрифтов"""
    try:
        font_map = {
            'Montserrat': 'Montserrat-Regular.ttf',
            'Arial': 'arial.ttf',
            'Roboto': 'Roboto-Regular.ttf'
        }
        if bold:
            font_map['Montserrat'] = 'Montserrat-Bold.ttf'
        if italic:
            font_map['Montserrat'] = 'Montserrat-Italic.ttf'
        
        return ImageFont.truetype(font_map.get(font_family, 'arial.ttf'), font_size)
    except:
        return ImageFont.load_default()

def create_background_optimized(width, height, settings):
    """Оптимизированное создание фона"""
    background_type = settings.get('type', 'color')
    
    if background_type == 'color':
        color = settings.get('color', '#667eea')
        if isinstance(color, str) and color.startswith('#'):
            rgb_color = hex_to_rgb(color)
            return Image.new('RGBA', (width, height), (*rgb_color, 255))
        return Image.new('RGBA', (width, height), color)
    
    elif background_type == 'gradient':
        return create_gradient_background_optimized(width, height, settings.get('gradient', {}))
    
    elif background_type == 'pattern':
        return create_pattern_background_optimized(width, height, settings)
    
    elif background_type == 'image' and settings.get('image'):
        bg_img = settings['image'].copy()
        bg_img = bg_img.resize((width, height), Image.Resampling.LANCZOS)
        return bg_img
    
    return Image.new('RGBA', (width, height), (255, 255, 255, 255))

def create_gradient_background_optimized(width, height, gradient_settings):
    """Оптимизированное создание градиента с использованием numpy"""
    try:
        import numpy as np
        
        colors = gradient_settings.get('colors', ['#667eea', '#764ba2'])
        rgb_colors = [hex_to_rgb(c) for c in colors]
        
        # Создаем градиент с помощью numpy
        gradient = np.zeros((height, width, 3), dtype=np.uint8)
        
        if gradient_settings.get('type', 'linear') == 'linear':
            for i, color in enumerate(rgb_colors):
                pos = i / (len(rgb_colors) - 1) if len(rgb_colors) > 1 else 0
                pos_x = int(pos * width)
                gradient[:, pos_x:pos_x+1] = color
        
        else:  # radial
            center_x, center_y = width / 2, height / 2
            Y, X = np.ogrid[:height, :width]
            dist = np.sqrt((X - center_x)**2 + (Y - center_y)**2)
            max_dist = np.sqrt(center_x**2 + center_y**2)
            t = dist / max_dist
            
            for i in range(3):
                gradient[:,:,i] = (rgb_colors[0][i] * (1 - t) + rgb_colors[-1][i] * t).astype(np.uint8)
        
        return Image.fromarray(gradient, 'RGB').convert('RGBA')
    
    except ImportError:
        # Fallback к стандартной реализации
        return create_gradient_background_standard(width, height, gradient_settings)

def create_pattern_background_optimized(width, height, settings):
    """Оптимизированное создание паттерна"""
    pattern_type = settings.get('pattern', 'dots')
    color = hex_to_rgb(settings.get('pattern_color', '#667eea'))
    bg_color = hex_to_rgb(settings.get('bg_color', '#FFFFFF'))
    
    img = Image.new('RGBA', (width, height), (*bg_color, 255))
    
    if pattern_type == 'dots':
        draw = ImageDraw.Draw(img)
        size = 50
        for x in range(0, width, size):
            for y in range(0, height, size):
                draw.ellipse([x-5, y-5, x+5, y+5], fill=(*color, 255))
    
    return img

def resize_image_batch(images, target_size):
    """Пакетное изменение размера изображений"""
    try:
        import cv2
        import numpy as np
        
        processed = []
        for img in images:
            img_np = np.array(img)
            resized = cv2.resize(img_np, target_size, interpolation=cv2.INTER_LANCZOS4)
            processed.append(Image.fromarray(resized))
        
        return processed
    
    except ImportError:
        return [img.resize(target_size, Image.Resampling.LANCZOS) for img in images]

# ================ ОПТИМИЗИРОВАННАЯ ПАКЕТНАЯ ОБРАБОТКА ================
def process_batch_chunk(chunk_data):
    """Обработка чанка изображений"""
    chunk, bg_settings, image_settings, data_elements, excel_df, start_idx = chunk_data
    
    results = []
    for i, (filename, image_bytes) in enumerate(chunk):
        try:
            # Оптимизированная загрузка
            main_img = load_image_cached(image_bytes)
            
            # Применяем настройки
            target_width = image_settings.get('canvas_width', 1200)
            target_height = image_settings.get('canvas_height', 1200)
            
            # Создаем фон (кешируем для чанка)
            bg_img = create_background_optimized(target_width, target_height, bg_settings)
            
            # Обрабатываем изображение
            processed_img = resize_image_with_settings_optimized(main_img, target_width, target_height, image_settings)
            
            # Комбинируем
            result = bg_img.copy()
            result.paste(processed_img, (0, 0), processed_img)
            
            # Добавляем элементы данных
            if data_elements:
                draw = ImageDraw.Draw(result)
                for element in data_elements:
                    if excel_df is not None and element['column'] in excel_df.columns:
                        try:
                            value = excel_df[element['column']].iloc[(start_idx + i) % len(excel_df)]
                            element['value'] = str(value)
                        except:
                            pass
                    
                    render_element_optimized(draw, element)
            
            # Сохраняем с оптимизацией
            output = io.BytesIO()
            result.save(output, format='PNG', optimize=True, compress_level=6)
            output.seek(0)
            
            results.append((f"processed_{start_idx + i:06d}_{filename}", output.getvalue()))
            
            # Очистка памяти
            if i % 10 == 0:
                clear_memory()
        
        except Exception as e:
            results.append((filename, None, str(e)))
    
    return results

def resize_image_with_settings_optimized(img, target_width, target_height, settings):
    """Оптимизированное изменение размера"""
    position = settings.get('image_position', 'center')
    scale = settings.get('image_scale', 1.0)
    
    if position == 'stretch':
        return img.resize((target_width, target_height), Image.Resampling.LANCZOS)
    
    elif position == 'fit':
        img.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)
        return img
    
    else:  # center
        new_width = int(img.width * scale)
        new_height = int(img.height * scale)
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        canvas = Image.new('RGBA', (target_width, target_height), (0, 0, 0, 0))
        x = (target_width - new_width) // 2
        y = (target_height - new_height) // 2
        canvas.paste(img, (x, y), img)
        return canvas

def render_element_optimized(draw, element):
    """Оптимизированная отрисовка элемента"""
    x, y = element['x'], element['y']
    width, height = element['width'], element['height']
    
    # Фон
    if element.get('background'):
        bg_color = hex_to_rgb(element['background'])
        draw.rounded_rectangle(
            [x, y, x + width, y + height],
            radius=element.get('border_radius', 15),
            fill=(*bg_color, int(255 * element.get('opacity', 1.0)))
        )
    
    # Текст
    text = str(element['value'])
    font = get_cached_font(
        element.get('font_family', 'Montserrat'),
        element.get('font_size', 36),
        element.get('bold', False),
        element.get('italic', False)
    )
    
    # Получаем размер текста
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Позиция
    alignment = element.get('alignment', 'center')
    if alignment == 'left':
        text_x = x + 15
    elif alignment == 'right':
        text_x = x + width - text_width - 15
    else:
        text_x = x + (width - text_width) // 2
    
    text_y = y + (height - text_height) // 2
    
    # Текст
    font_color = hex_to_rgb(element.get('font_color', '#FFFFFF'))
    draw.text((text_x, text_y), text, font=font, fill=(*font_color, 255))

def process_10000_images_parallel(images, bg_settings, image_settings, data_elements, excel_df):
    """Параллельная обработка 10000 изображений"""
    total = len(images)
    chunk_size = min(100, total // (st.session_state.max_workers * 2) + 1)
    
    # Подготовка данных
    image_data = [(img.name, img.getvalue()) for img in images]
    chunks = [image_data[i:i + chunk_size] for i in range(0, len(image_data), chunk_size)]
    
    # Прогресс
    progress_bar = st.progress(0)
    status_text = st.empty()
    time_text = st.empty()
    
    processed = []
    failed = []
    
    start_time = time.time()
    
    # Используем ProcessPoolExecutor для максимальной производительности
    with ProcessPoolExecutor(max_workers=min(st.session_state.max_workers, 16)) as executor:
        chunk_data = [
            (chunk, bg_settings, image_settings, data_elements, excel_df, i * chunk_size)
            for i, chunk in enumerate(chunks)
        ]
        
        futures = {executor.submit(process_batch_chunk, data): i for i, data in enumerate(chunk_data)}
        
        completed = 0
        for future in as_completed(futures):
            try:
                chunk_results = future.result(timeout=300)
                for result in chunk_results:
                    if len(result) == 2:  # Успех
                        processed.append(result)
                    else:  # Ошибка
                        failed.append(result[0])
                
                completed += 1
                progress = completed / len(chunks)
                progress_bar.progress(progress)
                
                elapsed = time.time() - start_time
                remaining = (elapsed / completed) * (len(chunks) - completed) if completed > 0 else 0
                
                status_text.text(f"✅ Обработано: {len(processed)} | ❌ Ошибок: {len(failed)}")
                time_text.text(f"⏱️ Прошло: {format_time(elapsed)} | Осталось: {format_time(remaining)}")
                
            except Exception as e:
                st.error(f"Ошибка в чанке: {str(e)}")
    
    return processed, failed

def format_time(seconds):
    """Форматирование времени"""
    if seconds < 60:
        return f"{int(seconds)} сек"
    elif seconds < 3600:
        return f"{int(seconds // 60)} мин {int(seconds % 60)} сек"
    else:
        return f"{int(seconds // 3600)} ч {int((seconds % 3600) // 60)} мин"

# ================ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ================
def hex_to_rgb(hex_color):
    """Преобразование HEX в RGB"""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    elif len(hex_color) != 6:
        hex_color = '667eea'
    
    try:
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except:
        return (102, 126, 234)

def create_gradient_background_standard(width, height, gradient_settings):
    """Стандартное создание градиента (запасной вариант)"""
    img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    colors = gradient_settings.get('colors', ['#667eea', '#764ba2'])
    rgb_colors = [hex_to_rgb(c) for c in colors]
    
    for y in range(height):
        t = y / height
        r = int(rgb_colors[0][0] * (1 - t) + rgb_colors[-1][0] * t)
        g = int(rgb_colors[0][1] * (1 - t) + rgb_colors[-1][1] * t)
        b = int(rgb_colors[0][2] * (1 - t) + rgb_colors[-1][2] * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
    
    return img

# ================ БОКОВАЯ ПАНЕЛЬ ================
def render_sidebar():
    """Отрисовка боковой панели"""
    with st.sidebar:
        st.markdown("### 🚀 МАССОВАЯ ОБРАБОТКА")
        
        # Настройки производительности
        with st.expander("⚡ Производительность", expanded=True):
            cpu_count = multiprocessing.cpu_count()
            st.session_state.max_workers = st.slider(
                "Потоков обработки",
                1, min(32, cpu_count * 2),
                st.session_state.max_workers,
                help="Больше потоков = быстрее, но больше нагрузка на CPU"
            )
            
            st.session_state.batch_size = st.slider(
                "Размер пакета",
                10, 500,
                st.session_state.batch_size,
                10,
                help="Изображений в одном пакете"
            )
            
            memory_gb = psutil.virtual_memory().available / (1024**3)
            st.metric("Доступно памяти", f"{memory_gb:.1f} GB")
            
            if check_gpu_available():
                st.success("✅ GPU доступен")
            else:
                st.info("ℹ️ Используется CPU")
        
        # Остальные вкладки
        tabs = st.tabs(["📷 Изображение", "🎨 Фон", "📊 Данные", "✏️ Текст"])
        
        with tabs[0]:
            render_image_tab()
        with tabs[1]:
            render_background_tab()
        with tabs[2]:
            render_data_tab()
        with tabs[3]:
            render_text_tab()
        
        st.markdown("---")
        
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("🧹 Очистить все", use_container_width=True):
                st.session_state.images = []
                st.session_state.data_elements = []
                st.rerun()
        
        with col_b2:
            if st.button("🚀 СТАРТ", type="primary", use_container_width=True):
                return True
        
        return False

def render_image_tab():
    """Вкладка настроек изображения"""
    st.markdown("#### 📐 Размер холста")
    
    marketplace = st.selectbox(
        "Размер для маркетплейса",
        list(MARKETPLACE_SIZES.keys()) + ["Пользовательский"],
        key="marketplace_size"
    )
    
    if marketplace != "Пользовательский":
        size_type = st.selectbox("Тип", list(MARKETPLACE_SIZES[marketplace].keys()), key="size_type")
        w, h = MARKETPLACE_SIZES[marketplace][size_type]
        st.session_state.canvas_width = w
        st.session_state.canvas_height = h
        st.success(f"✅ {w} x {h}")
    
    col_w, col_h = st.columns(2)
    with col_w:
        st.session_state.canvas_width = st.number_input("Ширина", 100, 5000, st.session_state.canvas_width, 10)
    with col_h:
        st.session_state.canvas_height = st.number_input("Высота", 100, 5000, st.session_state.canvas_height, 10)
    
    st.session_state.image_position = st.radio(
        "Позиция",
        ["center", "fit", "stretch"],
        format_func=lambda x: {
            "center": "🎯 По центру",
            "fit": "📏 Вписать",
            "stretch": "🔍 Растянуть"
        }[x]
    )

def render_background_tab():
    """Вкладка фона"""
    bg_type = st.radio(
        "Тип фона",
        ["Однотонный", "Градиент", "Паттерн", "Изображение"],
        horizontal=True
    )
    
    type_map = {
        "Однотонный": "color",
        "Градиент": "gradient",
        "Паттерн": "pattern",
        "Изображение": "image"
    }
    
    st.session_state.background_type = type_map[bg_type]
    
    if st.session_state.background_type == 'color':
        st.session_state.background_color = st.color_picker("Цвет", st.session_state.background_color)

def render_data_tab():
    """Вкладка данных"""
    st.markdown("#### 📥 Загрузка Excel")
    
    excel_file = st.file_uploader("Excel файл", type=['xlsx', 'xls', 'csv'])
    
    if excel_file:
        try:
            if excel_file.name.endswith('.csv'):
                df = pd.read_csv(excel_file)
            else:
                df = pd.read_excel(excel_file)
            
            st.session_state.excel_df = df
            st.success(f"✅ {len(df)} строк, {len(df.columns)} колонок")
            
            selected_cols = st.multiselect(
                "Колонки для отображения",
                df.columns.tolist(),
                key="columns_select"
            )
            
            st.session_state.selected_columns = selected_cols
            
            if selected_cols and st.button("➕ Добавить на холст"):
                for col in selected_cols:
                    element = create_data_element(
                        str(df[col].iloc[0]),
                        col,
                        len(st.session_state.data_elements),
                        {
                            'x': 100 + len(st.session_state.data_elements) * 30,
                            'y': 100 + len(st.session_state.data_elements) * 30,
                            'width': 300,
                            'height': 80,
                            'font_size': 36,
                            'font_color': '#FFFFFF',
                            'background': '#667eea'
                        }
                    )
                    st.session_state.data_elements.append(element)
                st.rerun()
        
        except Exception as e:
            st.error(f"Ошибка: {str(e)}")

def render_text_tab():
    """Вкладка текста"""
    st.session_state.text_settings['font_size'] = st.slider(
        "Размер шрифта", 10, 120,
        st.session_state.text_settings.get('font_size', 36)
    )
    
    st.session_state.text_settings['font_color'] = st.color_picker(
        "Цвет текста",
        st.session_state.text_settings.get('font_color', '#FFFFFF')
    )

def create_data_element(value, column, index, settings):
    """Создание элемента данных"""
    return {
        'id': f"element_{index}_{datetime.now().timestamp()}",
        'value': value,
        'column': column,
        'index': index,
        'x': settings.get('x', 100),
        'y': settings.get('y', 100),
        'width': settings.get('width', 300),
        'height': settings.get('height', 80),
        'font_size': settings.get('font_size', 36),
        'font_color': settings.get('font_color', '#FFFFFF'),
        'background': settings.get('background', None),
        'border_radius': settings.get('border_radius', 15),
        'opacity': settings.get('opacity', 1.0),
        'alignment': settings.get('alignment', 'center')
    }

# ================ ОСНОВНАЯ ОБЛАСТЬ ================
def render_main_area():
    """Отрисовка основной области"""
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 📸 Загрузка изображений")
        
        uploaded_files = st.file_uploader(
            "Выберите изображения",
            type=['png', 'jpg', 'jpeg', 'webp'],
            accept_multiple_files=True,
            key="image_uploader"
        )
        
        if uploaded_files:
            st.session_state.images = uploaded_files
            st.session_state.total_files = len(uploaded_files)
            
            total_size = sum(len(f.getvalue()) for f in uploaded_files) / (1024 * 1024)
            
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                st.metric("Всего файлов", len(uploaded_files))
            with col_m2:
                st.metric("Общий размер", f"{total_size:.1f} MB")
            with col_m3:
                avg_size = total_size / len(uploaded_files) if uploaded_files else 0
                st.metric("Средний размер", f"{avg_size:.1f} MB")
            
            # Предпросмотр
            if len(uploaded_files) > 0:
                st.markdown("#### 👁️ Предпросмотр")
                preview_idx = st.slider("Изображение", 0, len(uploaded_files)-1, 0)
                preview_img = Image.open(uploaded_files[preview_idx])
                st.image(preview_img, caption=uploaded_files[preview_idx].name, use_column_width=True)
    
    with col2:
        st.markdown("### 🎨 Элементы на холсте")
        
        if st.session_state.get('data_elements'):
            for i, element in enumerate(st.session_state.data_elements):
                with st.container():
                    col_e1, col_e2, col_e3 = st.columns([3, 1, 1])
                    with col_e1:
                        st.info(f"📌 {element['column']}")
                    with col_e2:
                        if st.button("✏️", key=f"edit_{i}"):
                            st.session_state.selected_element = i
                    with col_e3:
                        if st.button("🗑️", key=f"del_{i}"):
                            st.session_state.data_elements.pop(i)
                            st.rerun()
        else:
            st.info("Нет элементов. Добавьте данные из Excel")

# ================ ОСНОВНАЯ ФУНКЦИЯ ================
def main():
    """Главная функция"""
    st.markdown("## 🚀 MEGA Photo Editor ПРОФИ")
    st.markdown("### Массовая обработка до 10000 изображений")
    
    init_session_state()
    start_processing = render_sidebar()
    render_main_area()
    
    if start_processing and st.session_state.get('images'):
        total_images = len(st.session_state.images)
        
        if total_images > 10000:
            st.warning(f"⚠️ Загружено {total_images} изображений. Обработка может занять много времени.")
        
        with st.spinner(f"🔄 Обработка {total_images} изображений..."):
            # Настройки
            bg_settings = {
                'type': st.session_state.background_type,
                'color': st.session_state.background_color,
                'gradient': st.session_state.background_gradient,
                'pattern': st.session_state.background_pattern,
                'bg_color': getattr(st.session_state, 'pattern_bg_color', '#FFFFFF'),
                'image': st.session_state.background_image
            }
            
            image_settings = {
                'canvas_width': st.session_state.canvas_width,
                'canvas_height': st.session_state.canvas_height,
                'image_position': st.session_state.image_position,
                'image_scale': st.session_state.image_scale
            }
            
            # Обработка
            start_time = time.time()
            
            processed, failed = process_10000_images_parallel(
                st.session_state.images,
                bg_settings,
                image_settings,
                st.session_state.data_elements,
                st.session_state.excel_df
            )
            
            total_time = time.time() - start_time
            
            # Результаты
            st.markdown("### 📊 Результаты")
            
            col_r1, col_r2, col_r3, col_r4 = st.columns(4)
            with col_r1:
                st.metric("Всего", total_images)
            with col_r2:
                st.metric("✅ Успешно", len(processed))
            with col_r3:
                st.metric("❌ Ошибки", len(failed))
            with col_r4:
                speed = len(processed) / total_time if total_time > 0 else 0
                st.metric("Скорость", f"{speed:.1f} фото/сек")
            
            st.info(f"⏱️ Общее время: {format_time(total_time)}")
            
            # Создание ZIP
            if processed:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for filename, data in tqdm(processed, desc="Создание ZIP"):
                        zip_file.writestr(filename, data)
                
                zip_buffer.seek(0)
                
                st.download_button(
                    "📥 Скачать все фото (ZIP)",
                    data=zip_buffer,
                    file_name=f"processed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                    mime="application/zip",
                    use_container_width=True
                )
                
                # Статистика
                total_size_mb = sum(len(data) for _, data in processed) / (1024 * 1024)
                st.success(f"✅ Общий размер: {total_size_mb:.1f} MB")
            
            if failed:
                st.error(f"❌ Ошибки в {len(failed)} файлах")
                with st.expander("Показать список ошибок"):
                    for f in failed[:20]:
                        st.text(f"• {f}")
                    if len(failed) > 20:
                        st.text(f"... и еще {len(failed) - 20}")

if __name__ == "__main__":
    main()
