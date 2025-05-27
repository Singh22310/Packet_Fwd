import os
import logging
import psycopg2
from psycopg2.extras import DictCursor
import io
from dotenv import load_dotenv 

load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseHandler:
    def __init__(self):
        # Database credentials
        self.DB_HOST = os.getenv("DB_HOST")
        self.DB_PORT = os.getenv("DB_PORT")
        self.DB_NAME = os.getenv("DB_NAME")
        self.DB_USER = os.getenv("DB_USER")
        self.DB_PASSWORD = os.getenv("DB_PASSWORD")

    def init_db(self):
        try:
            # Connect to the PostgreSQL database
            self.conn = psycopg2.connect(
                host=self.DB_HOST,
                port=self.DB_PORT,
                dbname=self.DB_NAME,
                user=self.DB_USER,
                password=self.DB_PASSWORD
            )
            logger.info("Database connection established")

            # Create a cursor object
            self.cursor = self.conn.cursor()

            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS versionDB_Test (
                    id SERIAL PRIMARY KEY,
                    version VARCHAR(255) NOT NULL,
                    file_name VARCHAR(255) NOT NULL,
                    update_type VARCHAR(255) NOT NULL,
                    time_stamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            self.conn.commit()
            logger.info("Table 'version_recieved' created or already exists")
        
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

    def check_update(self, version):
        try:
            # Connect to the PostgreSQL database
            if not hasattr(self, 'conn'):
                self.init_db()

            self.cursor.execute('SELECT * FROM versionDB_Test WHERE version = %s', (version,))
            result = self.cursor.fetchone()
            
            if result:
                logger.info(f"Update available for version: {version}")
                return False  # Update available
            else:
                logger.info(f"No update available for version: {version}")
                return True  # No update available
        
        except Exception as e:
            logger.error(f"Error checking update: {e}")
            raise

    def put_update(version, file_name, update_type):
        try:
            if not hasattr(self, 'conn'):
                self.init_db()
            
            self.cursor.execute('''
                INSERT INTO versionDB_Test (version, file_name, update_type)
                VALUES (%s, %s, %s)
            ''', (version, file_name, update_type))
            self.conn.commit()
            logger.info(f"Update details inserted: {version}, {file_name}, {update_type}")
            return True

        except Exception as e:
            logger.error(f"Error inserting update details: {e}")
            return False

    def close_connection(self):
        if hasattr(self, 'cursor'):
            self.cursor.close()
        if hasattr(self, 'conn'):
            self.conn.close()