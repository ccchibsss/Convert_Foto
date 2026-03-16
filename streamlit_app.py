import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps
import io
import zipfile
from datetime import datetime
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import queue
import json
import base64
import random
import math
from io import BytesIO

# ================ КОНФИГУРАЦИЯ СТРАНИЦЫ ================
st.set_page_config(
    page_title="⚡ MEGA Photo Editor ПРОФИ",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================ РАСШИРЕННЫЕ CSS СТИЛИ ================
st.markdown("""
<style>
    /* Импорт шрифтов */
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Roboto:wght@300;400;700&display=swap');
    * {
        font-family: 'Montserrat', sans-serif;
    }
    /* Основной заголовок */
    .main-header {
        font-size: 4rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #ff6b6b 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
        padding: 2rem;
        animation: neonPulse 3s ease-in-out infinite;
        text-shadow: 0 0 30px rgba(102, 126, 234, 0.5);
    }
    @keyframes neonPulse {
        0%, 100% { filter: drop-shadow(0 0 20px rgba(102, 126, 234, 0.5)); }
        50% { filter: drop-shadow(0 0 50px rgba(255, 107, 107, 0.8)); }
    }
    /* Боковая панель с градиентом */
    .sidebar-gradient {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 25px;
        border-radius: 30px;
        margin: 15px 0;
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 20px 40px rgba(0,0,0,0.3);
    }
    /* Карточки инструментов */
    .tool-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 20px;
        margin: 15px 0;
        transition: all 0.3s ease;
        cursor: pointer;
        color: white;
        position: relative;
        overflow: hidden;
    }
    .tool-card::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
        animation: rotate 10s linear infinite;
        opacity: 0;
        transition: opacity 0.3s ease;
    }
    .tool-card:hover::before { opacity: 1; }
    .tool-card:hover {
        transform: translateY(-5px) scale(1.02);
        border-color: #667eea;
        box-shadow: 0 30px 60px rgba(102, 126, 234, 0.3);
    }
    .tool-card.active {
        border: 3px solid #ff6b6b;
        background: rgba(255, 107, 107, 0.1);
    }
    /* Область для работы с фоном */
    .background-workspace {
        background: #2a2a3a;
        border-radius: 30px;
        padding: 30px;
        margin: 20px 0;
        position: relative;
        min-height: 400px;
        border: 2px dashed #667eea;
        cursor: crosshair;
    }
    /* Элементы данных из Excel */
    .data-element {
        position: absolute;
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(5px);
        border-radius: 15px;
        padding: 15px;
        border: 2px solid #667eea;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        cursor: move;
        user-select: none;
        transition: all 0.2s ease;
        color: #333;
        font-weight: 600;
        min-width: 150px;
        text-align: center;
    }
    .data-element:hover {
        transform: scale(1.05);
        box-shadow: 0 20px 40px rgba(102, 126, 234, 0.4);
        border-color: #ff6b6b;
    }
    .data-element.selected {
        border: 4px solid #ff6b6b;
        background: rgba(255, 255, 255, 1);
    }
    /* Ресайз хендлы */
    .resize-handle {
        position: absolute;
        width: 15px;
        height: 15px;
        background: #667eea;
        border: 2px solid white;
        border-radius: 50%;
        z-index: 1000;
    }
    .resize-handle.nw { top: -7px; left: -7px; cursor: nw-resize; }
    .resize-handle.ne { top: -7px; right: -7px; cursor: ne-resize; }
    .resize-handle.sw { bottom: -7px; left: -7px; cursor: sw-resize; }
    .resize-handle.se { bottom: -7px; right: -7px; cursor: se-resize; }
    /* Цветовая палитра */
    .color-picker-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 10px;
        margin: 15px 0;
    }
    .color-swatch {
        width: 100%;
        aspect-ratio: 1;
        border-radius: 10px;
        cursor: pointer;
        border: 2px solid transparent;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .color-swatch:hover {
        transform: scale(1.1);
        border-color: white;
        box-shadow: 0 0 30px currentColor;
    }
    .color-swatch.selected {
        border: 4px solid #ff6b6b;
        transform: scale(1.05);
    }
    .color-swatch::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(135deg, transparent 50%, rgba(255,255,255,0.1) 100%);
    }
    /* Градиентные пресеты */
    .gradient-preview {
        height: 60px;
        border-radius: 15px;
        margin: 10px 0;
        cursor: pointer;
        border: 2px solid transparent;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .gradient-preview:hover {
        transform: translateY(-5px);
        border-color: white;
        box-shadow: 0 20px 40px rgba(0,0,0,0.3);
    }
    .gradient-preview.selected {
        border: 4px solid #ff6b6b;
    }
    /* Паттерны */
    .pattern-preview {
        width: 60px;
        height: 60px;
        border-radius: 15px;
        background-size: cover;
        cursor: pointer;
        border: 2px solid transparent;
        transition: all 0.3s ease;
    }
    .pattern-preview:hover {
        transform: scale(1.1) rotate(5deg);
        border-color: white;
    }
    .pattern-preview.selected {
        border: 4px solid #ff6b6b;
    }
    /* Управление мышью */
    .mouse-controls {
        background: rgba(0, 0, 0, 0.3);
        border-radius: 60px;
        padding: 20px 30px;
        display: flex;
        gap: 30px;
        justify-content: center;
        margin: 30px 0;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .mouse-button {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 10px;
        color: white;
        font-size: 14px;
    }
    .mouse-icon {
        width: 60px;
        height: 60px;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 30px;
        transition: all 0.3s ease;
    }
    .mouse-icon.active {
        background: #667eea;
        box-shadow: 0 0 30px #667eea;
        transform: scale(1.1);
    }
    /* Таблица данных */
    .excel-data-table {
        background: rgba(0, 0, 0, 0.2);
        border-radius: 20px;
        padding: 15px;
        max-height: 300px;
        overflow-y: auto;
    }
    .data-row {
        display: flex;
        gap: 10px;
        padding: 10px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        cursor: pointer;
        transition: all 0.3s ease;
        color: white;
    }
    .data-row:hover {
        background: rgba(102, 126, 234, 0.3);
        transform: translateX(10px);
    }
    .data-row.selected {
        background: rgba(255, 107, 107, 0.3);
        border-left: 4px solid #ff6b6b;
    }
    .data-cell {
        flex: 1;
        padding: 5px;
    }
</style>
""", unsafe_allow_html=True)

# ================ ИНИЦИАЛИЗАЦИЯ СОСТОЯНИЯ ================
def init_session_state():
    """Инициализация состояния сессии"""
    # Изображения
    if 'images' not in st.session_state:
        st.session_state.images = []
    if 'processed_images' not in st.session_state:
        st.session_state.processed_images = []
    if 'current_image_index' not in st.session_state:
        st.session_state.current_image_index = 0
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
        st.session_state.background_type = 'color'  # color, gradient, pattern, image
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
    # Настройки текста
    if 'text_settings' not in st.session_state:
        st.session_state.text_settings = {
            'font_family': 'Montserrat',
            'font_size': 24,
            'font_color': '#FFFFFF',
            'bold': False,
            'italic': False,
            'alignment': 'center',
            'opacity': 1.0
        }
    # UI состояние
    if 'selected_element' not in st.session_state:
        st.session_state.selected_element = None
    if 'mouse_mode' not in st.session_state:
        st.session_state.mouse_mode = 'move'  # move, resize, rotate
    if 'show_grid' not in st.session_state:
        st.session_state.show_grid = False
    if 'snap_to_grid' not in st.session_state:
        st.session_state.snap_to_grid = True
    if 'grid_size' not in st.session_state:
        st.session_state.grid_size = 20
    # Пакетная обработка
    if 'batch_queue' not in st.session_state:
        st.session_state.batch_queue = queue.Queue()
    if 'processing' not in st.session_state:
        st.session_state.processing = False
    if 'progress' not in st.session_state:
        st.session_state.progress = 0
    if 'total_files' not in st.session_state:
        st.session_state.total_files = 0

# ================ ЦВЕТОВЫЕ ПАЛИТРЫ ================
COLOR_PALETTES = {
    'modern': ['#667eea', '#764ba2', '#ff6b6b', '#4ecdc4', '#45b7d1'],
    'pastel': ['#FFB6C1', '#E6E6FA', '#98D8C8', '#FFF0F5', '#E0BBE4'],
    'vibrant': ['#FF3366', '#33FF99', '#3366FF', '#FFCC33', '#FF66CC'],
    'earth': ['#8B4513', '#D2691E', '#CD853F', '#DEB887', '#F4A460'],
    'ocean': ['#006994', '#0077BE', '#48D1CC', '#40E0D0', '#AFEEEE'],
    'sunset': ['#FF4500', '#FF6347', '#FF7F50', '#FF8C69', '#FFA07A'],
    'forest': ['#228B22', '#32CD32', '#6B8E23', '#9ACD32', '#ADFF2F'],
    'royal': ['#4B0082', '#800080', '#9370DB', '#BA55D3', '#DA70D6']
}

# ================ ГРАДИЕНТНЫЕ ПРЕСЕТЫ ================
GRADIENT_PRESETS = {
    'sunset': {
        'colors': ['#FF512F', '#DD2476'],
        'angle': 45,
        'name': 'Закат'
    },
    'ocean': {
        'colors': ['#2193b0', '#6dd5ed'],
        'angle': 135,
        'name': 'Океан'
    },
    'purple': {
        'colors': ['#8E2DE2', '#4A00E0'],
        'angle': 90,
        'name': 'Фиолетовый'
    },
    'green': {
        'colors': ['#11998e', '#38ef7d'],
        'angle': 45,
        'name': 'Зеленый'
    },
    'orange': {
        'colors': ['#F09819', '#FF512F'],
        'angle': 135,
        'name': 'Оранжевый'
    },
    'rainbow': {
        'colors': ['#FF0000', '#FF7F00', '#FFFF00', '#00FF00', '#0000FF', '#4B0082', '#9400D3'],
        'angle': 45,
        'name': 'Радуга'
    },
    'neon': {
        'colors': ['#12c2e9', '#c471ed', '#f64f59'],
        'angle': 90,
        'name': 'Неон'
    },
    'gold': {
        'colors': ['#FFD700', '#FFA500', '#FF8C00'],
        'angle': 45,
        'name': 'Золото'
    }
}

# ================ ПАТТЕРНЫ ================
PATTERNS = {
    'dots': '🔵 Точки',
    'lines': '📏 Линии',
    'grid': '🔲 Сетка',
    'stripes': '📊 Полосы',
    'chevron': '⚡ Шеврон',
    'circles': '⭕ Круги',
    'squares': '⬜ Квадраты',
    'triangles': '🔺 Треугольники',
    'hexagons': '⬡ Шестиугольники',
    'stars': '⭐ Звезды'
}

# ================ ШРИФТЫ ================
FONT_FAMILIES = {
    'Montserrat': 'Современный',
    'Playfair Display': 'Классический',
    'Roboto': 'Универсальный',
    'Arial': 'Стандартный',
    'Times New Roman': 'Деловой',
    'Courier New': 'Печатный',
    'Impact': 'Жирный',
    'Comic Sans': 'Дружелюбный'
}

# ===================== ФУНКЦИИ =====================
def create_background(width, height, settings):
    """Создание фона на основе настроек"""
    background_type = settings.get('type', 'color')
    if background_type == 'color':
        return Image.new('RGBA', (width, height), settings.get('color', '#667eea'))
    elif background_type == 'gradient':
        return create_gradient_background(width, height, settings.get('gradient', {}))
    elif background_type == 'pattern':
        return create_pattern_background(width, height, settings.get('pattern', 'dots'),
                                         settings.get('pattern_color', '#667eea'),
                                         settings.get('bg_color', '#FFFFFF'))
    elif background_type == 'image' and settings.get('image'):
        bg_img = settings['image'].copy()
        bg_img = bg_img.resize((width, height), Image.Resampling.LANCZOS)
        if settings.get('blur', 0) > 0:
            bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=settings['blur']))
        if settings.get('opacity', 1.0) < 1.0:
            alpha = bg_img.getchannel('L')
            alpha = alpha.point(lambda p: int(p * settings['opacity']))
            bg_img.putalpha(alpha)
        return bg_img
    return Image.new('RGBA', (width, height), '#FFFFFF')

def create_gradient_background(width, height, gradient_settings):
    """Создание градиентного фона"""
    gradient_type = gradient_settings.get('type', 'linear')
    colors = gradient_settings.get('colors', ['#667eea', '#764ba2'])
    angle = gradient_settings.get('angle', 45)
    img = Image.new('RGBA', (width, height))
    draw = ImageDraw.Draw(img)
    if gradient_type == 'linear':
        rad = math.radians(angle)
        dx = math.cos(rad)
        dy = math.sin(rad)
        for i in range(width):
            t = (i / width)
            color = interpolate_colors(colors, t)
            draw.line((i, 0, i, height), fill=color)
    elif gradient_type == 'radial':
        center_x, center_y = width / 2, height / 2
        max_dist = math.hypot(center_x, center_y)
        for y in range(height):
            for x in range(width):
                dist = math.hypot(x - center_x, y - center_y)
                t = dist / max_dist
                color = interpolate_colors(colors, t)
                draw.point((x, y), fill=color)
    return img

def interpolate_colors(colors, t):
    """Интерполяция цветов по t"""
    if len(colors) == 1:
        return colors[0]
    if len(colors) == 2:
        c1 = hex_to_rgb(colors[0])
        c2 = hex_to_rgb(colors[1])
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        return (r, g, b)
    n = len(colors)
    idx = int(t * (n - 1))
    t_local = t * (n - 1) - idx
    c1 = hex_to_rgb(colors[idx])
    c2 = hex_to_rgb(colors[min(idx + 1, n - 1)])
    r = int(c1[0] + (c2[0] - c1[0]) * t_local)
    g = int(c1[1] + (c2[1] - c1[1]) * t_local)
    b = int(c1[2] + (c2[2] - c1[2]) * t_local)
    return (r, g, b)

def create_pattern_background(width, height, pattern_type, color, bg_color):
    """Создание фона с паттерном"""
    img = Image.new('RGBA', (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    pattern_color = hex_to_rgb(color)
    size = 40
    if pattern_type == 'dots':
        for x in range(0, width, size):
            for y in range(0, height, size):
                draw.ellipse([x-3, y-3, x+3, y+3], fill=pattern_color)
    elif pattern_type == 'lines':
        for x in range(0, width, size//2):
            draw.line([(x, 0), (x, height)], fill=pattern_color, width=2)
    elif pattern_type == 'grid':
        for x in range(0, width, size):
            draw.line([(x, 0), (x, height)], fill=pattern_color, width=1)
        for y in range(0, height, size):
            draw.line([(0, y), (width, y)], fill=pattern_color, width=1)
    elif pattern_type == 'stripes':
        for i in range(-height, width, size):
            draw.line([(i, 0), (i + height, height)], fill=pattern_color, width=5)
    elif pattern_type == 'chevron':
        for x in range(-size, width, size):
            for y in range(0, height, size):
                points = [
                    (x, y + size//2),
                    (x + size//2, y),
                    (x + size, y + size//2),
                    (x + size//2, y + size)
                ]
                draw.polygon(points, outline=pattern_color)
    elif pattern_type == 'circles':
        for x in range(0, width, size):
            for y in range(0, height, size):
                draw.ellipse([x, y, x+size-5, y+size-5], outline=pattern_color, width=2)
    elif pattern_type == 'squares':
        for x in range(0, width, size):
            for y in range(0, height, size):
                draw.rectangle([x, y, x+size-5, y+size-5], outline=pattern_color, width=2)
    elif pattern_type == 'triangles':
        for x in range(0, width, size):
            for y in range(0, height, size):
                points = [
                    (x + size//2, y),
                    (x, y + size),
                    (x + size, y + size)
                ]
                draw.polygon(points, outline=pattern_color)
    elif pattern_type == 'hexagons':
        for x in range(0, width, int(size * 0.866)):
            for y in range(0, height, size):
                points = []
                for i in range(6):
                    angle = math.pi / 6 + i * math.pi / 3
                    px = x + size * math.cos(angle)
                    py = y + size * math.sin(angle)
                    points.append((px, py))
                draw.polygon(points, outline=pattern_color)
    elif pattern_type == 'stars':
        for x in range(0, width, size):
            for y in range(0, height, size):
                points = []
                for i in range(5):
                    angle = i * 4 * math.pi / 5 - math.pi / 2
                    px = x + size//2 + (size//2) * math.cos(angle)
                    py = y + size//2 + (size//2) * math.sin(angle)
                    points.append((px, py))
                    angle2 = (i + 0.5) * 4 * math.pi / 5 - math.pi / 2
                    px2 = x + size//2 + (size//4) * math.cos(angle2)
                    py2 = y + size//2 + (size//4) * math.sin(angle2)
                    points.append((px2, py2))
                draw.polygon(points, outline=pattern_color)
    return img

def hex_to_rgb(hex_color):
    """Преобразование HEX в RGB"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb):
    """Преобразование RGB в HEX"""
    return '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])

# ================ ФУНКЦИИ ДЛЯ РАБОТЫ С ДАННЫМИ ИЗ EXCEL ================
def load_excel_data(file):
    """Загрузка данных из Excel"""
    try:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        return df
    except Exception as e:
        st.error(f"Ошибка загрузки Excel: {str(e)}")
        return None

def create_data_element(value, column_name, index, settings):
    """Создание элемента данных для наложения"""
    return {
        'id': f"element_{index}_{datetime.now().timestamp()}",
        'value': str(value),
        'column': column_name,
        'index': index,
        'x': settings.get('x', 100),
        'y': settings.get('y', 100),
        'width': settings.get('width', 200),
        'height': settings.get('height', 60),
        'font_family': settings.get('font_family', 'Montserrat'),
        'font_size': settings.get('font_size', 24),
        'font_color': settings.get('font_color', '#FFFFFF'),
        'bold': settings.get('bold', False),
        'italic': settings.get('italic', False),
        'alignment': settings.get('alignment', 'center'),
        'opacity': settings.get('opacity', 1.0),
        'background': settings.get('background', None),
        'border': settings.get('border', None),
        'border_radius': settings.get('border_radius', 10),
        'rotation': settings.get('rotation', 0)
    }

def render_data_element(draw, element, x, y, width, height):
    """Отрисовка элемента данных на изображении"""
    # Рисуем фон элемента
    if element.get('background'):
        bg_color = hex_to_rgb(element['background'])
        draw.rounded_rectangle(
            [x, y, x + width, y + height],
            radius=element.get('border_radius', 10),
            fill=(*bg_color, int(255 * element.get('opacity', 1.0)))
        )
    # Рамка
    if element.get('border'):
        border_color = hex_to_rgb(element['border']['color'])
        border_width = element['border'].get('width', 2)
        for i in range(border_width):
            draw.rounded_rectangle(
                [x + i, y + i, x + width - i, y + height - i],
                radius=element.get('border_radius', 10),
                outline=(*border_color, 255)
            )
    # Текст
    text = element['value']
    font_family = element.get('font_family', 'Montserrat')
    font_size = element.get('font_size', 24)
    font_color = hex_to_rgb(element.get('font_color', '#FFFFFF'))
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    # Размер текста
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    # Выравнивание
    alignment = element.get('alignment', 'center')
    if alignment == 'left':
        text_x = x + 10
    elif alignment == 'right':
        text_x = x + width - text_width - 10
    else:
        text_x = x + (width - text_width) // 2
    text_y = y + (height - text_height) // 2
    # Рисуем текст
    draw.text((text_x, text_y), text, font=font, fill=(*font_color, 255))

# ================ ФУНКЦИИ ДЛЯ ПАКЕТНОЙ ОБРАБОТКИ ================
def process_single_image_with_data(image_data, background_settings, data_elements, excel_df):
    """Обработка одного изображения с наложением данных"""
    try:
        filename, image_bytes = image_data
        main_img = Image.open(io.BytesIO(image_bytes)).convert('RGBA')
        bg_img = create_background(main_img.width, main_img.height, background_settings)
        if background_settings.get('type') != 'image':
            result = bg_img.copy()
            result.paste(main_img, (0, 0), main_img)
        else:
            result = bg_img.copy()
            x = (result.width - main_img.width) // 2
            y = (result.height - main_img.height) // 2
            result.paste(main_img, (x, y), main_img)
        draw = ImageDraw.Draw(result)
        for element in data_elements:
            # Обновление значения из df, если нужно
            if excel_df is not None and element['column'] in excel_df.columns:
                value = excel_df[element['column']].iloc[0]
                element['value'] = str(value)
            render_data_element(
                draw,
                element,
                element['x'],
                element['y'],
                element['width'],
                element['height']
            )
        output = io.BytesIO()
        result.save(output, format='PNG', quality=95, optimize=True)
        output.seek(0)
        new_filename = f"processed_{filename}"
        if not new_filename.lower().endswith('.png'):
            new_filename = new_filename.rsplit('.', 1)[0] + '.png'
        return (new_filename, output.getvalue())
    except Exception as e:
        st.error(f"Ошибка обработки {filename}: {str(e)}")
        return None

def process_batch_parallel(images, background_settings, data_elements, excel_df, max_workers=10):
    """Параллельная обработка пакета изображений"""
    total = len(images)
    processed = []
    failed = []
    # подготовка данных
    image_data = [(img.name, img.getvalue()) for img in images]
    progress_bar = st.progress(0)
    status_text = st.empty()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_single_image_with_data, data, background_settings, data_elements, excel_df): data[0] for data in image_data}
        completed = 0
        for future in as_completed(futures):
            filename = futures[future]
            try:
                result = future.result(timeout=60)
                if result:
                    processed.append(result)
                else:
                    failed.append(filename)
            except Exception as e:
                failed.append(filename)
            completed += 1
            progress = completed / total
            progress_bar.progress(progress)
            status_text.text(f"🔄 Обработано: {completed}/{total} | ✅ Успешно: {len(processed)} | ❌ Ошибок: {len(failed)}")
    return processed, failed

# ================ БОКОВАЯ ПАНЕЛЬ ================
def render_sidebar():
    """Отрисовка боковой панели с настройками"""
    with st.sidebar:
        st.markdown('<div class="sidebar-gradient">', unsafe_allow_html=True)
        st.markdown("### 🎨 ПАНЕЛЬ УПРАВЛЕНИЯ")
        st.markdown('</div>', unsafe_allow_html=True)
        tab_bg, tab_data, tab_text, tab_settings = st.tabs(["🎨 Фон", "📊 Данные", "📝 Текст", "⚙️ Настройки"])
        with tab_bg:
            render_background_tab()
        with tab_data:
            render_data_tab()
        with tab_text:
            render_text_tab()
        with tab_settings:
            render_settings_tab()
        st.markdown("---")
        if st.button("🚀 ПРИМЕНИТЬ КО ВСЕМ", type="primary", use_container_width=True):
            return True
        return False

def render_background_tab():
    """Вкладка настроек фона"""
    bg_type = st.radio("Тип фона", ["Однотонный", "Градиент", "Паттерн", "Изображение"], horizontal=True, key="bg_type_radio")
    bg_type_map = {
        "Однотонный": "color",
        "Градиент": "gradient",
        "Паттерн": "pattern",
        "Изображение": "image"
    }
    st.session_state.background_type = bg_type_map[bg_type]
    if st.session_state.background_type == 'color':
        render_color_background()
    elif st.session_state.background_type == 'gradient':
        render_gradient_background()
    elif st.session_state.background_type == 'pattern':
        render_pattern_background()
    elif st.session_state.background_type == 'image':
        render_image_background()

    # Общие настройки
    st.markdown("#### ✨ Эффекты фона")
    st.session_state.background_opacity = st.slider("Прозрачность", 0.0, 1.0, st.session_state.background_opacity, 0.1, key="bg_opacity_slider")
    st.session_state.background_blur = st.slider("Размытие", 0, 20, st.session_state.background_blur, 1, key="bg_blur_slider")

def render_color_background():
    """Настройки однотонного фона"""
    st.markdown("#### 🎨 Выберите цвет")
    palette_name = st.selectbox("Палитра", list(COLOR_PALETTES.keys()), index=0, format_func=lambda x: x.capitalize(), key="palette_select")
    cols = st.columns(5)
    for i, color in enumerate(COLOR_PALETTES[palette_name][:5]):
        with cols[i]:
            is_selected = st.session_state.background_color == color
            st.markdown(f"""
            <div class="color-swatch {'selected' if is_selected else ''}" 
                 style="background: {color};"
                 onclick="alert('color_{color}')">
            </div>
            """, unsafe_allow_html=True)
            if st.button("✓", key=f"color_button_{color}", help=color):
                st.session_state.background_color = color
                st.rerun()
    st.session_state.background_color = st.color_picker("Точный цвет", st.session_state.background_color, key="bg_color_picker")

def render_gradient_background():
    """Настройки градиентного фона"""
    st.markdown("#### 🌈 Готовые градиенты")
    for preset_id, preset in GRADIENT_PRESETS.items():
        is_selected = st.session_state.background_gradient.get('preset') == preset_id
        gradient_css = f"linear-gradient({preset['angle']}deg, {', '.join(preset['colors'])})"
        st.markdown(f"""
        <div class="gradient-preview {'selected' if is_selected else ''}" 
             style="background: {gradient_css};"
             onclick="alert('gradient_{preset_id}')">
            <div style="padding: 15px; color: white; text-shadow: 0 2px 5px black;">
                {preset['name']}
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button(f"📌 {preset['name']}", key=f"gradient_btn_{preset_id}", use_container_width=True):
            st.session_state.background_gradient = {
                'type': 'linear',
                'colors': preset['colors'],
                'angle': preset['angle'],
                'preset': preset_id
            }
            st.rerun()

    st.markdown("#### ✏️ Свой градиент")
    grad_type = st.radio("Тип", ["Линейный", "Радиальный"], horizontal=True, key="grad_type_radio")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        color1 = st.color_picker("Цвет 1", st.session_state.background_gradient.get('colors', ['#667eea', '#764ba2'])[0], key="grad_color1")
    with col_c2:
        color2 = st.color_picker("Цвет 2", st.session_state.background_gradient.get('colors', ['#667eea', '#764ba2'])[1], key="grad_color2")
    if st.checkbox("➕ Добавить цвет", key="add_color_checkbox"):
        color3 = st.color_picker("Цвет 3", "#ff6b6b", key="grad_color3")
        colors = [color1, color2, color3]
    else:
        colors = [color1, color2]
    if grad_type == "Линейный":
        angle = st.slider("Угол", 0, 360, st.session_state.background_gradient.get('angle', 45), key="grad_angle")
    else:
        angle = 0
    st.session_state.background_gradient = {
        'type': 'linear' if grad_type == "Линейный" else 'radial',
        'colors': colors,
        'angle': angle
    }

def render_pattern_background():
    """Настройки паттерна"""
    st.markdown("#### 🔷 Выберите паттерн")
    pattern_cols = st.columns(3)
    for i, (pattern_id, pattern_name) in enumerate(PATTERNS.items()):
        with pattern_cols[i % 3]:
            is_selected = st.session_state.background_pattern == pattern_id
            st.markdown(f"""
            <div class="pattern-preview {'selected' if is_selected else ''}"
                 style="background: linear-gradient(45deg, #667eea, #764ba2); display: flex; align-items: center; justify-content: center; color: white;"
                 onclick="alert('pattern_{pattern_id}')">
                {pattern_name.split()[0]}
            </div>
            """, unsafe_allow_html=True)
            if st.button(pattern_name, key=f"pattern_{pattern_id}", use_container_width=True):
                st.session_state.background_pattern = pattern_id
                st.rerun()
    st.markdown("#### 🎨 Цвета паттерна")
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        pattern_color = st.color_picker("Цвет узора", "#667eea", key="pattern_color_picker")
    with col_p2:
        bg_color = st.color_picker("Цвет фона", "#FFFFFF", key="pattern_bg_color_picker")
    st.session_state.pattern_color = pattern_color
    st.session_state.pattern_bg_color = bg_color

def render_image_background():
    """Настройки фона из изображения"""
    st.markdown("#### 🖼️ Загрузите фоновое изображение")
    bg_image = st.file_uploader("Выберите изображение для фона", type=['png', 'jpg', 'jpeg', 'webp'], key="bg_image_uploader")
    if bg_image:
        st.session_state.background_image = Image.open(bg_image)
        st.success(f"✅ Загружено: {bg_image.name}")

# ==================== Вкладки с данными ====================
def render_data_tab():
    """Вкладка работы с данными из Excel"""
    st.markdown("#### 📊 Загрузка данных из Excel")
    excel_file = st.file_uploader("Выберите Excel файл", type=['xlsx', 'xls', 'csv'], key="excel_uploader")
    if excel_file:
        df = load_excel_data(excel_file)
        if df is not None:
            st.session_state.excel_df = df
            st.success(f"✅ Загружено: {len(df)} строк, {len(df.columns)} колонок")
            with st.expander("👁️ Превью данных"):
                st.dataframe(df.head(10), use_container_width=True)
            st.markdown("#### 📌 Выберите колонки для отображения")
            selected_cols = st.multiselect("Колонки", df.columns.tolist(), default=st.session_state.selected_columns, key="columns_multiselect")
            st.session_state.selected_columns = selected_cols
            if selected_cols:
                st.markdown("#### ⚙️ Настройки отображения")
                for col in selected_cols:
                    with st.expander(f"📋 {col}"):
                        sample_value = df[col].iloc[0]
                        st.info(f"Пример: {sample_value}")
                        st.markdown("**Позиция** (будет задана мышкой)")
                        col_w, col_h = st.columns(2)
                        with col_w:
                            width = st.number_input(f"Ширина", 50, 500, 200, key=f"w_{col}")
                        with col_h:
                            height = st.number_input(f"Высота", 30, 300, 60, key=f"h_{col}")
                        col_s1, col_s2 = st.columns(2)
                        with col_s1:
                            font_size = st.slider("Размер шрифта", 10, 72, 24, key=f"fs_{col}")
                            bold = st.checkbox("Жирный", key=f"bold_{col}")
                        with col_s2:
                            alignment = st.selectbox("Выравнивание", ["left", "center", "right"], index=1, key=f"align_{col}")
                            italic = st.checkbox("Курсив", key=f"italic_{col}")
                        col_c1, col_c2 = st.columns(2)
                        with col_c1:
                            text_color = st.color_picker("Цвет текста", "#FFFFFF", key=f"tc_{col}")
                        with col_c2:
                            bg_color = st.color_picker("Цвет фона", "#FFFFFF", key=f"bgc_{col}")
                        border = st.checkbox("Добавить рамку", key=f"border_{col}")
                        if border:
                            col_b1, col_b2 = st.columns(2)
                            with col_b1:
                                border_color = st.color_picker("Цвет рамки", "#667eea", key=f"bc_{col}")
                            with col_b2:
                                border_width = st.slider("Толщина", 1, 5, 2, key=f"bw_{col}")
                        if st.button(f"➕ Добавить {col} на холст", key=f"add_{col}"):
                            element = create_data_element(
                                sample_value,
                                col,
                                len(st.session_state.data_elements),
                                {
                                    'x': 100 + len(st.session_state.data_elements) * 50,
                                    'y': 100 + len(st.session_state.data_elements) * 50,
                                    'width': width,
                                    'height': height,
                                    'font_size': font_size,
                                    'font_color': text_color,
                                    'bold': bold,
                                    'italic': italic,
                                    'alignment': alignment,
                                    'background': bg_color if bg_color else None,
                                    'border': {
                                        'color': border_color,
                                        'width': border_width
                                    } if border else None
                                }
                            )
                            st.session_state.data_elements.append(element)
                            st.success(f"✅ Элемент {col} добавлен!")
                            st.rerun()

# ==================== Вкладка с настройками текста ====================
def render_text_tab():
    """Вкладка настроек текста"""
    st.markdown("#### 📝 Настройки текста по умолчанию")
    # Семейство шрифтов
    st.session_state.text_settings['font_family'] = st.selectbox(
        "Семейство шрифтов",
        list(FONT_FAMILIES.keys()),
        format_func=lambda x: f"{x} ({FONT_FAMILIES[x]})",
        index=list(FONT_FAMILIES.keys()).index(st.session_state.text_settings.get('font_family', 'Montserrat')),
        key="font_family_selectbox"
    )
    # Размер шрифта
    st.session_state.text_settings['font_size'] = st.slider(
        "Размер шрифта", 8, 72, st.session_state.text_settings.get('font_size', 24),
        key="font_size_slider"
    )
    # Цвет текста
    st.session_state.text_settings['font_color'] = st.color_picker(
        "Цвет текста", st.session_state.text_settings.get('font_color', '#FFFFFF'),
        key="font_color_picker"
    )
    col_st1, col_st2, col_st3 = st.columns(3)
    with col_st1:
        st.session_state.text_settings['bold'] = st.checkbox(
            "Жирный", st.session_state.text_settings.get('bold', False),
            key="bold_checkbox"
        )
    with col_st2:
        st.session_state.text_settings['italic'] = st.checkbox(
            "Курсив", st.session_state.text_settings.get('italic', False),
            key="italic_checkbox"
        )
    with col_st3:
        st.session_state.text_settings['underline'] = st.checkbox(
            "Подчеркнутый", st.session_state.text_settings.get('underline', False),
            key="underline_checkbox"
        )
    # Выравнивание
    st.session_state.text_settings['alignment'] = st.radio(
        "Выравнивание", ["left", "center", "right"],
        index=["left", "center", "right"].index(st.session_state.text_settings.get('alignment', 'center')),
        horizontal=True,
        key="alignment_radio"
    )
    # Прозрачность
    st.session_state.text_settings['opacity'] = st.slider(
        "Прозрачность", 0.0, 1.0, st.session_state.text_settings.get('opacity', 1.0),
        0.1,
        key="opacity_slider"
    )

# ==================== Основные настройки ====================
def render_settings_tab():
    """Вкладка общих настроек"""
    st.markdown("#### 🖱️ Управление мышью")
    mouse_mode = st.radio("Режим мыши", ["✋ Перемещение", "📏 Изменение размера", "🔄 Поворот"], horizontal=True, index=0, key="mouse_mode_radio")
    mouse_mode_map = {
        "✋ Перемещение": "move",
        "📏 Изменение размера": "resize",
        "🔄 Поворот": "rotate"
    }
    st.session_state.mouse_mode = mouse_mode_map[mouse_mode]
    st.markdown(f"""
<div class="mouse-controls">
    <div class="mouse-button">
        <div class="mouse-icon {'active' if st.session_state.mouse_mode == 'move' else ''}">✋</div>
        <span>ЛКМ - перетащить</span>
    </div>
    <div class="mouse-button">
        <div class="mouse-icon {'active' if st.session_state.mouse_mode == 'resize' else ''}">📏</div>
        <span>Колесо - размер</span>
    </div>
    <div class="mouse-button">
        <div class="mouse-icon {'active' if st.session_state.mouse_mode == 'rotate' else ''}">🔄</div>
        <span>Alt + колесо - поворот</span>
    </div>
</div>
""", unsafe_allow_html=True)
    st.markdown("#### 📐 Сетка и направляющие")
    st.session_state.show_grid = st.checkbox("Показать сетку", st.session_state.show_grid, key="show_grid_checkbox")
    st.session_state.snap_to_grid = st.checkbox("Провязка к сетке", st.session_state.snap_to_grid, key="snap_to_grid_checkbox")
    if st.session_state.show_grid:
        st.session_state.grid_size = st.slider("Размер сетки", 10, 100, st.session_state.grid_size, 5, key="grid_size_slider")
    st.markdown("#### ⚡ Производительность")
    max_workers = st.slider("Параллельных потоков", 1, 20, 10, key="max_workers_slider")
    quality = st.slider("Качество JPEG", 50, 100, 95, key="quality_slider")
    st.session_state.max_workers = max_workers
    st.session_state.quality = quality

# ==================== Основная область ====================
def render_main_area():
    """Отрисовка основной области с холстом"""
    col1, col2 = st.columns([1.2, 1.8])
    with col1:
        st.markdown("### 📁 Загрузка изображений")
        uploaded_files = st.file_uploader("Выберите изображения (до 10000)", type=['png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff'], accept_multiple_files=True, key="image_uploader")
        if uploaded_files:
            st.session_state.images = uploaded_files
            st.session_state.total_files = len(uploaded_files)
            total_size = sum(len(f.getvalue()) for f in uploaded_files) / (1024 * 1024)
            st.metric("Всего МБ", f"{total_size:.1f}")
            st.metric("Файлов", len(uploaded_files))
            st.metric("Средний", f"{total_size/len(uploaded_files):.1f} МБ")
            if len(uploaded_files) > 1:
                col_n1, col_n2, col_n3 = st.columns([1, 2, 1])
                with col_n1:
                    if st.button("◀️", use_container_width=True, key="prev_btn"):
                        st.session_state.current_image_index = max(0, st.session_state.current_image_index - 1)
                with col_n2:
                    st.markdown(f"<center>{st.session_state.current_image_index + 1} / {len(uploaded_files)}</center>", unsafe_allow_html=True)
                with col_n3:
                    if st.button("▶️", use_container_width=True, key="next_btn"):
                        st.session_state.current_image_index = min(len(uploaded_files) - 1, st.session_state.current_image_index + 1)
        with col2:
            st.markdown("### 🎨 Холст для редактирования")
            if st.session_state.get('images'):
                current_img = st.session_state['images'][st.session_state['current_image_index']]
                img = Image.open(current_img).convert('RGBA')
                # Создаем фон
                bg_settings = {
                    'type': st.session_state.background_type,
                    'color': st.session_state.background_color,
                    'gradient': st.session_state.background_gradient,
                    'pattern': st.session_state.background_pattern,
                    'pattern_color': getattr(st.session_state, 'pattern_color', '#667eea'),
                    'bg_color': getattr(st.session_state, 'pattern_bg_color', '#FFFFFF'),
                    'image': st.session_state.background_image,
                    'opacity': st.session_state.background_opacity,
                    'blur': st.session_state.background_blur
                }
                bg_img = create_background(img.width, img.height, bg_settings)
                result = bg_img.copy()
                if st.session_state.background_type != 'image':
                    result.paste(img, (0, 0), img)
                else:
                    x = (result.width - img.width) // 2
                    y = (result.height - img.height) // 2
                    result.paste(img, (x, y), img)
                # сетка
                if st.session_state.show_grid:
                    draw = ImageDraw.Draw(result)
                    grid_color = (128, 128, 128, 100)
                    size = st.session_state.grid_size
                    for x in range(0, result.width, size):
                        draw.line([(x, 0), (x, result.height)], fill=grid_color, width=1)
                    for y in range(0, result.height, size):
                        draw.line([(0, y), (result.width, y)], fill=grid_color, width=1)
                # показываем
                st.image(result, use_column_width=True)
                # инфо
                st.markdown(f"""
<div style="display: flex; gap: 10px; margin-top: 10px;">
    <span class="size-badge">📏 {result.width} x {result.height}</span>
    <span class="size-badge">📁 {get_image_size(result):.1f} KB</span>
    <span class="size-badge">🎨 {result.mode}</span>
</div>
""", unsafe_allow_html=True)
                # кнопки
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if st.button("💾 Сохранить текущее", use_container_width=True, key="save_btn"):
                        output = io.BytesIO()
                        result.save(output, format='PNG', quality=95)
                        output.seek(0)
                        st.download_button("📥 Скачать", data=output, file_name=f"edited_{current_img.name}", mime="image/png", use_container_width=True)
                with col_b2:
                    if st.button("🔄 Сбросить все", use_container_width=True, key="reset_btn"):
                        st.session_state.background_color = '#667eea'
                        st.session_state.background_opacity = 1.0
                        st.session_state.background_blur = 0
                        st.rerun()
                # элементы данных
                if st.session_state.get('data_elements'):
                    st.markdown("#### 📋 Элементы данных на холсте")
                    for i, element in enumerate(st.session_state['data_elements']):
                        col_e1, col_e2 = st.columns([3, 1])
                        with col_e1:
                            st.info(f"{element['column']}: {element['value']} (x:{element['x']}, y:{element['y']})")
                        with col_e2:
                            if st.button("❌", key=f"del_{i}"):
                                st.session_state['data_elements'].pop(i)
                                st.rerun()
            else:
                st.markdown("""
        <div style="text-align: center; padding: 100px; background: rgba(0,0,0,0.02); border-radius: 20px;">
            <div style="font-size: 80px;">📸</div>
            <h3>Загрузите изображения для начала работы</h3>
            <p>Поддерживаются форматы: PNG, JPG, JPEG, WEBP, BMP, TIFF</p>
        </div>
        """, unsafe_allow_html=True)

def get_image_size(img):
    """Получение размера изображения в KB"""
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return len(buffer.getvalue()) / 1024

# ==================== Основная функция ====================
def main():
    """Главная логика"""
    st.markdown('<h1 class="main-header">⚡ MEGA Photo Editor ПРОФЕССИОНАЛЬНЫЙ</h1>', unsafe_allow_html=True)
    init_session_state()
    start_processing = render_sidebar()
    render_main_area()
    if start_processing and st.session_state.get('images'):
        with st.spinner("🔄 Обработка изображений..."):
            bg_settings = {
                'type': st.session_state.background_type,
                'color': st.session_state.background_color,
                'gradient': st.session_state.background_gradient,
                'pattern': st.session_state.background_pattern,
                'pattern_color': getattr(st.session_state, 'pattern_color', '#667eea'),
                'bg_color': getattr(st.session_state, 'pattern_bg_color', '#FFFFFF'),
                'image': st.session_state.background_image,
                'opacity': st.session_state.background_opacity,
                'blur': st.session_state.background_blur
            }
            processed, failed = process_batch_parallel(
                st.session_state['images'],
                bg_settings,
                st.session_state['data_elements'],
                st.session_state['excel_df'],
                max_workers=getattr(st.session_state, 'max_workers', 10)
            )
            st.markdown("### 📊 Результаты обработки")
            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                st.metric("Всего", len(st.session_state['images']))
            with col_r2:
                st.metric("Успешно", len(processed))
            with col_r3:
                st.metric("Ошибки", len(failed))
            if processed:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for filename, data in processed:
                        zip_file.writestr(filename, data)
                zip_buffer.seek(0)
                st.download_button("📥 Скачать все обработанные фото (ZIP)", data=zip_buffer, file_name=f"edited_photos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip", mime="application/zip", use_container_width=True)

# ==================== Запуск ====================
if __name__ == "__main__":
    main()
