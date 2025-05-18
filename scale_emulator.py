"""
Модуль эмулятора весов самообслуживания для приложения обработки изображений.
"""

import os
import tkinter as tk
from tkinter import ttk
import random
from PIL import Image, ImageTk
import time
import threading

class ScaleEmulator:
    def __init__(self, parent_notebook, output_dir="output"):
        """
        Инициализация эмулятора весов
        
        Args:
            parent_notebook: родительский notebook для добавления вкладки
            output_dir: директория с изображениями продуктов
        """
        self.parent_notebook = parent_notebook
        self.output_dir = output_dir
        
        # Создаем вкладку
        self.tab = ttk.Frame(self.parent_notebook)
        self.parent_notebook.add(self.tab, text="Эмулятор весов")
        
        # Текущий вес продукта
        self.current_weight = 0.0
        self.current_product = None
        
        # Создаем элементы интерфейса
        self.setup_ui()
        
        # Загружаем продукты из выходной директории
        self.load_products()
        
        # Запускаем симуляцию весов
        self.start_weight_simulation()
    
    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        # Основной фрейм
        main_frame = ttk.Frame(self.tab, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Верхняя панель с весом и датой/временем
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Стиль для заголовков весов
        style = ttk.Style()
        style.configure("WeightLabel.TLabel", foreground="black", background="#d1e786", 
                         font=('Arial', 14, 'bold'), anchor="center")
        style.configure("Weight.TLabel", foreground="black", background="#d1e786", 
                         font=('Arial', 36, 'bold'), anchor="center")
        
        # Рамка для веса и метки
        weight_frame = ttk.Frame(top_frame, style="WeightLabel.TLabel")
        weight_frame.grid(row=0, column=0, padx=5, sticky=tk.W)
        
        # Метка "Вага, кг:"
        weight_label = ttk.Label(weight_frame, text="Вага, кг:", style="WeightLabel.TLabel")
        weight_label.pack(padx=10, pady=(5, 0), anchor=tk.W)
        
        # Отображение текущего веса
        self.weight_value = ttk.Label(weight_frame, text="0.000", style="Weight.TLabel", width=8)
        self.weight_value.pack(padx=10, pady=(0, 5), anchor=tk.W)
        
        # Отображение категорий товаров
        title_label = ttk.Label(top_frame, text="Категорії товарів", font=('Arial', 24, 'bold'))
        title_label.grid(row=0, column=1, padx=100)
        
        # Отображение даты и времени
        self.datetime_label = ttk.Label(top_frame, text="", font=('Arial', 12))
        self.datetime_label.grid(row=0, column=2, padx=5, sticky=tk.E)
        self.update_datetime()
        
        # Фрейм для категорий товаров (2 ряда по 3 категории)
        products_frame = ttk.Frame(main_frame)
        products_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Создаем сетку для категорий (2 ряда, 3 колонки)
        self.category_frames = []
        self.category_buttons = []
        
        for row in range(2):
            for col in range(3):
                # Рамка для категории
                category_frame = ttk.Frame(products_frame, borderwidth=2, relief=tk.GROOVE)
                category_frame.grid(row=row, column=col, padx=5, pady=5, sticky=tk.NSEW)
                self.category_frames.append(category_frame)
                
                # Добавляем кнопку для выбора категории
                btn = ttk.Button(category_frame, text=f"Категория {row*3+col+1}", 
                                command=lambda idx=row*3+col: self.show_product_list(idx))
                btn.pack(fill=tk.BOTH, expand=True)
                self.category_buttons.append(btn)
        
        # Настраиваем веса строк и столбцов для правильного масштабирования
        for i in range(3):
            products_frame.columnconfigure(i, weight=1)
        for i in range(2):
            products_frame.rowconfigure(i, weight=1)
        
        # Нижняя панель с кнопками навигации
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Кнопки навигации
        home_btn = ttk.Button(bottom_frame, text="Категорії", width=15)
        home_btn.pack(side=tk.LEFT, padx=5)
        
        back_btn = ttk.Button(bottom_frame, text="←", width=10)
        back_btn.pack(side=tk.LEFT, padx=5)
        
        next_btn = ttk.Button(bottom_frame, text="→", width=10)
        next_btn.pack(side=tk.LEFT, padx=5)
        
        search_btn = ttk.Button(bottom_frame, text="Пошук", width=15)
        search_btn.pack(side=tk.RIGHT, padx=5)
        
        # Фрейм для отображения списка продуктов (изначально скрыт)
        self.products_list_frame = ttk.Frame(main_frame)
        
        # Фрейм для отображения деталей продукта (изначально скрыт)
        self.product_detail_frame = ttk.Frame(main_frame)
        
    def update_datetime(self):
        """Обновление даты и времени"""
        now = time.localtime()
        time_str = time.strftime("%H:%M", now)
        date_str = time.strftime("%d.%m.%Y", now)
        self.datetime_label.config(text=f"{time_str}\n{date_str}")
        # Обновляем время каждую минуту
        self.tab.after(60000, self.update_datetime)
    
    def load_products(self):
        """Загрузка продуктов из выходной директории"""
        self.products = []
        
        if not os.path.exists(self.output_dir):
            print(f"Директория {self.output_dir} не существует")
            return
        
        # Получаем список файлов изображений
        image_files = [f for f in os.listdir(self.output_dir) 
                     if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        # Создаем продукты (имя файла - название продукта)
        for img_file in image_files:
            product_name = os.path.splitext(img_file)[0]
            product_path = os.path.join(self.output_dir, img_file)
            
            # Генерируем случайную цену за килограмм
            price_per_kg = round(random.uniform(20, 200), 2)
            
            self.products.append({
                'name': product_name,
                'image_path': product_path,
                'price_per_kg': price_per_kg,
                'category': random.randint(0, 5)  # Случайная категория
            })
        
        # Сортируем продукты по категориям
        self.products_by_category = {}
        for product in self.products:
            category = product['category']
            if category not in self.products_by_category:
                self.products_by_category[category] = []
            self.products_by_category[category].append(product)
        
        # Устанавливаем названия категорий
        category_names = [
            "Овочі та фрукти", "Випічка", "Заморожені продукти",
            "Засолка", "Крупи і макарони", "Морепродукти"
        ]
        
        # Обновляем названия кнопок категорий
        for i, btn in enumerate(self.category_buttons):
            if i < len(category_names):
                btn.config(text=category_names[i])
            
            # Если в категории нет продуктов, делаем кнопку неактивной
            if i not in self.products_by_category:
                btn.config(state=tk.DISABLED)
        
        # Создаем изображения для категорий
        self.load_category_images()
    
    def load_category_images(self):
        """Загрузка изображений для категорий"""
        # Словарь для хранения изображений (защита от сборщика мусора)
        self.category_images = {}
        
        # Для каждой категории выбираем изображение первого продукта
        for category, products in self.products_by_category.items():
            if products:
                # Берем первый продукт категории для изображения
                product = products[0]
                try:
                    # Загружаем и масштабируем изображение
                    img = Image.open(product['image_path'])
                    img = img.resize((150, 150), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    
                    # Сохраняем изображение и обновляем кнопку
                    self.category_images[category] = photo
                    self.category_buttons[category].config(image=photo, compound=tk.TOP)
                except Exception as e:
                    print(f"Ошибка при загрузке изображения {product['image_path']}: {e}")
    
    def show_product_list(self, category_index):
        """Отображение списка продуктов выбранной категории"""
        # Скрываем основной фрейм с категориями
        for frame in self.category_frames:
            frame.grid_remove()
        
        # Очищаем фрейм списка продуктов
        for widget in self.products_list_frame.winfo_children():
            widget.destroy()
        
        # Получаем продукты выбранной категории
        products = self.products_by_category.get(category_index, [])
        
        # Создаем сетку для продуктов (2 ряда, 3 колонки)
        for i, product in enumerate(products[:6]):  # Показываем максимум 6 продуктов
            row, col = divmod(i, 3)
            
            # Создаем фрейм для продукта
            product_frame = ttk.Frame(self.products_list_frame, borderwidth=2, relief=tk.GROOVE)
            product_frame.grid(row=row, column=col, padx=5, pady=5, sticky=tk.NSEW)
            
            try:
                # Загружаем и масштабируем изображение
                img = Image.open(product['image_path'])
                img = img.resize((150, 150), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                
                # Сохраняем изображение
                product['photo'] = photo
                
                # Создаем кнопку с изображением и названием
                btn = ttk.Button(product_frame, text=product['name'], image=photo, compound=tk.TOP,
                                command=lambda p=product: self.select_product(p))
                btn.pack(fill=tk.BOTH, expand=True)
                
                # Отображаем цену за кг
                price_label = ttk.Label(product_frame, 
                                      text=f"{product['price_per_kg']:.2f} грн/кг",
                                      font=('Arial', 10, 'bold'))
                price_label.pack(pady=5)
            except Exception as e:
                print(f"Ошибка при создании кнопки продукта: {e}")
        
        # Настраиваем веса строк и столбцов
        for i in range(3):
            self.products_list_frame.columnconfigure(i, weight=1)
        for i in range(2):
            self.products_list_frame.rowconfigure(i, weight=1)
        
        # Отображаем фрейм списка продуктов
        self.products_list_frame.pack(fill=tk.BOTH, expand=True, pady=10)
    
    def select_product(self, product):
        """Выбор продукта для взвешивания"""
        self.current_product = product
        
        # Скрываем список продуктов
        self.products_list_frame.pack_forget()
        
        # Очищаем фрейм деталей продукта
        for widget in self.product_detail_frame.winfo_children():
            widget.destroy()
        
        # Создаем интерфейс деталей продукта
        # Верхняя часть с изображением и информацией
        top_detail = ttk.Frame(self.product_detail_frame)
        top_detail.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Изображение продукта
        img_label = ttk.Label(top_detail, image=product['photo'])
        img_label.grid(row=0, column=0, rowspan=3, padx=20, pady=10)
        
        # Название продукта
        name_label = ttk.Label(top_detail, text=product['name'], 
                             font=('Arial', 16, 'bold'))
        name_label.grid(row=0, column=1, padx=10, pady=5, sticky=tk.W)
        
        # Цена за кг
        price_label = ttk.Label(top_detail, 
                              text=f"Цена: {product['price_per_kg']:.2f} грн/кг",
                              font=('Arial', 14))
        price_label.grid(row=1, column=1, padx=10, pady=5, sticky=tk.W)
        
        # Рассчитываем стоимость
        cost = self.current_weight * product['price_per_kg']
        
        # Общая стоимость
        self.cost_label = ttk.Label(top_detail, 
                                  text=f"Стоимость: {cost:.2f} грн",
                                  font=('Arial', 14, 'bold'))
        self.cost_label.grid(row=2, column=1, padx=10, pady=5, sticky=tk.W)
        
        # Кнопка "Добавить в корзину"
        add_btn = ttk.Button(self.product_detail_frame, text="Добавить в корзину", 
                           command=self.add_to_cart)
        add_btn.pack(pady=10)
        
        # Кнопка "Назад"
        back_btn = ttk.Button(self.product_detail_frame, text="Назад", 
                            command=self.back_to_list)
        back_btn.pack(pady=5)
        
        # Отображаем фрейм деталей продукта
        self.product_detail_frame.pack(fill=tk.BOTH, expand=True)
    
    def back_to_list(self):
        """Возврат к списку продуктов"""
        self.product_detail_frame.pack_forget()
        self.products_list_frame.pack(fill=tk.BOTH, expand=True, pady=10)
    
    def add_to_cart(self):
        """Добавление продукта в корзину"""
        if self.current_product and self.current_weight > 0:
            cost = self.current_weight * self.current_product['price_per_kg']
            messagebox = tk.messagebox
            messagebox.showinfo("Добавлено", 
                              f"Добавлено в корзину: {self.current_product['name']}\n"
                              f"Вес: {self.current_weight:.3f} кг\n"
                              f"Стоимость: {cost:.2f} грн")
            
            # Сбрасываем вес после добавления
            self.current_weight = 0
            self.weight_value.config(text=f"{self.current_weight:.3f}")
            
            # Обновляем стоимость
            if hasattr(self, 'cost_label'):
                cost = self.current_weight * self.current_product['price_per_kg']
                self.cost_label.config(text=f"Стоимость: {cost:.2f} грн")
    
    def start_weight_simulation(self):
        """Запуск симуляции весов в отдельном потоке"""
        def weight_simulation():
            while True:
                # Если выбран продукт, симулируем изменение веса
                if self.current_product:
                    # Случайное изменение веса
                    weight_change = random.uniform(-0.01, 0.02)
                    self.current_weight = max(0, self.current_weight + weight_change)
                    
                    # Обновляем отображение веса
                    self.weight_value.config(text=f"{self.current_weight:.3f}")
                    
                    # Обновляем стоимость, если метка существует
                    if hasattr(self, 'cost_label'):
                        cost = self.current_weight * self.current_product['price_per_kg']
                        self.cost_label.config(text=f"Стоимость: {cost:.2f} грн")
                
                time.sleep(0.5)
        
        # Запускаем симуляцию в отдельном потоке
        thread = threading.Thread(target=weight_simulation, daemon=True)
        thread.start()