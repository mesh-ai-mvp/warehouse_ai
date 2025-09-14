import { useState, useEffect } from 'react';

export interface Toast {
  id?: string;
  title?: string;
  description?: string;
  variant?: 'default' | 'destructive' | 'success';
}

interface ToastState {
  toasts: Toast[];
}

const toastState: ToastState = {
  toasts: [],
};

let listeners: Array<(state: ToastState) => void> = [];

function dispatch(action: Toast) {
  const id = Math.random().toString(36).substring(2, 9);
  const newToast = { ...action, id };

  toastState.toasts = [...toastState.toasts, newToast];

  // Notify all listeners
  listeners.forEach(listener => {
    listener(toastState);
  });

  // Auto-dismiss after 5 seconds
  setTimeout(() => {
    toastState.toasts = toastState.toasts.filter(t => t.id !== id);
    listeners.forEach(listener => {
      listener(toastState);
    });
  }, 5000);
}

export function toast(props: Toast) {
  dispatch(props);
}

export function useToast() {
  const [state, setState] = useState<ToastState>(toastState);

  useEffect(() => {
    listeners.push(setState);
    return () => {
      listeners = listeners.filter(l => l !== setState);
    };
  }, []);

  return {
    toasts: state.toasts,
    toast,
    dismiss: (toastId?: string) => {
      if (toastId) {
        toastState.toasts = toastState.toasts.filter(t => t.id !== toastId);
      } else {
        toastState.toasts = [];
      }
      listeners.forEach(listener => {
        listener(toastState);
      });
    },
  };
}