import { useEffect, useState } from 'react'
import { PayPalScriptProvider } from '@paypal/react-paypal-js'
import ChatWindow from './components/ChatWindow.jsx'

const SESSION_KEY = 'shoppal-session'

// One session ID per browser tab; the backend keys the cart and chat history on it.
function newSessionId() {
  const id = crypto.randomUUID()
  try {
    sessionStorage.setItem(SESSION_KEY, id)
  } catch {
    // Storage can be blocked (e.g. private mode); an in-memory ID still works.
  }
  return id
}

function getSessionId() {
  try {
    return sessionStorage.getItem(SESSION_KEY) || newSessionId()
  } catch {
    return newSessionId()
  }
}

export default function App() {
  const [sessionId, setSessionId] = useState(getSessionId)
  // null = still loading config, '' = PayPal not configured
  const [paypalClientId, setPaypalClientId] = useState(null)

  // Fetch the PayPal client ID from the backend so it only lives in one .env file.
  useEffect(() => {
    fetch('/api/config')
      .then((res) => res.json())
      .then((cfg) => setPaypalClientId(cfg.paypal_client_id || ''))
      .catch(() => setPaypalClientId(''))
  }, [])

  if (paypalClientId === null) {
    return (
      <div className="splash">
        <div className="spinner" aria-label="Loading" />
      </div>
    )
  }

  // Keying on sessionId means "New chat" remounts the window with a fresh, empty state.
  const chat = (
    <ChatWindow
      key={sessionId}
      sessionId={sessionId}
      paypalEnabled={Boolean(paypalClientId)}
      onNewChat={() => setSessionId(newSessionId())}
    />
  )

  return paypalClientId ? (
    <PayPalScriptProvider options={{ clientId: paypalClientId, currency: 'USD', intent: 'capture' }}>
      {chat}
    </PayPalScriptProvider>
  ) : (
    chat
  )
}
