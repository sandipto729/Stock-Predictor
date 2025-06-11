from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os

from langchain_community.document_loaders import UnstructuredURLLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.chat_models import init_chat_model

# Load environment variables
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    raise ValueError("GROQ_API_KEY is not set in your .env file.")
os.environ["GROQ_API_KEY"] = groq_api_key

app = Flask(__name__)

CORS(app, supports_credentials=True, resources={r"/*": {"origins": ["http://localhost:5173"]}})
@app.route('/')
def home():
    return "RAG Flask Backend is running!"

@app.route('/process_url', methods=['POST'])
def ask():
    data = request.get_json()
    urls = data.get('urls')
    query = data.get('query')

    if not urls or not query:
        return jsonify({"error": "Missing 'urls' or 'query'"}), 400

    try:
        # Load documents from URLs
        loader = UnstructuredURLLoader(urls=urls)
        documents = loader.load()

        # Split text
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
        splits = splitter.split_documents(documents)

        # Embed and store in Chroma
        embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vectorstore = Chroma.from_documents(documents=splits, embedding=embedding)

        # Initialize Groq model
        model = init_chat_model("llama3-8b-8192", model_provider="groq", temperature=0.7, api_key=groq_api_key)

        # Setup RAG chain
        retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
        qa = RetrievalQA.from_chain_type(
            llm=model,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True
        )

        result = qa({"query": query})
        sources = [doc.metadata.get("source", "unknown") for doc in result['source_documents']]

        return jsonify({
            "answer": result['result'],
            "sources": sources
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
