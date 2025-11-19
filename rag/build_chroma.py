from langchain_community.document_loaders import PyPDFLoader
from dotenv import load_dotenv
load_dotenv("../.env")

file_path = "./azure-doc.pdf"
loader = PyPDFLoader(file_path, mode="single")
docs = loader.load()
print(len(docs))
docs[0].page_content

from langchain_text_splitters import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(
    separators=[r"\r?\n(?=\d+\.\s+)"],
    is_separator_regex=True,
    chunk_size=1,
    chunk_overlap=0,
)

all_splits = text_splitter.split_documents(docs)
print(f"Text Splits: {len(all_splits)}")

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

# embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

vectorstore = Chroma.from_documents(
    documents=all_splits,          # your 13 docs or chunks
    embedding=embeddings,          # your OpenAIEmbeddings instance
    persist_directory="../app/data/chroma_db"  # folder to persist locally
)

print(f"ChromaDB created!")

