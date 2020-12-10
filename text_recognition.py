import cv2
import re
import sqlite3


def preprocessing(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 3)
    img_binar = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 41,
                                      12)  # Preprocessing
    cv2.imshow('img', img_binar)
    cv2.waitKey(0)
    return img_binar


def data_find(extracted_text):
    splits = extracted_text.splitlines()
    receipt_ocr = {}

    # Название магазина
    if re.search(r'Дикси', extracted_text):
        market_name = 'Дикси'
    elif re.search(r'Лента', extracted_text):
        market_name = 'Лента'
    else:
        market_name = splits[0]

    # Поиск строк с товарами в магазинах, где есть умножение
    lines_with_multiplication = []

    for line in splits:
        if re.search(r'[*]|[#]|[%]|[х]\s',
                     line):  # Иногда вместо * распознается # или =, так как # больше нигде не используется
            lines_with_multiplication.append(line)  # то добавлен поиск

    lines_with_multiplication_split = []  # Создаем список, в которому будут храниться отдельные слова в строках.
    for i in range(len(lines_with_multiplication)):
        lines_with_multiplication_split.append(lines_with_multiplication[i].split())

    product_name = []
    for i in range(len(lines_with_multiplication_split)):
        for j in range(len(lines_with_multiplication_split[i])):
            if re.search(r'[А-Я]+[а-я]*[A-Z]*[a-z]*', lines_with_multiplication_split[i][j]):
                product_name.append([])
                product_name[i].append(
                    re.search(r'[А-Я]+[а-я]*[A-Z]*[a-z]*', lines_with_multiplication_split[i][j]).group())

    # Удаляем пустые элементы (способ я выбрал неординарный)
    k = 0
    for i in range(len(product_name)):
        if product_name[i] == []:
            k += 1  # Количество пустых элементов
    product_name = product_name[:-k]  # Список идет до элемента последнего непустого элемента

    if market_name == 'Лента':

        # Избавляемся от "НДС" или других вариантов, как это слово может быть прочитано
        for i in range(len(product_name)):
            product_name[i] = product_name[i][:-1]

        # Цена товара
        price = []
        for i in range(len(lines_with_multiplication_split)):
            if lines_with_multiplication_split[i][-5] != '*':
                price.append(lines_with_multiplication_split[i][-5])
            else:
                price.append(lines_with_multiplication_split[i][-6])
        maketrans = str.maketrans  # https://issue.life/questions/29036023
        for i in range(len(price)):
            price[i] = price[i].translate(maketrans(',', '.'))
            price[i] = round(float(price[i]), 2)

        # Стоимость товара
        cost = []
        for i in range(len(lines_with_multiplication_split)):
            cost.append(lines_with_multiplication_split[i][-3])
            cost[i] = cost[i].translate(maketrans(',', '.'))
            cost[i] = cost[i].replace('=', '')  # Убираем знак = из чисел (в чеке они идут подряд)

    # Цена, количество, стоимость, итоговая сумма, объединение характеристик в общий элемент ДЛЯ ДИКСИ
    if market_name == 'Дикси':

        # Цена товара
        price = []
        for i in range(len(lines_with_multiplication_split)):
            price.append(lines_with_multiplication_split[i][-3])
        maketrans = str.maketrans
        for i in range(len(price)):
            price[i] = price[i].translate(maketrans(',', '.'))

        # Стоимость
        cost = []
        for i in range(len(lines_with_multiplication_split)):
            cost.append(lines_with_multiplication_split[i][-1])
            cost[i] = cost[i].translate(maketrans(',', '.'))

    # Итоговая сумма будет находиться через суммирование цен в чеке
    result = 0
    for i in range(len(cost)):
        result += float(cost[i])
        result = round(result, 2)

    # Количество
    quantity = []
    for i in range(len(lines_with_multiplication_split)):
        quantity.append(round(float(cost[i]) / float(price[i]), 3))

    # Объединяем название продуктов в один элементы, а эти элементы в общий список
    full_product_name = []
    for i in range(len(lines_with_multiplication_split)):
        product_first = []
        for j in range(len(product_name[i])):
            product_first.append(product_name[i][j])
        full_product_name.append(product_first)

    for i in range(len(full_product_name)):
        full_product_name[i] = [' '.join(full_product_name[i])]

    # Дата
    date = 'None'
    date_pattern = r'([0-9][0-9]\.[0-9][0-9]\.[0-9][0-9])'
    for line in splits:
        if re.search(date_pattern, line):  # Поиск даты и, если дата находится, то она преобразуется в
            date = line  # нужный формат
        if date == line:
            date = re.search(date_pattern, extracted_text).group()
            date_1 = date.split('.')
            date_2 = date_1[-1] + '.' + date_1[-2] + '.' + date_1[-3]
    receipt_ocr['date'] = date_2
    receipt_ocr['market_name'] = market_name
    receipt_ocr['result'] = result
    receipt_ocr['count'] = len(lines_with_multiplication_split)  # Запоминаем количество продуктов
    for i in range(len(lines_with_multiplication_split)):
        receipt_ocr[f'full_product_name_{i}'] = full_product_name[i][0]
        receipt_ocr[f'price_{i}'] = price[i]
        receipt_ocr[f'quantity_{i}'] = quantity[i]
        receipt_ocr[f'cost_{i}'] = cost[i]
    return receipt_ocr


def data_upload(receipt_ocr, path, uname):
    db = sqlite3.connect(path + '/database.db')
    cursor = db.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS receipts_main (
        id INTEGER PRIMARY KEY, 
        market_names TEXT, 
        dates TEXT, 
        results FLOAT,
        uname_name TEXT)
    ''')
    # В таблице с продуктами id будет меняться только, когда будет считываться следующий чек.
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS receipts_info (
        id INTEGER,  
        products TEXT,
        price FLOAT,
        quantity FLOAT,
        costs FLOAT)
    ''')

    # Отправляем данные в таблицу с чеками
    cursor.execute(
        f"INSERT INTO receipts_main (market_names, dates, results, uname_main) VALUES ('{receipt_ocr['market_name']}', '{receipt_ocr['date']}', '{receipt_ocr['result']}', '{uname}')")

    # Индентифицируем номер чека для таблицы с продуктами
    cursor.execute("SELECT MAX(id) FROM receipts_main")

    id_receipt = cursor.fetchall()

    # Вытаскиваем из receipts_main id только что считанного чека и вписываем это id в таблицу с продуктами
    # Отправляем данные в таблицу с продуктами
    for i in range(receipt_ocr['count']):
        cursor.execute(f'''INSERT INTO receipts_info (id, products, price, quantity, costs) VALUES (
        '{id_receipt[0][0]}',
        '{receipt_ocr[f"full_product_name_{i}"]}',
        '{receipt_ocr[f"price_{i}"]}',
        '{receipt_ocr[f'quantity_{i}']}',
        '{receipt_ocr[f'cost_{i}']}')
      ''')

    db.commit()
    db.close()
