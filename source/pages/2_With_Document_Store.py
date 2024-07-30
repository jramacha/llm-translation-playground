
from ast import Str
from calendar import prmonth
from math import exp
from sqlalchemy import true
import streamlit as st
import json
import boto3
import logging
import pandas as pd
from lxml import etree
import clipboard
from botocore.exceptions import ClientError
from sacrebleu.metrics import BLEU

from bedrock_apis import (
    invokeLLM,
    getPromptXml,
    converse,
    getPromptXml2,
)

from processors.tmx_processor_oss import (
    processTMXFile,
    queryIndex,
    listIndices,
    populateRuleLanguageLookup,
    loadExamples,
)

logger = logging.getLogger(__name__)

#Language Choices
LAN_CHOICES = {"EN": "English", "FR": "French", "ES": "Spanish", "DE": "German", "MLM":"Malayalam", "TML":"Tamil", "JP":"Japanese"}

#Translator Model Choices
MODEL_CHOICES = {
   "anthropic.claude-3-sonnet-20240229-v1:0": "Claude 3 Sonnet", 
   "anthropic.claude-3-haiku-20240307-v1:0": "Claude 3 Haiku", 
   "amazon.titan-text-premier-v1:0":"Amazon Titan Text Premier",
   "mistral.mistral-large-2402-v1:0": "Mistral", 
   "ai21.j2-ultra-v1":"Jurassic-2 Ultra",
   "cohere.command-r-plus-v1:0":"Cohere	Command R+",
   "meta.llama3-70b-instruct-v1:0":"Meta	Llama 3 70b Instruct"
}
bleu = BLEU()

def on_copy_click():
    # st.session_state.copied.append(text)
    if 'translated_text' in st.session_state:
      text = st.session_state['translated_text']
      clipboard.copy(text)

def populateExamplesXml(examplesRootElement, sl, tl): 
  if 'examples' in st.session_state :
    examples=st.session_state.examples
    for example in examples:
        exampleElement = etree.SubElement(examplesRootElement, 'example')
        source = etree.SubElement(exampleElement, 'source')
        source.text = example[sl]
        target = etree.SubElement(exampleElement, 'target')
        target.text = example[tl]
  

def loadRules(sl,tl):
  print(sl, tl)
  st.session_state.text2translate=text2translate
  st.session_state.sl=sl
  st.session_state.tl=tl
  examples = loadExamples(sl,tl,st.session_state.rule_language_lookup)
  st.session_state.examples=examples

def displayExamples(sl, tl):
  examples=st.session_state.examples
  exampleText=""
  for example in examples:
    exampleText+= example[sl] + " : "
    exampleText+= example[tl]+ "\n"
  return exampleText

def getExamplesDF(text2translate, sl, tl):
  if st.session_state.sl!=sl or st.session_state.tl!=tl or st.session_state.text2translate!=text2translate:
    loadRules(sl,tl)
  
  examples=st.session_state.examples
  columns = [LAN_CHOICES[sl],LAN_CHOICES[tl]]
  rows=[None]*len(examples)
  data=[None]*len(examples)
  for index, example in enumerate(examples):
    rows[index]=index+1
    data[index]=[example[sl],example[tl]]
  
  exampleDF = pd.DataFrame(data=data, index=rows, columns=columns)
  return exampleDF

def getExampleText(text2translate, sl, tl):
  exampleText=""
  if st.session_state.sl==sl and st.session_state.tl==tl and st.session_state.text2translate==text2translate:
    exampleText=displayExamples()
  else:
    loadRules(sl,tl)
    exampleText=displayExamples()

  return exampleText  


def dict_to_xml(examples):
    xml_out = ''
    # Split each line on a colon and print the result
    for line in examples:
        if ":" in line:
            parts = line.split(":", 1)
            xml_out += '\n<example> <source>'+parts[0]+'</source> <target>'+parts[1]+'</target> </example>'
    return xml_out




def getCustomExampleXmlElement(examplesRootElement,examples):
    for line in examples:
        if ":" in line:
            parts = line.split(":", 1)
            example = etree.SubElement(examplesRootElement, 'example')
            source = etree.SubElement(example, 'source')
            source.text = parts[0].strip()
            target = etree.SubElement(example, 'target')
            target.text = parts[1].strip()

    return examplesRootElement

def populateCustomExampleXml(custom_examples, examplesRootElement):
  if custom_examples.strip() != ""  :
    # Split the string on newlines
    lines = custom_examples.split("\n")
    getCustomExampleXmlElement(examplesRootElement,lines) 

def generateExamplesXML(custom_examples,sl,tl):
  examplesRootElement = etree.Element('examples')
  populateCustomExampleXml(custom_examples,examplesRootElement)
  populateExamplesXml(examplesRootElement,sl,tl)
  return examplesRootElement

def refresh_metrics():
   with st.sidebar:
    st.subheader("Metrics")
    if 'latency' in st.session_state:
      latency=st.session_state['latency']  
      st.metric(label="Latency", value=latency)
    if 'input_tokens' in st.session_state:
      input_tokens=st.session_state['input_tokens']  
      st.metric(label="Input Tokens", value=input_tokens)
    if 'output_tokens' in st.session_state:
      output_tokens=st.session_state['output_tokens']  
      st.metric(label="Input Tokens", value=output_tokens)
    if 'bleu' in st.session_state:
      bleu = st.session_state['bleu']
      if 'delta' in st.session_state['bleu']: st.metric(label="Translation score", value=str(round(bleu['score'], 2)), delta=str(round(bleu['delta'], 2)))
      else: st.metric(label="Translation score", value=str(round(bleu['score'], 2)))

def evaluate():
  print("Running Evaluation")
  #st.session_state['translated_text']
  if 'translated_text' in st.session_state and 'reference_text' in st.session_state:
    sys = st.session_state['translated_text'].split(".")
    refs = [st.session_state['reference_text'].split(".")]
    result = bleu.corpus_score(sys, refs)
    delta = None
    if 'bleu' in st.session_state:
       previous = st.session_state['bleu']['score']
       delta = result.score - previous
       st.session_state['bleu']['delta']=delta
    else:
       st.session_state['bleu'] = {}
    st.session_state['bleu']['score']=result.score
    refresh_metrics()

st.title("Language Translator with LLMs")
text2translate=st.text_area("Source Text")

col1, col2 = st.columns(2)

#Language Choices
with st.expander("Translation Choices",True):
  #st.header("Translation Choices")
  def format_func(option):
      return LAN_CHOICES[option]

  lcol1, lcol2 = st.columns(2)
  with lcol1:
    sl=st.selectbox("Select Source Language",options=list(LAN_CHOICES.keys()), format_func=format_func)
  with lcol2:
    tl=st.selectbox("Select Target Language",options=list(LAN_CHOICES.keys()), format_func=format_func)

  def format_func(option):
      return MODEL_CHOICES[option]
  model_id=st.selectbox("Select an LLM:",options=list(MODEL_CHOICES.keys()), format_func=format_func)
  
  st.text("Tune Model Parameters")
  tmcol1,tmcol2,tmcol3 = st.columns(3)
  with  tmcol1:
    max_seq_len = st.number_input('Max Tokens', value=2000)
  with  tmcol2:
    temperature = st.slider('Temperature', value=0.5, min_value=0.0, max_value=1.0)
  with  tmcol3:
     top_p = st.slider('top_p', value=0.95, min_value=0.0, max_value=1.0)

with st.expander("Prompt Configuration",False):
  systemPrompt=st.text_area("System Prompt","You are an expert language translator assistant for financial entrprise based in US. You will be given text in one language, and you need to translate it into another language. You should maintain the same tone, style, and meaning as the original text in your translation.")
  userPrompt =st.text_area("User Prompt","Translate the text in the input_text tag from SOURCE_LANGUAGE to TARGET_LANGUAGE. Use the examples provided in examples tag and apply matching examples to influence the translation output. Output only the exact translation.")

with st.expander("Translation customization"):
  egcol1, egcol2 = st.columns(2)
  with egcol1:
    list = ['No Index Selected']
    list.extend(listIndices())
    if len(list)>0:
      index_name = st.selectbox("Select a translation memory index", tuple(list),)
    st.divider()
    tmx_file = st.file_uploader("Upload a new TMX file", type=["tmx"])
    if tmx_file is not None:
        file_name = tmx_file.name
        st.write('You selected `%s`' % file_name)
        examples= []
        if st.button("Process TMX File"):
            tmx_data = tmx_file.getvalue()
            index_name=processTMXFile(tmx_file, file_name)
    if index_name is not None and index_name != "No Index Selected":
      documents=queryIndex(index_name)
      print(documents)
      rule_language_lookup=populateRuleLanguageLookup(documents)
      st.session_state.rule_language_lookup = rule_language_lookup
      st.session_state.tmx_loaded = True
      loadRules(sl,tl)

  with egcol2:
    #if st.button("Collect Matching Rules"):
    #    loadRules(sl,tl)
    custom_examples=st.text_area("Custom Examples: "+ LAN_CHOICES[sl] + " : " +LAN_CHOICES[tl] +"\n")
    st.write("One example pair per line seperated by colon (:). Example: Hello, how are you? : Hola, ¿cómo estás?")

df=None
if 'tmx_loaded' in st.session_state  and st.session_state.tmx_loaded == True:
  df=getExamplesDF(text2translate, sl, tl)

with st.expander("Translation pairs loaded from knowledge base",expanded=True):
    #st.table(df)
    if df is not None :
      st.markdown(df.to_html(escape=False), unsafe_allow_html=True)
      st.write(" ")

if st.button("Translate"):
  examplesXml=generateExamplesXML(custom_examples,sl,tl)
  prompt = getPromptXml2(LAN_CHOICES[sl],LAN_CHOICES[tl],text2translate,examplesXml, userPrompt, systemPrompt)
  with st.expander("Generated Prompt"):
     st.text_area("Prompt",prompt)
  response=converse(systemPrompt,prompt,model_id, max_seq_len, temperature,top_p)

  
  # Process and print the response
  #result = json.loads(response.get("body").read())
  st.session_state['input_tokens'] = response["usage"]["inputTokens"]
  st.session_state['output_tokens'] = response["usage"]["outputTokens"]
  st.session_state['latency']=response["metrics"]["latencyMs"]
  output_list = response["output"]["message"]["content"]

  print(f"- The model returned {len(output_list)} response(s):")
  for output in response.get("usage",[]):
      print(output)

  for output in output_list:
      print(output["text"])

  translated2Text = {
              output_list[0]["text"]
          }
  st.session_state['translated_text'] = output_list[0]["text"]
  if 'bleu' in st.session_state:
    st.session_state.pop("bleu")
  refresh_metrics()

with st.expander("Translation", expanded=True):
  egcol1, egcol2 = st.columns(2)
  with egcol1:
    if 'translated_text' in st.session_state:
      st.write(st.session_state['translated_text'])
      st.button("📋", on_click=on_copy_click, args=())
  with egcol2:
     st.write("Paste your reference " +LAN_CHOICES[tl] +" translation  below")
     st.session_state['reference_text']=st.text_area('')
     st.button("Evaluate", on_click=evaluate, args=())
  