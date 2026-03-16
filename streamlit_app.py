import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import os
import io
from datetime import datetime
import zipfile
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import hashlib
from collections import defaultdict

# Настройка страницы
st.set_page_config(
    page_title="ImageMagic Pro - Конвертер для маркетплейсов",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Кастомные CSS стили
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
    .marketplace-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        padding: 1rem;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    .size-badge {
        background-color: #f0f2f6;
        border-radius: 20px;
        padding: 0.3rem 0.8rem;
        margin: 0.2rem;
        display: inline-block;
        font-size: 0.8rem;
        color: #333;
    }
    .stats-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        text-align: center;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: bold;
        color: #FF4B4B;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #666;
    }
    .warning-badge {
        background-color: #ff4757;
        color: white;
        border-radius: 15px;
        padding: 0.2rem 0.8rem;
        font-size: 0.7rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Заголовок
st.markdown('<h1 class="main-header">✨ ImageMagic Pro</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Профессиональный конвертер изображений для маркетплейсов</p>', unsafe_allow_html=True)

# Группировка размеров по категориям
SIZE_CATEGORIES = {
    "Квадратные (1:1)": {
        "description": "Универсальный формат для большинства маркетплейсов",
        "sizes": [
            {"name": "Миниатюра", "size": (100, 100), "marketplaces": ["Все"]},
            {"name": "Маленький", "size": (300, 300), "marketplaces": ["Ozon", "Яндекс Маркет"]},
            {"name": "Средний", "size": (600, 600), "marketplaces": ["Ozon", "AliExpress"]},
            {"name": "Рекомендуемый", "size": (1000, 1000), "marketplaces": ["Яндекс Маркет", "AliExpress", "Amazon"]},
            {"name": "Большой", "size": (1200, 1200), "marketplaces": ["Ozon"]},
            {"name": "Для Etsy", "size": (2000, 2000), "marketplaces": ["Etsy"]},
            {"name": "Максимальный", "size": (3000, 3000), "marketplaces": ["Amazon", "Etsy"]},
            {"name": "Супер HD", "size": (4000, 4000), "marketplaces": ["Яндекс Маркет"]},
        ]
    },
    "Вертикальные (3:4)": {
        "description": "Идеально для Wildberries и мобильных устройств",
        "sizes": [
            {"name": "Минимальный WB", "size": (1000, 1333), "marketplaces": ["Wildberries"]},
            {"name": "Рекомендуемый WB", "size": (1200, 1600), "marketplaces": ["Wildberries"]},
            {"name": "Максимальный WB", "size": (2000, 2666), "marketplaces": ["Wildberries"]},
            {"name": "Инстаграм портрет", "size": (1080, 1350), "marketplaces": ["Instagram"]},
        ]
    },
    "Горизонтальные (16:9)": {
        "description": "Для баннеров и альбомных изображений",
        "sizes": [
            {"name": "YouTube миниатюра", "size": (1280, 720), "marketplaces": ["YouTube"]},
            {"name": "Презентационный", "size": (1920, 1080), "marketplaces": ["Full HD"]},
            {"name": "Инстаграм альбом", "size": (1080, 566), "marketplaces": ["Instagram"]},
        ]
    },
    "Специальные форматы": {
        "description": "Специфические требования маркетплейсов",
        "sizes": [
            {"name": "Ozon фото 360", "size": (1024, 1024), "marketplaces": ["Ozon 360"]},
            {"name": "Яндекс.Директ", "size": (1080, 607), "marketplaces": ["Яндекс.Директ"]},
            {"name": "Wildberries инфографика", "size": (1200, 1800), "marketplaces": ["Wildberries"]},
        ]
    }
}

# Словарь с требованиями маркетплейсов
MARKETPLACE_INFO = {
    "Wildberries": {
        "color": "#8A2BE2",
        "icon": "🛍️",
        "ratio": "3:4",
        "bg_color": "linear-gradient(135deg, #8A2BE2 0%, #4B0082 100%)"
    },
    "Ozon": {
        "color": "#005BFF",
        "icon": "📦",
        "ratio": "1:1",
        "bg_color": "linear-gradient(135deg, #005BFF 0%, #003399 100%)"
    },
    "Яндекс Маркет": {
        "color": "#FFCC00",
        "icon": "🌟",
        "ratio": "1:1",
        "bg_color": "linear-gradient(135deg, #FFCC00 0%, #FF9900 100%)"
    },
    "AliExpress": {
        "color": "#FF6B6B",
        "icon": "🛒",
        "ratio": "1:1",
        "bg_color": "linear-gradient(135deg, #FF6B6B 0%, #EE5A24 100%)"
    },
    "Etsy": {
        "color": "#F56400",
        "icon": "🎨",
        "ratio": "1:1",
        "bg_color": "linear-gradient(135deg, #F56400 0%, #D35400 100%)"
    },
    "Amazon": {
        "color": "#FF9900",
        "icon": "📚",
        "ratio": "1:1",
        "bg_color": "linear-gradient(135deg, #FF9900 0%, #FF6B35 100%)"
    },
    "Instagram": {
        "color": "#C13584",
        "icon": "📱",
        "ratio": "1:1/4:5/16:9",
        "bg_color": "linear-gradient(135deg, #C13584 0%, #833AB4 100%)"
    }
}

# Боковая панель
with st.sidebar:
    st.image("https://via.placeholder.com/300x100/FF4B4B/FFFFFF?text=ImageMagic+Pro", use_column=True)
    
    st.markdown("## 🎯 Быстрый старт")
    
    # Выбор режима с иконками
    mode = st.selectbox(
        "Режим работы",
        [
            "🚀 Экспресс конвертация",
            "🛒 Для маркетплейсов", 
            "📦 Пакетная обработка",
            "📊 Анализ изображений",
            "🔄 Пакетное переименование"
        ]
    )
    
    st.markdown("---")
    
    if mode == "🛒 Для маркетплейсов":
        st.markdown("### 🏪 Выберите площадку")
        
        # Отображаем маркетплейсы в виде цветных кнопок
        cols = st.columns(2)
        selected_marketplaces = []
        
        for i, (mp_name, mp_info) in enumerate(MARKETPLACE_INFO.items()):
            with cols[i % 2]:
                if st.button(
                    f"{mp_info['icon']} {mp_name}",
                    key=f"mp_{mp_name}",
                    help=f"Соотношение сторон: {mp_info['ratio']}",
                    use_container_width=True
                ):
                    if mp_name not in selected_marketplaces:
                        selected_marketplaces.append(mp_name)
                    else:
                        selected_marketplaces.remove(mp_name)
        
        # Отображаем выбранные маркетплейсы
        if selected_marketplaces:
            st.markdown("**Выбрано:** " + ", ".join(selected_marketplaces))
            
            # Автоматически выбираем размеры под выбранные маркетплейсы
            recommended_sizes = []
            for mp in selected_marketplaces:
                for category, cat_info in SIZE_CATEGORIES.items():
                    for size_info in cat_info["sizes"]:
                        if mp in size_info["marketplaces"] or "Все" in size_info["marketplaces"]:
                            if size_info not in recommended_sizes:
                                recommended_sizes.append(size_info)
            
            st.success(f"✅ Рекомендовано {len(recommended_sizes)} размеров")
    
    elif mode == "📊 Анализ изображений":
        st.markdown("### 🔬 Параметры анализа")
        analyze_quality = st.checkbox("Анализ качества", value=True)
        analyze_colors = st.checkbox("Цветовой анализ", value=True)
        analyze_metadata = st.checkbox("Извлечь метаданные", value=False)
        detect_duplicates = st.checkbox("Поиск дубликатов", value=False)
    
    elif mode == "🔄 Пакетное переименование":
        st.markdown("### 📝 Правила переименования")
        naming_pattern = st.selectbox(
            "Шаблон",
            [
                "SKU_Название_Размер",
                "Артикул_Размер_Название", 
                "Категория_SKU_Размер",
                "Дата_Название_Размер"
            ]
        )
        separator = st.selectbox("Разделитель", ["_", "-", " ", "."])
        add_timestamp = st.checkbox("Добавить дату", value=False)
        add_sku = st.text_input("Префикс SKU", placeholder="Например: WB-001")

# Основная область с табами
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📸 Конвертер", 
    "📊 Визуализация", 
    "📋 Сравнение размеров",
    "🔍 Предпросмотр сетки",
    "📈 Статистика"
])

with tab1:
    # Конвертер
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 📤 Загрузка изображений")
        
        # Drag & drop загрузка
        uploaded_files = st.file_uploader(
            "Перетащите файлы сюда",
            type=['png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp', 'heic'],
            accept_multiple_files=True,
            help="Поддерживаются PNG, JPG, WEBP, BMP, TIFF, HEIC"
        )
        
        if uploaded_files:
            st.success(f"✅ Загружено: {len(uploaded_files)} файлов")
            
            # Превью загруженных файлов
            with st.expander("📸 Превью загруженных"):
                preview_cols = st.columns(4)
                for idx, file in enumerate(uploaded_files[:8]):
                    with preview_cols[idx % 4]:
                        img = Image.open(file)
                        st.image(img, caption=f"{file.name[:10]}...", use_column=True)
    
    with col2:
        if uploaded_files:
            st.markdown("### ⚙️ Параметры конвертации")
            
            # Выбор размеров из категорий
            st.markdown("#### 📐 Выберите размеры")
            
            selected_sizes = []
            
            # Отображаем категории с группировкой
            for category, cat_info in SIZE_CATEGORIES.items():
                with st.expander(f"{category} - {cat_info['description']}"):
                    # Отображаем размеры в виде чипсов
                    cols = st.columns(2)
                    for i, size_info in enumerate(cat_info["sizes"]):
                        with cols[i % 2]:
                            size_text = f"{size_info['name']} ({size_info['size'][0]}x{size_info['size'][1]})"
                            if st.checkbox(
                                size_text, 
                                key=f"size_{category}_{i}",
                                help=f"Для: {', '.join(size_info['marketplaces'])}"
                            ):
                                selected_sizes.append(size_info)
            
            # Пользовательский размер
            st.markdown("#### ✏️ Свой размер")
            use_custom = st.checkbox("Добавить свой размер")
            if use_custom:
                col_a, col_b = st.columns(2)
                with col_a:
                    custom_width = st.number_input("Ширина", min_value=1, value=800)
                with col_b:
                    custom_height = st.number_input("Высота", min_value=1, value=800)
                
                if st.button("➕ Добавить", use_container_width=True):
                    selected_sizes.append({
                        "name": f"Custom_{custom_width}x{custom_height}",
                        "size": (custom_width, custom_height)
                    })
            
            # Формат и качество
            st.markdown("#### 🎨 Настройки качества")
            output_format = st.selectbox(
                "Формат",
                ["JPEG", "PNG", "WEBP", "BMP", "TIFF", "HEIC"]
            )
            
            quality = st.slider(
                "Качество (%)",
                min_value=1, max_value=100, value=85,
                help="Выше качество = больше размер файла"
            )
            
            # Дополнительные опции
            st.markdown("#### 🔧 Дополнительно")
            col_c, col_d = st.columns(2)
            with col_c:
                maintain_exif = st.checkbox("Сохранить EXIF", value=True)
                auto_orient = st.checkbox("Авто-ориентация", value=True)
            with col_d:
                add_watermark = st.checkbox("Добавить водяной знак", value=False)
                optimize_size = st.checkbox("Оптимизировать размер", value=True)
            
            if add_watermark:
                watermark_text = st.text_input("Текст водяного знака", "© Ваш бренд")
            
            # Кнопка конвертации
            if st.button("🚀 Начать конвертацию", use_container_width=True, type="primary"):
                if selected_sizes:
                    process_images(uploaded_files, selected_sizes, output_format, quality)
                else:
                    st.warning("⚠️ Выберите хотя бы один размер")

with tab2:
    st.markdown("### 📊 Визуальный анализ размеров")
    
    # Создаем DataFrame для визуализации
    size_data = []
    for category, cat_info in SIZE_CATEGORIES.items():
        for size_info in cat_info["sizes"]:
            size_data.append({
                "Категория": category,
                "Название": size_info["name"],
                "Ширина": size_info["size"][0],
                "Высота": size_info["size"][1],
                "Площадь (мп)": (size_info["size"][0] * size_info["size"][1]) / 1000000,
                "Соотношение": f"{size_info['size'][0]/size_info['size'][1]:.2f}"
            })
    
    df_sizes = pd.DataFrame(size_data)
    
    # Диаграмма рассеяния размеров
    fig = px.scatter(
        df_sizes, 
        x="Ширина", 
        y="Высота",
        color="Категория",
        size="Площадь (мп)",
        hover_name="Название",
        title="Распределение размеров по категориям",
        labels={"Ширина": "Ширина (px)", "Высота": "Высота (px)"}
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Тепловая карта популярных размеров
    st.markdown("### 🔥 Популярные комбинации размеров")
    
    # Создаем матрицу популярности
    popular_sizes = defaultdict(int)
    for category, cat_info in SIZE_CATEGORIES.items():
        for size_info in cat_info["sizes"]:
            for mp in size_info["marketplaces"]:
                popular_sizes[(size_info["size"][0], size_info["size"][1])] += 1
    
    # Создаем тепловую карту
    sizes_list = list(popular_sizes.keys())
    if sizes_list:
        matrix_size = min(len(sizes_list), 10)
        # Здесь можно создать тепловую карту
    
    # Круговая диаграмма категорий
    fig_pie = px.pie(
        df_sizes, 
        names="Категория", 
        title="Распределение размеров по категориям",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with tab3:
    st.markdown("### 📋 Сравнение размеров маркетплейсов")
    
    # Создаем сравнительную таблицу
    comparison_data = []
    for mp_name, mp_info in MARKETPLACE_INFO.items():
        mp_sizes = []
        for category, cat_info in SIZE_CATEGORIES.items():
            for size_info in cat_info["sizes"]:
                if mp_name in size_info["marketplaces"] or "Все" in size_info["marketplaces"]:
                    mp_sizes.append(f"{size_info['size'][0]}x{size_info['size'][1]}")
        
        comparison_data.append({
            "Маркетплейс": f"{mp_info['icon']} {mp_name}",
            "Соотношение": mp_info["ratio"],
            "Доступные размеры": ", ".join(mp_sizes[:3]) + ("..." if len(mp_sizes) > 3 else ""),
            "Количество": len(mp_sizes)
        })
    
    df_comparison = pd.DataFrame(comparison_data)
    st.dataframe(
        df_comparison,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Маркетплейс": st.column_config.TextColumn("Маркетплейс", width="medium"),
            "Соотношение": st.column_config.TextColumn("Соотношение", width="small"),
            "Доступные размеры": st.column_config.TextColumn("Доступные размеры", width="large"),
            "Количество": st.column_config.NumberColumn("Размеров", width="small")
        }
    )
    
    # Визуализация сравнения
    fig = px.bar(
        df_comparison, 
        x="Маркетплейс", 
        y="Количество",
        title="Количество доступных размеров по маркетплейсам",
        color="Количество",
        color_continuous_scale="Viridis"
    )
    st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.markdown("### 🔍 Предпросмотр размеров")
    
    if uploaded_files:
        selected_file = st.selectbox(
            "Выберите изображение для предпросмотра",
            [f.name for f in uploaded_files]
        )
        
        if selected_file:
            file_idx = [f.name for f in uploaded_files].index(selected_file)
            img = Image.open(uploaded_files[file_idx])
            
            # Создаем сетку превью
            st.markdown("#### Сетка всех размеров")
            
            # Определяем размеры для показа
            preview_sizes = []
            for category, cat_info in SIZE_CATEGORIES.items():
                for size_info in cat_info["sizes"][:2]:  # Показываем первые 2 из каждой категории
                    preview_sizes.append(size_info)
            
            # Отображаем в сетке
            grid_cols = st.columns(3)
            for idx, size_info in enumerate(preview_sizes):
                with grid_cols[idx % 3]:
                    # Изменяем размер для превью
                    resized = img.resize(size_info["size"], Image.Resampling.LANCZOS)
                    
                    # Создаем информационный блок
                    st.markdown(
                        f"<div style='background: #f0f2f6; padding: 10px; border-radius: 10px; margin-bottom: 10px;'>",
                        unsafe_allow_html=True
                    )
                    st.image(resized, use_column=True)
                    st.markdown(
                        f"<p style='text-align: center; margin: 5px;'><b>{size_info['name']}</b><br>{size_info['size'][0]}x{size_info['size'][1]}</p>",
                        unsafe_allow_html=True
                    )
                    st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("👈 Загрузите изображение для предпросмотра")

with tab5:
    st.markdown("### 📈 Статистика использования")
    
    # Статистика по категориям
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_sizes = sum(len(cat["sizes"]) for cat in SIZE_CATEGORIES.values())
        st.markdown(
            f"""
            <div class="stats-card">
                <div class="metric-value">{total_sizes}</div>
                <div class="metric-label">Всего размеров</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col2:
        total_mps = len(MARKETPLACE_INFO)
        st.markdown(
            f"""
            <div class="stats-card">
                <div class="metric-value">{total_mps}</div>
                <div class="metric-label">Маркетплейсов</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col3:
        max_size = 4000  # Максимальный размер в пикселях
        st.markdown(
            f"""
            <div class="stats-card">
                <div class="metric-value">{max_size}px</div>
                <div class="metric-label">Макс. размер</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col4:
        st.markdown(
            f"""
            <div class="stats-card">
                <div class="metric-value">📊</div>
                <div class="metric-label">Активно</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # График популярности размеров
    st.markdown("### 📊 Распределение размеров по площади")
    
    # Создаем данные для гистограммы
    size_areas = []
    size_names = []
    for category, cat_info in SIZE_CATEGORIES.items():
        for size_info in cat_info["sizes"]:
            area = size_info["size"][0] * size_info["size"][1] / 1000000
            size_areas.append(area)
            size_names.append(f"{size_info['name']}\n{size_info['size'][0]}x{size_info['size'][1]}")
    
    fig_hist = px.histogram(
        x=size_areas,
        nbins=20,
        title="Распределение размеров по площади (мегапиксели)",
        labels={"x": "Площадь (мегапиксели)", "y": "Количество размеров"}
    )
    st.plotly_chart(fig_hist, use_container_width=True)

# Вспомогательные функции
def process_images(files, sizes, output_format, quality):
    """
    Обработка изображений с визуализацией прогресса
    """
    # Создаем прогресс-бар
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Создаем ZIP архив
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zip_file:
        total_operations = len(files) * len(sizes)
        completed = 0
        
        for file_idx, uploaded_file in enumerate(files):
            original_name = Path(uploaded_file.name).stem
            original_image = Image.open(uploaded_file)
            
            for size_idx, size_info in enumerate(sizes):
                # Обновляем статус
                status_text.text(f"Обработка: {uploaded_file.name} -> {size_info['name']}")
                
                # Изменяем размер
                resized = resize_with_crop(original_image, size_info["size"])
                
                # Конвертируем в RGB если нужно
                if output_format == "JPEG" and resized.mode in ('RGBA', 'P'):
                    resized = resized.convert('RGB')
                
                # Сохраняем в буфер
                img_buffer = io.BytesIO()
                save_params = {'quality': quality} if output_format in ["JPEG", "WEBP"] else {}
                resized.save(img_buffer, format=output_format, **save_params)
                
                # Создаем имя файла
                filename = f"{original_name}_{size_info['name']}_{size_info['size'][0]}x{size_info['size'][1]}.{output_format.lower()}"
                filename = "".join(c for c in filename if c.isalnum() or c in "._- ").strip()
                
                # Добавляем в ZIP
                zip_file.writestr(filename, img_buffer.getvalue())
                
                # Обновляем прогресс
                completed += 1
                progress_bar.progress(completed / total_operations)
        
        status_text.text("✅ Обработка завершена!")
    
    # Предлагаем скачать ZIP
    zip_buffer.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    st.download_button(
        label="📥 Скачать все (ZIP)",
        data=zip_buffer.getvalue(),
        file_name=f"images_{timestamp}.zip",
        mime="application/zip",
        use_container_width=True
    )

def resize_with_crop(image, target_size):
    """
    Изменяет размер изображения с обрезкой под целевой размер
    """
    target_width, target_height = target_size
    
    # Вычисляем соотношения сторон
    target_ratio = target_width / target_height
    image_ratio = image.width / image.height
    
    if image_ratio > target_ratio:
        # Изображение шире - подгоняем по высоте
        new_height = target_height
        new_width = int(new_height * image_ratio)
    else:
        # Изображение выше - подгоняем по ширине
        new_width = target_width
        new_height = int(new_width / image_ratio)
    
    # Изменяем размер
    resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Обрезаем до целевого размера
    left = (new_width - target_width) // 2
    top = (new_height - target_height) // 2
    right = left + target_width
    bottom = top + target_height
    
    return resized.crop((left, top, right, bottom))

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        <p>✨ ImageMagic Pro v2.0 | Создано для профессиональной работы с маркетплейсами</p>
        <p style='font-size: 0.8rem;'>Поддерживаются все популярные форматы и маркетплейсы</p>
    </div>
    """,
    unsafe_allow_html=True
)
