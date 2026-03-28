export default function LabConsole({ session, phase }) {
  const isReady = (phase === 'ready' || phase === 'verifying' || phase === 'verified') && session?.guacamole_url

  return (
    <div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-gray-950">
      {isReady ? (
        <iframe
          src={session.guacamole_url}
          title="Lab console"
          className="flex-1 w-full bg-black"
          allow="fullscreen"
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
