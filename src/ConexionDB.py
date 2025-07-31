import mysql.connector
from mysql.connector import Error

def get_connection():

    try:
        connection = mysql.connector.connect(
            host="localhost",
            port=3306,
            user="root",
            password="12345",
            database="administracion"
        )

        if connection.is_connected():
            print("Conexion exitosa")
            info_server = connection.get_server_info()
            print("Informacion del servidor: ", info_server)
            return connection
        
    except Error as e:
        print("Con los dedos de las manos, con los dedos de los pies. Con la polla y los cojones, todo suma 23. ", e)
        return None