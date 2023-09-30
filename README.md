# instagram-parser
Требования: Python 3.11
# Как запустить?

### Стандратный запуск из командной строки
**1. Загрузите проект**

С помощью команды *git clone* или простой загрузкой zip-файла установите проект к себе на ПК.

**2. Создание .env файла**

Перед запуском необходимо создать *.env* файл в директории *src*. Файл должен иметь строго название - *'.env'*. Файл должен содержать переменные по аналогии с *.env.example*.

**Данный шаг можно пропустить и передать все необходимые настройки в качестве аргументов командной строки на шаге №5.*

**3. Добавление прокси и аккаунтов в базу данных**

Для стабильной работы парсера необходимо использовать прокси в связке с аккаунтами. Добавьте необходимое количество прокси и аккаунтов в базу данных с которой предстоит работа.
На каждую прокси не должно приходиться больше 10 аккаунтов. Суточный лимит запросов с одного аккаунта ~ 150. В скрипте учтены все данные ограничения.

**4. Установка зависимостей**

Перейдите в папку с проектом и с помощью команды *python -m venv venv* создайте виртуальное окружение для проекта.
Установите зависимости с помощью команды: *pip install -r requirements.txt*.

**5. Запуск**

Запутсите скрипт с помощью команды: *python src/main.py*.

**если не создан .env файл, то настройки передаются в качестве аргументов команной строки*:
```
usage: main.py [-h] [-db_host DB_HOST] [-db_port DB_PORT] [-db_user DB_USER] [-db_password DB_PASSWORD] [-ar ACCOUNT_DAILY_USAGE_RATE] [-pc PROCESS_COUNT] [-um UPDATE_PROCESS_DELAY_MAX] [-as ACCOUNT_TOO_MANY_REQUESTS_SLEEP]
options:
  -h, --help            show this help message and exit
  -db_host DB_HOST      db host address (default: None)
  -db_port DB_PORT      db host port (default: None)
  -db_user DB_USER      db host user (default: None)
  -db_password DB_PASSWORD
                        db host password (default: None)
  -ar ACCOUNT_DAILY_USAGE_RATE, --account_daily_usage_rate ACCOUNT_DAILY_USAGE_RATE
                        each account max daily usage rate (default: None)
  -pc PROCESS_COUNT, --process_count PROCESS_COUNT
                        number of parallel process (default: None)
  -um UPDATE_PROCESS_DELAY_MAX, --update_process_delay_max UPDATE_PROCESS_DELAY_MAX
                        max delay (choose randomly [0:value) for update process delay (default: None)
  -as ACCOUNT_TOO_MANY_REQUESTS_SLEEP, --account_too_many_requests_sleep ACCOUNT_TOO_MANY_REQUESTS_SLEEP
                        delay after too many requests error occur (default: None)
```
*Все аргументы имеют значения по умолачнию. Для корректной работы базы данных утсановите свои значения для аргументов: db_host, db_port, db_user, db_password.
Остальные аргументы имеют оптимальные значения по умолчанию, изменять не рекомендуется.*
