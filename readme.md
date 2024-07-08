# ilab Chat Readme
*Hi there!* This is simply a 'convenience' project. I often find myself forgetting the errors I encounter in my chats with ilab, and sometimes these errors are not consistent. So, this is a quick fix tool intended to run locally, helping me save old chats and clear them once I'm done.
## Purpose
We currently utilize the command line to identify gaps in the model's knowledge, which led me to see the value in using a UI-based tool. I'm just leveraging the REST API that insructlab is already offering. 

This tool offers a user-friendly interface and retains history in your project folder until you choose to clear it, enhancing our ability to track and address these knowledge gaps efficiently.


## Changing the URLs

Please update the config.py file  
  - if your instructlab serve url has changed, change config.py - EXTERNAL_API_ROOT.
  - if the UI url is different, change CORS_ORIGINS
  - Change HOST and PORT as neded. _Note:_ On a mac, AirPlay Receiver may be running on port 5000. If you use port 5000 for this aoi you will likely see CPRS errors in the UI. This api currently runs on port 5001. 

## One-time

### Mac and Linux
```
python3 -m venv venv
source venv/bin/activate
pip3 install -r ./requirements.txt
```

### Windows
```
python -m venv venv
venv\Scripts\activate
pip install -r .\requirements.txt
```
## Run the server

### Mac and Linux
```
python3 app.py
```

### Windows 

```
python app.py
```
Note: This is not tested on Windows.

After launching the server, run the UI in the chat-ui project.
