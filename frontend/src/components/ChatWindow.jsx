import { useEffect, useRef, useState } from 'react'
import MessageBubble from './MessageBubble.jsx'
import CartDrawer from './CartDrawer.jsx'
import { ArrowUpIcon, BagIcon, EditIcon, SparkIcon } from './Icons.jsx'
import { postJSON } from '../api.js'

const SUGGESTIONS = [
  { title: 'A gift for mom', prompt: 'I need a gift for my mom under $50' },
  { title: 'Laptop backpack', prompt: 'I want a laptop bag under $120' },
  { title: 'Jackets for men', prompt: 'Show me jackets for men' },
  { title: 'Something sparkly', prompt: 'Show me jewelry under $20' },
]

// Chat input that grows with its content. Enter sends, Shift+Enter adds a new line.
function Composer({ value, onChange, onSubmit, disabled, autoFocus }) {
  const ref = useRef(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }, [value])

  return (
    <form
      className="composer"
      onSubmit={(e) => {
        e.preventDefault()
        onSubmit()
      }}
    >
      <textarea
        ref={ref}
        rows={1}
        value={value}
        autoFocus={autoFocus}
        placeholder="Ask for anything — “a nice ring under $20”"
        aria-label="Message ShopPal"
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault()
            onSubmit()
          }
        }}
      />
      <button type="submit" className="send-btn" disabled={disabled || !value.trim()} aria-label="Send">
        <ArrowUpIcon />
      </button>
    </form>
  )
}

function TypingIndicator() {
  return (
    <div className="msg assistant">
      <div className="avatar"><SparkIcon /></div>
      <div className="typing" aria-label="ShopPal is thinking">
        <span /><span /><span />
      </div>
    </div>
  )
}

export default function ChatWindow({ sessionId, paypalEnabled, onNewChat }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [cart, setCart] = useState(null) // latest cart snapshot from the server
  const [cartOpen, setCartOpen] = useState(false)
  const threadRef = useRef(null)

  // Keep the newest message in view.
  useEffect(() => {
    const el = threadRef.current
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [messages, loading])

  async function sendMessage(raw) {
    const text = raw.trim()
    if (!text || loading) return

    setMessages((prev) => [...prev, { role: 'user', text }])
    setInput('')
    setLoading(true)
    try {
      const data = await postJSON('/api/chat', { session_id: sessionId, message: text })
      if (data.cart) setCart(data.cart)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: data.reply, products: data.products, cart: data.cart, checkout: data.checkout },
      ])
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'assistant', text: err.message, error: true }])
    } finally {
      setLoading(false)
    }
  }

  // Called by PayPalCheckout after the backend captures the payment.
  function handlePaid(result) {
    setCart(null)
    setMessages((prev) => [
      // Retire earlier checkout panels now that this cart is paid for.
      ...prev.map((m) => (m.checkout ? { ...m, checkout: false, cart: null } : m)),
      { role: 'assistant', text: result.reply, order: result.order, orderId: result.order_id },
    ])
  }

  // Only the most recent checkout message shows a live PayPal button.
  const lastCheckoutIndex = messages.findLastIndex((m) => m.checkout)
  const cartCount = cart?.item_count || 0
  const cartIds = new Set(cart?.items.map((i) => i.id))
  const isEmpty = messages.length === 0

  const composer = (
    <Composer value={input} onChange={setInput} onSubmit={() => sendMessage(input)} disabled={loading} autoFocus />
  )

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark"><BagIcon /></span>
          <span className="brand-name">ShopPal</span>
          <span className="badge">{paypalEnabled ? 'Sandbox' : 'Demo mode'}</span>
        </div>
        <div className="topbar-actions">
          {!isEmpty && (
            <button className="icon-btn" onClick={onNewChat} aria-label="New chat" title="New chat">
              <EditIcon />
            </button>
          )}
          <button className="cart-btn" onClick={() => setCartOpen(true)} aria-label={`Cart, ${cartCount} items`}>
            <BagIcon />
            <span className="cart-label">Cart</span>
            {cartCount > 0 && <span key={cartCount} className="count">{cartCount}</span>}
          </button>
        </div>
      </header>

      <main className="thread" ref={threadRef}>
        {isEmpty ? (
          <section className="hero">
            <div className="hero-mark"><SparkIcon width={22} height={22} /></div>
            <h1>What are you shopping for?</h1>
            <p className="hero-sub">
              Describe it in your own words. ShopPal finds it, fills your cart, and checks you out with PayPal.
            </p>
            {composer}
            <div className="suggestions">
              {SUGGESTIONS.map((s) => (
                <button key={s.title} className="suggestion" onClick={() => sendMessage(s.prompt)}>
                  <span className="suggestion-title">{s.title}</span>
                  <span className="suggestion-prompt">{s.prompt}</span>
                </button>
              ))}
            </div>
          </section>
        ) : (
          <div className="messages">
            {messages.map((message, i) => (
              <MessageBubble
                key={i}
                message={message}
                showCheckout={i === lastCheckoutIndex}
                sessionId={sessionId}
                paypalEnabled={paypalEnabled}
                cartIds={cartIds}
                busy={loading}
                onAddToCart={(p) => sendMessage(`Add "${p.title}" (product #${p.id}) to my cart`)}
                onOpenCart={() => setCartOpen(true)}
                onPaid={handlePaid}
              />
            ))}
            {loading && <TypingIndicator />}
          </div>
        )}
      </main>

      {!isEmpty && (
        <footer className="dock">
          <div className="dock-inner">
            {composer}
            <p className="fineprint">
              {paypalEnabled ? 'Payments run in PayPal Sandbox.' : 'Demo mode: payments are simulated.'} No real money moves.
            </p>
          </div>
        </footer>
      )}

      <CartDrawer
        open={cartOpen}
        cart={cart}
        busy={loading}
        onClose={() => setCartOpen(false)}
        onRemove={(item) => sendMessage(`Remove "${item.title}" (product #${item.id}) from my cart`)}
        onCheckout={() => {
          setCartOpen(false)
          sendMessage("I'm ready to check out")
        }}
      />
    </div>
  )
}
