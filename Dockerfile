FROM python:3

COPY src/* src/

ADD requirements.txt .

RUN python3 -m pip install --upgrade pip
RUN pip install -r requirements.txt

WORKDIR /src

CMD ["python3", "bot.py"]