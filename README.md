# Обработчик Метеорологических Зондирований

Этот инструмент обрабатывает данные метеорологических зондирований из базы данных Университета Вайоминга. Он извлекает температурные инверсии и сохраняет их в файлах Excel для дальнейшего анализа.


## Особенности

- Загрузка данных зондирования из базы данных Университета Вайоминга
- Работа с локальными файлами для предотвращения проблем с соединением
- Обнаружение температурных инверсий на высоте до 1000 метров
- Создание отдельных файлов Excel для каждого зондирования
- Формирование общего файла анализа с несколькими листами
- Интерфейс для лёгкого использования

## Установка

1. Клонировать репозиторий:
   ```bash
   git clone https://github.com/meteoFurletov/weather-sounding-tool.git
   cd weather-sounding-tool
   ```

2. Установить зависимости:
   ```bash
   pip install -r requirements.txt
   ```

3. Для графического интерфейса (опционально):
   ```bash
   # Для Ubuntu/Debian:
   sudo apt-get install python3-tk
   pip install tkcalendar
   ```

## Использование

### Способ 1: Через Jupyter Notebook (рекомендуется для начинающих)

Самый простой способ использования инструмента - через интерактивный Jupyter Notebook. Вы можете запустить его локально или в облаке через Google Colab.

#### Онлайн в Google Colab (без установки)

[![Открыть в Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/meteoFurletov/weather-sounding-tool/blob/main/demo_ru.ipynb)

1. Нажмите на кнопку "Открыть в Colab" выше
2. Запустите все ячейки по порядку
3. Настройте параметры (год, месяц, идентификатор станции)
4. Загрузите результаты на свой компьютер

#### Локально через Jupyter

1. Установите Jupyter, если его ещё нет:
   ```bash
   pip install jupyter
   ```

2. Запустите Jupyter в папке проекта:
   ```bash
   jupyter notebook
   ```

3. Откройте файл `demo.ipynb` и следуйте инструкциям

### Способ 2: Простой текстовый интерфейс

Для пользователей без GUI или Jupyter:

### Способ 4: Без установки - Используйте онлайн демо

Для пользователей, которые не хотят ничего устанавливать, вы можете использовать онлайн демо:

[![Открыть в Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/meteoFurletov/weather-sounding-tool/blob/main/demo.ipynb)

Это позволяет вам:
1. Запустить инструмент прямо в вашем браузере
2. Обработать данные из базы данных Вайоминга
3. Загрузить результаты на свой компьютер

Установка не требуется!

## Выходные файлы

## Вклад

Вклады приветствуются! Пожалуйста, не стесняйтесь отправлять Pull Request.

## Лицензия

Этот проект лицензирован по лицензии MIT - см. файл [LICENSE](LICENSE) для подробностей.

