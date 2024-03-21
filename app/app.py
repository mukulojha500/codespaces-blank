import os
import sys
import json
import boto3
import streamlit as st

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
    vectorstore_faiss=FAISS.from_documents(
        docs,
        bedrock_embeddings
    )
    vectorstore_faiss.save_local("faiss_index")

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


def main():
    st.set_page_config("Learn Smart")
    
    st.title("Chat with PDF using Learn Smart💁")


    # with st.sidebar:
    st.header("Upload your PDF")
    uploaded_file = st.file_uploader("Upload a PDF file", type="pdf")
    if uploaded_file is not None:
        # Save the uploaded file to the data directory
        with open(os.path.join("data", "uploaded_file.pdf"), "wb") as f:
            f.write(uploaded_file.getvalue())    
        if st.button("Vectors Update"):
            with st.spinner("Processing PDF..."):
                docs = data_ingestion()
                get_vector_store(docs)
                st.success("Done")

    user_question = st.text_input("Ask a Question from the PDF Files")

    if st.button("Get answer"):
        with st.spinner("Processing..."):
            # Assuming you're using a function or method to load the pickle file
            faiss_index = FAISS.load_local("faiss_index", bedrock_embeddings, allow_dangerous_deserialization=True)

            llm=get_claude_llm()
            
            #faiss_index = get_vector_store(docs)
            st.write(get_response_llm(llm,faiss_index,user_question))
            st.success("Done")

if __name__ == "__main__":
    main()