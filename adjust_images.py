from PIL import Image
import os
import argparse
import requests
from urllib.parse import urlparse
import concurrent.futures
import time
import re
import cv2
import numpy as np
from io import BytesIO
import warnings
import json

# Игнорируем предупреждения PIL для более чистого вывода
warnings.filterwarnings("ignore", category=UserWarning)

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
        print(f"Преобразование {json_file} в {urls_file}...")
        
        # Проверяем существование входного файла
        if not os.path.exists(json_file):
            print(f"Ошибка: Файл {json_file} не найден")
            return 0
        
        # Загружаем JSON данные
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Проверяем, что данные являются списком
        if not isinstance(data, list):
            print(f"Ошибка: JSON должен содержать список объектов. Получено: {type(data)}")
            return 0
        
        # Создаем директорию для urls_file, если она находится в подпапке
        urls_dir = os.path.dirname(urls_file)
        if urls_dir and not os.path.exists(urls_dir):
            os.makedirs(urls_dir)
        
        # Открываем файл для записи URLs
        with open(urls_file, 'w', encoding='utf-8') as f:
            count = 0
            for item in data:
                # Проверяем наличие необходимых полей
                if 'article' in item and 'selectedImage' in item:
                    article = item['article']
                    image_url = item['selectedImage']
                    
                    # Записываем строку в формате "article,url"
                    f.write(f"{article},{image_url}\n")
                    count += 1
        
        print(f"Трансформация успешно завершена: {count} записей сохранено в {urls_file}")
        return count
    
    except Exception as e:
        print(f"Ошибка при трансформации JSON в URLs: {str(e)}")
        import traceback
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

def adjust_aspect_ratio(image_path, output_path, target_ratio, fill_color=(255, 255, 255), enhance=False):
    """
    Adjust image to target aspect ratio by adding padding with specified color
    without changing or stretching the original image.
    
    Args:
        image_path (str): Path to the input image
        output_path (str): Path to save the processed image
        target_ratio (float): Target aspect ratio (width/height)
        fill_color (tuple): RGB color for padding (default: white)
        enhance (bool): Whether to enhance the image quality
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
            padding_bottom = new_height - orig_height - padding_top
            
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
            padding_right = new_width - orig_width - padding_left
            
            # Создаем новое изображение
            new_img = Image.new('RGB', (new_width, new_height), fill_color)
            # Вставляем оригинальное изображение
            new_img.paste(img, (padding_left, 0))
        
        # Определяем формат для сохранения на основе расширения выходного файла
        _, ext = os.path.splitext(output_path)
        save_format = get_pil_format(ext)
        
        # Создаем директорию для выходного файла, если не существует
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Сохраняем изображение с правильным форматом и параметрами
        if save_format == 'JPEG':
            new_img.save(output_path, format=save_format, quality=95, optimize=True)
        else:
            new_img.save(output_path, format=save_format)
            
        return True
    
    except Exception as e:
        print(f"Ошибка при обработке изображения {image_path}: {str(e)}")
        import traceback
        traceback.print_exc()  # Печатаем полный стек-трейс для отладки
        return False

def process_directory(input_dir="input", output_dir="output", target_ratio=1.0, fill_color=(255, 255, 255), file_mapping=None, enhance=False):
    """
    Process all images in a directory to adjust their aspect ratio
    
    Args:
        input_dir (str): Directory with input images
        output_dir (str): Directory to save processed images
        target_ratio (float): Target aspect ratio (width/height)
        fill_color (tuple): RGB color for padding
        file_mapping (dict): Маппинг {article: путь_к_файлу} для определения выходных имен файлов
        enhance (bool): Whether to enhance the image quality
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
        
        if adjust_aspect_ratio(input_path, output_path, target_ratio, fill_color, enhance):
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

if __name__ == "__main__":
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
    parser.add_argument('--only-json-to-urls', action='store_true', help='Только преобразовать JSON в URLs без обработки изображений')
    
    args = parser.parse_args()
    
    # Преобразуем строку цвета в кортеж RGB
    fill_color = parse_color(args.color)
    
    # Проверяем, нужно ли преобразовать JSON в URLs
    if args.json_file:
        output_urls_file = args.urls_file if args.urls_file else "urls.txt"
        transform_json_to_urls(args.json_file, output_urls_file)
        
        # Если нужно только преобразовать JSON в URLs без обработки, выходим
        if args.only_json_to_urls:
            print("Преобразование JSON в URLs выполнено.")
            exit(0)
        
        # Устанавливаем urls_file для дальнейшей обработки
        args.urls_file = output_urls_file
    
    # Проверяем, нужно ли загрузить изображения по URL
    urls_data = []
    file_mapping = None
    
    if args.urls:
        # Простой список URL без article
        urls_data.extend(args.urls)
    
    if args.urls_file and os.path.exists(args.urls_file):
        try:
            # Парсим файл с URLs в формате "article,url"
            file_urls = parse_urls_file(args.urls_file)
            urls_data.extend(file_urls)
        except Exception as e:
            print(f"Ошибка при чтении файла URL {args.urls_file}: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        if args.urls_file:
            print(f"Предупреждение: Файл {args.urls_file} не найден")
    
    # Загружаем изображения, если указаны URL
    if urls_data:
        print(f"Загрузка {len(urls_data)} изображений...")
        file_mapping = download_images_from_urls(urls_data, args.input, args.max_workers)
    
    # Проверяем, есть ли изображения для обработки
    if (not urls_data and not os.path.exists(args.input)) or (os.path.exists(args.input) and len(os.listdir(args.input)) == 0):
        print("Предупреждение: Нет изображений для обработки.")
        exit(0)
    
    # Обрабатываем директорию с изображениями
    print(f"Обработка изображений с соотношением сторон {args.ratio}...")
    if args.enhance:
        print("Включено улучшение качества изображений")
    
    process_directory(args.input, args.output, args.ratio, fill_color, file_mapping, args.enhance)