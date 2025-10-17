# Currency Converter API

![Python](https://img.shields.io/badge/Python-3.12-blue.svg)
![Framework](https://img.shields.io/badge/Framework-FastAPI-green.svg)
![Container](https://img.shields.io/badge/Container-Docker-blue.svg)
![Deployment](https://img.shields.io/badge/Deployment-AWS_ECS-orange.svg)

This project is a simple and effective RESTful API service that provides real-time exchange rate conversions between currencies. The project is built using modern Python technologies and backend development best practices, and it is fully containerized with Docker for easy setup and deployment.

## ✨ Features

-   **Real-time Exchange Rates:** Get up-to-date conversion rates from a specified base currency to all other active currencies.
-   **List Active Currencies:** Returns a full list of currency symbols that are registered and active in the system.
-   **Secure API Endpoints:** All endpoints are protected via a mandatory `X-API-KEY` header to prevent unauthorized access.
-   **Per-Device Rate Limiting:** Protects the API from abuse by limiting the number of requests per device, tracked via an `X-Device-ID` header.
-   **High-Performance Caching:** Utilizes **Redis** for caching external API responses, significantly reducing latency and dependency on third-party services.
-   **Asynchronous Architecture:** High-performance, non-blocking structure thanks to `FastAPI` and `httpx`.
-   **Database Integration:** Uses `SQLModel` for storing and managing currency information.
-   **Containerized:** Fully containerized with Docker for a consistent development and deployment environment.
-   **Historical Rate Data:** Provides historical currency rate data for various time ranges (e.g., 1 day, 1 week, 1 year) with automatic data aggregation for performance.
-   **Automated Data Collection:** Utilizes AWS EventBridge to trigger scheduled background jobs that reliably fetch and store historical currency rates.
-   **Personal Savings Tracking (CRUD):** Allows users to create, read, update, and delete their personal savings entries.
-   **Subscription-Based Limits:** Integrates with RevenueCat to manage user access, offering different usage limits for free and pro-tier users.
-   **Secure User Data Migration:** Supports a secure data migration path for users changing devices, validated against RevenueCat aliases.

## 🛠️ Tech Stack

-   **Backend:** Python 3.12, FastAPI
-   **Database:** PostgreSQL (Production on AWS RDS)
-   **Caching / In-Memory Database:** Redis (Production on AWS ElastiCache)
-   **Cloud & Deployment:** AWS ECS (Fargate), AWS ECR, Docker, AWS EventBridge for Scheduled Tasks
-   **Data Validation:** Pydantic
-   **Asynchronous HTTP Requests:** HTTPX
-   **Subscription Management:** RevenueCat
-   **Testing:** Pytest, pytest-mock, pytest-asyncio

## 🔄 CI/CD - Continuous Integration & Deployment
This project utilizes GitHub Actions for fully automated CI/CD pipelines for two separate environments.

-   **Test Environment:** Every push to the develop branch automatically builds, tests (if tests are added), and deploys the application to the AWS ECS test environment.
-   **Production Environment:** Merging changes from develop into the main branch triggers a deployment to the production environment on AWS ECS.

All deployments are managed via Infrastructure as Code principles using task definition files stored within this repository.

## ⏳ Scheduled Jobs
To ensure historical data is collected reliably and consistently, the API uses a decoupled, event-driven architecture powered by **AWS EventBridge**. These jobs run independently of user API requests.

-   ### Hourly Job
    -   **Trigger:** Runs every hour (`cron(0 * * * ? *)`).
    -   **Responsibilities:**
        1.  Fetches the latest currency rates from the external OpenExchangeRates API.
        2.  If the API call fails, it **forward-fills** the data using the last successful snapshot to ensure data continuity.
        3.  Saves the data as an `hourly` snapshot in the `currency_rate_snapshots` table.
        4.  Updates the primary `latest_usd_rates` key in the Redis cache with a 55-minute TTL.
        5.  Deletes hourly snapshots older than 30 days to manage database size.

-   ### Daily Job
    -   **Trigger:** Runs once a day (e.g., at 00:05 UTC).
    -   **Responsibilities:**
        1.  Finds the last available `hourly` snapshot from the previous day.
        2.  Creates a single, consolidated `daily` snapshot for that day. This is used to efficiently serve data for longer time ranges (e.g., 1 year, 5 years).

## 📖 API Endpoints

All endpoints are prefixed with `/api/v1`.

### Currency Endpoints

#### 1. Root / Health Check

-   **Endpoint:** `GET /`
-   **Description:** A simple health check to verify that the API is running.
-   **Sample Response:**
    ```json
    {
      "message": "Currency Converter API is up and running!"
    }
    ```

#### 2. List Active Symbols

-   **Endpoint:** `GET /currency-converter/v1/currencies`
-   **Description:** Lists all currencies marked as `active=True` in the database.
-   **Headers:**
    -   `X-API-KEY` (required): The secret API key for authentication.
    -   `X-Device-ID` (required): The unique identifier for the client device.
-   **Sample Response:**
    ```json
    [
      {
        "code": "USD",
        "name": "United States Dollar",
        "symbol": "$",
        "flag_url": "https://.../USD.png",
        "decimal_places": 2,
        "quick_rates": true,
        "quick_rates_order": 1
      },
      {
        "code": "TRY",
        "name": "Turkish Lira",
        "symbol": "₺",
        "flag_url": "https://.../TRY.png",
        "decimal_places": 2,
        "quick_rates": true,
        "quick_rates_order": 3
      },
      ...
    ]
    ```

#### 3. Convert Currency

-   **Endpoint:** `GET /currency-converter/v1/rates`
-   **Description:** Returns the current exchange rates from the currency specified in the `from` parameter to all other active currencies.
-   **Headers:**
    -   `X-API-KEY` (required): The secret API key for authentication.
    -   `X-Device-ID` (required): The unique identifier for the client device.
-   **Parameters:**
    -   `from` (required): The source currency code (e.g., `USD`).
-   **Sample Request:** `https://api.minelsaygisever.com/currency-converter/v1/rates?from=USD`
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
        },
        ...
      ]
    }
    ```


### **History Endpoints**

All endpoints are prefixed with `/api/v1/history`.

#### **4. Get Historical Rates**

-   **Endpoint:** `GET /history`
-   **Description:** Provides a list of historical rate snapshots against USD for a given time range. The data is automatically aggregated for longer ranges to reduce payload size and improve performance.
-   **Headers:**
    -   `X-API-KEY` (required)
-   **Parameters:**
    -   `range` (required): The time range. Supported values: `1d`, `1w`, `1m`, `6m`, `1y`, `5y`.
-   **Sample Request:** `https://api.minelsaygisever.com/api/v1/history?range=1w`
-   **Sample Response (`range=1w`):**
    ```json
    [
      {
        "effective_at": "2025-10-17T08:00:00Z",
        "rates": { "TRY": 32.5, "EUR": 0.92, "GBP": 0.81 }
      },
      ...
    ]
    ```

#### **5. Get Rate on a Specific Date**

-   **Endpoint:** `GET /history/rate-on-date`
-   **Description:** Returns the saved exchange rates for a specific historical date based on the daily snapshot.
-   **Headers:**
    -   `X-API-KEY` (required)
-   **Parameters:**
    -   `date` (required): Date in `YYYY-MM-DD` format.
-   **Sample Request:** `https://api.minelsaygisever.com/api/v1/history/rate-on-date?date=2025-10-16`
-   **Sample Response:**
    ```json
    {
      "rates": {
        "AED": 3.6729,
        "TRY": 32.45,
        "USD": 1,
        ...
      }
    }
    ```


### **Savings Endpoints**

These endpoints allow for CRUD operations on a user's personal savings entries. **User identification is handled via the `X-App-User-ID` header, which should contain the user's unique RevenueCat App User ID.**

All endpoints are prefixed with `/api/v1/savings`.

#### **6. Get All Savings Entries**

-   **Endpoint:** `GET /`
-   **Description:** Retrieves all savings entries for the specified user.
-   **Headers:**
    -   `X-API-KEY` (required)
    -   `X-App-User-ID` (required): The user's RevenueCat ID.
-   **Sample Response:**
    ```json
    [
      {
        "id": "c7a3c3e2-b1e1-4e3e-8c1c-1b1b1b1b1b1b",
        "currency_code": "USD",
        "amount": 1500.50,
        "purchase_date": "2025-08-20",
        "created_at": "2025-10-17T18:30:00Z",
        "updated_at": "2025-10-17T18:30:00Z"
      },
      ...
    ]
    ```

#### **7. Create a Savings Entry**

-   **Endpoint:** `POST /`
-   **Description:** Adds a new savings entry for the user. The API checks the user's subscription status (via RevenueCat) and enforces limits (1 for free users, 200 for pro users). Also supports data migration.
-   **Headers:**
    -   `X-API-KEY` (required)
    -   `X-App-User-ID` (required)
-   **Request Body:**
    ```json
    {
      "currency_code": "EUR",
      "amount": 500,
      "purchase_date": "2025-10-17"
    }
    ```
-   **Migration Request Body:**
    ```json
    {
      "currency_code": "EUR",
      "amount": 500,
      "purchase_date": "2025-10-17",
      "is_migration": true,
      "previous_user_id": "old_rc_user_id_abc"
    }
    ```

#### **8. Update a Savings Entry**

-   **Endpoint:** `PUT /{entry_id}`
-   **Description:** Updates an existing savings entry. The user can only update their own entries.
-   **Headers:**
    -   `X-API-KEY` (required)
    -   `X-App-User-ID` (required)
-   **Request Body:**
    ```json
    {
      "amount": 550.75
    }
    ```

#### **9. Delete a Savings Entry**

-   **Endpoint:** `DELETE /{entry_id}`
-   **Description:** Deletes a specific savings entry. The user can only delete their own entries.
-   **Headers:**
    -   `X-API-KEY` (required)
    -   `X-App-User-ID` (required)
-   **Response:** `204 No Content` on success.


### **Admin Endpoints**

These endpoints are intended for administrative purposes and should not be exposed to client applications.

-   **`POST /history/admin/clear-cache`**: Deletes a specific key from the Redis cache.
-   **`POST /history/jobs/trigger-hourly`**: Manually triggers the hourly data collection job.
-   **`POST /history/jobs/trigger-daily`**: Manually triggers the daily data aggregation job.