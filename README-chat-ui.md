# Business GPT Chat Interface

A simple HTML/JavaScript chat interface for interacting with the Business GPT agent.

## Features

- Clean, responsive chat interface
- Simple Flask API backend
- Connects to the existing BasicAgent implementation
- Easy to deploy locally or to a server

## Setup and Installation

### Prerequisites

- Python 3.6 or higher
- A virtual environment (recommended)
- All dependencies for the BasicAgent

### Installation

1. Activate your virtual environment:
   ```
   source buss_venv/bin/activate  # On Windows: buss_venv\Scripts\activate
   ```

2. Install required packages:
   ```
   pip install flask flask-cors
   ```

### Running the Application

1. Start the Flask server:
   ```
   python app.py
   ```

2. Open your web browser and navigate to:
   ```
   http://localhost:5000
   ```

3. Start chatting with the Business GPT agent!

## API Endpoints

- **GET /** - Serves the HTML interface
- **POST /api/chat** - Processes chat messages
  - Request body: `{ "query": "Your message here" }`
  - Response: `{ "response": "Agent's response" }`

## Deployment

### Local Development

For local development, the application runs on `http://localhost:5000` by default.

### Server Deployment

To deploy to a server:

1. Configure environment variables:
   - `PORT`: The port to run the server on (default: 5000)
   - `FLASK_ENV`: Set to 'production' for production deployment

2. For production deployment, consider using a WSGI server like Gunicorn:
   ```
   pip install gunicorn
   gunicorn -w 4 app:app
   ```

3. For security, add SSL/TLS with a reverse proxy like Nginx.

## Customization

- Modify `index.html` to change the UI appearance
- Update `app.py` to add more API endpoints or features

## Troubleshooting

- If you encounter CORS issues, ensure the Flask-CORS extension is properly configured
- Check server logs for detailed error messages
- Verify that all environment variables required by BasicAgent are set 