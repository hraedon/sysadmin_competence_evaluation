import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import EvalPanel from './EvalPanel.jsx'
import LabConsole from './LabConsole.jsx'
import LabInfoPanel from './LabInfoPanel.jsx'

describe('Mode E responsive layout', () => {
  it('keeps the evaluation panel below the console until the large breakpoint', () => {
    render(<EvalPanel isLabMode result={null} isEvaluating={false} />)
    fireEvent.click(screen.getByTitle('Expand evaluation panel'))

    expect(screen.getByText('Evaluation will appear here.').parentElement.parentElement)
      .toHaveClass('w-full', 'lg:w-80', 'lg:border-l')
  })

  it('uses a bounded console height in the narrow stacked layout', () => {
    render(<LabConsole phase="ready" session={{ guacamole_url: 'about:blank' }} />)

    expect(screen.getByTitle('Lab console').parentElement).toHaveClass('min-h-[50vh]', 'lg:min-h-0')
  })

  it('keeps lab instructions full width until the large breakpoint', () => {
    render(<LabInfoPanel
      scenario={{ domain_name: 'Test', level: 1, title: 'Lab', presentation: { modes: { E: {} } } }}
      phase="idle"
      handleStartLab={vi.fn()}
    />)

    expect(screen.getByText('Lab Exercise').closest('div[class*="w-full"]')).toHaveClass('w-full', 'lg:w-80')
  })
})
