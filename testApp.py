
import streamlit as st
import json,os
import boto3
import logging
from botocore.exceptions import ClientError
from tmxFileProcess import (
    processTMXFile,
    loadEmbeddings,
    getExamples,
    populateRuleLanguageLookup,
)

logger = logging.getLogger(__name__)


st.title("Language Translator with LLMs")
text2translate=st.text_area("Text To translate")

col1, col2 = st.columns(2)

#Language Choices
st.header("Translation options")
LAN_CHOICES = {"EN": "English", "FR": "French", "ES": "Spanish", "DE": "German"}
def format_func(option):
    return LAN_CHOICES[option]

lcol1, lcol2 = st.columns(2)
with lcol1:
  sl=st.selectbox("Select Source Language",options=list(LAN_CHOICES.keys()), format_func=format_func)
with lcol2:
  tl=st.selectbox("Select Target Language",options=list(LAN_CHOICES.keys()), format_func=format_func)

  

#Translator Model Choices
MODEL_CHOICES = {"anthropic.claude-3-sonnet-20240229-v1:0": "Claude 3 Sonnet", "anthropic.claude-3-haiku-20240307-v1:0": "Claude 3 Haiku", "mistral.mistral-large-2402-v1:0": "Mistral", "cohere.embed-multilingual-v3": "Cohere"}
def format_func(option):
    return MODEL_CHOICES[option]
model_id=st.selectbox("Select LLM models from Amazon Bedrock",options=list(MODEL_CHOICES.keys()), format_func=format_func)


st.header("Influence options")
#TMX Examples Files
filename = st.file_uploader("Upload a TMX file", type=["tmx"])
st.write('You selected `%s`' % filename)

#Embedding Model Choices
EMBED_CHOICES = {"amazon.titan-embed-text-v2:0": "Titan Embedding Text v2", "cohere.embed-multilingual-v3": "Cohere Multilingual", "cohere.embed-english-v3": "Cohere English"}

def format_func(option):
    return EMBED_CHOICES[option]

embedding_id=st.selectbox("Select Embedding models from Amazon Bedrock",options=list(EMBED_CHOICES.keys()), format_func=format_func)


def getExamplesXml(): 
    examples=st.session_state.examples
    xml_out = "\n"
    for example in examples:
        xml_out += f"<example>\n<source>{example[sl]}</source>\n<target>{example[tl]}</target>\n</example>\n"
    return xml_out

def loadRules(sl,tl):
  print(sl, tl)
  tmx_db=st.session_state.tmx_db
  matching_rules = tmx_db.similarity_search(text2translate, filter={"lang": sl})
  st.session_state.text2translate=text2translate
  st.session_state.sl=sl
  st.session_state.tl=tl
  st.session_state.matching_rules=matching_rules
  examples = getExamples(sl,tl,st.session_state.rule_language_lookup ,matching_rules)
  st.session_state.examples=examples

def displayExamples():
  examples=st.session_state.examples
  exampleText=""
  for example in examples:
    exampleText+= example[sl] + " : "
    exampleText+= example[tl]+ "\n"
  return exampleText



session_state = st.session_state
examples= []
egcol1, egcol2 = st.columns(2)
with egcol2:  
  if st.button("Process TMX File"):
    documents=processTMXFile(filename)
    tmx_db = loadEmbeddings(documents)
    st.session_state.tmx_db = tmx_db
    rule_language_lookup=populateRuleLanguageLookup(documents)
    st.session_state.rule_language_lookup = rule_language_lookup
    loadRules(sl,tl)
      
with egcol1:
    st.text("")


if st.button("Collect Matching Rules"):
    loadRules(sl,tl)

def getExampleText(text2translate, sl, tl):
  exampleText=""
  if st.session_state.sl==sl and st.session_state.tl==tl and st.session_state.text2translate==text2translate:
    exampleText=displayExamples()
  else:
    loadRules(sl,tl)
    exampleText=displayExamples()

  return exampleText  


st.text(getExampleText(text2translate, sl, tl))

example_xml=getExamplesXml()

custom_examples=st.text_area("Custom Examples: "+ LAN_CHOICES[sl] + " : " +LAN_CHOICES[tl] +"\n")
st.write("One example pair per line seperated by colon (:). Examples below")
st.write("Hello, how are you? : Hola, ¿cómo estás?")


def dict_to_xml(examples):
    xml_out = "\t\n"
    # Split each line on a colon and print the result
    for line in examples:
        if ":" in line:
            parts = line.split(":", 1)
            xml_out += f"<example>\n\t<source>{parts[0]}</source>\n\t<target>{parts[1]}</target>\n</example>\n"
    xml_out += "\n"
    return xml_out

custom_example_xml=""
if custom_examples.strip() != ""  :
  # Split the string on newlines
  lines = custom_examples.split("\n")
  custom_example_xml=dict_to_xml(lines)
  print(custom_example_xml)



prompt = """
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
          <source>MIS</source>
          <target>Ratings</target>
        </item>
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
          <source>Apple Inc.</source>
          <target>Apple Inc.</target>
        </item>
        <item>
          <source>Google LLC</source>
          <target>Google LLC</target>
        </item>
      </data_map>
    </rule>
  </translation_rules>


  <instructions>
    Translate the text in the <input_text> tags from {{SOURCE_LANGUAGE}} to {{TARGET_LANGUAGE}}. refer the examples provoded in the <Examples> section  and translation rules specified in the <translation_rules> section. Your translation should be enclosed in <translation></translation> tags.
  </instructions>
</prompt>
"""


client = boto3.client(
        service_name="bedrock-runtime", region_name="us-east-1"
    )

def invokeBedrock(sl, tl, text2translate,prompt):
    
    data = { 'sl':sl, 'tl':tl, 'text2translate':text2translate , 'custom_example_xml':custom_example_xml , 'example_xml':example_xml}
    xml_prompt = prompt%data
    
    # Initialize the Amazon Bedrock runtime client
    print(xml_prompt);
    # Invoke Claude 3 with the text prompt
    

    data = {
        "max_tokens": 1000,
        "messages": [
            {"role": "user", "content": xml_prompt}
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


if st.button("Translate"):
  response=invokeBedrock(sl,tl,text2translate,prompt);

  # Process and print the response
  result = json.loads(response.get("body").read())
  input_tokens = result["usage"]["input_tokens"]
  output_tokens = result["usage"]["output_tokens"]
  output_list = result.get("content", [])

  print("Invocation details:")
  print(f"- The input length is {input_tokens} tokens.")
  print(f"- The output length is {output_tokens} tokens.")

  print(f"- The model returned {len(output_list)} response(s):")
  for output in result.get("usage",[]):
      print(output)

  for output in output_list:
      print(output["text"])

  translated2Text = {    
              output_list[0]["text"]
          }
  st.write(translated2Text)

  st.write(f"- The input length is {input_tokens} tokens.")
  st.write(f"- The output length is {output_tokens} tokens.")

