/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { cpSync, existsSync, readFileSync } from 'node:fs'
import { resolve, sep } from 'node:path'

const scenariosRoot = resolve(import.meta.dirname, '../../scenarios')
const artifactPrefix = '/scenarios/'

// Docker copies artifacts after building, but local dev and `vite preview`
// need the same route. Keep it configured here rather than relying on a
// developer's untracked public/ copy.
function scenarioArtifacts() {
  const serveArtifacts = (server) => {
    server.middlewares.use((req, res, next) => {
      if (!req.url?.startsWith(artifactPrefix)) return next()
      const relativePath = decodeURIComponent(req.url.slice(artifactPrefix.length).split('?')[0])
      const file = resolve(scenariosRoot, relativePath)
      if (!file.startsWith(`${scenariosRoot}${sep}`) || !existsSync(file)) return next()
      res.setHeader('Content-Type', 'text/plain; charset=utf-8')
      res.end(readFileSync(file))
    })
  }

  return {
    name: 'scenario-artifacts',
    configureServer: serveArtifacts,
    configurePreviewServer: serveArtifacts,
    closeBundle() {
      cpSync(scenariosRoot, resolve(import.meta.dirname, 'dist/scenarios'), { recursive: true })
    },
  }
}

export default defineConfig({
  plugins: [react(), scenarioArtifacts()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
  },
})
