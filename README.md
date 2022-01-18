# DIT-Announcements
Sends new announcements from https://www.di.uoa.gr/announcements to discord
<br>
<br>
You can invite the bot or install it to host it yourself. (instructions below)
<br>
Invite link: https://discord.com/api/oauth2/authorize?client_id=881568952378073149&permissions=27664&scope=bot
<br>

## Installation
For any method you will need an api key from discord.

### Local:

1. Clone the repository

```
git clone https://github.com/DanielPikilidis/DIT-Announcements.git DitAnnouncements
cd DitAnnouncements
```

2. Install required dependencies: 

`pip3 install -r requirements.txt`

3. Start the bot:

`python3 bot.py`

4. A new directory named "data" is now created. Paste your api key in the config.txt file inside that directory.

5. Start the bot again:

`python3 bot.py`

### Docker:

1. Clone the repository:

```
git clone https://github.com/DanielPikilidis/DIT-Announcements.git DitAnnouncements
cd DitAnnouncements
```

2. Build the Docker image:

`docker build -t {image name} .`

3. Create and start the container:

`docker run -d -v $(pwd)/data:/data -v $(pwd)/logs:/logs --name {container name} {image name}`

4. A new directory named "data" is now created. Paste your api key in the config.txt file inside that directory.

5. Restart the container: 

`docker start {container name}`
