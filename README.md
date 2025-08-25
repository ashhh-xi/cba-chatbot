# CBA Product Chatbot

A modern AI-powered chatbot for Commonwealth Bank of Australia (CBA) products and services, built with Next.js frontend and FastAPI backend.

## 🚀 Features

- **AI-Powered Responses**: Uses Groq LLM for intelligent product recommendations
- **Document Search**: FAISS vector search through CBA product documentation
- **Modern UI**: Beautiful, responsive chat interface with animations
- **Real-time Chat**: Live conversation with context awareness
- **Product Information**: Comprehensive coverage of CBA products, insurance, and services

## 🏗️ Architecture

- **Frontend**: Next.js 15.5.0 with TypeScript and Framer Motion
- **Backend**: FastAPI with Python 3.12
- **AI/ML**: Groq LLM API, FAISS vector database, HuggingFace embeddings
- **Styling**: Custom CSS with modern design principles

## 📁 Project Structure

```
cba-chatbot/
├── frontend/                 # Next.js frontend application
│   ├── src/
│   │   └── app/
│   │       ├── components/   # React components
│   │       ├── globals.css   # Global styles
│   │       ├── layout.tsx    # Root layout
│   │       └── page.tsx      # Main chat page
│   ├── package.json
│   └── tsconfig.json
├── backend/                  # FastAPI backend application
│   ├── app/
│   │   └── main.py          # Main FastAPI application
│   ├── data/                # Document storage
│   ├── index/               # FAISS vector index
│   ├── requirements.txt     # Python dependencies
│   └── env.example          # Environment variables template
├── scripts/                 # Utility scripts
└── README.md
```

## 🛠️ Installation

### Prerequisites

- Node.js 18+ and npm
- Python 3.12+
- Groq API key

### Backend Setup

1. **Navigate to backend directory:**
```bash
   cd cba-chatbot/backend
   ```

2. **Create virtual environment:**
```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp env.example .env
   # Edit .env and add your GROQ_API_KEY
   ```

5. **Start the backend server:**
```bash
   python app/main.py
   ```
   The backend will run on `http://localhost:8000`

### Frontend Setup

1. **Navigate to frontend directory:**
```bash
   cd cba-chatbot/frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start the development server:**
```bash
npm run dev
```
   The frontend will run on `http://localhost:3000`

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
GROQ_API_KEY=your_groq_api_key_here
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
INDEX_DIR=index
```

### API Endpoints

- `GET /` - Health check
- `POST /chat` - Chat endpoint
  - Body: `{"conversation_id": "string", "query": "string"}`
  - Response: `{"answer": "string", "sources": "array"}`

## 🎯 Usage

1. Open your browser and navigate to `http://localhost:3000`
2. Start chatting with the AI about CBA products
3. Ask questions like:
   - "What insurances do you provide?"
   - "Tell me about pet insurance"
   - "What are the fees for business accounts?"
   - "How do I apply for a home loan?"

## 🎨 Features

### AI Response Formatting
- Clean, structured responses
- Proper line breaks and formatting
- Bullet points and numbered lists
- XSS-safe rendering

### Chat Interface
- Real-time messaging
- Loading states
- Error handling
- Responsive design
- Smooth animations

### Document Search
- FAISS vector similarity search
- Context-aware responses
- Source attribution
- 12,950+ indexed documents

## 🔒 Security

- XSS protection in frontend rendering
- Environment variable protection
- Input sanitization
- Secure API communication

## 📦 Dependencies

### Backend
- `fastapi==0.111.0` - Web framework
- `uvicorn[standard]==0.30.1` - ASGI server
- `langchain-groq==0.3.7` - Groq LLM integration
- `faiss-cpu==1.8.0` - Vector similarity search
- `sentence-transformers==2.5.1` - Text embeddings

### Frontend
- `next==15.5.0` - React framework
- `react==19.1.1` - UI library
- `framer-motion==12.23.12` - Animations
- `lucide-react==0.541.0` - Icons

## 🚀 Deployment

### Backend Deployment
1. Set up environment variables on your server
2. Install Python dependencies
3. Run with uvicorn: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

### Frontend Deployment
1. Build the application: `npm run build`
2. Deploy to Vercel, Netlify, or your preferred platform
3. Update API endpoint URLs for production

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is for educational and demonstration purposes.

## 🙏 Acknowledgments

- Commonwealth Bank of Australia for product information
- Groq for fast LLM inference
- HuggingFace for embedding models
- FAISS for vector similarity search

## 📞 Support

For issues and questions, please open an issue on GitHub.

---

**Note**: This is a demonstration project and should not be used for production banking services without proper security reviews and compliance checks.
