# 🛍️ ShopPal — AI Commerce Agent with PayPal

ShopPal is a conversational shopping agent. Tell it what you want in plain English
("I need a gift for my mom under $50"), and it searches the catalog, recommends options
as product cards, manages your cart, and checks you out with **PayPal**, all inside the chat.

Built for the **Build What's Next with PayPal and AI** hackathon.

## How it works

```
React chat UI  ──►  Flask    ──►  Gemini (function calling)
     │                 │               │ decides which tool to call
     │                 │               ▼
     │                 ├── search_products / get_product_details ──► Fake Store API
     │                 ├── add_to_cart / view_cart / remove_from_cart (server-side cart)
     │                 └── checkout ──► shows PayPal button in chat
     │
     └── PayPal JS SDK ──► /api/paypal/orders (create) ──► PayPal Orders v2 API
                       ──► /api/paypal/orders/{id}/capture ──► agent writes order confirmation
```

- **Agentic loop** ([backend/app/agent.py](backend/app/agent.py)): the model chooses tools, sees their results, and keeps going until it has an answer.
- **Tools** ([backend/app/tools.py](backend/app/tools.py)): each returns data for the LLM *and* structured UI data (product cards, cart, checkout flag) for the frontend.
- **Secure payments** ([backend/app/paypal.py](backend/app/paypal.py)): order totals are computed on the server from the cart, never from the browser. Orders are itemized, so the buyer sees each product in PayPal.

## Tech stack

| Layer    | Tech |
|----------|------|
| Frontend | React + Vite, `@paypal/react-paypal-js` |
| Backend  | Python, Flask, httpx (gunicorn in production) |
| AI       | Google Gemini with function calling (via its OpenAI-compatible API) |
| Products | [Fake Store API](https://fakestoreapi.com) |
| Payments | PayPal REST API (Orders v2), sandbox |
| Hosting  | Render |

## Local setup

**Prerequisites:** Python 3.11+, Node 18+, a Gemini API key (free at <https://aistudio.google.com/apikey>), and a PayPal developer account.

### 1. Get PayPal sandbox credentials
1. Go to <https://developer.paypal.com/dashboard/applications/sandbox> and create an app.
2. Copy the **Client ID** and **Secret**.
3. Under **Sandbox accounts**, note the auto-created *Personal* account email and password. You'll log in with it to "pay" during testing.

### 2. Configure environment
```bash
cp .env.example .env
# then edit .env and fill in GEMINI_API_KEY, PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET
```

### 3. Run the backend (terminal 1)
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
flask --app app.main run --port 5001 --debug
```

### 4. Run the frontend (terminal 2)
```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. Vite forwards `/api` calls to the backend.

## Deploy to Render

1. Push this repo to GitHub.
2. In Render, choose **New → Blueprint** and select the repo. Render reads [render.yaml](render.yaml).
3. Enter `GEMINI_API_KEY`, `PAYPAL_CLIENT_ID`, and `PAYPAL_CLIENT_SECRET` when prompted.

The build compiles the frontend, and Flask serves it with the API from a single service.

> Note: carts and chat history are kept in memory. On Render's free tier the service sleeps
> when idle, which resets sessions. That's fine for a demo.

## Try it

- "I want a laptop bag under $120"
- "I'll take the first one"
- "Actually, also show me some jewelry for my mom"
- "Checkout": pay with your sandbox Personal account in the PayPal popup

## License

[MIT](LICENSE)
