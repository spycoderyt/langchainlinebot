
# Talk To Your Documents (In Line!)

Documentation to help setup and run the Document Analysis Line Bot. The bot uses LangChain ConversationalRetrievalChain with ChromaDB and PyPDF2 to load, store, and analyze pdf files. Line API, OpenAI, Flask, and ngrok is used to create a Line Bot that can analyze PDF files.

# Prerequisites 
- Python 3.6 or later 
- OpenAI API key
- A Line account
- A Google account
# Setup directory
1. Create a virtual environment `python -m venv linebot`
2. Activate it:
   - Windows:`.\linebot\Scripts\activate`
   - Mac:  `source linebot/bin/activate`
3. Clone this repo: `git clone https://github.com/spycoderyt/langchainlinebot`
4. Go into the directory `cd langchainlinebot`
5. Install necessary Python packages using pip:  `pip install -r requirements.txt `
   - if ngrok doesn't seem to be working, just download it online and move the unzipped file to the `langchainlinebot` directory.
# Setup Line Bot
1. [Make a line bot](https://developers.line.biz/en/docs/messaging-api/building-bot/#setting-webhook-url)
2. Turn any auto-response messages off from https://manager.line.biz/
3. Turn on Webhook, turn off auto-reply messages from https://developers.line.biz/console/ in the Messaging API Section
4. Note the bot ID (Basic_ID) and Channel Access Token from https://developers.line.biz/console/ in the Messaging API section
5. Note the Channel Secret from https://developers.line.biz/console/ in the Basic Settings section
# Setup Firebase
Firebase is needed to store PDF files + OpenAI API Keys
1. Set up a Firebase project
2. Create a Firebase Storage and create a collection named `api_keys`
3. Create a Firestore Database and note the URL shown on the storage page, which is in the format `gs://[YOUR_PROJECT_NAME].appspot.com`
# Setup config file
1. Copy the example config file into a new file `copy Config.example > Config.py`
2. Fill in Channel_secret, Channel_access_token, and Basic_ID from the information in the Line Bot developer console https://developers.line.biz/console/ (Basic Settings + Messaging API)
3. Firebase Project > Project Settings > Service Accounts > Generate a New Private Key
4. Move the private key (.json file) into the Project folder of your directory 
5. Fill in FIREBASE_SECRET_JSON as the .json file's relative path
6. Fill in FIREBASE_URL as the URL from the storage page (should end in appspot.com)

# Startup 🚀
1. Activate the venv and navigate to the directory (see above) and setup ngrok with this command: `ngrok http 200`
2. ngrok should give you a link, and put this link in the https://developers.line.biz/ Messaging API section's Webhook URL. Make sure to add `/webhook` to the end of the URL. It should something like this: `  
https://7b97-110-170-208-162.ngrok-free.app/webhook`
3. In another terminal/cmd window, activate the venv and navigate to the directory again, then start the app `python app.py`
# Customization
- You can change the OpenAI GPT Model somewhere in the app.py file
- Feel free to send a pull request for bug fixes and adding additional features :)
# Next Steps 
- 24/7 Hosting from a server with Vercel / Heroku / Something Else
- Accurate Thai PDF reading (because PyPDF2 doesnt read Thai correctly)
    - [Someone seems to have fixed it with the tika-python library](https://stackoverflow.com/questions/50985619/how-to-read-pdf-files-which-are-in-asian-languages-chinese-japanese-thai-etc)
    - Some other alternatives?
- Make it be able to remember chat history
- Make it explicitly source what page and paragraph the chatbot gets the information from 
- Have a side-by-side interface of the PDF that highlights exactly where the chatbot gets the information from
- Support other file formats (.docx, .doc, .txt, etc.)
- Spreadsheet + SQL database insights
- Image analysis with tesseract / EasyOCR
# References  🔗
LC Chain used: [ConversationalRetrievalChain](https://python.langchain.com/en/latest/modules/chains/index_examples/chat_vector_db.html)

[Langchain Library](https://github.com/langchain/langchain)

[Line Bot Messaging API Documentation](https://developers.line.biz/en/docs/messaging-api/)

[OpenAI API](https://beta.openai.com/docs/)

# Info
👨🏾‍💻 Author: Jirat Chiaranaipanich

