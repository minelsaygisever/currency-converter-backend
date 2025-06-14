# Currency Converter API

![Python](https://img.shields.io/badge/Python-3.12-blue.svg)
![Framework](https://img.shields.io/badge/Framework-FastAPI-green.svg)
![Container](https://img.shields.io/badge/Container-Docker-blue.svg)
![Tests](https://img.shields.io/badge/Tests-Pytest-red.svg)

This project is a simple and effective RESTful API service that provides real-time exchange rate conversions between currencies. The project is built using modern Python technologies and backend development best practices, and it is fully containerized with Docker for easy setup and deployment.

## ✨ Features

-   **Real-time Currency Conversion:** Convert from a specified base currency to all other active currencies.
-   **List Active Currencies:** Returns all currency symbols that are registered and active in the system.
-   **Performance-Oriented Caching:** An in-memory cache mechanism with a 1-hour TTL (Time-To-Live) to reduce external API calls.
-   **Asynchronous Architecture:** High-performance, non-blocking structure thanks to `FastAPI` and `httpx`.
-   **Database Integration:** Uses `SQLModel` for storing and managing currency information in a database.
-   **Containerized:** Fully containerized with Docker and Docker Compose for a consistent development environment.
-   **Test Coverage:** Includes unit and integration tests written with `pytest`.

## 🛠️ Tech Stack

-   **Backend:** Python 3.12, FastAPI
-   **Database:** SQLite (with SQLModel ORM)
-   **Containerization:** Docker, Docker Compose
-   **Data Validation:** Pydantic
-   **Asynchronous HTTP Requests:** HTTPX
-   **Testing:** Pytest, pytest-mock, pytest-asyncio

## 📖 API Endpoints

All endpoints are prefixed with `/api/v1`.

### 1. Root / Health Check

-   **Endpoint:** `GET /`
-   **Description:** A simple health check to verify that the API is running.
-   **Sample Response:**
    ```json
    {
      "message": "Currency Converter API is up and running!"
    }
    ```

### 2. List Active Symbols

-   **Endpoint:** `GET /api/v1/currency/symbols`
-   **Description:** Lists all currencies marked as `active=True` in the database.
-   **Sample Response:**
    ```json
    [
      {
        "code": "USD",
        "name": "United States Dollar",
        "symbol": "$",
        "active": true,
        "flag_url": null,
        "decimal_places": 2
      }
    ]
    ```

### 3. Convert Currency

-   **Endpoint:** `GET /api/v1/currency/convert`
-   **Description:** Returns the current exchange rates from the currency specified in the `from` parameter to all other active currencies.
-   **Parameters:**
    -   `from` (required): The source currency code (e.g., `USD`).
-   **Sample Request:** `http://127.0.0.1:8000/api/v1/currency/convert?from=USD`
-   **Sample Response:**
    ```json
    {
      "from": "USD",
      "rates": [
        {
          "to": "EUR",
          "rate": 0.921504
        },
        {
          "to": "TRY",
          "rate": 32.258741
        }
      ]
    }
    ```