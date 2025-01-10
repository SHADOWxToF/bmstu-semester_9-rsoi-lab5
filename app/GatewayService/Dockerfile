FROM python:3.10

WORKDIR /code

ARG bonus_service="bonuses"
ARG flight_service="flights"
ARG ticket_service="tickets"
ARG identity_provider="keycloak"

ENV BONUS_SERVICE=$bonus_service
ENV FLIGHT_SERVICE=$flight_service
ENV TICKET_SERVICE=$ticket_service
ENV IDENTITY_PROVIDER=$identity_provider

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app/GatewayService /code/app

CMD ["fastapi", "run", "app/main.py", "--port", "8080"]