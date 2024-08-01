
import json
import boto3

LANG_CHOICES = None

MODEL_CHOICES = {
   "anthropic.claude-3-sonnet-20240229-v1:0": "Claude 3 Sonnet",
   "anthropic.claude-3-haiku-20240307-v1:0": "Claude 3 Haiku",
   "amazon.titan-text-premier-v1:0":"Amazon Titan Text Premier",
   "mistral.mistral-large-2402-v1:0": "Mistral",
   "ai21.j2-ultra-v1":"Jurassic-2 Ultra",
   "cohere.command-r-plus-v1:0":"Cohere	Command R+",
   "meta.llama3-70b-instruct-v1:0":"Meta	Llama 3 70b Instruct"
}

#Function that loads the list of supported languages from the supported_lang.json file. Return the loaded json object
# The file has the following format 
# [
#    {
#        "name": "English",
#        "code": "en"
#    },
#    {
#        "name": "French",
#        "code": "fr"
# ]
def loadLanguageList():
    with open("utils/static-language-list.json", "r") as f:
        return json.load(f)

def getLanguageList():
    global LANG_CHOICES
    if LANG_CHOICES is None:
        LANG_CHOICES = loadLanguageList()
    return LANG_CHOICES

# Loads the supported languages configuration by matching languages in lang_mask_filename with the static LANG_CHOICES list.
# The mask file has the following format: {"lang-mask":["EN", "FR", "ES"],}
# Returns the filtered list in the following format: {"EN": "English", "FR": "French", "ES": "Spanish", "DE": "German", "MLM":"Malayalam", "TML":"Tamil", "JP":"Japanese"}
def loadLanguageChoices(lang_mask_filename='utils/language-mask-config.json', lang_mask=None):
    lang_choices = getLanguageList()
    if lang_mask is None:
        with open(lang_mask_filename, "r") as f:
            lang_mask_conf = json.load(f)
            lang_mask = lang_mask_conf["lang-mask"]

    #filtered_langs = [
    #    (item["LanguageCode"].upper(), item["LanguageName"])
    #    for item in LANG_CHOICES
    #    if item["LanguageCode"].upper() in lang_mask
    #]
    print("lang_mask", lang_mask)
    filtered_langs = {item["LanguageCode"].upper(): item["LanguageName"] for item in lang_choices if item["LanguageCode"].upper() in lang_mask}
    return filtered_langs

def getDefaultLanguageMask(lang_mask_filename='utils/language-mask-config.json'):
    with open(lang_mask_filename, "r") as f:
        lang_mask_conf = json.load(f)
        lang_mask = lang_mask_conf["lang-mask"]
        return lang_mask