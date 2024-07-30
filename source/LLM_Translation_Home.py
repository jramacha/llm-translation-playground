import streamlit as st
import json
from bedrock_apis import (
    invokeLLM,
)

MODEL_CHOICES = {
   "anthropic.claude-3-sonnet-20240229-v1:0": "Claude 3 Sonnet", 
   "anthropic.claude-3-haiku-20240307-v1:0": "Claude 3 Haiku", 
   "amazon.titan-text-premier-v1:0":"Amazon Titan Text Premier",
   "mistral.mistral-large-2402-v1:0": "Mistral", 
   "ai21.j2-ultra-v1":"Jurassic-2 Ultra",
   "cohere.command-r-plus-v1:0":"Cohere	Command R+",
   "meta.llama3-70b-instruct-v1:0":"Meta	Llama 3 70b Instruct"
}

def format_func(option):
    return MODEL_CHOICES[option]

st.title("LLM Translation Playground")
st.write("Welcome to the LLM Translation Playground!")

with st.expander("Explore models", True):
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
