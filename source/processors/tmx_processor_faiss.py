from queue import Empty
from bs4 import BeautifulSoup
from langchain_core.documents import Document
from dotenv import load_dotenv
import uuid
import os
from utils.config import get_faiss_ingestion_limit

ingestion_limit = get_faiss_ingestion_limit

def loadTMXFile(tmx_file):
    return BeautifulSoup(open(tmx_file), "lxml")

def loadTMXFileContent(tmx_markups):
    return BeautifulSoup(tmx_markups, "lxml")

def processTMXFile(tmx_data, tmx_file):
    tmx_soup=loadTMXFileContent(tmx_data)
    return loadDocuments(tmx_soup)
    

def loadDocuments(tmx_soup):
    documents = []

    tu_tags = tmx_soup.find_all("tu")

    for id,tu_tag in enumerate(tu_tags):
        rule_id = id
        tuv_tags = tu_tag.find_all("tuv")
        
        for tuv_tag in tuv_tags:
            lang = tuv_tag["xml:lang"]
            text = tuv_tag.find("seg").get_text()
            
            document = Document(page_content=text, metadata={"rule_id": rule_id, "lang": lang})
            
            documents.append(document)
    return documents


def loadEmbeddings(documents,embedding_modelId):
    import pickle
    from io import BytesIO
    from pathlib import Path
    from langchain.embeddings import BedrockEmbeddings
    from langchain_community.vectorstores import FAISS
    import boto3

    boto3_session=boto3.session.Session()
    bedrock_runtime = boto3_session.client("bedrock-runtime")

    # will be used to embed user queries
    query_embed_model = BedrockEmbeddings(
        model_id=embedding_modelId,
        client=bedrock_runtime,
    )

    # will be used to embed documents
    doc_embed_model = BedrockEmbeddings(
        model_id=embedding_modelId,
        client=bedrock_runtime,
    )

    if(embedding_modelId=="cohere.embed-multilingual-v3"):
        query_embed_model.model_kwargs={"input_type": "search_query"}
        doc_embed_model.model_kwargs={"input_type": "search_document", "truncate": "END"}

    #vector_store_file = "tmx_vec_db_"+embedding_modelId+".pkl"
    tmx_db = FAISS.from_documents(documents[:ingestion_limit], doc_embed_model)
    tmx_db.embedding_function = query_embed_model
#    pickle.dump(tmx_db.serialize_to_bytes(), open(vector_store_file, "wb"))
#    tmx_db = FAISS.deserialize_from_bytes(serialized=vector_db_buff.read(), embeddings=query_embed_model)
    return tmx_db

def populateRuleLanguageLookup(documents) :
    from collections import defaultdict
    rule_language_lookup = defaultdict(dict)
    for  docs in documents:
        rule_language_lookup[docs.metadata["rule_id"]].update({docs.metadata["lang"]: docs.page_content})
    return rule_language_lookup


def getExamples(source_lang,target_lang,rule_language_lookup,matching_rules):
    examples = []
    # loop first 10 in rule_language_lookup

    for rule in matching_rules:
        matching_rule = rule_language_lookup[rule.metadata["rule_id"]]
        if target_lang in matching_rule :
            #print(matching_rule[target_lang])
            example = {source_lang: rule.page_content, target_lang: rule_language_lookup[rule.metadata["rule_id"]][target_lang]}
            examples.append(example)
            #print(example)
    return examples


