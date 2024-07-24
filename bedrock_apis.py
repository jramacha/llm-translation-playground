

import json
from queue import Empty
import boto3
import logging
from botocore.exceptions import ClientError
from click import prompt
from lxml import etree
from numpy import empty

logger = logging.getLogger(__name__)

client = boto3.client(
        service_name="bedrock-runtime", region_name="us-east-1"
    )


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
   
   


def getPromptXml(sl, tl, text2translate, custom_example_xml, example_xml):
    prompt=getXMLPromptTemplate(sl,tl,text2translate,custom_example_xml,example_xml)
    data = { 'sl':sl, 'tl':tl, 'text2translate':text2translate , 'custom_example_xml':custom_example_xml , 'example_xml':example_xml}
    xml_prompt = prompt%data
    # Initialize the Amazon Bedrock runtime client
    
    xml=etree.fromstring(xml_prompt)
    pretty_xml=etree.tostring(xml, pretty_print=True).decode()
    print(pretty_xml)
    # Invoke Claude 3 with the text prompt
    return pretty_xml

def getPromptXml2(sl, tl, text2translate, examples_xml,userPrompt, systemPrompt):
    prompt=getXMLPromptTemplate2(sl,tl,text2translate,userPrompt, systemPrompt)
    data = { 'sl':sl, 'tl':tl, 'text2translate':text2translate,"userPrompt":userPrompt, "systemPrompt":systemPrompt }
    xml_prompt = prompt%data 
    return appendExamples(xml_prompt,examples_xml)


def appendExamples(xml_prompt,examples_xml):


    if xml_prompt != '' :
        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.fromstring(xml_prompt, parser=parser)
        root.append(examples_xml)


        # Add the new element to the root
        xml_prompt=etree.tostring(root, pretty_print=True, encoding='utf-8').decode('utf-8')

    print(xml_prompt)
    return xml_prompt

def getXMLPromptTemplate(sl,tl,text2translate,custom_example_xml,example_xml):
    prompt="""
    <prompt>
    <system_instructions>
        You are an expert language translator assistant for financial enterprise based in US. You will be given text in one language, and you need to translate it into another language. You should maintain the same tone, style, and meaning as the original text in your translation.
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


    <examples>
        %(custom_example_xml)s
    </examples>


    <translation_rules>
        <rule>
        <description>Translate product names literally</description>
        <data_map>
            <item>
            <source>language</source>
            <target>bhasha</target>
            </item>
        </data_map>
        </rule>
        <rule>
        <description>Translate company names literally</description>
        <data_map>
            <item>
            <source>MIS</source>
            <target>Ratings</target>
            </item>
            <item>
            <source>Moodys Investment Services</source>
            <target>Moodys Ratings</target>
            </item>
        </data_map>
        </rule>
    </translation_rules>


    <instructions>
        Translate the text in the input_text tag from SOURCE_LANGUAGE to TARGET_LANGUAGE. Use the examples provided in examples tag and apply matching examples to influence the translation output. Output only the exact translation.
    </instructions>
    </prompt>
    """
    
    return prompt


def getXMLPromptTemplate2(sl,tl,text2translate,userPrompt, systemPrompt):
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


    <translation_rules>
        <rule>
        <description>Translate product names literally</description>
        <data_map>
            <item>
            <source>language</source>
            <target>bhasha</target>
            </item>
        </data_map>
        </rule>
        <rule>
        <description>Translate company names literally</description>
        <data_map>
            <item>
            <source>MIS</source>
            <target>Ratings</target>
            </item>
            <item>
            <source>Moodys Investment Services</source>
            <target>Moodys Ratings</target>
            </item>
        </data_map>
        </rule>
    </translation_rules>


    <instructions>
        %(userPrompt)s
    </instructions>
    </prompt>
    """
    
    return prompt