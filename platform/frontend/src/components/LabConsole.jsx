import { useRef, useEffect } from 'react'

export default function LabConsole({ session, phase }) {
  const iframeRef = useRef(null)
  const isReady = (phase === 'ready' || phase === 'verifying' || phase === 'verified') && session?.guacamole_url

  // Focus the iframe as soon as the lab becomes ready so keyboard input
  // goes straight into Guacamole without requiring an extra click.
  useEffect(() => {
    if (isReady) {
      const t = setTimeout(() => iframeRef.current?.focus(), 200)
      return () => clearTimeout(t)
    }
  }, [isReady])

  return (
    <div
      className="flex-1 flex flex-col min-w-0 overflow-hidden bg-gray-950"
      onClick={() => iframeRef.current?.focus()}
    >
      {isReady ? (
        <iframe
          ref={iframeRef}
          src={session.guacamole_url}
          title="Lab console"
          className="flex-1 w-full bg-black"
          allow="fullscreen"
          tabIndex={0}
        />
      ) : (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-sm text-gray-600">
            {phase === 'idle'
              ? 'Start the lab to connect to the environment.'
              : phase === 'error'
                ? 'Environment unavailable.'
                : 'Preparing environment…'}
          </p>
        </div>
      )}
    </div>
  )
}
