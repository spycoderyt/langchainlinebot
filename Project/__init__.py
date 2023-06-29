from .Config import *
import firebase_admin
from firebase_admin import credentials,storage,firestore
# Initialize Firebase
Firebase_secret_json = 'Project/langchainbot-e8599-firebase-adminsdk-jg4v5-fba15bcda8.json'
Firebase_url = 'langchainbot-e8599.appspot.com'
cred = credentials.Certificate(Firebase_secret_json)
firebase_admin.initialize_app(cred, {
    'storageBucket': Firebase_url,
})
db = firestore.client()

from flask import Flask,request,abort
import requests
import json
from Project.Config import *
import uncleengineer
app = Flask(__name__)
import openai
import logging
from linebot import LineBotApi
from datetime import datetime
import tempfile
import os
from langchain.memory import ConversationBufferMemory

from langchain.llms import OpenAI 
from langchain.embeddings import OpenAIEmbeddings
from langchain.chains import ConversationalRetrievalChain
from langchain.vectorstores import Chroma
from langchain.document_loaders import PyPDFLoader

#some global vars
qa = None
inchattext = "\n\nChat mode currently ON. Your API Key is being utilized. Send any message containing \"STOP\" to immediately discard your OpenAI API Key."
inchatmode = False
choosingfiles = False

@app.route('/webhook', methods=['POST','GET'])
def webhook():
    """
    Main webhook route, handles both POST and GET requests.
    For POST requests, it handles different types of messages like text and file.
    For GET requests, it simply returns a test response.
    """
    if request.method == 'POST':
        Reply = ""
        payload = request.json
        Reply_token = payload['events'][0]['replyToken']
        global choosingfiles
        logging.info(f"Received payload at {datetime.now()}: {payload}")
        line_id = payload['events'][0]['source']['userId']

        if payload['events'][0]['message']['type'] == "text":
            message = payload['events'][0]['message']['text']
            if ('EXIT' in message or 'STOP' in message) and choosingfiles:
                Reply = "File selection has been exited, and you can continue with your conversation. Type \"STOP\" or \"EXIT\" to exit the conversation altogether."
                ReplyMessage(Reply_token,Reply,Channel_access_token)
                choosingfiles = False
            elif choosingfiles:
                try:
                    HandleChooseFiles(payload) 
                    choosingfiles = False
                    
                except Exception as e:
                    Reply = "Please enter a valid sequence of comma-separated files or type \"STOP\" or \"EXIT\"."
                    ReplyMessage(Reply_token,Reply,Channel_access_token)
                    app.logger.error(e)
                    abort(400)
            else:
                try:
                    HandleText(payload)
                except Exception as e:
                    app.logger.error(e)
                    abort(400)
        elif payload['events'][0]['message']['type'] == 'file':
            api_key = get_openai_key(line_id)
            if api_key == None:
                Reply = "Please enter your OpenAI API Key before uploading files!"
                ReplyMessage(Reply_token,Reply,Channel_access_token)
            else:
                openai.api_key = api_key
                os.environ['OPENAI_API_KEY'] = api_key
                try:
                    HandleFile(payload)
                except Exception as e:
                    app.logger.error(e)
                    abort(400)
        return request.json, 200
    elif request.method == 'GET' :

        return 'this is method GET!!!' , 200
    else:
        abort(400)

@app.route('/')
def hello():
    """Default route, returns a test response. Can delete if ya want."""
    return 'hello world book',200
def is_pdf(file_path):
    """
    Checks if the given file is a PDF file.

    Parameters:
    file_path: The path to the file to check.

    Returns:
    True if the file is a PDF, False otherwise.
    """
    with open(file_path, 'rb') as f:
        return f.read(4) == b'%PDF'
def HandleFile(payload):
    """
    Handles files.
    The files are downloaded from Line servers and uploaded to Firebase.

    Parameters:
    payload: The payload received from Line servers.
    """
    line_id = payload['events'][0]['source']['userId']

    openai.api_key = get_openai_key(line_id)
    file_id = payload['events'][0]['message']['id']
    file_name = payload['events'][0]['message']['fileName']
    Reply_token = payload['events'][0]['replyToken']
    # Create a LineBotApi instance
    line_bot_api = LineBotApi(Channel_access_token)

    # Get the file content from Line servers
    message_content = line_bot_api.get_message_content(file_id)

    # Create a temporary file to store the content
    with open(file_name, 'wb') as temp_file:
        for chunk in message_content.iter_content():
            temp_file.write(chunk)
    if not is_pdf(file_name):
        print('The file is not a PDF.')
        return
    # After this, you should have the downloaded file in your local directory with the name as 'file_name'.
    
    # Now, you can upload the file to Firebase
    bucket = storage.bucket()
    blob = bucket.blob(file_name)
    blob.upload_from_filename(file_name)
    os.remove(file_name) 
    Reply = choose_files_for_chromadb()
    ReplyMessage(Reply_token,Reply,Channel_access_token)
def setup(store):
    """
    Setup function that prepares the ConversationalRetrievalChain object for conversational retrieval.

    Parameters:
    store: A vector store that is used to create the ConversationalRetrievalChain.
    """
    global qa
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    qa = ConversationalRetrievalChain.from_llm(OpenAI(model_name ="gpt-3.5-turbo-16k",temperature=1), store.as_retriever(), memory=memory,verbose = True)
def list_files(bucket):
    """
    List all files in the given Firebase bucket.

    Parameters:
    bucket: The Firebase bucket to list files from.

    Returns:
    A list of all file names in the bucket.
    """
    blobs = bucket.list_blobs()

    files = []
    for blob in blobs:
        files.append(blob.name)
    
    return files

def choose_files_for_chromadb():
    """
    Handles the interaction for choosing files for Chroma DB.

    Returns:
    A message indicating the files to choose from.
    """
    bucket = storage.bucket()
    files = list_files(bucket)
    Reply = "Here is a list of your files. Please continue uploading files or select files to be processed by send a message with the file numbers comma separated.\n\nExample: \"1,2,3,5,8\".\n\nFiles:\n"
    # Print all files with their indices
    for i, file_name in enumerate(files, start=1):
        Reply += (f"{i}. {file_name}\n")
    
    global choosingfiles
    choosingfiles = True
    Reply += "\n\nAlternatively, type \"STOP\" or \"EXIT\" in order to exit the file selection and return to normal conversation."
    return Reply
def HandleChooseFiles(payload):
    """
    Handles the user's choice of files for processing.

    Parameters:
    payload: The payload received from Line servers.
    """
    Reply_token = payload['events'][0]['replyToken']
    # Get the bucket instance
    bucket = storage.bucket()

    # Get the list of all files in the bucket
    files = list_files(bucket)

    # Get the file numbers from the payload
    file_numbers_text = payload['events'][0]['message']['text']

    # Convert the input into a list of integers
    file_numbers = list(map(int, file_numbers_text.split(',')))

    # Get the selected file names
    selected_files = [files[i-1] for i in file_numbers]
    cnt = 0
    
    # ReplyMessage(Reply_token,"starting to process files...",Channel_access_token)
    for file_name in selected_files:
        # Get the blob corresponding to the file name
        blob = bucket.blob(file_name)
        # Download the file content as bytes
        file_content = blob.download_as_bytes()

        # Write the content to a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name

        # Load and split the documents from the PDF file
        # ReplyMessage(Reply_token,f"{file_name} is being processed...",Channel_access_token)
        loader = PyPDFLoader(temp_file_path)
        docs = loader.load_and_split()

        # Create a Chroma instance from the documents
        if cnt == 0:
            store = Chroma.from_documents(docs, OpenAIEmbeddings())
        else:
            store.add_documents(docs)
        cnt+=1
    
    global choosingfiles
    choosingfiles = False
    ReplyMessage(Reply_token,"All files have been processed.\n\nEnter a query or type \"STOP\" or \"EXIT\" to exit the conversation.\n\nSend \"listfiles\" to list the files again.",Channel_access_token)
    setup(store)


def delete_file(file_number):
    """
    Deletes a file with the given number from Firebase bucket.

    Parameters:
    file_number: The number of the file to delete.

    Returns:
    A message indicating the result of the deletion.
    """
    # Get the bucket instance
    bucket = storage.bucket()

    # Get the list of all files in the bucket
    files = list_files(bucket)

    # Check if the file number is valid
    if file_number < 1 or file_number > len(files):
        return f"Invalid file number. Please enter a number between 1 and {len(files)}."

    # Get the file name from the list
    file_name = files[file_number - 1]

    # Create a blob for the file and delete it
    blob = bucket.blob(file_name)
    blob.delete()

    return f"The file {file_name} has been deleted."

def get_openai_key(line_user_id):
    """
    Fetches the OpenAI key for the given Line user ID.

    Parameters:
    line_user_id: The Line user ID to get the OpenAI key for.

    Returns:
    The OpenAI key if it exists, None otherwise.
    """

    # return os.environ['OPENAI_API_KEY'] #comment this out for actual use

    # uncomment everything below this for actual use
    doc_ref = db.collection('api_keys').document(line_user_id)
    doc = doc_ref.get()
    if doc.exists:
        api_key = doc.to_dict().get('openai_key')
        if api_key is not None:
            openai.api_key = api_key
            os.environ['OPENAI_API_KEY'] = api_key
            return doc.to_dict().get('openai_key')
        else:
            print("No such document!")
            return None
    else:
        print("No such document!")
        return None
def set_openai_key(line_user_id, openai_key):
    doc_ref = db.collection('api_keys').document(line_user_id)
    doc_ref.set({
        'openai_key': openai_key,
    })
def delete_openai_key(line_user_id):
    doc_ref = db.collection('api_keys').document(line_user_id)
    doc_ref.update({
        'openai_key': firestore.DELETE_FIELD,
    })

def HandleText(payload):
    """
    Handles the text type of messages in the payload.

    Parameters:
    payload: The payload received from Line servers.
    """
    Reply_token = payload['events'][0]['replyToken']
    print(Reply_token)
    message = payload['events'][0]['message']['text']
    print(message)
    line_id = payload['events'][0]['source']['userId']
    api_key = get_openai_key(line_id)
    global inchatmode

    if api_key is not None:
        openai.api_key = api_key
        inchatmode = True
    else:
        inchatmode = False
    if not inchatmode:  
        if message.lower().startswith("key:"):
            set_openai_key(line_id,message.split(':')[1])
            Reply = f"Great! Your OpenAI API Key,{message.split(':')[1]} has been recorded. \n\nChat mode is now ON. Send any message. If you want to stop, just send any message with the words \"STOP\" or \"EXIT\".\n\nIf you want a list of your files, send any message containing the phrase \"listfiles\".\n\nIf you want to delete a file, type \"delete:\" followed by the file number."
            inchatmode = True
        else:
            Reply ="Greetings from Gino\'s amazing Line Chatbot!\n\nPlease enter your openai key in this format:\"key:[OPENAI_API_KEY]\""
        
    else:
        query = message
        if 'STOP' in query or 'EXIT' in query:
            inchatmode = False
            openai.api_key = None
            global qa
            qa = None
            Reply = "Your OpenAI API Key has temporarily been discarded and the conversation has ended. To start the conversation again, simply type any message. To permamently remove you OpenAI API Key from the database, type \"REMOVE\".\n\nChat mode is temporarily OFF."
        elif 'REMOVE' in query:
            delete_openai_key(line_id)
            Reply = "Your OpenAI API Key has permanently been discarded. To start a conversation again, you must re-enter you OpenAI API Key in the format \"key:[OPENAI_API_KEY]\".\n\nChat mode is now OFF."
        elif message.lower().startswith("listfiles"):
            Reply = choose_files_for_chromadb()
        elif query.lower().startswith('delete:'):
            file_number_text = query.split(':')[1]
            try:
                file_number = int(file_number_text)
            except ValueError:
                Reply = "Invalid file number. Please enter a valid number."
            else:
                Reply = delete_file(file_number)
        else:
            ChatReply = [ {"role": "system", "content": "You are a intelligent assistant."} ]
            ChatReply.append(
                {"role": "user", "content": query},
            )
            if qa is None:
                try:
                    chat = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo", messages=ChatReply
                    )
                    Reply = chat.choices[0].message.content
                    Reply += inchattext
                except openai.OpenAIError as e:
                    app.logger.error(e)
                    Reply = "Your OpenAI API Key seems to be invalid. Please check it and try again. \n\nChat mode is now OFF."
                    inchatmode = False
            else:
                Reply = qa({"question":query})['answer']
                Reply += "\n\nYou are currently viewing files. Type \"STOP\" or \"EXIT\" to exit the file-viewing mode and return to normal GPT3."
    ReplyMessage(Reply_token, Reply, Channel_access_token)

def ReplyMessage(Reply_token, TextMessage, Line_Acees_Token):
    """
    Sends a reply message to the user using the LINE Messaging API.

    Parameters:
    Reply_token (str): The reply token associated with the event that the webhook is sending a reply to.
    TextMessage (str): The text message to be sent to the user.
    Line_Acees_Token (str): The Access Token of your LINE bot. 

    Returns:
    int: HTTP status code, 200 indicates the request has succeeded.
    """
    LINE_API = 'https://api.line.me/v2/bot/message/reply'

    Authorization = 'Bearer {}'.format(Line_Acees_Token) ##ที่ยาวๆ
    print(Authorization)
    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Authorization':Authorization
    }

    data = {
        "replyToken":Reply_token,
        "messages":[{
            "type":"text",
            "text":TextMessage
        }]
    }

    data = json.dumps(data) ## dump dict >> Json Object
    r = requests.post(LINE_API, headers=headers, data=data) 
    return 200