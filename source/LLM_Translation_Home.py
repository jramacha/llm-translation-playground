import streamlit as st
import json
from utils.ui_utils import ( 
    MODEL_CHOICES,
    loadLanguageChoices,
    getLanguageList,
    getDefaultLanguageMask,
)
from utils.bedrock_apis import (
    invokeLLM,
)
import pandas as pd
import base64
import streamlit as st
import base64

def format_func(option):
    return MODEL_CHOICES[option]

LOGO_IMAGE = "Arch_Amazon-Bedrock_64.png"

st.set_page_config(
    page_title="LLM Translation Playground",
    page_icon=":robot:",
    layout="wide"
)
st.markdown(
    """
    <style>
    .container {
        display: flex;
    }
    .logo-text {
        font-weight:300 !important;
        font-size:50px !important;
        color: #ffffff !important;
        padding-top: 40px !important;
        padding-left: 10px !important;
    }
    .logo-img {
        float:right;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    f"""
    <div class="container">
        <img class="logo-img" width="100" height="100" src="data:image/png;base64,{base64.b64encode(open(LOGO_IMAGE, "rb").read()).decode()}">
        <p class="logo-text">LLM Translation Playground</p>
    </div>
    """,
    unsafe_allow_html=True
)

url="https://aws.amazon.com/bedrock/"
st.subheader("Welcome to the LLM Machine Translation Playground! Powered by [Amazon Bedrock](%s)"% url)
with st.container(border=True):
    st.write("Placeholder for high level app description")

with st.expander("Supported Languages", True):
  user_lang_mask = None
  if "lang_mask" in  st.session_state:
     user_lang_mask = st.session_state['lang_mask']

  lang_list = loadLanguageChoices(lang_mask=user_lang_mask)
  lang_list_labels = ["{}-{}".format(code, lang_list[code]) for code in lang_list.keys()]
  
  main_list = getLanguageList()
  main_lang_list_labels = ["{}-{}".format(lang['LanguageCode'].upper(), lang['LanguageName']) for  lang in main_list]
  #print(main_lang_list_labels)
  #print(lang_list_labels)

  popover = st.popover("Configure Languages")
  selection = popover.multiselect("Languages", main_lang_list_labels, lang_list_labels)
  if selection is not None:
    new_lang_mask = [item.split("-")[0] for item in selection]
    new_lang_list = loadLanguageChoices(lang_mask=new_lang_mask)
    st.session_state['lang_mask'] = new_lang_mask
    st.session_state['lang_list'] = new_lang_list
  
    st.markdown(" ")
    lang_list_display = [[key, st.session_state['lang_list'][key]] for key in st.session_state['lang_list'].keys()]
    df = pd.DataFrame(lang_list_display, columns=["Code", "Name"])
    st.markdown(df.to_html(escape=False, index=False), unsafe_allow_html=True)
    st.markdown(" ")

with st.expander("Explore models"):
  model_id=st.selectbox("Select LLM models from Amazon Bedrock",options=list(MODEL_CHOICES.keys()), format_func=format_func)

  llm_q=st.text_area("Write your prompt")
  st.session_state.llm_q=llm_q

  st.text("Model Parameters")
  tmcol1,tmcol2,tmcol3 = st.columns(3)
  with  tmcol1:
    max_seq_len = st.number_input('Max Tokens', value=2000)
  with  tmcol2:
    temperature = st.slider('Temperature', value=0.5, min_value=0.0, max_value=1.0)
  with  tmcol3:
     top_p = st.slider('top_p', value=0.95, min_value=0.0, max_value=1.0)

  if st.button(MODEL_CHOICES[model_id]+" at Your Service"):
      response = invokeLLM(llm_q,model_id,max_seq_len,temperature,top_p)
      result = json.loads(response.get("body").read())
      output_list = result.get("content", [])
      st.write(output_list[0]["text"])
