from queue import Empty
from bs4 import BeautifulSoup
from langchain_core.documents import Document
from typing import Any
from dotenv import load_dotenv
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from opensearchpy.helpers import bulk
import boto3
import uuid
import os

load_dotenv()

host = os.getenv("HOST", default="localhost")
port = int(os.getenv("PORT", 443))
region = os.getenv("REGION", default="us-east-1")
service = 'aoss'
credentials = boto3.Session().get_credentials()
auth = AWSV4SignerAuth(credentials, region, service)
ingestion_limit = int(os.getenv("OSS_INGESTION_LIMIT", default=20))

client = OpenSearch(
        hosts=[{"host": host, "port": port}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=False,
        ssl_show_warn=False,
        connection_class=RequestsHttpConnection,
        timeout=30,
    )


def createIndex(index_name):
    client.indices.create(
            index_name,
            body={
                "mappings": {
                    "properties": {
                        "rule_id": {"type": "integer"},
                        "lang": {"type": "keyword"},
                        "text": {"type": "text"}
                    }
                }
            },
        )

def listIndices():
    indices = client.indices.get("*")
    return (list(indices.keys()))

def processTMXFile(tmx_data, index_name=None, metadata_tag=None, read_file=False):
    if not read_file:
        tmx_soup=loadTMXFileContent(tmx_data)
    else:
        tmx_soup=loadTMXFile(tmx_data)
    documents=parseDocuments(tmx_soup, ingestion_limit, metadata_tag)
    if index_name is None:
        index_name = os.path.splitext(tmx_data)[0].split("/")[-1]
    indexDocuments(documents, index_name)
    return index_name

def loadTMXFile(tmx_file):
    return BeautifulSoup(open(tmx_file), "lxml")

def loadTMXFileContent(tmx_markups):
    return BeautifulSoup(tmx_markups, "lxml")

def parseDocuments(tmx_soup, ingestion_limit, metadata_tag):
    documents = []
    tu_tags = tmx_soup.find_all("tu")

    for id, tu_tag in enumerate(tu_tags):
        if len(documents) >= ingestion_limit:
            break

        rule_id = id
        tuv_tags = tu_tag.find_all("tuv")

        for tuv_tag in tuv_tags:
            lang = tuv_tag["xml:lang"]
            text = tuv_tag.find("seg").get_text()

            document = {
                "rule_id": rule_id,
                "lang": lang,
                "text": text
            }
            documents.append(document)

    return documents

def indexDocuments(documents, index_name):
    data: Any = []
    i = 0

    if not client.indices.exists(index_name):
        createIndex(index_name)
    else:
        #delete index and recreate
        client.indices.delete(index=index_name)
        createIndex(index_name)

    for _id, document in enumerate(documents):
        data.append({"index": {"_index": index_name, "_id": _id}})
        data.append(document)
    
    bulk_data = [
        {"_index": index_name, "_id": i, "_source": doc} for i, doc in enumerate(documents)
    ]

    rc = bulk(client, bulk_data)
    return rc

def populateRuleLanguageLookup(documents):
    from collections import defaultdict
    rule_language_lookup = defaultdict(dict)
    for doc in documents:
        rule_language_lookup[doc["rule_id"]].update({doc["lang"]: doc["text"]})
    return rule_language_lookup


def loadExamples(source_lang,target_lang,rule_language_lookup):
    examples = []
    rule_list = list(rule_language_lookup.values())
    for rule in rule_list:
        if target_lang in rule and source_lang in rule:
            example = {source_lang: rule[source_lang], target_lang: rule[target_lang]}
            examples.append(example)
    return examples

def queryIndex(index_name: str):
    documents = []
    query_body = {"query": {"match_all": {}}}
    resp = client.search(index=index_name, body=query_body, size=100)
    for hit in resp["hits"]["hits"]:
        document = hit["_source"]
        documents.append(document)
    return documents

