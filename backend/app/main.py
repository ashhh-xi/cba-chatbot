import os
from pathlib import Path
from typing import Dict, List, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq

# --------------------------
# Load environment variables
# --------------------------
load_dotenv()

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
INDEX_DIR = os.getenv("INDEX_DIR", "index")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

print("🔍 Environment check:")
print("EMBEDDING_MODEL:", EMBEDDING_MODEL)
print("INDEX_DIR:", INDEX_DIR)
print("Current working directory:", os.getcwd())

# --------------------------
# FastAPI app setup
# --------------------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------
# Globals
# --------------------------
_embeddings = None
_vectorstore = None
_conversations: Dict[str, list] = {}

# Groq client wrapper (LangChain)
groq_client = ChatGroq(
    api_key=GROQ_API_KEY,
    model="llama3-8b-8192",
)

# --------------------------
# Data models
# --------------------------
class ChatRequest(BaseModel):
    conversation_id: str
    query: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]


# --------------------------
# Embeddings
# --------------------------
def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
            print("✅ Embeddings model loaded successfully")
    return _embeddings


# --------------------------
# Vector Store
# --------------------------
def get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
    index_path = Path(INDEX_DIR)
        print(f"🔍 Looking for index at: {index_path.resolve()}")

        if not index_path.exists():
            raise RuntimeError(f"❌ Index directory not found: {index_path}")

        try:
            _vectorstore = FAISS.load_local(
                str(index_path),
                get_embeddings(),
                allow_dangerous_deserialization=True
            )
            print(f"✅ FAISS index loaded successfully with {_vectorstore.index.ntotal} documents")
        except Exception as e:
            print(f"⚠️ Warning: could not initialize FAISS index: {e}")
            raise RuntimeError(f"Failed to load FAISS index: {e}")
    return _vectorstore


# --------------------------
# Helpers
# --------------------------
def format_conversation_history(conversation_id: str, query: str, context: str) -> str:
    """
    Builds a structured prompt with history, user query, and context.
    Ensures answers come back in a natural readable format.
    """
    history = _conversations.get(conversation_id, [])
    history_text = "\n".join([f"User: {turn['user']}\nAI: {turn['ai']}" for turn in history])

    return (
        f"{history_text}\n"
        f"User: {query}\n\n"
        f"Context (from CBA documents):\n{context}\n\n"
        f"AI: You are a helpful CBA product assistant. Provide clear, structured responses about CBA products and services.\n\n"
        f"IMPORTANT FORMATTING RULES:\n"
        f"- Format responses naturally with paragraphs, bullet points, or numbered lists when it improves clarity.\n"
        f"- Avoid any Markdown symbols such as *, **, _, or +.\n"
        f"- Present product names followed by a dash (–) and description.\n"
        f"- Use a new line for each product or concept.\n"
        f"- Be concise and informative.\n"
        f"- Only mention products that are actually available based on the provided context.\n"
        f"- Respond in clean, readable plain text.\n"
    )


def clean_ai_response(response: str) -> str:
    """
    Clean up the AI response to remove any prompt instructions or formatting artifacts,
    while keeping paragraphs, bullets, and numbered points intact.
    """
    lines = response.split('\n')
    cleaned_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Skip lines that are clearly prompt instructions
        if any(phrase in line.lower() for phrase in [
            'styling instructions:', 'ai:', 'user:', 'context:', 
            'example format', 'respond naturally', 'choose the best format'
        ]):
            continue
        # Remove leftover Markdown symbols
        line = line.replace('*', '').replace('**', '').replace('_', '').replace('+', '')
        cleaned_lines.append(line)

    return '\n'.join(cleaned_lines).strip()


def generate_ai_response(conversation_id: str, query: str, context: str) -> str:
    try:
        if not GROQ_API_KEY:
            return "⚠️ No GROQ_API_KEY found. Please set it in your environment variables."

        prompt = format_conversation_history(conversation_id, query, context)
        response = groq_client.invoke(prompt)

        # Clean up the response
        cleaned_response = clean_ai_response(response.content.strip())

        return cleaned_response
    except Exception as e:
        print(f"❌ Error with Groq LLM: {e}")
        return "⚠️ I'm having trouble generating a response. Please try again later."


# --------------------------
# Routes
# --------------------------
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    vectorstore = get_vectorstore()

    # Search in FAISS
    docs = vectorstore.similarity_search(request.query, k=8)
    context = "\n".join([doc.page_content for doc in docs])
    sources = [doc.metadata for doc in docs]

    print(f"🔎 Found {len(docs)} relevant documents for query: '{request.query}'")

    # Generate answer
    answer = generate_ai_response(request.conversation_id, request.query, context)

    # Save conversation history
    if request.conversation_id not in _conversations:
        _conversations[request.conversation_id] = []
    _conversations[request.conversation_id].append({"user": request.query, "ai": answer})

    return ChatResponse(answer=answer, sources=sources)


@app.get("/")
async def root():
    return {"message": "CBA Product Chatbot (Groq-powered) is running 🚀"}


# --------------------------
# Startup
# --------------------------
if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting CBA Product Chatbot with Groq...")

    try:
        get_vectorstore()
    except Exception as e:
        print(f"⚠️ Warning: could not initialize FAISS index: {e}")

    uvicorn.run(app, host="0.0.0.0", port=8000)
