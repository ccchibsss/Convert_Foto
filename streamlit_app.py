import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
import zipfile
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import queue
import json
import base64

# ================ КОНФИГУРАЦИЯ СТРАНИЦЫ ================
st.set_page_config(
    page_title="⚡ MEGA Infographic Factory",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================ CSS СТИЛИ ================
st.markdown("""
<style>
    /* Основные стили */
    .main-header {
        font-size: 3.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f43f5e 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
        padding: 2rem;
        animation: glow 3s ease-in-out infinite;
    }
    
    @keyframes glow {
        0%, 100% { filter: drop-shadow(0 0 20px rgba(102, 126, 234, 0.3)); }
        50% { filter: drop-shadow(0 0 40px rgba(102, 126, 234, 0.6)); }
    }
    
    /* Drag-and-drop области */
    .drop-zone {
        border: 3px dashed #667eea;
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        background: rgba(102, 126, 234, 0.05);
        transition: all 0.3s ease;
        min-height: 100px;
        margin: 10px 0;
        cursor: move;
        position: relative;
    }
    
    .drop-zone:hover {
        background: rgba(102, 126, 234, 0.1);
        border-color: #764ba2;
        transform: scale(1.02);
    }
    
    .drop-zone.active {
        border-color: #10b981;
        background: rgba(16, 185, 129, 0.1);
    }
    
    .resize-handle {
        position: absolute;
        bottom: 0;
        right: 0;
        width: 20px;
        height: 20px;
        cursor: se-resize;
        background: linear-gradient(135deg, transparent 50%, #667eea 50%);
        border-bottom-right-radius: 15px;
    }
    
    /* Текстовые боксы */
    .text-box {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border: 2px solid rgba(102, 126, 234, 0.3);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .text-box:hover {
        border-color: #667eea;
        transform: translateX(5px);
    }
    
    .text-box.selected {
        border-color: #10b981;
        background: rgba(16, 185, 129, 0.1);
    }
    
    /* Прогресс бар */
    .progress-container {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 20px;
        margin: 20px 0;
    }
    
    .progress-bar {
        height: 30px;
        background: linear-gradient(90deg, #667eea, #764ba2, #f43f5e);
        border-radius: 15px;
        transition: width 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .progress-bar::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
        animation: shimmer 2s infinite;
    }
    
    @keyframes shimmer {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(100%); }
    }
    
    /* Статистика */
    .stat-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        transition: all 0.3s ease;
    }
    
    .stat-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 40px rgba(0,0,0,0.2);
    }
    
    .stat-value {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .stat-label {
        color: #888;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Кнопки */
    .action-button {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        border: none;
        padding: 15px 30px;
        border-radius: 50px;
        font-size: 1.1rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        width: 100%;
        margin: 10px 0;
        position: relative;
        overflow: hidden;
    }
    
    .action-button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
        transition: left 0.5s ease;
    }
    
    .action-button:hover::before {
        left: 100%;
    }
    
    .action-button:hover {
        transform: translateY(-3px);
        box-shadow: 0 20px 40px rgba(102, 126, 234, 0.4);
    }
    
    /* Инструменты */
    .tool-panel {
        background: rgba(0, 0, 0, 0.02);
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
    }
    
    .tool-icon {
        font-size: 1.5rem;
        margin-right: 10px;
    }
    
    /* Уведомления */
    .notification {
        position: fixed;
        top: 20px;
        right: 20px;
        background: rgba(16, 185, 129, 0.9);
        backdrop-filter: blur(10px);
        color: white;
        padding: 15px 25px;
        border-radius: 50px;
        animation: slideIn 0.3s ease;
        z-index: 1000;
    }
    
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
</style>
""", unsafe_allow_html=True)

# ================ ИНИЦИАЛИЗАЦИЯ СОСТОЯНИЯ ================
def init_session_state():
    """Инициализация состояния сессии"""
    
    if 'templates' not in st.session_state:
        st.session_state.templates = {
            'template_1': {
                'name': 'Шаблон 1',
                'zones': {
                    'title': {'x': 0.1, 'y': 0.05, 'width': 0.8, 'height': 0.1, 'type': 'text', 'column': None},
                    'subtitle': {'x': 0.1, 'y': 0.16, 'width': 0.8, 'height': 0.06, 'type': 'text', 'column': None},
                    'chart': {'x': 0.05, 'y': 0.25, 'width': 0.9, 'height': 0.4, 'type': 'chart', 'column': None},
                    'metric_1': {'x': 0.05, 'y': 0.7, 'width': 0.2, 'height': 0.1, 'type': 'metric', 'column': 'value'},
                    'metric_2': {'x': 0.4, 'y': 0.7, 'width': 0.2, 'height': 0.1, 'type': 'metric', 'column': 'value'},
                    'metric_3': {'x': 0.75, 'y': 0.7, 'width': 0.2, 'height': 0.1, 'type': 'metric', 'column': 'value'},
                    'text_1': {'x': 0.05, 'y': 0.85, 'width': 0.4, 'height': 0.1, 'type': 'text', 'column': None},
                    'text_2': {'x': 0.55, 'y': 0.85, 'width': 0.4, 'height': 0.1, 'type': 'text', 'column': None}
                }
            },
            'template_2': {
                'name': 'Шаблон 2',
                'zones': {
                    'header': {'x': 0.1, 'y': 0.02, 'width': 0.8, 'height': 0.08, 'type': 'text', 'column': None},
                    'chart_left': {'x': 0.05, 'y': 0.15, 'width': 0.4, 'height': 0.4, 'type': 'chart', 'column': None},
                    'chart_right': {'x': 0.55, 'y': 0.15, 'width': 0.4, 'height': 0.4, 'type': 'chart', 'column': None},
                    'stats': {'x': 0.05, 'y': 0.6, 'width': 0.9, 'height': 0.2, 'type': 'metrics_grid', 'column': None},
                    'footer': {'x': 0.1, 'y': 0.85, 'width': 0.8, 'height': 0.1, 'type': 'text', 'column': None}
                }
            }
        }
    
    if 'current_template' not in st.session_state:
        st.session_state.current_template = 'template_1'
    
    if 'selected_zone' not in st.session_state:
        st.session_state.selected_zone = None
    
    if 'processed_files' not in st.session_state:
        st.session_state.processed_files = []
    
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
    "Corporate Blue": {"primary": "#1E3A8A", "secondary": "#2563EB", "accent": "#3B82F6", "background": "#F0F9FF"},
    "Modern Gradient": {"primary": "#8B5CF6", "secondary": "#EC4899", "accent": "#F59E0B", "background": "#FDF4FF"},
    "Earthy Tones": {"primary": "#92400E", "secondary": "#B45309", "accent": "#D97706", "background": "#FFFBEB"},
    "Ocean Vibes": {"primary": "#0F766E", "secondary": "#0891B2", "accent": "#06B6D4", "background": "#ECFEFF"},
    "Sunset": {"primary": "#B91C1C", "secondary": "#C2410C", "accent": "#F97316", "background": "#FFF7ED"},
    "Minimal Gray": {"primary": "#374151", "secondary": "#4B5563", "accent": "#6B7280", "background": "#F9FAFB"},
    "Fresh Green": {"primary": "#166534", "secondary": "#16A34A", "accent": "#4ADE80", "background": "#F0FDF4"},
    "Royal Purple": {"primary": "#581C87", "secondary": "#6B21A8", "accent": "#9333EA", "background": "#FAF5FF"},
    "Midnight": {"primary": "#020617", "secondary": "#0F172A", "accent": "#1E293B", "background": "#0B1120"},
    "Pastel Dreams": {"primary": "#FBCFE8", "secondary": "#FDE68A", "accent": "#A7F3D0", "background": "#FDF2F8"}
}

# ================ РАЗМЕРЫ ================
IMAGE_SIZES = {
    "Instagram Square": {"width": 1080, "height": 1080},
    "Instagram Portrait": {"width": 1080, "height": 1350},
    "Instagram Landscape": {"width": 1080, "height": 566},
    "Facebook Post": {"width": 1200, "height": 630},
    "Twitter Post": {"width": 1600, "height": 900},
    "LinkedIn Post": {"width": 1200, "height": 627},
    "Presentation 16:9": {"width": 1920, "height": 1080},
    "Presentation 4:3": {"width": 1024, "height": 768},
    "A4 Portrait": {"width": 2480, "height": 3508},
    "A4 Landscape": {"width": 3508, "height": 2480},
    "Custom": {"width": 1920, "height": 1080}
}

# ================ ФОНОВЫЕ ЭФФЕКТЫ ================
BACKGROUND_EFFECTS = {
    "Solid": "solid",
    "Linear Gradient": "gradient",
    "Radial Gradient": "radial",
    "Dots": "dots",
    "Lines": "lines",
    "Grid": "grid",
    "Noise": "noise"
}

# ================ ФУНКЦИИ ДЛЯ РАБОТЫ С ШАБЛОНАМИ ================
def render_template_preview(template_id):
    """Отрисовка превью шаблона"""
    
    template = st.session_state.templates[template_id]
    zones = template['zones']
    
    # Создаем фигуру для превью
    fig = go.Figure()
    
    # Добавляем прямоугольники для каждой зоны
    colors = ['#667eea', '#764ba2', '#f43f5e', '#10b981', '#f59e0b']
    
    for i, (zone_name, zone) in enumerate(zones.items()):
        color = colors[i % len(colors)]
        
        # Добавляем прямоугольник
        fig.add_shape(
            type="rect",
            x0=zone['x'],
            y0=1 - zone['y'] - zone['height'],
            x1=zone['x'] + zone['width'],
            y1=1 - zone['y'],
            line=dict(color=color, width=2),
            fillcolor=color,
            opacity=0.2
        )
        
        # Добавляем текст
        fig.add_annotation(
            x=zone['x'] + zone['width']/2,
            y=1 - zone['y'] - zone['height']/2,
            text=f"<b>{zone_name}</b><br>{zone['type']}",
            showarrow=False,
            font=dict(size=10, color=color)
        )
    
    fig.update_layout(
        title=f"Шаблон: {template['name']}",
        xaxis=dict(range=[0, 1], showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(range=[0, 1], showgrid=False, zeroline=False, showticklabels=False),
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

def create_template_editor():
    """Создание редактора шаблонов"""
    
    st.markdown("### 🎨 Редактор шаблонов")
    
    # Выбор шаблона
    template_options = {k: v['name'] for k, v in st.session_state.templates.items()}
    selected_template = st.selectbox(
        "Выберите шаблон для редактирования",
        options=list(template_options.keys()),
        format_func=lambda x: template_options[x],
        key="template_selector"
    )
    
    if selected_template:
        st.session_state.current_template = selected_template
        template = st.session_state.templates[selected_template]
        
        # Отображение превью
        st.plotly_chart(render_template_preview(selected_template), use_container_width=True)
        
        # Редактор зон
        st.markdown("#### Зоны шаблона")
        
        # Создаем колонки для зон
        zones = list(template['zones'].items())
        
        # Группируем зоны по 2 в ряд
        for i in range(0, len(zones), 2):
            cols = st.columns(2)
            for j in range(2):
                if i + j < len(zones):
                    zone_name, zone = zones[i + j]
                    with cols[j]:
                        with st.container():
                            st.markdown(f"""
                            <div class="text-box {'selected' if st.session_state.selected_zone == zone_name else ''}"
                                 onclick="alert('selected_{zone_name}')">
                                <b>{zone_name}</b> ({zone['type']})
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Кнопка выбора
                            if st.button(f"✏️ Выбрать", key=f"select_{zone_name}"):
                                st.session_state.selected_zone = zone_name
                                st.rerun()
        
        # Если выбрана зона, показываем настройки
        if st.session_state.selected_zone and st.session_state.selected_zone in template['zones']:
            zone = template['zones'][st.session_state.selected_zone]
            
            st.markdown(f"#### Настройки зоны: {st.session_state.selected_zone}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Позиция
                st.markdown("**Позиция**")
                x = st.slider("X", 0.0, 1.0, zone['x'], 0.01, key=f"x_{st.session_state.selected_zone}")
                y = st.slider("Y", 0.0, 1.0, zone['y'], 0.01, key=f"y_{st.session_state.selected_zone}")
                
                # Размер
                st.markdown("**Размер**")
                width = st.slider("Ширина", 0.0, 1.0, zone['width'], 0.01, key=f"w_{st.session_state.selected_zone}")
                height = st.slider("Высота", 0.0, 1.0, zone['height'], 0.01, key=f"h_{st.session_state.selected_zone}")
            
            with col2:
                # Тип зоны
                st.markdown("**Тип**")
                zone_type = st.selectbox(
                    "Тип контента",
                    ["text", "metric", "chart", "image", "metrics_grid"],
                    index=["text", "metric", "chart", "image", "metrics_grid"].index(zone['type']),
                    key=f"type_{st.session_state.selected_zone}"
                )
                
                # Привязка к колонке
                if 'df' in st.session_state and st.session_state.df is not None:
                    st.markdown("**Привязка данных**")
                    columns = ['Нет'] + list(st.session_state.df.columns)
                    current_col = zone.get('column', 'Нет')
                    col_index = columns.index(current_col) if current_col in columns else 0
                    
                    selected_col = st.selectbox(
                        "Колонка данных",
                        columns,
                        index=col_index,
                        key=f"col_{st.session_state.selected_zone}"
                    )
                    zone['column'] = None if selected_col == 'Нет' else selected_col
                
                # Дополнительные настройки
                if zone_type == 'text':
                    zone['font_size'] = st.slider("Размер шрифта", 8, 72, zone.get('font_size', 24), key=f"font_{st.session_state.selected_zone}")
                    zone['bold'] = st.checkbox("Жирный", zone.get('bold', False), key=f"bold_{st.session_state.selected_zone}")
                    zone['italic'] = st.checkbox("Курсив", zone.get('italic', False), key=f"italic_{st.session_state.selected_zone}")
                
                elif zone_type == 'metric':
                    zone['prefix'] = st.text_input("Префикс", zone.get('prefix', ''), key=f"prefix_{st.session_state.selected_zone}")
                    zone['suffix'] = st.text_input("Суффикс", zone.get('suffix', ''), key=f"suffix_{st.session_state.selected_zone}")
                    zone['decimals'] = st.number_input("Десятичных знаков", 0, 10, zone.get('decimals', 2), key=f"dec_{st.session_state.selected_zone}")
            
            # Кнопка сохранения
            if st.button("💾 Сохранить изменения зоны", key=f"save_{st.session_state.selected_zone}", use_container_width=True):
                template['zones'][st.session_state.selected_zone].update({
                    'x': x, 'y': y, 'width': width, 'height': height,
                    'type': zone_type
                })
                st.success(f"✅ Зона {st.session_state.selected_zone} обновлена!")
                st.rerun()
        
        # Кнопка создания новой зоны
        st.markdown("---")
        if st.button("➕ Добавить новую зону", use_container_width=True):
            new_zone_name = f"zone_{len(template['zones']) + 1}"
            template['zones'][new_zone_name] = {
                'x': 0.1, 'y': 0.1, 'width': 0.3, 'height': 0.2,
                'type': 'text', 'column': None
            }
            st.success(f"✅ Добавлена зона: {new_zone_name}")
            st.rerun()

# ================ ФУНКЦИИ ДЛЯ ПАКЕТНОЙ ОБРАБОТКИ ================
def process_single_file(file_data, template_id, color_theme, size_preset, bg_effect):
    """Обработка одного файла"""
    
    try:
        filename, file_content = file_data
        
        # Загрузка данных
        if filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(file_content))
        elif filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(file_content))
        else:
            return None
        
        # Получаем шаблон
        template = st.session_state.templates[template_id]
        color_palette = COLOR_PALETTES[color_theme]
        size = IMAGE_SIZES[size_preset]
        
        # Создаем изображение
        img = create_infographic_from_template(df, template, color_palette, size, bg_effect)
        
        # Сохраняем
        output = io.BytesIO()
        img.save(output, format='PNG', quality=95, dpi=(300, 300))
        output.seek(0)
        
        return (filename.replace('.csv', '').replace('.xlsx', '').replace('.xls', '') + '.png', output.getvalue())
        
    except Exception as e:
        return None

def create_infographic_from_template(df, template, color_palette, size, bg_effect):
    """Создание инфографики на основе шаблона"""
    
    width, height = size['width'], size['height']
    
    # Создаем фон
    img = Image.new('RGB', (width, height), color_palette['background'])
    draw = ImageDraw.Draw(img)
    
    # Применяем фоновый эффект
    if bg_effect != "Solid":
        apply_background_effect(img, bg_effect, color_palette)
    
    # Отрисовываем каждую зону
    for zone_name, zone in template['zones'].items():
        # Конвертируем относительные координаты в абсолютные
        x1 = int(zone['x'] * width)
        y1 = int(zone['y'] * height)
        x2 = int((zone['x'] + zone['width']) * width)
        y2 = int((zone['y'] + zone['height']) * height)
        
        # Рисуем рамку зоны (для отладки)
        draw.rectangle([x1, y1, x2, y2], outline=color_palette['secondary'], width=2)
        
        # Добавляем контент в зависимости от типа
        if zone['type'] == 'text':
            # Текст из колонки или статичный
            if zone.get('column') and zone['column'] in df.columns:
                text = str(df[zone['column']].iloc[0])
            else:
                text = zone_name
            
            # Параметры текста
            font_size = min(zone.get('font_size', 24), int(zone['height'] * height * 0.8))
            
            # Разбиваем текст на строки
            words = text.split()
            lines = []
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                if draw.textbbox((0, 0), test_line)[2] < (x2 - x1) * 0.9:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
            
            if current_line:
                lines.append(' '.join(current_line))
            
            # Отрисовываем текст
            y_offset = y1 + 10
            for line in lines:
                bbox = draw.textbbox((0, 0), line)
                text_width = bbox[2] - bbox[0]
                x_center = x1 + (x2 - x1 - text_width) // 2
                draw.text((x_center, y_offset), line, fill=color_palette['primary'])
                y_offset += bbox[3] - bbox[1] + 5
        
        elif zone['type'] == 'metric':
            # Метрика из колонки
            if zone.get('column') and zone['column'] in df.columns:
                value = df[zone['column']].iloc[0]
                
                # Форматирование
                prefix = zone.get('prefix', '')
                suffix = zone.get('suffix', '')
                decimals = zone.get('decimals', 2)
                
                if isinstance(value, (int, float)):
                    formatted_value = f"{prefix}{value:,.{decimals}f}{suffix}"
                else:
                    formatted_value = f"{prefix}{value}{suffix}"
                
                # Отрисовка
                font_size = min(36, int(zone['height'] * height * 0.5))
                bbox = draw.textbbox((0, 0), formatted_value)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                x_center = x1 + (x2 - x1 - text_width) // 2
                y_center = y1 + (y2 - y1 - text_height) // 2
                
                draw.text((x_center, y_center), formatted_value, fill=color_palette['primary'])
        
        elif zone['type'] == 'metrics_grid':
            # Сетка метрик
            numeric_cols = df.select_dtypes(include=[np.number]).columns[:4]
            
            if len(numeric_cols) > 0:
                grid_cols = min(2, len(numeric_cols))
                grid_rows = (len(numeric_cols) + grid_cols - 1) // grid_cols
                
                cell_width = (x2 - x1) // grid_cols
                cell_height = (y2 - y1) // grid_rows
                
                for i, col in enumerate(numeric_cols):
                    row = i // grid_cols
                    col_idx = i % grid_cols
                    
                    cx1 = x1 + col_idx * cell_width
                    cy1 = y1 + row * cell_height
                    cx2 = cx1 + cell_width
                    cy2 = cy1 + cell_height
                    
                    # Рамка ячейки
                    draw.rectangle([cx1, cy1, cx2, cy2], outline=color_palette['accent'], width=1)
                    
                    # Значение
                    value = df[col].iloc[0]
                    formatted_value = f"{value:,.2f}"
                    
                    # Заголовок
                    title_bbox = draw.textbbox((0, 0), col)
                    title_x = cx1 + (cell_width - (title_bbox[2] - title_bbox[0])) // 2
                    draw.text((title_x, cy1 + 5), col, fill=color_palette['secondary'])
                    
                    # Значение
                    value_bbox = draw.textbbox((0, 0), formatted_value)
                    value_x = cx1 + (cell_width - (value_bbox[2] - value_bbox[0])) // 2
                    draw.text((value_x, cy2 - 30), formatted_value, fill=color_palette['primary'])
    
    return img

def apply_background_effect(img, effect, color_palette):
    """Применение фонового эффекта"""
    
    width, height = img.size
    draw = ImageDraw.Draw(img)
    
    if effect == "gradient":
        for i in range(height):
            ratio = i / height
            r = int(int(color_palette['primary'][1:3], 16) * (1 - ratio) + 
                   int(color_palette['secondary'][1:3], 16) * ratio)
            g = int(int(color_palette['primary'][3:5], 16) * (1 - ratio) + 
                   int(color_palette['secondary'][3:5], 16) * ratio)
            b = int(int(color_palette['primary'][5:7], 16) * (1 - ratio) + 
                   int(color_palette['secondary'][5:7], 16) * ratio)
            draw.line([(0, i), (width, i)], fill=(r, g, b))
    
    elif effect == "radial":
        center_x, center_y = width // 2, height // 2
        max_dist = np.sqrt(center_x**2 + center_y**2)
        
        for x in range(0, width, 5):
            for y in range(0, height, 5):
                dist = np.sqrt((x - center_x)**2 + (y - center_y)**2)
                ratio = dist / max_dist
                
                r = int(int(color_palette['primary'][1:3], 16) * (1 - ratio) + 
                       int(color_palette['secondary'][3:5], 16) * ratio)
                g = int(int(color_palette['primary'][3:5], 16) * (1 - ratio) + 
                       int(color_palette['secondary'][5:7], 16) * ratio)
                b = int(int(color_palette['primary'][5:7], 16) * (1 - ratio) + 
                       int(color_palette['secondary'][7:9], 16) * ratio)
                
                draw.rectangle([x, y, x+5, y+5], fill=(r, g, b))
    
    elif effect == "dots":
        dot_color = color_palette['secondary']
        for x in range(0, width, 20):
            for y in range(0, height, 20):
                draw.ellipse([x-2, y-2, x+2, y+2], fill=dot_color)
    
    elif effect == "lines":
        line_color = color_palette['accent']
        for x in range(0, width, 30):
            draw.line([(x, 0), (x, height)], fill=line_color, width=1)
    
    elif effect == "grid":
        grid_color = color_palette['accent']
        for x in range(0, width, 50):
            draw.line([(x, 0), (x, height)], fill=grid_color, width=1)
        for y in range(0, height, 50):
            draw.line([(0, y), (width, y)], fill=grid_color, width=1)
    
    elif effect == "noise":
        noise = np.random.randint(0, 30, (height, width, 3), dtype=np.uint8)
        noise_img = Image.fromarray(noise)
        img = Image.blend(img, noise_img, alpha=0.1)

# ================ ФУНКЦИИ ДЛЯ ПАКЕТНОЙ ОБРАБОТКИ С ПРОГРЕССОМ ================
def process_batch_files_parallel(files, template_id, color_theme, size_preset, bg_effect, max_workers=10):
    """Параллельная обработка файлов"""
    
    total = len(files)
    processed = []
    failed = []
    
    # Создаем данные для обработки
    file_data = [(f.name, f.getvalue()) for f in files]
    
    # Прогресс бар
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Используем ThreadPoolExecutor для параллельной обработки
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_single_file, fd, template_id, color_theme, size_preset, bg_effect): fd[0] 
                  for fd in file_data}
        
        completed = 0
        for future in as_completed(futures):
            filename = futures[future]
            try:
                result = future.result(timeout=30)
                if result:
                    processed.append(result)
                else:
                    failed.append(filename)
            except Exception as e:
                failed.append(filename)
            
            completed += 1
            progress = completed / total
            progress_bar.progress(progress)
            status_text.text(f"🔄 Обработано: {completed}/{total} | Успешно: {len(processed)} | Ошибок: {len(failed)}")
    
    return processed, failed

# ================ ОСНОВНОЙ ИНТЕРФЕЙС ================
def main():
    """Основная функция"""
    
    # Заголовок
    st.markdown('<h1 class="main-header">⚡ MEGA Infographic Factory</h1>', unsafe_allow_html=True)
    
    # Инициализация состояния
    init_session_state()
    
    # Вкладки
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎨 Редактор шаблонов",
        "📦 Пакетная обработка",
        "📊 Данные",
        "⚙️ Настройки"
    ])
    
    with tab1:
        create_template_editor()
    
    with tab2:
        st.markdown("### 📦 Пакетная обработка файлов")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # Загрузка файлов
            uploaded_files = st.file_uploader(
                "Загрузите файлы для обработки (до 10000)",
                type=['csv', 'xlsx', 'xls'],
                accept_multiple_files=True,
                key="batch_uploader"
            )
            
            if uploaded_files:
                st.success(f"✅ Загружено файлов: {len(uploaded_files)}")
                
                # Настройки обработки
                st.markdown("### ⚙️ Настройки обработки")
                
                # Выбор шаблона
                template_options = {k: v['name'] for k, v in st.session_state.templates.items()}
                selected_template = st.selectbox(
                    "Шаблон",
                    options=list(template_options.keys()),
                    format_func=lambda x: template_options[x],
                    key="batch_template"
                )
                
                # Цветовая тема
                color_theme = st.selectbox(
                    "Цветовая тема",
                    list(COLOR_PALETTES.keys()),
                    index=0
                )
                
                # Размер
                size_preset = st.selectbox(
                    "Размер",
                    list(IMAGE_SIZES.keys()),
                    index=0
                )
                
                # Фон
                bg_effect = st.selectbox(
                    "Фоновый эффект",
                    list(BACKGROUND_EFFECTS.keys()),
                    index=0
                )
                
                # Количество потоков
                max_workers = st.slider(
                    "Параллельных потоков",
                    min_value=1,
                    max_value=20,
                    value=10,
                    help="Больше потоков = быстрее обработка, но больше нагрузка"
                )
                
                # Кнопка запуска
                if st.button("🚀 Запустить пакетную обработку", key="start_batch", use_container_width=True):
                    with st.spinner("Обработка файлов..."):
                        processed, failed = process_batch_files_parallel(
                            uploaded_files,
                            selected_template,
                            color_theme,
                            size_preset,
                            bg_effect,
                            max_workers
                        )
                        
                        # Сохраняем результаты
                        st.session_state.processed_files = processed
                        
                        # Показываем результаты
                        st.markdown("### 📊 Результаты обработки")
                        
                        col_r1, col_r2, col_r3 = st.columns(3)
                        with col_r1:
                            st.metric("Всего файлов", len(uploaded_files))
                        with col_r2:
                            st.metric("Успешно", len(processed))
                        with col_r3:
                            st.metric("С ошибками", len(failed))
                        
                        if failed:
                            with st.expander("❌ Файлы с ошибками"):
                                for f in failed:
                                    st.write(f"• {f}")
        
        with col2:
            if st.session_state.processed_files:
                st.markdown("### 📥 Результаты готовы")
                
                # Превью первого файла
                if len(st.session_state.processed_files) > 0:
                    st.markdown("#### Превью:")
                    preview_data = st.session_state.processed_files[0][1]
                    st.image(preview_data, use_column_width=True)
                
                # Создание ZIP архива
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for filename, data in st.session_state.processed_files:
                        zip_file.writestr(filename, data)
                
                zip_buffer.seek(0)
                
                # Кнопка скачивания
                st.download_button(
                    "📥 Скачать все файлы (ZIP)",
                    data=zip_buffer,
                    file_name=f"infographics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                    mime="application/zip",
                    use_container_width=True
                )
                
                # Очистка
                if st.button("🗑️ Очистить результаты", use_container_width=True):
                    st.session_state.processed_files = []
                    st.rerun()
    
    with tab3:
        st.markdown("### 📊 Загрузка данных")
        
        # Загрузка данных для привязки колонок
        data_file = st.file_uploader(
            "Загрузите файл с данными (для настройки шаблона)",
            type=['csv', 'xlsx', 'xls'],
            key="data_uploader"
        )
        
        if data_file:
            try:
                if data_file.name.endswith('.csv'):
                    df = pd.read_csv(data_file)
                else:
                    df = pd.read_excel(data_file)
                
                st.session_state.df = df
                
                st.success(f"✅ Загружено: {len(df)} строк, {len(df.columns)} колонок")
                
                # Превью данных
                with st.expander("👁️ Превью данных"):
                    st.dataframe(df.head(100), use_container_width=True)
                    
                    # Статистика
                    st.markdown("#### Статистика")
                    
                    # Числовые колонки
                    numeric_cols = df.select_dtypes(include=[np.number]).columns
                    if len(numeric_cols) > 0:
                        st.markdown("**Числовые колонки:**")
                        st.dataframe(df[numeric_cols].describe(), use_container_width=True)
                    
                    # Текстовые колонки
                    text_cols = df.select_dtypes(include=['object']).columns
                    if len(text_cols) > 0:
                        st.markdown("**Текстовые колонки:**")
                        for col in text_cols[:5]:
                            st.write(f"• {col}: {df[col].iloc[0] if len(df) > 0 else 'нет данных'}")
            
            except Exception as e:
                st.error(f"Ошибка загрузки: {str(e)}")
    
    with tab4:
        st.markdown("### ⚙️ Настройки приложения")
        
        col_s1, col_s2 = st.columns(2)
        
        with col_s1:
            st.markdown("#### Общие настройки")
            
            # Максимальное количество файлов
            max_files = st.number_input(
                "Максимум файлов для пакетной обработки",
                min_value=100,
                max_value=50000,
                value=10000,
                step=1000
            )
            
            # Таймаут обработки
            timeout = st.number_input(
                "Таймаут обработки (сек)",
                min_value=10,
                max_value=300,
                value=60,
                step=10
            )
            
            # Качество изображений
            image_quality = st.slider(
                "Качество изображений",
                min_value=50,
                max_value=100,
                value=95
            )
            
            # DPI для печати
            dpi = st.slider(
                "DPI",
                min_value=72,
                max_value=600,
                value=300,
                step=72
            )
        
        with col_s2:
            st.markdown("#### Пути сохранения")
            
            # Папка для сохранения
            save_folder = st.text_input(
                "Папка для сохранения",
                value="./output"
            )
            
            # Формат имени файлов
            name_format = st.text_input(
                "Формат имени",
                value="{filename}_{date}"
            )
            
            # Создание папки если не существует
            if st.button("📁 Создать папку", use_container_width=True):
                os.makedirs(save_folder, exist_ok=True)
                st.success(f"✅ Папка создана: {save_folder}")
        
        st.markdown("#### Управление шаблонами")
        
        col_t1, col_t2, col_t3 = st.columns(3)
        
        with col_t1:
            # Экспорт шаблонов
            if st.button("📤 Экспорт шаблонов", use_container_width=True):
                templates_json = json.dumps(st.session_state.templates, indent=2)
                st.download_button(
                    "📥 Скачать шаблоны",
                    data=templates_json,
                    file_name="templates_backup.json",
                    mime="application/json"
                )
        
        with col_t2:
            # Импорт шаблонов
            uploaded_json = st.file_uploader(
                "Импорт шаблонов",
                type=['json'],
                key="template_import"
            )
            
            if uploaded_json:
                try:
                    imported = json.load(uploaded_json)
                    st.session_state.templates.update(imported)
                    st.success("✅ Шаблоны импортированы")
                except Exception as e:
                    st.error(f"Ошибка импорта: {str(e)}")
        
        with col_t3:
            # Сброс к стандартным
            if st.button("🔄 Сброс к стандартным", use_container_width=True):
                init_session_state()
                st.success("✅ Настройки сброшены")
                st.rerun()

# ================ ЗАПУСК ================
if __name__ == "__main__":
    main()
