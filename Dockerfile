FROM python:3.9-alpine
LABEL org.opencontainers.image.source=https://github.com/Lovely-Development-Team/MottoBotto

COPY . .

RUN apk add --no-cache gcc musl-dev
RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python", "botto/run_botto.py" ]
