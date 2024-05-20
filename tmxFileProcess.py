from bs4 import BeautifulSoup
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
import uuid



def loadTMXFile(tmx_file):
    return BeautifulSoup(open(tmx_file), "lxml")

def processTMXFile(tmx_file):
    #ToDo - Should be deleted 
    tmx_file = "assets/ECDC.tmx"

    tmx_soup=loadTMXFile(tmx_file)
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


def loadEmbeddings(documents):
    import pickle
    from io import BytesIO
    from pathlib import Path
    from langchain.embeddings import BedrockEmbeddings
    from langchain_community.vectorstores import FAISS
    import boto3

    boto3_session=boto3.session.Session()
    bedrock_runtime = boto3_session.client("bedrock-runtime")
    embedding_modelId = "cohere.embed-multilingual-v3"

    # will be used to embed user queries
    query_embed_model = BedrockEmbeddings(
        model_id=embedding_modelId,
        model_kwargs={"input_type": "search_query"},
        client=bedrock_runtime,
    )


    # will be used to embed documents
    doc_embed_model = BedrockEmbeddings(
        model_id=embedding_modelId,
        model_kwargs={"input_type": "search_document", "truncate": "END"},
        client=bedrock_runtime,
    )

    vector_store_file = "tmx_vec_db.pkl"
    CREATE_NEW = False # create new vector store if True or load existing one if False
    DOCS_TO_INDEX = 3000 # number of documents to index, this code does about 700 docs per minute and the are over 64K docs in the tmx file

    if CREATE_NEW:
        tmx_db = FAISS.from_documents(documents[:DOCS_TO_INDEX], doc_embed_model)
        tmx_db.embedding_function = query_embed_model
        pickle.dump(tmx_db.serialize_to_bytes(), open(vector_store_file, "wb"))
    else:
        if not Path(vector_store_file).exists():
            raise FileNotFoundError(f"Vector store file {vector_store_file} not found. Set CREATE_NEW to True to create a new vector store.")
        
        vector_db_buff = BytesIO(pickle.load(open(vector_store_file, "rb")))
        tmx_db = FAISS.deserialize_from_bytes(serialized=vector_db_buff.read(), embeddings=query_embed_model)

    return tmx_db




def populateRuleLanguageLookup(documents) :
    from collections import defaultdict
    rule_language_lookup = defaultdict(dict)
    for  docs in documents:
        rule_language_lookup[docs.metadata["rule_id"]].update({docs.metadata["lang"]: docs.page_content})
    return rule_language_lookup


def getExamples(source_lang,target_lang,rule_language_lookup,matching_rules):
    examples = []
    print(len(matching_rules))
    print(len(rule_language_lookup))
    # loop first 10 in rule_language_lookup

    for rule in matching_rules:
        example = {source_lang: rule.page_content, target_lang: rule_language_lookup[rule.metadata["rule_id"]][target_lang]}
        examples.append(example)
        print(example)
    return examples

