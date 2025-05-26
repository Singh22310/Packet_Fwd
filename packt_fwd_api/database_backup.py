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

# Database credentials
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

def init_db():
    try:
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        logger.info("Database connection established")

        # Create a cursor object
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS versionDB_Test (
                id SERIAL PRIMARY KEY,
                version VARCHAR(255) NOT NULL,
                file_name VARCHAR(255) NOT NULL,
                update_type VARCHAR(255) NOT NULL,
                time_stamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        logger.info("Table 'version_recieved' created or already exists")
    
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

def check_update(version):
    try:
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        logger.info("Database connection established")

        # Create a cursor object
        cursor = conn.cursor(cursor_factory=DictCursor)

        cursor.execute('''
            SELECT * FROM versionDB_Test WHERE version = %s
        ''', (version,))
        result = cursor.fetchone()

        if result:
            logger.info(f"Version {version} already exists in the database")
            return True
        else:
            logger.info(f"Version {version} does not exist in the database... Update Available")
            return False

    except Exception as e:
        logger.error(f"Error checking version in database: {e}")
 

