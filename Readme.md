LLM Transaltion Play Ground

The Playground will help you to explore language translation capabilities using a wide array LLMs (Large Language model) available in bedrock. You can explore mutiple language options and its translation accuracy for different use cases. This playground enables you to attach your translation memory files to LLM to infleunce transaltion and assess the results.

The Steps to use

1. You can choose the language pair for transaltion.
2. Provide the text for translation.
3. Choose the LLM models from bedrock.
4. Upload your transaltion memory (TMX) File.
5. Choose your embedding model.
6. Process TMX file and store in Vector databse
7. And evaluate Examples picked by simiraltiy search that can influce transaltion.
8. Provide custom examples if required.

Steps to Build

1. Git Clone - <Link>
2. Update the Bedrock Connection details - Region, API_KEYS
3. 


Install
conda update conda -c conda-canary
conda config --set channel_priority flexible
conda create --name financialqaenv -c conda-forge python=3.10.6
conda activate financialqaenv

pip install --upgrade pip
pip install --upgrade -r requirements.txt