# A2A Estate - AI-Powered Real Estate Search Application

A2A Estate is an AI-powered real estate search application that supports efficient home searching, from property search to commute time calculation and AI-based property recommendations.

## Features

- **Property Search**: Search by area, price, and room layout
- **Commute Time Calculation**: Real commute time and fare calculation using NAVITIME API
- **AI Chat**: Property consultation and recommendation features using Gemini API
- **Map Display**: Property location confirmation with Google Maps
- **User Authentication**: Secure login with Google OAuth

## Tech Stack

### Backend
- **Python 3.11+**
- **FastAPI**: Fast, type-safe web API framework
- **SQLAlchemy**: ORM library
- **PostgreSQL**: Main database
- **Uvicorn**: ASGI server

### Frontend
- **React 18**: UI library
- **TypeScript**: Type-safe JavaScript
- **Vite**: Fast build tool
- **Tailwind CSS**: Utility-first CSS framework
- **Tanstack Query**: Data fetching and caching

### External APIs
- **NAVITIME API**: Route search and reachable stations
- **Google Gemini API**: AI chat functionality
- **Google Maps API**: Map display
- **Google OAuth**: Authentication system

## Project Structure

```
a2a-estate/
├── app/                    # Backend API
│   ├── main.py            # FastAPI application
│   ├── database.py        # Database configuration
│   ├── models.py          # SQLAlchemy models
│   ├── routers/           # API routers
│   │   ├── properties.py  # Properties API
│   │   ├── stations.py    # Station info API
│   │   ├── chat.py        # AI chat API
│   │   └── auth.py        # Authentication API
│   └── services/          # Business logic
│       ├── navitime.py    # NAVITIME API client
│       └── gemini.py      # Gemini API client
├── frontend/              # Frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components
│   │   ├── services/      # API clients
│   │   └── types/         # TypeScript type definitions
│   ├── package.json
│   └── vite.config.ts
├── .gitignore
└── README.md
```

## Setup

### Development Environment

1. **Clone repository**
   ```bash
   git clone [repository-url]
   cd a2a-estate
   ```

2. **Set environment variables**
   Create a `.env` file in the project root with the following variables:
   ```env
   # API Keys
   RAPIDAPI_KEY=your_rapidapi_key_here

   # Database Configuration
   DATABASE_HOST=localhost
   DATABASE_NAME=a2a_estate_db
   DATABASE_USER=app_user
   DATABASE_PASSWORD=your_password

   # Google API Keys
   GOOGLE_MAPS_API_KEY=your_maps_api_key
   GOOGLE_CLIENT_ID=your_oauth_client_id
   GOOGLE_CLIENT_SECRET=your_oauth_client_secret

   # JWT Configuration
   JWT_SECRET_KEY=your_jwt_secret_key
   ```

3. **Install dependencies**

   Backend:
   ```bash
   cd app/
   pip install fastapi uvicorn sqlalchemy psycopg2-binary requests python-jose httpx
   ```

   Frontend:
   ```bash
   cd frontend/
   npm install
   ```

### API Key Setup

1. **NAVITIME API (RapidAPI)**
   - Create account at https://rapidapi.com/
   - Search and subscribe to Route Transit API
   - Copy the API key

2. **Google APIs**
   - Create project in Google Cloud Console
   - Enable Maps JavaScript API
   - Enable Gemini API (Vertex AI)
   - Create OAuth 2.0 credentials

## Development

### Backend Development

```bash
cd app/
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
cd frontend/
npm run dev
```

### Database Setup

```bash
# Create tables (first time only)
python -c "from app.database import create_tables; create_tables()"
```

## API Endpoints

### Property Search
- `GET /api/v1/properties/search` - Search properties
- `GET /api/v1/properties/{id}` - Property details

### Station Information
- `GET /api/v1/stations/lines` - List of train lines
- `GET /api/v1/stations/{line}` - Stations on a line
- `POST /api/v1/stations/commute-time` - Calculate commute time

### AI Chat
- `POST /api/v1/chat/message` - Send chat message
- `GET /api/v1/chat/history` - Chat history

### Authentication
- `GET /api/v1/auth/google/url` - Get Google auth URL
- `POST /api/v1/auth/google/callback` - Auth callback
- `GET /api/v1/auth/me` - Get user info

## Configuration Notes

- This is a demonstration/portfolio project
- API keys and secrets should be properly configured for production use
- Database setup may be required for full functionality
- Some features may require additional external service configuration
