import streamlit as st
from PIL import Image, ImageEnhance, ImageOps, ImageDraw, ImageFilter, ImageFont
import io
import zipfile
import os
from datetime import datetime
import numpy as np
import pandas as pd
import math

# ================ КОНФИГУРАЦИЯ СТРАНИЦЫ ================

st.set_page_config(
    page_title="PRO Инфографика для маркетплейсов",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================ КЛАСС ДЛЯ СОЗДАНИЯ ИНФОГРАФИКИ ================

class InfographicGenerator:
    """Генератор профессиональной инфографики для карточек товаров"""
    
    def __init__(self):
        self.fonts = {}
        self.templates = {}
        self.icons = {}
    
    @staticmethod
    def hex_to_rgb(hex_color):
        """Конвертация HEX в RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def create_size_chart_infographic(self, product_data, design_settings):
        """Создание инфографики с размерной сеткой"""
        try:
            width = design_settings.get('width', 900)
            height = design_settings.get('height', 1200)
            bg_color = self.hex_to_rgb(design_settings.get('bg_color', '#FFFFFF'))
            
            img = Image.new('RGB', (width, height), bg_color)
            draw = ImageDraw.Draw(img)
            
            # Заголовок
            title_bg = self.hex_to_rgb(design_settings.get('title_bg', '#2C3E50'))
            draw.rectangle([0, 0, width, 80], fill=title_bg)
            
            title_text = product_data.get('title', 'Размерная сетка')
            draw.text((50, 30), title_text, fill='white')
            
            y_pos = 120
            
            # Изображение товара (если есть)
            if 'product_image' in product_data and product_data['product_image']:
                prod_img = product_data['product_image'].copy()
                prod_img.thumbnail((300, 300))
                img.paste(prod_img, (50, y_pos))
                y_pos += 320
            
            # Таблица размеров
            sizes = product_data.get('sizes', ['S', 'M', 'L', 'XL'])
            measurements = product_data.get('measurements', ['Длина', 'Ширина', 'Высота'])
            
            # Заголовки таблицы
            col_width = (width - 100) // (len(sizes) + 1)
            x_positions = [50 + i * col_width for i in range(len(sizes) + 1)]
            
            # Рисуем таблицу
            row_height = 50
            
            # Заголовки колонок
            draw.rectangle([50, y_pos, width-50, y_pos+row_height], 
                          fill=self.hex_to_rgb(design_settings.get('table_header', '#3498DB')))
            draw.text((x_positions[0] + 10, y_pos + 15), "Размер", fill='white')
            for i, size in enumerate(sizes):
                draw.text((x_positions[i+1] + 10, y_pos + 15), str(size), fill='white')
            
            y_pos += row_height
            
            # Строки с измерениями
            for meas in measurements:
                draw.rectangle([50, y_pos, width-50, y_pos+row_height], 
                              outline=self.hex_to_rgb('#BDC3C7'), width=1)
                draw.text((x_positions[0] + 10, y_pos + 15), meas, fill='black')
                
                for i, size in enumerate(sizes):
                    value = product_data.get(f'{size}_{meas}', '—')
                    draw.text((x_positions[i+1] + 10, y_pos + 15), str(value), fill='black')
                
                y_pos += row_height
            
            # Рекомендации по выбору размера
            if 'size_tip' in product_data:
                y_pos += 20
                draw.rectangle([50, y_pos, width-50, y_pos+80], 
                              fill=self.hex_to_rgb('#F39C12'), outline=self.hex_to_rgb('#E67E22'), width=2)
                draw.text((60, y_pos + 15), "💡 Как выбрать размер:", fill='white')
                draw.text((60, y_pos + 45), product_data['size_tip'], fill='white')
            
            return img
        except Exception as e:
            st.error(f"Ошибка создания размерной сетки: {str(e)}")
            return Image.new('RGB', (900, 1200), 'white')
    
    def create_specs_infographic(self, product_data, design_settings):
        """Создание инфографики с техническими характеристиками"""
        try:
            width = design_settings.get('width', 900)
            height = design_settings.get('height', 1200)
            bg_color = self.hex_to_rgb(design_settings.get('bg_color', '#FFFFFF'))
            
            img = Image.new('RGB', (width, height), bg_color)
            draw = ImageDraw.Draw(img)
            
            # Градиентный фон
            for i in range(height):
                color_value = int(255 - (i / height) * 50)
                draw.line([(0, i), (width, i)], fill=(color_value, color_value, color_value))
            
            # Заголовок
            title_rect = [(0, 0), (width, 100)]
            draw.rectangle(title_rect, fill=self.hex_to_rgb('#2980B9'))
            draw.text((50, 35), f"📊 {product_data.get('title', 'Характеристики')}", fill='white')
            
            y_pos = 130
            
            # Изображение товара справа
            if 'product_image' in product_data and product_data['product_image']:
                prod_img = product_data['product_image'].copy()
                prod_img.thumbnail((250, 250))
                img.paste(prod_img, (width - 280, y_pos))
            
            # Основные характеристики в две колонки
            specs = product_data.get('specs', {})
            col1_x, col2_x = 50, width // 2 + 30
            col_width = width // 2 - 80
            
            for i, (key, value) in enumerate(specs.items()):
                if i % 2 == 0:
                    x = col1_x
                else:
                    x = col2_x
                
                # Карточка характеристики
                card_y = y_pos + (i // 2) * 80
                draw.rectangle([x, card_y, x + col_width, card_y + 70], 
                              fill='white', outline=self.hex_to_rgb('#3498DB'), width=2)
                
                # Иконка (упрощенно)
                draw.ellipse([x + 10, card_y + 15, x + 40, card_y + 45], 
                            fill=self.hex_to_rgb('#3498DB'))
                
                # Текст
                draw.text((x + 50, card_y + 15), str(key), fill='black')
                draw.text((x + 50, card_y + 40), str(value), fill=self.hex_to_rgb('#7F8C8D'))
            
            y_pos += ((len(specs) + 1) // 2) * 80 + 20
            
            # Преимущества
            if 'benefits' in product_data:
                draw.rectangle([50, y_pos, width-50, y_pos + 100 + len(product_data['benefits'])*30], 
                              fill=self.hex_to_rgb('#27AE60'), outline=self.hex_to_rgb('#229954'), width=2)
                draw.text((70, y_pos + 15), "✓ Преимущества:", fill='white')
                
                for i, benefit in enumerate(product_data['benefits']):
                    draw.text((90, y_pos + 50 + i*30), f"• {benefit}", fill='white')
            
            return img
        except Exception as e:
            st.error(f"Ошибка создания характеристик: {str(e)}")
            return Image.new('RGB', (900, 1200), 'white')
    
    def create_comparison_infographic(self, product_data, design_settings):
        """Создание инфографики сравнения с конкурентами"""
        try:
            width = design_settings.get('width', 900)
            height = design_settings.get('height', 1200)
            bg_color = self.hex_to_rgb(design_settings.get('bg_color', '#FFFFFF'))
            
            img = Image.new('RGB', (width, height), bg_color)
            draw = ImageDraw.Draw(img)
            
            # Заголовок
            draw.rectangle([0, 0, width, 80], fill=self.hex_to_rgb('#8E44AD'))
            draw.text((50, 30), f"⚡ {product_data.get('title', 'Сравнение')}", fill='white')
            
            y_pos = 120
            
            # Наш продукт
            our_product = product_data.get('our_product', 'Наш товар')
            competitors = product_data.get('competitors', [])
            features = product_data.get('features', [])
            
            # Заголовки колонок
            col_width = (width - 100) // (len(competitors) + 2)
            x_positions = [50 + i * col_width for i in range(len(competitors) + 2)]
            
            # Шапка сравнения
            draw.rectangle([50, y_pos, width-50, y_pos+60], fill=self.hex_to_rgb('#34495E'))
            draw.text((x_positions[0] + 10, y_pos + 20), "Характеристика", fill='white')
            draw.text((x_positions[1] + 10, y_pos + 20), our_product[:15], fill='white')
            
            for i, comp in enumerate(competitors):
                draw.text((x_positions[i+2] + 10, y_pos + 20), comp[:15], fill='white')
            
            y_pos += 70
            
            # Строки сравнения
            for feature in features:
                draw.rectangle([50, y_pos, width-50, y_pos+50], 
                              outline=self.hex_to_rgb('#BDC3C7'), width=1)
                draw.text((x_positions[0] + 10, y_pos + 15), feature['name'], fill='black')
                
                # Наш продукт (зеленый)
                our_value = feature.get('our', '—')
                draw.text((x_positions[1] + 10, y_pos + 15), str(our_value), 
                         fill=self.hex_to_rgb('#27AE60'))
                
                # Конкуренты
                for i, comp_value in enumerate(feature.get('competitors', [])):
                    color = self.hex_to_rgb('#E74C3C') if i == 0 else self.hex_to_rgb('#95A5A6')
                    draw.text((x_positions[i+2] + 10, y_pos + 15), str(comp_value), fill=color)
                
                y_pos += 55
            
            # Итоговая рекомендация
            y_pos += 20
            draw.rectangle([50, y_pos, width-50, y_pos+80], fill=self.hex_to_rgb('#27AE60'))
            draw.text((60, y_pos + 20), "🏆 Почему стоит выбрать нас:", fill='white')
            draw.text((60, y_pos + 50), product_data.get('conclusion', 'Лучшее соотношение цены и качества'), 
                     fill='white')
            
            return img
        except Exception as e:
            st.error(f"Ошибка создания сравнения: {str(e)}")
            return Image.new('RGB', (900, 1200), 'white')
    
    def create_usp_infographic(self, product_data, design_settings):
        """Создание инфографики с уникальными торговыми предложениями"""
        try:
            width = design_settings.get('width', 900)
            height = design_settings.get('height', 1200)
            bg_color = self.hex_to_rgb(design_settings.get('bg_color', '#F8F9FA'))
            
            img = Image.new('RGB', (width, height), bg_color)
            draw = ImageDraw.Draw(img)
            
            # Верхний баннер
            draw.rectangle([0, 0, width, 200], fill=self.hex_to_rgb('#E67E22'))
            
            # Название товара
            title = product_data.get('title', 'НАШ ТОВАР')
            draw.text((50, 50), title.upper(), fill='white')
            draw.text((50, 100), product_data.get('subtitle', 'Почему стоит выбрать?'), fill='white')
            
            y_pos = 250
            
            # Список УТП в виде карточек
            usp_list = product_data.get('usp', [])
            cols = 2
            card_width = (width - 150) // cols
            card_height = 150
            
            for i, usp in enumerate(usp_list):
                row = i // cols
                col = i % cols
                
                x = 50 + col * (card_width + 50)
                y = y_pos + row * (card_height + 30)
                
                # Карточка
                draw.rectangle([x, y, x + card_width, y + card_height], 
                              fill='white', outline=self.hex_to_rgb('#E67E22'), width=3)
                
                # Иконка
                icon_x = x + 30
                icon_y = y + 30
                draw.ellipse([icon_x, icon_y, icon_x + 50, icon_y + 50], 
                            fill=self.hex_to_rgb('#E67E22'))
                draw.text((icon_x + 15, icon_y + 15), str(i+1), fill='white')
                
                # Заголовок
                draw.text((x + 100, y + 30), usp.get('title', f'Преимущество {i+1}'), 
                         fill='black')
                
                # Описание
                description = usp.get('description', '')
                lines = self.wrap_text(description, 25)
                for j, line in enumerate(lines[:2]):
                    draw.text((x + 100, y + 60 + j*25), line, fill=self.hex_to_rgb('#7F8C8D'))
            
            y_pos += ((len(usp_list) + cols - 1) // cols) * (card_height + 50)
            
            # Призыв к действию
            draw.rectangle([50, y_pos, width-50, y_pos+100], fill=self.hex_to_rgb('#27AE60'))
            draw.text((width//2 - 100, y_pos + 35), "🛒 КУПИТЬ СЕЙЧАС", fill='white')
            draw.text((width//2 - 80, y_pos + 65), product_data.get('price', 'Цена по запросу'), 
                     fill='white')
            
            return img
        except Exception as e:
            st.error(f"Ошибка создания УТП: {str(e)}")
            return Image.new('RGB', (900, 1200), 'white')
    
    def create_instruction_infographic(self, product_data, design_settings):
        """Создание инфографики с инструкцией по применению"""
        try:
            width = design_settings.get('width', 900)
            height = design_settings.get('height', 1200)
            bg_color = self.hex_to_rgb(design_settings.get('bg_color', '#FFFFFF'))
            
            img = Image.new('RGB', (width, height), bg_color)
            draw = ImageDraw.Draw(img)
            
            # Заголовок
            draw.rectangle([0, 0, width, 80], fill=self.hex_to_rgb('#3498DB'))
            draw.text((50, 30), f"📖 {product_data.get('title', 'Инструкция')}", fill='white')
            
            y_pos = 120
            
            # Шаги инструкции
            steps = product_data.get('steps', [])
            
            for i, step in enumerate(steps):
                # Номер шага
                draw.ellipse([50, y_pos, 100, y_pos+50], fill=self.hex_to_rgb('#3498DB'))
                draw.text((65, y_pos+15), str(i+1), fill='white')
                
                # Заголовок шага
                draw.text((120, y_pos+10), step.get('title', f'Шаг {i+1}'), fill='black')
                
                # Описание
                description = step.get('description', '')
                lines = self.wrap_text(description, 50)
                for j, line in enumerate(lines):
                    draw.text((120, y_pos+40 + j*25), line, fill=self.hex_to_rgb('#7F8C8D'))
                
                # Схематичное изображение
                if 'icon' in step:
                    icon_rect = [width-150, y_pos, width-50, y_pos+80]
                    draw.rectangle(icon_rect, outline=self.hex_to_rgb('#BDC3C7'), width=2)
                    draw.text((width-130, y_pos+30), step['icon'], fill='black')
                
                # Высота шага зависит от количества текста
                step_height = 80 + len(lines) * 25
                y_pos += step_height
                
                # Разделитель
                if i < len(steps) - 1:
                    draw.line([(50, y_pos-10), (width-50, y_pos-10)], 
                             fill=self.hex_to_rgb('#BDC3C7'), width=2)
            
            # Предупреждение
            if 'warning' in product_data:
                y_pos += 20
                draw.rectangle([50, y_pos, width-50, y_pos+80], 
                              fill=self.hex_to_rgb('#E74C3C'), outline=self.hex_to_rgb('#C0392B'), width=2)
                draw.text((60, y_pos+15), "⚠️ ВНИМАНИЕ:", fill='white')
                draw.text((60, y_pos+45), product_data['warning'], fill='white')
            
            return img
        except Exception as e:
            st.error(f"Ошибка создания инструкции: {str(e)}")
            return Image.new('RGB', (900, 1200), 'white')
    
    def create_package_infographic(self, product_data, design_settings):
        """Создание инфографики с информацией об упаковке"""
        try:
            width = design_settings.get('width', 900)
            height = design_settings.get('height', 1200)
            bg_color = self.hex_to_rgb(design_settings.get('bg_color', '#F5F5F5'))
            
            img = Image.new('RGB', (width, height), bg_color)
            draw = ImageDraw.Draw(img)
            
            # Верхняя часть с коробкой
            draw.rectangle([0, 0, width, 250], fill=self.hex_to_rgb('#2C3E50'))
            
            # Рисуем коробку
            box_top = [(width//2 - 150, 70), (width//2 + 150, 170)]
            draw.rectangle(box_top, fill=self.hex_to_rgb('#E67E22'), outline='white', width=3)
            
            # Крышка
            draw.polygon([(width//2 - 170, 70), (width//2, 40), (width//2 + 170, 70)], 
                        fill=self.hex_to_rgb('#F39C12'))
            
            draw.text((width//2 - 50, 110), "ПОСЫЛКА", fill='white')
            
            y_pos = 280
            
            # Информация об упаковке
            package_info = product_data.get('package', {})
            
            # Карточки с информацией
            cards = [
                ("📦 Размер упаковки", package_info.get('size', '30x30x30 см')),
                ("⚖️ Вес", package_info.get('weight', '1.5 кг')),
                ("📦 В коробке", package_info.get('quantity', '1 шт')),
                ("🏭 Производитель", package_info.get('manufacturer', 'Россия'))
            ]
            
            for i, (label, value) in enumerate(cards):
                card_x = 50 + (i % 2) * 400
                card_y = y_pos + (i // 2) * 120
                
                draw.rectangle([card_x, card_y, card_x + 350, card_y + 100], 
                              fill='white', outline=self.hex_to_rgb('#3498DB'), width=2)
                draw.text((card_x + 20, card_y + 20), label, fill='black')
                draw.text((card_x + 20, card_y + 60), value, fill=self.hex_to_rgb('#2C3E50'))
            
            y_pos += 300
            
            # Состав комплекта
            if 'contents' in product_data:
                draw.rectangle([50, y_pos, width-50, y_pos + 60 + len(product_data['contents'])*30], 
                              fill='white', outline=self.hex_to_rgb('#27AE60'), width=2)
                draw.text((70, y_pos + 15), "📋 В комплекте:", fill='black')
                
                for i, item in enumerate(product_data['contents']):
                    draw.text((90, y_pos + 50 + i*30), f"✓ {item}", fill=self.hex_to_rgb('#27AE60'))
            
            return img
        except Exception as e:
            st.error(f"Ошибка создания упаковки: {str(e)}")
            return Image.new('RGB', (900, 1200), 'white')
    
    def create_certificate_infographic(self, product_data, design_settings):
        """Создание инфографики с сертификатами и наградами"""
        try:
            width = design_settings.get('width', 900)
            height = design_settings.get('height', 1200)
            bg_color = self.hex_to_rgb(design_settings.get('bg_color', '#F8F9FA'))
            
            img = Image.new('RGB', (width, height), bg_color)
            draw = ImageDraw.Draw(img)
            
            # Верхний баннер
            draw.rectangle([0, 0, width, 150], fill=self.hex_to_rgb('#F1C40F'))
            draw.text((50, 50), "🏆 СЕРТИФИКАТЫ И НАГРАДЫ", fill='black')
            draw.text((50, 100), product_data.get('title', 'Подтвержденное качество'), fill='black')
            
            y_pos = 200
            
            # Сертификаты
            certificates = product_data.get('certificates', [])
            cols = 2
            card_width = (width - 150) // cols
            card_height = 200
            
            for i, cert in enumerate(certificates):
                row = i // cols
                col = i % cols
                
                x = 50 + col * (card_width + 50)
                y = y_pos + row * (card_height + 30)
                
                # Рамка сертификата
                draw.rectangle([x, y, x + card_width, y + card_height], 
                              fill='white', outline=self.hex_to_rgb('#F1C40F'), width=3)
                
                # Медаль
                draw.ellipse([x + 50, y + 30, x + 150, y + 130], 
                            fill=self.hex_to_rgb('#F1C40F'), outline=self.hex_to_rgb('#D4AC0D'), width=3)
                draw.text((x + 85, y + 70), "🏅", fill='black')
                
                # Название сертификата
                draw.text((x + 180, y + 50), cert.get('name', 'Сертификат'), fill='black')
                draw.text((x + 180, y + 80), cert.get('issuer', 'Орган сертификации'), 
                         fill=self.hex_to_rgb('#7F8C8D'))
                draw.text((x + 180, y + 110), cert.get('date', '2024'), 
                         fill=self.hex_to_rgb('#7F8C8D'))
            
            y_pos += ((len(certificates) + cols - 1) // cols) * (card_height + 50)
            
            # Соответствие стандартам
            if 'standards' in product_data:
                draw.rectangle([50, y_pos, width-50, y_pos + 80 + len(product_data['standards'])*30], 
                              fill=self.hex_to_rgb('#2980B9'))
                draw.text((70, y_pos + 20), "✓ Соответствует стандартам:", fill='white')
                
                for i, std in enumerate(product_data['standards']):
                    draw.text((90, y_pos + 60 + i*30), f"• {std}", fill='white')
            
            return img
        except Exception as e:
            st.error(f"Ошибка создания сертификатов: {str(e)}")
            return Image.new('RGB', (900, 1200), 'white')
    
    def create_price_infographic(self, product_data, design_settings):
        """Создание инфографики с ценами и акциями"""
        try:
            width = design_settings.get('width', 900)
            height = design_settings.get('height', 1200)
            bg_color = self.hex_to_rgb(design_settings.get('bg_color', '#FFFFFF'))
            
            img = Image.new('RGB', (width, height), bg_color)
            draw = ImageDraw.Draw(img)
            
            # Красный баннер для акции
            draw.rectangle([0, 0, width, 200], fill=self.hex_to_rgb('#E74C3C'))
            
            # Процент скидки
            discount = product_data.get('discount', '20')
            draw.text((50, 50), f"-{discount}%", fill='white')
            draw.text((50, 120), "СКИДКА", fill='white')
            
            # Цены
            old_price = product_data.get('old_price', '5000')
            new_price = product_data.get('new_price', '4000')
            currency = product_data.get('currency', '₽')
            
            draw.text((width-300, 50), f"{old_price} {currency}", fill='white')
            draw.line([(width-300, 85), (width-150, 85)], fill='white', width=3)
            draw.text((width-300, 100), f"{new_price} {currency}", fill='white')
            
            y_pos = 250
            
            # Преимущества покупки
            benefits = product_data.get('benefits', [
                "Бесплатная доставка",
                "Гарантия 2 года",
                "Подарок при покупке"
            ])
            
            for i, benefit in enumerate(benefits):
                draw.ellipse([50, y_pos + i*50, 80, y_pos + i*50 + 30], 
                            fill=self.hex_to_rgb('#27AE60'))
                draw.text((100, y_pos + i*50 + 5), benefit, fill='black')
            
            y_pos += len(benefits) * 50 + 30
            
            # Таймер акции
            if 'timer' in product_data:
                draw.rectangle([50, y_pos, width-50, y_pos+100], 
                              fill=self.hex_to_rgb('#F39C12'))
                draw.text((70, y_pos + 20), "⏰ До конца акции:", fill='white')
                draw.text((70, y_pos + 60), product_data['timer'], fill='white')
            
            return img
        except Exception as e:
            st.error(f"Ошибка создания цен: {str(e)}")
            return Image.new('RGB', (900, 1200), 'white')
    
    def create_materials_infographic(self, product_data, design_settings):
        """Создание инфографики с материалами и составом"""
        try:
            width = design_settings.get('width', 900)
            height = design_settings.get('height', 1200)
            bg_color = self.hex_to_rgb(design_settings.get('bg_color', '#F8F9FA'))
            
            img = Image.new('RGB', (width, height), bg_color)
            draw = ImageDraw.Draw(img)
            
            # Заголовок
            draw.rectangle([0, 0, width, 80], fill=self.hex_to_rgb('#27AE60'))
            draw.text((50, 30), f"🔬 {product_data.get('title', 'Состав и материалы')}", fill='white')
            
            y_pos = 120
            
            # Основные материалы
            materials = product_data.get('materials', {})
            
            # Круговая диаграмма (упрощенно)
            center_x, center_y = width // 2, 300
            radius = 150
            
            draw.ellipse([center_x - radius, center_y - radius, 
                         center_x + radius, center_y + radius], 
                        outline='black', width=2)
            
            # Сегменты (упрощенно)
            colors = ['#3498DB', '#E74C3C', '#F39C12', '#27AE60', '#9B59B6']
            total = sum(materials.values())
            start_angle = 0
            
            legend_y = center_y + radius + 30
            for i, (mat, value) in enumerate(materials.items()):
                # Сегмент
                angle = 360 * value / total
                # В реальном приложении здесь нужно рисовать сектор
                # Упрощенно: просто показываем проценты
                
                # Легенда
                draw.rectangle([50, legend_y + i*40, 80, legend_y + i*40 + 30], 
                              fill=self.hex_to_rgb(colors[i % len(colors)]))
                draw.text((100, legend_y + i*40 + 5), f"{mat}: {value}%", fill='black')
            
            y_pos = 500
            
            # Детальный состав
            if 'composition' in product_data:
                draw.rectangle([50, y_pos, width-50, y_pos + 150], 
                              fill='white', outline=self.hex_to_rgb('#27AE60'), width=2)
                draw.text((70, y_pos + 15), "📋 Детальный состав:", fill='black')
                
                comp_lines = self.wrap_text(product_data['composition'], 60)
                for i, line in enumerate(comp_lines):
                    draw.text((70, y_pos + 50 + i*25), line, fill=self.hex_to_rgb('#7F8C8D'))
            
            return img
        except Exception as e:
            st.error(f"Ошибка создания материалов: {str(e)}")
            return Image.new('RGB', (900, 1200), 'white')
    
    def wrap_text(self, text, max_chars):
        """Разбивка текста на строки"""
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 <= max_chars:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    def combine_with_product_image(self, infographic, product_image, position='right'):
        """Объединение инфографики с фото товара"""
        try:
            if not product_image:
                return infographic
            
            # Изменяем размер фото
            product_image.thumbnail((400, 400))
            
            # Создаем холст
            width = max(infographic.width, product_image.width + 50)
            height = infographic.height + product_image.height + 50
            
            result = Image.new('RGB', (width, height), 'white')
            
            if position == 'right':
                result.paste(infographic, (0, 0))
                result.paste(product_image, (infographic.width + 20, 20))
            elif position == 'left':
                result.paste(product_image, (20, 20))
                result.paste(infographic, (product_image.width + 40, 0))
            elif position == 'top':
                result.paste(product_image, ((width - product_image.width)//2, 20))
                result.paste(infographic, (0, product_image.height + 40))
            else:  # bottom
                result.paste(infographic, (0, 0))
                result.paste(product_image, ((width - product_image.width)//2, infographic.height + 20))
            
            return result
        except Exception as e:
            st.error(f"Ошибка объединения: {str(e)}")
            return infographic

# ================ ИНТЕРФЕЙС ПОЛЬЗОВАТЕЛЯ ================

def main():
    st.title("📊 PRO Инфографика для карточек товаров")
    st.markdown("---")
    
    # Инициализация
    if 'generator' not in st.session_state:
        st.session_state['generator'] = InfographicGenerator()
        st.session_state['infographics'] = []
    
    generator = st.session_state['generator']
    
    # Боковая панель с типами инфографики
    with st.sidebar:
        st.header("🎨 Тип инфографики")
        
        infographic_type = st.selectbox(
            "Выберите тип",
            [
                "📏 Размерная сетка",
                "📊 Технические характеристики",
                "⚖️ Сравнение с конкурентами",
                "💡 УТП и преимущества",
                "📖 Инструкция",
                "📦 Упаковка и комплектация",
                "🏆 Сертификаты",
                "💰 Цены и акции",
                "🔬 Состав и материалы"
            ]
        )
        
        st.markdown("---")
        st.header("🎨 Дизайн")
        
        # Настройки дизайна
        width = st.number_input("Ширина (px)", 600, 2000, 900)
        height = st.number_input("Высота (px)", 800, 3000, 1200)
        bg_color = st.color_picker("Цвет фона", "#FFFFFF")
        title_color = st.color_picker("Цвет заголовка", "#2C3E50")
        
        design_settings = {
            'width': width,
            'height': height,
            'bg_color': bg_color,
            'title_color': title_color
        }
        
        st.markdown("---")
        st.caption("💡 Загрузите данные и изображения для создания инфографики")
    
    # Основные вкладки
    tab1, tab2, tab3 = st.tabs(["📁 Данные", "🖼️ Предпросмотр", "📊 Результаты"])
    
    with tab1:
        st.header("1. Загрузка данных")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Excel с данными")
            data_file = st.file_uploader(
                "Загрузите файл с данными",
                type=["xlsx", "xls", "csv"],
                key="data_file"
            )
            
            if data_file:
                try:
                    if data_file.name.endswith('.csv'):
                        df = pd.read_csv(data_file)
                    else:
                        df = pd.read_excel(data_file)
                    
                    st.dataframe(df.head(), use_container_width=True)
                    st.session_state['df'] = df
                except Exception as e:
                    st.error(f"Ошибка: {str(e)}")
        
        with col2:
            st.subheader("🖼️ Изображения товаров")
            product_images = st.file_uploader(
                "Загрузите фото товаров",
                type=["jpg", "jpeg", "png"],
                accept_multiple_files=True,
                key="product_images"
            )
            
            if product_images:
                st.success(f"Загружено {len(product_images)} изображений")
                # Правильное присвоение в session_state
                st.session_state['product_images'] = {f.name: Image.open(f) for f in product_images}
        
        # Данные для конкретного типа инфографики
        st.subheader(f"📝 Данные для {infographic_type}")
        
        # В зависимости от выбранного типа собираем данные
        if 'infographic_type' not in st.session_state:
            st.session_state['infographic_type'] = infographic_type
        else:
            st.session_state['infographic_type'] = infographic_type
        
        if infographic_type == "📏 Размерная сетка":
            sizes = st.text_input("Размеры (через запятую)", "XS,S,M,L,XL")
            measurements = st.text_input("Измерения (через запятую)", "Длина,Ширина,Высота")
            size_tip = st.text_input("Совет по выбору", "Выбирайте по самой широкой части")
            st.session_state['infographic_data'] = {
                'title': 'Размерная сетка',
                'sizes': [s.strip() for s in sizes.split(',')],
                'measurements': [m.strip() for m in measurements.split(',')],
                'size_tip': size_tip
            }
        elif infographic_type == "📊 Технические характеристики":
            specs_text = st.text_area(
                "Характеристики (каждая с новой строки)",
                "Мощность: 100 Вт\nНапряжение: 12 В\nВес: 1.5 кг"
            )
            benefits = st.text_area("Преимущества (каждое с новой строки)", 
                                    "Высокое качество\nДолговечность\nГарантия")
            specs = {}
            for line in specs_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    specs[key.strip()] = value.strip()
            st.session_state['infographic_data'] = {
                'title': 'Технические характеристики',
                'specs': specs,
                'benefits': [b.strip() for b in benefits.split('\n') if b.strip()]
            }
        elif infographic_type == "⚖️ Сравнение с конкурентами":
            our_product = st.text_input("Название нашего товара", "Наш товар")
            competitors = st.text_input("Конкуренты (через запятую)", "Бренд А, Бренд Б, Бренд В")
            features_text = st.text_area(
                "Характеристики (каждая с новой строки в формате: Название | Наше значение | Значение А | Значение Б | Значение В)",
                "Цена | 1000 | 1500 | 1200 | 1800\nКачество | 5 | 4 | 3 | 4"
            )
            features = []
            for line in features_text.split('\n'):
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 2:
                    feature = {
                        'name': parts[0],
                        'our': parts[1] if len(parts) > 1 else '',
                        'competitors': parts[2:] if len(parts) > 2 else []
                    }
                    features.append(feature)
            st.session_state['infographic_data'] = {
                'title': 'Сравнение',
                'our_product': our_product,
                'competitors': [c.strip() for c in competitors.split(',')],
                'features': features,
                'conclusion': 'Лучшее соотношение цены и качества'
            }
        elif infographic_type == "💡 УТП и преимущества":
            title = st.text_input("Название товара", "Наш товар")
            subtitle = st.text_input("Подзаголовок", "Почему стоит выбрать?")
            price = st.text_input("Цена", "1 500 ₽")
            benefits = st.text_area("Преимущества", "Высокое качество\nДолговечность\nГарантия")
            usp_items = []
            for i in range(5):
                with st.expander(f"Преимущество {i+1}"):
                    usp_title = st.text_input(f"Заголовок {i+1}", f"Преимущество {i+1}", key=f"usp_title_{i}")
                    usp_desc = st.text_area(f"Описание {i+1}", f"Описание преимущества {i+1}", key=f"usp_desc_{i}")
                    if usp_title:
                        usp_items.append({'title': usp_title, 'description': usp_desc})
            st.session_state['infographic_data'] = {
                'title': title,
                'subtitle': subtitle,
                'price': price,
                'usp': usp_items
            }
        elif infographic_type == "📖 Инструкция":
            title = st.text_input("Название", "Инструкция по применению")
            warning = st.text_input("Предупреждение", "Перед использованием ознакомьтесь с инструкцией")
            steps = []
            for i in range(5):
                with st.expander(f"Шаг {i+1}"):
                    step_title = st.text_input(f"Заголовок шага {i+1}", f"Шаг {i+1}", key=f"step_title_{i}")
                    step_desc = st.text_area(f"Описание {i+1}", f"Описание шага {i+1}", key=f"step_desc_{i}")
                    step_icon = st.text_input(f"Иконка (эмодзи) {i+1}", "➡️", key=f"step_icon_{i}")
                    if step_title:
                        steps.append({
                            'title': step_title,
                            'description': step_desc,
                            'icon': step_icon
                        })
            st.session_state['infographic_data'] = {
                'title': title,
                'warning': warning,
                'steps': steps
            }
        elif infographic_type == "📦 Упаковка и комплектация":
            size = st.text_input("Размер упаковки", "30x30x30 см")
            weight = st.text_input("Вес", "1.5 кг")
            quantity = st.text_input("Количество в упаковке", "1 шт")
            manufacturer = st.text_input("Производитель", "Россия")
            contents = st.text_area("Состав комплекта (каждый с новой строки)", 
                                   "Товар\nИнструкция\nГарантийный талон")
            st.session_state['infographic_data'] = {
                'package': {
                    'size': size,
                    'weight': weight,
                    'quantity': quantity,
                    'manufacturer': manufacturer
                },
                'contents': [c.strip() for c in contents.split('\n') if c.strip()]
            }
        elif infographic_type == "🏆 Сертификаты":
            title = st.text_input("Название", "Сертификаты и награды")
            certificates = []
            for i in range(4):
                with st.expander(f"Сертификат {i+1}"):
                    cert_name = st.text_input(f"Название {i+1}", f"Сертификат {i+1}", key=f"cert_name_{i}")
                    cert_issuer = st.text_input(f"Кем выдан {i+1}", f"Орган сертификации", key=f"cert_issuer_{i}")
                    cert_date = st.text_input(f"Дата {i+1}", "2024", key=f"cert_date_{i}")
                    if cert_name:
                        certificates.append({
                            'name': cert_name,
                            'issuer': cert_issuer,
                            'date': cert_date
                        })
            standards = st.text_area("Соответствие стандартам (каждый с новой строки)", "ISO 9001\nГОСТ Р\nCE")
            st.session_state['infographic_data'] = {
                'title': title,
                'certificates': certificates,
                'standards': [s.strip() for s in standards.split('\n') if s.strip()]
            }
        elif infographic_type == "💰 Цены и акции":
            discount = st.text_input("Скидка %", "20")
            old_price = st.text_input("Старая цена", "5000")
            new_price = st.text_input("Новая цена", "4000")
            currency = st.selectbox("Валюта", ["₽", "$", "€"])
            benefits = st.text_area("Преимущества покупки (каждое с новой строки)", "Бесплатная доставка\nГарантия 2 года\nПодарок")
            timer = st.text_input("Таймер акции", "24:00:00")
            st.session_state['infographic_data'] = {
                'discount': discount,
                'old_price': old_price,
                'new_price': new_price,
                'currency': currency,
                'benefits': [b.strip() for b in benefits.split('\n') if b.strip()],
                'timer': timer
            }
        elif infographic_type == "🔬 Состав и материалы":
            title = st.text_input("Название", "Состав и материалы")
            st.info("Введите состав в процентах")
            materials = {}
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                mat1 = st.text_input("Материал 1", "Металл")
                val1 = st.number_input("%", 0, 100, 70, key="mat1")
                if mat1:
                    materials[mat1] = val1
            with col_m2:
                mat2 = st.text_input("Материал 2", "Пластик")
                val2 = st.number_input("%", 0, 100, 20, key="mat2")
                if mat2:
                    materials[mat2] = val2
            col_m3, col_m4 = st.columns(2)
            with col_m3:
                mat3 = st.text_input("Материал 3", "Резина")
                val3 = st.number_input("%", 0, 100, 10, key="mat3")
                if mat3:
                    materials[mat3] = val3
            composition = st.text_area("Детальный состав", "Подробное описание состава материала...")
            st.session_state['infographic_data'] = {
                'title': title,
                'materials': materials,
                'composition': composition
            }
    
    with tab2:
        st.header("2. Предпросмотр")
        if st.button("🎨 Создать предпросмотр", use_container_width=True):
            data = st.session_state.get('infographic_data', {})
            # Добавляем изображение если есть
            if 'product_images' in st.session_state:
                if st.session_state['product_images']:
                    first_img = list(st.session_state['product_images'].values())[0]
                    data['product_image'] = first_img
            # Создаем инфографику в зависимости от типа
            if 'infographic_type' in st.session_state:
                infographic_type = st.session_state['infographic_type']
            else:
                infographic_type = "📏 Размерная сетка"
            if infographic_type == "📏 Размерная сетка":
                result = generator.create_size_chart_infographic(data, design_settings)
            elif infographic_type == "📊 Технические характеристики":
                result = generator.create_specs_infographic(data, design_settings)
            elif infographic_type == "⚖️ Сравнение с конкурентами":
                result = generator.create_comparison_infographic(data, design_settings)
            elif infographic_type == "💡 УТП и преимущества":
                result = generator.create_usp_infographic(data, design_settings)
            elif infographic_type == "📖 Инструкция":
                result = generator.create_instruction_infographic(data, design_settings)
            elif infographic_type == "📦 Упаковка и комплектация":
                result = generator.create_package_infographic(data, design_settings)
            elif infographic_type == "🏆 Сертификаты":
                result = generator.create_certificate_infographic(data, design_settings)
            elif infographic_type == "💰 Цены и акции":
                result = generator.create_price_infographic(data, design_settings)
            elif infographic_type == "🔬 Состав и материалы":
                result = generator.create_materials_infographic(data, design_settings)
            else:
                result = Image.new('RGB', (900, 1200), 'white')
            st.image(result, caption="Предпросмотр инфографики", use_container_width=True)
            st.session_state['preview'] = result
    
    with tab3:
        st.header("3. Готовые результаты")
        if 'df' in st.session_state and 'product_images' in st.session_state:
            if st.button("🚀 СОЗДАТЬ ДЛЯ ВСЕХ ТОВАРОВ", type="primary", use_container_width=True):
                progress_bar = st.progress(0)
                status_text = st.empty()
                processed_files = []
                df = st.session_state['df']
                total = len(df)
                for idx, row in df.iterrows():
                    try:
                        status_text.text(f"Обработка: строка {idx+1}/{total}")
                        # Берем данные из строки
                        data = st.session_state.get('infographic_data', {}).copy()
                        # Подставляем значения из DataFrame
                        for key in data:
                            if isinstance(data[key], str) and '{' in data[key]:
                                try:
                                    data[key] = data[key].format(**row.to_dict())
                                except:
                                    pass
                        # Ищем изображение
                        article = str(row.get(st.session_state.get('article_col', 'Артикул'), ''))
                        product_img = None
                        if 'product_images' in st.session_state:
                            for fname, img in st.session_state['product_images'].items():
                                if article in fname or fname.startswith(article):
                                    product_img = img.copy()
                                    break
                        if product_img:
                            data['product_image'] = product_img
                        # Создаем инфографику
                        if 'infographic_type' in st.session_state:
                            infographic_type = st.session_state['infographic_type']
                        else:
                            infographic_type = "📏 Размерная сетка"
                        if infographic_type == "📏 Размерная сетка":
                            result = generator.create_size_chart_infographic(data, design_settings)
                        elif infographic_type == "📊 Технические характеристики":
                            result = generator.create_specs_infographic(data, design_settings)
                        elif infographic_type == "⚖️ Сравнение с конкурентами":
                            result = generator.create_comparison_infographic(data, design_settings)
                        elif infographic_type == "💡 УТП и преимущества":
                            result = generator.create_usp_infographic(data, design_settings)
                        elif infographic_type == "📖 Инструкция":
                            result = generator.create_instruction_infographic(data, design_settings)
                        elif infographic_type == "📦 Упаковка и комплектация":
                            result = generator.create_package_infographic(data, design_settings)
                        elif infographic_type == "🏆 Сертификаты":
                            result = generator.create_certificate_infographic(data, design_settings)
                        elif infographic_type == "💰 Цены и акции":
                            result = generator.create_price_infographic(data, design_settings)
                        elif infographic_type == "🔬 Состав и материалы":
                            result = generator.create_materials_infographic(data, design_settings)
                        else:
                            continue
                        # Сохраняем
                        img_bytes = io.BytesIO()
                        result.save(img_bytes, format='PNG')
                        filename = f"{article}_{infographic_type[:10]}.png"
                        processed_files.append((filename, img_bytes.getvalue()))
                    except Exception as e:
                        st.error(f"Ошибка: {str(e)}")
                    progress_bar.progress((idx + 1) / total)
                status_text.text("✅ Готово!")
                if processed_files:
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        for filename, data in processed_files:
                            zip_file.writestr(filename, data)
                    zip_buffer.seek(0)
                    st.download_button(
                        "📥 Скачать ZIP архив",
                        data=zip_buffer,
                        file_name=f"infographics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
        else:
            st.info("Загрузите данные и изображения во вкладке 'Данные'")

# ================ ЗАПУСК ================

if __name__ == "__main__":
    main()
