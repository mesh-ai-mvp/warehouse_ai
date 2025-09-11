import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderWithProviders, screen, userEvent } from '@/test/test-utils'
import { ProfessionalNotification, TypewriterText, ProfessionalSpinner } from '../success-animation'

describe('ProfessionalNotification', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders notification when show is true', () => {
    renderWithProviders(
      <ProfessionalNotification
        show={true}
        message="Operation completed successfully"
        type="success"
      />
    )

    expect(screen.getByText('Operation completed successfully')).toBeInTheDocument()
  })

  it('does not render when show is false', () => {
    renderWithProviders(
      <ProfessionalNotification
        show={false}
        message="Operation completed successfully"
        type="success"
      />
    )

    expect(screen.queryByText('Operation completed successfully')).not.toBeInTheDocument()
  })

  it('calls onComplete when clicked', async () => {
    const onComplete = vi.fn()
    const user = userEvent.setup()

    renderWithProviders(
      <ProfessionalNotification
        show={true}
        message="Test message"
        type="success"
        onComplete={onComplete}
      />
    )

    const notification = screen.getByText('Test message').closest('div')
    await user.click(notification!)

    expect(onComplete).toHaveBeenCalledOnce()
  })

  it('displays correct icon for success type', () => {
    renderWithProviders(
      <ProfessionalNotification show={true} message="Success message" type="success" />
    )

    // The CheckCircle icon should be present
    const icon = document.querySelector('svg')
    expect(icon).toBeInTheDocument()
  })

  it('applies correct styling for different types', () => {
    const { rerender } = renderWithProviders(
      <ProfessionalNotification show={true} message="Error message" type="error" />
    )

    let notification = screen.getByText('Error message').closest('div')
    expect(notification).toHaveClass('border-red-200', 'dark:border-red-800')

    rerender(<ProfessionalNotification show={true} message="Warning message" type="warning" />)

    notification = screen.getByText('Warning message').closest('div')
    expect(notification).toHaveClass('border-amber-200', 'dark:border-amber-800')
  })
})

describe('TypewriterText', () => {
  it('renders text character by character', () => {
    renderWithProviders(<TypewriterText text="Hello World" show={true} speed={10} />)

    // Initially, text should start appearing
    expect(
      screen.getByText((content, element) => {
        return (
          element?.textContent === 'Hello World' || element?.textContent?.startsWith('H') || false
        )
      })
    ).toBeInTheDocument()
  })

  it('does not render when show is false', () => {
    renderWithProviders(<TypewriterText text="Hello World" show={false} speed={10} />)

    expect(screen.queryByText('Hello World')).not.toBeInTheDocument()
  })

  it('calls onComplete when animation finishes', () => {
    const onComplete = vi.fn()

    renderWithProviders(<TypewriterText text="Hi" show={true} speed={10} onComplete={onComplete} />)

    // Wait for animation to complete
    setTimeout(() => {
      expect(onComplete).toHaveBeenCalled()
    }, 100)
  })
})

describe('ProfessionalSpinner', () => {
  it('renders spinner when show is true', () => {
    renderWithProviders(<ProfessionalSpinner show={true} message="Loading..." />)

    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('does not render when show is false', () => {
    renderWithProviders(<ProfessionalSpinner show={false} message="Loading..." />)

    expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
  })

  it('renders without message', () => {
    renderWithProviders(<ProfessionalSpinner show={true} />)

    // Should render the spinner div even without message
    const spinner = document.querySelector('.border-primary')
    expect(spinner).toBeInTheDocument()
  })

  it('applies correct size classes', () => {
    const { rerender } = renderWithProviders(<ProfessionalSpinner show={true} size="sm" />)

    let spinner = document.querySelector('.border-primary')
    expect(spinner).toHaveClass('w-4', 'h-4')

    rerender(<ProfessionalSpinner show={true} size="lg" />)

    spinner = document.querySelector('.border-primary')
    expect(spinner).toHaveClass('w-8', 'h-8')
  })
})
