import streamlit as st
from PIL import Image
import io
from datetime import datetime
import zipfile
from pathlib import Path
import pandas as pd
import plotly.express as px
from collections import defaultdict

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

    def process_images(files, sizes, output_format, quality):
        progress_bar = st.progress(0)
        status_text = st.empty()
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            total_operations = len(files) * len(sizes)
            completed = 0

            for uploaded_file in files:
                try:
                    original_name = Path(uploaded_file.name).stem
                    original_image = Image.open(uploaded_file)
                except Exception as e:
                    st.error(f"Ошибка при открытии файла {uploaded_file.name}: {e}")
                    continue

                for size_info in sizes:
                    try:
                        status_text.text(f"Обработка: {uploaded_file.name} -> {size_info['name']}")
                        resized = resize_with_crop(original_image, size_info["size"])
                        if output_format == "JPEG" and resized.mode in ('RGBA', 'P'):
                            resized = resized.convert('RGB')
                        img_buffer = io.BytesIO()
                        save_params = {'quality': quality} if output_format in ["JPEG", "WEBP"] else {}
                        resized.save(img_buffer, format=output_format, **save_params)
                        filename = f"{original_name}_{size_info['name']}_{size_info['size'][0]}x{size_info['size'][1]}.{output_format.lower()}"
                        filename = "".join(c for c in filename if c.isalnum() or c in "._- ").strip()
                        zip_file.writestr(filename, img_buffer.getvalue())
                        completed += 1
                        progress_bar.progress(completed / total_operations)
                    except Exception as e:
                        st.error(f"Ошибка при обработке размера {size_info['name']}: {e}")
                        continue
            status_text.text("✅ Обработка завершена!")

        zip_buffer.seek(0)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button(
            label="📥 Скачать все (ZIP)",
            data=zip_buffer.getvalue(),
            file_name=f"images_{timestamp}.zip",
            mime="application/zip",
            use_container_width=True
        )

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
    /* Стиль заголовков и элементов интерфейса */
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

    # Заголовки
    st.markdown('<h1 class="main-header">✨ ImageMagic Pro</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Профессиональный конвертер изображений для маркетплейсов</p>', unsafe_allow_html=True)

    # Размеры по категориям
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

    # Маркетплейсы
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

    # ===================== БОКОВАЯ ПАНЕЛЬ =====================

    with st.sidebar:
        # Исправленный отступ
        st.image("https://via.placeholder.com/300x100/FF4B4B/FFFFFF?text=ImageMagic+Pro", use_column_width=True)
        st.markdown("## 🎯 Быстрый старт")
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
            # Выбор маркетплейсов
            if 'selected_marketplaces' not in st.session_state:
                st.session_state['selected_marketplaces'] = []
            for mp_name, mp_info in MARKETPLACE_INFO.items():
                if st.button(f"{mp_info['icon']} {mp_name}", key=f"mp_{mp_name}"):
                    if mp_name not in st.session_state['selected_marketplaces']:
                        st.session_state['selected_marketplaces'].append(mp_name)
                    else:
                        st.session_state['selected_marketplaces'].remove(mp_name)
            selected_marketplaces = st.session_state['selected_marketplaces']
            if selected_marketplaces:
                st.write("Выбрано:", ", ".join(selected_marketplaces))
            # Рекомендуемые размеры
            if selected_marketplaces:
                recommended_sizes = []
                for mp in selected_marketplaces:
                    for category, cat_info in SIZE_CATEGORIES.items():
                        for size_info in cat_info["sizes"]:
                            if mp in size_info["marketplaces"] or "Все" in size_info["marketplaces"]:
                                if size_info not in recommended_sizes:
                                    recommended_sizes.append(size_info)
                st.success(f"Рекомендуется {len(recommended_sizes)} размеров")
        elif mode == "📊 Анализ изображений":
            analyze_quality = st.checkbox("Анализ качества", value=True)
            analyze_colors = st.checkbox("Цветовой анализ", value=True)
            analyze_metadata = st.checkbox("Извлечь метаданные", value=False)
            detect_duplicates = st.checkbox("Поиск дубликатов", value=False)
        elif mode == "🔄 Пакетное переименование":
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

    # ===================== ОСНОВНЫЕ ВКЛАДКИ =====================

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📸 Конвертер", "📊 Визуализация", "📋 Сравнение размеров",
        "🔍 Предпросмотр сетки", "📈 Статистика"
    ])

    # --------------------- Таб 1: Конвертер ---------------------
    with tab1:
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("### 📤 Загрузка изображений")
            uploaded_files = st.file_uploader(
                "Перетащите файлы сюда",
                type=['png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp', 'heic'],
                accept_multiple_files=True
            )
            if uploaded_files:
                st.session_state['uploaded_files'] = uploaded_files
                st.success(f"✅ Загружено: {len(uploaded_files)} файлов")
                with st.expander("📸 Превью загруженных"):
                    preview_cols = st.columns(4)
                    for idx, file in enumerate(uploaded_files[:8]):
                        with preview_cols[idx % 4]:
                            img = Image.open(file)
                            st.image(img, caption=f"{file.name[:10]}...", use_column=True)
            else:
                st.session_state['uploaded_files'] = []

        with col2:
            if st.session_state.get('uploaded_files'):
                st.markdown("### ⚙️ Параметры конвертации")
                # Размеры
                st.markdown("#### 📐 Выберите размеры")
                if 'selected_sizes' not in st.session_state:
                    st.session_state['selected_sizes'] = []
                selected_sizes = st.session_state['selected_sizes']
                for category, cat_info in SIZE_CATEGORIES.items():
                    with st.expander(f"{category} - {cat_info['description']}"):
                        for i, size_info in enumerate(cat_info["sizes"]):
                            key_name = f"size_{category}_{i}"
                            if st.checkbox(
                                f"{size_info['name']} ({size_info['size'][0]}x{size_info['size'][1]})",
                                key=key_name
                            ):
                                if size_info not in selected_sizes:
                                    selected_sizes.append(size_info)
                # Свой размер
                use_custom = st.checkbox("Добавить свой размер")
                if use_custom:
                    col_a, col_b = st.columns(2)
                    with col_a:
                        custom_width = st.number_input("Ширина", min_value=1, value=800)
                    with col_b:
                        custom_height = st.number_input("Высота", min_value=1, value=800)
                    if st.button("➕ Добавить", key="add_custom_size"):
                        size_name = f"Custom_{custom_width}x{custom_height}"
                        size_dict = {"name": size_name, "size": (custom_width, custom_height)}
                        if size_dict not in selected_sizes:
                            selected_sizes.append(size_dict)
                st.session_state['selected_sizes'] = selected_sizes

                # Формат и качество
                st.markdown("#### 🎨 Настройки качества")
                output_format = st.selectbox("Формат", ["JPEG", "PNG", "WEBP", "BMP", "TIFF", "HEIC"])
                quality = st.slider("Качество (%)", 1, 100, 85)
                # Дополнительно
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
                if st.button("🚀 Начать конвертацию", key="start_conversion"):
                    if st.session_state.get('uploaded_files') and st.session_state.get('selected_sizes'):
                        process_images(
                            st.session_state['uploaded_files'],
                            st.session_state['selected_sizes'],
                            output_format,
                            quality
                        )
                    else:
                        st.warning("⚠️ Выберите файлы и размеры для обработки")
            else:
                st.info("Загрузите изображения для конвертации.")

    # --------------------- Таб 2: Визуализация ---------------------
    with tab2:
        st.markdown("### 📊 Визуальный анализ размеров")
        size_data = []
        for category, cat_info in SIZE_CATEGORIES.items():
            for size_info in cat_info["sizes"]:
                size_data.append({
                    "Категория": category,
                    "Название": size_info["name"],
                    "Ширина": size_info["size"][0],
                    "Высота": size_info["size"][1],
                    "Площадь (мп)": (size_info["size"][0] * size_info["size"][1]) / 1_000_000,
                    "Соотношение": f"{size_info['size'][0]/size_info['size'][1]:.2f}"
                })
        df_sizes = pd.DataFrame(size_data)

        fig_scatter = px.scatter(
            df_sizes,
            x="Ширина",
            y="Высота",
            color="Категория",
            size="Площадь (мп)",
            hover_name="Название",
            title="Распределение размеров по категориям",
            labels={"Ширина": "Ширина (px)", "Высота": "Высота (px)"}
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

        st.markdown("### 🔥 Популярные комбинации размеров")
        # Можно добавить визуализацию популярных размеров
        # пропущено для краткости

        fig_pie = px.pie(
            df_sizes,
            names="Категория",
            title="Распределение размеров по категориям",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # --------------------- Таб 3: Сравнение ---------------------
    with tab3:
        st.markdown("### 📋 Сравнение размеров маркетплейсов")
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
        st.dataframe(df_comparison)
        fig_bar = px.bar(
            df_comparison,
            x="Маркетплейс",
            y="Количество",
            title="Количество доступных размеров по маркетплейсам",
            color="Количество",
            color_continuous_scale="Viridis"
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # --------------------- Таб 4: Предпросмотр ---------------------
    with tab4:
        st.markdown("### 🔍 Предпросмотр размеров")
        uploaded_files = st.session_state.get('uploaded_files', [])
        if uploaded_files:
            selected_file_name = st.selectbox(
                "Выберите изображение для предпросмотра",
                [f.name for f in uploaded_files]
            )
            if selected_file_name:
                file_idx = [f.name for f in uploaded_files].index(selected_file_name)
                img = Image.open(uploaded_files[file_idx])
                preview_sizes = []
                for category, cat_info in SIZE_CATEGORIES.items():
                    for size_info in cat_info["sizes"][:2]:
                        preview_sizes.append(size_info)
                grid_cols = st.columns(3)
                for idx, size_info in enumerate(preview_sizes):
                    with grid_cols[idx % 3]:
                        try:
                            resized = img.resize(size_info["size"], Image.Resampling.LANCZOS)
                            st.image(resized, caption=f"{size_info['name']} {size_info['size'][0]}x{size_info['size'][1]}")
                        except Exception as e:
                            st.error(f"Ошибка при создании превью: {e}")
        else:
            st.info("👈 Загрузите изображение для предпросмотра.")

    # --------------------- Таб 5: Статистика ---------------------
    with tab5:
        st.markdown("### 📈 Статистика использования")
        col1, col2, col3, col4 = st.columns(4)
        total_sizes = sum(len(cat["sizes"]) for cat in SIZE_CATEGORIES.values())
        col1.markdown(f"<div class='stats-card'><div class='metric-value'>{total_sizes}</div><div class='metric-label'>Всего размеров</div></div>", unsafe_allow_html=True)
        total_mps = len(MARKETPLACE_INFO)
        col2.markdown(f"<div class='stats-card'><div class='metric-value'>{total_mps}</div><div class='metric-label'>Маркетплейсов</div></div>", unsafe_allow_html=True)
        max_size = 4000
        col3.markdown(f"<div class='stats-card'><div class='metric-value'>{max_size}px</div><div class='metric-label'>Макс. размер</div></div>", unsafe_allow_html=True)
        col4.markdown(f"<div class='stats-card'><div class='metric-value'>📊</div><div class='metric-label'>Активно</div></div>", unsafe_allow_html=True)

        size_areas = []
        for category, cat_info in SIZE_CATEGORIES.items():
            for size_info in cat_info["sizes"]:
                area = size_info["size"][0] * size_info["size"][1] / 1_000_000
                size_areas.append(area)
        fig_hist = px.histogram(
            x=size_areas,
            nbins=20,
            title="Распределение размеров по площади (мегапиксели)",
            labels={"x": "Площадь (мегапиксели)", "y": "Количество размеров"}
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    # ===================== ВЫВОД =====================

    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'>✨ ImageMagic Pro v2.0 | Создано для профессиональной работы с маркетплейсами</div>",
        unsafe_allow_html=True
    )

# Вызов функции для запуска
if __name__ == "__main__":
    run_app()
