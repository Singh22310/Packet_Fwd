# Update Management System

A Flask-based application that automatically checks for updates, downloads them, and forwards them to designated target systems via SSH/SFTP. The system maintains a PostgreSQL database to track update versions and prevents duplicate processing.

## Features

- **Automated Update Checking**: Regularly checks for available updates via REST API
- **Smart Version Control**: Tracks processed updates in PostgreSQL database to avoid duplicates
- **File Download & Processing**: Downloads update files and extracts them automatically
- **Remote File Transfer**: Forwards updates to target systems using SSH/SFTP
- **Configuration-Based Deployment**: Uses JSON configuration files for flexible deployment targets
- **Comprehensive Logging**: Detailed logging for monitoring and debugging

## Architecture

The system consists of three main components:

1. **Flask API Server** (`app.py`) - Main application with REST endpoints
2. **Database Handler** (`database.py`) - PostgreSQL operations for version tracking
3. **File Handler** (`filehandler.py`) - File processing and remote transfer operations

## Prerequisites

- Python 3.7+
- PostgreSQL database
- SSH access to target systems
- Required Python packages (see Installation)

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd update-management-system
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file in the root directory:
   ```env
   # Database Configuration
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=your_database_name
   DB_USER=your_db_user
   DB_PASSWORD=your_db_password

   # API Configuration
   CHECK_UPDATE_API=http://your-update-server.com/api/check-updates

   # File Paths
   DOWNLOAD_PATH=/path/to/downloads
   UNZIP_PATH=/path/to/extracted/files
   ```

4. **Initialize the database**
   The application will automatically create the required tables on first run.

## Configuration

### Update Package Structure

Update packages should be ZIP files containing:
- Update files/folders
- `config.json` file with deployment configuration

### Sample config.json
```json
{
  "update_details": {
    "ip": "192.168.1.100",
    "username": "admin",
    "password": "secure_password",
    "target_dir": "/opt/application/updates"
  }
}
```

## API Endpoints

### Check for Updates
```http
GET /api/update-checker/
```

**Response:**
```json
{
  "message": "Update available",
  "version": "1.2.3"
}
```

### Download Updates
```http
GET /api/download/
```

**Response:**
```json
{
  "status": "success",
  "message": "File downloaded and saved as /path/to/file.zip"
}
```

## Usage

1. **Start the application**
   ```bash
   python app.py
   ```
   The server will start on `http://0.0.0.0:5000`

2. **Check for updates**
   ```bash
   curl http://localhost:5000/api/update-checker/
   ```

3. **Download and deploy updates**
   ```bash
   curl http://localhost:5000/api/download/
   ```

## Database Schema

The system creates a `versionDB_Test` table with the following structure:

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| version | VARCHAR(255) | Version identifier |
| file_name | VARCHAR(255) | Name of the update file |
| update_type | VARCHAR(255) | Type of update |
| time_stamp | TIMESTAMP | Creation timestamp |

## Error Handling

The application includes comprehensive error handling for:
- Database connection issues
- File download failures
- SSH/SFTP connection problems
- File extraction errors
- Missing configuration files

## Logging

Logs are configured to show:
- Timestamp
- Logger name
- Log level
- Message content

Log levels: INFO, ERROR, DEBUG

## Security Considerations

- Store sensitive credentials in environment variables
- Use secure SSH key authentication when possible
- Implement proper network security for API endpoints
- Validate update package integrity
- Use HTTPS for external API communications

## Development

### Project Structure
```
├── app.py              # Main Flask application
├── database.py         # Database operations
├── filehandler.py      # File processing and transfer
├── .env               # Environment variables (not in repo)
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

### Adding New Features

1. **New API Endpoints**: Add routes in `app.py`
2. **Database Operations**: Extend `DatabaseHandler` class
3. **File Processing**: Extend `FileHandler` class

## Dependencies

- Flask - Web framework
- psycopg2 - PostgreSQL adapter
- paramiko - SSH client
- requests - HTTP library
- python-dotenv - Environment variable loader
- flask-cors - CORS support

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license information here]

## Support

For issues and questions:
- Create an issue in the GitHub repository
- Check the logs for detailed error information
- Ensure all environment variables are properly configured

## Changelog

### Version 1.0.0
- Initial release
- Basic update checking and downloading
- Database integration for version tracking
- SSH/SFTP file transfer capabilities