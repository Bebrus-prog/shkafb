import sqlite3
import hashlib
import time
import datetime
from . import hook_config

# загрузка конфигурации программы
db = sqlite3.connect(hook_config.DATABASE_NAME)
cursor = db.cursor()

def str_xor(str1: str, str2: str):
    # вспомогательная функция для применения xor для строк
    return bool(str1) != bool(str2)

def get_date():
    # вспомогательная функция для получения сегодняшней даты
    return datetime.datetime.today().strftime('%d/%m/%Y')

def login_check_format(login: str):
    # вспомогательная функция для проверки формата юзернейма
    alph = "qwertyuiopasdfghjklzxcvbnm0123456789-_"
    if len(login) > 32 or len(login) == 0:
        return {"error": "length"}
    for el in login:
        if el not in alph:
            return {"error": "symbol"}
    return {"error": None}

def product_name_check_format(name: str):
    # вспомогательная функция для проверки формата наименования продукта
    alph = "qwertyuiopasdfghjklzxcvbnm йцукенгшщзхъфывапролджэячсмитьбю1234567890-_"
    if len(name) > 64:
        return {"error": "length"}
    for el in name:
        if el not in alph:
            return {"error": "symbol"}
    return {"error": None}


def hash_password(password: str):
    # вспомогательная функция для хэширования данных
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(stored_password: str, provided_password: str):
    # вспомогательная функция для проверки пароля
    return stored_password == provided_password

def fetch_login(login: str, password: str, gen_session_key: str, ip_addr: str):
    # выдача информации об авторизации пользователя
    login = login.lower().strip()

    # проверка формата
    login_error = login_check_format(login)["error"]
    if login_error:
        # возврат error = length, если больше 32 символов; возврат error = symbol, если нет в алфавите
        return {"error": login_error}
    else:
        cursor.execute("SELECT pass_hash FROM users WHERE username = ?", (login,))
        db_pass_hash = cursor.fetchone()
        if db_pass_hash == None:
            # возврат error = "no_result", если не найден в базе
            return {"error": "no_result"}
        else:
            db_pass_hash = db_pass_hash[0]
            chk_pass_bool = check_password(db_pass_hash, hash_password(password))
            if not chk_pass_bool:
                # возвращает error = "wrong_password", если пароли не совпадают
                return {"error": "wrong_password"}
            else:
                cursor.execute("SELECT id FROM users WHERE username = ?", (login,))
                userid = cursor.fetchone()[0]
                # проверка на открытые сессии и их закрытие
                cursor.execute("SELECT id FROM sessions WHERE userid = ? AND is_alive = 1", (userid,))
                started_session = cursor.fetchone()
                if started_session:
                    started_session = started_session[0]
                    cursor.execute("UPDATE sessions SET is_alive = 0 WHERE id = ?", (started_session,))
                    db.commit()
                
                # сбор данных и внесение изменений
                lifetime = int(time.time()) + 604800
                cursor.execute("SELECT permission FROM users WHERE username = ?", (login,))
                perm = cursor.fetchone()[0]
                cursor.execute("INSERT INTO sessions (userid, session_key, ip_addr, lifetime, is_alive) VALUES (?, ?, ?, ?, 1)", (userid, gen_session_key, ip_addr, lifetime))
                db.commit()
                return {"error": None, "permission": perm}

def session_check(session_key: str, ip_addr: str, admin_needed: bool = False):
    # admin_needed по умолчанию False
    # проверка сессии
    cursor.execute("SELECT * FROM sessions WHERE session_key = ? AND lifetime > ? AND ip_addr = ? AND is_alive = 1", (session_key, int(time.time()), ip_addr))
    seskey_session = cursor.fetchone()
    if not seskey_session:
        # возвращает error = no_result, если нет в базе
        return {"error": "no_result"}
    else:
        uid = seskey_session[1]
        cursor.execute("SELECT permission FROM users WHERE id = ?", (uid,))
        db_perm = cursor.fetchone()[0]

        # проверка прав доступа
        if db_perm == "user" and admin_needed:
            # возвращает error = no_permission, если нет доступа
            return {"error": "no_permission"}
        elif db_perm == "admin" and not admin_needed:
            # все так же наоборот, админ не может получить доступ к пользовательской панели
            return {"error": "no_permission"}
        else:
            # доступ получен
            return {"error": None}

def fetch_inventory(res_order: bool = False, sort_by: str = "alph", search_word: str = '', search_in: str = ''):
    search_word = search_word.lower().strip()

    # get-query: sort_by = sort, search_in = qt, search_word = q
    # sort_by может быть только alph / amount / stat
    # search_in может быть только name / user
    # 0 < длина search_word < 64 и содержит только буквы и цифры

    # проверка полученных аргументов

    if str_xor(search_word, search_in):
        # error = not_enough_arguments, если аргументы переданы не до конца
        return {"error": "not_enough_arguments"}
    elif (search_word and search_in) and sort_by not in ("alph", "amount", "stat"):
        # error = wrong_sorting_type, если введён неправильный тип сортировки
        return {"error": "wrong_sorting_type"}
    elif (search_word and search_in) and search_in not in ("name", "user"):
        # error = wrong_searching_type, если введён неправильный тип поиска
        return {"error": "wrong_searching_type"}
    elif search_word and search_in == "name" and product_name_check_format(search_word)["error"]:
        # возврат ошибки при проверке имени продукта (error = length / symbol)
        return {"error": product_name_check_format(search_word)["error"]}
    elif search_word and search_in == "user" and login_check_format(search_word)["error"]:
        # возврат ошибки при проверке имени пользователя (error = length / symbol)
        return {"error": login_check_format(search_word)["error"]}
    else:
        # проверка и вывод элементов

        # подстройка аргументов под таблицу
        if sort_by == "alph": 
            order_by = "name"
        elif sort_by == "amount":
            order_by = "amount"
        elif sort_by == "stat":
            order_by = "status"

        if not res_order:
            asc_desc_word = "ASC"
        else:
            asc_desc_word = "DESC"

        if search_word:
            # если есть поисковое слово
            if search_in == "name":
                # fetch_results при поиске по имени содержит следующие колонки:
                # ID предмета, имя, кол-во в инвентаре, статус (0-2)
                sql_arg_searchword = '%' + search_word + '%'
                cursor.execute(f"""SELECT * FROM inventory 
                               WHERE name LIKE ? 
                               ORDER BY {order_by} {asc_desc_word}""", (sql_arg_searchword,))
                fetch_results = cursor.fetchall()

            elif search_in == "user":
                # подстройка аргументов под таблицу
                if order_by == "name":
                    order_by = "inventory.name"
                elif order_by == "amount":
                    order_by = "belongings.amount"
                elif order_by == "status":
                    order_by = "inventory.status"

                cursor.execute("SELECT id FROM users WHERE username = ?", (search_word,))
                uid = cursor.fetchone()
                if not uid:
                    # возвращает error = "no_items", если пользователь не найден
                    return {"error": "no_items"}
                else:
                    # fetch_results при поиске по имени содержит следующие колонки:
                    # ID предмета, имя, статус, кол-во предметов в распоряжении, время создания заказа, комментарий к заказу
                    uid = uid[0]
                    cursor.execute(f'''SELECT inventory.id, inventory.name, inventory.status, belongings.amount, belongings.time, belongings.description
                                FROM inventory
                                INNER JOIN belongings ON belongings.obj_id = inventory.id
                                WHERE belongings.userid = ?
                                   ORDER BY {order_by} {asc_desc_word}''', (uid,))
                    
                    fetch_results = cursor.fetchall()
                    
        else:
            # если нет поискового слова
            # fetch_results при поиске по имени содержит следующие колонки:
            # ID предмета, имя, кол-во в инвентаре, статус (0-2)

            if not res_order:
                asc_desc_word = "ASC"
            else:
                asc_desc_word = "DESC"

            cursor.execute(f"SELECT * FROM inventory ORDER BY {order_by} {asc_desc_word}")
            fetch_results = cursor.fetchall()

    if not fetch_results:
        # возвращает error = "no_items", если нет элементов по выбранным критериям
        return {"error": "no_items"}
    else:
        # элементы найдены, error = None, передаётся список кортежей с найденными данными
        return {"error": None, "results": fetch_results}


def pick_inventory_element_by_id(eid: int):
    # дополнительный параметр поиска, вывод информации об определенном объекте с определенным ID предмета

    cursor.execute("SELECT * FROM inventory WHERE id = ?", (eid,))
    data = cursor.fetchone()
    if not data:
        # возвращает error = no_result, если нет в базе
        return {"error": "no_result"}
    else:
        # result содержит следующие колонки:
        # ID предмета, имя, кол-во в инвентаре, статус (0-2)
        return {"error": None, "result": data}

def remove_from_inventory(eid: int, session_key: str, ip_addr: str):
    # удаление элемента из инвентаря и запись о действии в лог

    cursor.execute("SELECT userid FROM sessions WHERE session_key = ? AND lifetime > ? AND ip_addr = ? AND is_alive = 1", (session_key, int(time.time()), ip_addr))
    uid = cursor.fetchone()
    cursor.execute("SELECT * FROM inventory WHERE id = ?", (eid,))
    rem_obj_data = cursor.fetchone()
    if not uid:
        # error = session_error, если сессия истекла
        return {"error": "session_error"}
    elif not rem_obj_data:
        # error = no_result, если сессия истекла
        return {"error": "no_result"}
    else:
        # проверка пройдена, удаление и закрепление в логе
        uid = uid[0]
        cursor.execute("DELETE FROM inventory WHERE id = ?", (eid,))
        cursor.execute("DELETE FROM belongings WHERE obj_id = ?", (eid,))
        cursor.execute("DELETE FROM pending_requests WHERE obj_id = ?", (eid,))
        cursor.execute("INSERT INTO logs (action, obj_id, userid, time) VALUES ('REM', ?, ?, ?)", (eid, uid, int(time.time())))
        db.commit()
        return {"error": None}

def add_to_inventory(name: str, amount: int, status: int, session_key: str, ip_addr: str):
    # добавление элемента в инвентарь и запись о действии в лог

    name = name.lower().strip()
    if product_name_check_format(name)["error"]:
        # возврат ошибки при проверке имени продукта (error = length / symbol)
        return {"error": product_name_check_format(name)["error"]}
    elif status < 0 or status > 2:
        return {"error": "wrong_status"}

    # дополнительная проверка
    cursor.execute("SELECT userid FROM sessions WHERE session_key = ? AND lifetime > ? AND ip_addr = ? AND is_alive = 1", (session_key, int(time.time()), ip_addr))
    uid = cursor.fetchone()
    cursor.execute("SELECT * FROM inventory WHERE name = ?", (name,))
    adding_obj_data = cursor.fetchone()
    if not uid:
        # error = session_error, если сессия истекла
        return {"error": "session_error"}
    elif adding_obj_data:
        # error = object_already_exists, если элемент с таким именем уже существует
        return {"error": "object_already_exists"}
    else:
        uid = uid[0]
        # добавление элемента в инвентарь и запись в лог
        cursor.execute("INSERT INTO inventory (name, amount, status) VALUES (?, ?, ?)", (name, amount, status))
        db.commit()
        cursor.execute("SELECT id FROM inventory WHERE name = ?", (name,))
        eid = cursor.fetchone()[0]
        cursor.execute("INSERT INTO logs (action, obj_id, userid, time) VALUES ('ADD', ?, ?, ?)", (eid, uid, int(time.time())))
        db.commit()

        # object_id содержит ID созданного в инвентаре предмета
        return {"error": None, "object_id": eid}

def edit_inventory_object(eid: int, new_name: str, new_amount: str, new_status: int, session_key: str, ip_addr: str):
    # изменение элемента по ID и запись о действии в лог

    new_name = new_name.lower().strip()
    if product_name_check_format(new_name)["error"]:
        # возврат ошибки при проверке имени продукта (error = length / symbol)
        return {"error": product_name_check_format(new_name)["error"]}
    elif new_status < 0 or new_status > 2:
        return {"error": "wrong_status"}
    
    # дополнительная проверка
    cursor.execute("SELECT userid FROM sessions WHERE session_key = ? AND lifetime > ? AND ip_addr = ? AND is_alive = 1", (session_key, int(time.time()), ip_addr))
    uid = cursor.fetchone()
    cursor.execute("SELECT * FROM inventory WHERE id = ?", (eid,))
    editing_obj_data = cursor.fetchone()
    if not uid:
        # error = session_error, если сессия истекла
        return {"error": "session_error"}
    elif not editing_obj_data:
        # error = no_result, если элемент не существует
        return {"error": "no_result"}
    else:
        uid = uid[0]
        # изменение элемента и запись о действии в лог
        cursor.execute("UPDATE inventory SET name = ?, amount = ?, status = ? WHERE id = ?", (new_name, new_amount, new_status, eid))
        cursor.execute("INSERT INTO logs (action, obj_id, userid, time) VALUES ('EDT', ?, ?, ?)", (eid, uid, int(time.time())))
        db.commit()
        return {"error": None}

def pin_inventory_element(eid: int, username: str, pinning_amount: int, description: str = ''):
    # закрепление элемента инвентаря за каким-либо пользователем
    
    username = username.lower().strip()
    description = description.strip()
    cursor.execute("SELECT amount FROM inventory WHERE id = ?", (eid,))
    inventory_amount = cursor.fetchone()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    uid = cursor.fetchone()
    if not uid:
        # error = no_user, если пользователь не найден
        return {"error": "no_user"}
    else:
        uid = uid[0]

    if not inventory_amount:
        # error = no_result, если элемент не существует
        return {"error": "no_result"}
    else:
        inventory_amount = inventory_amount[0]
        if inventory_amount < pinning_amount:
            # error = not_enough_amount, если недостаточно штук элемента в инвентаре
            return {"error": "not_enough_amount"}
        else:
            new_inventory_amount = inventory_amount - pinning_amount
            cursor.execute("UPDATE inventory SET amount = ? WHERE id = ?", (new_inventory_amount, eid))
            db.commit()
    
    cursor.execute("SELECT id FROM belongings WHERE userid = ? AND obj_id = ?", (uid, eid))
    belonging_id = cursor.fetchone()

    if belonging_id:
        # к пользователю уже прикреплён этот объект, поэтому при вызове функции прикрепления, прикреплённые объекты складываются
        # если комментарий не приведён, то он остаётся тем же
        belonging_id = belonging_id[0]
        cursor.execute("SELECT amount FROM belongings WHERE id = ?", (belonging_id,))
        current_amount = int(cursor.fetchone()[0])
        new_amount = current_amount + pinning_amount
        if not description:
            cursor.execute("UPDATE belongings SET amount = ?, time = ? WHERE id = ?", (new_amount, get_date(), belonging_id))
            db.commit()
        else:
            cursor.execute("UPDATE belongings SET amount = ?, time = ?, description = ? WHERE id = ?", (new_amount, get_date(), description, belonging_id))
            db.commit()
        return {"error": None}
    else:
        # создание нового прикрепления и назначение новому предмету статуса 1
        cursor.execute("INSERT INTO belongings (obj_id, userid, amount, time, description) VALUES (?, ?, ?, ?, ?)", (eid, uid, pinning_amount, get_date(), description))
        db.commit()
        
        cursor.execute("SELECT status FROM inventory WHERE id = ?", (eid,))
        old_status = cursor.fetchone()[0]
        if int(old_status) == 0:
            cursor.execute("UPDATE inventory SET status = 1 WHERE id = ?", (eid,))
            db.commit()

        return {"error": None}

def register_user(username: str, first_name: str, password: str, second_name: str = ''):
    # регистрация нового пользователя
    
    username = username.lower().strip()

    # проверка на существование пользователя в базе
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    existing_user = cursor.fetchone()
    if existing_user:
        # error = user_existing, если пользователь уже существует в базе
        return {"error": "user_existing"}

    first_name = first_name.strip()
    pass_hash = hash_password(password)

    if login_check_format(username)["error"]:
        # возврат ошибки при проверке никнейма (error = length / symbol)
        return {"error": login_check_format(username)["error"]}
    
    if product_name_check_format(first_name.lower())["error"]:
        # возврат ошибки при проверке имени пользователя (error = length / symbol)
        return {"error": product_name_check_format(first_name.lower())["error"]}
    
    if second_name:
        second_name = second_name.strip()
        if product_name_check_format(second_name.lower())["error"]:
            # возврат ошибки при проверке фамилии пользователя (error = length / symbol)
            return {"error": product_name_check_format(second_name.lower())["error"]}

    cursor.execute("INSERT INTO users (username, permission, first_name, second_name, pass_hash, creation_date) VALUES (?, 'user', ?, ?, ?, ?)", (username, first_name, second_name, pass_hash, get_date()))
    db.commit()
    return {"error": None}

def assign_administrator(username: str):
    # назначение пользователя администратором
    username = username.lower().strip()

    if login_check_format(username)["error"]:
        # возврат ошибки при проверке никнейма (error = length / symbol)
        return {"error": login_check_format(username)["error"]}
    
    # проверка на существование пользователя в базе
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    existing_user = cursor.fetchone()
    if not existing_user:
        # error = no_user, если пользователь не существует в базе
        return {"error": "no_user"}
    
    cursor.execute("UPDATE users SET permission = 'admin' WHERE username = ?", (username,))
    db.commit()
    return {"error": None}

def assign_user(username: str):
    # назначение пользователя юзером (разжалование)
    username = username.lower().strip()

    if login_check_format(username)["error"]:
        # возврат ошибки при проверке никнейма (error = length / symbol)
        return {"error": login_check_format(username)["error"]}
    
    # проверка на существование пользователя в базе
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    existing_user = cursor.fetchone()
    if not existing_user:
        # error = no_user, если пользователь не существует в базе
        return {"error": "no_user"}
    
    cursor.execute("UPDATE users SET permission = 'user' WHERE username = ?", (username,))
    db.commit()
    return {"error": None}

def is_admin(session_key: str, ip_addr: str):
    # функция, выдающая результат прав доступа пользователя по ключу сессии

    # проверка сессии
    cursor.execute("SELECT userid FROM sessions WHERE session_key = ? AND lifetime > ? AND ip_addr = ? AND is_alive = 1", (session_key, int(time.time()), ip_addr))
    uid = cursor.fetchone()
    if not uid:
        # error = session_error, если сессия истекла
        return {"error": "session_error"}
    else:
        uid = uid[0]
        cursor.execute("SELECT permission FROM users WHERE id = ?", (uid,))
        res = cursor.fetchone()[0]
        if res == "admin":
            # если клиент - адиминистратор
            return {"error": None, "result": True}
        else:
            # если клиент - пользователь
            return {"error": None, "result": False}
        
def create_request(r_type: str, eid: int, amount: int, session_key: str, ip_addr: str, description: str = ""):
    # функция, создающая заявку от пользователя
    # r_type = to_pin_element (на прикрепление предмета), to_repair_element (на починку/замену предмета)

    description = description.strip()
    r_type = r_type.lower().strip()
    if r_type not in ("to_pin_element", "to_repair_element"):
        # error = wrong_type, если введён неправильный тип заявки
        return {"error": "wrong_type"}
    if amount < 0:
        # error = wrong_amount, если в заявке указано неправильное количество
        return {"error": "wrong_amount"}
    
    # проверка сессии
    cursor.execute("SELECT userid FROM sessions WHERE session_key = ? AND lifetime > ? AND ip_addr = ? AND is_alive = 1", (session_key, int(time.time()), ip_addr))
    uid = cursor.fetchone()
    if not uid:
        # error = session_error, если сессия истекла
        return {"error": "session_error"}
    else:
        uid = uid[0]

        cursor.execute("SELECT amount FROM inventory WHERE id = ?", (eid,))
        inventory_amount = cursor.fetchone()
        if not inventory_amount:
            # error = no_result, если элемент не существует
            return {"error": "no_result"}
        else:
            inventory_amount = inventory_amount[0]

        if inventory_amount < amount:
            # error = not_enough_amount, если недостаточно штук элемента в инвентаре
            return {"error": "not_enough_amount"}

        # проверка на существование такой же заявки
        cursor.execute("SELECT * FROM pending_requests WHERE type = ? AND obj_id = ? AND userid = ? AND amount = ? AND description = ?", (r_type, eid, uid, amount, description))
        existing_request = cursor.fetchone()
        if existing_request:
            # error = request_already_exists, если точно такая же заявка уже существует
            return {"error": "request_already_exists"}

        # создание заявки
        cursor.execute("INSERT INTO pending_requests (type, obj_id, userid, amount, time, description) VALUES (?, ?, ?, ?, ?, ?)", (r_type, eid, uid, amount, get_date(), description))
        db.commit()
        return {"error": None}

def fetch_all_requests(r_type: str):
    # возвращает заявки в порядке их создания по возрастанию (используется администратором)
    # r_type = to_pin_element (на прикрепление предмета), to_repair_element (на починку/замену предмета)

    r_type = r_type.lower().strip()
    if r_type not in ("to_pin_element", "to_repair_element"):
        # error = wrong_type, если введён неправильный тип заявки
        return {"error": "wrong_type"}

    cursor.execute("""SELECT pending_requests.id, pending_requests.obj_id, inventory.name, users.username, pending_requests.amount, pending_requests.time, pending_requests.description
                   FROM ((pending_requests
                   INNER JOIN inventory ON pending_requests.obj_id = inventory.id)
                   INNER JOIN users ON pending_requests.userid = users.id)
                   WHERE pending_requests.type = ?
                   """, (r_type,))
    fetch_results = cursor.fetchall()

    if not fetch_results:
        # error = no_results, если элементов нет
        return {"error": "no_results"}
    else:
        # передача результатов
        # колонки: ID заявки, ID прдемета, наименование предмета, никнейм пользователя, кол-во предметов в заявке, дата подачи заявки, описание заявки
        return {"error": None, "results": fetch_results}
    
def approve_request(request_id: int):
    # принять заявку

    cursor.execute("SELECT type FROM pending_requests WHERE id = ?", (request_id,))
    request_type = cursor.fetchone()
    if not request_type:
        # error = "no_result", если заявки не существует
        return {"error": "no_result"}
    else:
        request_type = request_type[0]

    if request_type == "to_repair_element":
        # принять заявку по ремонту предмета (принятие и отмена заявки означают удаление)
        cursor.execute("DELETE FROM pending_requests WHERE id = ?", (request_id,))
        db.commit()
        return {"error": None}
    else:
        # принять заявку по прикреплению предмета
        cursor.execute("""SELECT pending_requests.obj_id, users.username, pending_requests.amount, pending_requests.description
                       FROM pending_requests
                       INNER JOIN users ON pending_requests.userid = users.id
                       WHERE pending_requests.id = ?""", (request_id,))
        request_data = cursor.fetchone()

        res = pin_inventory_element(request_data[0], request_data[1], request_data[2], request_data[3])
        if res["error"] != None:
            # если в процессе закрепления происходит ошибка, она передаётся в error
            return {"error": res["error"]}
        else:
            cursor.execute("DELETE FROM pending_requests WHERE id = ?", (request_id,))
            db.commit()
            return {"error": None}
        
def decline_request(request_id: int):
    # отменить заявку

    cursor.execute("SELECT type FROM pending_requests WHERE id = ?", (request_id,))
    request_type = cursor.fetchone()
    if not request_type:
        # error = "no_result", если заявки не существует
        return {"error": "no_result"}
    
    cursor.execute("DELETE FROM pending_requests WHERE id = ?", (request_id,))
    db.commit()
    return {"error": None}

def cancel_request(request_id: int, session_key: str, ip_addr: str):
    # отзыв заявки пользователем

    # проверка сессии
    cursor.execute("SELECT userid FROM sessions WHERE session_key = ? AND lifetime > ? AND ip_addr = ? AND is_alive = 1", (session_key, int(time.time()), ip_addr))
    uid = cursor.fetchone()
    if not uid:
        # error = session_error, если сессия истекла
        return {"error": "session_error"}
    else:
        uid = uid[0]

        cursor.execute("SELECT type FROM pending_requests WHERE id = ? AND userid = ?", (request_id, uid))
        request_type = cursor.fetchone()
        if not request_type:
            # error = "no_result", если заявки не существует / нет доступа к заявке
            return {"error": "no_result"}
        else:
            # удаление заявки
            cursor.execute("DELETE FROM pending_requests WHERE id = ? AND userid = ?", (request_id, uid))
            db.commit()
            return {"error": None}
        
def fetch_sent_requests(session_key: str, ip_addr: str):
    # вывод данных об отправленных пользователем заявках, которые ещё не были рассмотрены администрацией

    # проверка сессии
    cursor.execute("SELECT userid FROM sessions WHERE session_key = ? AND lifetime > ? AND ip_addr = ? AND is_alive = 1", (session_key, int(time.time()), ip_addr))
    uid = cursor.fetchone()
    if not uid:
        # error = session_error, если сессия истекла
        return {"error": "session_error"}
    else:
        uid = uid[0]

        cursor.execute("""SELECT pending_requests.id, pending_requests.type, pending_requests.obj_id, inventory.name, pending_requests.amount, pending_requests.time, pending_requests.description
                       FROM pending_requests
                       INNER JOIN inventory ON pending_requests.obj_id = inventory.id
                       WHERE pending_requests.userid = ?""", (uid,))
        request_data = cursor.fetchall()

        if not request_data:
            # error = no_results, если отправленных заявок не найдено
            return {"error": "no_results"}
        else:
            # передача результатов в results
            # колонки: ID заявки, тип заявки, ID предмета, наименование предмета, кол-во предметов в заявке, время подачи заявки, комментарий
            return {"error": None, "results": request_data}
        
def end_session(session_key: str, ip_addr: str):
    # выход пользователя из системы, завершение сессии

    # проверка сессии
    cursor.execute("SELECT id FROM sessions WHERE session_key = ? AND lifetime > ? AND ip_addr = ? AND is_alive = 1", (session_key, int(time.time()), ip_addr))
    session_id = cursor.fetchone()
    if not session_id:
        # error = session_error, если сессия истекла
        return {"error": "session_error"}
    else:
        session_id = session_id[0]

        cursor.execute("UPDATE sessions SET is_alive = 0 WHERE id = ?", (session_id,))
        db.commit()
        return {"error": None}
    
def fetch_all_users(u_type: str):
    # получение списка пользователей
    # u_type = admin, если вывести только администраторов
    # u_type = user, если вывести только пользователей

    if u_type not in ("admin", "user"):
        # error = wrong_type, если введён неправильный тип
        return {"error": "wrong_type"}
    
    cursor.execute("SELECT id, username, first_name, second_name, creation_date FROM users WHERE permission = ?", (u_type,))
    fetch_results = cursor.fetchall()

    if not fetch_results:
        # error = no_results, если нет записей о выбранных клиентах
        return {"error": "no_results"}
    else:
        # передача найденных результатов
        # колонки: ID пользователя, никнейм, имя, фамилия, дата создания
        return {"error": None, "results": fetch_results}
    
def terminate_all_sessions_of(uid: int):
    # "убить" все сессии пользователя

    cursor.execute("SELECT id FROM sessions WHERE userid = ? AND is_alive = 1", (uid,))
    session_ids = cursor.fetchall()
    if not session_ids:
        # error = no_result, если все сессии пользователя закрыты
        return {"error": "no_result"}
    else:
        cursor.execute("UPDATE sessions SET is_alive = 0 WHERE userid = ?", (uid,))
        db.commit()
        return {"error": None}

def change_password(session_key: str, ip_addr: str, old_password: str, new_password: str):
    # изменение пароля и "убийство" всех сессий

    # проверка сессии
    cursor.execute("SELECT userid FROM sessions WHERE session_key = ? AND lifetime > ? AND ip_addr = ? AND is_alive = 1", (session_key, int(time.time()), ip_addr))
    uid = cursor.fetchone()
    if not uid:
        # error = session_error, если сессия истекла
        return {"error": "session_error"}
    else:
        uid = uid[0]

        # проверка старого пароля
        cursor.execute("SELECT pass_hash FROM users WHERE id = ?", (uid,))
        db_old_password = cursor.fetchone()[0]
        if not check_password(db_old_password, hash_password(old_password)):
            # error = wrong_password, если текущий пароль неверен
            return {"error": "wrong_password"}
        else:
            cursor.execute("UPDATE users SET pass_hash = ? WHERE id = ?", (hash_password(new_password), uid))
            db.commit()
            return {"error": terminate_all_sessions_of(uid)["error"]}

def delete_user_of(uid: int):
    # удаление профиля, его принадлежностей, заявок и истории сессий

    cursor.execute("SELECT * FROM users WHERE id = ?", (uid,))
    existing_user = cursor.fetchone()
    if not existing_user:
        # error = no_result, если пользователь не найден
        return {"error": "no_result"}
    else:
        cursor.execute("DELETE FROM users WHERE id = ?", (uid,))
        cursor.execute("DELETE FROM belongings WHERE userid = ?", (uid,))
        cursor.execute("DELETE FROM pending_requests WHERE userid = ?", (uid,))
        cursor.execute("DELETE FROM sessions WHERE userid = ?", (uid,))
        db.commit()
        return {"error": None}


def fetch_my_belongings(session_key: str, ip_addr: str):
    # получение информации о закрепленных со стороны пользователя элементов

    # проверка сессии
    cursor.execute("SELECT userid FROM sessions WHERE session_key = ? AND lifetime > ? AND ip_addr = ? AND is_alive = 1", (session_key, int(time.time()), ip_addr))
    uid = cursor.fetchone()
    if not uid:
        # error = session_error, если сессия истекла
        return {"error": "session_error"}
    else:
        uid = uid[0]
        cursor.execute("""SELECT belongings.id, belongings.obj_id, inventory.name, belongings.amount, belongings.time, belongings.description
        FROM belongings
        INNER JOIN inventory ON belongings.obj_id = inventory.id
        WHERE belongings.userid = ?""", (uid,))
        fetch_results = cursor.fetchall()

        if not fetch_results:
            # error = no_results, если нет записей о закрепленных объектах
            return {"error": "no_results"}
        else:
            # передача найденных результатов
            # колонки: ID принадлежности элемента, ID элемента, наименование, прикреплённое количество, время прикрепления, комментарий
            return {"error": None, "results": fetch_results}

def return_my_belonging(bid: int, session_key: str, ip_addr: str):
    # вернуть элемент в инвентарь, добровольно открепить его от профиля

    # проверка сессии
    cursor.execute("SELECT userid FROM sessions WHERE session_key = ? AND lifetime > ? AND ip_addr = ? AND is_alive = 1", (session_key, int(time.time()), ip_addr))
    uid = cursor.fetchone()
    if not uid:
        # error = session_error, если сессия истекла
        return {"error": "session_error"}
    else:
        uid = uid[0]
        cursor.execute("SELECT userid FROM belongings WHERE id = ?", (bid,))
        bd_uid = cursor.fetchone()
        if not bd_uid:
            # error = no_result, если нет записей о принадлежности
            return {"error": "no_result"}
        elif bd_uid[0] != uid:
            # error = no_permission, если выбрана чужая принадлежность
            return {"error": "no_permission"}
        else:
            # открепление предмета
            cursor.execute("SELECT obj_id, amount FROM belongings WHERE id = ?", (bid,))
            eid, belonging_amount = cursor.fetchone()
            cursor.execute("SELECT amount FROM inventory WHERE id = ?", (eid,))
            inv_amount = cursor.fetchone()[0]
            cursor.execute("UPDATE inventory SET amount = ? WHERE id = ?", (belonging_amount+inv_amount, eid))
            cursor.execute("DELETE FROM belongings WHERE id = ?", (bid,))
            db.commit()
            return {"error": None}

def add_to_plan(name: str, price: int, amount: int, supplier_name: str):
    # добавление элемента в план закупок

    cursor.execute("INSERT INTO purchase_plan (name, price, amount, supplier_name) VALUES (?, ?, ?, ?)", (name, price, amount, supplier_name))
    db.commit()

def remove_from_plan(pid: int):
    # удаление элемента из плана закупок

    cursor.execute("SELECT * FROM purchase_plan WHERE id = ?", (pid,))
    existing_el = cursor.fetchone()
    if not existing_el:
        # error = no_result, если нет элемента с таким ID
        return {"error": "no_result"}
    else:
        cursor.execute("DELETE FROM purchase_plan WHERE id = ?", (pid,))
        db.commit()
        return {"error": None}

def fetch_plan():
    # получение списка элементов в плане закупок

    cursor.execute("SELECT * FROM purchase_plan ORDER BY id")
    fetch_results = cursor.fetchall()
    if not fetch_results:
        # error = no_results, если записей в плане нет
        return {"error": "no_results"}
    else:
        # передача результатов
        # колонки: ID элемента в плане, наименование, цена, количество, имя поставщика
        return {"error": None, "results": fetch_results}

def create_report():
    # создание отчета

    # нахождение суммы предметов
    cursor.execute("SELECT SUM(amount) FROM belongings")
    using_elements_number = cursor.fetchone()[0]

    # составление таблицы используемых предметов
    # подгон элементов под первую таблицу
    cursor.execute("SELECT id FROM inventory")
    inventory_ids = cursor.fetchall()
    raw_using_elements = []
    for eid in inventory_ids:
        eid = eid[0]
        cursor.execute("SELECT SUM(amount) FROM belongings WHERE obj_id = ?", (eid,))
        amount = cursor.fetchone()[0]
        if amount:
            cursor.execute("SELECT name FROM inventory WHERE id = ?", (eid,))
            name = cursor.fetchone()[0]
            raw_using_elements.append([eid, amount, name])

    using_elements = ""
    for el in raw_using_elements:
        eid, amount, name = el
        eid = str(eid); amount = str(amount); name = str(name)
        if len(eid) == 1: eid = f"   {eid}   "
        elif len(eid) == 2: eid = f"   {eid}  "
        elif len(eid) == 3: eid = f"  {eid}  "
        elif len(eid) == 4: eid = f"  {eid} "
        elif len(eid) == 5: eid = f" {eid} "
        else: eid += " "

        if len(amount) == 1: amount = f"     {amount}     "
        elif len(amount) == 2: amount = f"     {amount}     "
        elif len(amount) == 3: amount = f"     {amount}    "
        elif len(amount) == 4: amount = f"    {amount}    "
        elif len(amount) == 5: amount = f"    {amount}   "
        elif len(amount) >= 6: amount = " " + amount + " "

        using_elements = using_elements + "\t" + eid + "|" + amount + "| " + name + "\n"

    # подгон элементов под вторую таблицу
    cursor.execute("SELECT SUM(amount) FROM inventory WHERE status = 0")
    new_elements_number = cursor.fetchone()[0]
    if not new_elements_number: new_elements_number = 0
    cursor.execute("SELECT SUM(amount) FROM inventory WHERE status = 1")
    used_elements_number = cursor.fetchone()[0]
    if not used_elements_number: used_elements_number = 0
    cursor.execute("SELECT SUM(amount) FROM inventory WHERE status = 2")
    broken_elements_number = cursor.fetchone()[0]
    if not broken_elements_number: broken_elements_number = 0

    cursor.execute("SELECT id, name FROM inventory WHERE status = 2")
    raw_broken_elements = cursor.fetchall()
    broken_elements = ""
    for el in raw_broken_elements:
        eid, name = el
        eid = str(eid); name = str(name)
        if len(eid) == 1: eid = f"   {eid}   "
        elif len(eid) == 2: eid = f"   {eid}  "
        elif len(eid) == 3: eid = f"  {eid}  "
        elif len(eid) == 4: eid = f"  {eid} "
        elif len(eid) == 5: eid = f" {eid} "
        else: eid += " "

        broken_elements = broken_elements + "\t" + eid + "| " + name + "\n"

    form = f"""ОТЧЁТ ПО ИСПОЛЬЗОВАНИЮ И СОСТОЯНИЮ ИНВЕНТАРЯ
    Актуален на: {get_date()}
    
    Подробности об использовании инвентаря:
    Всего в использовании находится {using_elements_number} предметов.
    Элементы в использовании:
           id  | количество |   наименование
    {using_elements}
    
    Подробности о состоянии элементов инвентаря:
    Всего предметов: {new_elements_number + used_elements_number + broken_elements_number}
    Всего новых предметов: {new_elements_number}
    Всего использованных предметов: {used_elements_number}
    Всего сломанных предметов: {broken_elements_number}

    Сломанные элементы:
           id  |   наименование
    {broken_elements}

    Данный отчёт составлен автоматически.
    """
    return form

