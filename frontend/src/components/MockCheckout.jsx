import { useState } from 'react'
import { postJSON } from '../api.js'

// Stand-in for the PayPal button when PayPal keys aren't configured (development only).
// It calls the same backend endpoints as the real button, so order creation, capture,
// the agent's confirmation and the receipt are all exercised end to end.
export default function MockCheckout({ sessionId, total, onPaid }) {
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState(null)

  async function pay() {
    setProcessing(true)
    setError(null)
    try {
      const { id } = await postJSON('/api/paypal/orders', { session_id: sessionId })
      const result = await postJSON(`/api/paypal/orders/${id}/capture`, { session_id: sessionId })
      onPaid(result)
    } catch (err) {
      setError(`Payment couldn't be completed: ${err.message}`)
    } finally {
      setProcessing(false)
    }
  }

  return (
    <div className="mock-checkout">
      {error && <p className="notice">{error}</p>}
      <button className="primary-btn" onClick={pay} disabled={processing}>
        {processing ? 'Processing…' : `Simulate payment · $${total}`}
      </button>
      <p className="mock-note">Demo mode: PayPal keys aren't set, so no real PayPal call is made.</p>
    </div>
  )
}
