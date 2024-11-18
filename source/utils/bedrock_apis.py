

import json
from queue import Empty
import boto3
import logging
from botocore.exceptions import ClientError
from click import prompt
from defusedxml import ElementTree as DET
from xml.etree import ElementTree as ET
from numpy import empty
from utils.refreshable_boto_session import get_refreshable_boto_session

logger = logging.getLogger(__name__)

session = get_refreshable_boto_session()
client = session.client("bedrock-runtime")
#client = boto3.client(service_name="bedrock-runtime", region_name="us-east-1")

DEFAULT_SYSTEM_PROMPT="You are an expert language translation assistant.\
    You will be given a text in one language, and you will translate it into a target language. You should maintain the same tone, style, and meaning as the original text in your translation."

DEFAULT_USER_PROMPT="Translate the text in the input_text tag from SOURCE_LANGUAGE to TARGET_LANGUAGE. Source language and target language can be found respectively in the source_language and target_language tags.\
    Use the examples provided in examples tag and apply respective examples to influence the translation output's tone and vocabulary.\
    User the custom terms in the custom_terminology tags as strict translation guidelines.\
    Only return the translated text."

def invokeLLM(llm_q,model_id,maxTokes,temperature,top_p):
  data = {
      "max_tokens": maxTokes,
      "messages": [
          {"role": "user", "content": llm_q}
      ],
      "anthropic_version": "bedrock-2023-05-31",
      "temperature": temperature
      ,"top_p": top_p
      }

  try:
    response = client.invoke_model(
        modelId=model_id,
        body=json.dumps(data),
    )
    return response

  except ClientError as err:
    logger.error(
        "Couldn't invoke %s. Here's why: %s: %s",
        model_id,
        err.response["Error"]["Code"],
        err.response["Error"]["Message"],
    )
    raise
  


def converse (system_prompt,llm_q,model_id,maxTokens,temperature,top_p):

    try:

        data = [{
           "role": "user", 
           "content":[{"text": llm_q}],
        }]
    
  
        inference_config = {
        "maxTokens": maxTokens,
        "temperature": temperature
        ,"topP": top_p
        }

        if(model_id=="amazon.titan-text-premier-v1:0" or model_id=="ai21.j2-ultra-v1"):
            response = client.converse(
            modelId=model_id,
            messages=data,
            inferenceConfig=inference_config )
        else:
            response = client.converse(
            modelId=model_id,
            messages=data,
            system=[{"text":system_prompt}],
            inferenceConfig=inference_config )



        return response

    except ClientError as err:
        logger.error(
            "Couldn't invoke %s. Here's why: %s: %s",
            model_id,
            err.response["Error"]["Code"],
            err.response["Error"]["Message"],
        )
        raise
   
   

def getPromptXml2(sl, tl, text2translate, examples_xml,userPrompt, systemPrompt, customTerminology):
    prompt=getXMLPromptTemplate2(sl,tl,text2translate,userPrompt, systemPrompt, customTerminology)
    data = { 'sl':sl, 'tl':tl, 'text2translate':text2translate,"userPrompt":userPrompt, "systemPrompt":systemPrompt, "customTerminology":customTerminology}
    xml_prompt = prompt%data 
    return appendExamples(xml_prompt,examples_xml)

def indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for subelem in elem:
            indent(subelem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def appendExamples(xml_prompt,examples_xml):
    if xml_prompt != '' :
        root = DET.fromstring(xml_prompt)
        root.append(examples_xml)
        indent(root)
        # Add the new element to the root
        xml_prompt=ET.tostring(root, encoding='utf-8', method='xml').decode('utf-8')

    return xml_prompt

def populateCustomExampleXml(custom_examples, examplesRootElement):
  if custom_examples.strip() != ""  :
    # Split the string on newlines
    lines = custom_examples.split("\n")
    getCustomExampleXmlElement(examplesRootElement,lines) 

def generateExamplesXML(custom_examples,sl,tl, session_state):
  examplesRootElement = ET.Element('examples')
  populateCustomExampleXml(custom_examples,examplesRootElement)
  populateExamplesXml(examplesRootElement, sl, tl, session_state)
  return examplesRootElement

def populateExamplesXml(examplesRootElement, sl, tl, session_state):
  if 'examples' in session_state :
    examples=session_state.examples
    for example in examples:
        exampleElement = ET.SubElement(examplesRootElement, 'example')
        source = ET.SubElement(exampleElement, 'source')
        source.text = example[sl]
        target = ET.SubElement(exampleElement, 'target')
        target.text = example[tl]

def getCustomExampleXmlElement(examplesRootElement,examples):
    for line in examples:
        if ":" in line:
            parts = line.split(":", 1)
            example = ET.SubElement(examplesRootElement, 'example')
            source = ET.SubElement(example, 'source')
            source.text = parts[0].strip()
            target = ET.SubElement(example, 'target')
            target.text = parts[1].strip()
    return examplesRootElement

def generateCustomTerminologyXml(customTermValue):
    if customTermValue is not None and customTermValue.strip() != "":
        pairs = customTermValue.split("\n")
        customTermRootElement = DET.fromstring('<custom_terminology/>')
        for line in pairs:
            if ":" in line:
                parts = line.split(":", 1)
                example = ET.SubElement(customTermRootElement, 'custom_term')
                source = ET.SubElement(example, 'source')
                source.text = parts[0].strip()
                target = ET.SubElement(example, 'target')
                target.text = parts[1].strip()
        return ET.tostring(customTermRootElement, pretty_print=True, encoding='utf-8').decode('utf-8')
    return ""

def getXMLPromptTemplate2(sl, tl, text2translate, userPrompt, systemPrompt, customTerminology):
    prompt="""
    <prompt>
    <system_instructions>
        %(systemPrompt)s
    </system_instructions>


    <source_language>
        <language_name>%(sl)s</language_name>
    </source_language>


    <target_language>
        <language_name>%(tl)s</language_name>
    </target_language>


    <input_text>
        %(text2translate)s
    </input_text>

    %(customTerminology)s
    
    <instructions>
        %(userPrompt)s
    </instructions>
    </prompt>
    """
    return prompt