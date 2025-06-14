# DevopsFlow Web Server

A simple web interface for interacting with the DevopsFlow system.

## Project Structure

```
src/web/
├── api/                    # API endpoints
│   └── __init__.py
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── .env                   # Environment variables
└── README.md              # This file
```

## Setup

1. Install Python 3.8+ if not already installed.

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Server

### Development Mode

```bash
# In the src/web directory
flask run
```

The server will be available at `http://localhost:5000`

### Production Mode

```bash
gunicorn app:app
```

## API Endpoints

- `POST /api/init` - Start DevopsFlow with a prompt
  ```json
  {
    "prompt": "Your prompt here"
  }
  ```

- `GET /api/blackboard` - Get the current state of the blackboard

- `GET /api/status` - Get the current status of the DevopsFlow

## Frontend Development

The frontend is a Quasar SPA that will be served from the `frontend/dist` directory.

## License

This project is part of the TFM project.
