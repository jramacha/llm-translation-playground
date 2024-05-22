

import json
import boto3
import logging
from botocore.exceptions import ClientError
from click import prompt
from lxml import etree

logger = logging.getLogger(__name__)

client = boto3.client(
        service_name="bedrock-runtime", region_name="us-east-1"
    )

def invokeLLM(llm_q,model_id):
  data = {
      "max_tokens": 1000,
      "messages": [
          {"role": "user", "content": llm_q}
      ],
      "anthropic_version": "bedrock-2023-05-31"
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

def getXMLPromptTemplate(sl,tl,text2translate,custom_example_xml,example_xml):
    prompt="""
    <prompt>
    <system_instructions>
        You are an expert language translator assistant. You will be given text in one language, and you need to translate it into another language. You should maintain the same tone, style, and meaning as the original text in your translation.
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
        %(example_xml)s
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
        Translate the text in the input_text tag from SOURCE_LANGUAGE to TARGET_LANGUAGE. refer the examples provided in the Examples tag section  and apply translation rules specified in the translation_rules tag section after translation. Output only the exact translation.
    </instructions>
    </prompt>
    """
    
    return prompt