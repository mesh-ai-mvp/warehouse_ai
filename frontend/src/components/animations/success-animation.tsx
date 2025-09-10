import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, AlertCircle, Info, AlertTriangle } from 'lucide-react';

interface SuccessAnimationProps {
  show: boolean;
  message?: string;
  type?: 'success' | 'error' | 'warning' | 'info';
  onComplete?: () => void;
}

export function ProfessionalNotification({ 
  show, 
  message = "Operation completed", 
  type = 'success',
  onComplete 
}: SuccessAnimationProps) {
  if (!show) return null;

  const getIcon = () => {
    switch (type) {
      case 'success': return CheckCircle;
      case 'error': return AlertCircle;
      case 'warning': return AlertTriangle;
      case 'info': return Info;
      default: return CheckCircle;
    }
  };

  const getColors = () => {
    switch (type) {
      case 'success': 
        return {
          bg: 'bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-800',
          icon: 'text-green-600 dark:text-green-400',
          text: 'text-green-900 dark:text-green-100'
        };
      case 'error':
        return {
          bg: 'bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800',
          icon: 'text-red-600 dark:text-red-400',
          text: 'text-red-900 dark:text-red-100'
        };
      case 'warning':
        return {
          bg: 'bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800',
          icon: 'text-amber-600 dark:text-amber-400',
          text: 'text-amber-900 dark:text-amber-100'
        };
      case 'info':
        return {
          bg: 'bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800',
          icon: 'text-blue-600 dark:text-blue-400',
          text: 'text-blue-900 dark:text-blue-100'
        };
      default:
        return {
          bg: 'bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-800',
          icon: 'text-green-600 dark:text-green-400',
          text: 'text-green-900 dark:text-green-100'
        };
    }
  };

  const Icon = getIcon();
  const colors = getColors();

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -50, scale: 0.9 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -50, scale: 0.9 }}
        transition={{ 
          type: "spring",
          stiffness: 300,
          damping: 30,
          duration: 0.4
        }}
        className="fixed top-4 right-4 z-50 max-w-sm"
      >
        <motion.div
          className={`${colors.bg} border rounded-lg shadow-lg p-4 cursor-pointer`}
          onClick={onComplete}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <div className="flex items-start gap-3">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.1, type: "spring", stiffness: 400 }}
              className={`${colors.icon} flex-shrink-0`}
            >
              <Icon className="w-5 h-5" />
            </motion.div>
            
            <motion.div
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.2, duration: 0.3 }}
              className="flex-1"
            >
              <p className={`text-sm font-medium ${colors.text}`}>
                {message}
              </p>
            </motion.div>
          </div>

          {/* Professional progress bar */}
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: "100%" }}
            transition={{ delay: 0.5, duration: 3, ease: "linear" }}
            className="absolute bottom-0 left-0 h-0.5 bg-current opacity-20 rounded-b-lg"
            onAnimationComplete={onComplete}
          />
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

// Professional text generation effect for loading states
export function TypewriterText({ 
  text, 
  show, 
  speed = 50, 
  onComplete 
}: { 
  text: string; 
  show: boolean; 
  speed?: number; 
  onComplete?: () => void 
}) {
  if (!show) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="font-mono text-sm text-muted-foreground"
    >
      {text.split('').map((char, index) => (
        <motion.span
          key={index}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{
            delay: index * (speed / 1000),
            duration: 0.05
          }}
          onAnimationComplete={() => {
            if (index === text.length - 1) {
              onComplete?.();
            }
          }}
        >
          {char}
        </motion.span>
      ))}
    </motion.div>
  );
}

// Professional loading states with smooth transitions  
export function ProfessionalSpinner({ 
  show, 
  message, 
  size = 'md' 
}: { 
  show: boolean; 
  message?: string; 
  size?: 'sm' | 'md' | 'lg' 
}) {
  if (!show) return null;

  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6', 
    lg: 'w-8 h-8'
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="flex items-center gap-3"
    >
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
        className={`${sizeClasses[size]} border-2 border-primary border-r-transparent rounded-full`}
      />
      {message && (
        <motion.span
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
          className="text-sm text-muted-foreground"
        >
          {message}
        </motion.span>
      )}
    </motion.div>
  );
}

// Smooth fade transitions for content
export function FadeTransition({ 
  show, 
  children, 
  duration = 0.3 
}: { 
  show: boolean; 
  children: React.ReactNode; 
  duration?: number 
}) {
  return (
    <AnimatePresence mode="wait">
      {show && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration, ease: "easeInOut" }}
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  );
}