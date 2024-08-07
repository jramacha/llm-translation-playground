
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

from utils.bedrock_apis import (
    invokeLLM,
    converse,
    getPromptXml2,
    generateCustomTerminologyXml,
    generateExamplesXML,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_USER_PROMPT,
)

from processors.tmx_processor_oss import (
    processTMXFile,
    queryIndex,
    listIndices,
    populateRuleLanguageLookup,
    loadExamples,
)

from utils.ui_utils import (
    MODEL_CHOICES,
    loadLanguageChoices,
)

logger = logging.getLogger(__name__)

#Language Choices
#LAN_CHOICES = getLanguageChoices()

if "lang_list" not in st.session_state:
  st.session_state["lang_list"] = loadLanguageChoices()

bleu = BLEU()

def on_copy_click():
    # st.session_state.copied.append(text)
    if 'translated_text' in st.session_state:
      text = st.session_state['translated_text']
      clipboard.copy(text)

def getLanguageChoices():
  if "lang_list" not in st.session_state:
     current_lang_mask = None
     if "lang_mask" in st.session_state:
        current_lang_mask = st.session_state["lang_mask"]
        print("lang_mask", current_lang_mask)
     st.session_state["lang_list"] = loadLanguageChoices(lang_mask=current_lang_mask)
  print("lang_list", st.session_state["lang_list"])
  return st.session_state["lang_list"]

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
  columns = [getLanguageChoices()[sl],getLanguageChoices()[tl]]
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

def refresh_metrics():
   with st.sidebar:
    st.subheader("Metrics")
    if 'latency' in st.session_state:
      latency=st.session_state['latency']
      st.metric(label="Latency(ms)", value=f'{latency:,}')
    if 'input_tokens' in st.session_state:
      input_tokens=st.session_state['input_tokens']
      st.metric(label="Input Tokens", value=f'{input_tokens:,}')
    if 'output_tokens' in st.session_state:
      output_tokens=st.session_state['output_tokens']
      st.metric(label="Output Tokens", value=f'{output_tokens:,}')
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

def translate():
  examplesXml=generateExamplesXML(st.session_state['custom_examples'],sl,tl, st.session_state)
  customTermsXml=generateCustomTerminologyXml(st.session_state['custom_terms'])
  prompt = getPromptXml2(getLanguageChoices()[sl],getLanguageChoices()[tl],text2translate,examplesXml, userPrompt, systemPrompt, customTermsXml)
  st.session_state['prompt'] = prompt
  #response=invokeLLM(prompt,model_id)
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
  evaluate()

st.title("Language Translator with LLMs")
text2translate=st.text_area("Source Text")

col1, col2 = st.columns(2)

#Language Choices
with st.expander("Translation Configuration",True):
  #st.header("Translation Choices")
  def format_func(option):
      return getLanguageChoices()[option]

  lcol1, lcol2 = st.columns(2)
  with lcol1:
    sl=st.selectbox("Select Source Language",options=list(getLanguageChoices().keys()), format_func=format_func)
  with lcol2:
    tl=st.selectbox("Select Target Language",options=list(getLanguageChoices().keys()), format_func=format_func)

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
  translate_button=st.button("Translate", on_click=translate,args=())

with st.expander("Prompt Configuration",False):
  systemPrompt=st.text_area("System Prompt", DEFAULT_SYSTEM_PROMPT)
  userPrompt =st.text_area("User Prompt", DEFAULT_USER_PROMPT)

with st.expander("Translation Customization"):
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
            index_name=processTMXFile(tmx_data, file_name)
    if index_name is not None and index_name != "No Index Selected":
      documents=queryIndex(index_name)
      print(documents)
      rule_language_lookup=populateRuleLanguageLookup(documents)
      st.session_state.rule_language_lookup = rule_language_lookup
      st.session_state.tmx_loaded = True
      loadRules(sl,tl)

  with egcol2:
    custom_examples=st.text_area("Provide translation memory manually: "+ getLanguageChoices()[sl] + " : " +getLanguageChoices()[tl] +"\n")
    custom_terms=st.text_area("Provide custom terminology manually: "+ getLanguageChoices()[sl] + " : " +getLanguageChoices()[tl] +"\n")
    st.session_state['custom_examples']=custom_examples
    st.session_state['custom_terms']=custom_terms
    st.write("One language sample pair per line seperated by colon (:). Example: Hello, how are you? : Hola, ¿cómo estás?")

df=None
if 'tmx_loaded' in st.session_state  and st.session_state.tmx_loaded == True:
  df=getExamplesDF(text2translate, sl, tl)

with st.expander("Translation pairs loaded from knowledge base",expanded=True):
    #st.table(df)
    if df is not None :
      st.markdown(df.to_html(escape=False), unsafe_allow_html=True)
      st.write(" ")

with st.expander("Generated Prompt"):
     if 'prompt' in st.session_state:
      st.text_area("Prompt",st.session_state['prompt'])

if 'translated_text' in st.session_state:
  with st.expander("Translation", expanded=True):
    egcol1, egcol2 = st.columns(2)
    with egcol1:
      if 'translated_text' in st.session_state:
        st.write(st.session_state['translated_text'])
        bcol1, bcol2 = st.columns(2)
        with bcol1:
          st.button("✅ Evaluate", on_click=evaluate, args=())
        with bcol2:
          st.button("📋 Copy", on_click=on_copy_click, args=())
    with egcol2:
      st.write("Paste your reference " +getLanguageChoices()[tl] +" translation  below")
      st.session_state['reference_text']=st.text_area('')

refresh_metrics()