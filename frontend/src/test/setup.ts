import '@testing-library/jest-dom'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

// Cleanup after each test
afterEach(() => {
  cleanup()
})

// Mock global objects that may not be available in test environment
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock IntersectionObserver
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock scrollIntoView
Element.prototype.scrollIntoView = vi.fn()

// Mock for Plotly.js
vi.mock('plotly.js', () => ({
  default: {
    newPlot: vi.fn(),
    react: vi.fn(),
    redraw: vi.fn(),
    purge: vi.fn(),
  },
}))

// Mock for framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: 'div',
    button: 'button',
    span: 'span',
    a: 'a',
    form: 'form',
    input: 'input',
    textarea: 'textarea',
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => children,
  useMotionValue: () => ({ set: vi.fn(), get: vi.fn() }),
  useSpring: () => ({ set: vi.fn(), get: vi.fn() }),
  useTransform: () => ({ set: vi.fn(), get: vi.fn() }),
}))
