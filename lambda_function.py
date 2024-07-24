import subprocess
import json
def lambda_handler(event, context):
    # Start Streamlit in the background
    process = subprocess.Popen(["streamlit", "run", "main.py"])
    
    # Wait for Streamlit to start (you may need to adjust the sleep time)
    import time
    time.sleep(50)
    
    # Get the public URL of the Lambda function
    url = f"https://{event['requestContext']['domainName']}{event['requestContext']['path']}"
    
    return {
        'statusCode': 200,
        'body': json.dumps(f'Streamlit app is running at {url}')
    }