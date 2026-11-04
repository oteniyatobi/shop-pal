import ProductCard from './ProductCard.jsx'
import PayPalCheckout from './PayPalCheckout.jsx'
import MockCheckout from './MockCheckout.jsx'
import { CheckIcon, LockIcon, SparkIcon } from './Icons.jsx'

// Inline formatting: **bold** becomes <strong>. No HTML is ever injected.
function Inline({ text }) {
  return text.split(/\*\*(.+?)\*\*/g).map((part, i) => (i % 2 ? <strong key={i}>{part}</strong> : part))
}

// Render the model's text as paragraphs and bullet lists (lines starting with "* " or "- ").
function FormattedText({ text, error }) {
  const blocks = []
  for (const line of text.split('\n')) {
    const bullet = line.match(/^\s*[*-]\s+(.*)/)
    const last = blocks[blocks.length - 1]
    if (bullet) {
      if (last?.type === 'list') last.items.push(bullet[1])
      else blocks.push({ type: 'list', items: [bullet[1]] })
    } else if (line.trim()) {
      if (last?.type === 'p') last.lines.push(line)
      else blocks.push({ type: 'p', lines: [line] })
    } else {
      blocks.push({ type: 'gap' }) // blank line: the next text starts a new paragraph
    }
  }

  return (
    <div className={`msg-text${error ? ' error' : ''}`}>
      {blocks.map((b, i) => {
        if (b.type === 'list') {
          return (
            <ul key={i}>
              {b.items.map((item, j) => <li key={j}><Inline text={item} /></li>)}
            </ul>
          )
        }
        if (b.type === 'p') return <p key={i}><Inline text={b.lines.join('\n')} /></p>
        return null
      })}
    </div>
  )
}

// Itemized list with thumbnails and a total, shared by checkout and receipt cards.
function LineItems({ cart }) {
  return (
    <>
      <ul className="line-items">
        {cart.items.map((item) => (
          <li key={item.id} className="line">
            <div className="line-media"><img src={item.image} alt="" /></div>
            <div className="line-info">
              <div className="line-title">{item.title}</div>
              <div className="line-qty">Qty {item.quantity} · ${item.unit_price}</div>
            </div>
            <div className="line-price">${item.line_total}</div>
          </li>
        ))}
      </ul>
      <div className="total-row">
        <span>Total</span>
        <strong>${cart.total}</strong>
      </div>
    </>
  )
}

// Compact "cart updated" chip with stacked thumbnails.
function CartChip({ cart, onOpen }) {
  if (!cart?.items?.length) return null
  return (
    <div className="cart-chip">
      <div className="thumbs">
        {cart.items.slice(0, 3).map((item) => (
          <img key={item.id} src={item.image} alt="" />
        ))}
      </div>
      <span className="cart-chip-text">
        {cart.item_count} {cart.item_count === 1 ? 'item' : 'items'} · <strong>${cart.total}</strong>
      </span>
      <button className="link-btn" onClick={onOpen}>View cart</button>
    </div>
  )
}

export default function MessageBubble({
  message,
  showCheckout,
  sessionId,
  paypalEnabled,
  cartIds,
  busy,
  onAddToCart,
  onOpenCart,
  onPaid,
}) {
  const { role, text, products, cart, checkout, order, orderId, error } = message

  if (role === 'user') {
    return (
      <div className="msg user">
        <div className="user-bubble">{text}</div>
      </div>
    )
  }

  const showCheckoutCard = checkout && showCheckout && cart?.items?.length > 0

  return (
    <div className="msg assistant">
      <div className="avatar"><SparkIcon /></div>
      <div className="msg-body">
        {text && <FormattedText text={text} error={error} />}

        {products?.length > 0 && (
          <div className="product-row">
            {products.map((p, i) => (
              <ProductCard
                key={p.id}
                product={p}
                index={i + 1}
                inCart={cartIds.has(p.id)}
                disabled={busy}
                onAdd={onAddToCart}
              />
            ))}
          </div>
        )}

        {showCheckoutCard ? (
          <div className="panel checkout-card">
            <div className="panel-header">
              <span className="panel-title">Checkout</span>
              <span className="secure">
                <LockIcon width={13} height={13} /> {paypalEnabled ? 'Secured by PayPal' : 'Demo checkout'}
              </span>
            </div>
            <LineItems cart={cart} />
            <div className="panel-actions">
              {paypalEnabled ? (
                <PayPalCheckout sessionId={sessionId} total={cart.total} onPaid={onPaid} />
              ) : (
                <MockCheckout sessionId={sessionId} total={cart.total} onPaid={onPaid} />
              )}
            </div>
          </div>
        ) : (
          // Show a cart chip whenever a tool changed the cart, unless product cards already fill this message.
          cart && !products?.length && <CartChip cart={cart} onOpen={onOpenCart} />
        )}

        {order && (
          <div className="panel receipt">
            <div className="receipt-header">
              <span className="receipt-check"><CheckIcon width={16} height={16} /></span>
              <div>
                <div className="panel-title">Payment complete</div>
                <div className="order-id">Order {orderId}</div>
              </div>
            </div>
            <LineItems cart={order} />
          </div>
        )}
      </div>
    </div>
  )
}
