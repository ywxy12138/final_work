import pymysql
from datetime import datetime
from pymysql import OperationalError
import constants as const

def create_connection():
    # 创建与数据库的连接
    connection = None
    try:
        connection = pymysql.connect(
            # 按具体需求填写
            host='localhost',
            port=3306,
            user='root',
            password=f"{const.PASSWORD}",
            charset='utf8mb4',
        )
        if connection:
            return connection
    except OperationalError as e:
        print(f"数据库连接有误，异常为{e}")
    return connection

def init_work():
    # 初始化的工作
    connection = create_connection()
    if connection:
        with connection.cursor() as cursor:
            # 创建数据库
            cursor.execute("CREATE DATABASE IF NOT EXISTS plagiarism_database CHARACTER SET utf8mb4")
            cursor.execute("USE plagiarism_database")
            # 创建历史记录表（存储查重结果）
            cursor.execute(''' CREATE TABLE IF NOT EXISTS history (
                                id INT AUTO_INCREMENT PRIMARY KEY,
                                main_code_id INT AUTO_INCREMENT NOT NULL,
                                sub_code_id INT AUTO_INCREMENT NOT NULL,
                                similarity DOUBLE NOT NULL,
                                label TEXT NOT NULL,
                           ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
            connection.commit()
            connection.close()

def save_history(history):
    init_work()
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("USE plagiarism_database")
            # 插入历史记录
            cursor.execute('''INSERT INTO history (
            main_code_id, sub_code_id, similarity, label) 
            VALUES (%s, %s, %s, %s)''', (history['main_code_id'],
            history['sub_code_id'], history['similarity'], history['label']))
            connection.commit()
            return history['main_code_id']
        except Exception as e:
            print(f"保存历史纪录失败，报错如下:{e}")
            connection.rollback()
        finally:
            connection.close()
    return None

def get_history(main_code_id):
    init_work()
    connection = create_connection()
    history = []
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("USE plagiarism_database")
            cursor.execute('''SELECT * FROM history 
                            WHERE main_code_id = %s OR sub_code_id = %s'''
                           (main_code_id, main_code_id))
            results = cursor.fetchall()
            for result in results:
                history.append({
                    'main_code_id': result[1],
                    'sub_code_id': result[2],
                    'similarity': result[3],
                    'label': result[4]
                })
        except Exception as e:
            print(f"读取历史记录失败，异常如下：{e}")
        finally:
            connection.close()
    return history


