import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ScenarioPanel from './ScenarioPanel.jsx'

// Mock react-markdown as it can be complex in JSDOM
vi.mock('react-markdown', () => ({
  default: ({ children }) => <div>{children}</div>
}))

// Mock the artifact loader
vi.mock('../lib/scenarios.js', () => ({
  loadArtifact: vi.fn(() => Promise.resolve('Mock artifact content'))
}))

describe('ScenarioPanel', () => {
  const mockScenario = {
    id: 'test-scenario',
    title: 'Test Scenario',
    domain_name: 'Test Domain',
    level: 3,
    delivery_mode: 'A',
    presentation: {
      context: 'Test context',
      artifact_file: 'test-artifact.txt',
      type: 'script'
    }
  }

  it('renders correctly with scenario data', async () => {
    render(<ScenarioPanel scenario={mockScenario} onSubmit={vi.fn()} isEvaluating={false} />)
    
    expect(screen.getByText('Test Scenario')).toBeInTheDocument()
    expect(screen.getByText('Test Domain')).toBeInTheDocument()
    expect(screen.getByText('Level 3')).toBeInTheDocument()
    expect(screen.getByText('Test context')).toBeInTheDocument()
    
    // Artifact loading
    await waitFor(() => {
      expect(screen.getByText('Mock artifact content')).toBeInTheDocument()
    })
  })

  it('disables submit button when response is too short', () => {
    render(<ScenarioPanel scenario={mockScenario} onSubmit={vi.fn()} isEvaluating={false} />)
    
    const submitButton = screen.getByRole('button', { name: /Submit for Evaluation/i })
    expect(submitButton).toBeDisabled()
    
    const textarea = screen.getByPlaceholderText(/Write your analysis here/i)
    fireEvent.change(textarea, { target: { value: 'short response' } })
    
    expect(submitButton).toBeDisabled()
  })

  it('enables submit button and calls onSubmit when response is long enough', async () => {
    const handleSubmit = vi.fn()
    render(<ScenarioPanel scenario={mockScenario} onSubmit={handleSubmit} isEvaluating={false} />)
    
    // Wait for artifact to load so it's not null when submitting
    await waitFor(() => {
      expect(screen.getByText('Mock artifact content')).toBeInTheDocument()
    })

    const textarea = screen.getByPlaceholderText(/Write your analysis here/i)
    fireEvent.change(textarea, { target: { value: 'this is a long enough response for the test to pass the validation' } })
    
    const submitButton = screen.getByRole('button', { name: /Submit for Evaluation/i })
    expect(submitButton).not.toBeDisabled()
    
    fireEvent.click(submitButton)
    expect(handleSubmit).toHaveBeenCalledWith(
      'this is a long enough response for the test to pass the validation',
      'Mock artifact content'
    )
  })

  it('shows "Evaluating..." when isEvaluating is true', () => {
    render(<ScenarioPanel scenario={mockScenario} onSubmit={vi.fn()} isEvaluating={true} />)
    
    expect(screen.getByText('Evaluating…')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Evaluating…/i })).toBeDisabled()
  })
})
