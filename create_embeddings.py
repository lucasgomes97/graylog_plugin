
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

def embed_logs(log_texts, save_path="graylog_vector_index"):
    docs = [Document(page_content=log) for log in log_texts]

    embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = FAISS.from_documents(docs, embedding)

    # Salvar localmente
    vectorstore.save_local(save_path)

    return vectorstore

