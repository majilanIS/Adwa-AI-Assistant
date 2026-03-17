from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFDirectoryLoader
import os
import sys


sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from prompt import prompt


# Map each PDF filename to its Google Drive link
pdf_links = {
    "short historical note-2.pdf": "https://drive.google.com/file/d/17yCcBtWO840MSoW46_KmHr9bBkRekKVz/view?usp=sharing",
    "paulos_milkias_getachew_metaferia_the_battle_ofbook4you.pdf": "https://drive.google.com/file/d/1wBZsQa2Ja_3ParQh59YDKEZjWsOvGrKc/view?usp=sharing",
    "battle_of_adwa_overview.pdf": "https://drive.google.com/file/d/1o6BBKqGZHZCBkXSU-W3zNutGPGIe9L7S/view?usp=sharing",
    "short history about battle of Adwa.pdf": "https://drive.google.com/file/d/1KI3oSXPYsAoDmwyuogb-tKLmWYfK7sD8/view?usp=sharing",
    "The_Battle_of_Adwa_African_Victory_in_the_Age_of_Empire_Raymond.pdf": "https://drive.google.com/file/d/1okoxNtQgh8itpoTttLmu8F11W0AvWau1/view?usp=sharing"
}

loader = PyPDFDirectoryLoader("./data")
documents = loader.load()

# Attach the correct Google Drive link as metadata to each document
for doc in documents:
    filename = os.path.basename(doc.metadata.get("source", ""))
    if filename in pdf_links:
        doc.metadata["source"] = pdf_links[filename]

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)

chunks = splitter.split_documents(documents)

embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-base-en-v1.5"
)

vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="./adwa_db"
)

vectorstore.persist()

print("Vector database created successfully")


embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-base-en-v1.5"
)

vectorstore = Chroma(
    persist_directory="./adwa_db",
    embedding_function=embeddings
)

retriever = vectorstore.as_retriever(search_kwargs={"k":3})

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.1,
    api_key=groq_api_key
)

print("setup Completed!")
