"""
Скрипт для создания исполняемого EXE-файла из adjust_images_standalone.py с помощью PyInstaller.
"""

import os
import sys
import shutil
import subprocess

def build_exe():
    print("Начинаем создание EXE-файла...")
    
    # Проверяем наличие PyInstaller
    try:
        import PyInstaller
        print("PyInstaller уже установлен.")
    except ImportError:
        print("Устанавливаем PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Проверяем наличие необходимых файлов
    required_files = ["adjust_images_standalone.py"]
    for file in required_files:
        if not os.path.exists(file):
            print(f"Ошибка: Файл {file} не найден в текущей директории.")
            return False
    
    # Создаем директорию для сборки, если она не существует
    if not os.path.exists("build"):
        os.makedirs("build")
    
    # Создаем директорию для дистрибутива, если она не существует
    if not os.path.exists("dist"):
        os.makedirs("dist")
    
    # Подготавливаем команду для PyInstaller
    cmd = [
        sys.executable, 
        "-m", 
        "PyInstaller",
        "--noconfirm",
        "--onefile",  # Создаем один исполняемый файл вместо директории
        "--windowed",
        "--name", "TS-5 Images",
        "--add-data", f"scale_emulator.py{os.pathsep}.",  # Добавляем модуль эмулятора весов
        "--icon=icon.ico",  # Добавляем иконку
        "adjust_images_standalone.py"
    ]
    
    print("Запускаем PyInstaller...")
    print(" ".join(cmd))
    
    # Запускаем PyInstaller
    subprocess.check_call(cmd)
    
    print("\n" + "-"*50)
    print(f"Сборка завершена успешно! EXE-файл находится в директории dist/AdjustImages.exe")
    print("Вы можете запустить программу, открыв файл AdjustImages.exe")
    print("-"*50)
    
    return True

if __name__ == "__main__":
    build_exe()