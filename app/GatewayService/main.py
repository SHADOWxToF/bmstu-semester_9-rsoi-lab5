from fastapi import *
from fastapi.responses import *
from fastapi.exceptions import RequestValidationError
from sqlmodel import *
from database import *
from typing import Annotated
from fastapi.encoders import jsonable_encoder
from contextlib import asynccontextmanager
import uvicorn
from multiprocessing import Process
import os
import requests
from http import HTTPStatus

# bonusesHost = "localhost:8050"
# flightsHost = "localhost:8060"
# ticketsHost = "localhost:8070"
# bonusesHost = "bonuses:8050"
# flightsHost = "flights:8060"
# ticketsHost = "tickets:8070"
bonusesHost = f'{os.environ["BONUS_SERVICE"]}:8050'
flightsHost = f'{os.environ["FLIGHT_SERVICE"]}:8060'
ticketsHost = f'{os.environ["TICKET_SERVICE"]}:8070'
bonusesAPI = f"{bonusesHost}/api/v1"
flightsAPI = f"{flightsHost}/api/v1"
ticketsAPI = f"{ticketsHost}/api/v1"

@asynccontextmanager
async def lifespan(app: FastAPI):
    requests.post(f"http://{flightsHost}/manage/init")
    requests.post(f"http://{bonusesHost}/manage/init")
    yield

app = FastAPI(lifespan=lifespan)


@app.get('/manage/health', status_code=200)
def get_persons():
    return


@app.get('/api/v1/flights', status_code=200)
def get_persons(page: int, size: int) -> PaginationResponse:
    response = requests.get(f"http://{flightsAPI}/flights", params={"page": page, "size": size})
    out: PaginationResponse = PaginationResponse(**response.json())
    if response.status_code == HTTPStatus.OK:
        return out
    else:
        return PaginationResponse(page=page, size=size, totalElements=0, items=[])



# - GET api/v1/flights?page=&size=
# ответ
# class PaginationResponse(SQLModel):
#     pass
# {
#   "page": 1,
#   "pageSize": 1,
#   "totalElements": 1,
#   "items": [
# class FlightResponse(SQLModel):
#     pass
#     {
#       "flightNumber": "AFL031",
#       "fromAirport": "Санкт-Петербург Пулково",
#       "toAirport": "Москва Шереметьево",
#       "date": "2021-10-08 20:00",
#       "price": 1500
#     }
#   ]
# }

@app.get('/api/v1/tickets', status_code=200)
def get_persons(x_user_name: str = Header()) -> list[TicketResponse]:
    response = requests.get(f"http://{ticketsAPI}/tickets/", params={"user_name": x_user_name})
    out = []
    if response.status_code == HTTPStatus.OK:
        tickets: list[TicketJSON] = [TicketJSON(**i) for i in response.json()]
        for ticket in tickets:
            response = requests.get(f"http://{flightsAPI}/flights/{ticket.flightNumber}")
            if response.status_code == HTTPStatus.OK:
                flight_json = response.json()
                out.append(TicketResponse(ticketUid=ticket.ticketUid, status=ticket.status, **flight_json))
    return out
# - GET api/v1/tickets
# заголовок X-User-Name
# ответ
# [
# class TicketResponse(SQLModel):
#     pass
#   {
#     "ticketUid": "049161bb-badd-4fa8-9d90-87c9a82b0668",
#     "flightNumber": "AFL031",
#     "fromAirport": "Санкт-Петербург Пулково",
#     "toAirport": "Москва Шереметьево",
#     "date": "2021-10-08 20:00",
#     "price": 1500,
#     "status": "PAID"
#   }
# ]
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request : Request, exc):
    return JSONResponse({"message": "what", "errors": exc.errors()[0]}, status_code=400)

@app.post('/api/v1/tickets', status_code=200)
def get_persons(ticketPurchaseRequest: TicketPurchaseRequest, x_user_name: str = Header()) -> TicketPurchaseResponse:
    response = requests.get(f"http://{flightsAPI}/flights/{ticketPurchaseRequest.flightNumber}")
    if response.status_code != HTTPStatus.OK:
        return JSONResponse(content={"message": "Flight not found"}, status_code=404)
    flight = FlightData(**response.json())
    response = requests.post(f"http://{ticketsAPI}/tickets/", json=jsonable_encoder(TicketDataJSON(username=x_user_name, flightNumber=ticketPurchaseRequest.flightNumber, price=ticketPurchaseRequest.price)))
    if response.status_code != HTTPStatus.CREATED:
        return JSONResponse(content={"message": "Error"}, status_code=500)
    ticket: TicketJSON = TicketJSON(**response.json())
    response = requests.post(f"http://{bonusesAPI}/bonuses/calculate_price", json=jsonable_encoder(CalculatePriceJSON(name=x_user_name, price=ticketPurchaseRequest.price, paidFromBalance=ticketPurchaseRequest.paidFromBalance, ticketUid=ticket.ticketUid)))
    if response.status_code != HTTPStatus.ACCEPTED:
        return JSONResponse(content={"message": "Error"}, status_code=500)
    payment: PaymentDataJSON = PaymentDataJSON(**response.json())

    response = requests.get(f"http://{bonusesAPI}/bonuses/{x_user_name}")
    if response.status_code != HTTPStatus.OK:
        return JSONResponse(content={"message": "Error"}, status_code=500)
    privilege = PrivilegeDataJSON(**response.json())
    
    return TicketPurchaseResponse(ticketUid=ticket.ticketUid,
                                  flightNumber=flight.flightNumber,
                                  fromAirport=flight.fromAirport,
                                  toAirport=flight.toAirport,
                                  date=flight.date,
                                  price=flight.price,
                                  paidByMoney=payment.paidByMoney,
                                  paidByBonuses=payment.paidByBonuses,
                                  status=ticket.status,
                                  privilege=privilege)
    
    
# - POST api/v1/tickets
# заголовок X-User-Name
# class TicketPurchaseRequest(SQLModel):
#     pass
# {
#   "flightNumber": "AFL031",
#   "price": 1500,
#   "paidFromBalance": true
# }
# ответ
# 200
# class TicketPurchaseResponse(SQLModel):
#     pass
# {
#   "ticketUid": "049161bb-badd-4fa8-9d90-87c9a82b0668",
#   "flightNumber": "AFL031",
#   "fromAirport": "Санкт-Петербург Пулково",
#   "toAirport": "Москва Шереметьево",
#   "date": "2021-10-08 20:00",
#   "price": 1500,
#   "paidByMoney": 1500,
#   "paidByBonuses": 0,
#   "status": "PAID",
#   "privilege": {
#     "balance": 1500,
#     "status": "GOLD"
#   }
# }
# 400
# {
#   "message": "string",
#   "errors": [
#     {
#       "field": "string",
#       "error": "string"
#     }
#   ]
# }

@app.get('/api/v1/tickets/{ticketUid}', status_code=200)
def get_persons(ticketUid: str, x_user_name: str = Header()) -> TicketResponse:
    response = requests.get(f"http://{ticketsAPI}/tickets/", params={"user_name": x_user_name})
    if response.status_code != HTTPStatus.OK:
        return JSONResponse(content={"message": "User not found"}, status_code=404)

    tickets: list[TicketJSON] = [TicketJSON(**i) for i in response.json()]
    for ticket in tickets:
        if ticket.ticketUid == ticketUid:
            response = requests.get(f"http://{flightsAPI}/flights/{ticket.flightNumber}")
            if response.status_code == HTTPStatus.OK:
                flight_json = response.json()
                return TicketResponse(ticketUid=ticket.ticketUid, status=ticket.status, **flight_json)
            else:
                return JSONResponse(content={"message": "Error"}, status_code=500)
    return JSONResponse(content={"message": "Ticket not found"}, status_code=404)
# - GET /api/v1/tickets/{ticketUid}
# заголовок X-User-Name
# query-param ticketUid
# 200
# {
#   "ticketUid": "049161bb-badd-4fa8-9d90-87c9a82b0668",
#   "flightNumber": "AFL031",
#   "fromAirport": "Санкт-Петербург Пулково",
#   "toAirport": "Москва Шереметьево",
#   "date": "2021-10-08 20:00",
#   "price": 1500,
#   "status": "PAID"
# }
# 404
# {
#   "message": "string"
# }

@app.delete('/api/v1/tickets/{ticketUid}', status_code=204)
def get_persons(ticketUid: str, x_user_name: str = Header()):
    response = requests.delete(f"http://{ticketsAPI}/tickets/{ticketUid}")
    if response.status_code == HTTPStatus.NOT_FOUND:
        return JSONResponse(content={"message": "Ticket not found"}, status_code=404)

    if response.status_code == HTTPStatus.OK:
        return

    response = requests.post(f"http://{bonusesAPI}/bonuses/cancel", json=jsonable_encoder(CancelTicketJSON(name=x_user_name, ticketUid=ticketUid)))
    if response.status_code != HTTPStatus.ACCEPTED:
        return JSONResponse(content={"message": "User or ticket not found"}, status_code=404)

# - DELETE /api/v1/tickets/{ticketUid}
# заголовок X-User-Name
# query-param ticketUid
# 204 возврат выполнен
# 404 билет не найден
# {
#   "message": "string"
# }

@app.get('/api/v1/me', status_code=200)
def get_persons(x_user_name: str = Header()) -> UserInfoResponse:
    response = requests.get(f"http://{ticketsAPI}/tickets/", params={"user_name": x_user_name})
    tickets = []
    if response.status_code == HTTPStatus.OK:
        rawTickets: list[TicketJSON] = [TicketJSON(**i) for i in response.json()]
        for ticket in rawTickets:
            response = requests.get(f"http://{flightsAPI}/flights/{ticket.flightNumber}")
            if response.status_code == HTTPStatus.OK:
                flight_json = response.json()
                tickets.append(TicketResponse(ticketUid=ticket.ticketUid, status=ticket.status, **flight_json))
    response = requests.get(f"http://{bonusesAPI}/bonuses/{x_user_name}")
    if response.status_code != HTTPStatus.OK:
        return JSONResponse({}, 200)
    return UserInfoResponse(tickets=tickets, privilege=PrivilegeDataJSON(**response.json()))
# - GET /api/v1/me
# заголовок X-User-Name
# 200
# class UserInfoResponse(SQLModel):
#     pass
# {
#   "tickets": [
#     {
#       "ticketUid": "049161bb-badd-4fa8-9d90-87c9a82b0668",
#       "flightNumber": "AFL031",
#       "fromAirport": "Санкт-Петербург Пулково",
#       "toAirport": "Москва Шереметьево",
#       "date": "2021-10-08 20:00",
#       "price": 1500,
#       "status": "PAID"
#     }
#   ],
#   "privilege": {
#     "balance": 1500,
#     "status": "GOLD"
#   }
# }

@app.get('/api/v1/privilege', status_code=200)
def get_persons(x_user_name: str = Header()) -> PrivilegeInfoResponse:
    response = requests.get(f"http://{bonusesAPI}/history/{x_user_name}")
    if response.status_code != HTTPStatus.OK:
        return JSONResponse({}, 200)
    return PrivilegeInfoResponse(**response.json())
# - GET /api/v1/privilege
# заголовок X-User-Name
# 200
# class PrivilegeInfoResponse(SQLModel):
#     pass
# {
#   "balance": 1500,
#   "status": "GOLD",
#   "history": [
#     {
#       "date": "2021-10-08T19:59:19Z",
#       "ticketUid": "049161bb-badd-4fa8-9d90-87c9a82b0668",
#       "balanceDiff": 1500,
#       "operationType": "FILL_IN_BALANCE"
#     }
#   ]
# }