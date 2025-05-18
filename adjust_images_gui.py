import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import importlib.util

class AdjustImagesGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Adjust Images Tool")
        self.root.geometry("800x700")
        self.root.minsize(800, 700)
        
        # Определяем путь к директории исполняемого файла
        if getattr(sys, 'frozen', False):
            self.application_path = os.path.dirname(sys.executable)
        else:
            self.application_path = os.path.dirname(os.path.abspath(__file__))
        
        # Проверяем наличие adjust_images.py
        self.script_path = os.path.join(self.application_path, "adjust_images.py")
        if not os.path.exists(self.script_path):
            messagebox.showerror("Ошибка", f"Файл adjust_images.py не найден в директории {self.application_path}")
            root.destroy()
            return
        
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
        header = ttk.Label(main_frame, text="Настройте параметры обработки изображений", style="Header.TLabel")
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
        help_tab = ttk.Frame(notebook, padding=10)
        notebook.add(help_tab, text="Примеры и справка")
        
        # Фрейм для вывода команды и логов
        output_frame = ttk.LabelFrame(main_frame, text="Командная строка и лог", padding=10)
        output_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Текстовое поле для отображения команды
        self.command_text = tk.Text(output_frame, height=2, width=80, wrap=tk.WORD)
        self.command_text.pack(fill=tk.X, pady=(0, 10))
        
        # Текстовое поле для вывода логов
        self.log_text = tk.Text(output_frame, height=5, width=80, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Добавляем скролл для логов
        log_scrollbar = ttk.Scrollbar(self.log_text, orient='vertical', command=self.log_text.yview)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=log_scrollbar.set)
        
        # Кнопки внизу
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.run_button = ttk.Button(button_frame, text="Запустить обработку", command=self.run_command)
        self.run_button.pack(side=tk.RIGHT, padx=5)
        
        self.update_cmd_button = ttk.Button(button_frame, text="Обновить команду", command=self.update_command)
        self.update_cmd_button.pack(side=tk.RIGHT, padx=5)
        
        # Инициализируем переменные
        self.init_variables()
        
        # Заполняем вкладки
        self.setup_basic_tab(basic_tab)
        self.setup_loading_tab(loading_tab)
        self.setup_processing_tab(processing_tab)
        self.setup_help_tab(help_tab)
        
        # Обновляем командную строку
        self.update_command()

    def init_variables(self):
            # Основные настройки
            self.input_dir = tk.StringVar(value=os.path.join(self.application_path, "input"))
            self.output_dir = tk.StringVar(value=os.path.join(self.application_path, "output"))
            self.ratio = tk.DoubleVar(value=1.0)
            self.ratio_custom = tk.StringVar(value="1.0")
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
            self.visualize = tk.BooleanVar(value=False)
            self.visualize_file = tk.StringVar(value="")
            self.visualize_output = tk.StringVar(value=os.path.join(self.application_path, "object_detected.jpg"))
            
            # Режим запуска
            self.python_exe = tk.StringVar(value=sys.executable)
            self.direct_import = tk.BooleanVar(value=True)
        
    def setup_basic_tab(self, parent):
        # Директории ввода и вывода
        dir_frame = ttk.LabelFrame(parent, text="Директории", padding=10)
        dir_frame.pack(fill=tk.X, pady=5)
        
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
                       command=lambda: self.set_ratio(1.0)).grid(row=0, column=0, sticky=tk.W, pady=2)
        
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
        
        ttk.Label(ratio_frame, text="Примеры: 1.0 (1:1), 1.78 (16:9), 0.75 (3:4)").grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=5)
        
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
        
        # Режим запуска
        run_frame = ttk.LabelFrame(parent, text="Режим запуска (для продвинутых пользователей)", padding=10)
        run_frame.pack(fill=tk.X, pady=5)
        
        ttk.Checkbutton(run_frame, text="Использовать прямой импорт (рекомендуется для EXE-файла)", 
                        variable=self.direct_import).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5)

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
            self.update_command()

    def browse_file(self, var, filetypes, save=False):
        if save:
            filename = filedialog.asksaveasfilename(filetypes=filetypes)
        else:
            filename = filedialog.askopenfilename(filetypes=filetypes)
        if filename:
            var.set(filename)
            self.update_command()

    def set_ratio(self, value):
        self.ratio.set(value)
        self.ratio_custom.set(str(value))
        self.update_command()

    def update_ratio_from_custom(self):
        try:
            value = float(self.ratio_custom.get())
            self.ratio.set(value)
            self.update_command()
        except ValueError:
            pass

    def set_color(self, color):
        self.color.set(color)
        self.update_command()

    def toggle_smart_scale(self):
        if self.smart_scale.get() and self.white_background.get():
            self.white_background.set(False)
        self.update_command()

    def toggle_white_background(self):
        if self.white_background.get() and self.smart_scale.get():
            self.smart_scale.set(False)
        self.update_command()

    def toggle_visualize(self):
        self.update_command()

    def update_command(self):
        if self.direct_import:
            # Для режима прямого импорта команда генерируется для справки,
            # но будет использоваться другой механизм запуска
            cmd = ["python", self.script_path]
        else:
            # Для режима с Python используем путь к Python интерпретатору
            cmd = [self.python_exe, self.script_path]
        
        # Если выбрана визуализация
        if self.visualize.get() and self.visualize_file.get():
            cmd.append(f"--visualize-object \"{self.visualize_file.get()}\"")
            if self.visualize_output.get():
                cmd.append(f"--visualize-output \"{self.visualize_output.get()}\"")
            
            self.command_text.delete(1.0, tk.END)
            self.command_text.insert(tk.END, " ".join(cmd))
            return
        
        # Основные параметры
        cmd.append(f"--ratio {self.ratio.get()}")
        cmd.append(f"--color {self.color.get()}")
        cmd.append(f"--input \"{self.input_dir.get()}\"")
        cmd.append(f"--output \"{self.output_dir.get()}\"")
        
        # Параметры загрузки
        if self.urls_option.get() == "urls" and self.urls_file.get():
            cmd.append(f"--urls-file \"{self.urls_file.get()}\"")
            cmd.append(f"--max-workers {self.max_workers.get()}")
        elif self.urls_option.get() == "json" and self.json_file.get():
            cmd.append(f"--json-file \"{self.json_file.get()}\"")
            cmd.append("--json-to-urls")
            cmd.append(f"--max-workers {self.max_workers.get()}")
        
        # Параметры обработки
        if self.enhance.get():
            cmd.append("--enhance")
        
        if self.smart_scale.get():
            cmd.append("--smart-scale")
        
        if self.white_background.get():
            cmd.append("--white-background")
            cmd.append(f"--scale-factor {self.scale_factor.get()}")
        
        self.command_text.delete(1.0, tk.END)
        self.command_text.insert(tk.END, " ".join(cmd))
    
    def run_command(self):
        # Создаем папки ввода и вывода, если они не существуют
        input_dir = self.input_dir.get()
        output_dir = self.output_dir.get()
        
        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        
        # Очищаем лог
        self.log_text.delete(1.0, tk.END)
        
        # Получаем команду
        command = self.command_text.get(1.0, tk.END).strip()
        self.log_text.insert(tk.END, f"Команда: {command}\n\n")
        
        # Отключаем кнопку запуска во время обработки
        self.run_button.config(state=tk.DISABLED)
        
        # Запускаем обработку в отдельном потоке
        if self.direct_import:
            threading.Thread(target=self.run_direct_import, daemon=True).start()
        else:
            threading.Thread(target=self.run_subprocess, args=(command,), daemon=True).start()
    
    def run_subprocess(self, command):
        try:
            # Запускаем процесс через подпроцесс
            process = subprocess.Popen(
                command, 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            # Читаем вывод
            for line in process.stdout:
                # Добавляем в лог
                self.log_text.insert(tk.END, line)
                self.log_text.see(tk.END)
                self.root.update()
            
            # Ждем завершения
            process.wait()
            
            # Показываем результат
            if process.returncode == 0:
                self.log_text.insert(tk.END, "\nКоманда успешно выполнена!\n")
                messagebox.showinfo("Успех", "Обработка изображений завершена успешно!")
            else:
                self.log_text.insert(tk.END, f"\nКоманда завершилась с ошибкой (код {process.returncode})!\n")
                messagebox.showerror("Ошибка", f"Обработка изображений завершилась с ошибкой (код {process.returncode})!")
        
        except Exception as e:
            self.log_text.insert(tk.END, f"\nОшибка при запуске команды: {str(e)}\n")
            messagebox.showerror("Ошибка", f"Ошибка при запуске команды: {str(e)}")
        
        finally:
            # Включаем кнопку запуска
            self.run_button.config(state=tk.NORMAL)
    
    def run_direct_import(self):
        try:
            # Импортируем скрипт adjust_images.py
            spec = importlib.util.spec_from_file_location("adjust_images", self.script_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Создаем параметры командной строки
            import sys
            import shlex
            
            # Получаем команду из текстового поля
            command = self.command_text.get(1.0, tk.END).strip()
            
            # Удаляем "python adjust_images.py" из начала команды
            if command.startswith("python"):
                command = command.split(' ', 2)[2]
            
            # Сохраняем оригинальные аргументы
            original_argv = sys.argv.copy()
            
            # Устанавливаем новые аргументы
            sys.argv = ["adjust_images.py"] + shlex.split(command)
            
            # Создаем захват вывода
            from io import StringIO
            import contextlib
            
            f = StringIO()
            with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
                try:
                    module.main()  # Вызываем функцию main из импортированного модуля
                    success = True
                except Exception as e:
                    self.log_text.insert(tk.END, f"Ошибка при выполнении скрипта: {str(e)}\n")
                    import traceback
                    self.log_text.insert(tk.END, traceback.format_exc())
                    success = False
            
            # Восстанавливаем оригинальные аргументы
            sys.argv = original_argv
            
            # Вывод
            output = f.getvalue()
            self.log_text.insert(tk.END, output)
            self.log_text.see(tk.END)
            
            # Показываем результат
            if success:
                self.log_text.insert(tk.END, "\nОбработка успешно выполнена!\n")
                messagebox.showinfo("Успех", "Обработка изображений завершена успешно!")
            else:
                self.log_text.insert(tk.END, "\nОбработка завершилась с ошибкой!\n")
                messagebox.showerror("Ошибка", "Обработка изображений завершилась с ошибкой!")
            
        except Exception as e:
            self.log_text.insert(tk.END, f"\nОшибка при запуске скрипта: {str(e)}\n")
            import traceback
            self.log_text.insert(tk.END, traceback.format_exc())
            messagebox.showerror("Ошибка", f"Ошибка при запуске скрипта: {str(e)}")
        
        finally:
            # Включаем кнопку запуска
            self.run_button.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    app = AdjustImagesGUI(root)
    root.mainloop()