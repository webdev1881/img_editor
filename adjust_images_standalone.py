import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import importlib.util
import requests
from urllib.parse import urlparse
import time
import re
import concurrent.futures
import json
import warnings
import traceback


# Импорт эмулятора весов
try:
    from scale_emulator import ScaleEmulator
except ImportError:
    # Если файл не найден, создаем заглушку
    class ScaleEmulator:
        def __init__(self, parent_notebook, output_dir="output"):
            tab = ttk.Frame(parent_notebook)
            parent_notebook.add(tab, text="Эмулятор весов")
            ttk.Label(tab, text="Модуль эмулятора весов не найден", font=('Arial', 14)).pack(pady=50)

# Импортируем PIL и OpenCV с обработкой ошибок
try:
    from PIL import Image
    import cv2
    import numpy as np
except ImportError as e:
    # Если библиотеки не установлены, сообщаем об этом пользователю
    error_msg = f"Ошибка импорта: {str(e)}\n"
    error_msg += "Пожалуйста, установите необходимые библиотеки:\n"
    error_msg += "pip install pillow opencv-python numpy requests"
    
    # Создаем простое окно с ошибкой, если tkinter доступен
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Ошибка импорта", error_msg)
        root.destroy()
    except:
        print(error_msg)
    
    sys.exit(1)

# Игнорируем предупреждения PIL для более чистого вывода
warnings.filterwarnings("ignore", category=UserWarning)

#######################################################
# ФУНКЦИИ ОБРАБОТКИ ИЗОБРАЖЕНИЙ
#######################################################

def clean_filename(filename):
    """
    Очищает строку, чтобы она могла использоваться как имя файла
    
    Args:
        filename (str): Исходная строка
    
    Returns:
        str: Очищенная строка, безопасная для использования в имени файла
    """
    # Заменяем недопустимые символы на подчеркивание
    return re.sub(r'[\\/*?:"<>|]', '_', filename)

def transform_json_to_urls(json_file, urls_file="urls.txt"):
    """
    Преобразует файл inp.json в формат urls.txt
    
    Args:
        json_file (str): Путь к JSON файлу
        urls_file (str): Путь для сохранения URLs
    
    Returns:
        int: Количество обработанных записей
    """
    try:
        # Загружаем JSON данные
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Проверяем, что данные являются списком
        if not isinstance(data, list):
            print(f"Ошибка: JSON должен содержать список объектов. Получено: {type(data)}")
            return 0
        
        # Открываем файл для записи URLs
        with open(urls_file, 'w', encoding='utf-8') as f:
            for item in data:
                # Проверяем наличие необходимых полей
                if 'article' in item and 'selectedImage' in item:
                    article = item['article']
                    image_url = item['selectedImage']
                    
                    # Записываем строку в формате "article,url"
                    f.write(f"{article},{image_url}\n")
        
        print(f"Трансформация завершена: {len(data)} записей сохранено в {urls_file}")
        return len(data)
    
    except Exception as e:
        print(f"Ошибка при трансформации JSON в URLs: {str(e)}")
        traceback.print_exc()
        return 0

def download_image(url_data, save_dir="input"):
    """
    Загружает изображение по URL и сохраняет в указанную директорию
    
    Args:
        url_data (tuple): Кортеж (article, url) или просто url
        save_dir (str): Директория для сохранения
    
    Returns:
        tuple: (article, путь к сохраненному файлу) или None в случае ошибки
    """
    try:
        # Создаем директорию, если не существует
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        # Определяем article и url
        if isinstance(url_data, tuple) and len(url_data) == 2:
            article, url = url_data
        else:
            url = url_data
            article = None
        
        # Очищаем article для использования как имя файла
        if article:
            filename = clean_filename(article)
        else:
            # Получаем имя файла из URL, если article не указан
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            
            # Если имя файла пустое или не содержит расширение, генерируем имя
            if not filename or '.' not in filename:
                filename = f"image_{int(time.time())}_{hash(url) % 10000}"
        
        # Добавляем расширение, если его нет
        if '.' not in filename:
            filename += '.jpg'
        
        save_path = os.path.join(save_dir, filename)
        
        # Загружаем и сохраняем изображение
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        print(f"Загружено: {url} -> {save_path}")
        return (article, save_path)
    
    except Exception as e:
        print(f"Ошибка при загрузке {url}: {str(e)}")
        return None

def download_images_from_urls(urls_data, save_dir="input", max_workers=5):
    """
    Загружает изображения из списка URL параллельно
    
    Args:
        urls_data (list): Список данных URL (строки или кортежи (article, url))
        save_dir (str): Директория для сохранения
        max_workers (int): Максимальное количество параллельных загрузок
    
    Returns:
        dict: Словарь {article: путь к файлу}
    """
    downloaded_files = {}
    
    # Используем ThreadPoolExecutor для параллельной загрузки
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(download_image, url_data, save_dir): url_data for url_data in urls_data}
        
        for future in concurrent.futures.as_completed(future_to_url):
            try:
                result = future.result()
                if result:
                    article, file_path = result
                    downloaded_files[article] = file_path
            except Exception as e:
                url_data = future_to_url[future]
                if isinstance(url_data, tuple):
                    article, url = url_data
                else:
                    url = url_data
                print(f"Ошибка при загрузке {url}: {str(e)}")
    
    print(f"Загружено {len(downloaded_files)} из {len(urls_data)} изображений")
    return downloaded_files

def enhance_image_quality(image):
    """
    Улучшает качество изображения с использованием OpenCV
    
    Args:
        image: Изображение PIL или путь к файлу
    
    Returns:
        PIL.Image: Улучшенное изображение
    """
    # Если передан путь к файлу, открываем изображение
    if isinstance(image, str):
        # Открываем с помощью OpenCV для лучшей совместимости с алгоритмами улучшения
        img_cv = cv2.imread(image)
        if img_cv is None:
            # Если OpenCV не может открыть файл, используем PIL
            pil_img = Image.open(image).convert('RGB')
            img_cv = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    else:
        # Преобразуем PIL Image в OpenCV формат
        img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    # Шаг 1: Уменьшаем шум, сохраняя детали (Non-local Means Denoising)
    dst = cv2.fastNlMeansDenoisingColored(img_cv, None, 10, 10, 7, 21)
    
    # Шаг 2: Улучшаем детали изображения (Unsharp Masking)
    gaussian = cv2.GaussianBlur(dst, (0, 0), 2.0)
    unsharp_image = cv2.addWeighted(dst, 1.5, gaussian, -0.5, 0, dst)
    
    # Шаг 3: Адаптивная эквализация гистограммы для улучшения контраста
    lab = cv2.cvtColor(unsharp_image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    enhanced_lab = cv2.merge((cl, a, b))
    enhanced_img = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
    
    # Шаг 4: Тонкая настройка насыщенности
    hsv = cv2.cvtColor(enhanced_img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    s = cv2.multiply(s, 1.2)  # Увеличиваем насыщенность на 20%
    enhanced_hsv = cv2.merge([h, s, v])
    final_enhanced = cv2.cvtColor(enhanced_hsv, cv2.COLOR_HSV2BGR)
    
    # Преобразуем обратно в PIL Image
    enhanced_pil = Image.fromarray(cv2.cvtColor(final_enhanced, cv2.COLOR_BGR2RGB))
    
    return enhanced_pil

def properly_convert_to_rgba(img):
    """
    Корректно преобразует изображение в RGBA, обрабатывая различные форматы
    
    Args:
        img: PIL.Image - исходное изображение
    
    Returns:
        PIL.Image: Изображение в формате RGBA
    """
    # Получаем информацию о режиме и прозрачности
    mode = img.mode
    
    # Проверяем, является ли изображение палитровым с прозрачностью
    if mode == 'P':
        # Попробуем получить информацию о прозрачности
        try:
            transparency = img.info.get('transparency')
            if transparency is not None:
                # Преобразуем в RGBA для корректной обработки прозрачности
                return img.convert('RGBA')
        except:
            pass
    
    # Если изображение уже в RGBA, просто возвращаем его
    if mode == 'RGBA':
        return img
    
    # Если изображение с альфа-каналом
    if 'A' in mode:
        return img.convert('RGBA')
    
    # Для остальных изображений преобразуем в RGB
    return img.convert('RGB')

def get_pil_format(ext):
    """
    Преобразует расширение файла в правильный формат PIL для сохранения
    
    Args:
        ext (str): Расширение файла (с точкой или без)
    
    Returns:
        str: Формат PIL для метода save()
    """
    # Удаляем точку, если она есть
    if ext.startswith('.'):
        ext = ext[1:]
    
    # Преобразуем в верхний регистр
    ext = ext.upper()
    
    # Исправляем некоторые распространенные форматы
    format_map = {
        'JPG': 'JPEG',
        'TIF': 'TIFF',
        'BMP': 'BMP',
        'PNG': 'PNG',
        'GIF': 'GIF',
        'WEBP': 'WEBP'
    }
    
    # Если формат известен, возвращаем правильное значение
    if ext in format_map:
        return format_map[ext]
    
    # По умолчанию используем JPEG
    return 'JPEG'

def detect_object_region(image):
    """
    Определяет регион, содержащий основной объект на изображении
    
    Args:
        image: PIL.Image или путь к файлу изображения
    
    Returns:
        tuple: (x, y, width, height) - координаты и размеры региона с объектом
               или None, если не удалось определить
    """
    try:
        # Если передан путь к файлу, открываем изображение
        if isinstance(image, str):
            img_cv = cv2.imread(image)
            if img_cv is None:
                pil_img = Image.open(image).convert('RGB')
                img_cv = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        else:
            img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Получаем размеры изображения
        height, width = img_cv.shape[:2]
        
        # Преобразуем в оттенки серого
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        # Применяем размытие по Гауссу для уменьшения шума
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Применяем детектор краев Canny
        edges = cv2.Canny(blurred, 50, 150)
        
        # Находим контуры на изображении
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Если контуры не найдены, пробуем другие методы
        if not contours:
            # Метод 2: Применяем OTSU бинаризацию
            _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Если контуры всё ещё не найдены, используем другие методы сегментации
        if not contours:
            # Метод 3: Используем watershedding
            ret, markers = cv2.connectedComponents(thresh)
            markers = markers + 1
            markers[thresh == 0] = 0
            markers = cv2.watershed(img_cv, markers)
            img_cv[markers == -1] = [0, 0, 255]  # Отмечаем границы красным
            
            # Создаем маску из результатов watershed
            mask = np.zeros_like(gray)
            mask[markers > 1] = 255
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Если контуры найдены, находим основной объект
        if contours:
            # Сортируем контуры по площади (от большего к меньшему)
            contours = sorted(contours, key=cv2.contourArea, reverse=True)
            
            # Проходим по контурам и ищем наиболее подходящий
            # (исключаем слишком маленькие и слишком большие)
            for contour in contours:
                area = cv2.contourArea(contour)
                
                # Исключаем слишком маленькие контуры
                if area < (width * height) * 0.01:  # Менее 1% от общей площади
                    continue
                
                # Исключаем слишком большие контуры (почти все изображение)
                if area > (width * height) * 0.95:  # Более 95% от общей площади
                    continue
                
                # Находим ограничивающий прямоугольник
                x, y, w, h = cv2.boundingRect(contour)
                
                # Пропускаем слишком узкие или широкие регионы
                aspect_ratio = w / h
                if aspect_ratio > 5 or aspect_ratio < 0.2:
                    continue
                
                # Добавляем небольшой отступ (10% от размера)
                padding_x = int(w * 0.1)
                padding_y = int(h * 0.1)
                
                # Учитываем границы изображения
                x = max(0, x - padding_x)
                y = max(0, y - padding_y)
                w = min(width - x, w + padding_x * 2)
                h = min(height - y, h + padding_y * 2)
                
                return (x, y, w, h)
            
            # Если ни один контур не подошел, используем первый большой контур
            if contours and cv2.contourArea(contours[0]) > (width * height) * 0.01:
                x, y, w, h = cv2.boundingRect(contours[0])
                return (x, y, w, h)
        
        # Если не удалось найти объект, анализируем распределение яркости
        # Создаем тепловую карту яркости
        heatmap = cv2.blur(gray, (width//10, height//10))
        
        # Находим область с наибольшей яркостью
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(heatmap)
        
        # Используем эту область как центр объекта
        obj_center_x, obj_center_y = max_loc
        obj_width = width // 2
        obj_height = height // 2
        
        # Корректируем координаты, чтобы объект был полностью виден
        x = max(0, obj_center_x - obj_width // 2)
        y = max(0, obj_center_y - obj_height // 2)
        w = min(width - x, obj_width)
        h = min(height - y, obj_height)
        
        return (x, y, w, h)
        
    except Exception as e:
        print(f"Ошибка при определении региона объекта: {str(e)}")
        return None

def detect_object_on_white_background(image):
    """
    Специализированная функция для обнаружения объектов на белом фоне
    
    Args:
        image: PIL.Image или путь к файлу изображения
    
    Returns:
        tuple: (x, y, width, height) - координаты и размеры региона с объектом
               или None, если не удалось определить
    """
    try:
        # Открываем изображение, если передан путь
        if isinstance(image, str):
            img_cv = cv2.imread(image)
            if img_cv is None:
                pil_img = Image.open(image).convert('RGB')
                img_cv = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        else:
            img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Получаем размеры изображения
        height, width = img_cv.shape[:2]
        
        # Преобразуем в оттенки серого
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        # Для белого фона используем пороговую бинаризацию для выделения объекта
        # Значение порога подобрано для выделения не-белых объектов
        _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        
        # Применяем морфологические операции для удаления шума и объединения близких областей
        kernel = np.ones((5, 5), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        
        # Находим контуры на бинаризованном изображении
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            print("Не найдены контуры для объекта на белом фоне")
            return None
        
        # Создаем маску для всех найденных объектов
        mask = np.zeros((height, width), dtype=np.uint8)
        for contour in contours:
            # Фильтруем слишком маленькие контуры (шум)
            area = cv2.contourArea(contour)
            if area > 100:  # Минимальная площадь в пикселях
                cv2.drawContours(mask, [contour], -1, 255, -1)
        
        # Находим границы объекта по маске
        non_zero_pixels = cv2.findNonZero(mask)
        if non_zero_pixels is None or len(non_zero_pixels) == 0:
            print("Не найдены пиксели объекта на белом фоне")
            return None
        
        # Определяем минимальный ограничивающий прямоугольник для всех найденных пикселей
        x, y, w, h = cv2.boundingRect(non_zero_pixels)
        
        # Добавляем небольшой отступ (5% от размера)
        padding_x = int(w * 0.05)
        padding_y = int(h * 0.05)
        
        # Учитываем границы изображения
        x = max(0, x - padding_x)
        y = max(0, y - padding_y)
        w = min(width - x, w + padding_x * 2)
        h = min(height - y, h + padding_y * 2)
        
        return (x, y, w, h)
        
    except Exception as e:
        print(f"Ошибка при определении объекта на белом фоне: {str(e)}")
        traceback.print_exc()
        return None

def smart_scale_image(image, target_ratio, fill_color=(255, 255, 255)):
    """
    Умное масштабирование изображения для равномерного распределения объекта
    
    Args:
        image: PIL.Image или путь к файлу изображения
        target_ratio: Целевое соотношение сторон (ширина/высота)
        fill_color: Цвет заполнения (по умолчанию белый)
    
    Returns:
        PIL.Image: Изображение с равномерно распределенным объектом
    """
    # Открываем изображение, если передан путь
    if isinstance(image, str):
        img = Image.open(image)
        img = properly_convert_to_rgba(img)
    else:
        img = image
    
    # Получаем размеры исходного изображения
    orig_width, orig_height = img.size
    
    # Вычисляем текущее соотношение сторон
    current_ratio = orig_width / orig_height
    
    # Определяем регион с объектом
    region = detect_object_region(img)
    
    # Если не удалось определить регион, используем стандартное масштабирование
    if region is None:
        print("Не удалось определить объект, используем стандартное масштабирование")
        return adjust_aspect_ratio_simple(img, target_ratio, fill_color)
    
    # Получаем координаты региона
    obj_x, obj_y, obj_width, obj_height = region
    
    # Вычисляем соотношение сторон объекта
    obj_ratio = obj_width / obj_height
    
    # Вычисляем центр объекта
    obj_center_x = obj_x + obj_width // 2
    obj_center_y = obj_y + obj_height // 2
    
    # Вычисляем относительное положение объекта на изображении
    rel_x = obj_center_x / orig_width
    rel_y = obj_center_y / orig_height
    
    # Определяем, как масштабировать изображение в зависимости от соотношения сторон
    if current_ratio > target_ratio:
        # Если текущее соотношение больше целевого, добавляем поля сверху и снизу
        new_width = orig_width
        new_height = int(orig_width / target_ratio)
        
        # Вычисляем верхний отступ на основе положения объекта
        # Если объект ближе к верху, сдвигаем его ниже, и наоборот
        padding_top = int((new_height - orig_height) * rel_y)
        padding_top = max(0, padding_top)
        padding_top = min(new_height - orig_height, padding_top)
        
        # Создаем новое изображение
        new_img = Image.new('RGB', (new_width, new_height), fill_color)
        # Вставляем оригинальное изображение
        new_img.paste(img, (0, padding_top))
        
    else:
        # Если текущее соотношение меньше целевого, добавляем поля слева и справа
        new_height = orig_height
        new_width = int(orig_height * target_ratio)
        
        # Вычисляем левый отступ на основе положения объекта
        # Если объект ближе к левому краю, сдвигаем его правее, и наоборот
        padding_left = int((new_width - orig_width) * rel_x)
        padding_left = max(0, padding_left)
        padding_left = min(new_width - orig_width, padding_left)
        
        # Создаем новое изображение
        new_img = Image.new('RGB', (new_width, new_height), fill_color)
        # Вставляем оригинальное изображение
        new_img.paste(img, (padding_left, 0))
    
    return new_img

def smart_scale_white_background(image, target_ratio, fill_color=(255, 255, 255), margin_percent=10):
    """
    Умное масштабирование изображения с объектом на белом фоне
    
    Args:
        image: PIL.Image или путь к файлу изображения
        target_ratio: Целевое соотношение сторон (ширина/высота)
        fill_color: Цвет заполнения (по умолчанию белый)
        margin_percent: Процент отступа от краёв (по умолчанию 10%)
    
    Returns:
        PIL.Image: Масштабированное изображение
    """
    # Открываем изображение, если передан путь
    if isinstance(image, str):
        img = Image.open(image)
        img = properly_convert_to_rgba(img)
    else:
        img = image
    
    # Получаем размеры исходного изображения
    orig_width, orig_height = img.size
    
    # Определяем регион с объектом
    region = detect_object_on_white_background(img)
    
    # Если не удалось определить регион, используем стандартное масштабирование
    if region is None:
        print("Не удалось определить объект, используем стандартное масштабирование")
        return adjust_aspect_ratio_simple(img, target_ratio, fill_color)
    
    # Получаем координаты объекта
    obj_x, obj_y, obj_width, obj_height = region
    
    # Вычисляем текущее соотношение сторон объекта
    obj_ratio = obj_width / obj_height
    
    # Вычисляем новый размер с учетом отступов
    # Отступ в процентах от размера объекта
    margin = max(int(min(obj_width, obj_height) * margin_percent / 100), 10)
    
    # Новые размеры объекта (с отступами)
    new_obj_width = obj_width + 2 * margin
    new_obj_height = obj_height + 2 * margin
    new_obj_ratio = new_obj_width / new_obj_height
    
    # Вычисляем финальные размеры с учетом целевого соотношения
    if new_obj_ratio > target_ratio:
        # Если соотношение объекта больше целевого, подгоняем по ширине
        final_width = new_obj_width
        final_height = int(final_width / target_ratio)
    else:
        # Если соотношение объекта меньше целевого, подгоняем по высоте
        final_height = new_obj_height
        final_width = int(final_height * target_ratio)
    
    # Создаем новое изображение
    new_img = Image.new('RGB', (final_width, final_height), fill_color)
    
# Вычисляем координаты для вставки исходного изображения
    paste_x = (final_width - orig_width) // 2
    paste_y = (final_height - orig_height) // 2
    
    # Вставляем исходное изображение
    new_img.paste(img, (paste_x, paste_y))
    
    # Кадрируем область вокруг объекта с отступами
    crop_x = max(0, paste_x + obj_x - margin)
    crop_y = max(0, paste_y + obj_y - margin)
    crop_width = min(final_width - crop_x, obj_width + 2 * margin)
    crop_height = min(final_height - crop_y, obj_height + 2 * margin)
    
    # Кадрируем изображение
    cropped_img = new_img.crop((crop_x, crop_y, crop_x + crop_width, crop_y + crop_height))
    
    # Масштабируем до целевого соотношения
    if crop_width / crop_height > target_ratio:
        scaled_height = int(crop_width / target_ratio)
        scaled_img = Image.new('RGB', (crop_width, scaled_height), fill_color)
        paste_y = (scaled_height - crop_height) // 2
        scaled_img.paste(cropped_img, (0, paste_y))
    else:
        scaled_width = int(crop_height * target_ratio)
        scaled_img = Image.new('RGB', (scaled_width, crop_height), fill_color)
        paste_x = (scaled_width - crop_width) // 2
        scaled_img.paste(cropped_img, (paste_x, 0))
    
    return scaled_img

def adjust_aspect_ratio_simple(img, target_ratio, fill_color=(255, 255, 255)):
    """
    Простое изменение соотношения сторон путем добавления полей
    
    Args:
        img: PIL.Image - исходное изображение
        target_ratio: Целевое соотношение сторон (ширина/высота)
        fill_color: Цвет заполнения (по умолчанию белый)
    
    Returns:
        PIL.Image: Изображение с измененным соотношением сторон
    """
    # Получаем размеры исходного изображения
    orig_width, orig_height = img.size
    
    # Вычисляем текущее соотношение сторон
    current_ratio = orig_width / orig_height
    
    if current_ratio > target_ratio:
        # Если текущее соотношение больше целевого
        # нужно добавить поля сверху и снизу
        new_width = orig_width
        new_height = int(orig_width / target_ratio)
        padding_top = (new_height - orig_height) // 2
        
        # Создаем новое изображение
        new_img = Image.new('RGB', (new_width, new_height), fill_color)
        # Вставляем оригинальное изображение
        new_img.paste(img, (0, padding_top))
        
    else:
        # Если текущее соотношение меньше целевого
        # нужно добавить поля слева и справа
        new_height = orig_height
        new_width = int(orig_height * target_ratio)
        padding_left = (new_width - orig_width) // 2
        
        # Создаем новое изображение
        new_img = Image.new('RGB', (new_width, new_height), fill_color)
        # Вставляем оригинальное изображение
        new_img.paste(img, (padding_left, 0))
    
    return new_img

def adjust_aspect_ratio(image_path, output_path, target_ratio, fill_color=(255, 255, 255), enhance=False, smart_scale=False, white_background=False, scale_factor=1.5):
    """
    Adjust image to target aspect ratio by adding padding with specified color
    without changing or stretching the original image.
    
    Args:
        image_path (str): Path to the input image
        output_path (str): Path to save the processed image
        target_ratio (float): Target aspect ratio (width/height)
        fill_color (tuple): RGB color for padding (default: white)
        enhance (bool): Whether to enhance the image quality
        smart_scale (bool): Whether to use smart scaling for object detection
        white_background (bool): Whether to use specialized detection for white backgrounds
        scale_factor (float): Масштаб увеличения объекта (1.0 = без изменений)
    """
    try:
        # Открываем изображение
        img = Image.open(image_path)
        
        # Корректно конвертируем изображение с учетом альфа-канала и палитры
        img = properly_convert_to_rgba(img)
        
        # Если есть альфа-канал, создаем фон и накладываем изображение
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, fill_color)
            background.paste(img, (0, 0), img)
            img = background
        else:
            img = img.convert('RGB')
        
        # Улучшаем качество изображения, если указано
        if enhance:
            print(f"Улучшаем качество изображения: {os.path.basename(image_path)}")
            img = enhance_image_quality(img)
        
        # Специальная обработка для объектов на белом фоне
        if white_background:
            print(f"Применяем специальный режим для белого фона: {os.path.basename(image_path)}")
            # Определяем регион с объектом
            region = detect_object_on_white_background(img)
            
            if region:
                # Получаем координаты объекта
                obj_x, obj_y, obj_width, obj_height = region
                
                # Увеличиваем объект в соответствии с заданным масштабом
                # При этом сохраняем его положение на изображении
                if scale_factor != 1.0:
                    # Вырезаем объект
                    obj_img = img.crop((obj_x, obj_y, obj_x + obj_width, obj_y + obj_height))
                    
                    # Определяем новый размер объекта после масштабирования
                    new_obj_width = int(obj_width * scale_factor)
                    new_obj_height = int(obj_height * scale_factor)
                    
                    # Изменяем размер объекта
                    resized_obj = obj_img.resize((new_obj_width, new_obj_height), Image.LANCZOS)
                    
                    # Создаем новое изображение подходящего размера
                    new_width = max(img.width, new_obj_width + 2 * (obj_x // 2))
                    new_height = max(img.height, new_obj_height + 2 * (obj_y // 2))
                    
                    # Создаем новое изображение
                    new_img = Image.new('RGB', (new_width, new_height), fill_color)
                    
                    # Вычисляем положение для вставки увеличенного объекта (центрирование)
                    paste_x = (new_width - new_obj_width) // 2
                    paste_y = (new_height - new_obj_height) // 2
                    
                    # Вставляем увеличенный объект
                    new_img.paste(resized_obj, (paste_x, paste_y))
                    
                    # Используем новое изображение для дальнейшей обработки
                    img = new_img
            
            # Применяем специальное масштабирование для белого фона
            new_img = smart_scale_white_background(img, target_ratio, fill_color)
        # Используем умное масштабирование для других изображений
        elif smart_scale:
            print(f"Применяем умное масштабирование: {os.path.basename(image_path)}")
            new_img = smart_scale_image(img, target_ratio, fill_color)
        else:
            # Стандартное масштабирование для обычных изображений
            # Получаем размеры исходного изображения
            orig_width, orig_height = img.size
            
            # Вычисляем текущее соотношение сторон
            current_ratio = orig_width / orig_height
            
            if current_ratio > target_ratio:
                # Если текущее соотношение больше целевого, добавляем поля сверху и снизу
                new_width = orig_width
                new_height = int(orig_width / target_ratio)
                padding_top = (new_height - orig_height) // 2
                
                # Создаем новое изображение
                new_img = Image.new('RGB', (new_width, new_height), fill_color)
                # Вставляем оригинальное изображение
                new_img.paste(img, (0, padding_top))
                
            else:
                # Если текущее соотношение меньше целевого, добавляем поля слева и справа
                new_height = orig_height
                new_width = int(orig_height * target_ratio)
                padding_left = (new_width - orig_width) // 2
                
                # Создаем новое изображение
                new_img = Image.new('RGB', (new_width, new_height), fill_color)
                # Вставляем оригинальное изображение
                new_img.paste(img, (padding_left, 0))
        
        # Определяем формат для сохранения на основе расширения выходного файла
        _, ext = os.path.splitext(output_path)
        save_format = get_pil_format(ext)
        
        # Сохраняем изображение с правильным форматом и параметрами
        if save_format == 'JPEG':
            new_img.save(output_path, format=save_format, quality=95, optimize=True)
        else:
            new_img.save(output_path, format=save_format)
            
        return True
    
    except Exception as e:
        print(f"Ошибка при обработке изображения {image_path}: {str(e)}")
        traceback.print_exc()  # Печатаем полный стек-трейс для отладки
        return False

def process_directory(input_dir="input", output_dir="output", target_ratio=1.0, fill_color=(255, 255, 255), 
                      file_mapping=None, enhance=False, smart_scale=False, white_background=False, scale_factor=1.5):
    """
    Process all images in a directory to adjust their aspect ratio
    
    Args:
        input_dir (str): Directory with input images
        output_dir (str): Directory to save processed images
        target_ratio (float): Target aspect ratio (width/height)
        fill_color (tuple): RGB color for padding
        file_mapping (dict): Маппинг {article: путь_к_файлу} для определения выходных имен файлов
        enhance (bool): Whether to enhance the image quality
        smart_scale (bool): Whether to use smart scaling for object detection
        white_background (bool): Whether to use specialized detection for white backgrounds
        scale_factor (float): Масштаб увеличения объекта (1.0 = без изменений)
    """
    # Создаем выходную директорию, если она не существует
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Обрабатываем все файлы в директории
    successful = 0
    failed = 0
    
    # Если есть маппинг файлов, используем его
    if file_mapping:
        files_to_process = []
        for article, input_path in file_mapping.items():
            if os.path.isfile(input_path):
                # Определяем расширение входного файла
                _, ext = os.path.splitext(input_path)
                # Если у article нет расширения, добавляем
                if '.' not in article:
                    output_filename = clean_filename(article) + ext
                else:
                    output_filename = clean_filename(article)
                
                # Убедимся, что у выходного файла есть расширение
                if '.' not in output_filename:
                    output_filename += '.jpg'
                
                output_path = os.path.join(output_dir, output_filename)
                files_to_process.append((input_path, output_path))
    else:
        # Получаем список всех файлов для обработки
        files_to_process = []
        for filename in os.listdir(input_dir):
            input_path = os.path.join(input_dir, filename)
            
            # Проверяем, является ли файл изображением
            if os.path.isfile(input_path) and filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
                output_path = os.path.join(output_dir, filename)
                files_to_process.append((input_path, output_path))
    
    total_files = len(files_to_process)
    if total_files == 0:
        print(f"Не найдено изображений для обработки")
        return
    
    print(f"Найдено {total_files} изображений для обработки")
    
    # Обрабатываем каждое изображение
    for i, (input_path, output_path) in enumerate(files_to_process):
        print(f"Обработка {i+1}/{total_files}: {os.path.basename(input_path)} -> {os.path.basename(output_path)}")
        
        if adjust_aspect_ratio(input_path, output_path, target_ratio, fill_color, enhance, smart_scale, white_background, scale_factor):
            successful += 1
        else:
            failed += 1
    
    print(f"Обработка завершена: {successful} изображений успешно обработано, {failed} ошибок")

def parse_color(color_str):
    """
    Parse color string in format 'r,g,b' to RGB tuple
    """
    try:
        r, g, b = map(int, color_str.split(','))
        return (r, g, b)
    except:
        raise argparse.ArgumentTypeError("Цвет должен быть в формате 'r,g,b', например '255,0,0' для красного")

def parse_urls_file(file_path):
    """
    Читает файл со списком URL в формате "article,url"
    
    Args:
        file_path (str): Путь к файлу с URL
    
    Returns:
        list: Список кортежей (article, url)
    """
    result = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            parts = line.split(',', 1)  # Разделяем строку по первой запятой
            if len(parts) == 2:
                article, url = parts
                result.append((article.strip(), url.strip()))
            else:
                # Если в строке нет запятой, считаем, что это только URL
                result.append(('image_' + str(len(result)), line))
    
    return result

def visualize_object_detection(image_path, output_path=None):
    """
    Визуализирует обнаруженный объект на изображении, отмечая его рамкой
    
    Args:
        image_path (str): Путь к исходному изображению
        output_path (str, optional): Путь для сохранения результата. Если None,
                                    результат не сохраняется, а отображается.
    
    Returns:
        PIL.Image: Изображение с отмеченным объектом
    """
    try:
        # Открываем изображение
        img = Image.open(image_path)
        img = properly_convert_to_rgba(img)
        
        # Преобразуем в RGB для работы с OpenCV
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, (0, 0), img)
            img = background
        else:
            img = img.convert('RGB')
        
        # Получаем регион с объектом
        print("Ищем объект стандартным методом...")
        region = detect_object_region(img)
        
        if region is None:
            print("Стандартный метод не нашел объект, пробуем метод для белого фона...")
            region = detect_object_on_white_background(img)
        
        # Если не удалось определить регион, сообщаем об этом
        if region is None:
            print("Не удалось определить объект на изображении")
            return img
        
        # Получаем координаты региона
        obj_x, obj_y, obj_width, obj_height = region
        
        # Создаем копию изображения для отрисовки
        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        
        # Отрисовываем прямоугольник
        cv2.rectangle(img_cv, (obj_x, obj_y), (obj_x + obj_width, obj_y + obj_height), (0, 255, 0), 2)
        
        # Добавляем надпись
        cv2.putText(img_cv, "Object", (obj_x, obj_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        
        # Преобразуем обратно в PIL Image
        result_img = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))
        
        # Если указан путь для сохранения, сохраняем результат
        if output_path:
            result_img.save(output_path)
            print(f"Визуализация сохранена в {output_path}")
        
        return result_img
        
    except Exception as e:
        print(f"Ошибка при визуализации обнаруженного объекта: {str(e)}")
        traceback.print_exc()
        return None

def main():
    """
    Основная функция для запуска обработки изображений
    """
    parser = argparse.ArgumentParser(description='Изменение пропорций изображений путем добавления полей')
    
    # Основные параметры
    parser.add_argument('--ratio', type=float, default=1.0, help='Целевое соотношение сторон (ширина/высота), например 16/9=1.78')
    parser.add_argument('--color', type=str, default='255,255,255', help='Цвет заполнения в формате r,g,b (по умолчанию белый: 255,255,255)')
    parser.add_argument('--input', type=str, default='input', help='Директория с входными изображениями (по умолчанию: input)')
    parser.add_argument('--output', type=str, default='output', help='Директория для сохранения обработанных изображений (по умолчанию: output)')
    
    # Параметры для загрузки изображений из URL
    parser.add_argument('--urls', nargs='+', help='Список URL для загрузки изображений')
    parser.add_argument('--urls-file', type=str, help='Файл со списком URL в формате "article,url" (по одной паре на строку)')
    parser.add_argument('--max-workers', type=int, default=5, help='Максимальное количество параллельных загрузок (по умолчанию: 5)')
    
    # Параметр для улучшения качества изображений
    parser.add_argument('--enhance', action='store_true', help='Улучшить качество изображений с помощью ИИ-алгоритмов')
    
    # Параметры для работы с JSON
    parser.add_argument('--json-file', type=str, help='Путь к JSON файлу для преобразования в urls.txt')
    parser.add_argument('--json-to-urls', action='store_true', help='Преобразовать JSON файл в urls.txt')
    
    # Параметр для умного масштабирования
    parser.add_argument('--smart-scale', action='store_true', help='Использовать умное масштабирование для равномерного распределения объекта')
    
    # Параметры для специального режима белого фона
    parser.add_argument('--white-background', action='store_true', help='Использовать специальный режим для объектов на белом фоне')
    parser.add_argument('--scale-factor', type=float, default=1.5, help='Масштаб увеличения объекта (1.0 = без изменений, по умолчанию: 1.5)')
    
    # Параметр для визуализации обнаруженных объектов
    parser.add_argument('--visualize-object', type=str, help='Визуализировать обнаруженный объект на указанном изображении')
    parser.add_argument('--visualize-output', type=str, help='Путь для сохранения визуализации (по умолчанию: object_detected.jpg)')
    
    args = parser.parse_args()
    
    # Визуализация обнаруженного объекта, если указано
    if args.visualize_object:
        output_path = args.visualize_output if args.visualize_output else "object_detected.jpg"
        visualize_object_detection(args.visualize_object, output_path)
        return
    
    # Преобразуем строку цвета в кортеж RGB
    fill_color = parse_color(args.color)
    
    # Проверяем, нужно ли преобразовать JSON в URLs
    if args.json_file and args.json_to_urls:
        output_urls_file = args.urls_file if args.urls_file else "urls.txt"
        transform_json_to_urls(args.json_file, output_urls_file)
        # Если не нужно обрабатывать изображения, выходим
        if not any([args.urls, output_urls_file, os.path.exists(args.input)]):
            return
        
        # Устанавливаем urls_file для дальнейшей обработки
        args.urls_file = output_urls_file
    
    # Проверяем, нужно ли загрузить изображения по URL
    urls_data = []
    file_mapping = None
    
    if args.urls:
        # Простой список URL без article
        urls_data.extend(args.urls)
    
    if args.urls_file:
        try:
            # Парсим файл с URLs в формате "article,url"
            file_urls = parse_urls_file(args.urls_file)
            urls_data.extend(file_urls)
        except Exception as e:
            print(f"Ошибка при чтении файла URL: {str(e)}")
    
    # Загружаем изображения, если указаны URL
    if urls_data:
        print(f"Загрузка {len(urls_data)} изображений...")
        file_mapping = download_images_from_urls(urls_data, args.input, args.max_workers)
    
    # Обрабатываем директорию с изображениями
    print(f"Обработка изображений с соотношением сторон {args.ratio}...")
    if args.enhance:
        print("Включено улучшение качества изображений")
    if args.smart_scale:
        print("Включено умное масштабирование для равномерного распределения объекта")
    if args.white_background:
        print(f"Включен специальный режим для белого фона с масштабом {args.scale_factor}")
    
    process_directory(args.input, args.output, args.ratio, fill_color, file_mapping, args.enhance, args.smart_scale, args.white_background, args.scale_factor)

#######################################################
# ГРАФИЧЕСКИЙ ИНТЕРФЕЙС
#######################################################

class AdjustImagesGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("TS-5 Images Tool (SMK)")
        # self.root.geometry("800x400")
        self.root.minsize(800, 600)
        
        # Определяем путь к директории исполняемого файла
        if getattr(sys, 'frozen', False):
            self.application_path = os.path.dirname(sys.executable)
        else:
            self.application_path = os.path.dirname(os.path.abspath(__file__))
        
        # Стиль
        style = ttk.Style()
        style.configure("TButton", padding=6, relief="flat", font=('Arial', 10))
        style.configure("TLabel", font=('Arial', 10))
        style.configure("TCheckbutton", font=('Arial', 10))
        style.configure("TRadiobutton", font=('Arial', 10))
        style.configure("Header.TLabel", font=('Arial', 12, 'bold'))
        
        # Основной фрейм
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        header = ttk.Label(main_frame, text="Параметры обработки изображений", style="Header.TLabel")
        header.pack(pady=(0, 20))
        
        # Создаем notebook (вкладки)
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Вкладка 1: Основные настройки
        basic_tab = ttk.Frame(notebook, padding=10)
        notebook.add(basic_tab, text="Основные настройки")
        
        # Вкладка 2: Загрузка изображений
        loading_tab = ttk.Frame(notebook, padding=10)
        notebook.add(loading_tab, text="Загрузка изображений")
        
        # Вкладка 3: Обработка изображений
        processing_tab = ttk.Frame(notebook, padding=10)
        notebook.add(processing_tab, text="Обработка изображений")
        
        # Вкладка 4: Примеры и справка
        # help_tab = ttk.Frame(notebook, padding=10)
        # notebook.add(help_tab, text="Примеры и справка")

        # Фрейм для вывода команды и логов
        output_frame = ttk.LabelFrame(main_frame, text="Лог выполнения", padding=10)
        output_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Текстовое поле для вывода логов
        self.log_text = tk.Text(output_frame, height=8, width=80, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Добавляем скролл для логов
        log_scrollbar = ttk.Scrollbar(self.log_text, orient='vertical', command=self.log_text.yview)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=log_scrollbar.set)
        
        # Кнопки внизу
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.run_button = ttk.Button(button_frame, text="Запустить обработку", command=self.run_processing)
        self.run_button.pack(side=tk.RIGHT, padx=5)
        
        # Инициализируем переменные
        self.init_variables()
        
        # Заполняем вкладки
        self.setup_basic_tab(basic_tab)
        self.setup_loading_tab(loading_tab)
        self.setup_processing_tab(processing_tab)
        # self.setup_help_tab(help_tab)
        
        # Добавляем эмулятор весов (перед выводом приветственного сообщения)
        # self.scale_emulator = ScaleEmulator(notebook, self.output_dir.get())


        # Выводим приветственное сообщение
        # self.log_text.insert(tk.END, "Добро пожаловать в Adjust Images Tool!\n")
        self.log_text.insert(tk.END, "'Запустить обработку'.\n")
        
    def init_variables(self):
        # Основные настройки
        self.input_dir = tk.StringVar(value=os.path.join(self.application_path, "input"))
        self.output_dir = tk.StringVar(value=os.path.join(self.application_path, "output"))
        self.ratio = tk.DoubleVar(value=1.0)
        self.ratio_custom = tk.StringVar(value="1.33")
        self.ratio_option = tk.StringVar(value="custom")
        self.color = tk.StringVar(value="255,255,255")
        
        # Загрузка изображений
        self.urls_option = tk.StringVar(value="none")
        self.urls_file = tk.StringVar(value=os.path.join(self.application_path, "urls.txt"))
        self.json_file = tk.StringVar(value=os.path.join(self.application_path, "inp.json"))
        self.max_workers = tk.IntVar(value=5)
        
        # Обработка изображений
        self.enhance = tk.BooleanVar(value=False)
        self.smart_scale = tk.BooleanVar(value=False)
        self.white_background = tk.BooleanVar(value=False)
        self.scale_factor = tk.DoubleVar(value=1.5)
        
        # Визуализация
# Визуализация
        self.visualize = tk.BooleanVar(value=False)
        self.visualize_file = tk.StringVar(value="")
        self.visualize_output = tk.StringVar(value=os.path.join(self.application_path, "object_detected.jpg"))
        
    def setup_basic_tab(self, parent):
        # Директории ввода и вывода
        dir_frame = ttk.LabelFrame(parent, text="Директории", padding=10)
        dir_frame.pack(fill=tk.X, pady=1)
        
        ttk.Label(dir_frame, text="Входная директория:").grid(row=0, column=0, sticky=tk.W, pady=5)
        input_entry = ttk.Entry(dir_frame, textvariable=self.input_dir, width=40)
        input_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        ttk.Button(dir_frame, text="Обзор...", command=lambda: self.browse_directory(self.input_dir)).grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(dir_frame, text="Выходная директория:").grid(row=1, column=0, sticky=tk.W, pady=5)
        output_entry = ttk.Entry(dir_frame, textvariable=self.output_dir, width=40)
        output_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        ttk.Button(dir_frame, text="Обзор...", command=lambda: self.browse_directory(self.output_dir)).grid(row=1, column=2, padx=5, pady=5)
        
        # Соотношение сторон
        ratio_frame = ttk.LabelFrame(parent, text="Соотношение сторон", padding=10)
        ratio_frame.pack(fill=tk.X, pady=5)
        
        ttk.Radiobutton(ratio_frame, text="1:1 (квадрат)", variable=self.ratio_option, value="1:1", 
                       command=lambda: self.set_ratio(1.)).grid(row=0, column=0, sticky=tk.W, pady=2)
        
        ttk.Radiobutton(ratio_frame, text="4:3", variable=self.ratio_option, value="4:3", 
                       command=lambda: self.set_ratio(4.0/3.0)).grid(row=1, column=0, sticky=tk.W, pady=2)
        
        ttk.Radiobutton(ratio_frame, text="16:9 (широкоэкранный)", variable=self.ratio_option, value="16:9", 
                       command=lambda: self.set_ratio(16.0/9.0)).grid(row=2, column=0, sticky=tk.W, pady=2)
        
        ttk.Radiobutton(ratio_frame, text="2:1", variable=self.ratio_option, value="2:1", 
                       command=lambda: self.set_ratio(2.0)).grid(row=3, column=0, sticky=tk.W, pady=2)
        
        ttk.Radiobutton(ratio_frame, text="Своё значение:", variable=self.ratio_option, value="custom").grid(row=4, column=0, sticky=tk.W, pady=2)
        
        custom_entry = ttk.Entry(ratio_frame, textvariable=self.ratio_custom, width=10)
        custom_entry.grid(row=4, column=1, padx=5, pady=2, sticky=tk.W)
        custom_entry.bind("<KeyRelease>", lambda e: self.update_ratio_from_custom())
        
        # ttk.Label(ratio_frame, text="Примеры: 1.0 (1:1), 1.78 (16:9), 0.75 (3:4)").grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Цвет заполнения
        color_frame = ttk.LabelFrame(parent, text="Цвет заполнения", padding=10)
        color_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(color_frame, text="RGB цвет (r,g,b):").grid(row=0, column=0, sticky=tk.W, pady=5)
        color_entry = ttk.Entry(color_frame, textvariable=self.color, width=20)
        color_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        color_buttons_frame = ttk.Frame(color_frame)
        color_buttons_frame.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        ttk.Button(color_buttons_frame, text="Белый", command=lambda: self.set_color("255,255,255")).pack(side=tk.LEFT, padx=5)
        ttk.Button(color_buttons_frame, text="Черный", command=lambda: self.set_color("0,0,0")).pack(side=tk.LEFT, padx=5)
        ttk.Button(color_buttons_frame, text="Серый", command=lambda: self.set_color("128,128,128")).pack(side=tk.LEFT, padx=5)
        ttk.Button(color_buttons_frame, text="Прозрачный", command=lambda: self.set_color("0,0,0,0")).pack(side=tk.LEFT, padx=5)
    
    def setup_loading_tab(self, parent):
        # Опции загрузки
        option_frame = ttk.LabelFrame(parent, text="Источник изображений", padding=10)
        option_frame.pack(fill=tk.X, pady=5)
        
        ttk.Radiobutton(option_frame, text="Только локальные изображения из входной директории", 
                       variable=self.urls_option, value="none").grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        ttk.Radiobutton(option_frame, text="Загрузить из URLs файла:", 
                       variable=self.urls_option, value="urls").grid(row=1, column=0, sticky=tk.W, pady=5)
        
        urls_entry = ttk.Entry(option_frame, textvariable=self.urls_file, width=40)
        urls_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        
        ttk.Button(option_frame, text="Обзор...", 
                  command=lambda: self.browse_file(self.urls_file, [("Text files", "*.txt"), ("All files", "*.*")])).grid(row=1, column=2, padx=5, pady=5)
        
        ttk.Radiobutton(option_frame, text="Преобразовать JSON в URLs и загрузить:", 
                       variable=self.urls_option, value="json").grid(row=2, column=0, sticky=tk.W, pady=5)
        
        json_entry = ttk.Entry(option_frame, textvariable=self.json_file, width=40)
        json_entry.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        
        ttk.Button(option_frame, text="Обзор...", 
                  command=lambda: self.browse_file(self.json_file, [("JSON files", "*.json"), ("All files", "*.*")])).grid(row=2, column=2, padx=5, pady=5)
        
        # Дополнительные параметры загрузки
        workers_frame = ttk.LabelFrame(parent, text="Дополнительные параметры загрузки", padding=10)
        workers_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(workers_frame, text="Количество параллельных загрузок:").grid(row=0, column=0, sticky=tk.W, pady=5)
        workers_spinbox = ttk.Spinbox(workers_frame, from_=1, to=20, width=5, textvariable=self.max_workers)
        workers_spinbox.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(workers_frame, text="(увеличьте для более быстрой загрузки, но следите за нагрузкой)").grid(row=0, column=2, sticky=tk.W, pady=5)
    
    def setup_processing_tab(self, parent):
        # Опции обработки
        option_frame = ttk.LabelFrame(parent, text="Опции обработки изображений", padding=10)
        option_frame.pack(fill=tk.X, pady=5)
        
        ttk.Checkbutton(option_frame, text="Улучшить качество изображений (увеличить резкость, контраст)", 
                       variable=self.enhance).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        ttk.Checkbutton(option_frame, text="Использовать умное масштабирование (для обычных изображений)", 
                       variable=self.smart_scale, command=self.toggle_smart_scale).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        ttk.Checkbutton(option_frame, text="Специальный режим для объектов на белом фоне", 
                       variable=self.white_background, command=self.toggle_white_background).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        ttk.Label(option_frame, text="Масштаб увеличения объекта:").grid(row=3, column=0, sticky=tk.W, pady=5)
        scale_spinbox = ttk.Spinbox(option_frame, from_=1.0, to=3.0, increment=0.1, width=5, textvariable=self.scale_factor)
        scale_spinbox.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Визуализация (для отладки)
        vis_frame = ttk.LabelFrame(parent, text="Визуализация обнаружения объекта (для отладки)", padding=10)
        vis_frame.pack(fill=tk.X, pady=5)
        
        ttk.Checkbutton(vis_frame, text="Визуализировать обнаружение объекта на изображении", 
                       variable=self.visualize, command=self.toggle_visualize).grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        ttk.Label(vis_frame, text="Файл для визуализации:").grid(row=1, column=0, sticky=tk.W, pady=5)
        vis_entry = ttk.Entry(vis_frame, textvariable=self.visualize_file, width=40)
        vis_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        ttk.Button(vis_frame, text="Обзор...", 
                  command=lambda: self.browse_file(self.visualize_file, [("Image files", "*.jpg;*.jpeg;*.png"), ("All files", "*.*")])).grid(row=1, column=2, padx=5, pady=5)
        
        ttk.Label(vis_frame, text="Сохранить результат в:").grid(row=2, column=0, sticky=tk.W, pady=5)
        vis_out_entry = ttk.Entry(vis_frame, textvariable=self.visualize_output, width=40)
        vis_out_entry.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        ttk.Button(vis_frame, text="Обзор...", 
                  command=lambda: self.browse_file(self.visualize_output, [("Image files", "*.jpg;*.jpeg;*.png"), ("All files", "*.*")], save=True)).grid(row=2, column=2, padx=5, pady=5)
    
    def setup_help_tab(self, parent):
        help_text = """
        # Обработка изображений - Справка и примеры
        
        ## Основные использования:

        1. **Базовая обработка изображений из локальной папки**:
           - Укажите входную и выходную директории
           - Выберите соотношение сторон
           - Нажмите "Запустить обработку"
        
        2. **Загрузка изображений из URL**:
           - Выберите "Загрузить из URLs файла"
           - Укажите путь к файлу urls.txt (формат: "article,url" по одной паре на строку)
           - Выберите соотношение сторон и другие настройки
           - Нажмите "Запустить обработку"
        
        3. **Загрузка изображений из JSON**:
           - Выберите "Преобразовать JSON в URLs и загрузить"
           - Укажите путь к файлу inp.json
           - Выберите соотношение сторон и другие настройки
           - Нажмите "Запустить обработку"
        
        4. **Улучшение качества изображений на белом фоне**:
           - Включите "Специальный режим для объектов на белом фоне"
           - Установите масштаб увеличения объекта (1.5-2.0 обычно дает хорошие результаты)
           - Выберите соотношение сторон
           - Нажмите "Запустить обработку"
        
        5. **Отладка обнаружения объектов**:
           - Включите "Визуализировать обнаружение объекта"
           - Выберите изображение для визуализации
           - Укажите путь для сохранения результата
           - Нажмите "Запустить обработку"
        
        ## Форматы файлов:
        
        - **urls.txt**: Один URL на строку или формат "article,URL" для именования файлов
        - **inp.json**: Массив объектов с полями "article" и "selectedImage"
        
        ## Советы:
        
        - Для продуктовых фотографий на белом фоне используйте "Специальный режим для белого фона"
        - Если объект слишком маленький, увеличьте значение масштаба (1.5-2.0)
        - Для улучшения качества фотографий включите опцию "Улучшить качество изображений"
        - При загрузке большого количества изображений, увеличьте количество параллельных загрузок
        """
        
        text_widget = tk.Text(parent, wrap=tk.WORD, height=25)
        text_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Добавляем скролл для текста справки
        scrollbar = ttk.Scrollbar(text_widget, orient='vertical', command=text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.config(yscrollcommand=scrollbar.set)
        
        text_widget.insert(tk.END, help_text)
        text_widget.config(state=tk.DISABLED)  # Только для чтения
    
    def browse_directory(self, var):
        directory = filedialog.askdirectory()
        if directory:
            var.set(directory)
    
    def browse_file(self, var, filetypes, save=False):
        if save:
            filename = filedialog.asksaveasfilename(filetypes=filetypes)
        else:
            filename = filedialog.askopenfilename(filetypes=filetypes)
        if filename:
            var.set(filename)
    
    def set_ratio(self, value):
        self.ratio.set(value)
        self.ratio_custom.set(str(value))
    
    def update_ratio_from_custom(self):
        try:
            value = float(self.ratio_custom.get())
            self.ratio.set(value)
        except ValueError:
            pass
    
    def set_color(self, color):
        self.color.set(color)
    
    def toggle_smart_scale(self):
        if self.smart_scale.get() and self.white_background.get():
            self.white_background.set(False)
    
    def toggle_white_background(self):
        if self.white_background.get() and self.smart_scale.get():
            self.smart_scale.set(False)
    
    def toggle_visualize(self):
        pass
    
    def add_log(self, message):
        """Добавляет сообщение в лог и прокручивает его в конец"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update()  # Обновляем интерфейс для отображения сообщения
    
    def run_processing(self):
        """Запускает обработку изображений с выбранными параметрами"""
        # Создаем директории, если не существуют
        input_dir = self.input_dir.get()
        output_dir = self.output_dir.get()
        
        try:
            os.makedirs(input_dir, exist_ok=True)
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать директории: {str(e)}")
            return
        
        # Отключаем кнопку на время обработки
        self.run_button.config(state=tk.DISABLED)
        
        # Очищаем лог
        self.log_text.delete(1.0, tk.END)
        
        # Запускаем обработку в отдельном потоке
        threading.Thread(target=self._process, daemon=True).start()
    
    def _process(self):
        """Выполняет обработку в отдельном потоке"""
        try:
            # Подготавливаем параметры
            input_dir = self.input_dir.get()
            output_dir = self.output_dir.get()
            ratio = self.ratio.get()
            color = self.color.get()
            enhance = self.enhance.get()
            smart_scale = self.smart_scale.get()
            white_background = self.white_background.get()
            scale_factor = self.scale_factor.get()
            
            # Проверяем режим визуализации
            if self.visualize.get() and self.visualize_file.get():
                self.add_log(f"Запуск визуализации обнаружения объекта для файла {self.visualize_file.get()}")
                
                output_path = self.visualize_output.get()
                result = visualize_object_detection(self.visualize_file.get(), output_path)
                
                if result:
                    self.add_log(f"Визуализация сохранена в {output_path}")
                    messagebox.showinfo("Успех", f"Визуализация сохранена в {output_path}")
                else:
                    self.add_log("Ошибка при визуализации объекта")
                    messagebox.showerror("Ошибка", "Не удалось обнаружить объект на изображении")
                
                # Включаем кнопку запуска
                self.run_button.config(state=tk.NORMAL)
                return
            
            # Получаем список URL, если выбран соответствующий режим
            urls_data = []
            file_mapping = None
            
            if self.urls_option.get() == "urls" and self.urls_file.get():
                self.add_log(f"Загрузка URL из файла {self.urls_file.get()}")
                try:
                    file_urls = parse_urls_file(self.urls_file.get())
                    urls_data.extend(file_urls)
                except Exception as e:
                    self.add_log(f"Ошибка при чтении файла URL: {str(e)}")
            
            elif self.urls_option.get() == "json" and self.json_file.get():
                self.add_log(f"Преобразование JSON в URLs из файла {self.json_file.get()}")
                urls_file = os.path.join(self.application_path, "urls.txt")
                transform_json_to_urls(self.json_file.get(), urls_file)
                try:
                    file_urls = parse_urls_file(urls_file)
                    urls_data.extend(file_urls)
                except Exception as e:
                    self.add_log(f"Ошибка при чтении преобразованного файла URL: {str(e)}")
            
            # Загружаем изображения, если указаны URL
            if urls_data:
                self.add_log(f"Загрузка {len(urls_data)} изображений...")
                file_mapping = download_images_from_urls(urls_data, input_dir, self.max_workers.get())
                self.add_log(f"Загружено {len(file_mapping)} изображений")
            
            # Выводим информацию о настройках
            self.add_log(f"Обработка изображений с соотношением сторон {ratio}...")
            if enhance:
                self.add_log("Включено улучшение качества изображений")
            if smart_scale:
                self.add_log("Включено умное масштабирование для равномерного распределения объекта")
            if white_background:
                self.add_log(f"Включен специальный режим для белого фона с масштабом {scale_factor}")
            
            # Преобразуем строку цвета в кортеж RGB
            fill_color = parse_color(color)
            
            # Запускаем обработку директории
            process_directory(input_dir, output_dir, ratio, fill_color, file_mapping, enhance, smart_scale, white_background, scale_factor)
            
            # Выводим сообщение об успешном завершении
            self.add_log("Обработка завершена успешно!")
            messagebox.showinfo("Успех", "Обработка изображений завершена успешно!")
            
        except Exception as e:
            self.add_log(f"Ошибка при выполнении обработки: {str(e)}")
            traceback.print_exc()
            messagebox.showerror("Ошибка", f"Произошла ошибка: {str(e)}")
        
        finally:
            # Включаем кнопку запуска
            self.run_button.config(state=tk.NORMAL)

# Точка входа в программу
# Точка входа в программу
if __name__ == "__main__":
    # Создаем корневое окно
    root = tk.Tk()
    
    # Устанавливаем иконку (если доступна)
    try:
        # Определяем путь к иконке
        icon_path = "icon.ico"
        
        # Проверяем путь для скомпилированного EXE
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
            icon_path = os.path.join(base_dir, "icon.ico")
        
        # Если иконка существует, устанавливаем её
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except Exception as e:
        print(f"Ошибка при установке иконки: {e}")
    
    # Создаем экземпляр приложения
    app = AdjustImagesGUI(root)
    
    # Запускаем главный цикл
    root.mainloop()