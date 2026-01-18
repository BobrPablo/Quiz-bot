import logging
import asyncio
import random
from datetime import datetime
from typing import Dict, List, Optional

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup,
    InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

import sqlite3
import json
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Токен бота
BOT_TOKEN = "8371923111:AAGx69JbSqW-SP74qlhT_0rRP0Ebi6bktzA"

# Инициализация бота и диспетчера с новым синтаксисом
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# База данных
DB_NAME = "quiz_bot.db"


def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            total_quizzes INTEGER DEFAULT 0,
            total_score INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Таблица викторин
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quizzes (
            quiz_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subject TEXT,
            difficulty TEXT,
            num_questions INTEGER,
            questions TEXT,  -- JSON с вопросами
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    # Таблица статистики прохождения
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quiz_results (
            result_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            quiz_id INTEGER,
            score INTEGER,
            total_questions INTEGER,
            correct_answers INTEGER,
            time_spent REAL,  -- время в секундах
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (quiz_id) REFERENCES quizzes (quiz_id)
        )
    ''')

    conn.commit()
    conn.close()


# Банк вопросов по разным предметам
QUESTIONS_BANK = {
    "математика": {
        "легкий": [
            {
                "question": "Сколько будет 2 + 2?",
                "options": ["3", "4", "5", "6"],
                "correct_answer": 1,
                "explanation": "2 + 2 = 4"
            },
            {
                "question": "Чему равно 5 × 6?",
                "options": ["25", "30", "35", "40"],
                "correct_answer": 1,
                "explanation": "5 × 6 = 30"
            },
            {
                "question": "Что больше: 10 или 5?",
                "options": ["10", "5", "Они равны", "Нельзя сравнить"],
                "correct_answer": 0,
                "explanation": "10 больше 5"
            },
            {
                "question": "Сколько градусов в прямом углу?",
                "options": ["45°", "90°", "180°", "360°"],
                "correct_answer": 1,
                "explanation": "Прямой угол равен 90°"
            },
            {
                "question": "Чему равно 100 ÷ 10?",
                "options": ["5", "10", "15", "20"],
                "correct_answer": 1,
                "explanation": "100 ÷ 10 = 10"
            },
            {
                "question": "Чему равен периметр квадрата со стороной 3 см?",
                "options": ["6 см", "9 см", "12 см", "15 см"],
                "correct_answer": 2,
                "explanation": "Периметр квадрата = сторона × 4 = 3 × 4 = 12 см"
            },
            {
                "question": "Сколько будет 7 × 8?",
                "options": ["48", "54", "56", "64"],
                "correct_answer": 2,
                "explanation": "7 × 8 = 56"
            },
            {
                "question": "Какое число делится на 2 без остатка?",
                "options": ["7", "13", "18", "21"],
                "correct_answer": 2,
                "explanation": "18 делится на 2 без остатка (18 ÷ 2 = 9)"
            },
            {
                "question": "Сколько градусов в полном круге?",
                "options": ["90°", "180°", "270°", "360°"],
                "correct_answer": 3,
                "explanation": "Полный круг содержит 360 градусов"
            },
            {
                "question": "Чему равно 25 + 47?",
                "options": ["62", "68", "72", "82"],
                "correct_answer": 2,
                "explanation": "25 + 47 = 72"
            }
        ],
        "средний": [
            {
                "question": "Решите уравнение: x + 5 = 12",
                "options": ["x = 5", "x = 6", "x = 7", "x = 8"],
                "correct_answer": 2,
                "explanation": "x = 12 - 5 = 7"
            },
            {
                "question": "Площадь квадрата со стороной 4 см равна:",
                "options": ["8 см²", "12 см²", "16 см²", "20 см²"],
                "correct_answer": 2,
                "explanation": "Площадь квадрата = сторона² = 4² = 16 см²"
            },
            {
                "question": "Сколько будет 15% от 200?",
                "options": ["15", "30", "45", "60"],
                "correct_answer": 1,
                "explanation": "15% от 200 = 200 × 0.15 = 30"
            },
            {
                "question": "Чему равно (-3) × (-4)?",
                "options": ["-12", "-7", "7", "12"],
                "correct_answer": 3,
                "explanation": "Минус на минус дает плюс: (-3) × (-4) = 12"
            },
            {
                "question": "Упростите: 2a + 3a",
                "options": ["5a", "6a", "5a²", "6a²"],
                "correct_answer": 0,
                "explanation": "2a + 3a = 5a"
            },
            {
                "question": "Решите уравнение: 3x - 7 = 14",
                "options": ["x = 5", "x = 7", "x = 9", "x = 11"],
                "correct_answer": 1,
                "explanation": "3x = 14 + 7 = 21, x = 21 ÷ 3 = 7"
            },
            {
                "question": "Чему равна площадь круга с радиусом 5 см? (π ≈ 3.14)",
                "options": ["15.7 см²", "31.4 см²", "78.5 см²", "157 см²"],
                "correct_answer": 2,
                "explanation": "Площадь круга = π × r² = 3.14 × 25 = 78.5 см²"
            },
            {
                "question": "Упростите выражение: (a + b)²",
                "options": ["a² + b²", "a² + 2ab + b²", "a² - 2ab + b²", "a² + ab + b²"],
                "correct_answer": 1,
                "explanation": "(a + b)² = a² + 2ab + b² (формула квадрата суммы)"
            },
            {
                "question": "Сколько будет 0.25 в процентах?",
                "options": ["2.5%", "25%", "250%", "0.25%"],
                "correct_answer": 1,
                "explanation": "0.25 = 25/100 = 25%"
            },
            {
                "question": "Найдите НОД чисел 24 и 36",
                "options": ["6", "8", "12", "24"],
                "correct_answer": 2,
                "explanation": "НОД(24, 36) = 12 (24=2×2×2×3, 36=2×2×3×3)"
            }
        ],
        "сложный": [
            {
                "question": "Чему равна производная функции f(x) = x²?",
                "options": ["x", "2x", "2", "x³/3"],
                "correct_answer": 1,
                "explanation": "Производная x² равна 2x"
            },
            {
                "question": "Решите уравнение: 2x² - 8 = 0",
                "options": ["x = ±2", "x = ±4", "x = 2", "x = 4"],
                "correct_answer": 0,
                "explanation": "2x² = 8, x² = 4, x = ±2"
            },
            {
                "question": "Чему равен sin(90°)?",
                "options": ["0", "0.5", "1", "√2/2"],
                "correct_answer": 2,
                "explanation": "sin(90°) = 1"
            },
            {
                "question": "Сумма углов треугольника равна:",
                "options": ["90°", "180°", "270°", "360°"],
                "correct_answer": 1,
                "explanation": "Сумма углов треугольника всегда равна 180°"
            },
            {
                "question": "Решите систему: x + y = 10, x - y = 2",
                "options": ["x=6,y=4", "x=5,y=5", "x=8,y=2", "x=7,y=3"],
                "correct_answer": 0,
                "explanation": "Сложив уравнения: 2x = 12, x = 6, тогда y = 4"
            },
            {
                "question": "Чему равна производная функции f(x) = e^x?",
                "options": ["e^x", "ln(x)", "1", "0"],
                "correct_answer": 0,
                "explanation": "Производная e^x равна e^x"
            },
            {
                "question": "Решите уравнение: log₂(x) = 3",
                "options": ["x = 6", "x = 8", "x = 9", "x = 27"],
                "correct_answer": 1,
                "explanation": "log₂(x) = 3 ⇒ x = 2³ = 8"
            },
            {
                "question": "Чему равен предел lim(x→∞) (1 + 1/x)^x?",
                "options": ["0", "1", "e", "∞"],
                "correct_answer": 2,
                "explanation": "Это второй замечательный предел, равный числу e (≈2.718)"
            },
            {
                "question": "Найдите определитель матрицы [[2, 3], [1, 4]]",
                "options": ["5", "6", "7", "8"],
                "correct_answer": 0,
                "explanation": "det = (2×4) - (3×1) = 8 - 3 = 5"
            },
            {
                "question": "Чему равно i², где i - мнимая единица?",
                "options": ["1", "-1", "i", "0"],
                "correct_answer": 1,
                "explanation": "i² = -1 по определению мнимой единицы"
            }
        ]
    },
    "история": {
        "легкий": [
            {
                "question": "В каком году началась Вторая мировая война?",
                "options": ["1914", "1939", "1941", "1945"],
                "correct_answer": 1,
                "explanation": "Вторая мировая война началась 1 сентября 1939 года"
            },
            {
                "question": "Кто был первым президентом США?",
                "options": ["Авраам Линкольн", "Джордж Вашингтон", "Томас Джефферсон", "Барак Обама"],
                "correct_answer": 1,
                "explanation": "Джордж Вашингтон был первым президентом США (1789-1797)"
            },
            {
                "question": "Кем был Юрий Гагарин?",
                "options": ["Космонавт", "Ученый", "Политик", "Военный"],
                "correct_answer": 0,
                "explanation": "Юрий Гагарин - первый человек в космосе (1961 год)"
            },
            {
                "question": "Столица Древней Руси?",
                "options": ["Москва", "Новгород", "Киев", "Санкт-Петербург"],
                "correct_answer": 2,
                "explanation": "Киев был столицей Древней Руси"
            },
            {
                "question": "Кто написал роман 'Война и мир'?",
                "options": ["Достоевский", "Толстой", "Чехов", "Пушкин"],
                "correct_answer": 1,
                "explanation": "'Войну и мир' написал Лев Николаевич Толстой"
            },
            {
                "question": "Кто был первым космонавтом?",
                "options": ["Нил Армстронг", "Юрий Гагарин", "Валентина Терешкова", "Алексей Леонов"],
                "correct_answer": 1,
                "explanation": "Юрий Гагарин - первый человек в космосе (12 апреля 1961)"
            },
            {
                "question": "В каком году закончилась Великая Отечественная война?",
                "options": ["1943", "1944", "1945", "1946"],
                "correct_answer": 2,
                "explanation": "Великая Отечественная война закончилась 9 мая 1945 года"
            },
            {
                "question": "Кто написал 'Евгения Онегина'?",
                "options": ["Лермонтов", "Пушкин", "Гоголь", "Толстой"],
                "correct_answer": 1,
                "explanation": "'Евгения Онегина' написал Александр Сергеевич Пушкин"
            },
            {
                "question": "Какой город был столицей Византийской империи?",
                "options": ["Рим", "Константинополь", "Афины", "Александрия"],
                "correct_answer": 1,
                "explanation": "Столицей Византии был Константинополь (ныне Стамбул)"
            },
            {
                "question": "Кто открыл закон всемирного тяготения?",
                "options": ["Галилей", "Ньютон", "Эйнштейн", "Коперник"],
                "correct_answer": 1,
                "explanation": "Закон всемирного тяготения открыл Исаак Ньютон"
            }
        ],
        "средний": [
            {
                "question": "В каком году произошла Октябрьская революция?",
                "options": ["1905", "1914", "1917", "1922"],
                "correct_answer": 2,
                "explanation": "Октябрьская революция произошла в 1917 году"
            },
            {
                "question": "Кто открыл Америку?",
                "options": ["Васко да Гама", "Христофор Колумб", "Фернан Магеллан", "Джеймс Кук"],
                "correct_answer": 1,
                "explanation": "Америку открыл Христофор Колумб в 1492 году"
            },
            {
                "question": "Когда был подписан Декрет о мире?",
                "options": ["1917", "1918", "1920", "1922"],
                "correct_answer": 0,
                "explanation": "Декрет о мире был подписан в 1917 году"
            },
            {
                "question": "Кто был последним императором России?",
                "options": ["Александр II", "Александр III", "Николай I", "Николай II"],
                "correct_answer": 3,
                "explanation": "Последним императором России был Николай II"
            },
            {
                "question": "В каком году человек впервые высадился на Луну?",
                "options": ["1965", "1969", "1972", "1975"],
                "correct_answer": 1,
                "explanation": "Первая высадка на Луну состоялась в 1969 году"
            },
            {
                "question": "В каком году была битва на Куликовом поле?",
                "options": ["1240", "1380", "1480", "1580"],
                "correct_answer": 1,
                "explanation": "Куликовская битва произошла 8 сентября 1380 года"
            },
            {
                "question": "Кто был первым русским царём?",
                "options": ["Иван III", "Иван IV (Грозный)", "Петр I", "Алексей Михайлович"],
                "correct_answer": 1,
                "explanation": "Первым русским царём был Иван IV Грозный (в 1547 году)"
            },
            {
                "question": "Когда была отменена крепостная зависимость в России?",
                "options": ["1801", "1861", "1905", "1917"],
                "correct_answer": 1,
                "explanation": "Крепостное право отменено 19 февраля 1861 года"
            },
            {
                "question": "Кто возглавил первую русскую кругосветную экспедицию?",
                "options": ["Беринг", "Крузенштерн", "Лазарев", "Беллинсгаузен"],
                "correct_answer": 1,
                "explanation": "Первая русская кругосветная экспедиция (1803-1806) под руководством Крузенштерна"
            },
            {
                "question": "В каком году произошла Бородинская битва?",
                "options": ["1805", "1812", "1825", "1853"],
                "correct_answer": 1,
                "explanation": "Бородинское сражение состоялось 7 сентября 1812 года"
            }
        ],
        "сложный": [
            {
                "question": "Кто был автором 'Капитала'?",
                "options": ["Фридрих Энгельс", "Карл Маркс", "Владимир Ленин", "Макс Вебер"],
                "correct_answer": 1,
                "explanation": "'Капитал' написал Карл Маркс"
            },
            {
                "question": "Когда была принята Конституция РФ?",
                "options": ["1991", "1993", "1995", "2000"],
                "correct_answer": 1,
                "explanation": "Конституция РФ была принята 12 декабря 1993 года"
            },
            {
                "question": "Кто возглавлял СССР в годы Великой Отечественной войны?",
                "options": ["Ленин", "Сталин", "Хрущев", "Брежнев"],
                "correct_answer": 1,
                "explanation": "В годы войны СССР возглавлял Иосиф Сталин"
            },
            {
                "question": "В каком году распался СССР?",
                "options": ["1989", "1990", "1991", "1992"],
                "correct_answer": 2,
                "explanation": "СССР распался в декабре 1991 года"
            },
            {
                "question": "Кто был первым правителем единого русского государства?",
                "options": ["Рюрик", "Олег", "Игорь", "Иван III"],
                "correct_answer": 3,
                "explanation": "Иван III - первый правитель единого русского государства"
            },
            {
                "question": "Кто был автором 'Русской правды'?",
                "options": ["Ярослав Мудрый", "Владимир Мономах", "Иван Грозный", "Петр I"],
                "correct_answer": 0,
                "explanation": "'Русская правда' - свод законов Ярослава Мудрого (XI век)"
            },
            {
                "question": "Когда была принята 'Соборное уложение'?",
                "options": ["1497", "1550", "1649", "1716"],
                "correct_answer": 2,
                "explanation": "'Соборное уложение' принято в 1649 году при Алексее Михайловиче"
            },
            {
                "question": "Кто возглавлял восстание декабристов?",
                "options": ["Пестель и Муравьёв-Апостол", "Радищев", "Пугачёв", "Минин и Пожарский"],
                "correct_answer": 0,
                "explanation": "Восстание декабристов 1825 года возглавляли Павел Пестель и Сергей Муравьёв-Апостол"
            },
            {
                "question": "В каком году началась Столетняя война?",
                "options": ["1066", "1337", "1453", "1492"],
                "correct_answer": 1,
                "explanation": "Столетняя война между Англией и Францией началась в 1337 году"
            },
            {
                "question": "Кто был первым председателем Совнаркома?",
                "options": ["Ленин", "Сталин", "Троцкий", "Калинин"],
                "correct_answer": 0,
                "explanation": "Первым председателем Совета народных комиссаров (Совнаркома) был В.И. Ленин"
            }
        ]
    },
    "программирование": {
        "легкий": [
            {
                "question": "Что такое переменная в программировании?",
                "options": ["Константа", "Именованная ячейка памяти", "Функция", "Цикл"],
                "correct_answer": 1,
                "explanation": "Переменная - именованная ячейка памяти для хранения данных"
            },
            {
                "question": "Какой язык программирования назван в честь комедийного шоу?",
                "options": ["Java", "Python", "C++", "JavaScript"],
                "correct_answer": 1,
                "explanation": "Python назван в честь комедийного шоу 'Летающий цирк Монти Пайтона'"
            },
            {
                "question": "Что выводит команда print('Hello')?",
                "options": ["Привет", "Hello", "error", "Ничего"],
                "correct_answer": 1,
                "explanation": "Команда print('Hello') выводит текст Hello"
            },
            {
                "question": "Что такое HTML?",
                "options": ["Язык программирования", "Язык разметки", "База данных", "Фреймворк"],
                "correct_answer": 1,
                "explanation": "HTML - язык разметки гипертекста"
            },
            {
                "question": "Что такое алгоритм?",
                "options": ["Программа", "Последовательность действий", "База данных", "Язык программирования"],
                "correct_answer": 1,
                "explanation": "Алгоритм - последовательность действий для решения задачи"
            },
            {
                "question": "Что такое Python?",
                "options": ["Животное", "Язык программирования", "Операционная система", "База данных"],
                "correct_answer": 1,
                "explanation": "Python - высокоуровневый язык программирования"
            },
            {
                "question": "Как обозначается комментарий в Python?",
                "options": ["//", "#", "/* */", "--"],
                "correct_answer": 1,
                "explanation": "В Python комментарии начинаются с символа #"
            },
            {
                "question": "Какая функция выводит текст в Python?",
                "options": ["input()", "print()", "output()", "write()"],
                "correct_answer": 1,
                "explanation": "Функция print() используется для вывода текста"
            },
            {
                "question": "Что такое переменная типа integer?",
                "options": ["Строка", "Целое число", "Дробное число", "Логическое значение"],
                "correct_answer": 1,
                "explanation": "Integer (int) - целочисленный тип данных"
            },
            {
                "question": "Как называется повторяющаяся часть кода?",
                "options": ["Условие", "Функция", "Цикл", "Переменная"],
                "correct_answer": 2,
                "explanation": "Цикл используется для повторения блока кода"
            }
        ],
        "средний": [
            {
                "question": "Что такое ООП?",
                "options": ["Операционная система", "Объектно-ориентированное программирование",
                            "Основы программирования", "Онлайн обучение"],
                "correct_answer": 1,
                "explanation": "ООП - объектно-ориентированное программирование"
            },
            {
                "question": "Что такое Git?",
                "options": ["Язык программирования", "Система контроля версий", "База данных", "Фреймворк"],
                "correct_answer": 1,
                "explanation": "Git - система контроля версий"
            },
            {
                "question": "Какой оператор используется для сравнения в Python?",
                "options": ["=", "==", "===", "!="],
                "correct_answer": 1,
                "explanation": "Оператор '==' используется для сравнения в Python"
            },
            {
                "question": "Что такое API?",
                "options": ["Язык программирования", "Интерфейс программирования приложений", "База данных",
                            "Операционная система"],
                "correct_answer": 1,
                "explanation": "API - интерфейс программирования приложений"
            },
            {
                "question": "Что такое цикл for?",
                "options": ["Условный оператор", "Цикл с известным числом повторений", "Бесконечный цикл", "Функция"],
                "correct_answer": 1,
                "explanation": "Цикл for используется когда известно число повторений"
            },
            {
                "question": "Что такое список (list) в Python?",
                "options": ["Неизменяемая коллекция", "Изменяемая упорядоченная коллекция", "Множество уникальных элементов", "Словарь пар ключ-значение"],
                "correct_answer": 1,
                "explanation": "List - изменяемая упорядоченная коллекция элементов"
            },
            {
                "question": "Что такое 'DRY' принцип в программировании?",
                "options": ["Don't Repeat Yourself", "Do Repeat Yourself", "Debug Readily Yourself", "Design Right Yields"],
                "correct_answer": 0,
                "explanation": "DRY = Don't Repeat Yourself (Не повторяйся)"
            },
            {
                "question": "Что такое репозиторий в Git?",
                "options": ["Язык программирования", "Хранилище кода", "Текстовый редактор", "База данных"],
                "correct_answer": 1,
                "explanation": "Репозиторий Git - хранилище для кода и истории изменений"
            },
            {
                "question": "Что такое 'функция высшего порядка'?",
                "options": ["Функция, принимающая другие функции как аргументы", "Функция с большим количеством кода", "Функция, возвращающая число", "Функция без параметров"],
                "correct_answer": 0,
                "explanation": "Функция высшего порядка принимает или возвращает другие функции"
            },
            {
                "question": "Что такое 'итератор' в Python?",
                "options": ["Объект для перебора элементов", "Условие выполнения", "Тип данных", "Математическая операция"],
                "correct_answer": 0,
                "explanation": "Итератор - объект, позволяющий перебирать элементы коллекции"
            }
        ],
        "сложный": [
            {
                "question": "Что такое паттерн Singleton?",
                "options": ["Паттерн создания одного экземпляра класса", "Структурный паттерн", "Поведенческий паттерн",
                            "Архитектурный паттерн"],
                "correct_answer": 0,
                "explanation": "Singleton гарантирует существование только одного экземпляра класса"
            },
            {
                "question": "Что такое Big O notation?",
                "options": ["Стиль программирования", "Обозначение временной сложности алгоритма",
                            "Язык программирования", "Тип данных"],
                "correct_answer": 1,
                "explanation": "Big O обозначает временную сложность алгоритма"
            },
            {
                "question": "Что такое рекурсия?",
                "options": ["Цикл", "Вызов функции самой себя", "Условие", "Переменная"],
                "correct_answer": 1,
                "explanation": "Рекурсия - когда функция вызывает сама себя"
            },
            {
                "question": "Что такое полиморфизм в ООП?",
                "options": ["Наследование", "Способность объектов иметь разные формы", "Инкапсуляция", "Абстракция"],
                "correct_answer": 1,
                "explanation": "Полиморфизм - способность объектов иметь разные формы"
            },
            {
                "question": "Что такое Docker?",
                "options": ["Язык программирования", "Платформа для контейнеризации приложений", "База данных",
                            "Фреймворк"],
                "correct_answer": 1,
                "explanation": "Docker - платформа для контейнеризации приложений"
            },
            {
                "question": "Что такое 'декоратор' в Python?",
                "options": ["Функция, изменяющая поведение другой функции", "Тип комментария", "Специальный оператор", "Модуль для оформления"],
                "correct_answer": 0,
                "explanation": "Декоратор - функция, которая модифицирует поведение другой функции"
            },
            {
                "question": "Что такое 'генератор' в Python?",
                "options": ["Функция с yield вместо return", "Устройство выработки тока", "Тип цикла", "Математическая функция"],
                "correct_answer": 0,
                "explanation": "Генератор - функция с оператором yield, возвращающая итератор"
            },
            {
                "question": "Что такое 'лямбда-функция'?",
                "options": ["Анонимная функция", "Функция для работы с БД", "Главная функция программы", "Функция для математических расчётов"],
                "correct_answer": 0,
                "explanation": "Лямбда-функция - анонимная функция, определяемая в одной строке"
            },
            {
                "question": "Что такое 'мемоизация'?",
                "options": ["Кэширование результатов функций", "Оптимизация памяти", "Сжатие данных", "Шифрование информации"],
                "correct_answer": 0,
                "explanation": "Мемоизация - техника кэширования результатов выполнения функций"
            },
            {
                "question": "Что такое 'SOLID' принципы?",
                "options": ["Принципы объектно-ориентированного программирования", "Принципы базы данных", "Принципы сетевой безопасности", "Принципы UI/UX дизайна"],
                "correct_answer": 0,
                "explanation": "SOLID - набор принципов объектно-ориентированного программирования"
            }

        ]
    },
    "география": {
        "легкий": [
            {
                "question": "Какая самая длинная река в мире?",
                "options": ["Амазонка", "Нил", "Янцзы", "Миссисипи"],
                "correct_answer": 0,
                "explanation": "Амазонка - самая длинная река в мире (около 7000 км)"
            },
            {
                "question": "Какая самая высокая гора в мире?",
                "options": ["Килиманджаро", "Эверест", "Эльбрус", "Монблан"],
                "correct_answer": 1,
                "explanation": "Эверест (Джомолунгма) - высочайшая гора (8848 м)"
            },
            {
                "question": "Столица Франции?",
                "options": ["Лондон", "Берлин", "Париж", "Рим"],
                "correct_answer": 2,
                "explanation": "Париж - столица Франции"
            },
            {
                "question": "Сколько океанов на Земле?",
                "options": ["3", "4", "5", "6"],
                "correct_answer": 2,
                "explanation": "5 океанов: Тихий, Атлантический, Индийский, Южный, Северный Ледовитый"
            },
            {
                "question": "Самая большая страна по площади?",
                "options": ["Канада", "США", "Китай", "Россия"],
                "correct_answer": 3,
                "explanation": "Россия - самая большая страна (≈17 млн км²)"
            }
        ],
        "средний": [
            {
                "question": "Какая пустыня самая большая в мире?",
                "options": ["Гоби", "Сахара", "Каракумы", "Атакама"],
                "correct_answer": 1,
                "explanation": "Сахара - крупнейшая пустыня (≈9 млн км²)"
            },
            {
                "question": "Столица Австралии?",
                "options": ["Сидней", "Мельбурн", "Канберра", "Брисбен"],
                "correct_answer": 2,
                "explanation": "Канберра - столица Австралии"
            },
            {
                "question": "Сколько материков на Земле?",
                "options": ["5", "6", "7", "8"],
                "correct_answer": 1,
                "explanation": "6 материков: Евразия, Африка, Северная Америка, Южная Америка, Австралия, Антарктида"
            },
            {
                "question": "Какое озеро самое глубокое в мире?",
                "options": ["Байкал", "Виктория", "Танганьика", "Каспийское"],
                "correct_answer": 0,
                "explanation": "Байкал - самое глубокое озеро (1642 м)"
            },
            {
                "question": "В какой стране находится Амазонка?",
                "options": ["Африка", "Бразилия", "Индия", "Китай"],
                "correct_answer": 1,
                "explanation": "Река Амазонка протекает в основном по территории Бразилии"
            }
        ],
        "сложный": [
            {
                "question": "Какая страна имеет наибольшее количество часовых поясов?",
                "options": ["США", "Россия", "Китай", "Канада"],
                "correct_answer": 1,
                "explanation": "Россия имеет 11 часовых поясов"
            },
            {
                "question": "Самый большой остров в мире?",
                "options": ["Мадагаскар", "Гренландия", "Новая Гвинея", "Калимантан"],
                "correct_answer": 1,
                "explanation": "Гренландия - крупнейший остров (2.1 млн км²)"
            },
            {
                "question": "Какое государство является анклавом (полностью внутри другой страны)?",
                "options": ["Монако", "Сан-Марино", "Ватикан", "Лихтенштейн"],
                "correct_answer": 1,
                "explanation": "Сан-Марино - анклав внутри Италии"
            },
            {
                "question": "Где находится Мёртвое море?",
                "options": ["Между Израилем и Иорданией", "В Центральной Азии", "В Африке", "В Южной Америке"],
                "correct_answer": 0,
                "explanation": "Мёртвое море находится между Израилем и Иорданией"
            },
            {
                "question": "Какой пролив разделяет Европу и Африку?",
                "options": ["Берингов", "Гибралтарский", "Магелланов", "Дарданеллы"],
                "correct_answer": 1,
                "explanation": "Гибралтарский пролив соединяет Средиземное море с Атлантическим океаном"
            }
        ]
    }
}

# Состояния FSM
class QuizStates(StatesGroup):
    waiting_for_subject = State()
    waiting_for_difficulty = State()
    waiting_for_num_questions = State()
    taking_quiz = State()
    waiting_for_answer = State()


# Класс для управления викториной
class QuizManager:
    def __init__(self):
        self.active_quizzes = {}

    def create_quiz(self, user_id: int, subject: str, difficulty: str, num_questions: int) -> Dict:
        """Создает новую викторину"""
        if subject not in QUESTIONS_BANK:
            raise ValueError(f"Предмет '{subject}' не найден")

        if difficulty not in ["легкий", "средний", "сложный"]:
            raise ValueError(f"Сложность '{difficulty}' не поддерживается")

        available_questions = QUESTIONS_BANK[subject][difficulty]

        if num_questions > len(available_questions):
            num_questions = len(available_questions)

        selected_questions = random.sample(available_questions, num_questions)

        quiz = {
            "user_id": user_id,
            "subject": subject,
            "difficulty": difficulty,
            "num_questions": num_questions,
            "questions": selected_questions,
            "current_question": 0,
            "score": 0,
            "start_time": datetime.now(),
            "user_answers": []
        }

        self.active_quizzes[user_id] = quiz
        return quiz

    def get_current_question(self, user_id: int) -> Optional[Dict]:
        """Получает текущий вопрос"""
        if user_id not in self.active_quizzes:
            return None

        quiz = self.active_quizzes[user_id]
        if quiz["current_question"] >= len(quiz["questions"]):
            return None

        return quiz["questions"][quiz["current_question"]]

    def submit_answer(self, user_id: int, answer_index: int) -> Dict:
        """Принимает ответ и возвращает результат"""
        if user_id not in self.active_quizzes:
            return {"correct": False, "finished": True}

        quiz = self.active_quizzes[user_id]
        current_q = quiz["questions"][quiz["current_question"]]

        is_correct = (answer_index == current_q["correct_answer"])

        quiz["user_answers"].append({
            "question_index": quiz["current_question"],
            "answer_index": answer_index,
            "is_correct": is_correct
        })

        if is_correct:
            quiz["score"] += 1

        result = {
            "correct": is_correct,
            "correct_answer": current_q["correct_answer"],
            "explanation": current_q["explanation"],
            "score": quiz["score"],
            "current": quiz["current_question"] + 1,
            "total": len(quiz["questions"])
        }

        quiz["current_question"] += 1

        if quiz["current_question"] >= len(quiz["questions"]):
            result["finished"] = True
            result["final_score"] = quiz["score"]
            result["time_spent"] = (datetime.now() - quiz["start_time"]).total_seconds()

            # Сохраняем результаты
            self.save_results(user_id, quiz)
            del self.active_quizzes[user_id]
        else:
            result["finished"] = False

        return result

    def save_results(self, user_id: int, quiz: Dict):
        """Сохраняет результаты викторины в БД"""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Сохраняем викторину
        cursor.execute('''
            INSERT INTO quizzes (user_id, subject, difficulty, num_questions, questions)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            user_id,
            quiz["subject"],
            quiz["difficulty"],
            quiz["num_questions"],
            json.dumps(quiz["questions"], ensure_ascii=False)
        ))

        quiz_id = cursor.lastrowid

        # Сохраняем результаты
        cursor.execute('''
            INSERT INTO quiz_results 
            (user_id, quiz_id, score, total_questions, correct_answers, time_spent)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            quiz_id,
            quiz["score"],
            len(quiz["questions"]),
            quiz["score"],
            (datetime.now() - quiz["start_time"]).total_seconds()
        ))

        # Обновляем статистику пользователя
        cursor.execute('''
            UPDATE users 
            SET total_quizzes = total_quizzes + 1, 
                total_score = total_score + ?
            WHERE user_id = ?
        ''', (quiz["score"], user_id))

        conn.commit()
        conn.close()

    def cancel_quiz(self, user_id: int):
        """Отменяет активную викторину"""
        if user_id in self.active_quizzes:
            del self.active_quizzes[user_id]


# Инициализация менеджера викторин
quiz_manager = QuizManager()


def register_user(user_id: int, username: str, full_name: str):
    """Регистрирует пользователя в БД"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, full_name)
        VALUES (?, ?, ?)
    ''', (user_id, username, full_name))

    conn.commit()
    conn.close()


def get_user_stats(user_id: int) -> Dict:
    """Получает статистику пользователя"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT total_quizzes, total_score FROM users WHERE user_id = ?
    ''', (user_id,))

    user_stats = cursor.fetchone()

    cursor.execute('''
        SELECT COUNT(*), AVG(score), MAX(score), MIN(time_spent)
        FROM quiz_results WHERE user_id = ?
    ''', (user_id,))

    quiz_stats = cursor.fetchone()

    cursor.execute('''
        SELECT subject, COUNT(*), AVG(score), MAX(score)
        FROM quiz_results qr
        JOIN quizzes q ON qr.quiz_id = q.quiz_id
        WHERE qr.user_id = ?
        GROUP BY subject
        ORDER BY COUNT(*) DESC
        LIMIT 5
    ''', (user_id,))

    subject_stats = cursor.fetchall()

    conn.close()

    return {
        "user_stats": user_stats or (0, 0),
        "quiz_stats": quiz_stats or (0, 0, 0, 0),
        "subject_stats": subject_stats
    }


def get_global_stats() -> Dict:
    """Получает глобальную статистику"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM quiz_results')
    total_quizzes = cursor.fetchone()[0]

    cursor.execute('SELECT AVG(score) FROM quiz_results')
    avg_score = cursor.fetchone()[0] or 0

    cursor.execute('''
        SELECT username, total_score 
        FROM users 
        ORDER BY total_score DESC 
        LIMIT 10
    ''')
    top_users = cursor.fetchall()

    conn.close()

    return {
        "total_users": total_users,
        "total_quizzes": total_quizzes,
        "avg_score": round(avg_score, 2),
        "top_users": top_users
    }


# Обработчики команд
@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    register_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name
    )

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎯 Создать викторину")],
            [KeyboardButton(text="📊 Моя статистика"), KeyboardButton(text="🏆 Топ игроков")],
            [KeyboardButton(text="❓ Помощь")]
        ],
        resize_keyboard=True
    )

    welcome_text = (
        "👋 <b>Добро пожаловать в бот для создания викторин!</b>\n\n"
        "🎓 <b>Доступные предметы:</b>\n"
        "• Математика\n"
        "• История\n"
        "• География\n"
        "• Программирование\n\n"
        "📈 <b>Уровни сложности:</b>\n"
        "• Легкий\n"
        "• Средний\n"
        "• Сложный\n\n"
        "📊 <b>Статистика:</b> отслеживайте свой прогресс и соревнуйтесь с другими!"
    )

    await message.answer(welcome_text, reply_markup=keyboard)


@router.message(F.text == "🎯 Создать викторину")
async def create_quiz_start(message: Message, state: FSMContext):
    """Начало создания викторины"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📐 Математика", callback_data="subject_математика"),
            InlineKeyboardButton(text="📚 История", callback_data="subject_история")
        ],
        [
            InlineKeyboardButton(text="💻 Программирование", callback_data="subject_программирование")
        ],
        [
            InlineKeyboardButton(text="🌍 География", callback_data="subject_география")
        ]
    ])

    await message.answer(
        "📝 <b>Выберите предметную область:</b>",
        reply_markup=keyboard
    )
    await state.set_state(QuizStates.waiting_for_subject)


@router.message(F.text == "📊 Моя статистика")
async def show_stats(message: Message):
    """Показывает статистику пользователя"""
    stats = get_user_stats(message.from_user.id)
    total_quizzes, total_score = stats["user_stats"]
    count, avg_score, max_score, min_time = stats["quiz_stats"]

    if count == 0:
        await message.answer("📊 <b>У вас еще нет пройденных викторин!</b>")
        return

    text = (
        f"📊 <b>Ваша статистика:</b>\n\n"
        f"🎯 <b>Всего викторин:</b> {total_quizzes}\n"
        f"🏆 <b>Всего очков:</b> {total_score}\n"
        f"📈 <b>Средний балл:</b> {avg_score:.2f}\n"
        f"🌟 <b>Лучший результат:</b> {max_score}\n"
        f"⚡ <b>Самое быстрое прохождение:</b> {min_time:.1f} сек\n\n"
        f"<b>Статистика по предметам:</b>\n"
    )

    for subject, sub_count, sub_avg, sub_max in stats["subject_stats"]:
        text += f"\n📚 <b>{subject}:</b>\n"
        text += f"   • Количество: {sub_count}\n"
        text += f"   • Средний балл: {sub_avg:.2f}\n"
        text += f"   • Лучший результат: {sub_max}\n"

    await message.answer(text)


@router.message(F.text == "🏆 Топ игроков")
async def show_top_players(message: Message):
    """Показывает топ игроков"""
    stats = get_global_stats()

    text = (
        f"🏆 <b>Глобальная статистика:</b>\n\n"
        f"👥 <b>Всего пользователей:</b> {stats['total_users']}\n"
        f"🎯 <b>Всего викторин пройдено:</b> {stats['total_quizzes']}\n"
        f"📊 <b>Средний балл по всем:</b> {stats['avg_score']}\n\n"
        f"<b>Топ-10 игроков:</b>\n"
    )

    for i, (username, score) in enumerate(stats["top_users"], 1):
        display_name = f"@{username}" if username else f"Игрок {i}"
        text += f"\n{i}. {display_name} - {score} очков"

    await message.answer(text)


@router.message(F.text == "❓ Помощь")
async def show_help(message: Message):
    """Показывает справку"""
    help_text = (
        "❓ <b>Справка по боту:</b>\n\n"
        "🎯 <b>Создать викторину</b> - начать создание новой викторины\n"
        "📊 <b>Моя статистика</b> - посмотреть вашу статистику\n"
        "🏆 <b>Топ игроков</b> - посмотреть рейтинг игроков\n\n"
        "📝 <b>Процесс создания викторины:</b>\n"
        "1. Выберите предмет\n"
        "2. Выберите уровень сложности\n"
        "3. Укажите количество вопросов (от 1 до 5)\n"
        "4. Начните прохождение викторины\n\n"
        "✅ <b>Прохождение викторины:</b>\n"
        "• Выбирайте варианты ответов\n"
        "• После каждого ответа увидите объяснение\n"
        "• В конце получите итоговый результат\n\n"
        "📈 <b>Статистика:</b>\n"
        "• Сохраняются все ваши результаты\n"
        "• Можно сравнивать с другими игроками\n"
        "• Отслеживайте прогресс по предметам"
    )

    await message.answer(help_text)


@router.callback_query(F.data.startswith("subject_"))
async def process_subject(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора предмета"""
    subject = callback.data.split("_")[1]

    await state.update_data(subject=subject)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎯 Легкий", callback_data="difficulty_легкий"),
            InlineKeyboardButton(text="📈 Средний", callback_data="difficulty_средний")
        ],
        [
            InlineKeyboardButton(text="🏆 Сложный", callback_data="difficulty_сложный")
        ]
    ])

    await callback.message.edit_text(
        f"📝 <b>Выбран предмет:</b> {subject}\n\n"
        "📊 <b>Выберите уровень сложности:</b>",
        reply_markup=keyboard
    )
    await state.set_state(QuizStates.waiting_for_difficulty)


@router.callback_query(F.data.startswith("difficulty_"))
async def process_difficulty(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора сложности"""
    difficulty = callback.data.split("_")[1]

    await state.update_data(difficulty=difficulty)

    # Получаем предмет из предыдущего сообщения (исправляем проблему с \n)
    subject_line = callback.message.text.split('Выбран предмет: ')[1].split('\n')[0]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1 вопрос", callback_data="num_1"),
            InlineKeyboardButton(text="2 вопроса", callback_data="num_2"),
            InlineKeyboardButton(text="3 вопроса", callback_data="num_3")
        ],
        [
            InlineKeyboardButton(text="4 вопроса", callback_data="num_4"),
            InlineKeyboardButton(text="5 вопросов", callback_data="num_5")
        ]
    ])

    await callback.message.edit_text(
        f"📝 <b>Предмет:</b> {subject_line}\n"
        f"📊 <b>Сложность:</b> {difficulty}\n\n"
        "❓ <b>Выберите количество вопросов:</b>",
        reply_markup=keyboard
    )
    await state.set_state(QuizStates.waiting_for_num_questions)


@router.callback_query(F.data.startswith("num_"))
async def process_num_questions(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора количества вопросов"""
    num_questions = int(callback.data.split("_")[1])

    data = await state.get_data()
    subject = data["subject"]
    difficulty = data["difficulty"]

    try:
        # Создаем викторину
        quiz = quiz_manager.create_quiz(
            callback.from_user.id,
            subject,
            difficulty,
            num_questions
        )

        # Начинаем викторину
        question = quiz_manager.get_current_question(callback.from_user.id)

        if not question:
            await callback.message.answer("❌ Ошибка при создании викторины")
            await state.clear()
            return

        # Создаем клавиатуру с вариантами ответов
        keyboard_buttons = []
        for i, option in enumerate(question["options"]):
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"{chr(65 + i)}) {option}",
                callback_data=f"answer_{i}"
            )])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await callback.message.edit_text(
            f"🎯 <b>Викторина началась!</b>\n\n"
            f"📝 <b>Предмет:</b> {subject}\n"
            f"📊 <b>Сложность:</b> {difficulty}\n"
            f"❓ <b>Количество вопросов:</b> {num_questions}\n\n"
            f"<b>Вопрос 1/{num_questions}:</b>\n"
            f"{question['question']}",
            reply_markup=keyboard
        )

        await state.set_state(QuizStates.waiting_for_answer)

    except ValueError as e:
        await callback.message.answer(f"❌ Ошибка: {str(e)}")
        await state.clear()


@router.callback_query(F.data.startswith("answer_"))
async def process_answer(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа пользователя"""
    answer_index = int(callback.data.split("_")[1])

    # Проверяем ответ
    result = quiz_manager.submit_answer(callback.from_user.id, answer_index)

    # Отправляем результат ответа
    if result["correct"]:
        result_text = "✅ <b>Правильно!</b>"
    else:
        correct_letter = chr(65 + result["correct_answer"])
        result_text = f"❌ <b>Неправильно!</b>\nПравильный ответ: {correct_letter}"

    result_text += f"\n📖 <b>Объяснение:</b> {result['explanation']}\n\n"
    result_text += f"🏆 <b>Текущий счет:</b> {result['score']}/{result['current']}"

    await callback.message.edit_text(result_text)

    if result["finished"]:
        # Викторина завершена
        percentage = (result["final_score"] / result["total"]) * 100

        if percentage >= 80:
            emoji = "🏆"
            message_text = "Отличный результат!"
        elif percentage >= 60:
            emoji = "🎯"
            message_text = "Хороший результат!"
        else:
            emoji = "📚"
            message_text = "Есть над чем поработать!"

        final_text = (
            f"{emoji} <b>Викторина завершена!</b>\n\n"
            f"📊 <b>Результат:</b> {result['final_score']}/{result['total']}\n"
            f"📈 <b>Процент правильных:</b> {percentage:.1f}%\n"
            f"⏱️ <b>Время:</b> {result['time_spent']:.1f} сек\n\n"
            f"<b>{message_text}</b>\n\n"
            f"📊 Посмотреть статистику: /stats"
        )

        await callback.message.answer(final_text)

        # Обновляем клавиатуру
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🎯 Создать викторину")],
                [KeyboardButton(text="📊 Моя статистика"), KeyboardButton(text="🏆 Топ игроков")],
                [KeyboardButton(text="❓ Помощь")]
            ],
            resize_keyboard=True
        )


        await state.clear()
    else:
        # Показываем следующий вопрос
        await asyncio.sleep(1)  # Пауза перед следующим вопросом

        # Получаем следующий вопрос
        question = quiz_manager.get_current_question(callback.from_user.id)

        if not question:
            await callback.message.answer("❌ Ошибка: вопрос не найден")
            await state.clear()
            return

        # Создаем клавиатуру для следующего вопроса
        keyboard_buttons = []
        for i, option in enumerate(question["options"]):
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"{chr(65 + i)}) {option}",
                callback_data=f"answer_{i}"
            )])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        # Получаем информацию о текущей викторине
        if callback.from_user.id in quiz_manager.active_quizzes:
            quiz = quiz_manager.active_quizzes[callback.from_user.id]
            question_num = quiz["current_question"] + 1
            total_questions = quiz["num_questions"]
        else:
            # Если викторина уже завершена (на всякий случай)
            await callback.message.answer("✅ Викторина завершена!")
            await state.clear()
            return

        await callback.message.answer(
            f"<b>Вопрос {question_num}/{total_questions}:</b>\n"
            f"{question['question']}",
            reply_markup=keyboard
        )


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Команда для показа статистики"""
    await show_stats(message)


async def main():
    """Основная функция запуска бота"""
    # Инициализируем базу данных
    init_db()

    logger.info("Бот запущен!")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())