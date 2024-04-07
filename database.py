from pymongo import MongoClient
import certifi
import ssl

MONGO_URI = 'mongodb+srv://javierdes:DLkYlLHYCn9WjCkN@cluster0.kigg6os.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'
ca = certifi.where()

def dbConnection():
    try:
        client = MongoClient(MONGO_URI, tlsCAFile=ca)
        db = client["salud_db"]
        print("si jala we")
        return db
    except Exception as e:
        print('Error de conexión con la BD:', e)
        return None
