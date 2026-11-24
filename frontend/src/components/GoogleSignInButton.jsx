import { useEffect, useRef } from 'react'
import { useGoogleOAuth } from '@react-oauth/google'

let initializedClientId
let activeCallbacks

export default function GoogleSignInButton({ onSuccess, onError, text }) {
  const buttonRef = useRef(null)
  const { clientId, scriptLoadedSuccessfully } = useGoogleOAuth()
  const width = Math.max(200, Math.min(360, window.innerWidth - 90))

  useEffect(() => {
    if (!scriptLoadedSuccessfully) return

    const googleIdentity = window.google?.accounts?.id
    const container = buttonRef.current
    if (!googleIdentity || !container) return

    activeCallbacks = { onSuccess, onError }
    if (initializedClientId && initializedClientId !== clientId) {
      throw new Error('Google Identity Services is already initialized with another client ID.')
    }
    if (!initializedClientId) {
      googleIdentity.initialize({
        client_id: clientId,
        callback: (response) => {
          const callbacks = activeCallbacks
          if (response?.credential) {
            callbacks?.onSuccess(response)
          } else {
            callbacks?.onError()
          }
        },
      })
      initializedClientId = clientId
    }

    container.replaceChildren()
    googleIdentity.renderButton(container, {
      type: 'standard',
      theme: 'outline',
      size: 'large',
      text,
      shape: 'rectangular',
      width,
    })

    return () => container.replaceChildren()
  }, [clientId, onError, onSuccess, scriptLoadedSuccessfully, text, width])

  return <div className="google-signin-button" ref={buttonRef} />
}
