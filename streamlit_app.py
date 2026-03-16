import platform
import sys

# Проверка архитектуры Python (требуется 64-bit)
if platform.architecture()[0] != '64bit':
    error_msg = """
    ❌ ОШИБКА: Обнаружена 32-bit версия Python!
    
    Это приложение требует 64-bit версию Python, так как библиотеки 
    pyarrow, polars и duckdb не поддерживают 32-bit архитектуру на Windows.
    
    Решение:
    1. Скачайте и установите 64-bit Python с https://www.python.org/downloads/
    2. Переустановите зависимости: pip install -r requirements.txt
    3. Запустите приложение снова
    
    Текущая архитектура: {}
    """.format(platform.architecture()[0])
    print(error_msg)
    sys.exit(1)

import polars as pl
import duckdb
import streamlit as st
import os
import time
import logging
import io
import zipfile
from pathlib import Path
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
EXCEL_ROW_LIMIT = 1_000_000

class HighVolumeAutoPartsCatalog:
    
    def __init__(self):
        self.data_dir = Path("./auto_parts_data")
        self.data_dir.mkdir(exist_ok=True)
        self.db_path = self.data_dir / "catalog.duckdb"
        self.conn = duckdb.connect(database=str(self.db_path))
        self.setup_database()
        
        st.set_page_config(
            page_title="AutoParts Catalog 10M+", 
            layout="wide",
            page_icon="🚗"
        )
    
    def setup_database(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS oe_data (
                oe_number_norm VARCHAR PRIMARY KEY,
                oe_number VARCHAR,
                name VARCHAR,
                applicability VARCHAR,
                category VARCHAR
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS parts_data (
                artikul_norm VARCHAR,
                brand_norm VARCHAR,
                artikul VARCHAR,
                brand VARCHAR,
                multiplicity INTEGER,
                barcode VARCHAR,
                length DOUBLE, 
                width DOUBLE,
                height DOUBLE, 
                weight DOUBLE,
                image_url VARCHAR,
                dimensions_str VARCHAR,
                description VARCHAR,
                PRIMARY KEY (artikul_norm, brand_norm)
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS cross_references (
                oe_number_norm VARCHAR,
                artikul_norm VARCHAR,
                brand_norm VARCHAR,
                PRIMARY KEY (oe_number_norm, artikul_norm, brand_norm)
            )
        """)
        
    def create_indexes(self):
        st.info("Создание индексов для ускорения поиска...")
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_oe_data_oe ON oe_data(oe_number_norm)",
            "CREATE INDEX IF NOT EXISTS idx_parts_data_keys ON parts_data(artikul_norm, brand_norm)",
            "CREATE INDEX IF NOT EXISTS idx_cross_oe ON cross_references(oe_number_norm)",
            "CREATE INDEX IF NOT EXISTS idx_cross_artikul ON cross_references(artikul_norm, brand_norm)",
        ]
        for index_sql in indexes:
            self.conn.execute(index_sql)
        st.success("Индексы созданы.")

    @staticmethod
    def normalize_key(key_series: pl.Series) -> pl.Series:
        return (
            key_series
            .fill_null("")
            .cast(pl.Utf8)
            # Сначала удаляем апостроф полностью (он не нужен вообще)
            .str.replace_all("'", "")
            # Затем удаляем другие мусорные символы, оставляя: буквы, цифры, `, -, пробел
            .str.replace_all(r"[^0-9A-Za-zA-za-яЁё`\-\s]", "")
            # Нормализуем пробелы (множественные пробелы -> один)
            .str.replace_all(r"\s+", " ")
            # Убираем пробелы в начале и конце
            .str.strip_chars()
            .str.to_lowercase()
        )

    @staticmethod
    def clean_values(value_series: pl.Series) -> pl.Series:
        """Очистить оригинальные значения от апострофов и мусора на входе"""
        return (
            value_series
            .fill_null("")
            .cast(pl.Utf8)
            # Удаляем апостроф полностью
            .str.replace_all("'", "")
            # Удаляем другие мусорные символы, оставляя: буквы, цифры, `, -, пробел
            .str.replace_all(r"[^0-9A-Za-zA-za-яЁё`\-\s]", "")
            # Нормализуем пробелы (множественные пробелы -> один)
            .str.replace_all(r"\s+", " ")
            # Убираем пробелы в начале и конце
            .str.strip_chars()
        )

    @staticmethod
    def determine_category_vectorized(name_series: pl.Series) -> pl.Series:
        categories_map = {
            'Фильтр': 'фильтр|filter', 'Тормоза': 'тормоз|brake|колодк|диск|суппорт',
            'Подвеска': 'амортизатор|стойк|spring|подвеск|рычаг', 'Двигатель': 'двигатель|engine|свеч|поршень|клапан',
            'Трансмиссия': 'трансмиссия|сцеплен|коробк|transmission', 'Электрика': 'аккумулятор|генератор|стартер|провод|ламп',
            'Рулевое': 'рулевой|тяга|наконечник|steering', 'Выпуск': 'глушитель|катализатор|выхлоп|exhaust',
            'Охлаждение': 'радиатор|вентилятор|термостат|cooling', 'Топливо': 'топливный|бензонасос|форсунк|fuel'
        }
        name_lower = name_series.str.to_lowercase()
        categorization_expr = pl.when(pl.lit(False)).then(pl.lit(None))
        for category, pattern in categories_map.items():
            categorization_expr = categorization_expr.when(name_lower.str.contains(pattern)).then(pl.lit(category))
        return categorization_expr.otherwise(pl.lit('Разное')).alias('category')

    def detect_columns(self, actual_columns: List[str], expected_columns: List[str]) -> Dict[str, str]:
        mapping = {}
        column_variants = {
            'oe_number': ['oe номер', 'oe', 'оe', 'номер', 'code', 'OE'], 'artikul': ['артикул', 'article', 'sku'],
            'brand': ['бренд', 'brand', 'производитель', 'manufacturer'], 'name': ['наименование', 'название', 'name', 'описание', 'description'],
            'applicability': ['применимость', 'автомобиль', 'vehicle', 'applicability'], 'barcode': ['штрих-код', 'barcode', 'штрихкод', 'ean', 'eac13'],
            'multiplicity': ['кратность шт', 'кратность', 'multiplicity'], 'length': ['длина (см)', 'длина', 'length', 'длинна'],
            'width': ['ширина (см)', 'ширина', 'width'], 'height': ['высота (см)', 'высота', 'height'],
            'weight': ['вес (кг)', 'вес, кг', 'вес', 'weight'], 'image_url': ['ссылка', 'url', 'изображение', 'image', 'картинка'],
            'dimensions_str': ['весогабариты', 'размеры', 'dimensions', 'size']
        }
        actual_lower = {col.lower(): col for col in actual_columns}
        for expected in expected_columns:
            variants = [v.lower() for v in column_variants.get(expected, [expected])]
            for variant in variants:
                for actual_l, actual_orig in actual_lower.items():
                    if variant in actual_l:
                        mapping[actual_orig] = expected
                        break
                if expected in mapping.values():
                    break
        return mapping

    def read_and_prepare_file(self, file_path: str, file_type: str) -> pl.DataFrame:
        logger.info(f"Начинаю обработку файла: {file_type} ({file_path})")
        try:
            # Проверяем существование файла
            if not os.path.exists(file_path):
                logger.error(f"Файл не найден: {file_path}")
                return pl.DataFrame()
            
            # Проверяем размер файла
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                logger.warning(f"Файл пуст: {file_path}")
                return pl.DataFrame()
            
            df = pl.read_excel(file_path, engine='calamine')
            
            # Проверяем, что DataFrame не пустой после чтения
            if df.is_empty():
                logger.warning(f"Файл прочитан, но не содержит данных: {file_path}")
                return pl.DataFrame()
                
        except Exception as e:
            logger.exception(f"Не удалось прочитать файл {file_path}: {e}")
            return pl.DataFrame()

        schemas = {
            'oe': ['oe_number', 'artikul', 'brand', 'name', 'applicability'],
            'barcode': ['brand', 'artikul', 'barcode', 'multiplicity'],
            'dimensions': ['artikul', 'brand', 'length', 'width', 'height', 'weight', 'dimensions_str'],
            'images': ['artikul', 'brand', 'image_url'],
            'cross': ['oe_number', 'artikul', 'brand']
        }
        expected_cols = schemas.get(file_type, [])
        column_mapping = self.detect_columns(df.columns, expected_cols)
        
        if not column_mapping:
            logger.warning(f"Не удалось определить колонки для файла {file_type}. Доступные колонки: {df.columns}")
            # Возвращаем пустой DataFrame, но логируем проблему
            return pl.DataFrame()
        
        df = df.rename(column_mapping)
        
        # Очистить оригинальные значения от апострофов и мусора на входе
        if 'artikul' in df.columns:
            df = df.with_columns(artikul=self.clean_values(pl.col('artikul')))
        if 'brand' in df.columns:
            df = df.with_columns(brand=self.clean_values(pl.col('brand')))
        if 'oe_number' in df.columns:
            df = df.with_columns(oe_number=self.clean_values(pl.col('oe_number')))
        
        key_cols = [col for col in ['oe_number', 'artikul', 'brand'] if col in df.columns]
        if key_cols:
            df = df.unique(subset=key_cols, keep='first')

        # Создать нормализованные версии для ключей (нижний регистр)
        if 'artikul' in df.columns:
            df = df.with_columns(artikul_norm=self.normalize_key(pl.col('artikul')))
        if 'brand' in df.columns:
            df = df.with_columns(brand_norm=self.normalize_key(pl.col('brand')))
        if 'oe_number' in df.columns:
            df = df.with_columns(oe_number_norm=self.normalize_key(pl.col('oe_number')))
            
        return df

    def upsert_data(self, table_name: str, df: pl.DataFrame, pk: List[str]):
        if df.is_empty():
            return
        
        df = df.unique(keep='first')
        
        cols = df.columns
        pk_str = ", ".join(f'"{c}"' for c in pk)
        
        temp_view_name = f"temp_{table_name}_{int(time.time())}"
        self.conn.register(temp_view_name, df.to_arrow())
        
        update_cols = [col for col in cols if col not in pk]
        
        if not update_cols:
            on_conflict_action = "DO NOTHING"
        else:
            update_clause = ", ".join([f'"{col}" = excluded."{col}"' for col in update_cols])
            on_conflict_action = f"DO UPDATE SET {update_clause}"

        sql = f"""
        INSERT INTO {table_name}
        SELECT * FROM {temp_view_name}
        ON CONFLICT ({pk_str}) {on_conflict_action};
        """
        
        try:
            self.conn.execute(sql)
            logger.info(f"Успешно обновлено/вставлено {len(df)} записей в таблицу {table_name}.")
        except Exception as e:
            logger.error(f"Ошибка при UPSERT в {table_name}: {e}")
            st.error(f"Ошибка при записи в таблицу {table_name}. Детали в логе.")
        finally:
            self.conn.unregister(temp_view_name)


    def process_and_load_data(self, dataframes: Dict[str, pl.DataFrame]):
        st.info("🔄 Начало загрузки и обновления данных в базе...")
        
        steps = [s for s in ['oe', 'cross', 'parts'] if s in dataframes or s == 'parts']
        num_steps = len(steps)
        progress_bar = st.progress(0, text="Подготовка к обновлению базы данных...")
        step_counter = 0

        if 'oe' in dataframes:
            step_counter += 1
            progress_bar.progress(step_counter / (num_steps + 1), text=f"({step_counter}/{num_steps}) Обработка OE данных...")
            df = dataframes['oe'].filter(pl.col('oe_number_norm') != "")
            
            oe_df = df.select(['oe_number_norm', 'oe_number', 'name', 'applicability']).unique(subset=['oe_number_norm'], keep='first')
            if 'name' in oe_df.columns:
                oe_df = oe_df.with_columns(self.determine_category_vectorized(pl.col('name')))
            else:
                oe_df = oe_df.with_columns(category=pl.lit('Разное'))
            self.upsert_data('oe_data', oe_df, ['oe_number_norm'])
            
            cross_df_from_oe = df.filter(pl.col('artikul_norm') != "").select(['oe_number_norm', 'artikul_norm', 'brand_norm']).unique()
            self.upsert_data('cross_references', cross_df_from_oe, ['oe_number_norm', 'artikul_norm', 'brand_norm'])

        if 'cross' in dataframes:
            step_counter += 1
            progress_bar.progress(step_counter / (num_steps + 1), text=f"({step_counter}/{num_steps}) Обработка кроссов...")
            df = dataframes['cross'].filter((pl.col('oe_number_norm') != "") & (pl.col('artikul_norm') != ""))
            cross_df_from_cross = df.select(['oe_number_norm', 'artikul_norm', 'brand_norm']).unique()
            self.upsert_data('cross_references', cross_df_from_cross, ['oe_number_norm', 'artikul_norm', 'brand_norm'])

        step_counter += 1
        progress_bar.progress(step_counter / (num_steps + 1), text=f"({step_counter}/{num_steps}) Сборка и обновление данных по артикулам...")
        parts_df = None
        # Определяем порядок обработки файлов для правильного приоритета данных
        # Порядок важен: сначала базовые данные, потом специфичные (dimensions имеет приоритет)
        file_priority = ['oe', 'barcode', 'images', 'dimensions']
        key_files = {ftype: df for ftype, df in dataframes.items() if ftype in file_priority}
        
        if key_files:
            # Собираем все уникальные артикулы из всех файлов
            all_parts = pl.concat([
                df.select(['artikul', 'artikul_norm', 'brand', 'brand_norm']) 
                for df in key_files.values() if 'artikul_norm' in df.columns and 'brand_norm' in df.columns
            ]).filter(pl.col('artikul_norm') != "").unique(subset=['artikul_norm', 'brand_norm'], keep='first')

            parts_df = all_parts

            # Обрабатываем файлы в определенном порядке для правильного приоритета данных
            for ftype in file_priority:
                if ftype not in key_files: continue
                df = key_files[ftype]
                if df.is_empty() or 'artikul_norm' not in df.columns: continue
                
                join_cols = [col for col in df.columns if col not in ['artikul', 'artikul_norm', 'brand', 'brand_norm']]
                if not join_cols: continue
                
                # Фильтруем колонки, которые уже есть в parts_df, чтобы избежать дублирования
                existing_cols = set(parts_df.columns)
                join_cols = [col for col in join_cols if col not in existing_cols]
                if not join_cols: continue
                
                df_subset = df.select(['artikul_norm', 'brand_norm'] + join_cols).unique(subset=['artikul_norm', 'brand_norm'], keep='first')
                # coalesce=True перезаписывает пустые значения существующих колонок
                # Суффиксы не создаются, так как мы уже отфильтровали существующие колонки
                parts_df = parts_df.join(df_subset, on=['artikul_norm', 'brand_norm'], how='left', coalesce=True)

        if parts_df is not None and not parts_df.is_empty():
            # Безопасная обработка multiplicity
            if 'multiplicity' not in parts_df.columns:
                parts_df = parts_df.with_columns(multiplicity=pl.lit(1).cast(pl.Int32))
            else:
                parts_df = parts_df.with_columns(
                    pl.col('multiplicity').fill_null(1).cast(pl.Int32)
                )
            
            # Безопасная обработка dimensions_str - используем более простой подход
            # Сначала убеждаемся, что все числовые колонки есть
            for col in ['length', 'width', 'height']:
                if col not in parts_df.columns:
                    parts_df = parts_df.with_columns(pl.lit(None).cast(pl.Float64).alias(col))
            
            # Формируем dimensions_str безопасно
            if 'dimensions_str' not in parts_df.columns:
                parts_df = parts_df.with_columns(dimensions_str=pl.lit(None).cast(pl.Utf8))
            
            # Теперь безопасно формируем dimensions_str
            # Сначала создаем временные колонки для безопасной конкатенации
            parts_df = parts_df.with_columns([
                pl.col('length').cast(pl.Utf8).fill_null('').alias('_length_str'),
                pl.col('width').cast(pl.Utf8).fill_null('').alias('_width_str'),
                pl.col('height').cast(pl.Utf8).fill_null('').alias('_height_str'),
            ])
            
            # Формируем dimensions_str из временных колонок
            parts_df = parts_df.with_columns(
                dimensions_str=pl.when(
                    (pl.col('dimensions_str').is_not_null()) & 
                    (pl.col('dimensions_str').cast(pl.Utf8) != '')
                ).then(
                    pl.col('dimensions_str').cast(pl.Utf8)
                ).otherwise(
                    pl.concat_str([
                        pl.col('_length_str'), pl.lit('x'), 
                        pl.col('_width_str'), pl.lit('x'), 
                        pl.col('_height_str')
                    ], separator='')
                )
            )
            
            # Удаляем временные колонки
            parts_df = parts_df.drop(['_length_str', '_width_str', '_height_str'])
            
            # Безопасная обработка description
            if 'artikul' not in parts_df.columns:
                parts_df = parts_df.with_columns(artikul=pl.lit(''))
            if 'brand' not in parts_df.columns:
                parts_df = parts_df.with_columns(brand=pl.lit(''))
            
            # Создаем временные колонки для безопасной конкатенации
            parts_df = parts_df.with_columns([
                pl.col('artikul').cast(pl.Utf8).fill_null('').alias('_artikul_str'),
                pl.col('brand').cast(pl.Utf8).fill_null('').alias('_brand_str'),
                pl.col('multiplicity').cast(pl.Utf8).alias('_multiplicity_str'),
            ])
            
            # Формируем description из временных колонок
            parts_df = parts_df.with_columns(
                description=pl.concat_str([
                    pl.lit('Артикул: '), pl.col('_artikul_str'),
                    pl.lit(', Бренд: '), pl.col('_brand_str'),
                    pl.lit(', Кратность: '), pl.col('_multiplicity_str'), pl.lit(' шт.')
                ], separator='')
            )
            
            # Удаляем временные колонки
            parts_df = parts_df.drop(['_artikul_str', '_brand_str', '_multiplicity_str'])
            final_columns = [
                'artikul_norm', 'brand_norm', 'artikul', 'brand', 'multiplicity', 'barcode', 
                'length', 'width', 'height', 'weight', 'image_url', 'dimensions_str', 'description'
            ]
            select_exprs = [pl.col(c) if c in parts_df.columns else pl.lit(None).alias(c) for c in final_columns]
            parts_df = parts_df.select(select_exprs)
            
            self.upsert_data('parts_data', parts_df, ['artikul_norm', 'brand_norm'])
        
        progress_bar.progress(1.0, text="Обновление базы данных завершено!")
        time.sleep(1)
        progress_bar.empty()
        st.success("💾 Загрузка данных в базу завершена.")

    def merge_all_data_parallel(self, file_paths: Dict[str, str]) -> Dict[str, any]:
        start_time = time.time()
        stats = {}
        
        st.info("🚀 Начало параллельного чтения и подготовки файлов...")
        n_files = len(file_paths)
        file_progress_bar = st.progress(0, text="Ожидание...")
        
        dataframes = {}
        processed_files = 0
        with ThreadPoolExecutor() as executor:
            future_to_file = {executor.submit(self.read_and_prepare_file, path, ftype): ftype for ftype, path in file_paths.items()}
            for future in as_completed(future_to_file):
                ftype = future_to_file[future]
                try:
                    df = future.result()
                    if not df.is_empty():
                        dataframes[ftype] = df
                        st.success(f"✅ Файл '{ftype}' прочитан: {len(df):,} строк.")
                        logger.info(f"Файл '{ftype}' успешно обработан: {len(df):,} строк, колонки: {df.columns}")
                    else:
                        logger.warning(f"Файл '{ftype}' вернул пустой DataFrame после обработки")
                        st.warning(f"⚠️ Файл '{ftype}' пуст или не удалось обработать.")
                except Exception as e:
                    logger.exception(f"Ошибка обработки файла {ftype}")
                    st.error(f"❌ Ошибка в {ftype}: {e}")
                finally:
                    processed_files += 1
                    file_progress_bar.progress(processed_files / n_files, text=f"Обработка файла: {ftype} ({processed_files}/{n_files})")
        
        file_progress_bar.empty()

        if not dataframes:
            st.error("❌ Ни один файл не был загружен. Обработка остановлена.")
            return {}

        self.process_and_load_data(dataframes)
        
        processing_time = time.time() - start_time
        total_records = self.get_total_records()
        
        stats['processing_time'] = processing_time
        stats['total_records'] = total_records
        
        st.success(f"🎉 Обработка завершена за {processing_time:.2f} секунд")
        st.success(f"📊 Всего уникальных артикулов в базе: {total_records:,}")
        
        self.create_indexes()
        return stats
    
    def get_total_records(self) -> int:
        try:
            result = self.conn.execute("SELECT COUNT(*) FROM parts_data").fetchone()
            return result[0] if result else 0
        except (duckdb.Error, TypeError):
            return 0

    def get_export_query(self) -> str:
        return r"""
        WITH PartDetails AS (
            SELECT
                cr.artikul_norm,
                cr.brand_norm,
                STRING_AGG(DISTINCT regexp_replace(regexp_replace(o.oe_number, '''', ''), '[^0-9A-Za-zА-Яа-яЁё`\-\s]', '', 'g'), ', ') AS oe_list,
                ANY_VALUE(o.name) AS representative_name,
                ANY_VALUE(o.applicability) AS representative_applicability,
                ANY_VALUE(o.category) AS representative_category
            FROM cross_references cr
            JOIN oe_data o ON cr.oe_number_norm = o.oe_number_norm
            GROUP BY cr.artikul_norm, cr.brand_norm
        ),
        AllAnalogs AS (
            SELECT
                cr1.artikul_norm,
                cr1.brand_norm,
                STRING_AGG(DISTINCT regexp_replace(regexp_replace(p2.artikul, '''', ''), '[^0-9A-Za-zА-Яа-яЁё`\-\s]', '', 'g'), ', ') as analog_list
            FROM cross_references cr1
            JOIN cross_references cr2 ON cr1.oe_number_norm = cr2.oe_number_norm
            JOIN parts_data p2 ON cr2.artikul_norm = p2.artikul_norm AND cr2.brand_norm = p2.brand_norm
            WHERE cr1.artikul_norm != p2.artikul_norm OR cr1.brand_norm != p2.brand_norm
            GROUP BY cr1.artikul_norm, cr1.brand_norm
        )
        SELECT
            p.artikul AS "Артикул бренда",
            p.brand AS "Бренд",
            pd.representative_name AS "Наименование",
            pd.representative_applicability AS "Применимость",
            p.description AS "Описание",
            pd.representative_category AS "Категория товара",
            p.multiplicity AS "Кратность",
            p.length AS "Длинна",
            p.width AS "Ширина",
            p.height AS "Высота",
            p.weight AS "Вес",
            p.dimensions_str AS "Длинна/Ширина/Высота",
            pd.oe_list AS "OE номер",
            aa.analog_list AS "аналоги",
            p.image_url AS "Ссылка на изображение"
        FROM parts_data p
        LEFT JOIN PartDetails pd ON p.artikul_norm = pd.artikul_norm AND p.brand_norm = pd.brand_norm
        LEFT JOIN AllAnalogs aa ON p.artikul_norm = aa.artikul_norm AND p.brand_norm = aa.brand_norm
        WHERE pd.oe_list IS NOT NULL
        ORDER BY p.brand, p.artikul
        """

    from typing import List

    def build_export_query(self, selected_columns: List[str] | None) -> str:
        # Стандартный текст описания. Оставляем его как есть, с переносами строк.
        standard_description = """Состояние товара: новый (в упаковке).
    Высококачественные автозапчасти и автотовары — надежное решение для вашего автомобиля. 
    Обеспечьте безопасность, долговечность и высокую производительность вашего авто с помощью нашего широкого ассортимента оригинальных и совместимых автозапчастей.

    В нашем каталоге вы найдете тормозные системы, фильтры (масляные, воздушные, салонные), свечи зажигания, расходные материалы, автохимию, электрику, автомасла, инструмент, а также другие комплектующие, полностью соответствующие стандартам качества и безопасности. 

    Мы гарантируем быструю доставку, выгодные цены и профессиональную консультацию для любого клиента — автолюбителя, специалиста или автосервиса. 

    Выбирайте только лучшее — надежность и качество от ведущих производителей."""
        
        # Сопоставление отображаемого имени с выражением SQL
        columns_map = [
            ("Артикул бренда", 'r.artikul AS "Артикул бренда"'),
            ("Бренд", 'r.brand AS "Бренд"'),
            ("Наименование", 'COALESCE(r.representative_name, r.analog_representative_name) AS "Наименование"'),
            ("Применимость", 'COALESCE(r.representative_applicability, r.analog_representative_applicability) AS "Применимость"'),
            # ИЗМЕНЕНИЕ: Теперь мы просто конкатенируем с полем из нашего нового CTE
            ("Описание", "CONCAT(COALESCE(r.description, ''), dt.text) AS \"Описание\""),
            ("Категория товара", 'COALESCE(r.representative_category, r.analog_representative_category) AS "Категория товара"'),
            ("Кратность", 'r.multiplicity AS "Кратность"'),
            ("Длинна", 'COALESCE(r.length, r.analog_length) AS "Длинна"'),
            ("Ширина", 'COALESCE(r.width, r.analog_width) AS "Ширина"'),
            ("Высота", 'COALESCE(r.height, r.analog_height) AS "Высота"'),
            ("Вес", 'COALESCE(r.weight, r.analog_weight) AS "Вес"'),
            ("Длинна/Ширина/Высота", "COALESCE(CASE WHEN r.dimensions_str IS NULL OR r.dimensions_str = '' OR UPPER(TRIM(r.dimensions_str)) = 'XX' THEN NULL ELSE r.dimensions_str END, r.analog_dimensions_str) AS \"Длинна/Ширина/Высота\""),
            ("OE номер", 'r.oe_list AS "OE номер"'),
            ("аналоги", 'r.analog_list AS "аналоги"'),
            ("Ссылка на изображение", 'r.image_url AS "Ссылка на изображение"')
        ]

        if not selected_columns:
            selected_exprs = [expr for _, expr in columns_map]
        else:
            selected_exprs = [expr for name, expr in columns_map if name in selected_columns]
            if not selected_exprs:
                selected_exprs = [expr for _, expr in columns_map]

        # ГЛАВНОЕ ИЗМЕНЕНИЕ: Мы создаем CTE с нашим текстом, используя $$ для безопасности.
        # Это полностью изолирует сложный текст от остальной логики запроса.
        ctes = f"""
        WITH DescriptionTemplate AS (
            SELECT CHR(10) || CHR(10) || $${standard_description}$$ AS text
        ),
        PartDetails AS (
            SELECT
                cr.artikul_norm,
                cr.brand_norm,
                STRING_AGG(DISTINCT regexp_replace(regexp_replace(o.oe_number, '''', ''), '[^0-9A-Za-zА-Яа-яЁё`\\-\\s]', '', 'g'), ', ') AS oe_list,
                ANY_VALUE(o.name) AS representative_name,
                ANY_VALUE(o.applicability) AS representative_applicability,
                ANY_VALUE(o.category) AS representative_category
            FROM cross_references cr
            JOIN oe_data o ON cr.oe_number_norm = o.oe_number_norm
            GROUP BY cr.artikul_norm, cr.brand_norm
        ),
        AllAnalogs AS (
            SELECT
                cr1.artikul_norm,
                cr1.brand_norm,
                STRING_AGG(DISTINCT regexp_replace(regexp_replace(p2.artikul, '''', ''), '[^0-9A-Za-zА-Яа-яЁё`\\-\\s]', '', 'g'), ', ') as analog_list
            FROM cross_references cr1
            JOIN cross_references cr2 ON cr1.oe_number_norm = cr2.oe_number_norm
            JOIN parts_data p2 ON cr2.artikul_norm = p2.artikul_norm AND cr2.brand_norm = p2.brand_norm
            WHERE (cr1.artikul_norm != p2.artikul_norm OR cr1.brand_norm != p2.brand_norm)
            GROUP BY cr1.artikul_norm, cr1.brand_norm
        ),
        InitialOENumbers AS (
            SELECT DISTINCT
                p.artikul_norm,
                p.brand_norm,
                cr.oe_number_norm
            FROM parts_data p
            LEFT JOIN cross_references cr ON p.artikul_norm = cr.artikul_norm AND p.brand_norm = cr.brand_norm
            WHERE cr.oe_number_norm IS NOT NULL
        ),
        Level1Analogs AS (
            SELECT DISTINCT
                i.artikul_norm AS source_artikul_norm,
                i.brand_norm AS source_brand_norm,
                cr2.artikul_norm AS related_artikul_norm,
                cr2.brand_norm AS related_brand_norm
            FROM InitialOENumbers i
            JOIN cross_references cr2 ON i.oe_number_norm = cr2.oe_number_norm
            WHERE NOT (i.artikul_norm = cr2.artikul_norm AND i.brand_norm = cr2.brand_norm)
        ),
        Level1OENumbers AS (
            SELECT DISTINCT
                l1.source_artikul_norm,
                l1.source_brand_norm,
                cr3.oe_number_norm
            FROM Level1Analogs l1
            JOIN cross_references cr3 ON l1.related_artikul_norm = cr3.artikul_norm 
                                        AND l1.related_brand_norm = cr3.brand_norm
            WHERE NOT EXISTS (
                SELECT 1 FROM InitialOENumbers i 
                WHERE i.artikul_norm = l1.source_artikul_norm 
                AND i.brand_norm = l1.source_brand_norm 
                AND i.oe_number_norm = cr3.oe_number_norm
            )
        ),
        Level2Analogs AS (
            SELECT DISTINCT
                loe.source_artikul_norm,
                loe.source_brand_norm,
                cr4.artikul_norm AS related_artikul_norm,
                cr4.brand_norm AS related_brand_norm
            FROM Level1OENumbers loe
            JOIN cross_references cr4 ON loe.oe_number_norm = cr4.oe_number_norm
            WHERE NOT (loe.source_artikul_norm = cr4.artikul_norm AND loe.source_brand_norm = cr4.brand_norm)
        ),
        AllRelatedParts AS (
            SELECT DISTINCT source_artikul_norm, source_brand_norm, related_artikul_norm, related_brand_norm
            FROM Level1Analogs
            UNION
            SELECT DISTINCT source_artikul_norm, source_brand_norm, related_artikul_norm, related_brand_norm
            FROM Level2Analogs
        ),
        AggregatedAnalogData AS (
            SELECT
                arp.source_artikul_norm AS artikul_norm,
                arp.source_brand_norm AS brand_norm,
                MAX(CASE WHEN p2.length IS NOT NULL THEN p2.length ELSE NULL END) AS length,
                MAX(CASE WHEN p2.width IS NOT NULL THEN p2.width ELSE NULL END) AS width,
                MAX(CASE WHEN p2.height IS NOT NULL THEN p2.height ELSE NULL END) AS height,
                MAX(CASE WHEN p2.weight IS NOT NULL THEN p2.weight ELSE NULL END) AS weight,
                ANY_VALUE(CASE WHEN p2.dimensions_str IS NOT NULL 
                               AND p2.dimensions_str != '' 
                               AND UPPER(TRIM(p2.dimensions_str)) != 'XX' 
                          THEN p2.dimensions_str ELSE NULL END) AS dimensions_str,
                ANY_VALUE(CASE WHEN pd2.representative_name IS NOT NULL AND pd2.representative_name != '' THEN pd2.representative_name ELSE NULL END) AS representative_name,
                ANY_VALUE(CASE WHEN pd2.representative_applicability IS NOT NULL AND pd2.representative_applicability != '' THEN pd2.representative_applicability ELSE NULL END) AS representative_applicability,
                ANY_VALUE(CASE WHEN pd2.representative_category IS NOT NULL AND pd2.representative_category != '' THEN pd2.representative_category ELSE NULL END) AS representative_category
            FROM AllRelatedParts arp
            JOIN parts_data p2 ON arp.related_artikul_norm = p2.artikul_norm AND arp.related_brand_norm = p2.brand_norm
            LEFT JOIN PartDetails pd2 ON p2.artikul_norm = pd2.artikul_norm AND p2.brand_norm = pd2.brand_norm
            GROUP BY arp.source_artikul_norm, arp.source_brand_norm
        ),
        RankedData AS (
            SELECT
                p.artikul,
                p.brand,
                p.description,
                p.multiplicity,
                p.length,
                p.width,
                p.height,
                p.weight,
                p.dimensions_str,
                p.image_url,
                pd.representative_name,
                pd.representative_applicability,
                pd.representative_category,
                pd.oe_list,
                aa.analog_list,
                p_analog.length AS analog_length,
                p_analog.width AS analog_width,
                p_analog.height AS analog_height,
                p_analog.weight AS analog_weight,
                p_analog.dimensions_str AS analog_dimensions_str,
                p_analog.representative_name AS analog_representative_name,
                p_analog.representative_applicability AS analog_representative_applicability,
                p_analog.representative_category AS analog_representative_category,
                ROW_NUMBER() OVER(PARTITION BY p.artikul_norm, p.brand_norm ORDER BY pd.representative_name DESC NULLS LAST, pd.oe_list DESC NULLS LAST) as rn
            FROM parts_data p
            LEFT JOIN PartDetails pd ON p.artikul_norm = pd.artikul_norm AND p.brand_norm = pd.brand_norm
            LEFT JOIN AllAnalogs aa ON p.artikul_norm = aa.artikul_norm AND p.brand_norm = aa.brand_norm
            LEFT JOIN AggregatedAnalogData p_analog ON p.artikul_norm = p_analog.artikul_norm AND p.brand_norm = p_analog.brand_norm
        )
        """

        select_clause = ",\n            ".join(selected_exprs)

        # ИЗМЕНЕНИЕ: Добавляем CROSS JOIN к нашему CTE с текстом
        query = ctes + r"""
        SELECT
            """ + select_clause + r"""
        FROM RankedData r
        CROSS JOIN DescriptionTemplate dt
        WHERE r.rn = 1
        ORDER BY r.brand, r.artikul
        """

        return query

    def export_to_csv_optimized(self, output_path: str, selected_columns: List[str] | None = None) -> bool:
        total_records = self.conn.execute("SELECT count(*) FROM (SELECT DISTINCT artikul_norm, brand_norm FROM parts_data) AS t").fetchone()[0]
        if total_records == 0:
            st.warning("Нет данных для экспорта")
            return False
        
        st.info(f"📤 Экспорт {total_records:,} записей в CSV...")
        try:
            query = self.build_export_query(selected_columns)
            df = self.conn.execute(query).pl()

            # Преобразуем числовые столбцы в строки для консистентности
            dimension_cols = ["Длинна", "Ширина", "Высота", "Вес", "Длинна/Ширина/Высота", "Кратность"]
            for col_name in dimension_cols:
                if col_name in df.columns:
                    # Преобразуем в строку, заменяя null на пустую строку
                    df = df.with_columns(
                        pl.when(pl.col(col_name).is_not_null())
                        .then(pl.col(col_name).cast(pl.Utf8))
                        .otherwise(pl.lit(""))
                        .alias(col_name)
                    )

            buf = io.StringIO()
            df.write_csv(buf, separator=';')
            csv_text = buf.getvalue()
            
            with open(output_path, 'wb') as f:
                f.write(b'\xef\xbb\xbf')
                f.write(csv_text.encode('utf-8'))

            file_size = os.path.getsize(output_path) / (1024 * 1024)
            st.success(f"✅ Данные экспортированы в CSV: {output_path} ({file_size:.1f} МБ)")
            return True
        except Exception as e:
            logger.exception("Ошибка экспорта в CSV")
            st.error(f"❌ Ошибка экспорта в CSV: {e}")
            return False
    
    def export_to_excel(self, output_path: Path, selected_columns: List[str] | None = None) -> tuple[bool, Path | None]:
        total_records = self.conn.execute("SELECT count(*) FROM (SELECT DISTINCT artikul_norm, brand_norm FROM parts_data) AS t").fetchone()[0]
        if total_records == 0:
            st.warning("Нет данных для экспорта")
            return False, None

        st.info(f"📤 Экспорт {total_records:,} записей в Excel...")
        try:
            num_files = (total_records + EXCEL_ROW_LIMIT - 1) // EXCEL_ROW_LIMIT
            base_query = self.build_export_query(selected_columns)
            exported_files = []
            
            progress_bar = st.progress(0, text=f"Подготовка к экспорту {num_files} файла(ов)...")

            for i in range(num_files):
                progress_bar.progress((i + 1) / num_files, text=f"Экспорт части {i+1} из {num_files}...")
                offset = i * EXCEL_ROW_LIMIT
                query = f"{base_query} LIMIT {EXCEL_ROW_LIMIT} OFFSET {offset}"
                df = self.conn.execute(query).pl()
                
                # Преобразуем числовые столбцы в строки, чтобы Excel не интерпретировал их как даты
                dimension_cols = ["Длинна", "Ширина", "Высота", "Вес", "Длинна/Ширина/Высота", "Кратность"]
                for col_name in dimension_cols:
                    if col_name in df.columns:
                        # Преобразуем в строку, заменяя null на пустую строку
                        df = df.with_columns(
                            pl.when(pl.col(col_name).is_not_null())
                            .then(pl.col(col_name).cast(pl.Utf8))
                            .otherwise(pl.lit(""))
                            .alias(col_name)
                        )

                file_part_path = output_path.with_name(f"{output_path.stem}_part_{i+1}.xlsx")
                df.write_excel(str(file_part_path))
                exported_files.append(file_part_path)
            
            progress_bar.empty()

            if num_files > 1:
                st.info("Архивация файлов в ZIP...")
                zip_path = output_path.with_suffix('.zip')
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file in exported_files:
                        zipf.write(file, file.name)
                        os.remove(file)
                final_path = zip_path
            else:
                final_path = exported_files[0]
                if final_path.name != output_path.name:
                    os.rename(final_path, output_path)
                    final_path = output_path

            file_size = os.path.getsize(final_path) / (1024 * 1024)
            st.success(f"✅ Данные экспортированы: {final_path.name} ({file_size:.1f} МБ)")
            return True, final_path

        except Exception as e:
            logger.exception("Ошибка экспорта в Excel")
            st.error(f"❌ Ошибка экспорта в Excel: {e}")
            return False, None
            
    def export_to_parquet(self, output_path: str, selected_columns: List[str] | None = None) -> bool:
        total_records = self.conn.execute("SELECT count(*) FROM (SELECT DISTINCT artikul_norm, brand_norm FROM parts_data) AS t").fetchone()[0]
        if total_records == 0:
            st.warning("Нет данных для экспорта")
            return False
        
        st.info(f"📤 Экспорт {total_records:,} записей в Parquet...")
        try:
            query = self.build_export_query(selected_columns)
            df = self.conn.execute(query).pl()
            
            df.write_parquet(output_path)

            file_size = os.path.getsize(output_path) / (1024 * 1024)
            st.success(f"✅ Данные экспортированы в Parquet: {output_path} ({file_size:.1f} МБ)")
            return True
        except Exception as e:
            logger.exception("Ошибка экспорта в Parquet")
            st.error(f"❌ Ошибка экспорта в Parquet: {e}")
            return False

    def show_export_interface(self):
        st.header("📤 Умный экспорт данных")
        total_records = self.conn.execute("SELECT count(DISTINCT (artikul_norm, brand_norm)) FROM parts_data").fetchone()[0]
        st.info(f"Всего записей для экспорта (строк): {total_records:,}")
        
        if total_records == 0:
            st.warning("База данных пуста или нет связей для экспорта. Сначала загрузите данные.")
            return
        # Allow user to choose which columns to include in the export
        available_columns = [
            "Артикул бренда", "Бренд", "Наименование", "Применимость", "Описание",
            "Категория товара", "Кратность", "Длинна", "Ширина", "Высота",
            "Вес", "Длинна/Ширина/Высота", "OE номер", "аналоги", "Ссылка на изображение"
        ]
        selected_columns = st.multiselect("Выберите столбцы для экспорта (пусто = все)", options=available_columns, default=available_columns)

        export_format = st.radio("Выберите формат экспорта:", ["CSV", "Excel (.xlsx)", "Parquet (для разработчиков)"], index=0)

        if export_format == "CSV":
            if st.button("🚀 Экспорт в CSV", type="primary"):
                output_path = self.data_dir / "auto_parts_report.csv"
                with st.spinner("Идет экспорт в CSV..."):
                    success = self.export_to_csv_optimized(str(output_path), selected_columns if selected_columns else None)
                if success:
                    with open(output_path, "rb") as f:
                        st.download_button("📥 Скачать CSV файл", f, "auto_parts_report.csv", "text/csv")

        elif export_format == "Excel (.xlsx)":
            st.info("ℹ️ Если записей больше 1 млн, результат будет разделен на несколько файлов и упакован в ZIP-архив.")
            if st.button("📊 Экспорт в Excel", type="primary"):
                output_path = self.data_dir / "auto_parts_report.xlsx"
                with st.spinner("Идет экспорт в Excel..."):
                    success, final_path = self.export_to_excel(output_path, selected_columns if selected_columns else None)
                if success and final_path and final_path.exists():
                    with open(final_path, "rb") as f:
                        mime = "application/zip" if final_path.suffix == ".zip" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        st.download_button(f"📥 Скачать {final_path.name}", f, final_path.name, mime)
        
        elif export_format == "Parquet (для разработчиков)":
            if st.button("⚡️ Экспорт в Parquet", type="primary"):
                output_path = self.data_dir / "auto_parts_report.parquet"
                with st.spinner("Идет экспорт в Parquet..."):
                    success = self.export_to_parquet(str(output_path), selected_columns if selected_columns else None)
                if success:
                    with open(output_path, "rb") as f:
                        st.download_button("📥 Скачать Parquet файл", f, "auto_parts_report.parquet", "application/octet-stream")
    
    def delete_by_brand(self, brand_norm: str) -> int:
        """Delete all records for a given normalized brand. Returns count of deleted records."""
        try:
            # Get count before deletion using parameterized query
            count_result = self.conn.execute("SELECT COUNT(*) FROM parts_data WHERE brand_norm = ?", [brand_norm]).fetchone()
            deleted_count = count_result[0] if count_result else 0
            
            if deleted_count == 0:
                logger.info(f"No records found for brand: {brand_norm}")
                return 0
            
            # Delete from parts_data using parameterized query
            self.conn.execute("DELETE FROM parts_data WHERE brand_norm = ?", [brand_norm])
            
            # Delete associated cross_references that no longer have matching parts_data
            self.conn.execute("DELETE FROM cross_references WHERE (artikul_norm, brand_norm) NOT IN (SELECT DISTINCT artikul_norm, brand_norm FROM parts_data)")
            
            logger.info(f"Deleted {deleted_count} records for brand: {brand_norm}")
            return deleted_count
        except Exception as e:
            logger.error(f"Error deleting by brand {brand_norm}: {e}")
            raise
    
    def delete_by_artikul(self, artikul_norm: str) -> int:
        """Delete all records for a given normalized artikul. Returns count of deleted records."""
        try:
            # Get count before deletion using parameterized query
            count_result = self.conn.execute("SELECT COUNT(*) FROM parts_data WHERE artikul_norm = ?", [artikul_norm]).fetchone()
            deleted_count = count_result[0] if count_result else 0
            
            if deleted_count == 0:
                logger.info(f"No records found for artikul: {artikul_norm}")
                return 0
            
            # Delete from parts_data using parameterized query
            self.conn.execute("DELETE FROM parts_data WHERE artikul_norm = ?", [artikul_norm])
            
            # Delete associated cross_references that no longer have matching parts_data
            self.conn.execute("DELETE FROM cross_references WHERE (artikul_norm, brand_norm) NOT IN (SELECT DISTINCT artikul_norm, brand_norm FROM parts_data)")
            
            logger.info(f"Deleted {deleted_count} records for artikul: {artikul_norm}")
            return deleted_count
        except Exception as e:
            logger.error(f"Error deleting by artikul {artikul_norm}: {e}")
            raise
    
    def get_statistics(self) -> Dict:
        stats = {}
        try:
            stats['total_parts'] = self.get_total_records()
            if stats['total_parts'] == 0:
                return {
                    'total_parts': 0, 'total_oe': 0, 'total_brands': 0,
                    'top_brands': pl.DataFrame(), 'categories': pl.DataFrame()
                }

            total_oe_res = self.conn.execute("SELECT COUNT(*) FROM oe_data").fetchone()
            stats['total_oe'] = total_oe_res[0] if total_oe_res else 0

            total_brands_res = self.conn.execute("SELECT COUNT(DISTINCT brand) FROM parts_data WHERE brand IS NOT NULL").fetchone()
            stats['total_brands'] = total_brands_res[0] if total_brands_res else 0
            
            # Используем fetchall() вместо .pl() для избежания проблем с pyarrow
            try:
                result = self.conn.execute("SELECT brand, COUNT(*) as count FROM parts_data WHERE brand IS NOT NULL GROUP BY brand ORDER BY count DESC LIMIT 10")
                rows = result.fetchall()
                if rows:
                    stats['top_brands'] = pl.DataFrame(rows, schema=["brand", "count"])
                else:
                    stats['top_brands'] = pl.DataFrame(schema={"brand": pl.Utf8, "count": pl.Int64})
            except Exception as e:
                logger.error(f"Ошибка при получении статистики брендов: {e}")
                stats['top_brands'] = pl.DataFrame(schema={"brand": pl.Utf8, "count": pl.Int64})
            
            try:
                result = self.conn.execute("SELECT category, COUNT(*) as count FROM oe_data WHERE category IS NOT NULL GROUP BY category ORDER BY count DESC")
                rows = result.fetchall()
                if rows:
                    stats['categories'] = pl.DataFrame(rows, schema=["category", "count"])
                else:
                    stats['categories'] = pl.DataFrame(schema={"category": pl.Utf8, "count": pl.Int64})
            except Exception as e:
                logger.error(f"Ошибка при получении статистики категорий: {e}")
                stats['categories'] = pl.DataFrame(schema={"category": pl.Utf8, "count": pl.Int64})
        except Exception as e:
            logger.error(f"Ошибка при сборе статистики: {e}")
            return {
                'total_parts': 0, 'total_oe': 0, 'total_brands': 0,
                'top_brands': pl.DataFrame(), 'categories': pl.DataFrame()
            }
        return stats

def main():
    st.title("🚗 AutoParts Catalog - Профессиональная система для 10+ млн записей")
    st.markdown("""
    ### 💪 Мощная платформа для управления большими объемами данных автозапчастей
    - **Инкрементальные обновления**: Безопасно добавляйте новые файлы для дополнения и обновления каталога.
    - **Надежное объединение**: Данные из 5-ти типов файлов корректно сливаются в единую базу.
    - **Оптимизированное хранение**: Использование DuckDB для мгновенного доступа и анализа.
    - **Умный экспорт**: Быстрый и надежный экспорт в CSV, Excel или Parquet с гарантией отсутствия дубликатов.
    """)
    
    catalog = HighVolumeAutoPartsCatalog()
    
    st.sidebar.title("🧭 Навигация")
    menu_option = st.sidebar.radio("Выберите действие:", ["Загрузка данных", "Экспорт", "Статистика", "Управление данными"])
    
    if menu_option == "Загрузка данных":
        st.header("📥 Загрузка и обработка данных")
        
        # Проверяем, пуста ли база данных
        is_database_empty = catalog.get_total_records() == 0
        
        if is_database_empty:
            st.warning("""
            ⚠️ **База данных пуста. Требуется начальная загрузка всех файлов.**
            
            Для первоначальной инициализации базы данных необходимо загрузить **все 5 файлов одновременно**:
            """)
            st.info("""
            **Типы Файлов (все обязательны для начальной загрузки):**
            1. **Основные данные (OE)**: OE номера, артикулы, бренд, наименование.
            2. **Кроссы (OE -> Артикул)**: Связь OE номеров с артикулами и брендами.
            3. **Штрих-коды**: Связь артикулов со штрих-кодами и кратностью.
            4. **Весогабариты**: Размеры и вес товаров.
            5. **Изображения**: Ссылки на изображения.
            """)
        else:
            st.success("✅ База данных содержит данные. Вы можете догружать файлы по одному или несколько одновременно.")
            st.info("""
            **💡 Дополнение данных:**
            - Вы можете загружать файлы **по одному** или **пачками** (несколько файлов одновременно).
            - Система использует механизм UPSERT: новые записи добавляются, существующие обновляются.
            - При повторной загрузке файла с теми же артикулами/брендами данные будут обновлены, а не продублированы.
            """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            oe_file = st.file_uploader("1. Основные данные (OE)", type=['xlsx', 'xls'])
            cross_file = st.file_uploader("2. Кроссы (OE -> Артикул)", type=['xlsx', 'xls'])
            barcode_file = st.file_uploader("3. Штрих-коды и кратность", type=['xlsx', 'xls'])
        with col2:
            dimensions_file = st.file_uploader("4. Весогабаритные данные", type=['xlsx', 'xls'])
            images_file = st.file_uploader("5. Ссылки на изображения", type=['xlsx', 'xls'])

        file_map = {
            'oe': oe_file, 'cross': cross_file, 'barcode': barcode_file,
            'dimensions': dimensions_file, 'images': images_file
        }
        
        if st.button("🚀 Начать обработку данных", type="primary"):
            paths_to_process = {}
            uploaded_files_count = 0
            for ftype, uploaded_file in file_map.items():
                if uploaded_file:
                    uploaded_files_count += 1
                    path = catalog.data_dir / f"{ftype}_data_{int(time.time())}_{uploaded_file.name}"
                    with open(path, "wb") as f: f.write(uploaded_file.getvalue())
                    paths_to_process[ftype] = str(path)
            
            # Проверка для начальной загрузки
            if is_database_empty:
                required_files = ['oe', 'cross', 'barcode', 'dimensions', 'images']
                missing_files = [ftype for ftype in required_files if ftype not in paths_to_process]
                if missing_files:
                    st.error(f"❌ Для начальной загрузки необходимо загрузить все 5 файлов. Отсутствуют: {', '.join(missing_files)}")
                elif uploaded_files_count == len(required_files):
                    stats = catalog.merge_all_data_parallel(paths_to_process)
                    if stats:
                        st.subheader("📊 Статистика обработки")
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Общее время", f"{stats.get('processing_time', 0):.2f} сек")
                        col2.metric("Всего артикулов в базе", f"{stats.get('total_records', 0):,}")
                        col3.metric("Обработано файлов", f"{len(paths_to_process)}")
                else:
                    st.error(f"❌ Для начальной загрузки необходимо загрузить все 5 файлов. Загружено: {uploaded_files_count} из {len(required_files)}")
            else:
                # Дозагрузка - можно загружать по одному или несколько файлов
                if uploaded_files_count > 0:
                    stats = catalog.merge_all_data_parallel(paths_to_process)
                    if stats:
                        st.subheader("📊 Статистика обработки")
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Общее время", f"{stats.get('processing_time', 0):.2f} сек")
                        col2.metric("Всего артикулов в базе", f"{stats.get('total_records', 0):,}")
                        col3.metric("Обработано файлов", f"{len(paths_to_process)}")
                else:
                    st.warning("⚠️ Пожалуйста, загрузите хотя бы один файл для обработки.")

    elif menu_option == "Экспорт":
        catalog.show_export_interface()
    
    elif menu_option == "Статистика":
        st.header("📈 Статистика по каталогу")
        with st.spinner("Сбор статистики..."):
            stats = catalog.get_statistics()
        
        if stats.get('total_parts', 0) > 0:
            col1, col2, col3 = st.columns(3)
            col1.metric("Уникальных артикулов", f"{stats.get('total_parts', 0):,}")
            col2.metric("Уникальных OE", f"{stats.get('total_oe', 0):,}")
            col3.metric("Уникальных брендов", f"{stats.get('total_brands', 0):,}")
            
            st.subheader("🏆 Топ-10 брендов по количеству артикулов")
            if 'top_brands' in stats and not stats['top_brands'].is_empty():
                st.dataframe(stats['top_brands'].to_pandas(), width='stretch')
            else:
                st.write("Нет данных по брендам.")

            st.subheader("📊 Распределение по категориям")
            if 'categories' in stats and not stats['categories'].is_empty():
                st.bar_chart(stats['categories'].to_pandas().set_index('category'))
            else:
                st.write("Нет данных по категориям.")
        else:
            st.info("Данные отсутствуют. Перейдите в раздел 'Загрузка данных', чтобы начать.")
    
    elif menu_option == "Управление данными":
        st.header("🗑️ Управление данными в базе")
        st.warning("⚠️ Будьте осторожны! Операции удаления необратимы.")
        
        management_option = st.radio("Выберите операцию:", ["Удалить по бренду", "Удалить по артикулу"])
        
        if management_option == "Удалить по бренду":
            st.subheader("🏭 Удалить все артикулы определенного бренда")
            
            # Get list of available brands - используем fetchall вместо .pl() для избежания проблем с pyarrow
            try:
                brands_result = catalog.conn.execute("SELECT DISTINCT brand FROM parts_data WHERE brand IS NOT NULL ORDER BY brand").fetchall()
                available_brands = [row[0] for row in brands_result] if brands_result else []
            except Exception as e:
                logger.error(f"Ошибка при получении списка брендов: {e}")
                st.error(f"❌ Ошибка при загрузке списка брендов: {e}")
                available_brands = []
            
            if available_brands:
                selected_brand = st.selectbox("Выберите бренд для удаления:", available_brands)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    brand_norm_result = catalog.conn.execute("SELECT brand_norm FROM parts_data WHERE brand = ? LIMIT 1", [selected_brand]).fetchone()
                    if brand_norm_result:
                        brand_norm = brand_norm_result[0]
                    else:
                        # Fallback: normalize the brand name if not found in DB
                        brand_series = pl.Series([selected_brand])
                        normalized_series = catalog.normalize_key(brand_series)
                        brand_norm = normalized_series[0] if len(normalized_series) > 0 else ""
                    
                    # Count records to delete using parameterized query
                    count_result = catalog.conn.execute("SELECT COUNT(*) FROM parts_data WHERE brand_norm = ?", [brand_norm]).fetchone()
                    count_to_delete = count_result[0] if count_result else 0
                    
                    st.info(f"К удалению: **{count_to_delete}** записей из бренда '{selected_brand}'")
                
                with col2:
                    confirm_delete_brand = st.checkbox("Я подтверждаю удаление всех записей этого бренда", key=f"confirm_brand_{selected_brand}")
                    if st.button("❌ Удалить все записи бренда", type="secondary", disabled=not confirm_delete_brand):
                        try:
                            deleted = catalog.delete_by_brand(brand_norm)
                            st.success(f"✅ Успешно удалено {deleted} записей для бренда '{selected_brand}'")
                            st.rerun()  # Перезагрузить страницу для обновления списка брендов
                        except Exception as e:
                            st.error(f"❌ Ошибка при удалении: {e}")
                    if not confirm_delete_brand:
                        st.caption("⚠️ Отметьте чекбокс для активации кнопки удаления")
            else:
                st.warning("Нет доступных брендов для удаления.")
        
        elif management_option == "Удалить по артикулу":
            st.subheader("📦 Удалить все записи определенного артикула")
            st.info("💡 Введите артикул (поиск без учета регистра и спецсимволов)")
            
            # Manual input for artikul
            input_artikul = st.text_input("Введите артикул для удаления:")
            
            if input_artikul:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Normalize input using the same method as the system
                    if input_artikul:
                        # Use the normalize_key method to ensure consistent normalization
                        input_series = pl.Series([input_artikul])
                        normalized_series = catalog.normalize_key(input_series)
                        artikul_norm = normalized_series[0] if len(normalized_series) > 0 else ""
                    else:
                        artikul_norm = ""
                    
                    # Count records to delete using parameterized query
                    count_result = catalog.conn.execute("SELECT COUNT(*) FROM parts_data WHERE artikul_norm = ?", [artikul_norm]).fetchone()
                    count_to_delete = count_result[0] if count_result else 0
                    
                    if count_to_delete > 0:
                        st.info(f"К удалению: **{count_to_delete}** записей артикула '{input_artikul}'")
                    else:
                        st.warning(f"Артикул '{input_artikul}' не найден в базе")
                
                with col2:
                    if count_to_delete > 0:
                        confirm_delete_artikul = st.checkbox("Я подтверждаю удаление всех записей этого артикула", key=f"confirm_artikul_{artikul_norm}")
                        if st.button("❌ Удалить все записи артикула", type="secondary", disabled=not confirm_delete_artikul):
                            try:
                                deleted = catalog.delete_by_artikul(artikul_norm)
                                st.success(f"✅ Успешно удалено {deleted} записей для артикула '{input_artikul}'")
                                st.rerun()  # Перезагрузить страницу для очистки поля ввода
                            except Exception as e:
                                st.error(f"❌ Ошибка при удалении: {e}")
                        if not confirm_delete_artikul:
                            st.caption("⚠️ Отметьте чекбокс для активации кнопки удаления")

if __name__ == "__main__":
    main()