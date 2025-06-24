import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
from langchain_community.document_loaders import UnstructuredURLLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain_groq import ChatGroq



# Load environment variables
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    raise ValueError("GROQ_API_KEY is not set in your .env file.")
os.environ["GROQ_API_KEY"] = groq_api_key

app = Flask(__name__)

CORS(app, supports_credentials=True, resources={r"/*": {"origins": ["http://localhost:5173","https://stock-predictor-peach.vercel.app"]}})
@app.route('/')
def home():
    return "RAG Flask Backend is running!"


def extract_links_from_html(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    links = set()
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if href.startswith('http'):
            links.add(href)
        elif href.startswith('/'):
            links.add(requests.compat.urljoin(base_url, href))
    return list(links)


@app.route('/process_url_query', methods=['POST'])
def ask():
    data = request.get_json()
    urls = data.get('urls')
    query = data.get('query')

    if not urls or not query:
        return jsonify({"error": "Missing 'urls' or 'query'"}), 400

    try:       
        all_urls = set(urls)
        linked_urls = set()
        # Extract links from main pages
        for url in urls:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    new_links = extract_links_from_html(response.text, url)
                    linked_urls.update(new_links[:5]) 
            except Exception as e:
                print(f"Error fetching links from {url}: {e}")
            
            
        all_urls.update(linked_urls)

        print('All URLs:', all_urls)

        loader = UnstructuredURLLoader(urls=list(all_urls))
        documents = loader.load()

        # Split text
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
        splits = splitter.split_documents(documents)

        # Embed and store in Chroma
        embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vectorstore = Chroma.from_documents(documents=splits, embedding=embedding)

        
        model = ChatGroq(
            temperature=0.7,
            model_name="llama3-8b-8192",
            groq_api_key=groq_api_key
        )

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
    

@app.route('/process_url_summary', methods=['POST'])
def summarize():
    try:
        data = request.get_json()
        urls = data.get('urls')
        
        if not urls or not isinstance(urls, list):
            return jsonify({"error": "Missing or invalid 'urls'"}), 400

        loader = UnstructuredURLLoader(urls=urls)
        documents = loader.load()

        if not documents:
            return jsonify({"error": "No content extracted from URLs."}), 400

        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
        splits = splitter.split_documents(documents)

        all_text = "\n\n".join([doc.page_content for doc in splits])
        if len(all_text) > 10000:
            all_text = all_text[:10000]

        model = ChatGroq(
            temperature=0.7,
            model_name="llama3-8b-8192",
            groq_api_key=groq_api_key
        )

        prompt = (
            "You are a helpful AI assistant. Your task is to summarize the following content in a well-organized and detailed manner.\n\n"
            "Please follow this structure:\n"
            "1. Start with a **brief paragraph summary** explaining the overall topic.\n"
            "2. Then provide a **detailed bullet-point breakdown** of key facts, data points, and takeaways.\n"
            "3. If applicable, format structured data into a **Markdown-style table**, using proper syntax (no trailing pipes)."
            "4. Keep the language formal and concise, suitable for readers who haven't seen the original article.\n"
            "5. Maintain the order of importance and relevance as found in the content.\n\n"
            "Here is the content to summarize:\n\n"
            f"{all_text}\n\n"
            "Now generate the structured summary following the above format."
        )


        response = model.invoke(prompt)

        return jsonify({"answer": response.content})

    except Exception as e:
        print("[ERROR]", str(e))
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
