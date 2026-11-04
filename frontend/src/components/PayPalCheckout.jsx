import { useState } from 'react'
import { PayPalButtons, usePayPalScriptReducer } from '@paypal/react-paypal-js'
import { postJSON } from '../api.js'

// PayPal Smart Buttons wired to our backend.
// The backend builds the order from the server-side cart, so the browser never sets the price.
export default function PayPalCheckout({ sessionId, total, onPaid }) {
  const [{ isPending }] = usePayPalScriptReducer()
  const [error, setError] = useState(null)
  const [processing, setProcessing] = useState(false)

  return (
    <div className="paypal">
      {isPending && <div className="skeleton" aria-label="Loading PayPal" />}
      {processing && <p className="status">Confirming your payment…</p>}
      {error && <p className="notice">{error}</p>}

      <PayPalButtons
        style={{ layout: 'vertical', shape: 'pill', label: 'pay', height: 44 }}
        forceReRender={[total]}
        disabled={processing}
        // 1. Ask our backend to create the PayPal order and return its ID.
        createOrder={async () => {
          setError(null)
          const { id } = await postJSON('/api/paypal/orders', { session_id: sessionId })
          return id
        }}
        // 2. After the buyer approves in the PayPal popup, have the backend capture it.
        onApprove={async (data) => {
          setProcessing(true)
          try {
            const result = await postJSON(`/api/paypal/orders/${data.orderID}/capture`, { session_id: sessionId })
            onPaid(result)
          } catch (err) {
            setError(`Payment couldn't be completed: ${err.message}`)
          } finally {
            setProcessing(false)
          }
        }}
        onCancel={() => setError('Payment cancelled. Your cart is still saved.')}
        onError={() => setError('Something went wrong with PayPal. Please try again.')}
      />
    </div>
  )
}
