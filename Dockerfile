FROM python:3

ADD bot.py .
ADD guild_data.py .
ADD announcements_dit.py .
ADD requirements.txt .

RUN python3 -m pip install --upgrade pip
RUN pip install -r requirements.txt

CMD ["python3", "bot.py"]