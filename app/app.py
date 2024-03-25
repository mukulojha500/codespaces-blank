import os
import sys
import json
import boto3
import streamlit as st
import shutil

from datetime import datetime

bucket_name = "learn-smart-rag"

## We will be suing Titan Embeddings Model To generate Embedding

from langchain_community.embeddings import BedrockEmbeddings
from langchain_community.chat_models import BedrockChat
from langchain.llms.bedrock import Bedrock

## Data Ingestion

import numpy as np
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFDirectoryLoader

# Vector Embedding And Vector Store

from langchain_community.vectorstores import FAISS

## LLm Models
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA

## Bedrock Clients
bedrock=boto3.client(service_name="bedrock-runtime")
bedrock_embeddings=BedrockEmbeddings(model_id="amazon.titan-embed-text-v1",client=bedrock)


## Data ingestion
def data_ingestion():
    loader=PyPDFDirectoryLoader("data")
    documents=loader.load()

    # - in our testing Character split works better with this PDF data set
    text_splitter=RecursiveCharacterTextSplitter(chunk_size=10000,
                                                 chunk_overlap=1000)
    
    docs=text_splitter.split_documents(documents)
    return docs

## Vector Embedding and vector store

def get_vector_store(docs):
    # Initialize S3 client
    s3_client = boto3.client('s3')

    # Create a temporary directory to save the embeddings
    tmp_dir = "/tmp/embeddings"
    os.makedirs(tmp_dir, exist_ok=True)

    # Generate embeddings and save them in the temporary directory
    vectorstore_faiss = FAISS.from_documents(docs, bedrock_embeddings)
    vectorstore_faiss.save_local(tmp_dir)

    # Upload embeddings to the S3 bucket
    for root, dirs, files in os.walk(tmp_dir):
        for file in files:
            local_path = os.path.join(root, file)
            s3_path = os.path.join(bucket_name, "embeddings", file)
            s3_client.upload_file(local_path, bucket_name, s3_path)

    # Clean up the temporary directory
    shutil.rmtree(tmp_dir)

    return vectorstore_faiss

def get_claude_llm():
    ##create the Anthropic Model
    # llm=Bedrock(model_id="anthropic.claude-v2:1",client=bedrock,
    #             model_kwargs={'max_tokens_to_sample':512})
    llm=BedrockChat(model_id="anthropic.claude-3-haiku-20240307-v1:0",client=bedrock,
                model_kwargs={'max_tokens':1000})
    
    return llm

# def get_llama2_llm():
#     ##create the Anthropic Model
#     llm=Bedrock(model_id="meta.llama2-70b-chat-v1",client=bedrock,
#                 model_kwargs={'max_gen_len':512})
    
#    return llm


prompt_template = """

Human: Use the following pieces of context to provide a 
concise answer to the question at the end but usse atleast summarize with 
250 words with detailed explaantions. If you don't know the answer, 
just say that you don't know, don't try to make up an answer.
<context>
{context}
</context

Question: {question}

Assistant:"""

PROMPT = PromptTemplate(
    template=prompt_template, input_variables=["context", "question"]
)

def get_response_llm(llm,vectorstore_faiss,query):
    qa = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vectorstore_faiss.as_retriever(
        search_type="similarity", search_kwargs={"k": 3}
    ),
    return_source_documents=True,
    chain_type_kwargs={"prompt": PROMPT}
)
    answer=qa({"query":query})
    return answer['result']

def save_chat_history(chat_history):
    # Initialize S3 client
    s3_client = boto3.client('s3')

    # Ensure the data directory exists
    if not os.path.exists('data'):
        os.makedirs('data')

    # Load existing chat history or initialize a new one
    existing_chat_history = []
    if os.path.exists('data/chats.json'):
        with open('data/chats.json', 'r') as f:
            existing_chat_history = json.load(f)

    # Append current chat history
    existing_chat_history.extend(chat_history)

    # Save the updated chat history to a JSON file
    with open('data/chats.json', 'w') as f:
        json.dump(existing_chat_history, f)
    
    # Convert the chat history to a JSON string
    chat_history_json = json.dumps(chat_history)

    # Save the chat history to a JSON file in the S3 bucket
    s3_client.put_object(
        Body=chat_history_json,
        Bucket=bucket_name,
        Key=os.path.join("learn-smart-rag/embeddings", "chats.json")
    )

def main():
    st.set_page_config("Learn Smart")
    
    st.title("Chat with PDF using Learn Smart💁")

    with st.sidebar:
        st.title("History will be shown here")

    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    st.header("Upload your PDF")
    uploaded_file = st.file_uploader("Upload a PDF file", type="pdf")
    if uploaded_file is not None:
        # Save the uploaded file to the data directory
        docs=data_ingestion()
        with open(os.path.join("data", "uploaded_file.pdf"), "wb") as f:
            f.write(uploaded_file.getvalue())    
        if st.button("Upload PDF"):
            with st.spinner("Processing PDF..."):
                docs = data_ingestion()
                faiss_index=get_vector_store(docs)
                st.success("Done")

        user_question = st.text_input("Ask a Question from the PDF Files")

        if st.button("Get answer"):
            with st.spinner("Processing..."):
                # Assuming you're using a function or method to load the pickle file
                faiss_index = FAISS.load_local("faiss_index", bedrock_embeddings, allow_dangerous_deserialization=True)

                llm=get_claude_llm()
                    
                faiss_index = get_vector_store(docs)
                response = get_response_llm(llm,faiss_index,user_question)
                st.session_state.chat_history.append({"prompt": user_question, "answer": response})
                st.write(response)
                st.success("Done")

        for chat in reversed(st.session_state.chat_history):
            st.write(f"User:\n {chat['prompt']}")
            st.write(f"Learn Smart:\n {chat['answer']}")   

        if st.button("End Chat"):
            save_chat_history(st.session_state.chat_history)
            st.session_state.chat_history = []
            st.write("Chat history saved. You can end the chat now.")

if __name__ == "__main__":
    main()